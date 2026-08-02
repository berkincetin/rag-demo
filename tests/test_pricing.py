import pytest

from src.rag.pricing import estimate_cost, load_prices


def test_known_price_is_computed_per_million_tokens():
    # 1M input + 1M output on Opus 5 = 5.00 + 25.00
    assert estimate_cost("claude-opus-5", 1_000_000, 1_000_000) == pytest.approx(30.0)


def test_local_models_cost_nothing():
    assert estimate_cost("qwen2.5:7b-instruct", 1000, 1000) == 0.0


def test_unpriced_model_returns_none_not_zero():
    # An unverified price must never render as free.
    assert estimate_cost("gpt-4o-mini", 1000, 1000) is None


def test_missing_token_count_returns_none():
    assert estimate_cost("claude-opus-5", None, 500) is None


def test_price_table_records_its_source():
    assert load_prices()["_kaynak"]
