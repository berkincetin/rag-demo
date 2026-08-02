"""Terminal front-end for the RAG agent."""

import sys
from dataclasses import replace

from src.rag.agent import Agent
from src.rag.config import Config
from src.rag.index import load_index
from src.rag.llm import get_client
from src.rag.metrics import MetricsStore
from src.rag.models import Answer
from src.rag.retriever import Retriever
from src.rag.tools import ToolBox

_EXIT_WORDS = {"çıkış", "cikis", "exit", "quit"}


def resolve_provider(model_id: str) -> str:
    """Which provider serves this model. Anything not in the catalog is local."""
    from src.rag.catalog import get_model

    model = get_model(model_id)
    return model.provider if model else "ollama"


def build_agent(
    config: Config | None = None,
    model_id: str | None = None,
    session=None,
) -> Agent:
    """Wire the agent from a previously built index.

    `model_id` overrides the configured model (the UI picks one per session) and
    `session` carries the in-memory credential store so a browser-entered key is
    used without ever touching the environment.
    """
    config = config or Config.load()
    if model_id:
        config = replace(config, llm_model=model_id, llm_provider=resolve_provider(model_id))

    credentials = None
    if session is not None:
        from src.rag.ui_state import get_store

        credentials = get_store(session)

    index = load_index(config.storage_dir, config.embedding_model)
    retriever = Retriever(index, min_cosine=config.min_cosine, min_bm25=config.min_bm25)
    metrics = MetricsStore(config.storage_dir / "metrics.db")
    return Agent(
        retriever,
        ToolBox(retriever),
        get_client(config, credentials=credentials),
        config.max_tool_turns,
        metrics=metrics,
    )


def format_answer(answer: Answer) -> str:
    """Render an answer with its numbered source list."""
    if not answer.citations:
        return answer.text
    sources = "\n".join(
        f"  {position}. {label}" for position, label in enumerate(answer.citations, start=1)
    )
    return f"{answer.text}\n\nKaynaklar:\n{sources}"


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    agent = build_agent()

    if argv:
        print(format_answer(agent.answer(" ".join(argv))))
        return 0

    print("Soru sorun ('çıkış' ile bitirin).")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            return 0
        if not question or question.lower() in _EXIT_WORDS:
            return 0
        print("\n" + format_answer(agent.answer(question)))


if __name__ == "__main__":
    raise SystemExit(main())
