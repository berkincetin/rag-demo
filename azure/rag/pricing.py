"""Cost estimation from an editable price table.

Prices are never hardcoded and never guessed. A model whose price has not been
verified stays `null` in the table and produces `None` here — the UI renders
that as "fiyat girilmedi" rather than as free, because showing $0 for a paid
model is a lie that compounds across every aggregate built on top of it.

One deliberate difference from src/rag/pricing.py: an unknown model id returns
`None`, not `0.0`. In the local deployment `0.0` meant "this came from Ollama,
so it genuinely costs nothing." Here every model is a paid Azure deployment, so
that fallback would report a paid model as free — the exact lie the module
docstring above warns about.
"""

import json
from functools import lru_cache
from pathlib import Path

from azure.rag.catalog import get_model

_PRICES_PATH = Path(__file__).resolve().parents[1] / "config" / "model_prices.json"


@lru_cache(maxsize=1)
def load_prices() -> dict:
    """Read the price table. Cached — the file is edited between runs, not during."""
    return json.loads(_PRICES_PATH.read_text(encoding="utf-8"))


def estimate_cost(
    model_id: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    """USD for one run, or None when it cannot be known.

    None means "not measurable": the token counts are missing, the model is not
    this deployment's, or its price has not been verified.
    """
    if input_tokens is None or output_tokens is None:
        return None

    if get_model(model_id) is None:
        return None

    entry = load_prices().get(model_id)
    if not isinstance(entry, dict):
        return None
    if entry.get("input") is None or entry.get("output") is None:
        return None

    return (input_tokens / 1_000_000) * entry["input"] + (output_tokens / 1_000_000) * entry[
        "output"
    ]
