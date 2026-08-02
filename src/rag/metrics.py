"""Persistent record of every agent run, for comparing models.

SQLite because it is in the standard library, needs no server, and one file is
easy to ship or delete. Unmeasured values are stored as NULL rather than 0 —
SQL aggregates skip NULLs, so an unpriced model lowers no average, and
`priced_runs` reports how much of a total is actually known.
"""

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    model_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    question TEXT NOT NULL,
    latency_ms INTEGER NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    citation_count INTEGER NOT NULL,
    gate_passed INTEGER NOT NULL,
    tool_calls INTEGER NOT NULL,
    repaired INTEGER NOT NULL
)
"""


@dataclass
class RunRecord:
    model_id: str
    provider: str
    question: str
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    citation_count: int
    gate_passed: bool
    tool_calls: int
    repaired: bool
    ts: str | None = None


@dataclass
class ModelSummary:
    model_id: str
    provider: str
    runs: int
    priced_runs: int
    avg_latency_ms: float
    total_cost_usd: float | None
    avg_citations: float
    gate_pass_rate: float


class MetricsStore:
    """One SQLite file. A fresh connection per call — Streamlit is multi-threaded."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def record(self, run: RunRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (ts, model_id, provider, question, latency_ms,
                                  input_tokens, output_tokens, cost_usd,
                                  citation_count, gate_passed, tool_calls, repaired)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    run.model_id,
                    run.provider,
                    run.question,
                    run.latency_ms,
                    run.input_tokens,
                    run.output_tokens,
                    run.cost_usd,
                    run.citation_count,
                    int(run.gate_passed),
                    run.tool_calls,
                    int(run.repaired),
                ),
            )

    def recent(self, limit: int = 200) -> list[RunRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [
            RunRecord(
                model_id=row["model_id"],
                provider=row["provider"],
                question=row["question"],
                latency_ms=row["latency_ms"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                cost_usd=row["cost_usd"],
                citation_count=row["citation_count"],
                gate_passed=bool(row["gate_passed"]),
                tool_calls=row["tool_calls"],
                repaired=bool(row["repaired"]),
                ts=row["ts"],
            )
            for row in rows
        ]

    def summary_by_model(self) -> Iterable[ModelSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT model_id, provider,
                       COUNT(*)              AS runs,
                       COUNT(cost_usd)       AS priced_runs,
                       AVG(latency_ms)       AS avg_latency_ms,
                       SUM(cost_usd)         AS total_cost_usd,
                       AVG(citation_count)   AS avg_citations,
                       AVG(gate_passed)      AS gate_pass_rate
                FROM runs
                GROUP BY model_id, provider
                ORDER BY runs DESC
                """
            ).fetchall()
        return [
            ModelSummary(
                model_id=row["model_id"],
                provider=row["provider"],
                runs=row["runs"],
                priced_runs=row["priced_runs"],
                avg_latency_ms=row["avg_latency_ms"],
                total_cost_usd=row["total_cost_usd"],
                avg_citations=row["avg_citations"],
                gate_pass_rate=row["gate_pass_rate"],
            )
            for row in rows
        ]

    def columns(self) -> list[str]:
        with self._connect() as conn:
            return [row["name"] for row in conn.execute("PRAGMA table_info(runs)").fetchall()]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM runs")
