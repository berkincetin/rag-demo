from pathlib import Path

import pandas as pd
import pytest

from src.rag.loaders.xlsx_loader import detect_header_row, load_xlsx, row_to_text

DATA = Path("data")


def _find(pattern: str) -> Path:
    matches = sorted(DATA.glob(pattern))
    assert matches, f"no file matching {pattern} in {DATA}"
    return matches[0]


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
