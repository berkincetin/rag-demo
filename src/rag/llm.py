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
        response = requests.post(f"{self.base_url}/api/chat", json=body, timeout=_TIMEOUT_SECONDS)
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
