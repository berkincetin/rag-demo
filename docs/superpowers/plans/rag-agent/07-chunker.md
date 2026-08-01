# Task 7: Section-aware chunker with citation labels

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 6](06-loader-dispatch.md)
**Next:** [Task 8](08-index-ingest.md)

---

**Files:**
- Create: `src/rag/chunker.py`
- Test: `tests/test_chunker.py`

**Interfaces:**
- Consumes: `RawSection`, `Chunk`, `fold_tr`
- Produces: `chunk_sections(sections: list[RawSection], max_chars: int = 1200, overlap: int = 150) -> list[Chunk]`, `build_citation_label(section: RawSection) -> str`

Spreadsheet rows are never split (ADR-005). PDF and DOCX sections split on paragraph boundaries when they exceed `max_chars`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chunker.py
from src.rag.chunker import build_citation_label, chunk_sections
from src.rag.models import RawSection


def _pdf_section(text: str) -> RawSection:
    return RawSection(
        source_file="Aksef.pdf",
        doc_type="pdf",
        text=text,
        section_id="4.2",
        section_title="Pozoloji ve uygulama şekli",
        page_start=2,
        page_end=2,
    )


def test_citation_label_for_pdf_includes_section_and_page():
    label = build_citation_label(_pdf_section("x"))

    assert label == "Aksef.pdf — Bölüm 4.2 Pozoloji ve uygulama şekli, s.2"


def test_citation_label_for_docx_uses_the_heading_path():
    section = RawSection(
        source_file="arac.docx",
        doc_type="docx",
        text="x",
        section_path="3. ARAÇ TAHSİS POLİTİKASI",
    )

    assert build_citation_label(section) == "arac.docx — 3. ARAÇ TAHSİS POLİTİKASI"


def test_citation_label_for_xlsx_uses_sheet_and_row():
    section = RawSection(
        source_file="sss.xlsx", doc_type="xlsx", text="x", sheet="Genel SSS", row=5
    )

    assert build_citation_label(section) == "sss.xlsx — Genel SSS, satır 5"


def test_short_section_becomes_exactly_one_chunk():
    chunks = chunk_sections([_pdf_section("kısa metin")])

    assert len(chunks) == 1
    assert chunks[0].text == "kısa metin"


def test_long_section_splits_into_multiple_chunks_within_the_limit():
    paragraphs = "\n\n".join("p" * 400 for _ in range(6))

    chunks = chunk_sections([_pdf_section(paragraphs)], max_chars=1200, overlap=150)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 1200 + 150 for chunk in chunks)


def test_spreadsheet_rows_are_never_split_even_when_long():
    section = RawSection(
        source_file="taxonomy.xlsx",
        doc_type="xlsx",
        text="x" * 3000,
        sheet="Sheet1",
        row=4,
    )

    chunks = chunk_sections([section], max_chars=1200, overlap=150)

    assert len(chunks) == 1
    assert len(chunks[0].text) == 3000


def test_chunk_search_text_is_ascii_folded():
    chunks = chunk_sections([_pdf_section("İnsan Kaynakları")])

    assert chunks[0].search_text == "insan kaynaklari"


def test_chunk_ids_are_unique_across_sections():
    sections = [_pdf_section("a"), _pdf_section("b")]

    ids = [chunk.chunk_id for chunk in chunk_sections(sections)]

    assert len(ids) == len(set(ids))


def test_metadata_carries_location_fields_as_scalars():
    chunks = chunk_sections([_pdf_section("metin")])

    metadata = chunks[0].metadata

    assert metadata["source_file"] == "Aksef.pdf"
    assert metadata["section_id"] == "4.2"
    assert metadata["page_start"] == 2
    assert metadata["sheet"] == ""  # None becomes "" for Chroma compatibility
    assert metadata["row"] == -1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chunker.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.chunker'`

- [ ] **Step 3: Write minimal `src/rag/chunker.py`**

```python
"""Turn loaded sections into indexable chunks with human-readable citations.

Spreadsheet rows are atomic: splitting one would separate a question from
its answer. PDF and DOCX sections split on paragraph boundaries only.
"""

import re
from typing import Any

from src.rag.models import Chunk, RawSection
from src.rag.normalize import fold_tr

_NON_WORD = re.compile(r"[^a-z0-9]+")


def build_citation_label(section: RawSection) -> str:
    """Render the citation shown to the user for this section."""
    if section.doc_type == "xlsx":
        return f"{section.source_file} — {section.sheet}, satır {section.row}"
    if section.doc_type == "docx":
        return f"{section.source_file} — {section.section_path or section.section_title}"
    title = f"Bölüm {section.section_id} {section.section_title}".strip()
    if section.section_id is None:
        title = section.section_title or ""
    return f"{section.source_file} — {title}, s.{section.page_start}"


def _slug(value: str) -> str:
    return _NON_WORD.sub("-", fold_tr(value)).strip("-")[:40]


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


def _split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split on paragraph boundaries, carrying `overlap` characters forward."""
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    buffer = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            pieces.append(buffer)
            buffer = (buffer[-overlap:] + "\n\n" + paragraph).strip()
        else:
            pieces.append(paragraph[:max_chars])
            buffer = paragraph[max_chars - overlap :]
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
        for index, piece in enumerate(pieces):
            chunks.append(
                Chunk(
                    chunk_id=f"{base}__{marker}__{position}__{index}",
                    text=piece,
                    search_text=fold_tr(piece),
                    citation_label=build_citation_label(section),
                    metadata=_metadata(section, index, len(piece)),
                )
            )
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chunker.py -v --no-cov`
Expected: PASS (9 passed)

- [ ] **Step 5: Write the failing integration test over the real corpus**

```python
# append to tests/test_chunker.py
from pathlib import Path

import pytest

from src.rag.loaders import load_all


@pytest.mark.integration
def test_corpus_produces_a_chunk_count_in_the_expected_range():
    chunks = chunk_sections(load_all(Path("data")))

    assert 250 <= len(chunks) <= 450


@pytest.mark.integration
def test_every_chunk_has_a_non_empty_citation_label():
    chunks = chunk_sections(load_all(Path("data")))

    assert all(chunk.citation_label.strip() for chunk in chunks)


@pytest.mark.integration
def test_the_fuel_limit_table_value_survives_chunking():
    chunks = chunk_sections(load_all(Path("data")))

    assert any("1.500 TL/ay" in chunk.text for chunk in chunks)
```

- [ ] **Step 6: Run integration test to verify it passes**

Run: `pytest tests/test_chunker.py -m integration -v --no-cov`
Expected: PASS (3 passed). If the chunk count falls outside 250–450, invoke `superpowers:systematic-debugging` — either a loader is dropping content or the splitter is over-splitting.

- [ ] **Step 7: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/chunker.py tests/test_chunker.py
git commit -m "feat(chunker): add section-aware chunking with citation labels"
```
