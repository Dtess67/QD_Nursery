# Established Results
**Repeatedly observed, survived testing. Not axioms (chosen) — these
were confirmed, not decided.**

- Sign/reason mismatch at the KernelVerdict boundary is caught and
  raises an error — confirmed via automated behavioral test.
- Falsifier bypass is structurally detected — `assert_was_called()`
  raises `FalsifierSkippedError` when the gate is skipped — confirmed
  via automated behavioral test.
- Evidence Policy v0.2 is symmetric in practice, not just in design —
  confirmed via 5/5 behavioral tests covering SUPPORTED, REFUTED, and
  CONTESTED verdict directions.
- Ledger is genuinely append-only — no `update()` or `delete()` method
  exists on the `Ledger` class — confirmed by inspection and test.
- Reconciliation scars are logged with original and corrected values
  intact, not overwritten — confirmed via automated test.
- Ledger failure does not crash the kernel — confirmed via induced
  failure test.
- Source tiering filters low-tier (social/forum) sources before they
  reach the assessor, without zeroing their confidence to nothing —
  confirmed via mocked Tavily response containing Facebook and Twitter
  results, both correctly excluded.
- Live run (July 1) with retrieval + tiering active: water/H2O claim
  returned SUPPORTED at 0.90 confidence with real external sources;
  alcohol-health-benefits claim correctly returned UNCERTAIN — the
  Falsifier caught non-peer-reviewed secondary sources rather than
  accepting a confident-sounding synthesis.
- Retrieval-result variance across two runs of the identical Earth-flat
  claim was traced, via the run-comparison tool, to a difference in
  which sources Tavily returned (one run included nasa.gov, the other
  didn't) — not to Falsifier inconsistency. The Falsifier reasoned
  consistently given what it was shown both times.
- Elimination-funnel Assessor mechanics implemented and deterministically
  tested. Built, integrated into `qd/kernel.py`'s `_assess` path (not a
  stranded branch), passing 30/30 tests in `qd/test_funnel.py` — candidate
  narrowing across evidence, the four outcome mappings, same-polarity
  survivor corroboration, Evidence Policy symmetry, reconciliation scars.
  On `origin/main` at commit 678fd37 (July 5), via 1628cc9 (July 4
  bakeoff) and fixes 1b65edb (funnel state progression + confidence
  formula) and 678fd37 (survivor-polarity classification). Established at
  automated behavioral-test level only: the tests mock the model, so they
  establish that the funnel narrows, reads polarity, and rejects unknown/
  already-eliminated candidate ids correctly — deterministic mechanics.
  Mechanics confirmed; live behavior pending. No live Qwen + Tavily funnel
  run exists yet; every live-run entry in this file is pre-funnel (July 1).
  A live run extends this entry when done — it is not what this entry
  claims. (Reconciled July 6; the July-4 07_DECISION_LOG entry was
  accurate, files 03/05 and Constitution §12 had lagged.)
- Defensive requirement — ignore hypothesis ids that are unknown or
  already eliminated (ratified July 4, 07_DECISION_LOG, Darrell's "Leave
  it in") — present in `_run_funnel` (`i in by_id and i in alive`, plus
  `dict.fromkeys` batch dedup) and covered by a named test,
  `test_run_funnel_ignores_unknown_and_already_eliminated_ids`. Present in
  code and mechanically tested — same deterministic scope as the entry
  above; not a live-run claim.
