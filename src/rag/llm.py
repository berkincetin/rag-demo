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
from src.rag.models import TokenUsage  # re-exported: callers import it from here

# A 7B model on CPU takes minutes on the agent loop's second turn, where the
# prompt carries the retrieved passages. 120s was measured to be too short.
_DEFAULT_TIMEOUT_SECONDS = 600

# Ollama varsayılanı 0.8. Ölçüldü: 0.8'de aynı temellendirilmiş istem bazen
# [n] atıf işaretini atlıyor ve atıf kapısı doğru cevabı eliyor. 0'da çıktı
# tekrarlanabilir oluyor ve Türkçe kalitesi de düzeliyor.
_DEFAULT_TEMPERATURE = 0.0


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
    return LLMResponse(
        text=message.get("content") or None,
        tool_calls=calls,
        usage=TokenUsage(payload.get("prompt_eval_count"), payload.get("eval_count")),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else dict(value)


class OllamaClient:
    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        timeout: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = timeout or int(
            os.getenv("LLM_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS))
        )
        self.temperature = (
            temperature
            if temperature is not None
            else float(os.getenv("LLM_TEMPERATURE", str(_DEFAULT_TEMPERATURE)))
        )

    def _post(self, url: str, json: dict[str, Any], timeout: int):
        return requests.post(url, json=json, timeout=timeout)

    def chat(self, messages, tools=None) -> LLMResponse:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }
        if tools:
            body["tools"] = [{"type": "function", "function": schema} for schema in tools]
        response = self._post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
        response.raise_for_status()
        return parse_ollama_response(response.json())


class AnthropicClient:
    def __init__(self, model: str = "claude-opus-5", api_key: str | None = None) -> None:
        import anthropic

        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

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
        usage = getattr(message, "usage", None)
        return LLMResponse(
            text=text or None,
            tool_calls=calls,
            usage=TokenUsage(
                getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)
            ),
        )


class OpenAIClient:
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None) -> None:
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()

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
        usage = getattr(completion, "usage", None)
        return LLMResponse(
            text=choice.content,
            tool_calls=calls,
            usage=TokenUsage(
                getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None)
            ),
        )


class GeminiClient:
    def __init__(self, model: str = "gemini-2.0-flash", api_key: str | None = None) -> None:
        from google import genai

        self.model = model
        self._genai = genai
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def chat(self, messages, tools=None) -> LLMResponse:
        from google.genai import types

        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            types.Content(
                role="model" if m["role"] == "assistant" else "user",
                parts=[types.Part(text=m["content"])],
            )
            for m in messages
            if m["role"] != "system"
        ]

        config: dict[str, Any] = {"temperature": _DEFAULT_TEMPERATURE}
        if system:
            config["system_instruction"] = system
        if tools:
            config["tools"] = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=schema["name"],
                            description=schema["description"],
                            parameters=schema["parameters"],
                        )
                        for schema in tools
                    ]
                )
            ]

        response = self._client.models.generate_content(
            model=self.model, contents=contents, config=types.GenerateContentConfig(**config)
        )

        calls = [
            ToolCall(
                id=str(index),
                name=part.function_call.name,
                arguments=dict(part.function_call.args or {}),
            )
            for index, part in enumerate(_gemini_parts(response))
            if getattr(part, "function_call", None)
        ]
        meta = getattr(response, "usage_metadata", None)
        return LLMResponse(
            text=getattr(response, "text", None) or None,
            tool_calls=calls,
            usage=TokenUsage(
                getattr(meta, "prompt_token_count", None),
                getattr(meta, "candidates_token_count", None),
            ),
        )


def _gemini_parts(response: Any) -> list[Any]:
    """Flatten the first candidate's parts, tolerating an empty response."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    return list(getattr(content, "parts", None) or [])


def get_client(config: Config | None = None, credentials: Any = None) -> LLMClient:
    """Build the configured LLM client, taking its key from the session store first."""
    from src.rag.credentials import resolve_key

    config = config or Config.load()
    provider = config.llm_provider.lower()
    if provider == "ollama":
        return OllamaClient(model=config.llm_model)
    if provider == "anthropic":
        return AnthropicClient(api_key=resolve_key("anthropic", credentials))
    if provider == "openai":
        return OpenAIClient(model=config.llm_model, api_key=resolve_key("openai", credentials))
    if provider == "gemini":
        return GeminiClient(model=config.llm_model, api_key=resolve_key("gemini", credentials))
    raise ValueError(f"unsupported LLM_PROVIDER: {config.llm_provider}")
