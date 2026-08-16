"""Configuration loading for the Azure deployment."""

from azure.rag.config import AzureConfig


def test_load_reads_endpoint_and_deployments(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
    monkeypatch.setenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

    config = AzureConfig.load()

    assert config.openai_endpoint == "https://example.openai.azure.com/"
    assert config.openai_api_key == "secret"
    assert config.chat_deployment == "gpt-4.1-mini"
    assert config.embedding_deployment == "text-embedding-3-small"


def test_thresholds_have_no_silent_default():
    """The e5 thresholds are invalid for text-embedding-3-small.

    Task 8 measures real values. Until then the defaults must be explicit
    placeholders that a reader cannot mistake for calibrated numbers.
    """
    assert AzureConfig.load().min_cosine != 0.80
