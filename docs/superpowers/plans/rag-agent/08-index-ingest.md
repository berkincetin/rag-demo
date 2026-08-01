# Task 8: Index builder and ingest entry point

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 7](07-chunker.md)
**Next:** [Task 9](09-retriever.md)

---

**Files:**
- Create: `src/rag/index.py`, `scripts/ingest.py`
- Test: `tests/test_index.py`

**Interfaces:**
- Consumes: `Chunk`, `Config`, `chunk_sections`, `load_all`
- Produces: `build_index(chunks, storage_dir, embedding_model) -> IngestReport`, `load_index(storage_dir) -> LoadedIndex`, dataclass `LoadedIndex` with fields `collection`, `bm25`, `chunks: list[Chunk]`, and `IngestReport` with `chunk_count: int`, `per_file: dict[str, int]`, `seconds: float`

Embedding uses the e5 prefix scheme: documents are embedded as `"passage: " + search_text`, queries as `"query: " + folded_query` (Task 9). Batch size 64.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_index.py
import json
from pathlib import Path

import pytest

from src.rag.chunker import chunk_sections
from src.rag.index import build_index, load_index
from src.rag.loaders import load_all
from src.rag.models import RawSection


def _tiny_corpus() -> list:
    sections = [
        RawSection(
            source_file="a.xlsx",
            doc_type="xlsx",
            text="Yıllık izin talebi HRPortal üzerinden yapılır.",
            sheet="Genel SSS",
            row=4,
        ),
        RawSection(
            source_file="b.xlsx",
            doc_type="xlsx",
            text="Havuz aracı FleetApp üzerinden talep edilir.",
            sheet="Genel SSS",
            row=5,
        ),
    ]
    return chunk_sections(sections)


@pytest.mark.integration
def test_build_index_writes_all_three_artifacts(tmp_path):
    report = build_index(_tiny_corpus(), tmp_path)

    assert (tmp_path / "chroma").exists()
    assert (tmp_path / "bm25.pkl").exists()
    assert (tmp_path / "chunks.jsonl").exists()
    assert report.chunk_count == 2


@pytest.mark.integration
def test_chunks_jsonl_round_trips_text_and_citation(tmp_path):
    build_index(_tiny_corpus(), tmp_path)

    lines = (tmp_path / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]

    assert len(records) == 2
    assert all(record["citation_label"] for record in records)
    assert any("HRPortal" in record["text"] for record in records)


@pytest.mark.integration
def test_rebuilding_is_idempotent(tmp_path):
    build_index(_tiny_corpus(), tmp_path)
    second = build_index(_tiny_corpus(), tmp_path)

    loaded = load_index(tmp_path)

    assert second.chunk_count == 2
    assert len(loaded.chunks) == 2
    assert loaded.collection.count() == 2


@pytest.mark.integration
def test_report_counts_chunks_per_source_file(tmp_path):
    report = build_index(_tiny_corpus(), tmp_path)

    assert report.per_file == {"a.xlsx": 1, "b.xlsx": 1}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_index.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.index'`

- [ ] **Step 3: Write minimal `src/rag/index.py`**

```python
"""Build and load the hybrid index: Chroma vectors plus a BM25 ranking."""

import json
import pickle
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi

from src.rag.models import Chunk

COLLECTION_NAME = "documents"
_BATCH_SIZE = 64
_EMBEDDING_MODEL_DEFAULT = "intfloat/multilingual-e5-base"


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
    embedding_model: str = _EMBEDDING_MODEL_DEFAULT


def _encoder(model_name: str):
    """Import lazily so unit tests that never embed stay fast."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def build_index(
    chunks: list[Chunk],
    storage_dir: Path,
    embedding_model: str = _EMBEDDING_MODEL_DEFAULT,
) -> IngestReport:
    """Embed chunks into Chroma, build BM25, and persist chunk records."""
    started = time.perf_counter()
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(storage_dir / "chroma"))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:  # noqa: BLE001 - collection simply does not exist yet
        pass
    collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

    model = _encoder(embedding_model)
    for start in range(0, len(chunks), _BATCH_SIZE):
        batch = chunks[start : start + _BATCH_SIZE]
        embeddings = model.encode(
            [f"passage: {chunk.search_text}" for chunk in batch],
            normalize_embeddings=True,
        ).tolist()
        collection.add(
            ids=[chunk.chunk_id for chunk in batch],
            embeddings=embeddings,
            documents=[chunk.text for chunk in batch],
            metadatas=[chunk.metadata for chunk in batch],
        )

    bm25 = BM25Okapi([chunk.search_text.split() for chunk in chunks])
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


def load_index(
    storage_dir: Path, embedding_model: str = _EMBEDDING_MODEL_DEFAULT
) -> LoadedIndex:
    """Load a previously built index from disk."""
    storage_dir = Path(storage_dir)
    client = chromadb.PersistentClient(path=str(storage_dir / "chroma"))
    collection = client.get_collection(COLLECTION_NAME)
    bm25 = pickle.loads((storage_dir / "bm25.pkl").read_bytes())
    chunks = [
        Chunk(**json.loads(line))
        for line in (storage_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    return LoadedIndex(
        collection=collection, bm25=bm25, chunks=chunks, embedding_model=embedding_model
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_index.py -m integration -v --no-cov`
Expected: PASS (4 passed). First run downloads ~1.1 GB of model weights.

- [ ] **Step 5: Write `scripts/ingest.py`**

```python
"""Build the search index from the documents in the data directory."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rag.chunker import chunk_sections  # noqa: E402
from src.rag.config import Config  # noqa: E402
from src.rag.index import build_index  # noqa: E402
from src.rag.loaders import load_all  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    config = Config.load()

    sections = load_all(config.data_dir)
    chunks = chunk_sections(sections, config.chunk_max_chars, config.chunk_overlap)
    report = build_index(chunks, config.storage_dir, config.embedding_model)

    print(f"\nSections: {len(sections)}  Chunks: {report.chunk_count}")
    for name, count in sorted(report.per_file.items()):
        print(f"  {count:>4}  {name}")
    print(f"Completed in {report.seconds:.1f}s -> {config.storage_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run ingest against the real corpus and read the output**

Run: `python scripts/ingest.py`
Expected: prints a per-file table, chunk count between 250 and 450, all 6 files listed, completes in under 3 minutes with the model cached.

- [ ] **Step 7: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/index.py scripts/ingest.py tests/test_index.py
git commit -m "feat(index): add Chroma and BM25 index builder with ingest script"
```
