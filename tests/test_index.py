import json

import pytest

from src.rag.chunker import chunk_sections
from src.rag.index import build_index, load_index
from src.rag.models import RawSection


def _tiny_corpus() -> list:
    sections = [
        RawSection(
            source_file="a.xlsx",
            doc_type="xlsx",
            text="Yıllık izin talebi HRPortal üzerinden yapılır.",
            sheet="Genel SSS",
            row=4,
        ),
        RawSection(
            source_file="b.xlsx",
            doc_type="xlsx",
            text="Havuz aracı FleetApp üzerinden talep edilir.",
            sheet="Genel SSS",
            row=5,
        ),
    ]
    return chunk_sections(sections)


@pytest.mark.integration
def test_build_index_writes_all_three_artifacts(tmp_path):
    report = build_index(_tiny_corpus(), tmp_path)

    assert (tmp_path / "chroma").exists()
    assert (tmp_path / "bm25.pkl").exists()
    assert (tmp_path / "chunks.jsonl").exists()
    assert report.chunk_count == 2


@pytest.mark.integration
def test_chunks_jsonl_round_trips_text_and_citation(tmp_path):
    build_index(_tiny_corpus(), tmp_path)

    lines = (tmp_path / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]

    assert len(records) == 2
    assert all(record["citation_label"] for record in records)
    assert any("HRPortal" in record["text"] for record in records)


@pytest.mark.integration
def test_rebuilding_is_idempotent(tmp_path):
    build_index(_tiny_corpus(), tmp_path)
    second = build_index(_tiny_corpus(), tmp_path)

    loaded = load_index(tmp_path)

    assert second.chunk_count == 2
    assert len(loaded.chunks) == 2
    assert loaded.collection.count() == 2


@pytest.mark.integration
def test_report_counts_chunks_per_source_file(tmp_path):
    report = build_index(_tiny_corpus(), tmp_path)

    assert report.per_file == {"a.xlsx": 1, "b.xlsx": 1}
