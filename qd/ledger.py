from __future__ import annotations

import json
import sqlite3
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventType(str, Enum):
    CLAIM_RECEIVED   = "CLAIM_RECEIVED"    # claim text + submitted confidence
    SOURCE_FILTERED  = "SOURCE_FILTERED"   # retrieval excluded a low-tier source
    ASSESSOR_OUTPUT  = "ASSESSOR_OUTPUT"   # sign, reason, confidence, evidence count
    POLICY_PASS      = "POLICY_PASS"       # policy checked, no violation
    POLICY_VIOLATION = "POLICY_VIOLATION"  # policy fired, verdict downgraded
    FALSIFIER_OUTPUT = "FALSIFIER_OUTPUT"  # approved/rejected, notes, confidence
    RECONCILE_SCAR   = "RECONCILE_SCAR"   # sign/reason mismatch was silently corrected
    EVIDENCE_LABEL_SCAR = "EVIDENCE_LABEL_SCAR"  # endorsement label missing/malformed → defaulted not-endorsing
    VERDICT_ISSUED   = "VERDICT_ISSUED"    # final triple
    EMERGENCY_STOP   = "EMERGENCY_STOP"   # kernel halted


_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT    NOT NULL,
    claim_id    TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    payload     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_run_id   ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_claim_id ON events(claim_id);
CREATE INDEX IF NOT EXISTS idx_type     ON events(event_type);
"""


class Ledger:
    """
    QD flight recorder. Append-only SQLite ledger.

    Records every major epistemic event during a kernel evaluation run —
    not just the final verdict. The goal is to reconstruct the kernel's
    reasoning after the fact, not just see what it decided.

    Never UPDATE. Never DELETE. Only INSERT.
    """

    def __init__(self, db_path: str = "qd_ledger.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def log(
        self,
        run_id:     str,
        claim_id:   str,
        event_type: EventType,
        payload:    dict,
    ) -> None:
        """Append one event. Never modifies existing rows."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (run_id, claim_id, event_type, payload, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, claim_id, event_type.value, json.dumps(payload), _utcnow_str()),
            )

    def get_run(self, run_id: str) -> list[dict]:
        """All events for a single evaluation run, in order."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event_type, payload, created_at "
                "FROM events WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
        return [
            {
                "id":         r[0],
                "event_type": r[1],
                "payload":    json.loads(r[2]),
                "created_at": r[3],
            }
            for r in rows
        ]

    def recent_runs(self, n: int = 10) -> list[str]:
        """Last N distinct run_ids, most recent first."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT run_id FROM events "
                "ORDER BY id DESC LIMIT ?",
                (n,),
            ).fetchall()
        return [r[0] for r in rows]

    def print_run(self, run_id: str) -> None:
        """Pretty-print a full run to stdout."""
        events = self.get_run(run_id)
        if not events:
            print(f"No events found for run {run_id}")
            return
        print(f"\n{'─'*60}")
        print(f"LEDGER RUN: {run_id}")
        print(f"{'─'*60}")
        for e in events:
            print(f"\n[{e['event_type']}] {e['created_at']}")
            for k, v in e['payload'].items():
                print(f"  {k}: {v}")
        print(f"{'─'*60}\n")

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")   # safe concurrent reads
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
