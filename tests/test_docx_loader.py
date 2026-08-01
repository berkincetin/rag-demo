from pathlib import Path

import pytest

from src.rag.loaders.docx_loader import load_docx, rows_to_markdown

DATA = Path("data")


def _find(pattern: str) -> Path:
    matches = sorted(DATA.glob(pattern))
    assert matches, f"no file matching {pattern} in {DATA}"
    return matches[0]


def test_rows_to_markdown_emits_a_header_separator_row():
    rows = [["Pozisyon", "Yakıt Limiti"], ["Direktör", "1.500 TL/ay"]]

    assert rows_to_markdown(rows) == (
        "| Pozisyon | Yakıt Limiti |\n| --- | --- |\n| Direktör | 1.500 TL/ay |"
    )


def test_rows_to_markdown_escapes_pipes_inside_cells():
    assert "\\|" in rows_to_markdown([["a|b"], ["c"]])


def test_rows_to_markdown_returns_empty_string_for_no_rows():
    assert rows_to_markdown([]) == ""


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
