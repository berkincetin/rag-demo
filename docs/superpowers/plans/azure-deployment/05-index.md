# Task 5: Index with Injected Embedder

**Goal:** Build and load the Chroma + BM25 index using the Azure embedder,
with the E5 `passage:` prefix removed.

**Files:**
- Create: `azure/rag/index.py`
- Create: `azure/tests/test_index.py`

**Interfaces:**
- Consumes: `Embedder` / `AzureOpenAIEmbedder` (Task 2), `Chunk` (Task 4)
- Produces:
  ```python
  COLLECTION_NAME = "documents"

  @dataclass
  class IngestReport:
      chunk_count: int
      per_file: dict[str, int]
      seconds: float

  @dataclass
  class LoadedIndex:
      collection: Any
      bm25: BM25Okapi
      chunks: list[Chunk] = field(default_factory=list)

  def build_index(chunks: list[Chunk], storage_dir: Path,
                  embedder: Embedder) -> IngestReport: ...
  def load_index(storage_dir: Path) -> LoadedIndex: ...
  ```

Note the two deliberate signature changes from `src/rag/index.py`:
`embedder` is injected rather than a model name, and `LoadedIndex` no longer
carries `embedding_model` (the retriever gets its embedder injected too).

---

## 🚨 The change that must not be missed

`src/rag/index.py:76` embeds `f"passage: {chunk.search_text}"`. The `passage:`
prefix is an `intfloat/multilingual-e5-base` training artifact. Sent to
`text-embedding-3-small` it is literal text that dilutes every vector.

**Embed `chunk.search_text` with no prefix.** A test enforces this.

`hnsw:search_ef=200` is kept: ADR-016 recorded that the default of 10 dropped
the true nearest neighbour out of the top-20 in 2 of 8 runs, producing refusals
on valid questions. That finding is about HNSW, not about the embedding model,
so it still applies.

- [ ] **Step 1: Write the failing tests**

Create `azure/tests/test_index.py`:

```python
"""Index construction with an injected embedder."""

from pathlib import Path

import pytest

from azure.rag.index import COLLECTION_NAME, build_index, load_index
from azure.rag.models import Chunk


class SpyEmbedder:
    """Records exactly what text was embedded."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.seen.extend(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        search_text=text,
        citation_label=f"belge.docx — {chunk_id}",
        metadata={"source_file": "belge.docx"},
    )


def test_embeds_search_text_without_e5_prefix(tmp_path):
    """`passage:` is an e5 artifact; it must not reach text-embedding-3-small."""
    embedder = SpyEmbedder()

    build_index([_chunk("c1", "yillik izin")], tmp_path, embedder)

    assert embedder.seen == ["yillik izin"]
    assert not any(text.startswith("passage:") for text in embedder.seen)


def test_report_counts_chunks_per_file(tmp_path):
    chunks = [_chunk("c1", "bir"), _chunk("c2", "iki")]

    report = build_index(chunks, tmp_path, SpyEmbedder())

    assert report.chunk_count == 2
    assert report.per_file == {"belge.docx": 2}
    assert report.seconds >= 0


def test_load_index_round_trips_chunks(tmp_path):
    build_index([_chunk("c1", "bir")], tmp_path, SpyEmbedder())

    loaded = load_index(tmp_path)

    assert [chunk.chunk_id for chunk in loaded.chunks] == ["c1"]
    assert loaded.collection.name == COLLECTION_NAME
    assert loaded.bm25 is not None


def test_rebuild_replaces_the_collection(tmp_path):
    """A second build must not append to the first."""
    build_index([_chunk("c1", "bir")], tmp_path, SpyEmbedder())
    build_index([_chunk("c2", "iki")], tmp_path, SpyEmbedder())

    loaded = load_index(tmp_path)

    assert [chunk.chunk_id for chunk in loaded.chunks] == ["c2"]
    assert loaded.collection.count() == 1
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_index.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'azure.rag.index'`

- [ ] **Step 3: Write the index module**

Create `azure/rag/index.py`:

```python
"""Build and load the hybrid index: Chroma vectors plus a BM25 ranking.

Differs from src/rag/index.py in two ways:

1. The embedder is injected instead of a sentence-transformers model name,
   so this module has no opinion about where vectors come from.
2. No `passage:` prefix. That string is an e5 training artifact; sending it
   to text-embedding-3-small would embed the literal word.
"""

import json
import pickle
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi

from azure.rag.embedder import Embedder
from azure.rag.models import Chunk
from azure.rag.normalize import bm25_tokens

COLLECTION_NAME = "documents"
_BATCH_SIZE = 64

# ADR-016: HNSW's default search_ef of 10 is narrower than the 20 candidates
# the retriever asks for. Measured on this corpus, the true nearest neighbour
# dropped out of the dense top-20 in 2 of 8 runs, pushing the best cosine under
# the gate and making the agent refuse a valid question. This is a property of
# HNSW, not of the embedding model, so it carries over unchanged.
_SEARCH_EF = 200


@dataclass
class IngestReport:
    chunk_count: int
    per_file: dict[str, int]
    seconds: float


@dataclass
class LoadedIndex:
    collection: Any
    bm25: BM25Okapi
    chunks: list[Chunk] = field(default_factory=list)


def build_index(chunks: list[Chunk], storage_dir: Path, embedder: Embedder) -> IngestReport:
    """Embed chunks into Chroma, build BM25, and persist chunk records."""
    started = time.perf_counter()
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(storage_dir / "chroma"))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001 - collection simply does not exist yet
        pass
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "hnsw:search_ef": _SEARCH_EF},
    )

    for start in range(0, len(chunks), _BATCH_SIZE):
        batch = chunks[start : start + _BATCH_SIZE]
        # No prefix: `passage:` is an e5 artifact, not a general convention.
        embeddings = embedder.encode([chunk.search_text for chunk in batch])
        collection.add(
            ids=[chunk.chunk_id for chunk in batch],
            embeddings=embeddings,
            documents=[chunk.text for chunk in batch],
            metadatas=[chunk.metadata for chunk in batch],
        )

    bm25 = BM25Okapi([bm25_tokens(chunk.search_text) for chunk in chunks])
    (storage_dir / "bm25.pkl").write_bytes(pickle.dumps(bm25))

    with (storage_dir / "chunks.jsonl").open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.__dict__, ensure_ascii=False) + "\n")

    per_file = Counter(chunk.metadata["source_file"] for chunk in chunks)
    return IngestReport(
        chunk_count=len(chunks),
        per_file=dict(per_file),
        seconds=time.perf_counter() - started,
    )


def load_index(storage_dir: Path) -> LoadedIndex:
    """Load a previously built index from disk."""
    storage_dir = Path(storage_dir)
    client = chromadb.PersistentClient(path=str(storage_dir / "chroma"))
    collection = client.get_collection(COLLECTION_NAME)
    bm25 = pickle.loads((storage_dir / "bm25.pkl").read_bytes())
    chunks = [
        Chunk(**json.loads(line))
        for line in (storage_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    return LoadedIndex(collection=collection, bm25=bm25, chunks=chunks)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run: `pytest azure/tests/test_index.py -v`
Expected: 4 passed

- [ ] **Step 5: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 6: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 7: Commit**

```bash
git add azure/
git commit -m "feat(azure): add index builder with injected embedder"
```
