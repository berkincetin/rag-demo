"""Uploaded-document retrieval, fused with the corpus.

The gate is the subtle part. Layer 1 refuses off-topic questions on retrieval
score alone, before any LLM call — so a question only the uploaded file can
answer would be refused unless uploaded hits reach the gate too.
"""

from dataclasses import dataclass, field

from azure.rag.models import Chunk, SearchHit
from azure.rag.upload_search import UploadAwareRetriever, search_uploads
from azure.rag.uploads import UploadedDoc, UploadStore


def _chunk(chunk_id, text):
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        search_text=text.lower(),
        citation_label=f"yuklenen.txt — {chunk_id}",
        metadata={"source_file": "yuklenen.txt"},
    )


def _doc():
    return UploadedDoc(
        filename="yuklenen.txt",
        chunks=[_chunk("u1", "kurumsal arac tahsis kurallari"), _chunk("u2", "kedi besleme")],
        vectors=[[1.0, 0.0], [0.0, 1.0]],
    )


# --- ranking uploaded chunks ------------------------------------------------


def test_search_uploads_ranks_the_semantically_closest_chunk_first():
    hits = search_uploads([_doc()], query="arac tahsis", query_vector=[1.0, 0.0], top_k=2)

    assert hits[0].chunk.chunk_id == "u1"


def test_search_uploads_reports_the_cosine_it_computed():
    hits = search_uploads([_doc()], query="arac", query_vector=[1.0, 0.0], top_k=1)

    assert hits[0].cosine == 1.0


def test_search_uploads_returns_nothing_without_documents():
    assert search_uploads([], query="x", query_vector=[1.0, 0.0], top_k=3) == []


def test_search_uploads_respects_top_k():
    assert len(search_uploads([_doc()], "x", [1.0, 0.0], top_k=1)) == 1


def test_search_uploads_carries_the_citation_label():
    hits = search_uploads([_doc()], "arac", [1.0, 0.0], top_k=1)

    assert hits[0].chunk.citation_label == "yuklenen.txt — u1"


# --- the retriever wrapper --------------------------------------------------


class _Embedder:
    def encode(self, texts):
        return [[1.0, 0.0] for _ in texts]


class _OrthogonalEmbedder:
    def encode(self, texts):
        return [[0.0, 0.0] for _ in texts]


@dataclass
class _StubBase:
    """Stands in for the corpus Retriever."""

    hits: list = field(default_factory=list)
    confident: bool = False
    min_cosine: float = 0.25
    min_bm25: float = 4.22
    index: object = None
    embedder: object = None
    seen_confidence_input: list = field(default_factory=list)

    def search(self, query, top_k=5, source_filter=None):
        return list(self.hits)

    def is_confident(self, hits):
        self.seen_confidence_input.append(list(hits))
        return self.confident


def _corpus_hit(chunk_id="c1", cosine=0.9, bm25=9.0):
    return SearchHit(chunk=_chunk(chunk_id, "korpus metni"), score=0.5, cosine=cosine, bm25=bm25)


def test_wrapper_merges_corpus_and_uploaded_hits():
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[_corpus_hit()], confident=True, embedder=_Embedder())

    hits = UploadAwareRetriever(base, "k", store).search("arac tahsis", top_k=5)

    ids = {hit.chunk.chunk_id for hit in hits}
    assert "c1" in ids and "u1" in ids


def test_wrapper_behaves_like_the_base_when_nothing_is_uploaded():
    base = _StubBase(hits=[_corpus_hit()], confident=True, embedder=_Embedder())

    hits = UploadAwareRetriever(base, "k", UploadStore()).search("soru", top_k=5)

    assert [hit.chunk.chunk_id for hit in hits] == ["c1"]


def test_wrapper_respects_top_k_after_merging():
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[_corpus_hit("c1"), _corpus_hit("c2")], embedder=_Embedder())

    assert len(UploadAwareRetriever(base, "k", store).search("arac", top_k=2)) == 2


def test_wrapper_mirrors_the_base_thresholds():
    base = _StubBase(embedder=_Embedder(), min_cosine=0.31, min_bm25=5.5)

    wrapper = UploadAwareRetriever(base, "k", UploadStore())

    assert (wrapper.min_cosine, wrapper.min_bm25) == (0.31, 5.5)


# --- the gate ---------------------------------------------------------------


def test_gate_passes_when_only_an_uploaded_chunk_is_relevant():
    """Without this the question is refused before the LLM sees the upload."""
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[], confident=False, embedder=_Embedder())
    retriever = UploadAwareRetriever(base, "k", store)

    hits = retriever.search("arac tahsis", top_k=5)

    assert retriever.is_confident(hits) is True


def test_gate_still_refuses_when_the_uploaded_chunk_is_far_away():
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[], confident=False, embedder=_OrthogonalEmbedder())
    retriever = UploadAwareRetriever(base, "k", store)

    hits = retriever.search("alakasiz", top_k=5)

    assert retriever.is_confident(hits) is False


def test_gate_defers_to_the_base_for_corpus_only_hits():
    base = _StubBase(hits=[_corpus_hit()], confident=True, embedder=_Embedder())
    retriever = UploadAwareRetriever(base, "k", UploadStore())

    assert retriever.is_confident(retriever.search("soru", top_k=5)) is True


def test_the_base_gate_never_sees_uploaded_hits():
    """Uploaded BM25 is on a different IDF basis; feeding it to the measured
    two-signal rule would compare incomparable numbers."""
    store = UploadStore()
    store.add("k", _doc())
    base = _StubBase(hits=[_corpus_hit()], confident=False, embedder=_Embedder())
    retriever = UploadAwareRetriever(base, "k", store)

    retriever.is_confident(retriever.search("arac", top_k=5))

    passed_ids = {hit.chunk.chunk_id for hit in base.seen_confidence_input[-1]}
    assert passed_ids == {"c1"}
