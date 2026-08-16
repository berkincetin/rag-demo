"""Logic behind the Gradio front-end.

`gradio_app.py` is layout and wiring only and is excluded from coverage, so
everything that can be reasoned about lives here instead and is tested with a
plain dict standing in for the session. This module imports no UI framework —
the session is any `MutableMapping`.
"""

from collections.abc import MutableMapping
from dataclasses import dataclass

from src.rag.catalog import ModelInfo, get_model, list_models, local_model, providers
from src.rag.credentials import SessionCredentialStore, mask_key

_STORE_KEY = "_credential_store"
_ACTIVE_MODEL_KEY = "_active_model_id"
_MEMORY_KEY = "_conversation_memory"
_USER_NAME_KEY = "_user_name"
_TRANSCRIPT_KEY = "_transcript"


def get_memory(session: MutableMapping):
    """The session's conversation memory, created on first use."""
    from src.rag.memory import ConversationMemory

    memory = session.get(_MEMORY_KEY)
    if memory is None:
        memory = ConversationMemory()
        session[_MEMORY_KEY] = memory
    return memory


def set_user_name(session: MutableMapping, name: str) -> None:
    session[_USER_NAME_KEY] = (name or "").strip()


def get_user_name(session: MutableMapping) -> str:
    return session.get(_USER_NAME_KEY, "")


def get_transcript(session: MutableMapping) -> list[tuple[str, str]]:
    """What is shown on screen — a superset of what the model remembers.

    Refusals are deliberately kept out of `ConversationMemory` but still belong
    in front of the user, so the screen keeps its own list.
    """
    return session.setdefault(_TRANSCRIPT_KEY, [])


def add_to_transcript(session: MutableMapping, question: str, answer: str) -> None:
    get_transcript(session).append((question, answer))


def clear_chat(session: MutableMapping) -> None:
    """Reset the conversation. The user's name survives — it is not a turn."""
    get_memory(session).clear()
    session[_TRANSCRIPT_KEY] = []


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
                "toplam giriş tk": _int_or_dash(summary.total_input_tokens),
                "toplam çıkış tk": _int_or_dash(summary.total_output_tokens),
                "tepe CPU": format_percent(summary.peak_cpu_percent),
                "tepe RAM": format_ram(summary.peak_ram_mb),
                "ort. atıf": _tr(summary.avg_citations, 1),
                "kapı isabeti": format_rate(summary.gate_pass_rate),
                "cost": cost,
            }
        )
    return rows


def _int_or_dash(value: int | None) -> str:
    return "—" if value is None else f"{value:,}".replace(",", ".")


def format_percent(value: float | None) -> str:
    return "—" if value is None else f"%{value:.0f}"


def format_ram(mb: int | None) -> str:
    if mb is None:
        return "—"
    return f"{_tr(mb / 1024, 1)} GB" if mb >= 1024 else f"{mb} MB"


def format_gpu(vram_mb: int | None) -> str:
    """`None` = ölçülemedi; `0` = model yüklü ama CPU'da çalışıyor."""
    if vram_mb is None:
        return "ölçülmedi"
    if vram_mb == 0:
        return "CPU'da (GPU kullanılmıyor)"
    return f"{_tr(vram_mb / 1024, 1)} GB VRAM"


def citation_markdown(answer) -> str:
    """The numbered source list shown under an answer.

    An answer with no citations is a refusal or a "bilmiyorum"; say so rather
    than rendering an empty block, which reads as a broken panel.
    """
    if not answer.citations:
        return "_Bu cevap için kaynak gösterilmedi._"
    return "\n".join(
        f"**{position}.** {label}" for position, label in enumerate(answer.citations, start=1)
    )


def tool_trace_rows(answer) -> list[list]:
    """Tool calls as table rows, keeping the automatic ones distinguishable.

    `injected` marks a search the agent ran on the model's behalf after the
    model answered without consulting anything. Collapsing it into a plain call
    would overstate how often the model chose its own tools.
    """
    return [
        [
            call["name"],
            str(call.get("arguments", {})),
            call.get("chars", 0),
            "otomatik" if call.get("injected") else "model",
        ]
        for call in answer.tool_trace
    ]


def metrics_line(answer, cost_usd: float | None) -> str:
    """One line of per-answer measurements, labelling anything unmeasured."""
    if answer.usage.input_tokens is None:
        tokens = "token ölçülmedi"
    else:
        tokens = f"↑{answer.usage.input_tokens} / ↓{answer.usage.output_tokens} token"
    return f"⏱ {format_latency(answer.latency_ms)}  ·  🔤 {tokens}  ·  💵 {format_cost(cost_usd)}"


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
