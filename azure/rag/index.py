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
