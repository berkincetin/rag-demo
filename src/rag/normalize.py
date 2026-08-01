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
