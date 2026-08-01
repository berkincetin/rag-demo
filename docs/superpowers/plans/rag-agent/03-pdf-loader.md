# Task 3: PDF loader with section and page tracking

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 2](02-normalize.md)
**Next:** [Task 4](04-docx-loader.md)

---

**Files:**
- Create: `src/rag/loaders/pdf_loader.py`
- Test: `tests/test_pdf_loader.py`

**Interfaces:**
- Consumes: `RawSection` from `src.rag.models`, `clean_text` from `src.rag.normalize`
- Produces: `load_pdf(path: Path) -> list[RawSection]`

**Measured facts this must satisfy** (`docs/01-veri-kesif-bulgulari.md` §1.2): Aksef is 12 pages / 27 detectable headings; Duxet is 24 pages / 32 raw matches of which ~5 are footnote false positives on page 15 (e.g. `7 Plasebodan ististiksel olarak anlamlı değil`). Section `4.3 Kontrendikasyonlar` starts on Aksef page 3.

- [ ] **Step 1: Write the failing unit test for heading recognition**

```python
# tests/test_pdf_loader.py
import pytest

from src.rag.loaders.pdf_loader import KUB_SECTION_IDS, parse_heading


def test_parse_heading_accepts_a_numbered_kub_section():
    assert parse_heading("4.2 Pozoloji ve uygulama şekli") == ("4.2", "Pozoloji ve uygulama şekli")


def test_parse_heading_accepts_a_top_level_section_with_trailing_dot():
    assert parse_heading("1. BEŞERİ TIBBİ ÜRÜNÜN ADI") == ("1", "BEŞERİ TIBBİ ÜRÜNÜN ADI")


def test_parse_heading_rejects_a_line_that_is_not_a_heading():
    assert parse_heading("Etkin madde: Sefuroksim aksetil 601,44 mg") is None


def test_parse_heading_rejects_a_page_marker():
    assert parse_heading("1/12") is None


def test_kub_whitelist_covers_the_standard_section_numbers():
    assert "4.1" in KUB_SECTION_IDS
    assert "6.6" in KUB_SECTION_IDS
    # Footnote markers on Duxet page 15 look like headings but are not sections.
    assert "7" not in KUB_SECTION_IDS
    assert "10" not in KUB_SECTION_IDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pdf_loader.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.loaders.pdf_loader'`

- [ ] **Step 3: Write minimal `src/rag/loaders/pdf_loader.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pdf_loader.py -v --no-cov`
Expected: PASS (5 passed)

- [ ] **Step 5: Write the failing integration test against the real PDFs**

```python
# append to tests/test_pdf_loader.py
from pathlib import Path

from src.rag.loaders.pdf_loader import load_pdf

DATA = Path("data")


def _find(pattern: str) -> Path:
    matches = sorted(DATA.glob(pattern))
    assert matches, f"no file matching {pattern} in {DATA}"
    return matches[0]


@pytest.mark.integration
def test_aksef_yields_at_least_twenty_sections():
    sections = load_pdf(_find("Aksef*.pdf"))

    assert len(sections) >= 20
    assert all(section.text for section in sections)


@pytest.mark.integration
def test_aksef_contraindications_section_starts_on_page_three():
    sections = load_pdf(_find("Aksef*.pdf"))

    section = next(s for s in sections if s.section_id == "4.3")

    assert section.page_start == 3
    assert "Kontrendikasyon" in section.section_title


@pytest.mark.integration
def test_duxet_footnote_markers_are_not_treated_as_sections():
    sections = load_pdf(_find("Duxet*.pdf"))

    ids = {section.section_id for section in sections}

    assert len(sections) >= 20
    assert "7" not in ids
    assert "10" not in ids
```

- [ ] **Step 6: Run integration test to verify it passes**

Run: `pytest tests/test_pdf_loader.py -m integration -v --no-cov`
Expected: PASS (3 passed). If `4.3` lands on the wrong page, invoke `superpowers:systematic-debugging` before changing the assertion — the page number is a measured fact.

- [ ] **Step 7: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/loaders/pdf_loader.py tests/test_pdf_loader.py
git commit -m "feat(loaders): add PDF section loader with footnote false-positive filter"
```
