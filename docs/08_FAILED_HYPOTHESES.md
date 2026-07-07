# Failed Hypotheses
**Not failed experiments — failed ideas. What was tried or proposed,
why it looked attractive, why it didn't hold up. Purpose: stop the same
attractive-but-broken idea from getting reinvented in six months with
nobody remembering it already failed once.**

---

**Hypothesis:** Pass only the ternary sign (+1/0/-1) across the kernel
boundary — the kernel doesn't need the full reasoning, just the
verdict.

**Why attractive:** Simpler interface. Fewer fields to validate. Matches
how most systems report a boolean-ish outcome.

**Why it failed:** Sign alone collapses UNCERTAIN and CONTESTED into
an identical 0 — a knowledge gap and an active credible disagreement
look the same to anything downstream, even though they call for
completely different responses.

**Evidence:** Identified before any code was written, in the first
design conversation of the kernel — rejected before being built.

**Date:** 2026-07-01 (morning).

---

**Hypothesis:** Evidence Policy only needs to check the supporting side
of a claim — if a claim is REFUTED, there's no "supporting" evidence to
validate.

**Why attractive:** Simpler check. Matches the intuitive framing of
"prove it's true," not "prove it's false."

**Why it failed:** A model could refute a true claim using nothing but
its own unverified memory, and the policy would never fire, because it
only ever looked at the supporting side. The Earth-flat test case
exposed this directly — REFUTED at high confidence, approved by the
Falsifier, entirely on model-memory evidence, because the gate never
checked.

**Evidence:** Built as v0.1, ran in the live kernel, confirmed via test
output before being replaced by symmetric v0.2 the same day.

**Date:** 2026-07-01.

---

**Hypothesis:** Keep two separate ledgers — one for QD's physical
events (hardware damage, falls) and one for her mental events (wrong
verdicts, corrected beliefs).

**Why attractive:** Feels like a clean separation of concerns — body
data and mind data are different kinds of data.

**Why it failed:** Two separate histories risk the same kind of
self-blindness a person can have — being afraid of heights without
consciously knowing it traces back to a specific fall. If the physical
and mental records don't share one timeline, QD could develop a
behavioral pattern (caution near an edge) with no way to trace it back
to the scar that caused it.

**Evidence:** Proposed and rejected in the same conversation, before
any code was written — replaced by one ledger with physical and mental
events as sibling event families.

**Date:** 2026-07-01.
