"""The single model this deployment can use.

Unlike src/rag/catalog.py there is no provider choice: the deployment talks to
one Azure OpenAI deployment, named by configuration. Local models are absent
entirely — there is no Ollama here.
"""

from dataclasses import dataclass

AZURE_MODEL_ID = "gpt-4.1-mini"
PROVIDER = "azure_openai"


@dataclass(frozen=True)
class ModelInfo:
    """One selectable model."""

    id: str
    provider: str
    label: str
    context_tokens: int | None = None
    local: bool = False


_MODELS = (ModelInfo(AZURE_MODEL_ID, PROVIDER, "GPT-4.1 mini (Azure)", 128_000),)


def list_models() -> list[ModelInfo]:
    """Every model this deployment can use."""
    return list(_MODELS)


def get_model(model_id: str) -> ModelInfo | None:
    """Look up a model by id; None when it is not this deployment's model."""
    return next((model for model in _MODELS if model.id == model_id), None)
