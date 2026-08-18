"""The agent as an explicit state machine.

The three safety layers are the same ones the hand-written loop enforced, but
each is now its own node, so the flow can be inspected and every step measured:

    score_gate ─(unsafe)─► refuse
        │ (safe)
        ▼
    llm_turn ─(tool call)─► run_tools ─┐
        │ ▲                             │
        │ └─────────────────────────────┘  (bounded by max_tool_turns)
        │ (answered without consulting anything) ─► inject_context ─┘
        │                                   (budget spent) ─► final_answer ─┐
        ▼                                                                   │
    citation_check ◄────────────────────────────────────────────────────────┘
        │ (no citation)─► repair ─► citation_check ─► no_info
        │ (cited)
        ▼
      finish

`final_answer` re-asks the model with the tools withheld. Two measured failures
land there, both of which used to throw away a correct context:

  gpt-5-mini          repeats the same search every turn and never writes text,
                      spending the whole budget
  Phi-4-mini-instruct returns an empty message while the tool schema is in
                      front of it, and answers normally once it is withheld

See docs/02-karar-kaydi.md ADR-011 for why this replaced the raw loop.
"""

import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from azure.rag.models import TokenUsage
from azure.rag.prompts import (
    CITATION_REMINDER,
    CITATION_REPAIR,
    NO_INFO_TEMPLATE,
    REFUSAL_TEMPLATE,
    SYSTEM_PROMPT,
    USER_NAME_LINE,
)
from azure.rag.tools import TOOL_SCHEMAS

# `[tool: search_documents]` — the placeholder run_tools writes into the
# transcript. Matched only as a whole line; see `_strip_tool_markers`.
_TOOL_MARKER = re.compile(r"^\s*\[tool:[^\]]*\]\s*$")


class AgentState(TypedDict, total=False):
    question: str
    messages: list[dict[str, Any]]
    tool_outputs: list[str]
    trace: list[dict[str, Any]]
    final_text: str
    citations: list[str]
    repaired: bool
    # True once the toolless answer turn has run, so it cannot run twice.
    answered_toolless: bool
    gate_passed: bool
    turns: int
    usage: TokenUsage
    # Tool calls the last llm_turn asked for. Declared in the schema because
    # LangGraph only carries keys the state type knows about.
    pending_tool_calls: list[Any]
    # Session conversation history, or None for a stateless single question.
    memory: Any
    user_name: str | None


def _strip_tool_markers(text: str) -> str:
    """Drop `[tool: name]` placeholder lines the model copied from the transcript.

    `run_tools` records each call as an assistant message reading
    `[tool: search_documents]`. In the toolless answer turn that transcript is
    the model's context, and gpt-5-mini was measured imitating the format —
    the marker then reached the user. Only whole lines are removed, so a
    citation or a sentence that merely contains brackets survives.
    """
    kept = [line for line in text.splitlines() if not _TOOL_MARKER.match(line)]
    return "\n".join(kept).strip()


def _system_prompt(state: "AgentState") -> str:
    """The grounded prompt, plus one line naming the user when one is known.

    Kept to a single appended sentence on purpose: Task 12 measured that every
    extra instruction in this prompt can stop qwen2.5-7b calling its tools at
    all. With no name, the prompt is byte-identical to the tested one.
    """
    name = (state.get("user_name") or "").strip()
    if not name:
        return SYSTEM_PROMPT
    return f"{SYSTEM_PROMPT}\n\n{USER_NAME_LINE.format(name=name)}"


def initial_state(question: str, memory=None, user_name: str | None = None) -> AgentState:
    """A fresh state for one question, optionally carrying history and identity."""
    return AgentState(
        question=question,
        memory=memory,
        user_name=user_name,
        messages=[],
        tool_outputs=[],
        trace=[],
        final_text="",
        citations=[],
        repaired=False,
        answered_toolless=False,
        gate_passed=False,
        turns=0,
        usage=TokenUsage(),
        pending_tool_calls=[],
    )


def build_graph(retriever, toolbox, llm, max_tool_turns: int = 3):
    """Compile the agent graph for one retriever/toolbox/LLM triple."""
    from azure.rag.agent import extract_citations

    def score_gate(state: AgentState) -> AgentState:
        from azure.rag.memory import retrieval_query

        memory = state.get("memory")
        # Search with the widened query so a follow-up question still reaches
        # its documents; the model still sees exactly what the user typed.
        hits = retriever.search(retrieval_query(state["question"], memory), top_k=5)
        passed = retriever.is_confident(hits)

        history = memory.as_messages() if memory is not None else []
        return {
            "gate_passed": passed,
            "messages": [
                {"role": "system", "content": _system_prompt(state)},
                *history,
                {"role": "user", "content": state["question"]},
            ],
        }

    def refuse(state: AgentState) -> AgentState:
        return {"final_text": REFUSAL_TEMPLATE, "citations": []}

    def llm_turn(state: AgentState) -> AgentState:
        response = llm.chat(state["messages"], TOOL_SCHEMAS)
        update: AgentState = {
            "turns": state["turns"] + 1,
            "usage": state["usage"] + response.usage,
            "pending_tool_calls": list(response.tool_calls),
        }
        if not response.tool_calls:
            update["final_text"] = response.text or ""
        return update

    def _add_tool_result(state: AgentState, name, arguments, injected: bool) -> AgentState:
        output = toolbox.run(name, arguments)
        # The name rides here as well as in the system prompt. Measured: with it
        # only in the system prompt, qwen2.5-7b never used it — the same failure
        # Task 12 saw with the citation rule, and the same fix.
        reminder = CITATION_REMINDER
        user_name = (state.get("user_name") or "").strip()
        if user_name:
            reminder = f"{reminder} {USER_NAME_LINE.format(name=user_name)}"
        return {
            "tool_outputs": [*state["tool_outputs"], output],
            "trace": [
                *state["trace"],
                {
                    "name": name,
                    "arguments": arguments,
                    "chars": len(output),
                    "injected": injected,
                },
            ],
            "messages": [
                *state["messages"],
                {"role": "assistant", "content": f"[tool: {name}]"},
                {"role": "user", "content": f"{output}\n\n{reminder}"},
            ],
        }

    def run_tools(state: AgentState) -> AgentState:
        update: AgentState = {}
        working = dict(state)
        for call in state["pending_tool_calls"]:
            update = _add_tool_result(working, call.name, call.arguments, injected=False)
            working.update(update)
        return update

    def inject_context(state: AgentState) -> AgentState:
        # The model answered without consulting the documents. Small local models
        # skip the tool call unpredictably, so retrieve on its behalf rather than
        # losing the answer to the citation gate. Widened like the gate's search:
        # a follow-up question alone would pull the wrong documents.
        from azure.rag.memory import retrieval_query

        query = retrieval_query(state["question"], state.get("memory"))
        return _add_tool_result(state, "search_documents", {"query": query}, injected=True)

    def final_answer(state: AgentState) -> AgentState:
        """Bütçe bitti: araçsız bir tur isteyerek toplanan bağlamı cevaba çevir.

        Ölçüldü (canlı `gpt-5-mini`): akıl yürüten model sistem promptundaki
        "cevap vermeden önce HER ZAMAN ara" talimatını her turda yeniden
        değerlendirip aynı aramayı tekrarlıyor ve hiç metin yazmıyor. Araç
        şeması gönderilmediğinde arama seçeneği ortadan kalkar ve model
        önündeki kaynaklardan cevabı yazar.

        `tools=None` bu düğümün tamamı: prompt değişmiyor, bağlam değişmiyor,
        yalnızca araçlar geri çekiliyor. Normal yolu izleyen modeller buraya
        hiç uğramaz — `after_tools` yalnızca bütçe dolduğunda yönlendirir.
        """
        response = llm.chat(state["messages"])
        return {
            "final_text": _strip_tool_markers(response.text or ""),
            "usage": state["usage"] + response.usage,
            # Marks this path as spent. Without it a model that returns nothing
            # even with the tools withheld would be routed straight back here by
            # `after_llm` and loop forever.
            "answered_toolless": True,
        }

    def citation_check(state: AgentState) -> AgentState:
        return {"citations": extract_citations(state["final_text"], state["tool_outputs"])}

    def repair(state: AgentState) -> AgentState:
        messages = [
            *state["messages"],
            {"role": "assistant", "content": state["final_text"]},
            {"role": "user", "content": CITATION_REPAIR},
        ]
        response = llm.chat(messages, TOOL_SCHEMAS)
        return {
            "messages": messages,
            "final_text": response.text or state["final_text"],
            "repaired": True,
            "usage": state["usage"] + response.usage,
        }

    def no_info(state: AgentState) -> AgentState:
        return {"final_text": NO_INFO_TEMPLATE, "citations": []}

    # ---- routing -------------------------------------------------------
    def after_gate(state: AgentState) -> str:
        return "llm_turn" if state["gate_passed"] else "refuse"

    def after_llm(state: AgentState) -> str:
        if state["pending_tool_calls"]:
            return "run_tools"
        if not state["tool_outputs"]:
            return "inject_context"
        # Tools ran but the model returned neither a call nor any text. Measured
        # on Phi-4-mini-instruct: with the tool schema in front of it the model
        # answers with an empty message every time (3/3), and writes a normal
        # answer the moment the schema is withheld. Retry once without tools
        # rather than discarding the context — `final_answer` guards itself
        # against a second pass, so a model that stays silent still reaches
        # no_info instead of looping.
        if not state["final_text"] and not state.get("answered_toolless"):
            return "final_answer"
        return "citation_check"

    def after_tools(state: AgentState) -> str:
        # The tool budget bounds the llm_turn <-> run_tools loop only. When it
        # runs out the model has never written an answer, so go and ask for one
        # with the tools withheld rather than discarding the gathered context.
        return "llm_turn" if state["turns"] < max_tool_turns else "final_answer"

    def after_citation_check(state: AgentState) -> str:
        if state["citations"]:
            return END
        # Repair only when an answer actually exists and was grounded in tool output;
        # a loop that exhausted its turn budget has no answer to repair.
        if state["tool_outputs"] and state["final_text"] and not state["repaired"]:
            return "repair"
        return "no_info"

    graph = StateGraph(AgentState)
    graph.add_node("score_gate", score_gate)
    graph.add_node("refuse", refuse)
    graph.add_node("llm_turn", llm_turn)
    graph.add_node("run_tools", run_tools)
    graph.add_node("inject_context", inject_context)
    graph.add_node("final_answer", final_answer)
    graph.add_node("citation_check", citation_check)
    graph.add_node("repair", repair)
    graph.add_node("no_info", no_info)

    graph.set_entry_point("score_gate")
    graph.add_conditional_edges("score_gate", after_gate, ["llm_turn", "refuse"])
    graph.add_edge("refuse", END)
    graph.add_conditional_edges(
        "llm_turn", after_llm, ["run_tools", "inject_context", "final_answer", "citation_check"]
    )
    graph.add_conditional_edges("run_tools", after_tools, ["llm_turn", "final_answer"])
    graph.add_edge("final_answer", "citation_check")
    graph.add_edge("inject_context", "llm_turn")
    graph.add_conditional_edges("citation_check", after_citation_check, ["repair", "no_info", END])
    graph.add_edge("repair", "citation_check")
    graph.add_edge("no_info", END)

    return graph.compile()
