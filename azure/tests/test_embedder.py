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
    """Order must survive the split into batches."""
    client = FakeClient()
    # Deliberately more than _BATCH_SIZE so the split actually happens.
    texts = ["x" * n for n in range(1, 100)]

    vectors = _embedder(client).encode(texts)

    assert len(vectors) == 99
    assert len(client.embeddings.calls) == 2  # 99 texts at 64 per batch
    # The fake encodes input length in the first component before
    # normalization; after normalizing a [len, 0, 3] vector, that component
    # increases monotonically with length, so ordering is checkable.
    firsts = [vector[0] for vector in vectors]
    assert firsts == sorted(firsts)
    # And the flattened request order matches the input order exactly.
    sent = [text for call in client.embeddings.calls for text in call]
    assert sent == texts


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
