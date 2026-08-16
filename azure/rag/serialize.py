"""Dataclasses → JSON payloads for the Next.js front-end.

Kept separate from `api.py` so the wire contract is testable without starting a
server. Two rules hold throughout:

* **camelCase keys** — the consumer is TypeScript.
* **An unmeasured value stays `null`.** A model may have no verified price;
  rendering that as `0` would state a measurement that was never taken.

Reduced from src/rag/serialize.py: the resource keys (peakCpuPercent, peakRamMb,
gpuVramMb) are gone because this deployment does not measure them, and
`evaluation_payload` is gone because the evaluation endpoints were removed from
the API's attack surface.
"""

from typing import Any

from azure.rag.catalog import ModelInfo
from azure.rag.metrics import ModelSummary, RunRecord
from azure.rag.models import Answer


def answer_payload(answer: Answer, cost_usd: float | None) -> dict[str, Any]:
    """One agent answer, with everything the chat view renders."""
    return {
        "text": answer.text,
        "citations": list(answer.citations),
        # `grounded` saves the client from re-deriving "was this a refusal?"
        # from an empty citation list.
        "grounded": bool(answer.citations),
        "toolTrace": [
            {
                "name": call["name"],
                "arguments": call.get("arguments", {}),
                "chars": call.get("chars", 0),
                "injected": bool(call.get("injected")),
            }
            for call in answer.tool_trace
        ],
        "latencyMs": answer.latency_ms,
        "inputTokens": answer.usage.input_tokens,
        "outputTokens": answer.usage.output_tokens,
        "costUsd": cost_usd,
    }


def model_payload(model: ModelInfo) -> dict[str, Any]:
    """One selectable model."""
    return {
        "id": model.id,
        "label": model.label,
        "provider": model.provider,
        "local": model.local,
        "contextTokens": model.context_tokens,
    }


def run_payload(run: RunRecord) -> dict[str, Any]:
    """One recorded question, for the metrics history table."""
    return {
        "ts": run.ts,
        "modelId": run.model_id,
        "provider": run.provider,
        "question": run.question,
        "latencyMs": run.latency_ms,
        "inputTokens": run.input_tokens,
        "outputTokens": run.output_tokens,
        "costUsd": run.cost_usd,
        "citationCount": run.citation_count,
        "gatePassed": run.gate_passed,
        "toolCalls": run.tool_calls,
        "repaired": run.repaired,
        "turnIndex": run.turn_index,
    }


def summary_payload(summary: ModelSummary) -> dict[str, Any]:
    """Per-model aggregate. `pricedRuns < runs` means the cost is partial."""
    return {
        "modelId": summary.model_id,
        "provider": summary.provider,
        "runs": summary.runs,
        "pricedRuns": summary.priced_runs,
        "avgLatencyMs": summary.avg_latency_ms,
        "totalCostUsd": summary.total_cost_usd,
        "avgCitations": summary.avg_citations,
        "gatePassRate": summary.gate_pass_rate,
        "totalInputTokens": summary.total_input_tokens,
        "totalOutputTokens": summary.total_output_tokens,
    }
