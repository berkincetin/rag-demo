"""JSON shapes the Next.js front-end consumes.

`src/rag/api.py` holds the FastAPI app itself (routing + wiring, excluded from
coverage like the UI files). Everything that decides *what the JSON says* lives
in `serialize.py` and is tested here — the front-end contract is exactly these
functions.
"""

from src.rag.evaluation import EvalResult
from src.rag.metrics import ModelSummary, RunRecord
from src.rag.models import Answer, TokenUsage
from src.rag.serialize import (
    answer_payload,
    model_payload,
    run_payload,
    summary_payload,
)


def test_answer_payload_carries_text_citations_and_trace():
    answer = Answer(
        text="Yakıt limiti 1.500 TL/ay'dır [1].",
        citations=["arac_kullanim_proseduru.docx — 3. ARAC TAHSIS POLITIKASI"],
        tool_trace=[
            {
                "name": "search_documents",
                "arguments": {"query": "yakıt"},
                "chars": 90,
                "injected": False,
            }
        ],
        usage=TokenUsage(input_tokens=2900, output_tokens=100),
        latency_ms=4321,
    )

    payload = answer_payload(answer, cost_usd=0.0025)

    assert payload["text"].startswith("Yakıt limiti")
    assert payload["citations"] == ["arac_kullanim_proseduru.docx — 3. ARAC TAHSIS POLITIKASI"]
    assert payload["latencyMs"] == 4321
    assert payload["inputTokens"] == 2900
    assert payload["costUsd"] == 0.0025
    assert payload["toolTrace"][0]["name"] == "search_documents"
    # The front-end renders a badge for agent-initiated retrieval.
    assert payload["toolTrace"][0]["injected"] is False


def test_answer_payload_keeps_unmeasured_values_null():
    # Ollama often returns no token counts. JSON null must survive as null so
    # the UI can print "ölçülmedi" instead of a fabricated 0.
    payload = answer_payload(Answer(text="x", usage=TokenUsage()), cost_usd=None)

    assert payload["inputTokens"] is None
    assert payload["outputTokens"] is None
    assert payload["costUsd"] is None


def test_answer_payload_flags_a_refusal():
    # No citations means the gate refused or the model had no grounded answer;
    # the UI shows a distinct state rather than an empty source list.
    payload = answer_payload(Answer(text="Bu soru kapsam dışında.", citations=[]), cost_usd=None)

    assert payload["grounded"] is False


def test_answer_payload_marks_a_cited_answer_grounded():
    payload = answer_payload(Answer(text="a [1]", citations=["f.docx — B1"]), cost_usd=None)

    assert payload["grounded"] is True


def test_model_payload_exposes_provider_and_locality():
    from src.rag.catalog import get_model

    payload = model_payload(get_model("claude-opus-5"))

    assert payload["id"] == "claude-opus-5"
    assert payload["provider"] == "anthropic"
    assert payload["local"] is False
    assert payload["label"] == "Claude Opus 5"


def test_run_payload_uses_camel_case_keys():
    run = RunRecord(
        model_id="qwen2.5:7b",
        provider="ollama",
        question="soru",
        latency_ms=1200,
        input_tokens=None,
        output_tokens=None,
        cost_usd=None,
        citation_count=2,
        gate_passed=True,
        tool_calls=1,
        repaired=False,
        ts="2026-08-06T12:00:00",
    )

    payload = run_payload(run)

    assert payload["modelId"] == "qwen2.5:7b"
    assert payload["latencyMs"] == 1200
    assert payload["citationCount"] == 2
    assert payload["gatePassed"] is True
    assert payload["inputTokens"] is None


def test_summary_payload_reports_partial_pricing():
    # 3 of 5 runs priced: the UI must be able to say so rather than implying
    # the cost covers every run.
    summary = ModelSummary(
        model_id="gpt-4o-mini",
        provider="openai",
        runs=5,
        priced_runs=3,
        avg_latency_ms=900.0,
        total_cost_usd=0.02,
        avg_citations=1.5,
        gate_pass_rate=0.8,
    )

    payload = summary_payload(summary)

    assert payload["runs"] == 5
    assert payload["pricedRuns"] == 3
    assert payload["totalCostUsd"] == 0.02


def test_summary_payload_keeps_unpriced_cost_null():
    summary = ModelSummary(
        model_id="qwen2.5:7b",
        provider="ollama",
        runs=2,
        priced_runs=0,
        avg_latency_ms=50000.0,
        total_cost_usd=None,
        avg_citations=1.0,
        gate_pass_rate=1.0,
    )

    assert summary_payload(summary)["totalCostUsd"] is None


def test_eval_payload_orders_by_citation_rate():
    from src.rag.serialize import evaluation_payload

    weak = EvalResult("m-weak", 13, 0.4, 0.3, 0.3, 1.0, 1000.0, None, 13)
    strong = EvalResult("m-strong", 13, 0.9, 0.8, 0.8, 1.0, 5000.0, 0.1, 0)

    rows = evaluation_payload([weak, strong])

    assert [row["modelId"] for row in rows] == ["m-strong", "m-weak"]
    assert rows[0]["citationRate"] == 0.9
