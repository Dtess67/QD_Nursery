# Fix Task: Survivor Polarity Classification

## Confirmed bug — found via live run, diagnosed jointly with Q

`_funnel_outcome()` currently maps outcomes purely by **counting**
survivors:

- 1 survivor → SUPPORTED/REFUTED
- >1 survivor → always CONTESTED
- 0 survivors → UNCERTAIN

This is too crude. It never checks whether multiple survivors actually
**disagree** with each other, or just **agree via different reasoning
paths**.

**Live verified impact:** claim "The Earth is flat," real Ollama run.
5 hypotheses generated, evidence narrowed the field to exactly 2
survivors. Both surviving hypotheses independently concluded the
Earth is round — one citing satellite imagery, the other citing
horizon-curvature and lunar-eclipse-shadow evidence. They agree with
each other. Neither supports "the Earth is flat." This was scored
CONTESTED, confidence 0.44 — and the Falsifier correctly rejected it,
noting the survivors don't actually conflict. Two independent lines of
evidence converging on the same answer is corroboration, not a contest.

**Important — confirm before treating this as new work:** polarity
(supported/refuted) is already tagged on each hypothesis at generation
time — `_generate_explanations` already produces polarity-tagged
candidates, and this is visible in the existing elimination prompt
formatting. **Do not build a new tagging system.** The bug is narrower
than that: `_funnel_outcome` has access to each surviving hypothesis's
existing polarity and simply never inspects it — it only counts.
Confirm this is accurate against the current code before starting; if
polarity turns out not to already be a reliable structured field on
`_Explanation`, say so and treat that as its own finding rather than
assuming.

## Required new outcome logic

Per joint review (Claude + Q), the mapping should become:

- **Zero survivors** → UNCERTAIN (unchanged)
- **One survivor** → outcome = that survivor's polarity (unchanged)
- **Multiple survivors, same polarity** → outcome = the shared polarity
  (SUPPORTED or REFUTED, not CONTESTED). Confidence should reflect
  corroboration — it should rise as more independent survivors agree,
  capped at a reasonable ceiling, not treated as an uncertain case.
- **Multiple survivors, mixed polarity** → CONTESTED (this is the only
  case that should actually produce CONTESTED going forward)
- **Multiple survivors, unclear/neutral polarity** → UNCERTAIN

**Hard requirement on how polarity gets checked:** do not casually
infer agreement from the wording or tone of the surviving explanations.
Polarity must be read from the existing structured field set at
generation time. If that field is ever missing or ambiguous for a
surviving hypothesis, treat that case as unclear polarity → UNCERTAIN,
not as a guess.

## Required new tests

Add regression tests covering all four real scenarios, not just the
happy path:

1. Multiple survivors, all polarity=SUPPORTED → outcome SUPPORTED,
   confidence reflects convergence.
2. Multiple survivors, all polarity=REFUTED → outcome REFUTED,
   confidence reflects convergence. (This is the exact Earth-flat case
   — worth mirroring directly as a test.)
3. Multiple survivors, mixed polarity (some SUPPORTED, some REFUTED)
   → outcome CONTESTED.
4. Multiple survivors, unclear/neutral polarity → outcome UNCERTAIN.

## Hard constraints — same as prior fix tasks

- Preserve every existing passing test — the original 7, the 22 funnel
  tests, and the bug-#1 regression test (23 total going in). Nothing
  that passes today may start failing.
- Do NOT change Falsifier behavior, Evidence Policy logic, or the
  Ledger schema.
- Do NOT modify files outside `qd/kernel.py` and its test file unless
  strictly necessary — explain in the summary if you must.
- Do not remove the hypothesis-ID safety guard — ratified as permanent.
- Do not touch the zero-survivor or single-survivor confidence formulas
  from the previous fix — they're already working and verified live.
  This task only adds the same-polarity-convergence path and the
  mixed/unclear polarity routing.

## Deliverable

1. Concise summary of what changed and why.
2. Explicit confirmation of whether polarity already existed as a
   structured field (expected) or had to be added (unexpected finding
   — flag clearly if so).
3. List of every file touched.
4. Confirmation all tests — old and new — pass.
5. Confirmation the new tests check actual polarity-based routing, not
   just survivor count.
