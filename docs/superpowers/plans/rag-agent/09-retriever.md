# Task 9: Hybrid retriever with RRF fusion and confidence gate

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 8](08-index-ingest.md)
**Next:** [Task 10](10-tools-prompts.md)

---

**Files:**
- Create: `src/rag/retriever.py`
- Test: `tests/test_retriever.py`

**Interfaces:**
- Consumes: `LoadedIndex`, `SearchHit`, `fold_tr`
- Produces: class `Retriever(index: LoadedIndex, min_cosine: float = 0.72)` with methods `search(query: str, top_k: int = 5, source_filter: str | None = None) -> list[SearchHit]` and `is_confident(hits: list[SearchHit]) -> bool`; module function `reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]`

RRF is used because cosine similarity and BM25 scores live on different scales; rank-based fusion needs no normalization and no weight tuning (ADR-004).

- [ ] **Step 1: Write the failing unit test for the fusion function**

```python
# tests/test_retriever.py
from src.rag.retriever import reciprocal_rank_fusion


def test_fusion_ranks_a_chunk_found_by_both_rankers_first():
    dense = ["a", "b", "c"]
    lexical = ["c", "a", "d"]

    scores = reciprocal_rank_fusion([dense, lexical])

    assert max(scores, key=scores.get) == "a"


def test_fusion_score_matches_the_reciprocal_rank_formula():
    scores = reciprocal_rank_fusion([["a"], ["a"]], k=60)

    assert scores["a"] == pytest.approx(2 / 61)


def test_fusion_includes_chunks_seen_by_only_one_ranker():
    scores = reciprocal_rank_fusion([["a"], ["b"]])

    assert set(scores) == {"a", "b"}


def test_fusion_of_no_rankings_is_empty():
    assert reciprocal_rank_fusion([]) == {}
```

Add `import pytest` at the top of the file.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retriever.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.retriever'`

- [ ] **Step 3: Write minimal `src/rag/retriever.py`**

```python
"""Hybrid retrieval: dense vectors and BM25, fused by reciprocal rank."""

from dataclasses import dataclass

from src.rag.index import LoadedIndex
from src.rag.models import Chunk, SearchHit
from src.rag.normalize import fold_tr

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
    min_cosine: float = 0.72

    def __post_init__(self) -> None:
        self._by_id: dict[str, Chunk] = {chunk.chunk_id: chunk for chunk in self.index.chunks}
        self._model = None

    def _encode_query(self, folded_query: str) -> list[float]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.index.embedding_model)
        return self._model.encode(
            [f"query: {folded_query}"], normalize_embeddings=True
        )[0].tolist()

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
        """True when the best hit clears the cosine floor or is a strong lexical match."""
        if not hits:
            return False
        best = hits[0]
        return best.cosine >= self.min_cosine or best.bm25 >= self._bm25_floor()

    def _bm25_floor(self) -> float:
        return 8.0

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
        cosines = {chunk_id: 1.0 - distance for chunk_id, distance in zip(ids, distances)}
        return ids, cosines

    def _lexical(
        self, folded_query: str, allowed: set[str] | None
    ) -> tuple[list[str], dict[str, float]]:
        scores = self.index.bm25.get_scores(folded_query.split())
        pairs = [
            (chunk.chunk_id, float(score))
            for chunk, score in zip(self.index.chunks, scores)
            if allowed is None or chunk.chunk_id in allowed
        ]
        pairs.sort(key=lambda item: item[1], reverse=True)
        top = pairs[:_CANDIDATES]
        return [chunk_id for chunk_id, _ in top], dict(top)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_retriever.py -v --no-cov`
Expected: PASS (4 passed)

- [ ] **Step 5: Write the failing integration tests — the four retrieval probes**

These are the accuracy contract for the whole system. Each probe targets a distinct failure mode.

```python
# append to tests/test_retriever.py
from pathlib import Path

import pytest

from src.rag.index import load_index
from src.rag.retriever import Retriever

STORAGE = Path("storage")


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    if not (STORAGE / "chunks.jsonl").exists():
        pytest.skip("index not built; run python scripts/ingest.py")
    return Retriever(load_index(STORAGE))


@pytest.mark.integration
def test_turkish_query_finds_the_ascii_folded_hr_document(retriever):
    # Proves the fold_tr fix: the query is spelled correctly, the document is not.
    hits = retriever.search("İnsan Kaynakları yıllık izin", top_k=3)

    sources = [hit.chunk.metadata["source_file"] for hit in hits]

    assert any("ik_surecleri" in source or "calisan_sss" in source for source in sources)


@pytest.mark.integration
def test_document_code_is_matched_exactly(retriever):
    # Proves BM25 pulls its weight: dense embeddings do not reliably match codes.
    hits = retriever.search("OPS-PRO-003", top_k=3)

    assert "arac_kullanim" in hits[0].chunk.metadata["source_file"]


@pytest.mark.integration
def test_drug_section_query_lands_on_the_right_section(retriever):
    hits = retriever.search("Aksef kontrendikasyonları", top_k=3)

    assert "Aksef" in hits[0].chunk.metadata["source_file"]
    assert hits[0].chunk.metadata["section_id"].startswith("4.3")


@pytest.mark.integration
def test_product_lookup_finds_the_taxonomy_row(retriever):
    hits = retriever.search("Vitatin95 ürün müdürü", top_k=3)

    assert any("Vitatin95" in hit.chunk.text for hit in hits)


@pytest.mark.integration
def test_source_filter_restricts_results_to_one_document(retriever):
    hits = retriever.search("pozoloji", top_k=5, source_filter="Duxet")

    assert hits
    assert all("Duxet" in hit.chunk.metadata["source_file"] for hit in hits)


@pytest.mark.integration
def test_off_topic_question_is_not_confident(retriever):
    hits = retriever.search("Bugün hava nasıl olacak?", top_k=5)

    assert not retriever.is_confident(hits)


@pytest.mark.integration
def test_in_domain_question_is_confident(retriever):
    hits = retriever.search("Yıllık izin talebimi nasıl yaparım?", top_k=5)

    assert retriever.is_confident(hits)
```

- [ ] **Step 6: Run integration tests and calibrate the thresholds**

Run: `pytest tests/test_retriever.py -m integration -v --no-cov`
Expected: PASS (7 passed).

If the confidence tests fail, print the actual `cosine` and `bm25` values for the eight demo questions (PRD §7) and five off-topic questions, then pick `min_cosine` and the BM25 floor so that every valid question clears the gate and no off-topic one does. Record the chosen values and the observed score distribution in `MEMORY.md` — they go into the README.

- [ ] **Step 7: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/retriever.py tests/test_retriever.py
git commit -m "feat(retriever): add hybrid BM25 and dense search with RRF fusion"
```
