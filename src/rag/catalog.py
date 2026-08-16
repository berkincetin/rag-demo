"""The single source of truth for providers and their cloud models.

Local models are deliberately absent: they are whatever Ollama currently has
installed, discovered at runtime by `ollama_admin`. Only cloud models — whose
identifiers are fixed by their vendor — are listed here.
"""

from dataclasses import dataclass

PROVIDERS = ("ollama", "anthropic", "openai", "gemini")


@dataclass(frozen=True)
class ModelInfo:
    """One selectable model."""

    id: str
    provider: str
    label: str
    context_tokens: int | None = None
    local: bool = False


# Canonical vendor identifiers — never append a date suffix to these.
_CLOUD_MODELS = (
    ModelInfo("claude-opus-5", "anthropic", "Claude Opus 5", 1_000_000),
    ModelInfo("claude-sonnet-5", "anthropic", "Claude Sonnet 5", 1_000_000),
    ModelInfo("claude-haiku-4-5", "anthropic", "Claude Haiku 4.5", 200_000),
    ModelInfo("gpt-4o-mini", "openai", "GPT-4o mini", 128_000),
    ModelInfo("gemini-3.5-flash", "gemini", "Gemini 3.5 Flash", 1_000_000),
)


def providers() -> tuple[str, ...]:
    """Every provider the system can talk to."""
    return PROVIDERS


def list_models(provider: str | None = None) -> list[ModelInfo]:
    """Cloud models, optionally narrowed to one provider."""
    if provider is None:
        return list(_CLOUD_MODELS)
    return [model for model in _CLOUD_MODELS if model.provider == provider]


def get_model(model_id: str) -> ModelInfo | None:
    """Look up a cloud model by id; None when it is not a known cloud model."""
    return next((model for model in _CLOUD_MODELS if model.id == model_id), None)


def local_model(name: str) -> ModelInfo:
    """Wrap an Ollama model name as a ModelInfo."""
    return ModelInfo(id=name, provider="ollama", label=name, local=True)
