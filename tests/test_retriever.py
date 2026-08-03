from pathlib import Path

import pytest

from src.rag.index import LoadedIndex, load_index
from src.rag.models import Chunk, SearchHit
from src.rag.retriever import Retriever, reciprocal_rank_fusion

STORAGE = Path("storage")


def _gate(*hits: tuple[float, float]) -> bool:
    """Run the confidence gate over hits given as (cosine, bm25) pairs."""
    retriever = Retriever(LoadedIndex(collection=None, bm25=None, chunks=[]))
    return retriever.is_confident(
        [
            SearchHit(
                chunk=Chunk(
                    chunk_id="x", text="x", search_text="x", citation_label="x", metadata={}
                ),
                score=0.0,
                cosine=cosine,
                bm25=bm25,
            )
            for cosine, bm25 in hits
        ]
    )


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    if not (STORAGE / "chunks.jsonl").exists():
        pytest.skip("index not built; run python scripts/ingest.py")
    return Retriever(load_index(STORAGE))


def test_fusion_ranks_a_chunk_found_by_both_rankers_first():
    dense = ["a", "b", "c"]
    lexical = ["c", "a", "d"]

    scores = reciprocal_rank_fusion([dense, lexical])

    assert max(scores, key=scores.get) == "a"


def test_fusion_score_matches_the_reciprocal_rank_formula():
    scores = reciprocal_rank_fusion([["a"], ["a"]], k=60)

    assert scores["a"] == pytest.approx(2 / 61)


def test_fusion_includes_chunks_seen_by_only_one_ranker():
    scores = reciprocal_rank_fusion([["a"], ["b"]])

    assert set(scores) == {"a", "b"}


def test_fusion_of_no_rankings_is_empty():
    assert reciprocal_rank_fusion([]) == {}


def test_confidence_rejects_high_similarity_with_no_lexical_support():
    # Measured: the off-topic "Bana bir şiir yaz" reaches cosine 0.813 at bm25 0.0,
    # higher than the weakest valid question. Similarity alone cannot separate them.
    assert not _gate((0.813, 0.0))


def test_confidence_rejects_a_lexical_match_the_meaning_does_not_support():
    # Measured: the off-topic "En sevdiğin film hangisi?" reaches bm25 8.25 at cosine 0.746.
    assert not _gate((0.746, 8.25))


def test_confidence_accepts_the_weakest_valid_question():
    # Measured: "OPS-PRO-003", the weakest of the ten valid probes.
    assert _gate((0.811, 7.55))


def test_no_hits_is_never_confident():
    assert not _gate()


@pytest.mark.integration
def test_turkish_query_finds_the_ascii_folded_hr_document(retriever):
    # Proves the fold_tr fix: the query is spelled correctly, the document is not.
    hits = retriever.search("İnsan Kaynakları yıllık izin", top_k=3)

    sources = [hit.chunk.metadata["source_file"] for hit in hits]

    assert any("ik_surecleri" in source or "calisan_sss" in source for source in sources)


@pytest.mark.integration
def test_document_code_is_matched_exactly(retriever):
    # Proves BM25 pulls its weight: dense embeddings do not reliably match codes.
    hits = retriever.search("OPS-PRO-003", top_k=3)

    assert "arac_kullanim" in hits[0].chunk.metadata["source_file"]


@pytest.mark.integration
def test_drug_section_query_lands_on_the_right_section(retriever):
    hits = retriever.search("Aksef kontrendikasyonları", top_k=3)

    assert "Aksef" in hits[0].chunk.metadata["source_file"]
    assert hits[0].chunk.metadata["section_id"].startswith("4.3")


@pytest.mark.integration
def test_product_lookup_finds_the_taxonomy_row(retriever):
    hits = retriever.search("Vitatin95 ürün müdürü", top_k=3)

    assert any("Vitatin95" in hit.chunk.text for hit in hits)


@pytest.mark.integration
def test_source_filter_restricts_results_to_one_document(retriever):
    hits = retriever.search("pozoloji", top_k=5, source_filter="Duxet")

    assert hits
    assert all("Duxet" in hit.chunk.metadata["source_file"] for hit in hits)


@pytest.mark.integration
def test_off_topic_question_is_not_confident(retriever):
    hits = retriever.search("Bugün hava nasıl olacak?", top_k=5)

    assert not retriever.is_confident(hits)


@pytest.mark.integration
def test_in_domain_question_is_confident(retriever):
    hits = retriever.search("Yıllık izin talebimi nasıl yaparım?", top_k=5)

    assert retriever.is_confident(hits)


@pytest.mark.integration
def test_a_bare_follow_up_question_would_be_refused(retriever):
    # The risk memory introduces: on its own this text resembles no document,
    # so the score gate treats it as off-topic.
    hits = retriever.search("peki ya müdür seviyesinde?", top_k=5)

    assert not retriever.is_confident(hits)


@pytest.mark.integration
def test_the_enriched_follow_up_finds_the_vehicle_procedure(retriever):
    from src.rag.memory import ConversationMemory, retrieval_query

    memory = ConversationMemory()
    memory.add("Direktör seviyesindeki bir çalışanın aylık yakıt limiti nedir?", "1.500 TL/ay")

    hits = retriever.search(retrieval_query("peki ya müdür seviyesinde?", memory), top_k=5)

    assert retriever.is_confident(hits)
    assert any("arac_kullanim" in hit.chunk.metadata["source_file"] for hit in hits)
