"""Agent control flow with a mocked LLM. Output text is never asserted on."""

from azure.rag.agent import Agent, extract_citations
from azure.rag.llm_client import LLMResponse, ToolCall
from azure.rag.models import Chunk, SearchHit, TokenUsage


class FakeLLM:
    """Returns queued responses and records the messages it received."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools=None) -> LLMResponse:
        self.calls.append(messages)
        return self.responses.pop(0)


class FakeRetriever:
    def __init__(self, confident: bool, hits=None) -> None:
        self.confident = confident
        self.hits = hits or []

    def search(self, query, top_k=5, source_filter=None):
        return self.hits

    def is_confident(self, hits) -> bool:
        return self.confident


class FakeToolBox:
    def __init__(self, output: str = "[1] belge.docx — Bölüm 1\nİçerik") -> None:
        self.output = output
        self.calls: list[tuple[str, dict]] = []

    def run(self, name, arguments) -> str:
        self.calls.append((name, arguments))
        return self.output


def _hit(cosine: float = 0.9, bm25: float = 9.0) -> SearchHit:
    chunk = Chunk(
        chunk_id="c1",
        text="Aylık yakıt limiti 1.500 TL/ay olarak belirlenmiştir.",
        search_text="aylik yakit limiti",
        citation_label="arac.docx — Bölüm 3",
        metadata={"source_file": "arac.docx"},
    )
    return SearchHit(chunk=chunk, score=1.0, cosine=cosine, bm25=bm25)


def test_refuses_when_retrieval_is_not_confident():
    """Off-topic questions must not reach the LLM as answerable."""
    llm = FakeLLM([LLMResponse(text="Bilmiyorum.")])
    agent = Agent(FakeRetriever(confident=False), FakeToolBox(), llm)

    answer = agent.answer("Bugün hava nasıl?")

    assert answer.citations == []


def test_runs_a_requested_tool_and_feeds_the_result_back():
    llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall(id="1", name="search_documents", arguments={"query": "yakıt"})]
            ),
            LLMResponse(text="Aylık yakıt limiti 1.500 TL/ay'dır [1]."),
        ]
    )
    toolbox = FakeToolBox()
    agent = Agent(FakeRetriever(confident=True, hits=[_hit()]), toolbox, llm)

    answer = agent.answer("Yakıt limiti nedir?")

    assert toolbox.calls[0][0] == "search_documents"
    assert answer.citations


def test_stops_at_max_tool_turns():
    """A model that only ever asks for tools must not loop forever."""
    always_tool = [
        LLMResponse(
            tool_calls=[ToolCall(id=str(n), name="search_documents", arguments={"query": "x"})]
        )
        for n in range(10)
    ]
    llm = FakeLLM(always_tool)
    agent = Agent(
        FakeRetriever(confident=True, hits=[_hit()]), FakeToolBox(), llm, max_tool_turns=2
    )

    agent.answer("soru")

    assert len(llm.calls) <= 3


def test_accumulates_token_usage_across_turns():
    llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall(id="1", name="search_documents", arguments={"query": "x"})],
                usage=TokenUsage(100, 10),
            ),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(200, 20)),
        ]
    )
    agent = Agent(FakeRetriever(confident=True, hits=[_hit()]), FakeToolBox(), llm)

    answer = agent.answer("soru")

    assert answer.usage.input_tokens == 300
    assert answer.usage.output_tokens == 30


def test_extract_citations_maps_markers_to_labels():
    outputs = ["[1] arac.docx — Bölüm 3\nİçerik"]

    citations = extract_citations("Limit 1.500 TL/ay [1].", outputs)

    assert citations == ["arac.docx — Bölüm 3"]


def test_extract_citations_ignores_unmatched_markers():
    citations = extract_citations("Cevap [7].", ["[1] arac.docx — Bölüm 3"])

    assert citations == []
