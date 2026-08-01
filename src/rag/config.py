"""Environment-backed configuration for the RAG agent."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Runtime settings. Defaults match docs/bolum1-rag/TRD.md section 5."""

    data_dir: Path
    storage_dir: Path
    embedding_model: str
    chunk_max_chars: int
    chunk_overlap: int
    top_k: int
    min_cosine: float
    max_tool_turns: int
    llm_provider: str
    llm_model: str

    @classmethod
    def load(cls) -> "Config":
        """Build a Config from environment variables, falling back to defaults."""
        load_dotenv()
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", "./data")),
            storage_dir=Path(os.getenv("STORAGE_DIR", "./storage")),
            embedding_model=os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"),
            chunk_max_chars=int(os.getenv("CHUNK_MAX_CHARS", "1200")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
            top_k=int(os.getenv("TOP_K", "5")),
            min_cosine=float(os.getenv("MIN_COSINE", "0.72")),
            max_tool_turns=int(os.getenv("MAX_TOOL_TURNS", "3")),
            llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
            llm_model=os.getenv("LLM_MODEL", "qwen2.5:7b-instruct"),
        )
