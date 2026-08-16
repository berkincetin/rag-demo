"""Hybrid retrieval: fusion, filtering, the confidence gate, and no e5 prefix."""

import pytest

from azure.rag.index import LoadedIndex
from azure.rag.models import Chunk, SearchHit
from azure.rag.retriever import Retriever, reciprocal_rank_fusion


class SpyEmbedder:
    def __init__(self) -> None:
        self.seen: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.seen.extend(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeCollection:
    def __init__(self, ids, distances) -> None:
        self.ids, self.distances = ids, distances
        self.queries: list[dict] = []

    def query(self, query_embeddings, n_results, where=None):
        self.queries.append({"where": where, "n_results": n_results})
        return {"ids": [self.ids], "distances": [self.distances]}


class FakeBM25:
    def __init__(self, scores) -> None:
        self.scores = scores

    def get_scores(self, tokens):
        return self.scores


def _chunk(chunk_id: str, source_file: str = "belge.docx") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=f"metin {chunk_id}",
        search_text=f"metin {chunk_id}",
        citation_label=f"{source_file} — {chunk_id}",
        metadata={"source_file": source_file},
    )


def _retriever(embedder=None, ids=("c1", "c2"), distances=(0.1, 0.4), bm25=(9.0, 2.0)):
    chunks = [_chunk("c1"), _chunk("c2")]
    index = LoadedIndex(
        collection=FakeCollection(list(ids), list(distances)),
        bm25=FakeBM25(list(bm25)),
        chunks=chunks,
    )
    return Retriever(index=index, embedder=embedder or SpyEmbedder(), min_cosine=0.5, min_bm25=5.0)


def test_query_is_embedded_without_e5_prefix():
    embedder = SpyEmbedder()

    _retriever(embedder).search("Yıllık İzin")

    assert embedder.seen == ["yillik izin"]
    assert not any(text.startswith("query:") for text in embedder.seen)


def test_thresholds_are_required():
    """No defaults: the e5 values must never leak in implicitly."""
    index = LoadedIndex(collection=FakeCollection([], []), bm25=FakeBM25([]), chunks=[])

    with pytest.raises(TypeError):
        Retriever(index=index, embedder=SpyEmbedder())  # type: ignore[call-arg]


def test_cosine_is_one_minus_distance():
    hits = _retriever(distances=(0.1, 0.4)).search("soru")

    assert hits[0].cosine == pytest.approx(0.9)


def test_gate_requires_both_signals():
    retriever = _retriever()

    strong = [SearchHit(chunk=_chunk("c1"), score=1.0, cosine=0.9, bm25=9.0)]
    weak_lexical = [SearchHit(chunk=_chunk("c1"), score=1.0, cosine=0.9, bm25=1.0)]
    weak_dense = [SearchHit(chunk=_chunk("c1"), score=1.0, cosine=0.1, bm25=9.0)]

    assert retriever.is_confident(strong)
    assert not retriever.is_confident(weak_lexical)
    assert not retriever.is_confident(weak_dense)
    assert not retriever.is_confident([])


def test_reciprocal_rank_fusion_rewards_agreement():
    scores = reciprocal_rank_fusion([["a", "b"], ["a", "c"]])

    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["c"]


def test_source_filter_narrows_the_dense_query():
    retriever = _retriever()
    retriever.index.chunks = [_chunk("c1", "ik_politikasi.docx"), _chunk("c2", "arac.docx")]

    retriever.search("soru", source_filter="arac")

    assert retriever.index.collection.queries[-1]["where"] is not None
