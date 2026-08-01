from src.rag.models import Answer, Chunk, RawSection, SearchHit


def test_rawsection_defaults_optional_location_fields_to_none():
    section = RawSection(source_file="a.pdf", doc_type="pdf", text="body")

    assert section.section_id is None
    assert section.page_start is None
    assert section.sheet is None


def test_chunk_carries_display_text_and_search_text_separately():
    chunk = Chunk(
        chunk_id="a__1__0",
        text="İnsan Kaynakları",
        search_text="insan kaynaklari",
        citation_label="a.pdf — Bölüm 1",
        metadata={"source_file": "a.pdf"},
    )

    assert chunk.text != chunk.search_text
    assert chunk.metadata["source_file"] == "a.pdf"


def test_searchhit_exposes_score_and_chunk():
    chunk = Chunk("id", "t", "t", "label", {})
    hit = SearchHit(chunk=chunk, score=0.5, cosine=0.8, bm25=1.2)

    assert hit.score == 0.5
    assert hit.chunk.chunk_id == "id"


def test_answer_defaults_to_empty_citations_and_trace():
    answer = Answer(text="cevap")

    assert answer.citations == []
    assert answer.tool_trace == []
