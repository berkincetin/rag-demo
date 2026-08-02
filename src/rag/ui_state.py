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


def active_model(session: MutableMapping, local_models: list[str]) -> ModelInfo | None:
    """The selected model, falling back to a local one when it is no longer usable."""
    chosen = session.get(_ACTIVE_MODEL_KEY)
    if chosen:
        candidates = {model.id: model for model in available_models(session, local_models)}
        if chosen in candidates:
            return candidates[chosen]
        session.pop(_ACTIVE_MODEL_KEY, None)

    return local_model(local_models[0]) if local_models else None
