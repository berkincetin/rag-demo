# Task 6: Hybrid Retriever

**Goal:** Port hybrid retrieval with the `query:` prefix removed and the
embedder injected. Thresholds stay uncalibrated until Task 8.

**Files:**
- Create: `azure/rag/retriever.py`
- Create: `azure/tests/test_retriever.py`

**Interfaces:**
- Consumes: `LoadedIndex` (Task 5), `Embedder` (Task 2), `SearchHit` (Task 4)
- Produces:
  ```python
  def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]: ...

  @dataclass
  class Retriever:
      index: LoadedIndex
      embedder: Embedder
      min_cosine: float
      min_bm25: float

      def search(self, query: str, top_k: int = 5,
                 source_filter: str | None = None) -> list[SearchHit]: ...
      def is_confident(self, hits: list[SearchHit]) -> bool: ...
  ```

`min_cosine` and `min_bm25` are **required** here — unlike
`src/rag/retriever.py`, they have no defaults. Defaulting them would let the
invalid e5 values leak in silently.

---

## 🚨 Two changes that must not be missed

1. `src/rag/retriever.py:37` encodes `f"query: {folded_query}"`. **Drop the
   prefix** — same reasoning as Task 5.
2. `src/rag/retriever.py:25-26` defaults `min_cosine=0.80`, `min_bm25=5.0`.
   Those are e5 numbers. **No defaults here.**

The `is_confident` AND-gate logic is kept: Part 1 measured that either signal
alone is insufficient — off-topic questions reached cosine 0.813 (above the
weakest valid question at 0.811) and BM25 8.25. Whether that still holds for
`text-embedding-3-small` is exactly what Task 8 measures.

- [ ] **Step 1: Write the failing tests**

Create `azure/tests/test_retriever.py`:

```python
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
    return Retriever(
        index=index, embedder=embedder or SpyEmbedder(), min_cosine=0.5, min_bm25=5.0
    )


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
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_retriever.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.retriever'`

- [ ] **Step 3: Write the retriever**

Create `azure/rag/retriever.py` by copying `src/rag/retriever.py` and applying
exactly these changes:

- Import `Embedder` from `azure.rag.embedder`; import the rest from `azure.rag.*`
- Add `embedder: Embedder` as a dataclass field
- Remove the defaults from `min_cosine` and `min_bm25` (keep the type
  annotations, drop `= 0.80` and `= 5.0`)
- Replace `_encode_query` with:

```python
    def _encode_query(self, folded_query: str) -> list[float]:
        # No `query:` prefix: that is an e5 training artifact, and
        # text-embedding-3-small would embed it as literal text.
        return self.embedder.encode([folded_query])[0]
```

- Delete the `self._model = None` line from `__post_init__`
- Update the `is_confident` docstring to state that the thresholds are
  measured in Task 8 against `text-embedding-3-small`, and that the numbers
  quoted in the original docstring (0.813 / 0.811 / 8.25) were e5
  measurements

Everything else — `search`, `_allowed_files`, `_allowed_ids`, `_dense`,
`_lexical`, `reciprocal_rank_fusion`, `_CANDIDATES = 20`, `_RRF_K = 60` —
is copied unchanged.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest azure/tests/test_retriever.py -v`
Expected: 6 passed

- [ ] **Step 5: Verify no e5 artifacts survive anywhere**

```bash
grep -rn "passage:\|query:\|sentence_transformers\|SentenceTransformer" azure/rag/
```

Expected: **no output**. Any hit is a bug — fix it before committing.

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
git commit -m "feat(azure): add hybrid retriever with injected embedder"
```
