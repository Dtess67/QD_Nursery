# Build Status
**As of July 1, 2026. In code, tested, committed.**
**Updated July 5–6, 2026 — funnel Assessor moved from "not yet built" to
implemented + deterministically tested (mechanics only; live run pending).
Commit count corrected.**

- Ternary truth system: triple (sign, reason, confidence) at every
  kernel boundary — never sign alone.
- Falsifier — structurally required, cannot be bypassed, confidence
  acts only as a ceiling.
- Evidence Policy v0.2 — symmetric, both supporting and refuting sides
  held to identical standard, model memory never valid evidence in
  either direction.
- Flight recorder ledger — SQLite, append-only, reconciliation scars
  logged rather than silently corrected.
- Retrieval layer — Tavily integration, real external sources.
- Source quality tiering — 4-tier domain classification, low-trust
  sources filtered (never zeroed) before reaching the assessor.
- Split error taxonomy — structural violations vs. runtime failures.
- Run-comparison tool — surfaced that retrieval variance, not Falsifier
  inconsistency, explained a verdict flip between two runs of the same
  claim (real diagnostic finding, not yet resolved in code).
- Elimination-funnel Assessor — wide polarity-tagged base, incremental
  evidence-driven narrowing, survivors mapped to the ternary output
  (same-polarity = corroboration, mixed = CONTESTED). Integrated into the
  `_assess` path; 30/30 tests in `qd/test_funnel.py`. Mechanics only —
  live Qwen + Tavily behavior pending. See 06_ESTABLISHED_RESULTS.

**Repo:** github.com/Dtess67/QD_Nursery — head 678fd37, 7 commits as of
July 5.

**Not yet built:** Approval TTL, claim decomposition.
See 05_WORKING_HYPOTHESES.md.
