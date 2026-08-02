"""Terminal front-end for the RAG agent."""

import sys

from src.rag.agent import Agent
from src.rag.config import Config
from src.rag.index import load_index
from src.rag.llm import get_client
from src.rag.models import Answer
from src.rag.retriever import Retriever
from src.rag.tools import ToolBox

_EXIT_WORDS = {"çıkış", "cikis", "exit", "quit"}


def build_agent(config: Config | None = None) -> Agent:
    """Wire the agent from a previously built index."""
    config = config or Config.load()
    index = load_index(config.storage_dir, config.embedding_model)
    retriever = Retriever(index, min_cosine=config.min_cosine, min_bm25=config.min_bm25)
    return Agent(retriever, ToolBox(retriever), get_client(config), config.max_tool_turns)


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
