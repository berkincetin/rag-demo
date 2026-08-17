"""Single-file loading for uploads.

The corpus contains no .txt file, so `SUPPORTED_SUFFIXES` and the ingest path
stay as they are; uploads get their own suffix set and dispatcher.
"""

import pytest

from azure.rag.loaders import SUPPORTED_SUFFIXES, UPLOAD_SUFFIXES, load_file
from azure.rag.loaders.txt_loader import load_txt


def test_load_txt_produces_one_section_named_after_the_file(tmp_path):
    path = tmp_path / "notlar.txt"
    path.write_text("Yıllık izin 14 gündür.", encoding="utf-8")

    sections = load_txt(path)

    assert len(sections) == 1
    assert sections[0].source_file == "notlar.txt"
    assert sections[0].doc_type == "txt"
    assert "Yıllık izin" in sections[0].text


def test_load_txt_reads_utf8_turkish_characters(tmp_path):
    path = tmp_path / "tr.txt"
    path.write_text("İnsan Kaynakları şğüöç", encoding="utf-8")

    assert "İnsan Kaynakları" in load_txt(path)[0].text


def test_load_txt_tolerates_a_non_utf8_file(tmp_path):
    """A user's file is not guaranteed to be UTF-8; decoding must not explode."""
    path = tmp_path / "latin.txt"
    path.write_bytes("Yıllık izin".encode("cp1254"))

    assert load_txt(path)[0].text.strip() != ""


def test_load_file_dispatches_on_the_suffix(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("merhaba", encoding="utf-8")

    assert load_file(path)[0].doc_type == "txt"


def test_load_file_is_case_insensitive_about_the_suffix(tmp_path):
    path = tmp_path / "A.TXT"
    path.write_text("merhaba", encoding="utf-8")

    assert load_file(path)[0].doc_type == "txt"


def test_load_file_rejects_an_unsupported_suffix(tmp_path):
    path = tmp_path / "a.exe"
    path.write_bytes(b"\x00")

    with pytest.raises(ValueError):
        load_file(path)


def test_upload_suffixes_cover_the_four_accepted_types():
    assert UPLOAD_SUFFIXES == {".pdf", ".docx", ".xlsx", ".txt"}


def test_corpus_suffixes_are_unchanged():
    """Adding .txt for uploads must not change what the ingest pipeline scans."""
    assert SUPPORTED_SUFFIXES == {".pdf", ".docx", ".xlsx"}
