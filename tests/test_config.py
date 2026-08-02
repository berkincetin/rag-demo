from pathlib import Path

from src.rag.config import Config


def test_load_returns_documented_defaults():
    cfg = Config.load()

    assert cfg.data_dir == Path("./data")
    assert cfg.storage_dir == Path("./storage")
    assert cfg.embedding_model == "intfloat/multilingual-e5-base"
    assert cfg.chunk_max_chars == 1200
    assert cfg.chunk_overlap == 150
    assert cfg.top_k == 5
    # Calibrated in Task 9 against the demo question set, replacing the
    # planned 0.72 which admitted every off-topic question.
    assert cfg.min_cosine == 0.80
    assert cfg.min_bm25 == 5.0
    assert cfg.max_tool_turns == 3
    assert cfg.llm_provider == "ollama"


def test_load_reads_overrides_from_environment(monkeypatch):
    monkeypatch.setenv("TOP_K", "9")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    cfg = Config.load()

    assert cfg.top_k == 9
    assert cfg.llm_provider == "anthropic"
