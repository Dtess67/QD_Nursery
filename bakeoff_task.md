# Bake-Off Task: Funnel-Based Assessor Rework

## Current behavior (for context)
`qd/kernel.py`'s `_assess()` method currently asks the model for a single-shot
verdict — one sign, one reason, one confidence — in one LLM call. The model
guesses once and that guess becomes the proposed verdict.

## Required new behavior
Replace single-shot guessing with an elimination-funnel pattern:

1. The Assessor first generates a **wide base of plausible explanations**
   for the claim — not just one candidate answer.
2. Each piece of retrieved evidence is used to **eliminate explanations it
   contradicts** — evidence narrows the candidate set, it doesn't just
   support or oppose a single pre-picked answer.
3. The process converges to exactly one of four outcomes:
   - **One explanation survives** → sign = SUPPORTED or REFUTED (whichever
     the surviving explanation corresponds to)
   - **More than one explanation survives** and the evidence can't
     separate them → sign = UNCERTAIN, reason = CONTESTED
   - **Nothing in the original base survives and nothing replaces it** →
     sign = UNCERTAIN, reason = UNCERTAIN

## Hard constraints
- Preserve every existing passing test in `test_kernel.py` and any tests
  already in the `qd/` package. Nothing that passes today may start failing.
- Do NOT change Falsifier behavior, Evidence Policy logic, or the Ledger
  schema. This task is scoped to the Assessor's reasoning process only.
- Do NOT modify files outside `qd/kernel.py` unless strictly necessary. If
  you must touch another file, explain why in your summary — don't do it
  silently.

## Required new tests
Add tests proving:
1. The funnel genuinely narrows a candidate set across multiple evidence
   items — not a single-shot guess wearing new terminology.
2. All four outcome mappings are correct (one survivor → SUPPORTED/REFUTED,
   multiple survivors → CONTESTED, none survive → UNCERTAIN).
3. Existing kernel behavior is unaffected — symmetric Evidence Policy,
   ledger logging, and reconciliation scar logging all still pass unchanged.

## Deliverable
1. A concise summary of what changed and why.
2. A list of every file touched.
3. Confirmation that all tests (old and new) pass.
4. Do not touch the Falsifier, Evidence Policy, Ledger, or Retriever files.
   If you believe you must, stop and explain instead of proceeding.
