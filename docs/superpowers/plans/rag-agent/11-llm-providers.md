# Task 11: LLM provider abstraction

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 10](10-tools-prompts.md)
**Next:** [Task 12](12-agent.md)

---

**Files:**
- Create: `src/rag/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `Config`
- Produces: dataclasses `ToolCall(id: str, name: str, arguments: dict)` and `LLMResponse(text: str | None, tool_calls: list[ToolCall])`; protocol `LLMClient` with `chat(messages, tools=None) -> LLMResponse`; classes `OllamaClient`, `AnthropicClient`, `OpenAIClient`; factory `get_client(config: Config | None = None) -> LLMClient`

Default provider is Ollama (ADR-007). `src/rag/llm.py` is excluded from coverage — only the factory's routing and the response parsers are unit-tested; the network calls are not.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm.py
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
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert isinstance(get_client(Config.load()), AnthropicClient)


def test_get_client_routes_to_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert isinstance(get_client(Config.load()), OpenAIClient)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.llm'`

- [ ] **Step 3: Write minimal `src/rag/llm.py`**

```python
"""Pluggable LLM providers.

Default is Ollama so the system runs fully offline (the case prefers a local
model). Cloud providers are one environment variable away when local
tool-calling proves unreliable. See docs/02-karar-kaydi.md ADR-007.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests

from src.rag.config import Config

_TIMEOUT_SECONDS = 120


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class LLMClient(Protocol):
    def chat(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse: ...


def parse_ollama_response(payload: dict[str, Any]) -> LLMResponse:
    """Normalize an Ollama /api/chat payload into an LLMResponse."""
    message = payload.get("message", {})
    calls = [
        ToolCall(
            id=str(index),
            name=call["function"]["name"],
            arguments=_as_dict(call["function"].get("arguments", {})),
        )
        for index, call in enumerate(message.get("tool_calls") or [])
    ]
    return LLMResponse(text=message.get("content") or None, tool_calls=calls)


def _as_dict(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else dict(value)


class OllamaClient:
    def __init__(self, model: str, base_url: str | None = None) -> None:
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def chat(self, messages, tools=None) -> LLMResponse:
        body: dict[str, Any] = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            body["tools"] = [{"type": "function", "function": schema} for schema in tools]
        response = requests.post(
            f"{self.base_url}/api/chat", json=body, timeout=_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return parse_ollama_response(response.json())


class AnthropicClient:
    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        import anthropic

        self.model = model
        self._client = anthropic.Anthropic()

    def chat(self, messages, tools=None) -> LLMResponse:
        system = "".join(m["content"] for m in messages if m["role"] == "system")
        turns = [m for m in messages if m["role"] != "system"]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1024,
            "system": system,
            "messages": turns,
        }
        if tools:
            payload["tools"] = [
                {
                    "name": schema["name"],
                    "description": schema["description"],
                    "input_schema": schema["parameters"],
                }
                for schema in tools
            ]
        message = self._client.messages.create(**payload)
        text = "".join(block.text for block in message.content if block.type == "text")
        calls = [
            ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
            for block in message.content
            if block.type == "tool_use"
        ]
        return LLMResponse(text=text or None, tool_calls=calls)


class OpenAIClient:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI()

    def chat(self, messages, tools=None) -> LLMResponse:
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
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
        return LLMResponse(text=choice.content, tool_calls=calls)


def get_client(config: Config | None = None) -> LLMClient:
    """Build the configured LLM client."""
    config = config or Config.load()
    provider = config.llm_provider.lower()
    if provider == "ollama":
        return OllamaClient(model=config.llm_model)
    if provider == "anthropic":
        return AnthropicClient()
    if provider == "openai":
        return OpenAIClient(model=config.llm_model)
    raise ValueError(f"unsupported LLM_PROVIDER: {config.llm_provider}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm.py -v --no-cov`
Expected: PASS (7 passed). Anthropic and OpenAI construction requires their SDKs; if not installed, the routing tests for those providers may be skipped — note that in the commit message rather than adding the dependency.

- [ ] **Step 5: Smoke-test the configured provider by hand**

Run:
```bash
python -c "from src.rag.llm import get_client; print(get_client().chat([{'role':'user','content':'Merhaba, tek kelimeyle cevap ver.'}]).text)"
```
Expected: a short Turkish reply. If Ollama is not running, start it and pull the model (`ollama pull qwen2.5:7b-instruct`), or switch `LLM_PROVIDER` in `.env`.

- [ ] **Step 6: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/llm.py tests/test_llm.py
git commit -m "feat(llm): add pluggable Ollama, Anthropic, and OpenAI clients"
```
