from src.rag.agent import Agent
from src.rag.llm import LLMResponse, TokenUsage, ToolCall
from src.rag.metrics import MetricsStore
from tests.test_graph import _ScriptedLLM, _StubRetriever, _StubToolBox


class _NamedLLM(_ScriptedLLM):
    """A scripted LLM that also reports a model id, as real clients do."""

    def __init__(self, responses, model="claude-opus-5"):
        super().__init__(responses)
        self.model = model


def test_a_successful_answer_is_recorded(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _NamedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "izin"})]),
            LLMResponse(text="İzin HRPortal'dan alınır [1].", usage=TokenUsage(500, 40)),
        ]
    )
    agent = Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store)

    agent.answer("Yıllık izin nasıl alınır?")

    row = store.recent()[0]
    assert row.citation_count == 1
    assert row.gate_passed is True
    assert row.tool_calls == 1


def test_a_refusal_is_recorded_too(tmp_path):
    # Refusals must be measured, otherwise gate accuracy cannot be reported.
    store = MetricsStore(tmp_path / "m.db")
    agent = Agent(_StubRetriever(confident=False), _StubToolBox(), _NamedLLM([]), metrics=store)

    agent.answer("Bugün hava nasıl?")

    row = store.recent()[0]
    assert row.gate_passed is False
    assert row.citation_count == 0
    assert row.tool_calls == 0


def test_token_usage_is_summed_across_turns(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _NamedLLM(
        [
            LLMResponse(
                tool_calls=[ToolCall("1", "search_documents", {"query": "x"})],
                usage=TokenUsage(100, 10),
            ),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(400, 30)),
        ]
    )
    Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store).answer("s")

    row = store.recent()[0]
    assert row.input_tokens == 500
    assert row.output_tokens == 40


def test_unmeasured_usage_stays_null(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _NamedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1]."),
        ]
    )
    Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store).answer("s")

    assert store.recent()[0].input_tokens is None


def test_a_priced_model_gets_a_cost(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _NamedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(1_000_000, 0)),
        ],
        model="claude-opus-5",
    )
    Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store).answer("s")

    assert store.recent()[0].cost_usd == 5.0


def test_an_unpriced_model_records_a_null_cost(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    llm = _NamedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(1000, 100)),
        ],
        model="gpt-4o-mini",
    )
    Agent(_StubRetriever(confident=True), _StubToolBox(), llm, metrics=store).answer("s")

    assert store.recent()[0].cost_usd is None


def test_metrics_are_optional():
    # metrics=None must keep the agent working exactly as before.
    agent = Agent(_StubRetriever(confident=False), _StubToolBox(), _NamedLLM([]))

    assert agent.answer("Bugün hava nasıl?").text


def test_answer_exposes_latency_and_usage():
    llm = _NamedLLM(
        [
            LLMResponse(tool_calls=[ToolCall("1", "search_documents", {"query": "x"})]),
            LLMResponse(text="Cevap [1].", usage=TokenUsage(10, 5)),
        ]
    )

    answer = Agent(_StubRetriever(confident=True), _StubToolBox(), llm).answer("s")

    assert answer.latency_ms >= 0
    assert answer.usage.output_tokens == 5
