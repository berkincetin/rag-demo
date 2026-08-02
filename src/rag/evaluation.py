"""Deterministic quality scoring for comparing models.

No LLM-as-judge: the score must be reproducible and free. What is measured is
behaviour the system controls — did it cite, did it cite the right document,
did the expected fact survive, and did the gate refuse what it should refuse.
Answer wording is never scored, because wording is not deterministic.
"""

import json
from dataclasses import dataclass
from pathlib import Path

_EVAL_SET_PATH = Path(__file__).resolve().parents[2] / "config" / "eval_set.json"


@dataclass(frozen=True)
class EvalCase:
    question: str
    expect_answer: bool
    expect_source: str | None = None
    expect_evidence: str | None = None


@dataclass
class EvalResult:
    model_id: str
    cases: int
    citation_rate: float | None
    source_accuracy: float | None
    evidence_hit: float | None
    refusal_accuracy: float | None
    avg_latency_ms: float | None
    total_cost_usd: float | None
    unpriced_runs: int


def load_eval_set(path: Path | None = None) -> list[EvalCase]:
    """Read the shipped question set."""
    raw = json.loads((path or _EVAL_SET_PATH).read_text(encoding="utf-8"))
    return [
        EvalCase(
            question=entry["question"],
            expect_answer=entry["expect_answer"],
            expect_source=entry.get("expect_source"),
            expect_evidence=entry.get("expect_evidence"),
        )
        for entry in raw
    ]


def _rate(hits: int, total: int) -> float | None:
    """None when there is nothing to measure — never 0, which means 'all failed'."""
    return hits / total if total else None


def evaluate(agent, cases: list[EvalCase], on_progress=None) -> EvalResult:
    """Run every case through the agent and score the outcomes."""
    cited = source_ok = evidence_ok = refused_ok = 0
    answerable = evidence_cases = off_topic = 0
    latencies: list[int] = []
    costs: list[float] = []
    unpriced = 0

    for index, case in enumerate(cases):
        answer = agent.answer(case.question)
        if on_progress is not None:
            on_progress(index + 1, len(cases), case.question)

        latencies.append(answer.latency_ms)
        cost = _cost_of(agent, answer)
        if cost is None:
            unpriced += 1
        else:
            costs.append(cost)

        if case.expect_answer:
            answerable += 1
            if answer.citations:
                cited += 1
                if case.expect_source and any(
                    case.expect_source in label for label in answer.citations
                ):
                    source_ok += 1
            if case.expect_evidence:
                evidence_cases += 1
                if case.expect_evidence in answer.text:
                    evidence_ok += 1
        else:
            off_topic += 1
            if not answer.citations:
                refused_ok += 1

    return EvalResult(
        model_id=getattr(getattr(agent, "llm", None), "model", "bilinmiyor"),
        cases=len(cases),
        citation_rate=_rate(cited, answerable),
        source_accuracy=_rate(source_ok, answerable),
        evidence_hit=_rate(evidence_ok, evidence_cases),
        refusal_accuracy=_rate(refused_ok, off_topic),
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
        total_cost_usd=sum(costs) if costs else None,
        unpriced_runs=unpriced,
    )


def _cost_of(agent, answer) -> float | None:
    from src.rag.pricing import estimate_cost

    model_id = getattr(getattr(agent, "llm", None), "model", "")
    return estimate_cost(model_id, answer.usage.input_tokens, answer.usage.output_tokens)
