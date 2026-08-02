import pytest

from src.rag.config import Config
from src.rag.llm import (
    AnthropicClient,
    LLMResponse,
    OllamaClient,
    OpenAIClient,
    get_client,
    parse_ollama_response,
)


def test_get_client_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    assert isinstance(get_client(Config.load()), OllamaClient)


def test_get_client_routes_to_anthropic(monkeypatch):
    # The cloud SDKs are optional: Ollama is the default provider and the only
    # one in requirements.txt. Constructing the client needs the SDK installed.
    pytest.importorskip("anthropic")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert isinstance(get_client(Config.load()), AnthropicClient)


def test_get_client_routes_to_openai(monkeypatch):
    pytest.importorskip("openai")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert isinstance(get_client(Config.load()), OpenAIClient)


def test_get_client_routing_table_names_every_supported_provider(monkeypatch):
    # Routing itself is testable without the SDKs: an unknown provider raises,
    # a known one does not reach the "unsupported" branch.
    for provider in ("ollama", "anthropic", "openai"):
        monkeypatch.setenv("LLM_PROVIDER", provider)
        try:
            get_client(Config.load())
        except ModuleNotFoundError:
            pass  # SDK absent, but routing reached the right constructor
        except ValueError as error:  # pragma: no cover - would be a routing bug
            pytest.fail(f"{provider} was not routed: {error}")


def test_get_client_rejects_an_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "hal9000")

    with pytest.raises(ValueError, match="unsupported LLM_PROVIDER"):
        get_client(Config.load())


def test_parse_ollama_response_extracts_plain_text():
    payload = {"message": {"content": "Merhaba", "tool_calls": []}}

    response = parse_ollama_response(payload)

    assert response.text == "Merhaba"
    assert response.tool_calls == []


def test_parse_ollama_response_extracts_tool_calls():
    payload = {
        "message": {
            "content": "",
            "tool_calls": [
                {"function": {"name": "search_documents", "arguments": {"query": "izin"}}}
            ],
        }
    }

    response = parse_ollama_response(payload)

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "search_documents"
    assert response.tool_calls[0].arguments == {"query": "izin"}


def test_llm_response_reports_whether_it_wants_tools():
    assert LLMResponse(text="hi", tool_calls=[]).wants_tools is False


def test_ollama_timeout_is_configurable(monkeypatch):
    # A 7B model on CPU needs well over 120s once tool output is in the context;
    # the second turn of the agent loop timed out at the original hardcoded value.
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "999")

    assert OllamaClient(model="m").timeout == 999


def test_ollama_timeout_default_allows_a_cpu_second_turn():
    assert OllamaClient(model="m").timeout >= 300


def test_ollama_defaults_to_deterministic_sampling():
    # Ollama's default temperature is 0.8. Measured: at 0.8 the same grounded
    # prompt sometimes omits the [n] citation marker, and the citation gate then
    # discards a correct answer. Grounded QA wants reproducible output.
    assert OllamaClient(model="m").temperature == 0.0


def test_ollama_temperature_is_configurable(monkeypatch):
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")

    assert OllamaClient(model="m").temperature == 0.7


def test_ollama_sends_temperature_in_the_request_options():
    sent = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "ok", "tool_calls": []}}

    def _fake_post(url, json, timeout):
        sent.update(json)
        return _FakeResponse()

    client = OllamaClient(model="m")
    client._post = _fake_post

    client.chat([{"role": "user", "content": "x"}])

    assert sent["options"]["temperature"] == 0.0
