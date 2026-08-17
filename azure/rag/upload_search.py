"""Searching a conversation's uploaded documents, fused with the corpus.

The corpus index is a persistent Chroma collection plus a prebuilt BM25 model.
Inserting a user's ad-hoc document into either would mutate state shared by
every session, so uploads get their own tiny ranking pass and the two result
lists are fused instead.

Scale mismatch, deliberately handled: BM25 over a handful of uploaded chunks
has a different IDF basis than BM25 over the 276-chunk corpus, so the two BM25
numbers are not comparable. The gate therefore judges uploaded hits on cosine
alone — cosines of unit vectors from the same embedding model *are* comparable
— while corpus hits keep the measured two-signal rule untouched.
"""

from typing import Any

from rank_bm25 import BM25Okapi

from azure.rag.models import SearchHit
from azure.rag.normalize import bm25_tokens, fold_tr
from azure.rag.retriever import reciprocal_rank_fusion
from azure.rag.uploads import UploadedDoc

_CANDIDATES = 20


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


def search_uploads(
    docs: list[UploadedDoc], query: str, query_vector: list[float], top_k: int = 5
) -> list[SearchHit]:
    """Rank uploaded chunks with the same hybrid shape the corpus uses."""
    chunks = [chunk for doc in docs for chunk in doc.chunks]
    vectors = [vector for doc in docs for vector in doc.vectors]
    if not chunks:
        return []

    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    cosines = {
        chunk.chunk_id: _dot(query_vector, vector)
        for chunk, vector in zip(chunks, vectors, strict=False)
    }
    dense_ids = sorted(cosines, key=lambda chunk_id: cosines[chunk_id], reverse=True)[:_CANDIDATES]

    scores = BM25Okapi([bm25_tokens(chunk.search_text) for chunk in chunks]).get_scores(
        bm25_tokens(fold_tr(query))
    )
    bm25_scores = {
        chunk.chunk_id: float(score) for chunk, score in zip(chunks, scores, strict=False)
    }
    lexical_ids = sorted(bm25_scores, key=lambda chunk_id: bm25_scores[chunk_id], reverse=True)[
        :_CANDIDATES
    ]

    fused = reciprocal_rank_fusion([dense_ids, lexical_ids])
    ordered = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    return [
        SearchHit(
            chunk=by_id[chunk_id],
            score=score,
            cosine=cosines.get(chunk_id, 0.0),
            bm25=bm25_scores.get(chunk_id, 0.0),
        )
        for chunk_id, score in ordered
    ][:top_k]


class UploadAwareRetriever:
    """A Retriever-shaped facade that also searches this conversation's uploads.

    Presents exactly the surface `ToolBox` and `graph.py` consume, so neither
    needs to know uploads exist.
    """

    def __init__(self, base: Any, key: str, store: Any) -> None:
        self.base = base
        self.key = key
        self.store = store
        # Mirrored so anything reading the base's attributes keeps working.
        self.index = base.index
        self.embedder = base.embedder
        self.min_cosine = base.min_cosine
        self.min_bm25 = base.min_bm25
        self._upload_ids: set[str] = set()

    def search(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[SearchHit]:
        corpus_hits = self.base.search(query, top_k, source_filter)
        docs = self.store.get(self.key)
        if not docs:
            self._upload_ids = set()
            return corpus_hits

        query_vector = self.embedder.encode([fold_tr(query)])[0]
        upload_hits = search_uploads(docs, query, query_vector, top_k)
        self._upload_ids = {hit.chunk.chunk_id for hit in upload_hits}

        merged = reciprocal_rank_fusion(
            [
                [hit.chunk.chunk_id for hit in corpus_hits],
                [hit.chunk.chunk_id for hit in upload_hits],
            ]
        )
        by_id = {hit.chunk.chunk_id: hit for hit in [*corpus_hits, *upload_hits]}
        ordered = sorted(merged.items(), key=lambda item: item[1], reverse=True)
        return [by_id[chunk_id] for chunk_id, _ in ordered if chunk_id in by_id][:top_k]

    def is_confident(self, hits: list[SearchHit]) -> bool:
        """Pass when the corpus rule passes, or an uploaded chunk is close enough.

        The base gate only ever sees corpus hits: its thresholds were measured
        against the corpus's BM25 distribution, which uploaded chunks do not
        share.
        """
        corpus_hits = [hit for hit in hits if hit.chunk.chunk_id not in self._upload_ids]
        if self.base.is_confident(corpus_hits):
            return True
        upload_hits = [hit for hit in hits if hit.chunk.chunk_id in self._upload_ids]
        return any(hit.cosine >= self.min_cosine for hit in upload_hits)
