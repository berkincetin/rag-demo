# Task 5: XLSX loader with header detection and row-per-section

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 4](04-docx-loader.md)
**Next:** [Task 6](06-loader-dispatch.md)

---

**Files:**
- Create: `src/rag/loaders/xlsx_loader.py`
- Test: `tests/test_xlsx_loader.py`

**Interfaces:**
- Consumes: `RawSection`, `clean_text`
- Produces: `load_xlsx(path: Path) -> list[RawSection]`, `detect_header_row(frame: pd.DataFrame) -> int`

**Measured facts** (§1.5): `calisan_sss_rehberi.xlsx` has 3 sheets whose real column headers sit on **row index 2**, not 0. Sheet shapes are 17×6, 14×5, 19×6. `Anonim_Urun_Taksonomi_100Satir.xlsx` has 100 rows × 15 columns and must produce exactly 100 sections. One spreadsheet row is a self-contained answer — never split it.

- [ ] **Step 1: Write the failing unit test for header detection**

```python
# tests/test_xlsx_loader.py
import pandas as pd

from src.rag.loaders.xlsx_loader import detect_header_row, row_to_text


def test_detect_header_row_finds_headers_below_a_title_and_subtitle():
    frame = pd.DataFrame(
        [
            ["TEKNOPARK YAZILIM A.S. — CALISAN SSS REHBERI", None, None],
            ["Son Guncelleme: Ocak 2025", None, None],
            ["#", "Kategori", "Soru & Cevap"],
            ["1", "Insan Kaynaklari", "SORU: ...\n\nCEVAP: ..."],
        ]
    )

    assert detect_header_row(frame) == 2


def test_detect_header_row_returns_zero_when_headers_are_already_first():
    frame = pd.DataFrame([["Ürün", "Molekül"], ["Vitatin95", "Amlodipin"]])

    assert detect_header_row(frame) == 0


def test_row_to_text_renders_field_value_pairs_and_skips_empty_cells():
    row = pd.Series({"Ürün": "Vitatin95", "Molekül": "Amlodipin", "Not": None})

    assert row_to_text(row) == "Ürün: Vitatin95 | Molekül: Amlodipin"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_xlsx_loader.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.loaders.xlsx_loader'`

- [ ] **Step 3: Write minimal `src/rag/loaders/xlsx_loader.py`**

```python
"""Load spreadsheets as one section per row.

A row in these workbooks is already a self-contained record (a full
question/answer pair, or one product's taxonomy), so rows are never split.
Header rows are detected rather than assumed: the FAQ workbook carries a
title and a subtitle above its real headers.
"""

from pathlib import Path

import pandas as pd

from src.rag.models import RawSection
from src.rag.normalize import clean_text

_MAX_HEADER_SCAN = 10
_MIN_FILL_RATIO = 0.6


def detect_header_row(frame: pd.DataFrame) -> int:
    """Return the index of the row that holds the real column headers."""
    best_index = 0
    best_filled = -1
    for index in range(min(_MAX_HEADER_SCAN, len(frame))):
        row = frame.iloc[index]
        filled = int(row.notna().sum())
        if filled / max(len(row), 1) >= _MIN_FILL_RATIO and filled > best_filled:
            best_index, best_filled = index, filled
    return best_index


def row_to_text(row: pd.Series) -> str:
    """Serialize a row as `Field: Value` pairs, dropping empty cells."""
    parts = [
        f"{name}: {str(value).strip()}"
        for name, value in row.items()
        if pd.notna(value) and str(value).strip()
    ]
    return " | ".join(parts)


def load_xlsx(path: Path) -> list[RawSection]:
    """Produce one RawSection per data row across every sheet."""
    sections: list[RawSection] = []
    workbook = pd.ExcelFile(path)

    for sheet_name in workbook.sheet_names:
        raw = workbook.parse(sheet_name, header=None)
        if raw.empty:
            continue
        header_index = detect_header_row(raw)
        frame = workbook.parse(sheet_name, header=header_index)
        frame = frame.dropna(how="all")

        for offset, (_, row) in enumerate(frame.iterrows()):
            text = row_to_text(row)
            if not text:
                continue
            sections.append(
                RawSection(
                    source_file=path.name,
                    doc_type="xlsx",
                    text=clean_text(text),
                    sheet=sheet_name,
                    row=header_index + offset + 2,
                    section_title=sheet_name,
                    section_path=sheet_name,
                )
            )
    return sections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_xlsx_loader.py -v --no-cov`
Expected: PASS (3 passed)

- [ ] **Step 5: Write the failing integration test against the real workbooks**

```python
# append to tests/test_xlsx_loader.py
from pathlib import Path

import pytest

from src.rag.loaders.xlsx_loader import load_xlsx

DATA = Path("data")


def _find(pattern: str) -> Path:
    matches = sorted(DATA.glob(pattern))
    assert matches, f"no file matching {pattern} in {DATA}"
    return matches[0]


@pytest.mark.integration
def test_taxonomy_yields_exactly_one_hundred_sections():
    sections = load_xlsx(_find("Anonim_Urun_Taksonomi*.xlsx"))

    assert len(sections) == 100


@pytest.mark.integration
def test_taxonomy_row_keeps_product_and_owner_in_one_section():
    sections = load_xlsx(_find("Anonim_Urun_Taksonomi*.xlsx"))

    section = next(s for s in sections if "Vitatin95" in s.text)

    assert "Ürün Müdürü" in section.text
    assert "Terapötik Sistem" in section.text


@pytest.mark.integration
def test_faq_covers_all_three_sheets_and_keeps_question_answer_together():
    sections = load_xlsx(_find("calisan_sss*.xlsx"))

    sheets = {section.sheet for section in sections}
    qa_sections = [s for s in sections if "SORU:" in s.text]

    assert len(sheets) == 3
    assert len(sections) >= 30
    assert qa_sections, "expected at least one full SORU/CEVAP row"
    assert all("CEVAP:" in section.text for section in qa_sections)
```

- [ ] **Step 6: Run integration test to verify it passes**

Run: `pytest tests/test_xlsx_loader.py -m integration -v --no-cov`
Expected: PASS (3 passed)

- [ ] **Step 7: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/loaders/xlsx_loader.py tests/test_xlsx_loader.py
git commit -m "feat(loaders): add XLSX loader with header detection and row sections"
```
