"""The three tools exposed to the LLM, plus their JSON schemas."""

from typing import Any

from azure.rag.normalize import fold_tr
from azure.rag.retriever import Retriever

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
                "top_k": {
                    "type": "integer",
                    "description": "Sonuç sayısı (varsayılan 5, en fazla 10)",
                },
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

    def search_documents(self, query: str, top_k: int = 5, source_filter: str | None = None) -> str:
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
