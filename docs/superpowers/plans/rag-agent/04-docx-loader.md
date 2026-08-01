# Task 4: DOCX loader with heading hierarchy and tables

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 3](03-pdf-loader.md)
**Next:** [Task 5](05-xlsx-loader.md)

---

**Files:**
- Create: `src/rag/loaders/docx_loader.py`
- Test: `tests/test_docx_loader.py`

**Interfaces:**
- Consumes: `RawSection`, `clean_text`
- Produces: `load_docx(path: Path) -> list[RawSection]`, `table_to_markdown(table) -> str`

**Measured facts** (§1.3): `ik_surecleri_politikası.docx` has 84 non-empty paragraphs, 7 tables, 8 Heading 1 and 16 Heading 2 styles. `arac_kullanim_proseduru.docx` has 54 paragraphs and 9 tables. The string `1.500 TL/ay` exists **only inside a table** — it is the proof that table extraction works.

Two traps: iterating `document.paragraphs` silently drops every table, and `paragraph.style` is `None` for some paragraphs (this raised `AttributeError` during data exploration).

- [ ] **Step 1: Write the failing unit test for Markdown table rendering**

```python
# tests/test_docx_loader.py
from src.rag.loaders.docx_loader import rows_to_markdown


def test_rows_to_markdown_emits_a_header_separator_row():
    rows = [["Pozisyon", "Yakıt Limiti"], ["Direktör", "1.500 TL/ay"]]

    assert rows_to_markdown(rows) == (
        "| Pozisyon | Yakıt Limiti |\n| --- | --- |\n| Direktör | 1.500 TL/ay |"
    )


def test_rows_to_markdown_escapes_pipes_inside_cells():
    assert "\\|" in rows_to_markdown([["a|b"], ["c"]])


def test_rows_to_markdown_returns_empty_string_for_no_rows():
    assert rows_to_markdown([]) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_docx_loader.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.loaders.docx_loader'`

- [ ] **Step 3: Write minimal `src/rag/loaders/docx_loader.py`**

```python
"""Load DOCX policies into sections that follow the heading hierarchy.

Tables are rendered as Markdown and appended to the section they appear in,
because the most queryable facts in this corpus live in tables.
"""

from pathlib import Path

import docx
from docx.document import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.rag.models import RawSection
from src.rag.normalize import clean_text

_PREAMBLE_TITLE = "Belge Bilgileri"


def rows_to_markdown(rows: list[list[str]]) -> str:
    """Render table rows as a Markdown table. First row is the header."""
    if not rows:
        return ""
    escaped = [[cell.replace("|", "\\|").strip() for cell in row] for row in rows]
    header = "| " + " | ".join(escaped[0]) + " |"
    separator = "| " + " | ".join("---" for _ in escaped[0]) + " |"
    body = ["| " + " | ".join(row) + " |" for row in escaped[1:]]
    return "\n".join([header, separator, *body])


def _iter_block_items(document: Document):
    """Yield paragraphs and tables in document order.

    `document.paragraphs` alone would skip every table.
    """
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _style_name(paragraph: Paragraph) -> str:
    """Style can be None on some paragraphs; treat that as no style."""
    return getattr(paragraph.style, "name", "") or ""


def load_docx(path: Path) -> list[RawSection]:
    """Split a DOCX into sections keyed by its Heading 1 / Heading 2 structure."""
    document = docx.Document(str(path))
    sections: list[RawSection] = []
    heading_1 = ""
    heading_2 = ""
    current = RawSection(
        source_file=path.name,
        doc_type="docx",
        text="",
        section_title=_PREAMBLE_TITLE,
        section_path=_PREAMBLE_TITLE,
    )
    sections.append(current)

    def open_section() -> RawSection:
        path_parts = [part for part in (heading_1, heading_2) if part]
        section = RawSection(
            source_file=path.name,
            doc_type="docx",
            text="",
            section_title=heading_2 or heading_1,
            section_path=" > ".join(path_parts),
        )
        sections.append(section)
        return section

    for block in _iter_block_items(document):
        if isinstance(block, Table):
            rows = [[cell.text for cell in row.cells] for row in block.rows]
            current.text += "\n" + rows_to_markdown(rows) + "\n"
            continue

        text = block.text.strip()
        if not text:
            continue
        style = _style_name(block)
        if style == "Heading 1":
            heading_1, heading_2 = text, ""
            current = open_section()
        elif style == "Heading 2":
            heading_2 = text
            current = open_section()
        elif style == "List Paragraph":
            current.text += f"- {text}\n"
        else:
            current.text += text + "\n"

    for section in sections:
        section.text = clean_text(section.text)
    return [section for section in sections if section.text]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_docx_loader.py -v --no-cov`
Expected: PASS (3 passed)

- [ ] **Step 5: Write the failing integration test against the real DOCX files**

```python
# append to tests/test_docx_loader.py
from pathlib import Path

import pytest

from src.rag.loaders.docx_loader import load_docx

DATA = Path("data")


def _find(pattern: str) -> Path:
    matches = sorted(DATA.glob(pattern))
    assert matches, f"no file matching {pattern} in {DATA}"
    return matches[0]


@pytest.mark.integration
def test_fuel_limit_from_a_table_is_present_in_the_loaded_text():
    sections = load_docx(_find("arac_kullanim*.docx"))

    combined = "\n".join(section.text for section in sections)

    assert "1.500 TL/ay" in combined


@pytest.mark.integration
def test_hr_policy_yields_at_least_eight_distinct_section_paths():
    sections = load_docx(_find("ik_surecleri*.docx"))

    paths = {section.section_path for section in sections if section.section_path}

    assert len(paths) >= 8


@pytest.mark.integration
def test_every_table_row_reaches_the_output():
    import docx

    path = _find("arac_kullanim*.docx")
    expected_cells = [
        cell.text.strip()
        for table in docx.Document(str(path)).tables
        for row in table.rows
        for cell in row.cells
        if cell.text.strip()
    ]

    combined = "\n".join(section.text for section in load_docx(path))

    missing = [cell for cell in expected_cells if cell.replace("|", "\\|") not in combined]
    assert missing == []
```

- [ ] **Step 6: Run integration test to verify it passes**

Run: `pytest tests/test_docx_loader.py -m integration -v --no-cov`
Expected: PASS (3 passed)

- [ ] **Step 7: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/loaders/docx_loader.py tests/test_docx_loader.py
git commit -m "feat(loaders): add DOCX loader with heading hierarchy and table extraction"
```
