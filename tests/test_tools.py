import pytest

from src.rag.models import Chunk, SearchHit
from src.rag.tools import TOOL_SCHEMAS, ToolBox


class _FakeRetriever:
    def __init__(self, hits):
        self._hits = hits
        self.index = type("Index", (), {"chunks": [hit.chunk for hit in hits]})()
        self.last_call = None

    def search(self, query, top_k=5, source_filter=None):
        self.last_call = (query, top_k, source_filter)
        return self._hits


def _hit(chunk_id="c1", text="Kontrendikasyon metni", source="Aksef.pdf", section="4.3"):
    chunk = Chunk(
        chunk_id=chunk_id,
        text=text,
        search_text=text.lower(),
        citation_label=f"{source} — Bölüm {section}, s.3",
        metadata={
            "source_file": source,
            "doc_type": "pdf",
            "section_id": section,
            "section_title": "Kontrendikasyonlar",
        },
    )
    return SearchHit(chunk=chunk, score=0.5, cosine=0.8, bm25=9.0)


def test_three_tools_are_exposed_with_the_documented_names():
    names = [schema["name"] for schema in TOOL_SCHEMAS]

    assert names == ["search_documents", "lookup_section", "list_documents"]


def test_every_tool_schema_declares_a_description_and_parameters():
    for schema in TOOL_SCHEMAS:
        assert schema["description"].strip()
        assert "parameters" in schema


def test_search_documents_numbers_results_and_shows_citations():
    box = ToolBox(_FakeRetriever([_hit()]))

    output = box.search_documents("kontrendikasyon")

    assert output.startswith("[1] Aksef.pdf — Bölüm 4.3, s.3")
    assert "Kontrendikasyon metni" in output


def test_search_documents_reports_no_results_plainly():
    box = ToolBox(_FakeRetriever([]))

    assert "sonuç bulunamadı" in box.search_documents("xyz").lower()


def test_search_documents_caps_top_k_at_ten():
    retriever = _FakeRetriever([_hit()])
    ToolBox(retriever).search_documents("q", top_k=50)

    assert retriever.last_call[1] == 10


def test_lookup_section_returns_the_matching_section():
    box = ToolBox(_FakeRetriever([_hit()]))

    output = box.lookup_section("Aksef", "4.3")

    assert "Kontrendikasyon metni" in output


def test_lookup_section_reports_a_miss_without_raising():
    box = ToolBox(_FakeRetriever([_hit()]))

    assert "bulunamadı" in box.lookup_section("Aksef", "9.9").lower()


def test_list_documents_lists_each_source_once():
    box = ToolBox(_FakeRetriever([_hit(), _hit(chunk_id="c2")]))

    assert box.list_documents().count("Aksef.pdf") == 1


def test_run_dispatches_by_tool_name():
    box = ToolBox(_FakeRetriever([_hit()]))

    assert "[1]" in box.run("search_documents", {"query": "x"})


def test_run_rejects_an_unknown_tool_name():
    box = ToolBox(_FakeRetriever([]))

    with pytest.raises(ValueError, match="unknown tool"):
        box.run("delete_everything", {})
