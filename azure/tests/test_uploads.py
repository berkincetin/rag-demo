"""Expiring, in-memory upload store.

Nothing here reaches disk. The tests pin the three properties that make that
safe: entries expire, limits are enforced, and one session can never read
another's documents.
"""

import pytest

from azure.rag.models import Chunk
from azure.rag.uploads import (
    UploadedDoc,
    UploadLimitError,
    UploadStore,
    build_uploaded_doc,
)


def _doc(filename="a.txt", chunk_count=1):
    chunks = [
        Chunk(
            chunk_id=f"{filename}-{index}",
            text=f"metin {index}",
            search_text=f"metin {index}",
            citation_label=f"{filename} — parça {index}",
            metadata={"source_file": filename},
        )
        for index in range(chunk_count)
    ]
    return UploadedDoc(filename=filename, chunks=chunks, vectors=[[0.1] * 4] * chunk_count)


# --- storage and isolation --------------------------------------------------


def test_added_document_is_returned_for_its_key():
    store = UploadStore()
    store.add("s1:c1", _doc("rapor.pdf"))

    assert [doc.filename for doc in store.get("s1:c1")] == ["rapor.pdf"]


def test_conversations_are_isolated_from_each_other():
    store = UploadStore()
    store.add("s1:c1", _doc("a.txt"))

    assert store.get("s1:c2") == []


def test_sessions_are_isolated_from_each_other():
    """The key embeds the session id; one user must never see another's upload."""
    store = UploadStore()
    store.add("s1:c1", _doc("gizli.pdf"))

    assert store.get("s2:c1") == []


def test_reuploading_the_same_filename_replaces_the_old_entry():
    store = UploadStore()
    store.add("k", _doc("a.txt", chunk_count=1))
    store.add("k", _doc("a.txt", chunk_count=3))

    docs = store.get("k")
    assert len(docs) == 1
    assert len(docs[0].chunks) == 3


def test_an_unknown_key_returns_an_empty_list():
    assert UploadStore().get("yok") == []


# --- limits -----------------------------------------------------------------


def test_exceeding_the_document_limit_raises():
    store = UploadStore(max_docs=2)
    store.add("k", _doc("a.txt"))
    store.add("k", _doc("b.txt"))

    with pytest.raises(UploadLimitError):
        store.add("k", _doc("c.txt"))


def test_replacing_a_document_does_not_count_against_the_document_limit():
    store = UploadStore(max_docs=2)
    store.add("k", _doc("a.txt"))
    store.add("k", _doc("b.txt"))

    store.add("k", _doc("a.txt", chunk_count=2))  # yükseltmemeli

    assert len(store.get("k")) == 2


def test_exceeding_the_chunk_limit_raises():
    store = UploadStore(max_chunks=5)
    store.add("k", _doc("a.txt", chunk_count=4))

    with pytest.raises(UploadLimitError):
        store.add("k", _doc("b.txt", chunk_count=2))


def test_a_rejected_upload_leaves_the_existing_documents_intact():
    store = UploadStore(max_docs=1)
    store.add("k", _doc("a.txt"))

    with pytest.raises(UploadLimitError):
        store.add("k", _doc("b.txt"))

    assert [doc.filename for doc in store.get("k")] == ["a.txt"]


# --- removal ----------------------------------------------------------------


def test_remove_drops_only_the_named_document():
    store = UploadStore()
    store.add("k", _doc("a.txt"))
    store.add("k", _doc("b.txt"))

    remaining = store.remove("k", "a.txt")

    assert [doc.filename for doc in remaining] == ["b.txt"]


def test_clear_empties_the_key():
    store = UploadStore()
    store.add("k", _doc("a.txt"))

    store.clear("k")

    assert store.get("k") == []


# --- expiry -----------------------------------------------------------------


def test_entries_expire_after_the_ttl():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))

    clock["now"] = 1061.0

    assert store.get("k") == []


def test_touching_an_entry_extends_its_life():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))

    clock["now"] = 1030.0
    assert store.get("k") != []  # bu erişim süreyi tazeler
    clock["now"] = 1080.0

    assert store.get("k") != []


def test_sweep_removes_expired_keys_without_access():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))
    clock["now"] = 1100.0

    store.sweep()

    assert store.get("k") == []


def test_sweep_keeps_live_keys():
    clock = {"now": 1000.0}
    store = UploadStore(ttl_seconds=60, clock=lambda: clock["now"])
    store.add("k", _doc("a.txt"))
    clock["now"] = 1030.0

    store.sweep()

    assert store.get("k") != []


# --- citation labels --------------------------------------------------------


class _StubEmbedder:
    def encode(self, texts):
        return [[1.0, 0.0] for _ in texts]


def test_uploaded_chunks_cite_the_users_filename_not_the_temp_file(tmp_path):
    """The parser needs a path, but its generated name must never reach a citation."""
    temp_like = tmp_path / "tmp2wt19fln.txt"
    temp_like.write_text("Gizli proje kodu ZPX-9981.", encoding="utf-8")

    doc = build_uploaded_doc(temp_like, _StubEmbedder(), display_name="ozel_proje.txt")

    assert doc.filename == "ozel_proje.txt"
    for chunk in doc.chunks:
        assert "tmp2wt19fln" not in chunk.citation_label
        assert "ozel_proje.txt" in chunk.citation_label


def test_a_text_upload_gets_a_clean_citation_label(tmp_path):
    """A plain text file has no section or page, so neither may be rendered."""
    path = tmp_path / "notlar.txt"
    path.write_text("Bir metin.", encoding="utf-8")

    doc = build_uploaded_doc(path, _StubEmbedder())

    label = doc.chunks[0].citation_label
    assert "None" not in label
    assert not label.rstrip().endswith("—")
    assert "notlar.txt" in label


def test_display_name_defaults_to_the_file_on_disk(tmp_path):
    path = tmp_path / "rapor.txt"
    path.write_text("içerik", encoding="utf-8")

    assert build_uploaded_doc(path, _StubEmbedder()).filename == "rapor.txt"
