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
