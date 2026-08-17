"""Turn loaded sections into indexable chunks with human-readable citations.

Spreadsheet rows are atomic: splitting one would separate a question from
its answer. PDF and DOCX sections split on paragraph boundaries only.
"""

import re
from typing import Any

from azure.rag.models import Chunk, RawSection
from azure.rag.normalize import fold_tr

_NON_WORD = re.compile(r"[^a-z0-9]+")


def build_citation_label(section: RawSection) -> str:
    """Render the citation shown to the user for this section."""
    if section.doc_type == "xlsx":
        return f"{section.source_file} — {section.sheet}, satır {section.row}"
    if section.doc_type == "docx":
        return f"{section.source_file} — {section.section_path or section.section_title}"
    # Plain text carries no section and no page; rendering the generic form
    # would print "— , s.None". Only uploads produce this type.
    if section.doc_type == "txt":
        return section.source_file
    title = f"Bölüm {section.section_id} {section.section_title}".strip()
    if section.section_id is None:
        title = section.section_title or ""
    return f"{section.source_file} — {title}, s.{section.page_start}"


def _slug(value: str) -> str:
    return _NON_WORD.sub("-", fold_tr(value)).strip("-")[:40]


def _search_heading(section: RawSection) -> str:
    """Heading words to prepend to the search field, never to the display text.

    A KUB section titled "Kontrendikasyonlar" does not repeat that word in its
    body, so a query naming the section can only match through its heading.
    """
    parts = [section.section_id, section.section_title, section.section_path, section.sheet]
    seen: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.append(part)
    return " ".join(seen)


def _metadata(section: RawSection, chunk_index: int, char_count: int) -> dict[str, Any]:
    """Chroma metadata values must be scalars; None is not allowed."""
    return {
        "source_file": section.source_file,
        "doc_type": section.doc_type,
        "section_id": section.section_id or "",
        "section_title": section.section_title or "",
        "section_path": section.section_path or "",
        "page_start": section.page_start if section.page_start is not None else -1,
        "page_end": section.page_end if section.page_end is not None else -1,
        "sheet": section.sheet or "",
        "row": section.row if section.row is not None else -1,
        "chunk_index": chunk_index,
        "char_count": char_count,
        "citation_label": build_citation_label(section),
    }


def _hard_split(paragraph: str, max_chars: int, overlap: int) -> list[str]:
    """Cut a paragraph that alone exceeds `max_chars` into fitting pieces.

    Prefer a line break or sentence end inside the window; fall back to a
    hard cut when the last boundary sits too early to be useful.
    """
    pieces: list[str] = []
    start = 0
    while start < len(paragraph):
        if len(paragraph) - start <= max_chars:
            pieces.append(paragraph[start:])
            break
        window = paragraph[start : start + max_chars]
        cut = max(window.rfind("\n"), window.rfind(". ") + 1)
        if cut < max_chars // 2:
            cut = max_chars
        pieces.append(paragraph[start : start + cut])
        start += max(cut - overlap, 1)
    return pieces


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split on paragraph boundaries, carrying `overlap` characters forward.

    Paragraphs are hard-split first: KUB sections are frequently one
    unbroken paragraph of several thousand characters, so splitting on
    "\\n\\n" alone would leave chunks far above `max_chars`.
    """
    if len(text) <= max_chars:
        return [text]
    paragraphs = [
        piece
        for paragraph in text.split("\n\n")
        for piece in (
            _hard_split(paragraph, max_chars, overlap)
            if len(paragraph) > max_chars
            else [paragraph]
        )
    ]
    pieces: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        pieces.append(buffer)
        carried = f"{buffer[-overlap:]}\n\n{paragraph}".strip()
        buffer = carried if len(carried) <= max_chars else paragraph
    if buffer:
        pieces.append(buffer)
    return pieces


def chunk_sections(
    sections: list[RawSection], max_chars: int = 1200, overlap: int = 150
) -> list[Chunk]:
    """Convert sections into chunks, keeping spreadsheet rows intact."""
    chunks: list[Chunk] = []
    for position, section in enumerate(sections):
        pieces = (
            [section.text]
            if section.doc_type == "xlsx"
            else _split_text(section.text, max_chars, overlap)
        )
        base = _slug(section.source_file)
        marker = _slug(section.section_id or section.section_path or str(section.row or position))
        heading = _search_heading(section)
        for index, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=f"{base}__{marker}__{position}__{index}",
                    text=piece,
                    search_text=fold_tr(f"{heading} {piece}" if heading else piece),
                    citation_label=build_citation_label(section),
                    metadata=_metadata(section, index, len(piece)),
                )
            )
    return chunks
