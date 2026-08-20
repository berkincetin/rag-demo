"""The question-answering agent: a tool-calling loop with three safety layers.

Layer 1 refuses off-topic questions on retrieval score alone, before any LLM
call. Layer 2 is the grounded system prompt. Layer 3 rejects any answer that
cites nothing. See docs/planlama/02-karar-kaydi.md ADR-008.
"""

import re
import time

from src.rag.models import Answer

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
    """Facade over the LangGraph state machine in `graph.py`.

    The public surface is deliberately unchanged from the hand-written loop it
    replaced, so the CLI, Streamlit, the demo notebook, and the smoke test do
    not need to know the internals moved.
    """

    def __init__(self, retriever, toolbox, llm, max_tool_turns: int = 3, metrics=None) -> None:
        from src.rag.graph import build_graph

        self.retriever = retriever
        self.toolbox = toolbox
        self.llm = llm
        self.max_tool_turns = max_tool_turns
        self.metrics = metrics
        self._graph = build_graph(retriever, toolbox, llm, max_tool_turns)

    def answer(self, question: str, memory=None, user_name: str | None = None) -> Answer:
        """Answer a question, or refuse when the knowledge base cannot support one."""
        from src.rag.graph import initial_state
        from src.rag.resources import NullMonitor, ResourceMonitor

        # Sampling costs a thread and one Ollama call; skip it when nothing
        # will consume the numbers.
        is_local = _provider_of(getattr(self.llm, "model", "")) == "ollama"
        monitor = ResourceMonitor(read_gpu=is_local) if self.metrics is not None else NullMonitor()

        started = time.perf_counter()
        with monitor:
            state = self._graph.invoke(initial_state(question, memory=memory, user_name=user_name))
        latency_ms = int((time.perf_counter() - started) * 1000)
        self._last_resources = monitor
        # Read before the turn is appended, so the first question is turn 0.
        turn_index = len(memory) if memory is not None else 0

        answer = Answer(
            text=state["final_text"],
            citations=state["citations"],
            tool_trace=state["trace"],
            usage=state["usage"],
            latency_ms=latency_ms,
        )
        self._record(question, state, answer, turn_index)
        if memory is not None and answer.citations:
            # Only grounded answers enter the history; remembering a refusal
            # would pollute the next question's retrieval query.
            memory.add(question, answer.text)
        return answer

    def _record(self, question: str, state: dict, answer: Answer, turn_index: int = 0) -> None:
        if self.metrics is None:
            return

        from src.rag.metrics import RunRecord
        from src.rag.pricing import estimate_cost

        model_id = getattr(self.llm, "model", "bilinmiyor")
        self.metrics.record(
            RunRecord(
                model_id=model_id,
                provider=_provider_of(model_id),
                question=question,
                latency_ms=answer.latency_ms,
                input_tokens=answer.usage.input_tokens,
                output_tokens=answer.usage.output_tokens,
                cost_usd=estimate_cost(
                    model_id, answer.usage.input_tokens, answer.usage.output_tokens
                ),
                citation_count=len(answer.citations),
                gate_passed=state["gate_passed"],
                tool_calls=len(state["trace"]),
                repaired=state["repaired"],
                peak_cpu_percent=self._last_resources.peak_cpu_percent,
                peak_ram_mb=self._last_resources.peak_ram_mb,
                gpu_vram_mb=self._last_resources.gpu_vram_mb,
                turn_index=turn_index,
            )
        )


def _provider_of(model_id: str) -> str:
    from src.rag.catalog import get_model

    model = get_model(model_id)
    return model.provider if model else "ollama"
