"""Per-request context carried without changing any function signature.

The agent graph (`graph.py`) is deliberately untouched by the streaming and
upload features. Both need something that is request-scoped, so it travels in
context variables instead of through the graph's state.

Threading note: context variables do NOT propagate into a thread created with
`threading.Thread`. The streaming endpoint therefore installs the sink *inside*
the worker thread rather than relying on inheritance.
"""

from collections.abc import Callable
from contextvars import ContextVar, Token
from typing import Any

_token_sink: ContextVar[Callable[[str], None] | None] = ContextVar("token_sink", default=None)
_upload_store: ContextVar[Any] = ContextVar("upload_store", default=None)


def set_token_sink(sink: Callable[[str], None]) -> Token:
    """Install a sink that receives every text delta the LLM produces."""
    return _token_sink.set(sink)


def reset_token_sink(token: Token) -> None:
    _token_sink.reset(token)


def emit_token(text: str) -> None:
    """Publish one text delta. A no-op when nothing is listening."""
    sink = _token_sink.get()
    if sink is not None and text:
        sink(text)


def set_upload_store(store: Any) -> Token:
    """Install the uploaded-document store for the current request."""
    return _upload_store.set(store)


def reset_upload_store(token: Token) -> None:
    _upload_store.reset(token)


def active_upload_store() -> Any:
    """The current request's uploaded-document store, or None."""
    return _upload_store.get()
