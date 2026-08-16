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
        # `agent.py` reads `llm.model` to label metrics and price the run. Without
        # this attribute it falls back to "bilinmiyor", so every recorded run and
        # every cost lookup loses the model identity — measured, not assumed.
        self.model = self.config.chat_deployment
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
