"""Azure OpenAI chat client: payload shape, tool parsing, token usage."""

import json

from azure.rag.config import AzureConfig
from azure.rag.llm_client import AzureOpenAIClient


class FakeCompletions:
    def __init__(self, response) -> None:
        self.response = response
        self.payloads: list[dict] = []

    def create(self, **payload):
        self.payloads.append(payload)
        return self.response


class FakeClient:
    def __init__(self, response) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions(response)})()


def _response(content=None, tool_calls=None, prompt=11, completion=7):
    message = type("Message", (), {"content": content, "tool_calls": tool_calls or []})()
    return type(
        "Completion",
        (),
        {
            "choices": [type("Choice", (), {"message": message})()],
            "usage": type(
                "Usage", (), {"prompt_tokens": prompt, "completion_tokens": completion}
            )(),
        },
    )()


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


def test_sends_deployment_name_as_model():
    fake = FakeClient(_response(content="merhaba"))

    AzureOpenAIClient(config=_config(), client=fake).chat([{"role": "user", "content": "selam"}])

    assert fake.chat.completions.payloads[0]["model"] == "gpt-4.1-mini"


def test_uses_temperature_zero():
    """Measured in Part 1: higher temperature drops citation markers."""
    fake = FakeClient(_response(content="x"))

    AzureOpenAIClient(config=_config(), client=fake).chat([{"role": "user", "content": "s"}])

    assert fake.chat.completions.payloads[0]["temperature"] == 0.0


def test_parses_tool_calls_with_json_arguments():
    call = type(
        "Call",
        (),
        {
            "id": "call_1",
            "function": type(
                "Fn", (), {"name": "search_documents", "arguments": json.dumps({"query": "izin"})}
            )(),
        },
    )()
    fake = FakeClient(_response(tool_calls=[call]))

    response = AzureOpenAIClient(config=_config(), client=fake).chat([])

    assert response.wants_tools
    assert response.tool_calls[0].name == "search_documents"
    assert response.tool_calls[0].arguments == {"query": "izin"}


def test_maps_token_usage():
    fake = FakeClient(_response(content="x", prompt=120, completion=34))

    response = AzureOpenAIClient(config=_config(), client=fake).chat([])

    assert response.usage.input_tokens == 120
    assert response.usage.output_tokens == 34


def test_wraps_tool_schemas_in_function_envelope():
    fake = FakeClient(_response(content="x"))
    schema = {"name": "t", "description": "d", "parameters": {"type": "object"}}

    AzureOpenAIClient(config=_config(), client=fake).chat([], tools=[schema])

    sent = fake.chat.completions.payloads[0]["tools"][0]
    assert sent == {"type": "function", "function": schema}
