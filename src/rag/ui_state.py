"""Logic behind the Streamlit pages.

Streamlit page files are excluded from coverage, so everything that can be
reasoned about lives here instead and is tested with a plain dict standing in
for `st.session_state`. This module imports no Streamlit.
"""

from collections.abc import MutableMapping
from dataclasses import dataclass

from src.rag.catalog import ModelInfo, get_model, list_models, local_model, providers
from src.rag.credentials import SessionCredentialStore, mask_key

_STORE_KEY = "_credential_store"
_ACTIVE_MODEL_KEY = "_active_model_id"


@dataclass(frozen=True)
class ProviderStatus:
    provider: str
    configured: bool
    masked: str


def get_store(session: MutableMapping) -> SessionCredentialStore:
    """The session's credential store, created on first use."""
    store = session.get(_STORE_KEY)
    if store is None:
        store = SessionCredentialStore()
        session[_STORE_KEY] = store
    return store


def set_key(session: MutableMapping, provider: str, key: str) -> None:
    """Store or clear a provider key for this session."""
    get_store(session).set(provider, key)


def provider_status(session: MutableMapping) -> dict[str, ProviderStatus]:
    """Which cloud providers currently have a key, with the key masked."""
    store = get_store(session)
    statuses = {}
    for provider in providers():
        if provider == "ollama":
            continue
        key = store.get(provider)
        statuses[provider] = ProviderStatus(
            provider=provider, configured=bool(key), masked=mask_key(key or "")
        )
    return statuses


def available_models(session: MutableMapping, local_models: list[str]) -> list[ModelInfo]:
    """Local models plus the cloud models whose provider has a key."""
    store = get_store(session)
    models = [local_model(name) for name in local_models]
    models.extend(model for model in list_models() if store.get(model.provider))
    return models


def set_active_model(
    session: MutableMapping, model_id: str, local_models: list[str] | None = None
) -> None:
    """Select a model, refusing cloud models whose key is missing."""
    if model_id in (local_models or []):
        session[_ACTIVE_MODEL_KEY] = model_id
        return

    model = get_model(model_id)
    if model is None:
        # Not a known cloud model and not in the local list — treat as local.
        session[_ACTIVE_MODEL_KEY] = model_id
        return
    if not get_store(session).get(model.provider):
        raise ValueError(f"{model.provider} için anahtar girilmedi")
    session[_ACTIVE_MODEL_KEY] = model_id


def active_model(
    session: MutableMapping, local_models: list[str], preferred: str | None = None
) -> ModelInfo | None:
    """The selected model, falling back to a local one when it is no longer usable.

    `preferred` is the configured chat model. It matters because `ollama list`
    also returns embedding models, and defaulting to whichever came first would
    hand the agent a model that cannot hold a conversation.
    """
    chosen = session.get(_ACTIVE_MODEL_KEY)
    if chosen:
        candidates = {model.id: model for model in available_models(session, local_models)}
        if chosen in candidates:
            return candidates[chosen]
        session.pop(_ACTIVE_MODEL_KEY, None)

    if preferred and preferred in local_models:
        return local_model(preferred)
    return local_model(local_models[0]) if local_models else None


# --- presentation helpers ---------------------------------------------------
#
# Turkish number formatting uses a comma as the decimal separator. The rule that
# matters most: a value that was never measured is labelled, never rendered as
# zero — "$0,0000" for an unpriced model would be a lie, and "—" for a rate with
# no applicable cases keeps it out of comparisons.

_SUGGESTED = ("qwen2.5:7b-instruct", "llama3.1:8b", "gemma2:9b", "qwen2.5:0.5b")

# Rough per-case token estimate, averaged from the runs measured in Task 6.
_TOKENS_PER_CASE = (6000, 200)


def _tr(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "boyut bilinmiyor"
    # Decimal units, matching what `ollama list` prints, so the two can be
    # compared side by side without the user wondering which one is wrong.
    if size_bytes >= 1_000_000_000:
        return f"{_tr(size_bytes / 1_000_000_000, 1)} GB"
    return f"{_tr(size_bytes / 1_000_000, 1)} MB"


def suggested_models(installed: list[str]) -> list[str]:
    return [name for name in _SUGGESTED if name not in installed]


def pull_label(status: str, fraction: float | None) -> str:
    """Show a percentage only when Ollama actually reported a total."""
    if fraction is None:
        return status
    return f"{status} — %{round(fraction * 100)}"


def format_cost(cost_usd: float | None) -> str:
    if cost_usd is None:
        return "fiyat girilmedi"
    return f"${_tr(cost_usd, 4)}"


def format_latency(latency_ms: float) -> str:
    if latency_ms < 1000:
        return f"{round(latency_ms)} ms"
    return f"{_tr(latency_ms / 1000, 1)} sn"


def format_rate(rate: float | None) -> str:
    return "—" if rate is None else f"%{round(rate * 100)}"


def summary_rows(summaries) -> list[dict]:
    """Metric table rows, with partial pricing spelled out rather than hidden."""
    rows = []
    for summary in summaries:
        if summary.total_cost_usd is None:
            cost = "fiyat girilmedi"
        elif summary.priced_runs < summary.runs:
            cost = (
                f"{format_cost(summary.total_cost_usd)} ({summary.priced_runs}/{summary.runs} koşu)"
            )
        else:
            cost = format_cost(summary.total_cost_usd)
        rows.append(
            {
                "model": summary.model_id,
                "sağlayıcı": summary.provider,
                "koşu": summary.runs,
                "ort. süre": format_latency(summary.avg_latency_ms),
                "ort. atıf": _tr(summary.avg_citations, 1),
                "kapı isabeti": format_rate(summary.gate_pass_rate),
                "cost": cost,
            }
        )
    return rows


def estimate_eval_cost(model_id: str, cases: int) -> float | None:
    """A rough pre-flight estimate — label it as approximate wherever it is shown."""
    from src.rag.pricing import estimate_cost

    return estimate_cost(model_id, _TOKENS_PER_CASE[0] * cases, _TOKENS_PER_CASE[1] * cases)


def comparison_rows(results) -> list[dict]:
    """Evaluation results, best citation rate first, then fastest."""
    ordered = sorted(
        results,
        key=lambda r: (-(r.citation_rate or -1), r.avg_latency_ms or float("inf")),
    )
    return [
        {
            "model": result.model_id,
            "atıf oranı": format_rate(result.citation_rate),
            "kaynak isabeti": format_rate(result.source_accuracy),
            "kanıt isabeti": format_rate(result.evidence_hit),
            "red isabeti": format_rate(result.refusal_accuracy),
            "ort. süre": format_latency(result.avg_latency_ms or 0),
            "toplam maliyet": format_cost(result.total_cost_usd),
        }
        for result in ordered
    ]
