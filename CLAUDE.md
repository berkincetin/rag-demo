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
| [docs/bolum1-rag/](docs/bolum1-rag/) | Part 1 PRD (acceptance criteria), TRD (technical design). **Background, not the execution plan** |
| [docs/bolum2-analiz/](docs/bolum2-analiz/) | Part 2 PRD, TRD. **Background, not the execution plan** |

### 🚦 One execution source: the superpowers plan

**Implementation follows `docs/superpowers/plans/` and nothing else.**

`docs/bolum1-rag/UYGULAMA-PLANI.md` and `docs/bolum2-analiz/UYGULAMA-PLANI.md` are the
earlier phase-narrative drafts. They explain *why* the work is sequenced the way it is and
they are still worth reading for rationale — but they are **not** the plan you execute, and
their step numbering is superseded. When the two disagree, the superpowers task file wins.

Never work from `UYGULAMA-PLANI.md` steps. Never mix the two numbering schemes ("Faz 1.2"
vs "Task 3 Step 2") in commits, PROGRESSION.md, or status reports — use task numbers.

### The executable plan — read one task file at a time

Part 1 is broken into **14 task files** under
[docs/superpowers/plans/rag-agent/](docs/superpowers/plans/rag-agent/). Each task carries
its own tests, implementation code, commands, and expected output — it is self-contained.

**Reading rule:** read [00-overview.md](docs/superpowers/plans/rag-agent/00-overview.md)
(100 lines: goal, global constraints, task sequence) plus **exactly one** task file
(111–303 lines). Never load the whole task set — the constraints you need are in the
overview, and the neighbouring task interfaces you need are in your own task's
`Interfaces` block.

`PROGRESSION.md` names which task file is current.

The planning docs are written in Turkish. That is intentional — the user reads them.
This file (CLAUDE.md) is in English.

### Skills available in this repo

The **superpowers** skill collection (v6.2.0, MIT, github.com/obra/superpowers) is
installed project-locally at `.claude/skills/`. Invoke a skill with the Skill tool.

| Skill | Use it when | Status here |
|---|---|---|
| `test-driven-development` | Before writing any implementation code | **Mandatory** — see §3 |
| `verification-before-completion` | Before claiming anything is done, passing, or fixed | **Mandatory** — see §4 |
| `systematic-debugging` | Any bug, test failure, or unexpected behaviour | **Mandatory** before proposing a fix |
| `executing-plans` | Working through the task plan | **The execution path** — the plan lives in `docs/superpowers/plans/rag-agent/` |
| `writing-plans` | Producing a new plan | Planning is done; use only if replanning |
| `brainstorming` | Turning a vague idea into a spec | Planning is done; use only for new scope |
| `requesting-code-review` / `receiving-code-review` | Reviewing a finished chunk of work | Optional, ask first (spawns a subagent) |
| `subagent-driven-development`, `dispatching-parallel-agents` | Parallel/subagent execution | **Do not use** unless the user explicitly asks — this project runs single-threaded, phase by phase |
| `using-git-worktrees`, `finishing-a-development-branch` | Branch isolation and merge flow | **Not applicable** — we commit straight to `main` (§5) |

`.claude/` is gitignored, so these skills are not part of the delivery.

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
1. READ      PROGRESSION.md + MEMORY.md + the plan overview + THIS TASK'S file only (see §1)
2. INVOKE    Skill(skill="test-driven-development")     ← REQUIRED, before any code
3. BUILD     work through the phase's steps in the RED→GREEN→REFACTOR cycle (§3) —
             one step at a time, only what this phase covers, nothing from later phases
4. INVOKE    Skill(skill="verification-before-completion")  ← REQUIRED, before any claim
5. VERIFY    run the full quality gate (§4) and confirm the phase's DoD line by line
6. UPDATE    PROGRESSION.md (mark phase done, set next step) and MEMORY.md (what you learned)
7. COMMIT    conventional commit, then push to main (§5)
8. STOP      report what was done and ask for approval before starting the next phase
```

Steps 2 and 4 are **actual `Skill` tool calls**, not a reminder to keep the idea in mind.
Invoke them once per phase, at those points. Do not skip them because "I already know what
TDD is" — the skill text is the contract, and re-reading it is what keeps the discipline
from eroding over a long session.

### Skill triggers — invoke when the situation appears

| Situation | Invoke |
|---|---|
| About to write implementation code (any phase, any step) | `test-driven-development` |
| About to say something is done / passing / fixed, or about to commit | `verification-before-completion` |
| A test fails, a bug appears, or behaviour surprises you | `systematic-debugging` — **before** proposing a fix |
| Starting a phase whose plan you are about to follow step by step | `executing-plans` (optional but recommended) |
| The user asks for scope that isn't in the PRDs | `brainstorming` — before designing anything |

**Step 8 is a hard stop.** Do not chain phases. After pushing, summarize:
what was built, what the tests prove, anything that deviated from the plan, and what the
next phase is. Then wait.

If a phase's Definition of Done (DoD) in the plan cannot be met, stop and say so — do not
move on with a partially satisfied DoD, and do not quietly redefine the DoD.

---

## 3. Testing requirements — TDD is mandatory

**Invoke `Skill(skill="test-driven-development")` before the first line of code in each
phase.** The summary below is not a substitute for the skill — it is a pointer to it.

### The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Every step inside a phase follows **RED → GREEN → REFACTOR**:

1. **RED** — write one minimal test for one behavior. Clear name, real code, no mocks
   unless unavoidable.
2. **Verify RED** — run it and **watch it fail**. This step is mandatory and cannot be
   skipped. The failure must be "feature missing", not a typo or import error. If the test
   passes immediately, it is testing existing behavior — fix the test.
3. **GREEN** — write the simplest code that passes. No extra options, no anticipated
   features, no "while I'm here" improvements.
4. **Verify GREEN** — run it, see it pass, and confirm nothing else broke. Output must be
   clean: no errors, no warnings.
5. **REFACTOR** — only once green. Remove duplication, improve names. No new behavior.

If production code was written before its test: **delete it and start over.** Do not keep
it "as reference", do not adapt it while writing the test. That is testing-after wearing a
disguise.

Rationalizations that mean *stop and restart with TDD*: "too simple to test", "I'll test
after", "already manually tested", "deleting it would waste the hour I spent",
"TDD is dogmatic, I'm being pragmatic", "this case is different because…".

**Bug fixes are TDD too:** write a failing test that reproduces the bug first, then fix.
When a test fails or something behaves unexpectedly, invoke
`Skill(skill="systematic-debugging")` **before** proposing a fix — root cause first,
patch second.

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

## 4. Quality gate and verification

**Invoke `Skill(skill="verification-before-completion")` before claiming a phase is done
and before every commit.**

### The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you have not run the command **in this message**, you cannot say it passes. Not
"should pass", not "looks correct", not "done" — those are claims, and claims need output.

Before any commit, run all of these and read the actual output:

```bash
ruff format .                       # format
ruff check . --fix                  # lint (unused imports, undefined names, etc.)
pytest -q --cov --cov-fail-under=70 # unit + integration tests with coverage
```

If any step fails: **do not commit**. Fix it. If it cannot be fixed, stop and report.

Never bypass hooks (`--no-verify`) and never lower the coverage threshold to make a
commit go through.

### Gate function — apply before every completion claim

```
1. IDENTIFY  which command proves this claim?
2. RUN       the full command, fresh — not a remembered earlier run
3. READ      full output, exit code, failure count
4. VERIFY    does the output actually confirm the claim?
5. ONLY THEN state the claim, together with its evidence
```

| Claim | What proves it | What does NOT prove it |
|---|---|---|
| "Tests pass" | pytest output showing 0 failures, now | An earlier run, "should pass" |
| "Lint is clean" | `ruff check` exit 0 | A partial check, extrapolation |
| "Phase 1 is done" | Every DoD line in the plan checked one by one | "Tests pass, so it's done" |
| "The bug is fixed" | The test that reproduced it now passes | The code changed, so presumably |
| "Ingest works" | `python scripts/ingest.py` ran and printed its summary | The unit tests pass |

**Do not express satisfaction before verification.** No "Great!", "Perfect!", "Done!"
ahead of the evidence. Report the phase's DoD as a line-by-line checklist, not as a
general impression.

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

🚫 **No attribution trailers.** Do **not** append `Co-Authored-By: Claude ...`,
`Generated with Claude Code`, or any similar footer to commit messages. This overrides the
default Claude Code behaviour and applies to every commit in this repository. The commit
message ends with its own content — nothing after it. The same applies to PR descriptions
if any are ever created.

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
| **Part 2 identifiers** (`src/analysis/`, `notebooks/analiz.ipynb`, `tests/test_analysis_*.py`) | **English** — function names, variable names, class names, constants, test names. Same as Part 1 |
| **Part 2 comments, docstrings and markdown cells** | **Turkish** — every comment, docstring and notebook narrative cell |
| **Part 2 DataFrame column names** | **Turkish** — `pazar`, `sirket`, `urun`, `tarih`, `brut_kutu`, `mf_oran`, `net_tl`, `mf_oran_temiz`, `net_kutu`, `birim_fiyat`, `gercek`, `tahmin`. These mirror the dataset's own headers (`Brüt Kutu`, `MF Oran`, `Net TL`) and keep the data contract traceable to the source workbook. **They are data, not identifiers — never rename them** |

> ⚠️ Part 2 originally used Turkish identifiers; the user changed this on 2026-08-04.
> When renaming, beware that a blanket regex will also hit Turkish comments and string
> literals (it turned "tahmin edilmedi" into "prediction edilmedi") and DataFrame column
> names inside `.query()` strings. Rename deliberately, then re-run the notebook and
> diff the outputs — they must be identical.
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
