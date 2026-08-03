# Sales Analysis Implementation Plan — Overview

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Read this file plus exactly one task file per work session.** Each task file is self-contained: it carries its own tests, the shape of the implementation, commands, and expected output. Never read the whole task set at once.

**Goal:** Answer the case's seven pharmaceutical sales questions (A1–A7) over four markets × 124 months, in a Jupyter notebook backed by tested Python modules, with charts, statistics, forecasting, and both a technical and a business comment per question.

**Architecture:** A thin notebook over thick, tested modules. `load.py` unpivots the three-row hierarchical header into tidy rows; `clean.py` applies seven measured data corrections and returns a quality report; `metrics.py` derives Net Kutu / Birim Fiyat and the analytical measures; `forecast.py` runs walk-forward evaluation of five models; `plots.py` holds the shared Turkish chart style. `notebooks/analiz.ipynb` calls them and does the interpreting.

**Tech Stack:** Python 3.10, pandas, numpy, openpyxl, matplotlib, statsmodels (STL), scipy (Mann-Whitney, Welch), scikit-learn, lightgbm, jupyter.

---

## Global Constraints

These apply to **every** task. Each task's requirements implicitly include this section.

- **Code language: Turkish** — identifiers, comments, docstrings and DataFrame column names (`brut_kutu`, `mf_oran`, `net_tl`, `pazar`, `sirket`, `urun`). This is the opposite of Part 1 and it is deliberate: the domain terms come from the dataset, and keeping them Turkish preserves traceability to the source. See CLAUDE.md §6. **Commit messages stay English.**
- **Python 3.10.** `str | None` unions are fine; no 3.11+ features.
- **All file I/O is UTF-8.** The Windows console is cp1252 — entry points call `sys.stdout.reconfigure(encoding="utf-8")`.
- **Never hardcode "B Pazarı"** for the MF scale fix. Detect it programmatically (group median > 1 ⇒ percent scale). The rule must survive a data change.
- **Primary key is always `(pazar, sirket, urun)`** — never `urun` alone. `Ürün-A` and `Ürün-FP` each appear under more than one company.
- **Never fabricate a number.** Every figure in the notebook comes from code that ran. Short series are reported, never silently dropped or filled.
- **TDD is mandatory.** No production code without a failing test first. RED → verify RED → GREEN → verify GREEN → REFACTOR.
- **Quality gate before every commit:** `ruff format . && ruff check . --fix && pytest -q --cov --cov-fail-under=70`.
- **Commit format:** Conventional Commits. **No `Co-Authored-By` or any attribution trailer.**
- **Coverage floor stays 70%** over the whole repository (Part 1 sits at ~95%, so Part 2 must not drag it under).
- **No new dependencies** beyond the TRD list without asking. `plotly` is deliberately **not** installed: PRD §3.3 rules out the interactive dashboard and the deliverable needs static PNGs.

---

## The measured facts every task depends on

Full detail in [docs/01-veri-kesif-bulgulari.md](../../../01-veri-kesif-bulgulari.md) §2. Test assertions come from there.

| # | Fact | Consequence |
|---|---|---|
| 1 | 378 × 375 sheet, 3-row header (Yıl / Ay / Metrik), keys in columns 0–2 | `pd.read_excel(header=0)` is wrong; unpivot manually |
| 2 | **374 series × 124 months × 3 metrics**, 2016-01 → 2026-04, no duplicate keys | Shape assertions |
| 3 | 🚨 **`MF Oran` is percent-scaled in B Pazarı only** (median 5.9–7.4 vs ~0 elsewhere) | Without ÷100 the unit price is **−0.88 TL** instead of 8.32 TL; A4, A6 and A7 are all wrong |
| 4 | Extreme MF outliers survive the scale fix (max 469.5) | Clip to `[0, 0.95]`, flag, report |
| 5 | 1,158 negative `Brüt Kutu` / 1,168 negative `Net TL` | Returns. Flag; keep in totals, zero in forecast inputs |
| 6 | 28,006 empty cells (20%) and 9,536 zero months | Product lifecycle — trim before first positive sale, don't fill with 0 |
| 7 | Product names carry double spaces (`Ürün  2`) | Normalize `\s+ → ' '` |
| 8 | Series lengths are wildly uneven: `C/Ürün 1` = **1 month**, `D/Ürün 78` = 11, `B/Ürün-FP` = 27 | Seasonality and forecasting impossible for them — report explicitly |
| 9 | Şirket 1 has **18 product-market series**: A 10, B 4, C 2, D 2 | 10 of 18 are in A Pazarı → metrics must be reported **per market** |

---

## Task Sequence

Work in order. Each task ends with its own commit and is independently testable.

| # | Task | File | Produces |
|---|---|---|---|
| 1 | Skeleton, dependencies, wide → tidy loader | [01-iskelet-yukleme.md](01-iskelet-yukleme.md) | `requirements-analysis.txt`, `src/analysis/load.py` → `yukle_ham` |
| 2 | Cleaning pipeline and data quality report 🚨 | [02-temizleme.md](02-temizleme.md) | `clean.py` → `mf_olcek_tespit`, `temizle`, `VeriKalitesiRaporu` |
| 3 | Derived and analytical metrics | [03-metrikler.md](03-metrikler.md) | `metrics.py` → net kutu, birim fiyat, pazar payı, HHI, YoY, STL seasonality |
| 4 | Chart style module | [04-grafikler.md](04-grafikler.md) | `plots.py` → Turkish formatting, fixed palettes, `figures/` writer |
| 5 | Baseline forecasts and walk-forward harness | [05-tahmin-temel.md](05-tahmin-temel.md) | `forecast.py` → `naive`, `snaive`, `ma3`, `walk_forward`, MAE/MAPE/RMSE/WAPE/sMAPE |
| 6 | Global LightGBM and the MF ablation | [06-tahmin-lgbm.md](06-tahmin-lgbm.md) | `ozellik_matrisi`, `lgbm`, `lgbm_no_mf` |
| 7 | Notebook: quality report + A1, A2 | [07-notebook-a1-a2.md](07-notebook-a1-a2.md) | `notebooks/analiz.ipynb` opening + two tasks |
| 8 | Notebook: A3, A4 | [08-notebook-a3-a4.md](08-notebook-a3-a4.md) | Seasonality heat map, MF event study with p-values |
| 9 | Notebook: A5, A6 | [09-notebook-a5-a6.md](09-notebook-a5-a6.md) | Competitor growth, unit price and promotion cost |
| 10 | Notebook: A7 | [10-notebook-a7.md](10-notebook-a7.md) | Model × market table, ablation, forecast chart |
| 11 | Closing: Restart & Run All, figures, README | [11-kapanis.md](11-kapanis.md) | Executive summary, PNG figures, delivery checklist |

**Dependency chain:** 1 → 2 → 3 → {4, 5} → 6 → 7 → 8 → 9 → 10 → 11.
Tasks 4 and 5 are independent of each other. Every notebook task depends on all module tasks.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/analysis/__init__.py` | Package marker |
| `src/analysis/load.py` | XLSX → tidy frame, with shape validation |
| `src/analysis/clean.py` | Seven corrections + quality report |
| `src/analysis/metrics.py` | Derived metrics and analytical measures |
| `src/analysis/plots.py` | Shared Turkish chart style, PNG writer |
| `src/analysis/forecast.py` | Baselines, features, LightGBM, walk-forward |
| `notebooks/analiz.ipynb` | The seven tasks, charts and commentary |
| `tests/test_analysis_*.py` | One test module per source module |
| `figures/` | Generated PNGs (gitignored — regenerable) |

---

## Reference Documents

Consult these only when a task points you at them — do not read them up front.

| Document | When you need it |
|---|---|
| `docs/01-veri-kesif-bulgulari.md` §2 | The measured data facts. **Every number in a test assertion comes from here** |
| `docs/bolum2-analiz/TRD.md` | Full technical design: formulas, model features, per-task methodology |
| `docs/bolum2-analiz/PRD.md` | Acceptance criteria (§4) and the ten analytical decisions V1–V10 (§5) |
| `docs/02-karar-kaydi.md` | ADR-009 (modules over notebook cells), ADR-010 (no SARIMA/Prophet) |

## Where We Are

Current phase and next concrete step live in [PROGRESSION.md](../../../../PROGRESSION.md).
Durable lessons and decisions live in [MEMORY.md](../../../../MEMORY.md).
