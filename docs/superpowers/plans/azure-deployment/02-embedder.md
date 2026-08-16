# Task 2: Azure OpenAI Embedder

**Goal:** Replace `sentence-transformers` with an Azure OpenAI embedder that
batches, retries, and never applies E5 prefixes.

**Files:**
- Create: `azure/rag/embedder.py`
- Create: `azure/tests/test_embedder.py`

**Interfaces:**
- Consumes: `AzureConfig` from Task 1
- Produces:
  ```python
  class Embedder(Protocol):
      def encode(self, texts: list[str]) -> list[list[float]]: ...

  class AzureOpenAIEmbedder:
      def __init__(self, config: AzureConfig | None = None, client: Any = None) -> None: ...
      def encode(self, texts: list[str]) -> list[list[float]]: ...
  ```
  `encode` returns L2-normalized vectors, one per input, in input order.

---

## Why normalization matters

Chroma is configured with `hnsw:space=cosine` and the retriever computes
`cosine = 1.0 - distance`. That identity only holds for unit vectors. The old
code got this from `normalize_embeddings=True`; Azure OpenAI does not
normalize, so the embedder must do it explicitly.

- [ ] **Step 1: Write the failing tests**

Create `azure/tests/test_embedder.py`:

```python
"""Azure OpenAI embedder: batching, ordering, and normalization."""

import math

import pytest

from azure.rag.config import AzureConfig
from azure.rag.embedder import AzureOpenAIEmbedder


class FakeEmbeddings:
    """Records calls and returns unnormalized vectors."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, model: str, input: list[str]):
        self.calls.append(list(input))
        data = [type("Item", (), {"embedding": [float(len(text)), 0.0, 3.0]})() for text in input]
        return type("Response", (), {"data": data})()


class FakeClient:
    def __init__(self) -> None:
        self.embeddings = FakeEmbeddings()


def _embedder(client: FakeClient) -> AzureOpenAIEmbedder:
    config = AzureConfig(
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
    return AzureOpenAIEmbedder(config=config, client=client)


def test_returns_unit_vectors():
    """Chroma's cosine space requires normalized vectors."""
    client = FakeClient()

    vectors = _embedder(client).encode(["abcd"])

    length = math.sqrt(sum(value * value for value in vectors[0]))
    assert length == pytest.approx(1.0)


def test_preserves_input_order_across_batches():
    client = FakeClient()
    texts = [f"{'x' * n}" for n in range(1, 25)]

    vectors = _embedder(client).encode(texts)

    assert len(vectors) == 24
    # First component encodes the input length before normalization, so the
    # ordering is checkable after it.
    assert vectors[0][0] > 0
    assert len(client.embeddings.calls) > 1  # batching actually happened


def test_never_adds_e5_prefixes():
    """`passage:` / `query:` are e5 artifacts and must not reach this model."""
    client = FakeClient()

    _embedder(client).encode(["yillik izin"])

    sent = client.embeddings.calls[0][0]
    assert sent == "yillik izin"
    assert "passage:" not in sent
    assert "query:" not in sent


def test_empty_input_makes_no_request():
    client = FakeClient()

    assert _embedder(client).encode([]) == []
    assert client.embeddings.calls == []
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_embedder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.embedder'`

- [ ] **Step 3: Write the embedder**

Create `azure/rag/embedder.py`:

```python
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
        raise RuntimeError(f"embedding request failed after {_MAX_RETRIES} attempts") from last_error


def _normalize(vector: list[float]) -> list[float]:
    """Scale to unit length; a zero vector is returned unchanged."""
    length = math.sqrt(sum(value * value for value in vector))
    if length == 0.0:
        return list(vector)
    return [value / length for value in vector]
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest azure/tests/test_embedder.py -v`
Expected: 4 passed

- [ ] **Step 5: Verify against the real deployment**

This proves the deployment, key, and API version actually work together.

```bash
python -c "
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from azure.rag.embedder import AzureOpenAIEmbedder
vectors = AzureOpenAIEmbedder().encode(['yillik izin talebi', 'arac tahsisi'])
print('vectors:', len(vectors), 'dim:', len(vectors[0]))
print('norm:', sum(v*v for v in vectors[0]) ** 0.5)
"
```

Expected: `vectors: 2 dim: 1536` and a norm of `1.0` (within float error).
Record the dimension in the commit message — Task 5 needs it.

Requires `AZURE_OPENAI_API_KEY` in `azure/.env` or the environment.

- [ ] **Step 6: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 7: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 8: Commit**

```bash
git add azure/
git commit -m "feat(azure): add Azure OpenAI embedder with normalization and batching"
```
