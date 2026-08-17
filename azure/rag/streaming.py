"""Turn one agent run into a stream of SSE events.

The agent graph is synchronous and returns a complete answer. Streaming works
by running it on a worker thread while text deltas arrive on a queue, which
this generator drains.

Why `replace` exists: the text that streams is a *candidate*. The citation gate
can reject it and substitute a repaired answer, a "no information" template, or
a refusal that never called the LLM at all. When the final text differs from
what was streamed, the client is told to swap it.
"""

import json
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Any

from azure.rag.request_context import reset_token_sink, set_token_sink

_END = object()


def format_sse(event: dict[str, Any]) -> str:
    """One event as an SSE `data:` frame."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def answer_events(
    run: Callable[[Callable[[str], None]], dict[str, Any]],
    *,
    on_meta: Callable[[dict[str, Any]], dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Run `run` on a worker thread, yielding start/token/meta/replace/error.

    `run` receives an `emit` callable and returns the finished result dict.
    `on_meta` turns that result into the payload of the `meta` event.
    """
    deltas: queue.Queue = queue.Queue()
    outcome: dict[str, Any] = {}

    def worker() -> None:
        # Context variables do not cross thread boundaries, so the sink is
        # installed here rather than in the caller's context.
        token = set_token_sink(deltas.put)
        try:
            outcome["result"] = run(deltas.put)
        except Exception as error:  # noqa: BLE001 - surfaced as an error event
            outcome["error"] = str(error)
        finally:
            reset_token_sink(token)
            deltas.put(_END)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    yield {"type": "start"}

    streamed: list[str] = []
    while True:
        item = deltas.get()
        if item is _END:
            break
        streamed.append(item)
        yield {"type": "token", "content": item}

    thread.join()

    if "error" in outcome:
        yield {"type": "error", "detail": outcome["error"]}
        return

    result = outcome.get("result") or {}
    final_text = result.get("text", "")
    if final_text != "".join(streamed):
        yield {"type": "replace", "content": final_text}

    yield {"type": "meta", **on_meta(result)}
