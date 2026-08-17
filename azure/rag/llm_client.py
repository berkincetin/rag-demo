"""Chat via an Azure OpenAI deployment.

Azure differs from the OpenAI API in one way that matters here: `model` is the
*deployment* name, not the model name. They happen to match in this project
(`gpt-4.1-mini`), which makes the distinction easy to forget when the
deployment is later renamed.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from azure.rag.catalog import resolve_chat_model
from azure.rag.config import AzureConfig
from azure.rag.models import TokenUsage
from azure.rag.request_context import emit_token


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

    def __init__(
        self,
        config: AzureConfig | None = None,
        client: Any = None,
        model_id: str | None = None,
    ) -> None:
        self.config = config or AzureConfig.load()
        # Selection is resolved against the catalog *before* any request, so an
        # unknown name can never reach the wire as a deployment name. Raising
        # here (rather than falling back) is deliberate: a silently substituted
        # model would answer with something the caller never asked for.
        self.spec = resolve_chat_model(model_id or self.config.chat_deployment)
        # `agent.py` reads `llm.model` to label metrics and price the run. Without
        # this attribute it falls back to "bilinmiyor", so every recorded run and
        # every cost lookup loses the model identity — measured, not assumed.
        self.model = self.spec.deployment
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
        """Stream the completion, returning the same shape a blocking call did.

        Streaming is an observation layer, not a control-flow change: the agent
        graph still receives one complete LLMResponse. The only difference is
        that text deltas are published to the request's token sink on the way
        through, which is what lets the browser render the answer as it arrives.
        """
        payload: dict[str, Any] = {
            # On Azure this is the deployment name, not the model name.
            "model": self.spec.deployment,
            "messages": messages,
            # Temperature and the token-limit field differ per model and are
            # measured, not assumed — the gpt-5 family rejects both `max_tokens`
            # and `temperature=0` outright. See catalog.py for the probe results.
            **self.spec.payload_limits(),
            "stream": True,
            # Without this the streamed response carries no usage at all and
            # every token count and cost silently becomes null.
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": schema} for schema in tools]

        text_parts: list[str] = []
        # Keyed by the delta's `index`, which is how the API ties the fragments
        # of one tool call together across chunks.
        partial_calls: dict[int, dict[str, Any]] = {}
        usage = TokenUsage()

        for chunk in self._client.chat.completions.create(**payload):
            chunk_usage = getattr(chunk, "usage", None)
            if chunk_usage is not None:
                usage = TokenUsage(
                    getattr(chunk_usage, "prompt_tokens", None),
                    getattr(chunk_usage, "completion_tokens", None),
                )
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            content = getattr(delta, "content", None)
            if content:
                text_parts.append(content)
                emit_token(content)

            for call in getattr(delta, "tool_calls", None) or []:
                slot = partial_calls.setdefault(call.index, {"id": "", "name": "", "arguments": ""})
                if call.id:
                    slot["id"] = call.id
                function = getattr(call, "function", None)
                if function is not None:
                    if getattr(function, "name", None):
                        slot["name"] = function.name
                    if getattr(function, "arguments", None):
                        slot["arguments"] += function.arguments

        calls = [
            ToolCall(
                id=slot["id"],
                name=slot["name"],
                arguments=_as_dict(slot["arguments"] or "{}"),
            )
            for _, slot in sorted(partial_calls.items())
        ]
        return LLMResponse(text="".join(text_parts) or None, tool_calls=calls, usage=usage)


def _as_dict(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else dict(value)
