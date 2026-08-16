"""Core data structures shared across the ingest and retrieval pipeline.

Copied verbatim from `src/rag/models.py`.
"""

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


@dataclass(frozen=True)
class TokenUsage:
    """Tokens a provider reported for one call.

    `None` means the provider did not report the number — which is not the same
    as reporting zero, so the fields are never defaulted to 0.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """Sum across turns, treating unreported values as absent, not zero."""
        return TokenUsage(
            _add_optional(self.input_tokens, other.input_tokens),
            _add_optional(self.output_tokens, other.output_tokens),
        )


def _add_optional(left: int | None, right: int | None) -> int | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


@dataclass
class Answer:
    """Final agent output."""

    text: str
    citations: list[str] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency_ms: int = 0
