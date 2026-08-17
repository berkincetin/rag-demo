"""Azure OpenAI chat client: payload shape, tool parsing, token usage, streaming.

The client streams internally (`stream=True`) but still returns one complete
LLMResponse, so every assertion here is about that unchanged contract. The
fakes mimic the SDK's streaming shape: a sequence of chunks whose final member
carries `usage` and no choices.
"""

import json
from types import SimpleNamespace

from azure.rag import request_context
from azure.rag.config import AzureConfig
from azure.rag.llm_client import AzureOpenAIClient


def _delta_chunk(content=None, tool_calls=None):
    """One streamed chunk carrying a text and/or tool-call delta."""
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)], usage=None)


def _usage_chunk(prompt_tokens=11, completion_tokens=7):
    """The final chunk: usage only, no choices."""
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(choices=[], usage=usage)


def _tool_delta(index, call_id, name, arguments):
    return SimpleNamespace(
        index=index,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class FakeCompletions:
    def __init__(self, chunks) -> None:
        self.chunks = chunks
        self.payloads: list[dict] = []

    def create(self, **payload):
        self.payloads.append(payload)
        return iter(self.chunks)


class FakeClient:
    def __init__(self, chunks) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(chunks))


def _config() -> AzureConfig:
    return AzureConfig(
        openai_endpoint="https://example.openai.azure.com/",
        openai_api_key="k",
        api_version="2024-10-21",
        chat_deployment="gpt-4.1-mini",
        embedding_deployment="text-embedding-3-small",
        storage_dir="/tmp",
        data_dir="/tmp",
        top_k=5,
        min_cosine=-1.0,
        min_bm25=-1.0,
        max_tool_turns=3,
        internal_token=None,
    )


# --- payload shape ----------------------------------------------------------


def test_sends_deployment_name_as_model():
    fake = FakeClient([_delta_chunk("merhaba"), _usage_chunk()])

    AzureOpenAIClient(config=_config(), client=fake).chat([{"role": "user", "content": "selam"}])

    assert fake.chat.completions.payloads[0]["model"] == "gpt-4.1-mini"


def test_uses_temperature_zero():
    """Measured in Part 1: higher temperature drops citation markers."""
    fake = FakeClient([_delta_chunk("x"), _usage_chunk()])

    AzureOpenAIClient(config=_config(), client=fake).chat([{"role": "user", "content": "s"}])

    assert fake.chat.completions.payloads[0]["temperature"] == 0.0


def test_wraps_tool_schemas_in_function_envelope():
    fake = FakeClient([_delta_chunk("x"), _usage_chunk()])
    schema = {"name": "t", "description": "d", "parameters": {"type": "object"}}

    AzureOpenAIClient(config=_config(), client=fake).chat([], tools=[schema])

    sent = fake.chat.completions.payloads[0]["tools"][0]
    assert sent == {"type": "function", "function": schema}


def test_requests_usage_explicitly_when_streaming():
    """Without stream_options the API omits usage and every metric becomes null."""
    fake = FakeClient([_usage_chunk()])

    AzureOpenAIClient(config=_config(), client=fake).chat([])

    payload = fake.chat.completions.payloads[0]
    assert payload["stream"] is True
    assert payload["stream_options"] == {"include_usage": True}


# --- response assembly ------------------------------------------------------


def test_concatenates_text_deltas():
    fake = FakeClient([_delta_chunk("Yıllık "), _delta_chunk("izin"), _usage_chunk()])

    response = AzureOpenAIClient(config=_config(), client=fake).chat([])

    assert response.text == "Yıllık izin"


def test_maps_token_usage():
    fake = FakeClient([_delta_chunk("x"), _usage_chunk(prompt_tokens=120, completion_tokens=34)])

    response = AzureOpenAIClient(config=_config(), client=fake).chat([])

    assert response.usage.input_tokens == 120
    assert response.usage.output_tokens == 34


def test_parses_tool_calls_with_json_arguments():
    fake = FakeClient(
        [
            _delta_chunk(
                tool_calls=[
                    _tool_delta(0, "call_1", "search_documents", json.dumps({"query": "izin"}))
                ]
            ),
            _usage_chunk(),
        ]
    )

    response = AzureOpenAIClient(config=_config(), client=fake).chat([])

    assert response.wants_tools
    assert response.tool_calls[0].name == "search_documents"
    assert response.tool_calls[0].arguments == {"query": "izin"}


def test_accumulates_tool_call_arguments_across_deltas():
    """Arguments arrive as string fragments that only parse once joined."""
    fake = FakeClient(
        [
            _delta_chunk(
                tool_calls=[_tool_delta(0, "call_1", "search_documents", '{"query": "yem')]
            ),
            _delta_chunk(tool_calls=[_tool_delta(0, None, None, 'ek"}')]),
            _usage_chunk(),
        ]
    )

    response = AzureOpenAIClient(config=_config(), client=fake).chat([], tools=[{"name": "x"}])

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "search_documents"
    assert response.tool_calls[0].arguments == {"query": "yemek"}


def test_keeps_parallel_tool_calls_separate():
    fake = FakeClient(
        [
            _delta_chunk(tool_calls=[_tool_delta(0, "a", "list_documents", "{}")]),
            _delta_chunk(tool_calls=[_tool_delta(1, "b", "search_documents", '{"query": "x"}')]),
            _usage_chunk(),
        ]
    )

    response = AzureOpenAIClient(config=_config(), client=fake).chat([], tools=[{"name": "x"}])

    assert [call.name for call in response.tool_calls] == ["list_documents", "search_documents"]


# --- token sink -------------------------------------------------------------


def test_publishes_text_deltas_to_the_sink():
    fake = FakeClient([_delta_chunk("a"), _delta_chunk("b"), _usage_chunk()])
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    try:
        AzureOpenAIClient(config=_config(), client=fake).chat([])
    finally:
        request_context.reset_token_sink(token)

    assert received == ["a", "b"]


def test_tool_call_deltas_are_not_published_as_text():
    fake = FakeClient(
        [
            _delta_chunk(tool_calls=[_tool_delta(0, "c", "list_documents", "{}")]),
            _usage_chunk(),
        ]
    )
    received: list[str] = []
    token = request_context.set_token_sink(received.append)
    try:
        AzureOpenAIClient(config=_config(), client=fake).chat([], tools=[{"name": "x"}])
    finally:
        request_context.reset_token_sink(token)

    assert received == []


def test_works_without_a_sink_installed():
    fake = FakeClient([_delta_chunk("a"), _usage_chunk()])

    response = AzureOpenAIClient(config=_config(), client=fake).chat([])

    assert response.text == "a"
