from src.rag.agent import Agent, extract_citations
from src.rag.llm import LLMResponse, ToolCall
from src.rag.models import Chunk, SearchHit
from src.rag.prompts import NO_INFO_TEMPLATE, REFUSAL_TEMPLATE


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


def test_an_uncited_answer_gets_one_repair_attempt_before_being_discarded():
    # Measured: the same grounded prompt occasionally omits the [n] marker, and
    # the citation gate then throws away a correct answer. One explicit retry
    # recovers it instead of showing "bilgi bulamadım" for a known fact.
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "izin"})]),
            LLMResponse(text="İzin HRPortal üzerinden alınır."),
            LLMResponse(text="İzin HRPortal üzerinden alınır [1]."),
        ]
    )
    agent = Agent(_StubRetriever(confident=True), _StubToolBox(), llm)

    answer = agent.answer("Yıllık izin nasıl alınır?")

    assert answer.citations == ["sss.xlsx — Genel SSS, satır 4"]
    assert "HRPortal" in answer.text
    assert llm.call_count == 3


def test_answer_without_any_citation_is_replaced_by_the_no_info_template():
    llm = _ScriptedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Bence muhtemelen 20 gündür."),
            LLMResponse(text="Bence muhtemelen 20 gündür."),  # onarım turu da atıfsız
        ]
    )
    agent = Agent(_StubRetriever(confident=True), _StubToolBox(), llm)

    answer = agent.answer("Kaç gün izin var?")

    assert answer.text == NO_INFO_TEMPLATE
    assert answer.citations == []


def test_context_is_injected_when_the_model_skips_the_tool_call():
    # Measured on qwen2.5:7b-instruct: the model frequently answers from its own
    # knowledge without calling any tool, which would strand every answer on the
    # no-info template. The agent must retrieve for it instead of giving up.
    llm = _ScriptedLLM(
        [
            LLMResponse(text="Sanırım İK'ya sormalısınız."),
            LLMResponse(text="İzin HRPortal üzerinden alınır [1]."),
        ]
    )
    toolbox = _StubToolBox()
    agent = Agent(_StubRetriever(confident=True), toolbox, llm)

    answer = agent.answer("Yıllık izin nasıl alınır?")

    assert answer.citations == ["sss.xlsx — Genel SSS, satır 4"]
    assert toolbox.calls == [("search_documents", {"query": "Yıllık izin nasıl alınır?"})]
    assert answer.tool_trace[0]["injected"] is True


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
