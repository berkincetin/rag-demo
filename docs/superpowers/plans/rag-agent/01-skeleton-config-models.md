# Task 1: Project skeleton, config, and data models

> Part of the [RAG Agent implementation plan](00-overview.md). Read
> [00-overview.md](00-overview.md) first — it holds the goal, architecture,
> and **Global Constraints** that apply to every task.
> Do not read the other task files; this one is self-contained.

**Previous:** none (first task)
**Next:** [Task 2](02-normalize.md)

---

**Files:**
- Create: `src/rag/__init__.py`, `src/rag/config.py`, `src/rag/models.py`, `src/rag/loaders/__init__.py`, `tests/__init__.py`, `requirements.txt`, `.env.example`, `pyproject.toml`
- Test: `tests/test_config.py`, `tests/test_models.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: `Config` (frozen dataclass with `data_dir: Path`, `storage_dir: Path`, `embedding_model: str`, `chunk_max_chars: int`, `chunk_overlap: int`, `top_k: int`, `min_cosine: float`, `max_tool_turns: int`, `llm_provider: str`, `llm_model: str`) and classmethod `Config.load() -> Config`; dataclasses `RawSection`, `Chunk`, `SearchHit`, `Answer` as defined below.

- [ ] **Step 1: Create directory skeleton and copy source documents**

```bash
mkdir -p src/rag/loaders scripts tests notebooks data storage
touch src/rag/__init__.py src/rag/loaders/__init__.py tests/__init__.py
cp "AI Engineer/Rag_Agent/"* data/
ls data/   # must list exactly 6 files
```

- [ ] **Step 2: Write `requirements.txt` with pinned versions**

```
chromadb==0.5.23
sentence-transformers==3.3.1
rank-bm25==0.2.2
pypdf==5.1.0
python-docx==1.1.2
pandas==2.2.3
openpyxl==3.1.5
streamlit==1.41.1
python-dotenv==1.0.1
requests==2.32.3
pytest==8.3.4
pytest-cov==6.0.0
ruff==0.8.4
```

- [ ] **Step 3: Write `pyproject.toml` with ruff, pytest, and coverage config**

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
markers = ["integration: touches real project data files"]
addopts = "--cov=src --cov-report=term-missing"

[tool.coverage.run]
source = ["src"]
omit = ["src/rag/llm.py", "app.py"]
```

- [ ] **Step 4: Append to `.gitignore`**

```
.venv/
storage/
data/
```

(`AI Engineer/`, `.claude/`, `figures/` are already ignored.)

- [ ] **Step 5: Write the failing test for `Config`**

```python
# tests/test_config.py
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
    assert cfg.min_cosine == 0.72
    assert cfg.max_tool_turns == 3
    assert cfg.llm_provider == "ollama"


def test_load_reads_overrides_from_environment(monkeypatch):
    monkeypatch.setenv("TOP_K", "9")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    cfg = Config.load()

    assert cfg.top_k == 9
    assert cfg.llm_provider == "anthropic"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_config.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.config'`

- [ ] **Step 7: Write minimal `src/rag/config.py`**

```python
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
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_config.py -v --no-cov`
Expected: PASS (2 passed)

- [ ] **Step 9: Write the failing test for the data models**

```python
# tests/test_models.py
from src.rag.models import Answer, Chunk, RawSection, SearchHit


def test_rawsection_defaults_optional_location_fields_to_none():
    section = RawSection(source_file="a.pdf", doc_type="pdf", text="body")

    assert section.section_id is None
    assert section.page_start is None
    assert section.sheet is None


def test_chunk_carries_display_text_and_search_text_separately():
    chunk = Chunk(
        chunk_id="a__1__0",
        text="İnsan Kaynakları",
        search_text="insan kaynaklari",
        citation_label="a.pdf — Bölüm 1",
        metadata={"source_file": "a.pdf"},
    )

    assert chunk.text != chunk.search_text
    assert chunk.metadata["source_file"] == "a.pdf"


def test_searchhit_exposes_score_and_chunk():
    chunk = Chunk("id", "t", "t", "label", {})
    hit = SearchHit(chunk=chunk, score=0.5, cosine=0.8, bm25=1.2)

    assert hit.score == 0.5
    assert hit.chunk.chunk_id == "id"


def test_answer_defaults_to_empty_citations_and_trace():
    answer = Answer(text="cevap")

    assert answer.citations == []
    assert answer.tool_trace == []
```

- [ ] **Step 10: Run test to verify it fails**

Run: `pytest tests/test_models.py -v --no-cov`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.rag.models'`

- [ ] **Step 11: Write minimal `src/rag/models.py`**

```python
"""Core data structures shared across the ingest and retrieval pipeline."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawSection:
    """A logical document section produced by a loader, before chunking."""

    source_file: str
    doc_type: str
    text: str
    section_id: str | None = None
    section_title: str | None = None
    section_path: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    sheet: str | None = None
    row: int | None = None


@dataclass
class Chunk:
    """An indexable unit. `text` is displayed, `search_text` is searched."""

    chunk_id: str
    text: str
    search_text: str
    citation_label: str
    metadata: dict[str, Any]


@dataclass
class SearchHit:
    """One retrieval result with its fused and per-ranker scores."""

    chunk: Chunk
    score: float
    cosine: float
    bm25: float


@dataclass
class Answer:
    """Final agent output."""

    text: str
    citations: list[str] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
```

- [ ] **Step 12: Run test to verify it passes**

Run: `pytest tests/test_models.py -v --no-cov`
Expected: PASS (4 passed)

- [ ] **Step 13: Write `.env.example`**

```ini
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b-instruct
OLLAMA_BASE_URL=http://localhost:11434
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

EMBEDDING_MODEL=intfloat/multilingual-e5-base
DATA_DIR=./data
STORAGE_DIR=./storage
CHUNK_MAX_CHARS=1200
CHUNK_OVERLAP=150
TOP_K=5
MIN_COSINE=0.72
MAX_TOOL_TURNS=3
```

- [ ] **Step 14: Run the full quality gate**

Run: `ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70`
Expected: exit 0, 6 tests passed

- [ ] **Step 15: Commit**

```bash
git add src tests scripts requirements.txt pyproject.toml .env.example .gitignore
git commit -m "feat(config): add project skeleton, settings, and data models"
```
