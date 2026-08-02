"""Session-scoped API key storage.

Keys entered in the UI live in memory for the lifetime of the browser session
and nowhere else: not on disk, not in an OS credential vault, and never written
back to the environment. A test asserts this module contains no persistence
calls at all, so the guarantee cannot erode by accident. Environment variables
remain a read-only fallback so the CLI and the Docker image keep working
without a UI session.
"""

import os
from typing import Protocol

_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


class CredentialStore(Protocol):
    def set(self, provider: str, key: str) -> None: ...
    def get(self, provider: str) -> str | None: ...
    def providers_with_keys(self) -> list[str]: ...


class SessionCredentialStore:
    """Holds keys in memory. Never serialized, never logged."""

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def set(self, provider: str, key: str) -> None:
        """Store a key, or clear it when the value is blank."""
        cleaned = (key or "").strip()
        if cleaned:
            self._keys[provider] = cleaned
        else:
            self._keys.pop(provider, None)

    def get(self, provider: str) -> str | None:
        return self._keys.get(provider)

    def providers_with_keys(self) -> list[str]:
        return sorted(self._keys)

    def __repr__(self) -> str:
        """Provider names only — the values must never reach a log or traceback."""
        return f"SessionCredentialStore(providers={self.providers_with_keys()})"


def mask_key(key: str) -> str:
    """Render a key for display: only the last four characters survive."""
    if not key:
        return ""
    if len(key) <= 8:
        return "…"
    return "…" + key[-4:]


def resolve_key(provider: str, store: CredentialStore | None = None) -> str | None:
    """Session key first, environment variable second."""
    if store is not None:
        session_key = store.get(provider)
        if session_key:
            return session_key

    env_var = _ENV_VARS.get(provider)
    if env_var is None:
        return None
    return os.getenv(env_var) or None
