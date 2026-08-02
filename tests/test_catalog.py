from src.rag.catalog import get_model, list_models, providers


def test_catalog_covers_the_four_providers():
    assert set(providers()) == {"ollama", "anthropic", "openai", "gemini"}


def test_models_can_be_filtered_by_provider():
    anthropic_models = list_models(provider="anthropic")

    assert anthropic_models
    assert all(m.provider == "anthropic" for m in anthropic_models)


def test_cloud_models_are_not_marked_local():
    assert get_model("claude-opus-5").local is False


def test_unknown_model_returns_none():
    assert get_model("model-yok") is None
