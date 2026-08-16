"""Embeddings via Azure OpenAI.

Replaces sentence-transformers entirely: no torch, no local model download,
no 1.1 GB image layer.

Two behaviours are load-bearing and must not be "simplified" away:

1. Vectors are L2-normalized here. Chroma uses `hnsw:space=cosine` and the
   retriever reads similarity as `1.0 - distance`, which is only the cosine
   for unit vectors. Azure OpenAI does not return normalized vectors.
2. No `passage:` / `query:` prefix is ever added. Those strings are
   `intfloat/multilingual-e5-base` training artifacts. Sent to
   text-embedding-3-small they are just literal tokens that dilute the
   embedding.
"""

import math
import time
from typing import Any, Protocol

from azure.rag.config import AzureConfig

# Azure OpenAI accepts far larger batches, but the per-request payload limit
# is what bites first on long chunks. 64 matches the old ingest batch size.
_BATCH_SIZE = 64
_MAX_RETRIES = 4
_BACKOFF_SECONDS = 2.0


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class AzureOpenAIEmbedder:
    """Batching, retrying embedder over an Azure OpenAI deployment."""

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

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Embed `texts`, returning unit vectors in the same order."""
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            response = self._create_with_retry(batch)
            vectors.extend(_normalize(item.embedding) for item in response.data)
        return vectors

    def _create_with_retry(self, batch: list[str]) -> Any:
        """Retry on transient failures; 429 is expected under GlobalStandard."""
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return self._client.embeddings.create(
                    model=self.config.embedding_deployment, input=batch
                )
            except Exception as error:  # noqa: BLE001 - re-raised after retries
                last_error = error
                if attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(_BACKOFF_SECONDS * (2**attempt))
        raise RuntimeError(
            f"embedding request failed after {_MAX_RETRIES} attempts"
        ) from last_error


def _normalize(vector: list[float]) -> list[float]:
    """Scale to unit length; a zero vector is returned unchanged."""
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0.0:
        return list(vector)
    return [value / length for value in vector]
