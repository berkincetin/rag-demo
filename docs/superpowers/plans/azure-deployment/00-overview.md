# Azure Deployment Implementation Plan — Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Part 1 RAG agent to Azure as a two-tier, authenticated,
cloud-only application — Azure OpenAI for both chat and embeddings, a public
Next.js tier, and a backend with no public route.

**Architecture:** A new top-level `azure/` package holds a self-contained copy
of the RAG pipeline. `src/rag/` is never edited, so the local offline path and
its 329 tests cannot regress. The browser reaches only the Next.js tier, which
authenticates the user and proxies to the internal FastAPI tier server-side.

**Tech Stack:** Python 3.11, FastAPI, Chroma, rank-bm25, LangGraph,
Azure OpenAI (`gpt-4.1-mini`, `text-embedding-3-small`), Next.js 15,
`jose` (JWT), `bcryptjs`, Azure Container Apps, Azure Container Registry.

**Spec:** [docs/superpowers/specs/2026-08-16-azure-deployment-design.md](../../specs/2026-08-16-azure-deployment-design.md)

---

## Global Constraints

Every task's requirements implicitly include this section.

### Absolute rules

- **Never modify `src/rag/`, `gradio_app.py`, `app.py`, `docker-compose.yml`,
  or anything under `tests/`.** The local path must stay byte-identical.
  Verify with `git status` before every commit.
- **Never touch the `azure-rag` or `azure-rag-web` Azure resources.** They
  belong to a different project and are currently running. This deployment
  uses the `nobel-rag-*` prefix everywhere.
- **TDD is mandatory** (CLAUDE.md §3): a failing test precedes every line of
  implementation. Watch it fail for the right reason before implementing.
- **Never assert on LLM output text** — it is non-deterministic. Mock the LLM
  client when testing control flow.
- **Never fabricate numbers.** Thresholds, prices, and measurements come from
  code that actually ran.
- **No `@pytest.mark.skip` or `xfail`** to make a task pass.

### Fixed values (copy verbatim)

| Name | Value |
|---|---|
| Resource group | `foundry-lab-rg` |
| Location | `eastus` |
| Azure OpenAI account | `foundry-lab-hbc26` |
| Azure OpenAI endpoint | `https://foundry-lab-hbc26.openai.azure.com/` |
| Chat deployment | `gpt-4.1-mini` |
| Embedding deployment | `text-embedding-3-small` |
| Container registry | `cad8870592d9acr` (`cad8870592d9acr.azurecr.io`) |
| Container Apps env | `azure-rag-env` |
| Backend app name | `nobel-rag-api` (internal ingress, port 8000) |
| Frontend app name | `nobel-rag-web` (external ingress, port 3000) |

### Language rules (CLAUDE.md §6)

- Code, identifiers, comments, docstrings, commit messages: **English**
- User-facing strings (login page, error messages, UI labels): **Turkish**

### Quality gate — before every commit

```bash
ruff format .
ruff check . --fix
pytest -q --cov --cov-fail-under=70
```

All three must pass. Never bypass hooks, never lower the threshold.

### Commit format

Conventional Commits, scope from the module. **No attribution trailers**
(CLAUDE.md §5) — no `Co-Authored-By`, no `Generated with`.

---

## Task Sequence

| # | Task | Deliverable |
|---|---|---|
| 1 | [Provisioning and config](01-provision-and-config.md) | `text-embedding-3-small` deployed; `azure/rag/config.py` |
| 2 | [Embedder](02-embedder.md) | `AzureOpenAIEmbedder` |
| 3 | [LLM client](03-llm-client.md) | `AzureOpenAIClient` with tool calling |
| 4 | [Core module copies](04-core-copies.md) | models, normalize, chunker, loaders |
| 5 | [Index](05-index.md) | `build_index` / `load_index` with injected embedder |
| 6 | [Retriever](06-retriever.md) | Hybrid retrieval, E5 prefixes removed |
| 7 | [Agent and tools](07-agent-tools.md) | LangGraph loop, 3 tools, prompts |
| 8 | [Ingest and calibration](08-ingest-and-calibration.md) | Real index + **measured thresholds** |
| 9 | [Support modules](09-support-modules.md) | metrics, pricing, catalog, ui_state, serialize, memory |
| 10 | [API](10-api.md) | FastAPI with internal-token auth, reduced surface |
| 11 | [Backend image](11-backend-docker.md) | Slim Dockerfile, no torch |
| 12 | [Web authentication](12-web-auth.md) | Login, JWT, middleware |
| 13 | [Web proxy](13-web-proxy.md) | BFF proxy, session-id substitution |
| 14 | [Deploy and verify](14-deploy-and-verify.md) | Live URL, end-to-end evidence |

**Dependency chain:** 1 → {2, 3} → 4 → 5 → 6 → 7 → 8 → {9} → 10 → 11 → 12 → 13 → 14

Task 8 is a gate: no deployment work proceeds until thresholds are measured.

---

## Critical domain knowledge

Carried from CLAUDE.md §9 — getting these wrong breaks the deliverable.

1. **Turkish character folding.** Index and query both pass through
   `fold_tr()`. Turkish mappings (`İ→I`, `ı→i`, `ş→s`, `ğ→g`, `ç→c`, `ö→o`,
   `ü→u`) apply **before** `casefold()`.
2. **DOCX tables carry answers.** `1.500 TL/ay` exists only in a table, not in
   any paragraph. It is the canonical retrieval smoke test.
3. **XLSX headers are not on row 0.** The loaders already detect this.
4. **Never hardcode filenames** — one contains a Turkish `ı`. Glob the directory.
5. 🚨 **The E5 `passage:` / `query:` prefixes must be deleted, not ported.**
   They are `intfloat/multilingual-e5-base` training artifacts. Sent to
   `text-embedding-3-small` they become literal content and silently degrade
   retrieval quality. See Task 5 and Task 6.
6. 🚨 **`MIN_COSINE=0.80` / `MIN_BM25=5.0` are invalid for the new embedding
   model.** They were calibrated against e5-base. Task 8 measures replacements.
   Using the old values without measuring is a correctness failure.
7. **Console encoding is cp1252** on this machine. Entry points that print
   Turkish need `sys.stdout.reconfigure(encoding="utf-8")` or
   `PYTHONIOENCODING=utf-8`.

---

## Definition of Done for the whole plan

- [ ] `text-embedding-3-small` deployed on `foundry-lab-hbc26`
- [ ] `git status` shows no modification to `src/rag/`, `gradio_app.py`,
      `docker-compose.yml`, or `tests/`
- [ ] Local test suite still green (329 tests)
- [ ] Azure image contains no `torch` and no `sentence-transformers`
- [ ] Thresholds recalibrated from measured data, values recorded with evidence
- [ ] All security tests pass (Task 12, 13)
- [ ] `nobel-rag-api` has no public FQDN; a direct request from the internet fails
- [ ] The app is unreachable without logging in
- [ ] Live URL answers a grounded question with citations
- [ ] Live URL refuses an off-topic question
- [ ] `azure-rag` and `azure-rag-web` still running, untouched
- [ ] Quality gate green
