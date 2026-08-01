from pathlib import Path

import pytest

from src.rag.loaders.pdf_loader import KUB_SECTION_IDS, load_pdf, parse_heading

DATA = Path("data")


def _find(pattern: str) -> Path:
    matches = sorted(DATA.glob(pattern))
    assert matches, f"no file matching {pattern} in {DATA}"
    return matches[0]


def test_parse_heading_accepts_a_numbered_kub_section():
    assert parse_heading("4.2 Pozoloji ve uygulama şekli") == ("4.2", "Pozoloji ve uygulama şekli")


def test_parse_heading_accepts_a_top_level_section_with_trailing_dot():
    assert parse_heading("1. BEŞERİ TIBBİ ÜRÜNÜN ADI") == ("1", "BEŞERİ TIBBİ ÜRÜNÜN ADI")


def test_parse_heading_rejects_a_line_that_is_not_a_heading():
    assert parse_heading("Etkin madde: Sefuroksim aksetil 601,44 mg") is None


def test_parse_heading_rejects_a_page_marker():
    assert parse_heading("1/12") is None


def test_kub_whitelist_covers_the_standard_section_numbers():
    assert "4.1" in KUB_SECTION_IDS
    assert "6.6" in KUB_SECTION_IDS
    # Footnote markers on Duxet page 15 look like headings but are not sections.
    assert "7" not in KUB_SECTION_IDS
    assert "10" not in KUB_SECTION_IDS


@pytest.mark.integration
def test_aksef_yields_at_least_twenty_sections():
    sections = load_pdf(_find("Aksef*.pdf"))

    assert len(sections) >= 20
    assert all(section.text for section in sections)


@pytest.mark.integration
def test_aksef_contraindications_section_starts_on_page_three():
    sections = load_pdf(_find("Aksef*.pdf"))

    section = next(s for s in sections if s.section_id == "4.3")

    assert section.page_start == 3
    assert "Kontrendikasyon" in section.section_title


@pytest.mark.integration
def test_duxet_footnote_markers_are_not_treated_as_sections():
    sections = load_pdf(_find("Duxet*.pdf"))

    ids = {section.section_id for section in sections}

    assert len(sections) >= 20
    assert "7" not in ids
    assert "10" not in ids
