# Fix Task: Funnel State Progression + Confidence Calculation

## Confirmed bug #1 — priority, fix first

In `qd/kernel.py`, `_assess()` runs this loop:

```python
for e in retrieved:
    elim = self._eliminate_with_evidence(claim, e, base)
```

`base` is the same static list of original explanations on every single
iteration. Each evidence item is being judged against the full original
lineup — including explanations already eliminated by earlier evidence —
instead of against only the candidates still actually alive.

**Live verified impact:** running the merged funnel against real Ollama +
real retrieved evidence, on claims that resolved correctly before this
rework (e.g. "the Earth is flat" → REFUTED), produces UNCERTAIN with 0
survivors instead. Ledger trace confirmed the failure pattern directly:
one evidence item eliminating most of the base at once, several evidence
items in the middle eliminating nothing, and a later evidence item wiping
out multiple remaining survivors simultaneously — consistent with the
model repeatedly re-judging against a stale, non-shrinking candidate list
rather than a genuinely narrowing one.

**Required fix:** each evidence item's elimination call must only be
shown the candidates still surviving *at that point* in the loop — not
the original base. The candidate set must narrow incrementally, evidence
item by evidence item, not all at once at the end.

## Confirmed bug #2 — separate, also real

`_funnel_confidence()` only calculates an evidence-sensitive number for
the single-survivor case. The zero-survivor branch always returns a
hardcoded `0.15`. The multiple-survivor branch always returns a
hardcoded `0.30`. Neither reflects the actual strength or quantity of
evidence — they're constants, not calculations.

**Required fix:** make confidence in both branches reflect the actual
evidence — e.g. how many evidence items contributed to eliminating the
base to zero, or how close/far apart the surviving candidates are — the
same way the single-survivor branch already scales with
`eliminated_frac`. If a clean evidence-sensitive formula isn't obvious,
it is acceptable to leave the current constants in place **but log this
explicitly in the change summary as an unresolved follow-up** — do not
silently leave it and call the fix complete.

## Required new test — this is not optional

Add a regression test that would have caught bug #1. Design (per
independent review, both Claude and Q converged on this shape
separately):

- Set up several hypotheses.
- Evidence item 1 eliminates some of them.
- Evidence item 2 should be shown *only* the remaining survivors.
- **The test must fail if evidence item 2 receives the original full
  candidate list instead of the narrowed one.**
- This means the test needs to inspect what candidate set was actually
  *passed into* each elimination call — not just check the final output
  or the final survivor count. Checking the input to each call is the
  point; checking only the end result would not have caught this bug
  and won't catch its regression either.

## Hard constraints — same as the original bake-off task

- Preserve every existing passing test — the original 7 in
  `qd/test_kernel.py` and the 22 in `qd/test_funnel.py`. Nothing that
  passes today may start failing.
- Do NOT change Falsifier behavior, Evidence Policy logic, or the
  Ledger schema.
- Do NOT modify files outside `qd/kernel.py` and its test file unless
  strictly necessary. If you must touch another file, explain why in
  your summary — don't do it silently.
- Do not remove the existing hypothesis-ID safety check (rejecting
  unknown or already-eliminated ids) — that protection was reviewed and
  ratified as a permanent requirement, not optional scope from the
  original build.

## Deliverable

1. A concise summary of what changed and why, for both bugs.
2. Explicit confirmation of how bug #2 was handled — fixed with a real
   formula, or logged as an acknowledged follow-up. Either is
   acceptable; silence is not.
3. A list of every file touched.
4. Confirmation that all tests — old and new — pass.
5. Confirmation the new regression test actually inspects the input to
   each elimination call, not just final output.
