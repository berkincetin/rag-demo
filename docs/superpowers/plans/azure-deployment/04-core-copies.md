# Task 4: Core Module Copies

**Goal:** Copy the loader and text-processing layer into `azure/rag/` with
imports rewritten. Logic changes: **none**.

**Files:**
- Modify: `azure/rag/models.py` (append the remaining dataclasses)
- Create: `azure/rag/normalize.py`, `azure/rag/chunker.py`
- Create: `azure/rag/loaders/__init__.py`, `pdf_loader.py`, `docx_loader.py`, `xlsx_loader.py`
- Create: `azure/tests/test_core_copies.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-3
- Produces:
  ```python
  # azure/rag/models.py
  RawSection, Chunk, SearchHit, TokenUsage, Answer

  # azure/rag/normalize.py
  def fold_tr(text: str) -> str: ...
  def bm25_tokens(text: str) -> list[str]: ...

  # azure/rag/chunker.py
  def chunk_sections(sections: list[RawSection], max_chars: int = 1200,
                     overlap: int = 150) -> list[Chunk]: ...

  # azure/rag/loaders/__init__.py
  def load_all(data_dir: Path) -> list[RawSection]: ...
  ```

Confirm the exact `chunk_sections` and `load_all` signatures by reading the
source files before copying; use whatever is actually there.

---

## Method

This task is mechanical. For each file:

1. `cp src/rag/<file>.py azure/rag/<file>.py`
2. Rewrite imports: `from src.rag.` → `from azure.rag.`
3. Change **nothing else** — no renames, no "improvements", no reformatting

The copies must stay behaviourally identical, because the integration
assertions in Task 8 come from measurements taken against the originals.

- [ ] **Step 1: Write the failing equivalence tests**

Create `azure/tests/test_core_copies.py`:

```python
"""The azure copies must behave identically to the originals.

These tests import both and compare. If a copy ever drifts, this fails —
which is the only protection against the duplication the design accepted.
"""

from pathlib import Path

import pytest

from azure.rag import normalize as azure_normalize
from src.rag import normalize as local_normalize

DATA_DIR = Path("data")


@pytest.mark.parametrize(
    "text",
    [
        "İnsan Kaynakları",
        "Insan Kaynaklari",
        "Yıllık İzin Talebi",
        "ŞİRKET ÇALIŞMA ĞÜÖ",
        "OPS-PRO-003",
    ],
)
def test_fold_tr_matches_original(text):
    assert azure_normalize.fold_tr(text) == local_normalize.fold_tr(text)


@pytest.mark.parametrize("text", ["yıllık izin talebi", "OPS-PRO-003 prosedürü"])
def test_bm25_tokens_match_original(text):
    assert azure_normalize.bm25_tokens(text) == local_normalize.bm25_tokens(text)


@pytest.mark.integration
def test_load_all_matches_original():
    """Same 6 documents, same sections, same text."""
    from azure.rag.loaders import load_all as azure_load_all
    from src.rag.loaders import load_all as local_load_all

    azure_sections = azure_load_all(DATA_DIR)
    local_sections = local_load_all(DATA_DIR)

    assert len(azure_sections) == len(local_sections)
    assert [s.text for s in azure_sections] == [s.text for s in local_sections]


@pytest.mark.integration
def test_chunking_matches_original():
    from azure.rag.chunker import chunk_sections as azure_chunk
    from azure.rag.loaders import load_all as azure_load_all
    from src.rag.chunker import chunk_sections as local_chunk
    from src.rag.loaders import load_all as local_load_all

    azure_chunks = azure_chunk(azure_load_all(DATA_DIR))
    local_chunks = local_chunk(local_load_all(DATA_DIR))

    assert len(azure_chunks) == len(local_chunks)
    assert [c.search_text for c in azure_chunks] == [c.search_text for c in local_chunks]


@pytest.mark.integration
def test_docx_table_value_survives_chunking():
    """`1.500 TL/ay` exists only in a DOCX table — the canonical smoke test."""
    from azure.rag.chunker import chunk_sections
    from azure.rag.loaders import load_all

    chunks = chunk_sections(load_all(DATA_DIR))

    assert any("1.500 TL/ay" in chunk.text for chunk in chunks)
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `pytest azure/tests/test_core_copies.py -v`
Expected: FAIL with `ImportError` / `ModuleNotFoundError` for `azure.rag.normalize`

- [ ] **Step 3: Copy the files**

```bash
cp src/rag/normalize.py azure/rag/normalize.py
cp src/rag/chunker.py  azure/rag/chunker.py
mkdir -p azure/rag/loaders
cp src/rag/loaders/__init__.py    azure/rag/loaders/__init__.py
cp src/rag/loaders/pdf_loader.py  azure/rag/loaders/pdf_loader.py
cp src/rag/loaders/docx_loader.py azure/rag/loaders/docx_loader.py
cp src/rag/loaders/xlsx_loader.py azure/rag/loaders/xlsx_loader.py
```

- [ ] **Step 4: Rewrite the imports**

In every copied file, replace `from src.rag.` with `from azure.rag.`.

```bash
grep -rn "src\.rag" azure/rag/
```

Expected after the rewrite: **no output**.

- [ ] **Step 5: Append the remaining dataclasses to `azure/rag/models.py`**

Task 3 created this file with `TokenUsage` and `_add_optional`. Add
`RawSection`, `Chunk`, `SearchHit`, and `Answer` copied verbatim from
`src/rag/models.py`. Keep the module docstring accurate.

Verify all five are present:

```bash
python -c "from azure.rag.models import RawSection, Chunk, SearchHit, TokenUsage, Answer; print('ok')"
```

- [ ] **Step 6: Run the unit tests**

Run: `pytest azure/tests/test_core_copies.py -v -m "not integration"`
Expected: all `fold_tr` and `bm25_tokens` cases pass

- [ ] **Step 7: Run the integration tests against the real corpus**

Run: `pytest azure/tests/test_core_copies.py -v -m integration`
Expected: 3 passed. The section and chunk counts must equal the originals
(219 sections → 276 chunks, per PROGRESSION.md).

If the counts differ, a copy drifted — fix the copy, do not adjust the test.

- [ ] **Step 8: Confirm the local path is untouched**

```bash
git status --short src/ tests/ gradio_app.py docker-compose.yml
```

Expected: no output.

- [ ] **Step 9: Quality gate**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
```

- [ ] **Step 10: Commit**

```bash
git add azure/
git commit -m "feat(azure): copy loaders, chunker, normalizer and models"
```
