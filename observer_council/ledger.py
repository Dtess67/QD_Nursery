from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _utcnow_str() -> str:
    return datetime.now(timezone.utc).isoformat()


class CouncilLedger:
    """
    Append-only log of a council session. Same philosophy as the QD
    kernel's flight recorder — every phase, every response, every
    failure gets written, not just the final synthesis. JSONL, one
    event per line, never rewritten.
    """

    def __init__(self, log_path: str = "council_ledger.jsonl"):
        self.log_path = Path(log_path)

    def log(self, session_id: str, event_type: str, payload: dict) -> None:
        entry = {
            "session_id": session_id,
            "event_type": event_type,
            "payload": payload,
            "timestamp": _utcnow_str(),
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def get_session(self, session_id: str) -> list[dict]:
        if not self.log_path.exists():
            return []
        events = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry["session_id"] == session_id:
                    events.append(entry)
        return events

    def print_session(self, session_id: str) -> None:
        events = self.get_session(session_id)
        if not events:
            print(f"No events found for session {session_id}")
            return
        print(f"\n{'='*70}\nCOUNCIL SESSION: {session_id}\n{'='*70}")
        for e in events:
            print(f"\n[{e['event_type']}] {e['timestamp']}")
            for k, v in e["payload"].items():
                text = str(v)
                if len(text) > 300:
                    text = text[:300] + "... [truncated for display]"
                print(f"  {k}: {text}")
        print(f"\n{'='*70}\n")
