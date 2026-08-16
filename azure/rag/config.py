"""Environment-backed configuration for the Azure deployment.

Separate from src/rag/config.py on purpose: this deployment has no Ollama,
no local embedding model, and no session-scoped API keys. Its credentials
come from Container Apps secrets injected as environment variables.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Explicit path to azure/.env. A bare load_dotenv() searches upward from the
# current working directory and would pick up the repository's root .env,
# which belongs to the local (non-Azure) deployment. Loading a missing file
# is a no-op, which is correct inside the container where real environment
# variables supply everything.
_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"  # azure/.env

# These threshold/path/tuning variables are prefixed AZURE_ because
# src/rag/config.py reads unprefixed names (MIN_COSINE, MIN_BM25, TOP_K,
# MAX_TOOL_TURNS, DATA_DIR, STORAGE_DIR) via the same os.environ. Both
# configs call load_dotenv(), which only *sets* a variable if it is not
# already present — so whichever config loads first silently donates its
# value to the other when both run in one process (same container, same
# pytest session). Discovered when azure/tests/test_config.py and
# tests/test_config.py were run together: the local config's documented
# 0.80/5.0 defaults were replaced by the Azure placeholder -1.0. Do not
# remove this prefix without re-verifying that collision is gone.

# Placeholder thresholds. Task 8 replaces these with measured values.
# They are deliberately NOT the e5 numbers (0.80 / 5.0): those were
# calibrated against a different embedding model and are invalid here.
_UNCALIBRATED_COSINE = -1.0
_UNCALIBRATED_BM25 = -1.0


@dataclass(frozen=True)
class AzureConfig:
    """Runtime settings for the cloud-only deployment."""

    openai_endpoint: str
    openai_api_key: str | None
    api_version: str
    chat_deployment: str
    embedding_deployment: str
    storage_dir: Path
    data_dir: Path
    top_k: int
    min_cosine: float
    min_bm25: float
    max_tool_turns: int
    internal_token: str | None

    @classmethod
    def load(cls) -> "AzureConfig":
        """Build a config from environment variables."""
        load_dotenv(_ENV_PATH)
        return cls(
            openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            openai_api_key=os.getenv("AZURE_OPENAI_API_KEY") or None,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            chat_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini"),
            embedding_deployment=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
            ),
            storage_dir=Path(os.getenv("AZURE_STORAGE_DIR", "./azure/storage")),
            data_dir=Path(os.getenv("AZURE_DATA_DIR", "./data")),
            top_k=int(os.getenv("AZURE_TOP_K", "5")),
            min_cosine=float(os.getenv("AZURE_MIN_COSINE", str(_UNCALIBRATED_COSINE))),
            min_bm25=float(os.getenv("AZURE_MIN_BM25", str(_UNCALIBRATED_BM25))),
            max_tool_turns=int(os.getenv("AZURE_MAX_TOOL_TURNS", "3")),
            internal_token=os.getenv("INTERNAL_TOKEN") or None,
        )
