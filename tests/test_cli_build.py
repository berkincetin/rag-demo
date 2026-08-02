"""build_agent must honour a UI-selected model and session credentials."""

from src.rag.cli import resolve_provider


def test_a_local_model_resolves_to_ollama():
    assert resolve_provider("qwen2.5:7b-instruct") == "ollama"


def test_a_cloud_model_resolves_to_its_vendor():
    assert resolve_provider("claude-opus-5") == "anthropic"
    assert resolve_provider("gemini-2.0-flash") == "gemini"


def test_an_unknown_model_is_treated_as_local():
    # Anything Ollama has installed is unknown to the static catalog.
    assert resolve_provider("some-custom-model") == "ollama"
