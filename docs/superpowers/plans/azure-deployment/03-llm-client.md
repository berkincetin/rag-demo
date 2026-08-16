# Task 3: Azure OpenAI Chat Client

**Goal:** A chat client for the `gpt-4.1-mini` deployment that supports tool
calling and reports token usage, matching the existing `LLMClient` protocol.

**Files:**
- Create: `azure/rag/llm_client.py`
- Create: `azure/tests/test_llm_client.py`

**Interfaces:**
- Consumes: `AzureConfig` (Task 1)
- Produces:
  ```python
  @dataclass
  class ToolCall:
      id: str
      name: str
      arguments: dict[str, Any]

  @dataclass
  class LLMResponse:
      text: str | None = None
      tool_calls: list[ToolCall] = field(default_factory=list)
      usage: TokenUsage = field(default_factory=TokenUsage)

      @property
      def wants_tools(self) -> bool: ...

  class AzureOpenAIClient:
      def __init__(self, config: AzureConfig | None = None, client: Any = None) -> None: ...
      def chat(self, messages: list[dict], tools: list[dict] | None = None) -> LLMResponse: ...
  ```

`TokenUsage` is copied in Task 4 (`azure/rag/models.py`). Until then, import it
from `src.rag.models` **only inside the test** — the implementation must import
from `azure.rag.models`, which Task 4 creates. To keep this task independently
runnable, create the minimal `azure/rag/models.py` here (Step 3) and let Task 4
extend it.

---

## Why temperature 0

Measured in Part 1: at Ollama's default 0.8 the model intermittently dropped
the `[n]` citation marker, and the citation gate then rejected a correct
answer. `LLM_TEMPERATURE=0` fixed it. The same reasoning applies here.

- [ ] **Step 1: Write the failing tests**

Create `azure/tests/test_llm_client.py`:

```python
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
    message = type(
        "Message", (), {"content": content, "tool_calls": tool_calls or []}
    )()
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
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_llm_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.llm_client'`

- [ ] **Step 3: Create the minimal models module**

Create `azure/rag/models.py` with `TokenUsage` copied verbatim from
`src/rag/models.py` lines 44-68 (`TokenUsage` and `_add_optional`). Change no
logic. Task 4 appends the remaining dataclasses to this same file.

- [ ] **Step 4: Write the client**

Create `azure/rag/llm_client.py`:

```python
"""Chat via an Azure OpenAI deployment.

Azure differs from the OpenAI API in one way that matters here: `model` is the
*deployment* name, not the model name. They happen to match in this project
(`gpt-4.1-mini`), which makes the distinction easy to forget when the
deployment is later renamed.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from azure.rag.config import AzureConfig
from azure.rag.models import TokenUsage

# Measured in Part 1: at a higher temperature the model intermittently omits
# the [n] citation marker and the citation gate then rejects a correct answer.
_TEMPERATURE = 0.0
_MAX_TOKENS = 1024


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class AzureOpenAIClient:
    """Tool-calling chat client over an Azure OpenAI deployment."""

    def __init__(self, config: AzureConfig | None = None, client: Any = None) -> None:
        self.config = config or AzureConfig.load()
        self._client = client or self._build_client()

    def _build_client(self) -> Any:
        from openai import AzureOpenAI

        return AzureOpenAI(
            azure_endpoint=self.config.openai_endpoint,
            api_key=self.config.openai_api_key,
            api_version=self.config.api_version,
        )

    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            # On Azure this is the deployment name, not the model name.
            "model": self.config.chat_deployment,
            "messages": messages,
            "temperature": _TEMPERATURE,
            "max_tokens": _MAX_TOKENS,
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": schema} for schema in tools]

        completion = self._client.chat.completions.create(**payload)
        choice = completion.choices[0].message
        calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=_as_dict(call.function.arguments),
            )
            for call in (choice.tool_calls or [])
        ]
        usage = getattr(completion, "usage", None)
        return LLMResponse(
            text=choice.content,
            tool_calls=calls,
            usage=TokenUsage(
                getattr(usage, "prompt_tokens", None),
                getattr(usage, "completion_tokens", None),
            ),
        )


def _as_dict(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else dict(value)
```

- [ ] **Step 5: Run the tests and verify they pass**

Run: `pytest azure/tests/test_llm_client.py -v`
Expected: 5 passed

- [ ] **Step 6: Verify against the real deployment**

```bash
python -c "
import sys
sys.stdout.reconfigure(encoding='utf-8')
from azure.rag.llm_client import AzureOpenAIClient
r = AzureOpenAIClient().chat([{'role':'user','content':'Tek kelimeyle cevap ver: merhaba'}])
print('text:', r.text)
print('tokens:', r.usage.input_tokens, r.usage.output_tokens)
"
```

Expected: a Turkish word and two integer token counts.

- [ ] **Step 7: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 8: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 9: Commit**

```bash
git add azure/
git commit -m "feat(azure): add Azure OpenAI chat client with tool calling"
```
