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
