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


def test_history_is_placed_before_the_current_question():
    from src.rag.memory import ConversationMemory

    memory = ConversationMemory()
    memory.add("Önceki soru", "Önceki cevap")
    seen = {}

    class _Capturing(_ScriptedLLM):
        def chat(self, messages, tools=None):
            seen.setdefault("messages", list(messages))  # first call only
            return super().chat(messages, tools)

    llm = _Capturing([LLMResponse(text="ilk"), LLMResponse(text="Cevap [1].")])
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), llm)
    graph.invoke(initial_state("Yeni soru", memory=memory))

    roles = [m["role"] for m in seen["messages"]]
    contents = [m["content"] for m in seen["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert contents[1] == "Önceki soru"
    assert contents[3] == "Yeni soru"


def test_the_gate_searches_with_the_enriched_query():
    from src.rag.memory import ConversationMemory

    memory = ConversationMemory()
    memory.add("Direktör yakıt limiti nedir?", "1.500 TL/ay")

    class _RecordingRetriever(_StubRetriever):
        def __init__(self):
            super().__init__(confident=True)
            self.queries = []

        def search(self, query, top_k=5, source_filter=None):
            self.queries.append(query)
            return self._hits

    retriever = _RecordingRetriever()
    graph = build_graph(
        retriever,
        _StubToolBox(),
        _ScriptedLLM([LLMResponse(text="ilk"), LLMResponse(text="Cevap [1].")]),
    )
    graph.invoke(initial_state("peki ya müdür?", memory=memory))

    assert "yakıt limiti" in retriever.queries[0]


def test_the_injected_search_is_enriched_too():
    # When the model skips the tool call we retrieve on its behalf. That search
    # needs the same widening as the gate, or a follow-up question would be
    # answered from documents chosen by "peki ya müdür?" alone.
    from src.rag.memory import ConversationMemory

    memory = ConversationMemory()
    memory.add("Direktör yakıt limiti nedir?", "1.500 TL/ay")
    calls = []

    class _RecordingToolBox(_StubToolBox):
        def run(self, name, arguments):
            calls.append(arguments)
            return super().run(name, arguments)

    graph = build_graph(
        _StubRetriever(confident=True),
        _RecordingToolBox(),
        # No tool call on the first turn, so the injection path runs.
        _ScriptedLLM([LLMResponse(text="atıfsız"), LLMResponse(text="Cevap [1].")]),
    )
    graph.invoke(initial_state("peki ya müdür?", memory=memory))

    assert "yakıt limiti" in calls[0]["query"]


def test_the_name_rides_on_the_tool_result_as_well():
    # Measured: qwen2.5-7b never used the name when it appeared only in the
    # system prompt (two grounded answers, neither greeted). Task 12 found the
    # same for the citation rule and solved it the same way.
    seen = []

    class _Capturing(_ScriptedLLM):
        def chat(self, messages, tools=None):
            seen.append(list(messages))
            return super().chat(messages, tools)

    llm = _Capturing(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1]."),
        ]
    )
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), llm)
    graph.invoke(initial_state("soru", user_name="Berkin"))

    tool_result = seen[1][-1]["content"]
    assert "Berkin" in tool_result


def test_no_name_leaves_the_tool_result_unchanged():
    seen = []

    class _Capturing(_ScriptedLLM):
        def chat(self, messages, tools=None):
            seen.append(list(messages))
            return super().chat(messages, tools)

    llm = _Capturing(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1]."),
        ]
    )
    graph = build_graph(_StubRetriever(confident=True), _StubToolBox(), llm)
    graph.invoke(initial_state("soru"))

    from src.rag.prompts import CITATION_REMINDER

    assert seen[1][-1]["content"].endswith(CITATION_REMINDER)


def test_without_a_user_name_the_system_prompt_is_untouched():
    # Measured in Task 12: every extra sentence in the system prompt can
    # suppress the tool call, so the default prompt must stay byte-identical.
    from src.rag.prompts import SYSTEM_PROMPT

    seen = {}

    class _Capturing(_ScriptedLLM):
        def chat(self, messages, tools=None):
            seen["system"] = messages[0]["content"]
            return super().chat(messages, tools)

    graph = build_graph(
        _StubRetriever(confident=True),
        _StubToolBox(),
        _Capturing([LLMResponse(text="x"), LLMResponse(text="x [1].")]),
    )
    graph.invoke(initial_state("soru"))

    assert seen["system"] == SYSTEM_PROMPT


def test_a_user_name_is_appended_as_a_single_sentence():
    from src.rag.prompts import SYSTEM_PROMPT

    seen = {}

    class _Capturing(_ScriptedLLM):
        def chat(self, messages, tools=None):
            seen["system"] = messages[0]["content"]
            return super().chat(messages, tools)

    graph = build_graph(
        _StubRetriever(confident=True),
        _StubToolBox(),
        _Capturing([LLMResponse(text="x"), LLMResponse(text="x [1].")]),
    )
    graph.invoke(initial_state("soru", user_name="Berkin"))

    assert seen["system"].startswith(SYSTEM_PROMPT)
    assert "Berkin" in seen["system"]
    # One added line only — the prompt must not grow beyond that.
    assert len(seen["system"].splitlines()) == len(SYSTEM_PROMPT.splitlines()) + 2


def test_a_blank_user_name_changes_nothing():
    from src.rag.prompts import SYSTEM_PROMPT

    seen = {}

    class _Capturing(_ScriptedLLM):
        def chat(self, messages, tools=None):
            seen["system"] = messages[0]["content"]
            return super().chat(messages, tools)

    graph = build_graph(
        _StubRetriever(confident=True),
        _StubToolBox(),
        _Capturing([LLMResponse(text="x"), LLMResponse(text="x [1].")]),
    )
    graph.invoke(initial_state("soru", user_name="   "))

    assert seen["system"] == SYSTEM_PROMPT


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
