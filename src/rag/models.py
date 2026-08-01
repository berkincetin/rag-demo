"""Core data structures shared across the ingest and retrieval pipeline."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawSection:
    """A logical document section produced by a loader, before chunking."""

    source_file: str
    doc_type: str
    text: str
    section_id: str | None = None
    section_title: str | None = None
    section_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    sheet: str | None = None
    row: int | None = None


@dataclass
class Chunk:
    """An indexable unit. `text` is displayed, `search_text` is searched."""

    chunk_id: str
    text: str
    search_text: str
    citation_label: str
    metadata: dict[str, Any]


@dataclass
class SearchHit:
    """One retrieval result with its fused and per-ranker scores."""

    chunk: Chunk
    score: float
    cosine: float
    bm25: float


@dataclass
class Answer:
    """Final agent output."""

    text: str
    citations: list[str] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
