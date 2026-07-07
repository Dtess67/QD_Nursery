# Fix Task: Evidence Endorsement Classification

## Confirmed bug — found live, diagnosed from real code + real ledger

In `qd/kernel.py`, the `_ELIMINATION_PROMPT` asks the model, per evidence
item:

```
"supports_claim": true or false,    // does this evidence, on net, support the claim?
```

The word "support" is ambiguous between two different meanings:
- "does this evidence ASSERT the claim is true" (what we want), and
- "is this evidence ABOUT / on the topic of the claim" (a false trigger).

**Live verified impact:** on the claim "The Earth is flat," a Guardian
article that *describes and satirizes* flat-earth belief (drenched in
flat-earth language, but arguing the opposite) was tagged as supporting
the claim. The Falsifier correctly caught it and rejected an otherwise-
correct REFUTED verdict. The Assessor's funnel logic was right; the
evidence label was wrong. A source explaining why people believe X is
not support for X.

## Three changes required (reviewed and specified jointly with Q)

### Change 1 — rewrite the endorsement question in `_ELIMINATION_PROMPT`

Replace the ambiguous `supports_claim` line with an explicit,
enumerated definition. Use this content (wording may be lightly adapted
for format, but every listed failure case must survive):

```
source_endorses_claim: true ONLY if the source itself endorses or
concludes that the claim is true.

false if the source:
 - denies the claim,
 - argues against the claim,
 - fact-checks the claim as false,
 - quotes someone else making the claim without endorsing it,
 - explains why people believe the claim,
 - satirizes the claim,
 - discusses the claim as a belief, rumor, theory, controversy, or
   misinformation.

Do NOT mark true merely because the evidence mentions the claim,
describes believers, or contains quoted language asserting the claim.
```

### Change 2 — rename the field `supports_claim` → `source_endorses_claim`

Per Q: "support" is too semantically slippery; "endorses" forces the
right distinction. **IMPORTANT SCOPING NOTE — read before doing this:**

`supports_claim` is not local to `kernel.py`. It is a field on the
`Evidence` schema object (set at `kernel.py` line ~302), and it is
READ by the Evidence Policy and the Falsifier. This task's hard
constraints say do not change Falsifier or Evidence Policy *behavior* —
but a field rename that those files must follow is a mechanical
signature change, not a behavior change, and is acceptable ONLY IF:

- the rename is purely mechanical (same value, same meaning, new name),
- every read site is updated in the same commit so nothing breaks,
- no logic in Falsifier or Evidence Policy changes — only the field
  name they reference.

**If the rename cannot be done without changing behavior in those
files, STOP and report that instead of proceeding.** A clean rename is
preferred; a rename that forces logic changes in protected files is
not worth it — in that case, keep the name `supports_claim` and just
do Changes 1 and 3. Flag clearly which path you took and why.

### Change 3 — fix the default, and make malformed labels visible

Current: `bool(elim.get("supports_claim", True))` — a missing or
malformed label silently defaults to "supports the claim." That is the
wrong direction for a truth-seeking kernel: absence of a clear
endorsement is not endorsement.

Required behavior (per Q):
- explicit true  → endorsement
- explicit false → not endorsement
- missing/malformed → **not endorsement, AND logged as a scar / warning
  in the ledger** (not a silent false). The point: bad JSON must never
  quietly become evidence *for* a claim, and "the model clearly said no"
  must not look identical in the record to "the model returned garbage."

Use the existing ledger scar mechanism if one exists (there is a
RECONCILE_SCAR event type already — check whether a similar
evidence-label scar fits, or whether a new event type is warranted).
Do not invent elaborate new machinery if a simple, existing pattern
already fits.

## Hard constraints

- Preserve every currently passing test (30 going in). Nothing that
  passes today may start failing.
- Do NOT change Falsifier or Evidence Policy *logic/behavior*. A
  mechanical field rename they must follow is acceptable per the
  scoping note in Change 2; a behavioral change is not.
- Do NOT change the Ledger schema in a breaking way. Adding a new event
  type or scar record is acceptable; altering existing event shapes is
  not.
- Do not remove the hypothesis-ID safety guard, the funnel narrowing
  logic, the polarity-based outcome mapping, or any confidence formula
  — all ratified/verified earlier and out of scope here.

## Why this one is harder to verify — read this

This is a PROMPT-WORDING fix at its core. Unlike the previous funnel
fixes, there is no clean deterministic unit test for "did the model
interpret this word correctly" — that only proves out against the live
model on real ambiguous sources. So:

- Unit tests CAN and MUST cover: the default-flip behavior (missing/
  malformed → not endorsement + scar logged), and the field rename not
  breaking any read site.
- Unit tests CANNOT fully prove the prompt wording works. That requires
  a live `test_kernel.py` run against real Ollama, specifically on the
  Earth-flat claim, checking that the previously-mislabeled source is
  no longer tagged as endorsing.
- Be explicit in your summary about which claims are unit-verified vs.
  which need the live run to confirm.

## Deliverable

1. Concise summary of all three changes.
2. Explicit statement of which rename path you took (clean rename, or
   kept `supports_claim` because the rename forced protected-file logic
   changes) and why.
3. Confirmation of how missing/malformed labels are now handled and
   where the scar is logged.
4. List of every file touched — including any outside `kernel.py`, with
   justification per the scoping rules above.
5. Which behaviors are unit-tested vs. which require the live run.
6. Confirmation all existing tests still pass.
