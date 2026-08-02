"""Cost estimation from an editable price table.

Prices are never hardcoded and never guessed. A model whose price has not been
verified stays `null` in the table and produces `None` here — the UI renders
that as "fiyat girilmedi" rather than as free, because showing $0 for a paid
model is a lie that compounds across every aggregate built on top of it.
"""

import json
from functools import lru_cache
from pathlib import Path

from src.rag.catalog import get_model

_PRICES_PATH = Path(__file__).resolve().parents[2] / "config" / "model_prices.json"


@lru_cache(maxsize=1)
def load_prices() -> dict:
    """Read the price table. Cached — the file is edited between runs, not during."""
    return json.loads(_PRICES_PATH.read_text(encoding="utf-8"))


def estimate_cost(
    model_id: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    """USD for one run, or None when it cannot be known.

    None means "not measurable": either the token counts are missing or the
    model has no verified price. Local models are genuinely free of API cost.
    """
    if input_tokens is None or output_tokens is None:
        return None

    if get_model(model_id) is None:
        # Not a known cloud model — it came from Ollama, so it runs locally.
        return 0.0

    entry = load_prices().get(model_id)
    if not isinstance(entry, dict):
        return None
    if entry.get("input") is None or entry.get("output") is None:
        return None

    return (input_tokens / 1_000_000) * entry["input"] + (output_tokens / 1_000_000) * entry[
        "output"
    ]
