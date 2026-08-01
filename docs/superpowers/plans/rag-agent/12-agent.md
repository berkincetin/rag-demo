# Task 12: Agent loop with the three-layer safety net

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 11](11-llm-providers.md)
**Next:** [Task 13](13-frontends.md)

---

**Files:**
- Create: `src/rag/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `Retriever`, `ToolBox`, `LLMClient`, `LLMResponse`, `ToolCall`, `Answer`, `SYSTEM_PROMPT`, `REFUSAL_TEMPLATE`, `NO_INFO_TEMPLATE`
- Produces: class `Agent(retriever, toolbox, llm, max_tool_turns=3)` with method `answer(question: str) -> Answer`; helper `extract_citations(text: str, tool_outputs: list[str]) -> list[str]`

The three layers (ADR-008): a retrieval-score gate that refuses before any LLM call, a grounded system prompt, and a citation post-check that replaces an uncited answer with `NO_INFO_TEMPLATE`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent.py
from src.rag.agent import Agent, extract_citations
from src.rag.llm import LLMResponse, ToolCall
from src.rag.models import Chunk, SearchHit
from src.rag.prompts import NO_INFO_TEMPLATE, REFUSAL_TEMPLATE


class _StubRetriever:
    def __init__(self, confident: bool):
        self._confident = confident
        chunk = Chunk("c1", "İzin HRPortal'dan alınır.", "izin", "sss.xlsx — Genel SSS, satır 4", {})
        self.index = type("Index", (), {"chunks": [chunk]})()
        self._hits = [SearchHit(chunk=chunk, score=0.5, cosine=0.9, bm25=9.0)]

    def search(self, query, top_k=5, source_filter=None):
        return self._hits

    def is_confident(self, hits):
        return self._confident


class _StubToolBox:
    def __init__(self):
        self.calls = []

    def run(self, name, arguments):
        self.calls.append((name, arguments))
        return "[1] sss.xlsx — Genel SSS, satır 4\nİzin HRPortal'dan alınır."


class _ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self.call_count = 0

    def chat(self, messages, tools=None):
        self.call_count += 1
        return self._responses.pop(0)


def test_off_topic_question_is_refused_without_calling_the_llm():
    llm = _ScriptedLLM([])
    agent = Agent(_StubRetriever(confident=False), _StubToolBox(), llm)

    answer = agent.answer("Bugün hava nasıl?")

    assert answer.text == REFUSAL_TEMPLATE
    assert llm.call_count == 0
    assert answer.tool_trace == []


def test_tool_call_result_is_fed_back_and_the_final_answer_is_returned():
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "izin"})]),
            LLMResponse(text="İzin HRPortal üzerinden alınır [1].\n\nKaynaklar:\n[1] sss.xlsx"),
        ]
    )
    toolbox = _StubToolBox()
    agent = Agent(_StubRetriever(confident=True), toolbox, llm)

    answer = agent.answer("Yıllık izin nasıl alınır?")

    assert "HRPortal" in answer.text
    assert toolbox.calls == [("search_documents", {"query": "izin"})]
    assert len(answer.tool_trace) == 1
    assert answer.tool_trace[0]["name"] == "search_documents"


def test_answer_without_any_citation_is_replaced_by_the_no_info_template():
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Bence muhtemelen 20 gündür."),
        ]
    )
    agent = Agent(_StubRetriever(confident=True), _StubToolBox(), llm)

    answer = agent.answer("Kaç gün izin var?")

    assert answer.text == NO_INFO_TEMPLATE
    assert answer.citations == []


def test_tool_loop_stops_at_the_configured_turn_limit():
    responses = [
        LLMResponse(tool_calls=[ToolCall(str(i), "search_documents", {"query": "x"})])
        for i in range(5)
    ]
    llm = _ScriptedLLM(responses)
    agent = Agent(_StubRetriever(confident=True), _StubToolBox(), llm, max_tool_turns=3)

    agent.answer("döngü testi")

    assert llm.call_count == 3


def test_extract_citations_returns_labels_referenced_by_number():
    output = "[1] sss.xlsx — Genel SSS, satır 4\nmetin\n\n[2] a.pdf — Bölüm 1, s.1\nmetin"

    citations = extract_citations("Cevap [1] ve [2].", [output])

    assert citations == ["sss.xlsx — Genel SSS, satır 4", "a.pdf — Bölüm 1, s.1"]


def test_extract_citations_ignores_numbers_with_no_matching_source():
    citations = extract_citations("Cevap [7].", ["[1] a.pdf — Bölüm 1, s.1\nmetin"])

    assert citations == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.agent'`

- [ ] **Step 3: Write minimal `src/rag/agent.py`**

```python
"""The question-answering agent: a tool-calling loop with three safety layers.

Layer 1 refuses off-topic questions on retrieval score alone, before any LLM
call. Layer 2 is the grounded system prompt. Layer 3 rejects any answer that
cites nothing. See docs/02-karar-kaydi.md ADR-008.
"""

import re
from typing import Any

from src.rag.models import Answer
from src.rag.prompts import NO_INFO_TEMPLATE, REFUSAL_TEMPLATE, SYSTEM_PROMPT
from src.rag.tools import TOOL_SCHEMAS

_CITATION_MARKER = re.compile(r"\[(\d+)\]")
_SOURCE_LINE = re.compile(r"^\[(\d+)\]\s+(.+)$", re.MULTILINE)


def extract_citations(text: str, tool_outputs: list[str]) -> list[str]:
    """Map [n] markers in the answer back to the citation labels the tools returned."""
    labels: dict[str, str] = {}
    for output in tool_outputs:
        for number, label in _SOURCE_LINE.findall(output):
            labels.setdefault(number, label.strip())
    seen: list[str] = []
    for number in _CITATION_MARKER.findall(text):
        label = labels.get(number)
        if label and label not in seen:
            seen.append(label)
    return seen


class Agent:
    def __init__(self, retriever, toolbox, llm, max_tool_turns: int = 3) -> None:
        self.retriever = retriever
        self.toolbox = toolbox
        self.llm = llm
        self.max_tool_turns = max_tool_turns

    def answer(self, question: str) -> Answer:
        """Answer a question, or refuse when the knowledge base cannot support one."""
        hits = self.retriever.search(question, top_k=5)
        if not self.retriever.is_confident(hits):
            return Answer(text=REFUSAL_TEMPLATE)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        trace: list[dict[str, Any]] = []
        outputs: list[str] = []
        final_text = ""

        for _ in range(self.max_tool_turns):
            response = self.llm.chat(messages, TOOL_SCHEMAS)
            if not response.tool_calls:
                final_text = response.text or ""
                break
            for call in response.tool_calls:
                output = self.toolbox.run(call.name, call.arguments)
                outputs.append(output)
                trace.append(
                    {"name": call.name, "arguments": call.arguments, "chars": len(output)}
                )
                messages.append({"role": "assistant", "content": f"[tool: {call.name}]"})
                messages.append({"role": "user", "content": output})

        citations = extract_citations(final_text, outputs)
        if not citations:
            return Answer(text=NO_INFO_TEMPLATE, tool_trace=trace)
        return Answer(text=final_text, citations=citations, tool_trace=trace)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_agent.py -v --no-cov`
Expected: PASS (6 passed)

- [ ] **Step 5: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/agent.py tests/test_agent.py
git commit -m "feat(agent): add tool-calling loop with refusal and citation checks"
```
