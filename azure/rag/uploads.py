"""In-memory, expiring store for documents a user uploaded to one conversation.

Nothing here reaches disk. The uploaded file is parsed inside the request that
carried it and then discarded; only chunks and their vectors survive, and only
until the TTL expires. That is the whole point: uploads must not accumulate on
the server.

Per-replica, like the rate limiter in `api.py`. Under multi-replica scale a
conversation could land on a replica that never saw its upload; the front-end
reconciles by listing documents whenever the conversation changes.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from azure.rag.chunker import chunk_sections
from azure.rag.loaders import load_file
from azure.rag.models import Chunk

MAX_FILE_BYTES = 10 * 1024 * 1024
_DEFAULT_TTL_SECONDS = 3600
_DEFAULT_MAX_DOCS = 5
_DEFAULT_MAX_CHUNKS = 300


class UploadLimitError(Exception):
    """A per-conversation limit would be exceeded."""


@dataclass
class UploadedDoc:
    """One uploaded document: its chunks and their unit vectors, in order."""

    filename: str
    chunks: list[Chunk]
    vectors: list[list[float]]


@dataclass
class _Entry:
    docs: list[UploadedDoc] = field(default_factory=list)
    touched_at: float = 0.0


class UploadStore:
    """Documents per (session, conversation), evicted after `ttl_seconds` idle."""

    def __init__(
        self,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        max_docs: int = _DEFAULT_MAX_DOCS,
        max_chunks: int = _DEFAULT_MAX_CHUNKS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_docs = max_docs
        self.max_chunks = max_chunks
        self._clock = clock or time.monotonic
        self._entries: dict[str, _Entry] = {}

    def sweep(self) -> None:
        """Drop every entry that has been idle longer than the TTL."""
        now = self._clock()
        expired = [
            key for key, entry in self._entries.items() if now - entry.touched_at > self.ttl_seconds
        ]
        for key in expired:
            del self._entries[key]

    def _live_entry(self, key: str) -> _Entry | None:
        self.sweep()
        return self._entries.get(key)

    def add(self, key: str, doc: UploadedDoc) -> None:
        """Store `doc`, replacing any earlier upload with the same filename.

        Limits are checked against the list *after* replacement, so re-uploading
        a file the conversation already holds never trips the document cap.
        """
        entry = self._entries.setdefault(key, _Entry())
        kept = [existing for existing in entry.docs if existing.filename != doc.filename]

        if len(kept) + 1 > self.max_docs:
            raise UploadLimitError(f"Bir sohbete en fazla {self.max_docs} belge yüklenebilir.")
        total_chunks = sum(len(existing.chunks) for existing in kept) + len(doc.chunks)
        if total_chunks > self.max_chunks:
            raise UploadLimitError(
                f"Bu sohbetteki toplam parça sayısı {self.max_chunks} sınırını aşıyor."
            )

        entry.docs = [*kept, doc]
        entry.touched_at = self._clock()

    def get(self, key: str) -> list[UploadedDoc]:
        """Documents for `key`, refreshing its idle timer."""
        entry = self._live_entry(key)
        if entry is None:
            return []
        entry.touched_at = self._clock()
        return list(entry.docs)

    def remove(self, key: str, filename: str) -> list[UploadedDoc]:
        """Drop one document, returning what remains."""
        entry = self._live_entry(key)
        if entry is None:
            return []
        entry.docs = [doc for doc in entry.docs if doc.filename != filename]
        entry.touched_at = self._clock()
        return list(entry.docs)

    def clear(self, key: str) -> None:
        self._entries.pop(key, None)


def build_uploaded_doc(path: Path, embedder: Any) -> UploadedDoc:
    """Parse, chunk and embed one file. The caller deletes `path` afterwards."""
    sections = load_file(path)
    chunks = chunk_sections(sections)
    vectors = embedder.encode([chunk.search_text for chunk in chunks])
    return UploadedDoc(filename=Path(path).name, chunks=chunks, vectors=vectors)
