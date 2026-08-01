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
