# CLAUDE.md

Operating instructions for Claude Code in this repository. Read this before doing anything.

---

## 1. What this project is

A two-part technical assessment ("case study"). The full brief is
`AI Engineer/Ai engineer case study.pdf`.

| Part | Scope | Status |
|---|---|---|
| **Part 1 — RAG Agent** | Local-capable RAG question-answering agent over 6 company documents (PDF/DOCX/XLSX), with tool calling, source citation, "I don't know" handling, Streamlit UI, Docker | **Build first** |
| **Part 2 — Sales Analysis** | Pharma sales & demand analysis over 4 markets × 124 months; 7 analysis tasks; Jupyter notebook with charts, statistics, and forecasting | Build **after** Part 1 is deliverable |

**This is a demo.** Implement exactly what the case document asks for — mandatory features
plus the bonus list. Do not add features beyond that. Every "out of scope" decision is
already recorded in the PRDs; if you think something must be added, ask first.

### Planning documents — read these before writing code

| Document | Why you need it |
|---|---|
| [docs/README.md](docs/README.md) | Index of all planning docs |
| [docs/00-case-analizi.md](docs/00-case-analizi.md) | Requirement traceability matrix — every case requirement → where it is satisfied |
| [docs/01-veri-kesif-bulgulari.md](docs/01-veri-kesif-bulgulari.md) | **Measured** data findings. Not assumptions. Several of them change the implementation |
| [docs/02-karar-kaydi.md](docs/02-karar-kaydi.md) | 10 ADRs — the "why" behind every technology choice |
| [docs/bolum1-rag/](docs/bolum1-rag/) | Part 1 PRD, TRD, phase plan |
| [docs/bolum2-analiz/](docs/bolum2-analiz/) | Part 2 PRD, TRD, phase plan |

The planning docs are written in Turkish. That is intentional — the user reads them.
This file (CLAUDE.md) is in English.

### State tracking — read at the start of every session

| File | Purpose |
|---|---|
| [PROGRESSION.md](PROGRESSION.md) | Where we are. Which phase is done, which is current, what the next concrete step is |
| [MEMORY.md](MEMORY.md) | Durable knowledge: decisions made during implementation, gotchas discovered, things that cost time |

**Always read both before starting work.** Always update both before ending a phase.

---

## 2. The workflow — non-negotiable

Work **one phase at a time**, in the order defined in the phase plans. Never start a phase
before the previous one is fully closed.

For each phase:

```
1. READ      PROGRESSION.md + MEMORY.md + the phase's section in the relevant UYGULAMA-PLANI.md
2. IMPLEMENT the phase — only what that phase covers, nothing from later phases
3. TEST      write unit tests AND integration tests for what the phase produced (see §3)
4. VERIFY    run the full quality gate (see §4). All of it must pass
5. UPDATE    PROGRESSION.md (mark phase done, set next step) and MEMORY.md (what you learned)
6. COMMIT    conventional commit, then push to main (see §5)
7. STOP      report what was done and ask for approval before starting the next phase
```

**Step 7 is a hard stop.** Do not chain phases. After pushing, summarize:
what was built, what the tests prove, anything that deviated from the plan, and what the
next phase is. Then wait.

If a phase's Definition of Done (DoD) in the plan cannot be met, stop and say so — do not
move on with a partially satisfied DoD, and do not quietly redefine the DoD.

---

## 3. Testing requirements

Every phase produces both kinds of tests. A phase is not finished until they pass.

### Unit tests
Isolated, fast, deterministic, no network, no LLM calls. Test the logic the phase added.

### Integration tests
Test that the phase's components work together against **real project data** — the actual
files in `data/` and `AI Engineer/bolum2_veriseti.xlsx`, not fixtures invented from
imagination. Examples:
- `loaders` integration: run `load_all(data_dir)` over the real 6 documents and assert on
  the counts and content the plan specifies (e.g. `1.500 TL/ay` must appear in a chunk).
- `retriever` integration: build the real index, run the four probe queries from the plan.
- Part 2: load the real workbook and assert 374 series × 124 months.

### Rules
- **Never** test LLM output text — it is non-deterministic. Test everything up to the LLM
  boundary, and mock the LLM client when testing the agent loop's control flow.
- **Never** use `@pytest.mark.skip` or `xfail` to get a phase to pass. If a test fails,
  fix the root cause or report the blocker.
- Test data assertions come from [docs/01-veri-kesif-bulgulari.md](docs/01-veri-kesif-bulgulari.md).
  Those numbers were measured — trust them, and if reality disagrees, investigate before
  changing the assertion.
- Tests live in `tests/`, named `test_<module>.py`. Integration tests are marked
  `@pytest.mark.integration` so they can be run separately.

### Coverage
Minimum **70%** line coverage, enforced by `pytest --cov --cov-fail-under=70`.
Modules that only wrap external services (`llm.py` provider adapters, `app.py` Streamlit
glue) are excluded via `omit` in the coverage config — everything else counts.

---

## 4. Quality gate

Before any commit, all of these must pass:

```bash
ruff format .                       # format
ruff check . --fix                  # lint (unused imports, undefined names, etc.)
pytest -q --cov --cov-fail-under=70 # unit + integration tests with coverage
```

If any step fails: **do not commit**. Fix it. If it cannot be fixed, stop and report.

Never bypass hooks (`--no-verify`) and never lower the coverage threshold to make a
commit go through.

---

## 5. Commits and push

- Branch: **`main`** directly. No feature branches, no PRs.
- One commit per phase (fixups within a phase are fine; keep history readable).
- Push to `origin/main` after each phase's commit.
- Format: **Conventional Commits**.

```
feat(loaders): add DOCX table extraction and heading hierarchy
test(retriever): add hybrid search integration tests over real corpus
fix(clean): correct MF ratio scale detection for B Pazarı
docs(progression): close phase 1, set phase 2 as current
chore(deps): pin requirements for reproducible install
```

Scopes follow module names: `loaders`, `chunker`, `index`, `retriever`, `tools`, `llm`,
`agent`, `cli`, `ui`, `docker`, `load`, `clean`, `metrics`, `forecast`, `plots`,
`notebook`, `progression`.

Commit body: optional, one short paragraph if the change needs justification.
End every commit message with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

> Note: the user's global instruction is "write the commit message, don't run git commit."
> **This project overrides that** — the user explicitly asked for commit + push at the end
> of every phase. That authorization applies to phase-boundary commits only. Any other
> commit still needs to be asked for.

**Never commit:** `.env`, API keys, `storage/`, `data/`, `figures/` outputs that are
regenerable, `__pycache__/`, notebook checkpoints.

---

## 6. Language rules

| Context | Language |
|---|---|
| **Part 1 code** (`src/rag/`, `app.py`, `scripts/`, `tests/`) | **English** — identifiers, comments, docstrings, log messages, all of it |
| **Part 1 user-facing strings** | **Turkish** — Streamlit UI labels, LLM system prompt, refusal/no-info templates, CLI prompts |
| **Part 2 code** (`src/analysis/`, `notebooks/analiz.ipynb`) | **Turkish** — identifiers, comments, docstrings, DataFrame column names (`brut_kutu`, `mf_oran`, `net_tl`, `pazar`, `sirket`, `urun`). The domain terms come from the dataset; keeping them Turkish preserves traceability to the source data |
| Commit messages | English (both parts) |
| `docs/`, `PROGRESSION.md`, `MEMORY.md` | Turkish |
| `CLAUDE.md`, `README.md` | English (README may include a Turkish section if useful) |

---

## 7. Environment

- **OS:** Windows 11. Primary shell is **PowerShell**; a Bash tool is also available.
  Each takes its own syntax — PowerShell has no `&&`, no `||`, no ternary.
- **Python:** 3.10.3 at `C:\Users\Polinity\AppData\Local\Programs\Python\Python310`.
  Already installed: `pandas`, `openpyxl`, `python-docx`, `pypdf`.
- **Console encoding is cp1252.** Any script that prints Turkish text needs
  `PYTHONIOENCODING=utf-8`, or it raises `UnicodeEncodeError`. In Python entry points,
  call `sys.stdout.reconfigure(encoding="utf-8")` defensively.
- **Repo:** `github.com/berkincetin/rag-demo`, branch `main`.
- Use a virtual environment (`.venv/`) — it is gitignored.

---

## 8. Data files

The source documents are **not committed** (user's decision). They live at:

- Part 1 corpus: `AI Engineer/Rag_Agent/` → copy into `data/` during Phase 0
- Part 2 dataset: `AI Engineer/bolum2_veriseti.xlsx`

`data/`, `AI Engineer/`, and `storage/` are all in `.gitignore`.

⚠️ **Delivery consequence — do not forget:** the case requires a ZIP with runnable code.
Since the documents are not in git, the delivery ZIP must include `data/` manually, or the
evaluator cannot run `ingest.py`. This is a checklist item in the final phase of
[docs/bolum1-rag/UYGULAMA-PLANI.md](docs/bolum1-rag/UYGULAMA-PLANI.md); keep it there.

---

## 9. Critical domain knowledge

These were measured from the actual data. Getting them wrong breaks the deliverable.
Full detail in [docs/01-veri-kesif-bulgulari.md](docs/01-veri-kesif-bulgulari.md).

### Part 1 — RAG corpus
1. **Turkish character inconsistency.** DOCX files are ASCII-folded (`Insan Kaynaklari`),
   PDFs are full Turkish (`İnsan Kaynakları`), sometimes mixed inside one sentence.
   Both the index and the query must go through `fold_tr()`. Apply the Turkish-specific
   mappings (`İ→I`, `ı→i`, `ş→s`, `ğ→g`, `ç→c`, `ö→o`, `ü→u`) **before** `casefold()` —
   Python's default lowercasing mangles `İ`.
2. **DOCX tables carry the answers.** 7 and 9 tables respectively. `document.paragraphs`
   misses all of them; iterate `document.element.body` to get paragraphs and tables in
   document order. Also: `paragraph.style` can be `None` — guard with `getattr`.
3. **XLSX headers are on row 3**, not row 0. `pd.read_excel(header=0)` reads them wrong.
4. **Never hardcode filenames.** `ik_surecleri_politikası.docx` contains a Turkish `ı`
   and the case document spells it differently. Glob the directory.
5. **PDF section detection has false positives** — footnote lines on Duxet page 15 look
   like section headings. Filter with the KÜB section whitelist plus monotonic ordering.

### Part 2 — Sales dataset
1. 🚨 **`MF Oran` is on a different scale in B Pazarı** — percent (0–100) there, ratio
   (0–1) everywhere else. Median in B is ~5.9–7.4; 86% of Şirket 1's B rows exceed 1.
   Without dividing by 100, `Net Kutu = Brüt × (1 − MF)` goes negative and unit price comes
   out at **−0.88 TL** instead of 8.32 TL. **Tasks A4, A6 and A7 are all wrong without this
   fix.** Detect it programmatically (group median > 1 ⇒ percent scale), don't hardcode
   "B Pazarı".
2. **Primary key is always `(Pazar, Şirket, Ürün)`.** `Ürün-A` and `Ürün-FP` each appear
   under more than one company. Grouping by product name alone merges different products.
3. **Product names have inconsistent whitespace** (`Ürün 1` vs `Ürün  2`). Normalize with
   `\s+ → ' '`.
4. **Series lengths are wildly uneven.** `C Pazarı/Ürün 1` has exactly **one** observation;
   `D Pazarı/Ürün 78` has 11. Seasonality and forecasting are impossible for them —
   report that explicitly in the notebook, never silently drop or fabricate.
5. Negative `Brüt Kutu`/`Net TL` (~1,158 rows) are returns. Flag them; don't delete them.

---

## 10. How to behave

- **Follow the plan.** The phase plans have numbered steps and a Definition of Done per
  step. Work through them in order. If reality contradicts the plan, say so and propose a
  change — don't silently improvise.
- **Report honestly.** If tests fail, show the output. If a DoD was not met, say which one.
  If a model performs worse than the baseline, that is a finding — write it down, don't
  hide it. Never claim something works without having run it.
- **Never fabricate numbers.** Every figure in a notebook, README, or report must come from
  code that actually ran. No placeholder results, no "approximately" from memory.
- **Stay in scope.** No refactors of code the current phase doesn't touch. No new
  dependencies beyond the ones listed in the TRDs — if you need one, ask.
- **Ask when a decision is genuinely the user's.** Otherwise pick the sensible default,
  state it, and continue.
- Prefer editing existing files over creating new ones. Don't create documentation files
  that weren't asked for.

---

## 11. Quick reference

```bash
# setup
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt

# Part 1 — the three commands the README promises
pip install -r requirements.txt
python scripts/ingest.py
streamlit run app.py

# CLI
python -m src.rag.cli "Yıllık izin talebimi nasıl yaparım?"

# quality gate
ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70

# tests only
pytest -q                              # everything
pytest -q -m "not integration"         # unit only
pytest -q -m integration               # integration only

# Part 2
jupyter lab notebooks/analiz.ipynb
```
