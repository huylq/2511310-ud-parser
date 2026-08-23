"""Spend ledger with hard-stop enforcement.

CLAUDE.md rule 5: budget caps abort the flow, they do not warn. This module is the
only place that decides whether a call is affordable, and it refuses *before* the
call is made -- a cap discovered after spending the money is not a cap.

The ledger is SQLite on a mounted volume so spend survives container restarts. A
per-flow budget that resets on crash-loop is not a budget.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .policy import Model, estimate_usd


class BudgetExceeded(RuntimeError):
    """Hard stop. Never catch this to continue -- catch it only to shut down."""


@dataclass(frozen=True)
class Spend:
    flow_usd: float
    day_usd: float
    total_usd: float
    calls: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS spend (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    day          TEXT    NOT NULL,
    flow_run_id  TEXT    NOT NULL,
    task         TEXT    NOT NULL,
    model        TEXT    NOT NULL,
    input_tokens  INTEGER NOT NULL,
    cached_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    usd          REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS spend_day ON spend(day);
CREATE INDEX IF NOT EXISTS spend_flow ON spend(flow_run_id);
"""


class BudgetLedger:
    """Append-only spend log that gates every paid call."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        flow_cap_usd: float | None = None,
        daily_cap_usd: float | None = None,
        total_cap_usd: float | None = None,
    ) -> None:
        self.db_path = Path(
            db_path or os.getenv("VIETNLP_BUDGET_DB", "/data/budget/spend.db")
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.flow_cap = _cap(flow_cap_usd, "VIETNLP_FLOW_CAP_USD", 5.0)
        self.daily_cap = _cap(daily_cap_usd, "VIETNLP_DAILY_CAP_USD", 20.0)
        self.total_cap = _cap(total_cap_usd, "VIETNLP_TOTAL_CAP_USD", 200.0)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level="IMMEDIATE")
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def spent(self, flow_run_id: str) -> Spend:
        today = date.today().isoformat()
        with self._connect() as conn:
            flow = conn.execute(
                "SELECT COALESCE(SUM(usd), 0), COUNT(*) FROM spend WHERE flow_run_id = ?",
                (flow_run_id,),
            ).fetchone()
            day = conn.execute(
                "SELECT COALESCE(SUM(usd), 0) FROM spend WHERE day = ?", (today,)
            ).fetchone()[0]
            total = conn.execute("SELECT COALESCE(SUM(usd), 0) FROM spend").fetchone()[0]
        return Spend(flow_usd=flow[0], day_usd=day, total_usd=total, calls=flow[1])

    def check_affordable(
        self, flow_run_id: str, model: Model, est_input: int, est_output: int
    ) -> float:
        """Raise BudgetExceeded if this call would breach any cap. Returns estimate."""
        estimate = estimate_usd(model, est_input, est_output)
        s = self.spent(flow_run_id)
        for name, used, cap in (
            ("flow", s.flow_usd, self.flow_cap),
            ("daily", s.day_usd, self.daily_cap),
            ("total", s.total_usd, self.total_cap),
        ):
            if used + estimate > cap:
                raise BudgetExceeded(
                    f"{name} budget would be exceeded: spent ${used:.4f} + "
                    f"estimated ${estimate:.4f} > cap ${cap:.2f} "
                    f"(flow_run_id={flow_run_id}). Aborting."
                )
        return estimate

    def record(
        self,
        *,
        flow_run_id: str,
        task: str,
        model: Model,
        input_tokens: int,
        cached_tokens: int,
        output_tokens: int,
    ) -> float:
        """Log actual usage after a call. Returns the actual USD charged."""
        usd = estimate_usd(model, input_tokens, output_tokens, cached_tokens)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO spend (day, flow_run_id, task, model, input_tokens, "
                "cached_tokens, output_tokens, usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    date.today().isoformat(),
                    flow_run_id,
                    task,
                    model.value,
                    input_tokens,
                    cached_tokens,
                    output_tokens,
                    usd,
                ),
            )
        return usd

    def report(self, flow_run_id: str | None = None) -> list[tuple]:
        """Spend broken down by task and model, for the operator."""
        sql = (
            "SELECT task, model, COUNT(*), SUM(input_tokens), SUM(cached_tokens), "
            "SUM(output_tokens), ROUND(SUM(usd), 4) FROM spend "
        )
        params: tuple = ()
        if flow_run_id:
            sql += "WHERE flow_run_id = ? "
            params = (flow_run_id,)
        sql += "GROUP BY task, model ORDER BY SUM(usd) DESC"
        with self._connect() as conn:
            return conn.execute(sql, params).fetchall()


def _cap(explicit: float | None, env_var: str, default: float) -> float:
    value = explicit if explicit is not None else float(os.getenv(env_var, default))
    if value <= 0:
        raise ValueError(f"{env_var} must be positive, got {value}")
    return value
