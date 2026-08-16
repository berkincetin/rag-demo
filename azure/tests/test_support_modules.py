"""Support modules: catalog, pricing, session state, metrics, serialization."""

from azure.rag.catalog import AZURE_MODEL_ID, get_model, list_models
from azure.rag.metrics import MetricsStore, RunRecord
from azure.rag.models import Answer, TokenUsage
from azure.rag.pricing import estimate_cost
from azure.rag.serialize import answer_payload, model_payload, run_payload, summary_payload
from azure.rag.ui_state import (
    add_to_transcript,
    clear_chat,
    get_transcript,
    get_user_name,
    set_user_name,
)

# --- catalog -----------------------------------------------------------------


def test_catalog_exposes_only_the_azure_model():
    models = list_models()

    assert [model.id for model in models] == [AZURE_MODEL_ID]
    assert models[0].provider == "azure_openai"
    assert models[0].local is False


def test_get_model_returns_none_for_a_foreign_model():
    assert get_model("gpt-4o-mini") is None
    assert get_model(AZURE_MODEL_ID) is not None


# --- pricing -----------------------------------------------------------------


def test_estimate_cost_is_none_when_price_is_unverified():
    """Azure pricing is region-dependent and unverified, so it stays null."""
    assert estimate_cost(AZURE_MODEL_ID, 1000, 100) is None


def test_estimate_cost_is_none_for_unreported_tokens():
    assert estimate_cost(AZURE_MODEL_ID, None, None) is None
    assert estimate_cost(AZURE_MODEL_ID, 100, None) is None


def test_unknown_model_is_not_reported_as_free():
    """The local deployment returned 0.0 here to mean 'local Ollama, no cost'.

    Every model here is a paid Azure deployment, so 0.0 would report a paid
    model as free — the lie the pricing module exists to prevent.
    """
    assert estimate_cost("some-other-model", 1000, 100) is None


# --- session state -----------------------------------------------------------


def test_transcript_accumulates_and_clears():
    session: dict = {}

    add_to_transcript(session, "soru 1", "cevap 1")
    add_to_transcript(session, "soru 2", "cevap 2")

    assert get_transcript(session) == [("soru 1", "cevap 1"), ("soru 2", "cevap 2")]

    clear_chat(session)

    assert get_transcript(session) == []


def test_user_name_survives_a_chat_clear():
    """The name is not a conversation turn, so clearing the chat keeps it."""
    session: dict = {}
    set_user_name(session, "  Berkin  ")

    clear_chat(session)

    assert get_user_name(session) == "Berkin"


def test_user_name_defaults_to_empty():
    assert get_user_name({}) == ""


# --- metrics -----------------------------------------------------------------


def _record(**overrides) -> RunRecord:
    fields = {
        "model_id": "gpt-4.1-mini",
        "provider": "azure_openai",
        "question": "soru",
        "latency_ms": 1200,
        "input_tokens": 1483,
        "output_tokens": 115,
        "cost_usd": None,
        "citation_count": 1,
        "gate_passed": True,
        "tool_calls": 1,
        "repaired": False,
    }
    fields.update(overrides)
    return RunRecord(**fields)


def test_metrics_round_trip(tmp_path):
    store = MetricsStore(tmp_path / "m.db")

    store.record(_record())
    runs = store.recent()

    assert len(runs) == 1
    assert runs[0].model_id == "gpt-4.1-mini"
    assert runs[0].input_tokens == 1483
    assert runs[0].gate_passed is True


def test_metrics_accepts_exactly_the_fields_the_agent_builds(tmp_path):
    """agent.py builds a RunRecord with these 12 fields and no resource columns.

    If the two ever disagree, every answer crashes at the recording step, so
    this asserts the contract rather than trusting it.
    """
    store = MetricsStore(tmp_path / "m.db")

    store.record(
        RunRecord(
            model_id="gpt-4.1-mini",
            provider="azure_openai",
            question="soru",
            latency_ms=1,
            input_tokens=1,
            output_tokens=1,
            cost_usd=None,
            citation_count=0,
            gate_passed=False,
            tool_calls=0,
            repaired=False,
            turn_index=0,
        )
    )

    assert len(store.recent()) == 1


def test_unpriced_runs_are_counted_separately(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_record(cost_usd=None))
    store.record(_record(cost_usd=None))

    summary = list(store.summary_by_model())[0]

    assert summary.runs == 2
    assert summary.priced_runs == 0
    assert summary.total_cost_usd is None


def test_clear_empties_the_store(tmp_path):
    store = MetricsStore(tmp_path / "m.db")
    store.record(_record())

    store.clear()

    assert store.recent() == []


# --- serialization -----------------------------------------------------------


def test_answer_payload_uses_camel_case_keys():
    """The TypeScript client consumes these names verbatim."""
    answer = Answer(
        text="cevap",
        citations=["arac.docx — Bolum 3"],
        usage=TokenUsage(10, 5),
        latency_ms=42,
    )

    payload = answer_payload(answer, cost_usd=None)

    assert payload["text"] == "cevap"
    assert payload["citations"] == ["arac.docx — Bolum 3"]
    assert payload["grounded"] is True
    assert payload["latencyMs"] == 42
    assert payload["inputTokens"] == 10
    assert payload["outputTokens"] == 5
    assert payload["costUsd"] is None


def test_answer_payload_marks_a_refusal_as_ungrounded():
    payload = answer_payload(Answer(text="Bilmiyorum."), cost_usd=None)

    assert payload["grounded"] is False
    assert payload["citations"] == []


def test_payloads_carry_no_resource_keys(tmp_path):
    """Resource measurement is dropped in this deployment; the wire must agree."""
    store = MetricsStore(tmp_path / "m.db")
    store.record(_record())

    run = run_payload(store.recent()[0])
    summary = summary_payload(list(store.summary_by_model())[0])

    for key in ("peakCpuPercent", "peakRamMb", "gpuVramMb"):
        assert key not in run
        assert key not in summary


def test_model_payload_shape():
    payload = model_payload(list_models()[0])

    assert payload["id"] == AZURE_MODEL_ID
    assert payload["provider"] == "azure_openai"
    assert payload["local"] is False
    assert payload["contextTokens"] == 128_000
