"""Session state behind the HTTP API.

Reduced from src/rag/ui_state.py to the six helpers this deployment needs.
Everything about credential stores, model switching, provider status, Ollama
and evaluation is gone: there is one model, its key comes from a Container
Apps secret, and the key-entry endpoints were deliberately removed from the
attack surface.

This module imports no web framework — the session is any `MutableMapping`,
which is what makes it testable with a plain dict.
"""

from collections.abc import MutableMapping

_MEMORY_KEY = "_conversation_memory"
_USER_NAME_KEY = "_user_name"
_TRANSCRIPT_KEY = "_transcript"


def get_memory(session: MutableMapping):
    """The session's conversation memory, created on first use."""
    from azure.rag.memory import ConversationMemory

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
