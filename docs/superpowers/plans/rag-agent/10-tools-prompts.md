# Task 10: Tools and prompts

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** [Task 9](09-retriever.md)
**Next:** [Task 11](11-llm-providers.md)

---

**Files:**
- Create: `src/rag/tools.py`, `src/rag/prompts.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `Retriever`, `LoadedIndex`, `Chunk`
- Produces: `TOOL_SCHEMAS: list[dict]`, class `ToolBox(retriever: Retriever)` with methods `search_documents(query, top_k=5, source_filter=None) -> str`, `lookup_section(document, section) -> str`, `list_documents() -> str`, and `run(name: str, arguments: dict) -> str`; from prompts: `SYSTEM_PROMPT: str`, `REFUSAL_TEMPLATE: str`, `NO_INFO_TEMPLATE: str`

Tool output is numbered (`[1]`, `[2]`) so the model can cite by number and the post-check in Task 12 can match citations back to real sources.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tools.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tools.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.tools'`

- [ ] **Step 3: Write `src/rag/prompts.py`**

```python
"""Turkish user-facing prompt and refusal templates."""

SYSTEM_PROMPT = """Sen bir şirket iç bilgi tabanı asistanısın.

Kurallar:
1. SADECE araçlardan (tool) gelen belge içeriğine dayanarak cevap ver.
   Kendi genel bilgini kullanma.
2. Her bilgi için kaynağını [1], [2] gibi numaralarla göster.
   Cevabın sonunda "Kaynaklar:" başlığı altında kullandığın kaynakları listele.
3. Araçlardan gelen içerikte cevap yoksa şunu söyle:
   "Bu konuda bilgi tabanımda bilgi bulamadım." Tahmin yürütme, uydurma.
4. Şirket bilgi tabanı dışındaki konularda (hava durumu, genel kültür, kişisel
   tavsiye vb.) kibarca kapsam dışı olduğunu belirt.
5. Türkçe, kısa ve net cevap ver.
"""

REFUSAL_TEMPLATE = (
    "Bu soru şirket bilgi tabanımın kapsamı dışında görünüyor. "
    "Ben İK politikaları, araç kullanım prosedürü, çalışan SSS, ürün taksonomisi "
    "ve ilaç kısa ürün bilgisi (KÜB) belgeleri hakkındaki soruları yanıtlayabiliyorum."
)

NO_INFO_TEMPLATE = (
    "Bu konuda bilgi tabanımda bilgi bulamadım. "
    "Soruyu farklı kelimelerle sormayı deneyebilir veya ilgili departmana danışabilirsiniz."
)
```

- [ ] **Step 4: Write minimal `src/rag/tools.py`**

```python
"""The three tools exposed to the LLM, plus their JSON schemas."""

from typing import Any

from src.rag.normalize import fold_tr
from src.rag.retriever import Retriever

_MAX_TOP_K = 10

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_documents",
        "description": (
            "Şirket bilgi tabanında doğal dil sorgusuyla arama yapar. "
            "İlgili doküman parçalarını kaynak bilgisiyle birlikte döndürür."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Arama sorgusu (Türkçe)"},
                "top_k": {"type": "integer", "description": "Sonuç sayısı (varsayılan 5, en fazla 10)"},
                "source_filter": {
                    "type": "string",
                    "description": "Belge adı filtresi, örneğin 'Aksef' veya 'ik_surecleri'",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "lookup_section",
        "description": (
            "Belirli bir belgenin belirli bir bölümünü doğrudan getirir. "
            "Bölüm numarası veya başlığı biliniyorsa aramak yerine bunu kullan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "document": {"type": "string", "description": "Belge adının bir parçası"},
                "section": {"type": "string", "description": "Bölüm numarası veya başlığı"},
            },
            "required": ["document", "section"],
        },
    },
    {
        "name": "list_documents",
        "description": "Bilgi tabanındaki tüm belgeleri ve tiplerini listeler.",
        "parameters": {"type": "object", "properties": {}},
    },
]


class ToolBox:
    """Executes tool calls against the retriever and index."""

    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    def search_documents(
        self, query: str, top_k: int = 5, source_filter: str | None = None
    ) -> str:
        hits = self.retriever.search(query, min(int(top_k), _MAX_TOP_K), source_filter)
        if not hits:
            return "Bu sorgu için sonuç bulunamadı."
        blocks = [
            f"[{position}] {hit.chunk.citation_label}\n{hit.chunk.text}"
            for position, hit in enumerate(hits, start=1)
        ]
        return "\n\n".join(blocks)

    def lookup_section(self, document: str, section: str) -> str:
        document_key = fold_tr(document)
        section_key = fold_tr(section)
        matches = [
            chunk
            for chunk in self.retriever.index.chunks
            if document_key in fold_tr(chunk.metadata["source_file"])
            and (
                fold_tr(chunk.metadata.get("section_id", "")) == section_key
                or section_key in fold_tr(chunk.metadata.get("section_title", ""))
                or section_key in fold_tr(chunk.metadata.get("section_path", ""))
            )
        ]
        if not matches:
            return f"'{document}' belgesinde '{section}' bölümü bulunamadı."
        return "\n\n".join(
            f"[{position}] {chunk.citation_label}\n{chunk.text}"
            for position, chunk in enumerate(matches, start=1)
        )

    def list_documents(self) -> str:
        seen: dict[str, str] = {}
        for chunk in self.retriever.index.chunks:
            seen.setdefault(chunk.metadata["source_file"], chunk.metadata["doc_type"])
        return "\n".join(f"- {name} ({doc_type})" for name, doc_type in sorted(seen.items()))

    def run(self, name: str, arguments: dict[str, Any]) -> str:
        """Dispatch a tool call by name."""
        if name == "search_documents":
            return self.search_documents(**arguments)
        if name == "lookup_section":
            return self.lookup_section(**arguments)
        if name == "list_documents":
            return self.list_documents()
        raise ValueError(f"unknown tool: {name}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_tools.py -v --no-cov`
Expected: PASS (10 passed)

- [ ] **Step 6: Run quality gate and commit**

```bash
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70
git add src/rag/tools.py src/rag/prompts.py tests/test_tools.py
git commit -m "feat(tools): add search, lookup, and list tools with Turkish prompts"
```
