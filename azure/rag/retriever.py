"""Hybrid retrieval: dense vectors and BM25, fused by reciprocal rank."""

from dataclasses import dataclass

from azure.rag.embedder import Embedder
from azure.rag.index import LoadedIndex
from azure.rag.models import Chunk, SearchHit
from azure.rag.normalize import bm25_tokens, fold_tr

_CANDIDATES = 20
_RRF_K = 60


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = _RRF_K) -> dict[str, float]:
    """Fuse ranked id lists. Score is the sum of 1 / (k + rank) across rankings."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


@dataclass
class Retriever:
    index: LoadedIndex
    embedder: Embedder
    min_cosine: float
    min_bm25: float

    def __post_init__(self) -> None:
        self._by_id: dict[str, Chunk] = {chunk.chunk_id: chunk for chunk in self.index.chunks}

    def _encode_query(self, folded_query: str) -> list[float]:
        # No `query:` prefix: that is an e5 training artifact, and
        # text-embedding-3-small would embed it as literal text.
        return self.embedder.encode([folded_query])[0]

    def search(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> list[SearchHit]:
        """Return the top_k chunks for `query`, fused from both rankers."""
        folded = fold_tr(query)
        allowed_files = self._allowed_files(source_filter)
        allowed_ids = self._allowed_ids(allowed_files)

        dense_ids, cosines = self._dense(folded, allowed_files)
        lexical_ids, bm25_scores = self._lexical(folded, allowed_ids)

        fused = reciprocal_rank_fusion([dense_ids, lexical_ids])
        ordered = sorted(fused.items(), key=lambda item: item[1], reverse=True)

        hits = [
            SearchHit(
                chunk=self._by_id[chunk_id],
                score=score,
                cosine=cosines.get(chunk_id, 0.0),
                bm25=bm25_scores.get(chunk_id, 0.0),
            )
            for chunk_id, score in ordered
            if chunk_id in self._by_id
        ]
        return hits[:top_k]

    def is_confident(self, hits: list[SearchHit]) -> bool:
        """True when both rankers back the best hit.

        `min_cosine` and `min_bm25` are measured in Task 8 against
        text-embedding-3-small; they have no defaults here so an invalid
        value cannot leak in silently. The original docstring's numbers
        (off-topic cosine 0.813, above the weakest valid question's 0.811;
        off-topic BM25 8.25) were measurements against e5-base and do not
        necessarily hold for this embedding model — Task 8 re-measures them.
        """
        if not hits:
            return False
        best = hits[0]
        return best.cosine >= self.min_cosine and best.bm25 >= self.min_bm25

    def _allowed_files(self, source_filter: str | None) -> set[str] | None:
        """Source files whose name contains `source_filter`, or None for no filter."""
        if source_filter is None:
            return None
        needle = fold_tr(source_filter)
        return {
            chunk.metadata["source_file"]
            for chunk in self.index.chunks
            if needle in fold_tr(chunk.metadata["source_file"])
        }

    def _allowed_ids(self, allowed_files: set[str] | None) -> set[str] | None:
        if allowed_files is None:
            return None
        return {
            chunk.chunk_id
            for chunk in self.index.chunks
            if chunk.metadata["source_file"] in allowed_files
        }

    def _dense(
        self, folded_query: str, allowed_files: set[str] | None
    ) -> tuple[list[str], dict[str, float]]:
        where = {"source_file": {"$in": sorted(allowed_files)}} if allowed_files else None
        result = self.index.collection.query(
            query_embeddings=[self._encode_query(folded_query)],
            n_results=_CANDIDATES,
            where=where,
        )
        ids = result["ids"][0]
        distances = result.get("distances", [[]])[0]
        cosines = {
            chunk_id: 1.0 - distance for chunk_id, distance in zip(ids, distances, strict=False)
        }
        return ids, cosines

    def _lexical(
        self, folded_query: str, allowed: set[str] | None
    ) -> tuple[list[str], dict[str, float]]:
        scores = self.index.bm25.get_scores(bm25_tokens(folded_query))
        pairs = [
            (chunk.chunk_id, float(score))
            for chunk, score in zip(self.index.chunks, scores, strict=False)
            if allowed is None or chunk.chunk_id in allowed
        ]
        pairs.sort(key=lambda item: item[1], reverse=True)
        top = pairs[:_CANDIDATES]
        return [chunk_id for chunk_id, _ in top], dict(top)
