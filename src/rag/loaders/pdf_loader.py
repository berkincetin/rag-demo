"""Load KÜB-style PDFs into sections carrying section id, title, and page range."""

import re
from pathlib import Path

import pypdf

from src.rag.models import RawSection
from src.rag.normalize import clean_text

# Standard "Kısa Ürün Bilgisi" section numbers. Anything outside this set that
# looks like a heading is body text or a footnote marker (Duxet page 15).
KUB_SECTION_IDS: frozenset[str] = frozenset(
    ["1", "2", "3", "4", "5", "6"]
    + [f"4.{i}" for i in range(1, 10)]
    + [f"5.{i}" for i in range(1, 4)]
    + [f"6.{i}" for i in range(1, 7)]
)

_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2})\.?\s+(\S.{2,70})$")
_PAGE_MARKER = re.compile(r"^\d+\s*/\s*\d+$")
_BARE_NUMBER = re.compile(r"^\d{1,3}$")


def parse_heading(line: str) -> tuple[str, str] | None:
    """Return (section_id, title) when the line is a KÜB section heading."""
    stripped = line.strip()
    if _PAGE_MARKER.match(stripped) or _BARE_NUMBER.match(stripped):
        return None
    match = _HEADING.match(stripped)
    if match is None:
        return None
    section_id = match.group(1)
    if section_id not in KUB_SECTION_IDS:
        return None
    return section_id, match.group(2).strip()


def _sort_key(section_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in section_id.split("."))


def _is_page_noise(line: str) -> bool:
    stripped = line.strip()
    return not stripped or bool(_PAGE_MARKER.match(stripped)) or bool(_BARE_NUMBER.match(stripped))


def load_pdf(path: Path) -> list[RawSection]:
    """Split a PDF into sections. Falls back to one section per page."""
    reader = pypdf.PdfReader(str(path))
    sections: list[RawSection] = []
    current: RawSection | None = None
    last_key: tuple[int, ...] = ()

    for page_no, page in enumerate(reader.pages, start=1):
        for line in (page.extract_text() or "").split("\n"):
            heading = parse_heading(line)
            if heading is not None and _sort_key(heading[0]) > last_key:
                section_id, title = heading
                last_key = _sort_key(section_id)
                current = RawSection(
                    source_file=path.name,
                    doc_type="pdf",
                    text="",
                    section_id=section_id,
                    section_title=title,
                    page_start=page_no,
                    page_end=page_no,
                )
                sections.append(current)
                continue
            if current is None or _is_page_noise(line):
                continue
            current.text += line.strip() + "\n"
            current.page_end = page_no

    if not sections:
        return _one_section_per_page(path, reader)

    for section in sections:
        section.text = clean_text(section.text)
    return [section for section in sections if section.text]


def _one_section_per_page(path: Path, reader: pypdf.PdfReader) -> list[RawSection]:
    """Fallback for PDFs that carry no recognizable section numbering."""
    return [
        RawSection(
            source_file=path.name,
            doc_type="pdf",
            text=clean_text(page.extract_text() or ""),
            section_title=f"Sayfa {page_no}",
            page_start=page_no,
            page_end=page_no,
        )
        for page_no, page in enumerate(reader.pages, start=1)
        if (page.extract_text() or "").strip()
    ]
