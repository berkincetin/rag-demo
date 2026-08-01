# RAG Agent Implementation Plan — Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Read this file plus exactly one task file per work session.** Each task file is self-contained: it carries its own tests, implementation code, commands, and expected output. Never read the whole task set at once.

**Goal:** Build a locally-runnable Turkish RAG question-answering agent over six company documents (2 PDF, 2 DOCX, 2 XLSX) that answers natural-language questions with file/section/page citations, exposes three tools to an LLM, and refuses to hallucinate.

**Architecture:** Offline ingest pipeline (format-specific loaders → section-aware chunker → Chroma vector index + BM25 lexical index) feeding a hybrid retriever (Reciprocal Rank Fusion). An agent loop drives a tool-calling LLM through three tools, guarded by a three-layer safety net: a deterministic retrieval-score gate before the LLM, a grounded system prompt, and a citation post-check after. Two front-ends (CLI, Streamlit) sit on top.

**Tech Stack:** Python 3.10, pypdf, python-docx, pandas+openpyxl, sentence-transformers (`intfloat/multilingual-e5-base`), chromadb, rank-bm25, streamlit, pytest, ruff.

---

## Global Constraints

These apply to **every** task. Each task's requirements implicitly include this section.

- **Python 3.10.** Use `str | None` unions (valid from 3.10); do **not** use 3.11+ features (`tomllib`, `Self`, `ExceptionGroup`).
- **Code language: English.** Identifiers, comments, docstrings, log messages, commit messages — all English. See CLAUDE.md §6.
- **User-facing strings: Turkish.** Streamlit labels, LLM system prompt, refusal/no-info templates, CLI prompts.
- **All file I/O is UTF-8.** Every `open()` passes `encoding="utf-8"`. Entry points call `sys.stdout.reconfigure(encoding="utf-8")` — the Windows console is cp1252 and raises `UnicodeEncodeError` otherwise.
- **Never hardcode source filenames.** `ik_surecleri_politikası.docx` contains a Turkish `ı`. Discover files with `glob`.
- **Max 12 direct dependencies.** Do not add libraries beyond those in this plan without asking.
- **TDD is mandatory.** No production code without a failing test first. Every task follows RED → GREEN → REFACTOR.
- **Quality gate before every commit:** `ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70`.
- **Commit format:** Conventional Commits. **No `Co-Authored-By` or any attribution trailer.**
- **Coverage floor: 70%**, with `src/rag/llm.py` and `app.py` omitted.
- **Config constants (exact values):** `CHUNK_MAX_CHARS=1200`, `CHUNK_OVERLAP=150`, `TOP_K=5`, `MIN_COSINE=0.72`, `MAX_TOOL_TURNS=3`, `RRF_K=60`, `EMBEDDING_MODEL=intfloat/multilingual-e5-base`.

---

## Task Sequence

Work in order. Each task ends with its own commit and is independently testable.

| # | Task | File | Produces |
|---|---|---|---|
| 1 | Project skeleton, config, and data models | [01-skeleton-config-models.md](01-skeleton-config-models.md) | `Config`, `RawSection`, `Chunk`, `SearchHit`, `Answer` |
| 2 | Turkish-aware text normalization | [02-normalize.md](02-normalize.md) | `fold_tr`, `clean_text` |
| 3 | PDF loader with section and page tracking | [03-pdf-loader.md](03-pdf-loader.md) | `load_pdf`, `parse_heading`, `KUB_SECTION_IDS` |
| 4 | DOCX loader with heading hierarchy and tables | [04-docx-loader.md](04-docx-loader.md) | `load_docx`, `rows_to_markdown` |
| 5 | XLSX loader with header detection | [05-xlsx-loader.md](05-xlsx-loader.md) | `load_xlsx`, `detect_header_row`, `row_to_text` |
| 6 | Loader dispatch over the corpus directory | [06-loader-dispatch.md](06-loader-dispatch.md) | `load_all`, `SUPPORTED_SUFFIXES` |
| 7 | Section-aware chunker with citation labels | [07-chunker.md](07-chunker.md) | `chunk_sections`, `build_citation_label` |
| 8 | Index builder and ingest entry point | [08-index-ingest.md](08-index-ingest.md) | `build_index`, `load_index`, `LoadedIndex`, `IngestReport`, `scripts/ingest.py` |
| 9 | Hybrid retriever with RRF and confidence gate | [09-retriever.md](09-retriever.md) | `Retriever`, `reciprocal_rank_fusion` |
| 10 | Tools and prompts | [10-tools-prompts.md](10-tools-prompts.md) | `TOOL_SCHEMAS`, `ToolBox`, `SYSTEM_PROMPT`, refusal templates |
| 11 | LLM provider abstraction | [11-llm-providers.md](11-llm-providers.md) | `LLMResponse`, `ToolCall`, `get_client`, three clients |
| 12 | Agent loop with the three-layer safety net | [12-agent.md](12-agent.md) | `Agent`, `extract_citations` |
| 13 | CLI and Streamlit front-ends | [13-frontends.md](13-frontends.md) | `build_agent`, `format_answer`, `app.py` |
| 14 | Demo notebook, Docker, and README | [14-demo-docker-readme.md](14-demo-docker-readme.md) | Case deliverables |
| — | Verification checklist | [99-verification-checklist.md](99-verification-checklist.md) | Final acceptance pass |

**Dependency chain:** 1 → 2 → {3, 4, 5} → 6 → 7 → 8 → 9 → {10, 11} → 12 → 13 → 14.
Tasks 3–5 are independent of each other. Tasks 10 and 11 are independent of each other.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/rag/config.py` | Environment-backed settings dataclass |
| `src/rag/models.py` | `RawSection`, `Chunk`, `SearchHit`, `Answer` dataclasses |
| `src/rag/normalize.py` | Turkish-aware ASCII folding, text cleanup |
| `src/rag/loaders/pdf_loader.py` | PDF → sections with section id/title/page |
| `src/rag/loaders/docx_loader.py` | DOCX → sections with heading path + tables |
| `src/rag/loaders/xlsx_loader.py` | XLSX → one section per row |
| `src/rag/loaders/__init__.py` | `load_all()` — glob dispatch by extension |
| `src/rag/chunker.py` | `RawSection` → `Chunk` with citation labels |
| `src/rag/index.py` | Build/load Chroma + BM25 + `chunks.jsonl` |
| `src/rag/retriever.py` | Hybrid search, RRF fusion, confidence gate |
| `src/rag/tools.py` | Three tool schemas + implementations |
| `src/rag/prompts.py` | System prompt and refusal templates |
| `src/rag/llm.py` | Provider abstraction (ollama/anthropic/openai) |
| `src/rag/agent.py` | Tool-calling loop + three-layer safety net |
| `src/rag/cli.py` | Terminal front-end |
| `scripts/ingest.py` | Ingest entry point |
| `app.py` | Streamlit front-end |

Tests mirror this structure under `tests/`. Integration tests carry `@pytest.mark.integration`.

---

## Reference Documents

Consult these only when a task points you at them — do not read them up front.

| Document | When you need it |
|---|---|
| `docs/01-veri-kesif-bulgulari.md` | The measured data facts. **Every number in a test assertion comes from here.** If reality disagrees with an assertion, investigate before changing it |
| `docs/02-karar-kaydi.md` | Why each technology was chosen (10 ADRs) |
| `docs/bolum1-rag/TRD.md` | Full technical design, including the ASCII architecture diagram for the README |
| `docs/bolum1-rag/PRD.md` | Acceptance criteria and the eight demo questions |

## Where We Are

Current phase and next concrete step live in [PROGRESSION.md](../../../../PROGRESSION.md).
Durable lessons and decisions live in [MEMORY.md](../../../../MEMORY.md).
