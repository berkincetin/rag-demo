"""Araç bütçesi dolduğunda toplanan bağlam çöpe gitmemeli.

Ölçülmüş kusur (2026-08-17, canlı `gpt-5-mini`): akıl yürüten model sistem
promptundaki "cevap vermeden önce HER ZAMAN ara" talimatını her turda yeniden
değerlendirip aynı aramayı tekrarlıyor. Tur bütçesi dolduğunda grafik doğrudan
`citation_check`'e gidiyordu; orada `final_text` boş olduğu için `repair` de
devreye giremiyor (o dal metin varlığına bakıyor) ve altı aramalık doğru bağlam
kullanılmadan `no_info` dönüyordu.

Aynı soruya `gpt-4.1-mini` 2 turda 2 atıflı doğru cevap veriyor — yani sorun
bağlamda değil, bütçe bitince modelden cevap istenmemesinde.
"""

from types import SimpleNamespace

from azure.rag.graph import build_graph, initial_state
from azure.rag.models import Chunk, SearchHit


class _StubRetriever:
    def __init__(self, confident: bool = True):
        self._confident = confident
        chunk = Chunk(
            "c1",
            "Yıllık izin HRPortal üzerinden alınır.",
            "yillik izin hrportal",
            "calisan_sss_rehberi.xlsx — Genel SSS, satır 4",
            {},
        )
        self.index = SimpleNamespace(chunks=[chunk])
        self._hits = [SearchHit(chunk=chunk, score=0.5, cosine=0.9, bm25=9.0)]

    def search(self, query, top_k=5, source_filter=None):
        return self._hits

    def is_confident(self, hits):
        return self._confident


class _StubToolBox:
    def __init__(self):
        self.calls = []

    def run(self, name, arguments):
        self.calls.append((name, arguments))
        return (
            "[1] calisan_sss_rehberi.xlsx — Genel SSS, satır 4\n"
            "Yıllık izin HRPortal üzerinden alınır."
        )


def _tool_call(query="yıllık izin"):
    return SimpleNamespace(id="t1", name="search_documents", arguments={"query": query})


class _AlwaysSearches:
    """Hiç metin yazmayan, her turda aynı aramayı tekrarlayan model.

    `gpt-5-mini`'nin canlıda ölçülen davranışı. `final_answer` verildiğinde,
    araçsız sorulan turda ne döndüreceğini belirler.
    """

    def __init__(self, final_answer: str | None = None):
        self.calls: list[dict] = []
        self.final_answer = final_answer

    def chat(self, messages, tools=None):
        self.calls.append({"tools": tools, "messages": list(messages)})
        usage = SimpleNamespace(input_tokens=10, output_tokens=5)
        # Araç şeması verilmediğinde model artık arayamaz; cevabını yazar.
        if not tools and self.final_answer is not None:
            return SimpleNamespace(text=self.final_answer, tool_calls=[], usage=usage)
        return SimpleNamespace(text=None, tool_calls=[_tool_call()], usage=usage)


def _run(llm, max_tool_turns=3):
    graph = build_graph(_StubRetriever(), _StubToolBox(), llm, max_tool_turns)
    return graph.invoke(initial_state("Yıllık izin talebimi nasıl yaparım?"))


def test_an_exhausted_budget_still_asks_the_model_to_answer():
    """Bütçe bitince model araçsız bir turla cevap yazmaya çağrılmalı."""
    llm = _AlwaysSearches(final_answer="Yıllık izin HRPortal'dan alınır [1].")

    state = _run(llm)

    assert state["final_text"] == "Yıllık izin HRPortal'dan alınır [1]."
    assert state["citations"] == ["calisan_sss_rehberi.xlsx — Genel SSS, satır 4"]


def test_the_final_turn_withholds_the_tools():
    """Araç şeması gönderilirse model aramayı yine tekrarlar; bu turda verilmez."""
    llm = _AlwaysSearches(final_answer="Cevap [1].")

    _run(llm)

    assert llm.calls[-1]["tools"] is None


def test_the_context_gathered_before_the_budget_ran_out_is_kept():
    """Toplanan araç çıktısı son turda modelin önünde durmalı."""
    llm = _AlwaysSearches(final_answer="Cevap [1].")

    _run(llm)

    last = llm.calls[-1]["messages"]
    assert any("calisan_sss_rehberi.xlsx" in str(m.get("content", "")) for m in last)


def test_a_model_that_still_writes_nothing_falls_back_to_no_info():
    """Son tur da boş dönerse uydurma yapılmaz; bilgi yok cevabı verilir."""
    llm = _AlwaysSearches(final_answer=None)

    state = _run(llm)

    assert state["citations"] == []
    assert "bilgi bulamadım" in state["final_text"]


def test_a_model_that_answers_normally_is_unaffected():
    """gpt-4.1-mini yolu değişmemeli: tek arama, sonra atıflı cevap."""

    class _NormalModel:
        def __init__(self):
            self.calls = 0

        def chat(self, messages, tools=None):
            self.calls += 1
            usage = SimpleNamespace(input_tokens=10, output_tokens=5)
            if self.calls == 1:
                return SimpleNamespace(text=None, tool_calls=[_tool_call()], usage=usage)
            return SimpleNamespace(
                text="Yıllık izin HRPortal'dan alınır [1].", tool_calls=[], usage=usage
            )

    llm = _NormalModel()
    state = _run(llm)

    assert llm.calls == 2
    assert state["citations"] == ["calisan_sss_rehberi.xlsx — Genel SSS, satır 4"]


# --- araç şeması metin üretimini bastıran modeller ---------------------------


class _SilentWithTools:
    """Araç şeması verildiğinde boş, çekildiğinde metin döndüren model.

    `Phi-4-mini-instruct`'ın canlıda ölçülen davranışı: araç sonucunu gördükten
    sonra `text=None` ve araç çağrısı da yok — tamamen boş yanıt (3/3 tekrar).
    Araç şeması gönderilmediğinde aynı bağlamla cevabını yazıyor (3/3).
    """

    def __init__(self, answer: str):
        self.answer = answer
        self.calls: list[dict] = []

    def chat(self, messages, tools=None):
        self.calls.append({"tools": tools})
        usage = SimpleNamespace(input_tokens=10, output_tokens=5)
        if tools is None:
            return SimpleNamespace(text=self.answer, tool_calls=[], usage=usage)
        if len(self.calls) == 1:
            return SimpleNamespace(text=None, tool_calls=[_tool_call()], usage=usage)
        # Araç sonucundan sonra: şema hâlâ önündeyken hiçbir şey yazmıyor.
        return SimpleNamespace(text=None, tool_calls=[], usage=usage)


def test_a_blank_turn_after_tools_is_retried_without_them():
    """Araçlar metni bastırıyorsa bütçeyi beklemeden cevap istenmeli."""
    llm = _SilentWithTools("Yıllık izin HRPortal'dan alınır [1].")

    state = _run(llm)

    assert state["final_text"] == "Yıllık izin HRPortal'dan alınır [1]."
    assert state["citations"] == ["calisan_sss_rehberi.xlsx — Genel SSS, satır 4"]


def test_the_retry_happens_before_the_budget_is_spent():
    """Model 2. turda susuyor; 3 turluk bütçenin dolmasını beklemeye gerek yok."""
    llm = _SilentWithTools("Cevap [1].")

    _run(llm, max_tool_turns=3)

    # 1) araç çağrısı, 2) araç sonrası boş tur, 3) araçsız cevap turu
    assert len(llm.calls) == 3
    assert llm.calls[-1]["tools"] is None
