from src.rag.graph import build_graph, initial_state
from src.rag.llm import LLMResponse, ToolCall
from src.rag.models import Chunk, SearchHit

# Stubs are duplicated from tests/test_agent.py on purpose: that file is the
# behaviour contract for the migration and must stay byte-identical, so it
# cannot be refactored to share fixtures.


class _StubRetriever:
    def __init__(self, confident: bool):
        self._confident = confident
        chunk = Chunk(
            "c1", "İzin HRPortal'dan alınır.", "izin", "sss.xlsx — Genel SSS, satır 4", {}
        )
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


def test_graph_refuses_before_any_llm_call():
    llm = _ScriptedLLM([])
    graph = build_graph(_StubRetriever(confident=False), _StubToolBox(), llm)

    state = graph.invoke(initial_state("Bugün hava nasıl?"))

    assert llm.call_count == 0
    assert state["citations"] == []
    assert state["gate_passed"] is False


def test_graph_exposes_its_node_names_for_visualisation():
    # Making the flow inspectable is one of the reasons for choosing a graph.
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), _ScriptedLLM([]))

    nodes = set(graph.get_graph().nodes)

    assert {"score_gate", "llm_turn", "run_tools", "citation_check", "repair"} <= nodes


def test_repair_node_runs_at_most_once():
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="atıfsız"),
            LLMResponse(text="yine atıfsız"),
        ]
    )
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), llm)

    state = graph.invoke(initial_state("kaç gün izin?"))

    assert state["repaired"] is True
    assert llm.call_count == 3  # one tool turn + one answer + one repair


def test_graph_accumulates_token_usage_across_turns():
    from src.rag.llm import TokenUsage

    llm = _ScriptedLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall("1", "search_documents", {"query": "x"})],
                usage=TokenUsage(100, 10),
            ),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(400, 30)),
        ]
    )
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), llm)

    state = graph.invoke(initial_state("soru"))

    assert state["usage"] == TokenUsage(500, 40)
