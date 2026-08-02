from pathlib import Path

import pytest

from src.rag.chunker import build_citation_label, chunk_sections
from src.rag.loaders import load_all
from src.rag.models import RawSection


def _pdf_section(text: str) -> RawSection:
    return RawSection(
        source_file="Aksef.pdf",
        doc_type="pdf",
        text=text,
        section_id="4.2",
        section_title="Pozoloji ve uygulama şekli",
        page_start=2,
        page_end=2,
    )


def test_citation_label_for_pdf_includes_section_and_page():
    label = build_citation_label(_pdf_section("x"))

    assert label == "Aksef.pdf — Bölüm 4.2 Pozoloji ve uygulama şekli, s.2"


def test_citation_label_for_docx_uses_the_heading_path():
    section = RawSection(
        source_file="arac.docx",
        doc_type="docx",
        text="x",
        section_path="3. ARAÇ TAHSİS POLİTİKASI",
    )

    assert build_citation_label(section) == "arac.docx — 3. ARAÇ TAHSİS POLİTİKASI"


def test_citation_label_for_xlsx_uses_sheet_and_row():
    section = RawSection(
        source_file="sss.xlsx", doc_type="xlsx", text="x", sheet="Genel SSS", row=5
    )

    assert build_citation_label(section) == "sss.xlsx — Genel SSS, satır 5"


def test_short_section_becomes_exactly_one_chunk():
    chunks = chunk_sections([_pdf_section("kısa metin")])

    assert len(chunks) == 1
    assert chunks[0].text == "kısa metin"


def test_long_section_splits_into_multiple_chunks_within_the_limit():
    paragraphs = "\n\n".join("p" * 400 for _ in range(6))

    chunks = chunk_sections([_pdf_section(paragraphs)], max_chars=1200, overlap=150)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 1200 + 150 for chunk in chunks)


def test_a_single_paragraph_longer_than_the_limit_is_split_to_fit():
    # KUB sections are one unbroken paragraph of several thousand characters,
    # so there is no "\n\n" for the splitter to break on.
    chunks = chunk_sections([_pdf_section("c" * 5000)], max_chars=1200, overlap=150)

    assert all(len(chunk.text) <= 1200 for chunk in chunks)


def test_hard_splitting_a_long_paragraph_drops_no_sentence():
    # A splitter that cut at a sentence boundary but advanced by max_chars
    # would silently lose the text between the two positions.
    sentences = [f"cumle{index}." for index in range(600)]

    chunks = chunk_sections([_pdf_section(" ".join(sentences))], max_chars=1200, overlap=150)

    combined = " ".join(chunk.text for chunk in chunks)
    assert [sentence for sentence in sentences if sentence not in combined] == []


def test_spreadsheet_rows_are_never_split_even_when_long():
    section = RawSection(
        source_file="taxonomy.xlsx",
        doc_type="xlsx",
        text="x" * 3000,
        sheet="Sheet1",
        row=4,
    )

    chunks = chunk_sections([section], max_chars=1200, overlap=150)

    assert len(chunks) == 1
    assert len(chunks[0].text) == 3000


def test_chunk_search_text_is_ascii_folded():
    chunks = chunk_sections([_pdf_section("İnsan Kaynakları")])

    assert "insan kaynaklari" in chunks[0].search_text
    assert chunks[0].search_text == chunks[0].search_text.casefold()


def test_search_text_includes_the_section_heading():
    # "Kontrendikasyonlar" is the title of KUB section 4.3 but never appears in
    # its body, so a query naming the section can only match via the heading.
    section = RawSection(
        source_file="Aksef.pdf",
        doc_type="pdf",
        text="Sefuroksime aşırı duyarlılığı olanlarda kullanılmamalıdır.",
        section_id="4.3",
        section_title="Kontrendikasyonlar",
        page_start=3,
    )

    chunk = chunk_sections([section])[0]

    assert "kontrendikasyonlar" in chunk.search_text
    assert "Kontrendikasyonlar" not in chunk.text  # display text stays as loaded


def test_chunk_ids_are_unique_across_sections():
    sections = [_pdf_section("a"), _pdf_section("b")]

    ids = [chunk.chunk_id for chunk in chunk_sections(sections)]

    assert len(ids) == len(set(ids))


def test_metadata_carries_location_fields_as_scalars():
    chunks = chunk_sections([_pdf_section("metin")])

    metadata = chunks[0].metadata

    assert metadata["source_file"] == "Aksef.pdf"
    assert metadata["section_id"] == "4.2"
    assert metadata["page_start"] == 2
    assert metadata["sheet"] == ""  # None becomes "" for Chroma compatibility
    assert metadata["row"] == -1


@pytest.mark.integration
def test_corpus_produces_a_chunk_count_in_the_expected_range():
    chunks = chunk_sections(load_all(Path("data")))

    assert 250 <= len(chunks) <= 450


@pytest.mark.integration
def test_every_chunk_has_a_non_empty_citation_label():
    chunks = chunk_sections(load_all(Path("data")))

    assert all(chunk.citation_label.strip() for chunk in chunks)


@pytest.mark.integration
def test_the_fuel_limit_table_value_survives_chunking():
    chunks = chunk_sections(load_all(Path("data")))

    assert any("1.500 TL/ay" in chunk.text for chunk in chunks)
