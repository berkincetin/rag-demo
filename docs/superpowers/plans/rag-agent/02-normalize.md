# Task 2: Turkish-aware text normalization

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 1](01-skeleton-config-models.md)
**Next:** [Task 3](03-pdf-loader.md)

---

**Files:**
- Create: `src/rag/normalize.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Consumes: nothing
- Produces: `fold_tr(s: str) -> str` (ASCII-folded, casefolded, whitespace-collapsed search text) and `clean_text(s: str) -> str` (collapses runs of blank lines and trailing spaces, preserves paragraph breaks)

**Why this exists:** `docs/01-veri-kesif-bulgulari.md` §1.4 — DOCX files are ASCII-folded (`Insan Kaynaklari`), PDFs are full Turkish (`İnsan Kaynakları`). Without folding both sides, a correctly-typed query cannot match the DOCX corpus.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_normalize.py
from src.rag.normalize import clean_text, fold_tr


def test_turkish_and_ascii_spellings_fold_to_the_same_string():
    assert fold_tr("İnsan Kaynakları") == fold_tr("Insan Kaynaklari") == "insan kaynaklari"


def test_dotted_capital_i_does_not_leave_a_combining_dot():
    # str.lower() turns "İ" into "i̇" (i + U+0307). That must not happen here.
    assert fold_tr("İZİN") == "izin"
    assert "̇" not in fold_tr("İZİN")


def test_dotless_i_folds_to_ascii_i():
    assert fold_tr("yıllık") == "yillik"


def test_all_turkish_specific_letters_fold():
    assert fold_tr("ŞĞÇÖÜ şğçöü") == "sgcou sgcou"


def test_runs_of_whitespace_collapse_to_one_space():
    assert fold_tr("  a\t\tb\n\nc  ") == "a b c"


def test_clean_text_preserves_paragraph_breaks_but_drops_extra_blank_lines():
    assert clean_text("a\n\n\n\nb") == "a\n\nb"


def test_clean_text_strips_trailing_spaces_on_each_line():
    assert clean_text("a   \nb  ") == "a\nb"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.normalize'`

- [ ] **Step 3: Write minimal `src/rag/normalize.py`**

The Turkish mappings must run **before** `casefold()`. Python's default lowercasing turns `İ` into `i` + U+0307, which then survives NFKD stripping as a separate combining mark and breaks equality.

```python
"""Text normalization for Turkish search text.

The corpus mixes full Turkish orthography (PDFs) with ASCII-folded text
(DOCX). `fold_tr` maps both onto one search space. Display text is never
folded — only the search field is.
"""

import re
import unicodedata

_TURKISH_MAP = str.maketrans(
    {
        "İ": "I",
        "ı": "i",
        "Ş": "S",
        "ş": "s",
        "Ğ": "G",
        "ğ": "g",
        "Ç": "C",
        "ç": "c",
        "Ö": "O",
        "ö": "o",
        "Ü": "U",
        "ü": "u",
    }
)

_WHITESPACE = re.compile(r"\s+")
_TRAILING_SPACES = re.compile(r"[ \t]+$", re.MULTILINE)
_EXTRA_BLANK_LINES = re.compile(r"\n{3,}")


def fold_tr(text: str) -> str:
    """Fold Turkish text to a lowercase ASCII search form.

    Turkish-specific letters are mapped first, because `casefold` turns "İ"
    into "i" plus a combining dot that would survive the NFKD pass.
    """
    mapped = text.translate(_TURKISH_MAP)
    decomposed = unicodedata.normalize("NFKD", mapped)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _WHITESPACE.sub(" ", stripped.casefold()).strip()


def clean_text(text: str) -> str:
    """Normalize line endings and drop redundant blank lines and trailing spaces."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _TRAILING_SPACES.sub("", normalized)
    return _EXTRA_BLANK_LINES.sub("\n\n", normalized).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalize.py -v --no-cov`
Expected: PASS (7 passed)

- [ ] **Step 5: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/normalize.py tests/test_normalize.py
git commit -m "feat(normalize): add Turkish-aware ASCII folding for search text"
```
