"""Index construction with an injected embedder."""

from azure.rag.index import COLLECTION_NAME, build_index, load_index
from azure.rag.models import Chunk


class SpyEmbedder:
    """Records exactly what text was embedded."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.seen.extend(texts)
        return [[1.0, 0.0, 0.0] for _ in texts]


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        search_text=text,
        citation_label=f"belge.docx — {chunk_id}",
        metadata={"source_file": "belge.docx"},
    )


def test_embeds_search_text_without_e5_prefix(tmp_path):
    """`passage:` is an e5 artifact; it must not reach text-embedding-3-small."""
    embedder = SpyEmbedder()

    build_index([_chunk("c1", "yillik izin")], tmp_path, embedder)

    assert embedder.seen == ["yillik izin"]
    assert not any(text.startswith("passage:") for text in embedder.seen)


def test_report_counts_chunks_per_file(tmp_path):
    chunks = [_chunk("c1", "bir"), _chunk("c2", "iki")]

    report = build_index(chunks, tmp_path, SpyEmbedder())

    assert report.chunk_count == 2
    assert report.per_file == {"belge.docx": 2}
    assert report.seconds >= 0


def test_load_index_round_trips_chunks(tmp_path):
    build_index([_chunk("c1", "bir")], tmp_path, SpyEmbedder())

    loaded = load_index(tmp_path)

    assert [chunk.chunk_id for chunk in loaded.chunks] == ["c1"]
    assert loaded.collection.name == COLLECTION_NAME
    assert loaded.bm25 is not None


def test_rebuild_replaces_the_collection(tmp_path):
    """A second build must not append to the first."""
    build_index([_chunk("c1", "bir")], tmp_path, SpyEmbedder())
    build_index([_chunk("c2", "iki")], tmp_path, SpyEmbedder())

    loaded = load_index(tmp_path)

    assert [chunk.chunk_id for chunk in loaded.chunks] == ["c2"]
    assert loaded.collection.count() == 1
