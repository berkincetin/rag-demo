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


def load_index(storage_dir: Path, embedding_model: str = _EMBEDDING_MODEL_DEFAULT) -> LoadedIndex:
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
