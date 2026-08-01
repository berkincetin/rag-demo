# Task 6: Loader dispatch over the corpus directory

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 5](05-xlsx-loader.md)
**Next:** [Task 7](07-chunker.md)

---

**Files:**
- Modify: `src/rag/loaders/__init__.py`
- Test: `tests/test_loaders.py`

**Interfaces:**
- Consumes: `load_pdf`, `load_docx`, `load_xlsx`
- Produces: `load_all(data_dir: Path) -> list[RawSection]`

Filenames are never hardcoded: `ik_surecleri_politikası.docx` contains a Turkish `ı` and the case document spells it with a plain `i`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_loaders.py
from pathlib import Path

import pytest

from src.rag.loaders import SUPPORTED_SUFFIXES, load_all

DATA = Path("data")


def test_supported_suffixes_cover_the_three_corpus_formats():
    assert SUPPORTED_SUFFIXES == {".pdf", ".docx", ".xlsx"}


def test_load_all_ignores_unsupported_files(tmp_path):
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    assert load_all(tmp_path) == []


@pytest.mark.integration
def test_load_all_reads_every_document_in_the_corpus():
    sections = load_all(DATA)

    files = {section.source_file for section in sections}

    assert len(files) == 6
    assert {section.doc_type for section in sections} == {"pdf", "docx", "xlsx"}


@pytest.mark.integration
def test_load_all_finds_the_hr_policy_despite_its_turkish_filename():
    sections = load_all(DATA)

    assert any("ik_surecleri" in section.source_file for section in sections)


@pytest.mark.integration
def test_every_loaded_section_has_text_and_a_source():
    sections = load_all(DATA)

    assert sections
    assert all(section.text.strip() for section in sections)
    assert all(section.source_file for section in sections)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loaders.py -v --no-cov`
Expected: FAIL with `ImportError: cannot import name 'load_all'`

- [ ] **Step 3: Write minimal `src/rag/loaders/__init__.py`**

```python
"""Discover and load every supported document in the corpus directory."""

import logging
from pathlib import Path

from src.rag.loaders.docx_loader import load_docx
from src.rag.loaders.pdf_loader import load_pdf
from src.rag.loaders.xlsx_loader import load_xlsx
from src.rag.models import RawSection

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".xlsx"}

_LOADERS = {".pdf": load_pdf, ".docx": load_docx, ".xlsx": load_xlsx}


def load_all(data_dir: Path) -> list[RawSection]:
    """Load every supported file in `data_dir`, skipping temp and unknown files."""
    sections: list[RawSection] = []
    for path in sorted(Path(data_dir).glob("*")):
        if path.name.startswith("~$") or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        loader = _LOADERS[path.suffix.lower()]
        loaded = loader(path)
        logger.info("loaded %s sections from %s", len(loaded), path.name)
        sections.extend(loaded)
    return sections
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_loaders.py -v --no-cov`
Expected: PASS (5 passed)

- [ ] **Step 5: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/loaders/__init__.py tests/test_loaders.py
git commit -m "feat(loaders): add glob-based dispatch over the corpus directory"
```
