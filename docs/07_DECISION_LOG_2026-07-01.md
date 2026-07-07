# Decision Log — 2026-07-01

**Format: Decision / Reason / Consequence. One entry, no essays. If an
entry grows past a few lines, it belongs in the Constitution or a
Working Hypothesis instead — move it there.**

---

**Decision:** QD redefined as the whole being; the kernel is one organ
inside her, not the whole of her.
**Reason:** Earlier drift used "QD" to mean only the constitutional
kernel.
**Consequence:** Constitution §0 logs this revision explicitly. Carto,
Newsroom, future systems are applications that use QD, not pieces of
her.

---

**Decision:** Self-override routes through the same Falsifier /
Evidence Policy as any external challenge. No privileged internal
channel.
**Reason:** Truth doesn't care who brought the evidence.
**Consequence:** Constitution §4.

---

**Decision:** Evidence Policy made symmetric (v0.2).
**Reason:** v0.1 only checked the supporting side; model memory could
refute a claim without the gate firing.
**Consequence:** Both directions now held to identical standard.

---

**Decision:** Adopted three independent behavioral layers — Curiosity,
Exploration Aggressiveness, Human Safety — replacing a single graduated
consequence scale.
**Reason:** Injuring a person is not "a bigger scar" than cracking a
shell — it's a different category. Grounded in the 2018 Uber/Herzberg
case: sensors detected the pedestrian, the failure was in continuity of
belief, not detection.
**Consequence:** Constitution §8. Layer 3 is non-bypassable and does
not loosen with maturity or track record.

---

**Decision:** Emotional modeling defined by function, not human
phenomenology.
**Reason:** Preserve fast pre-conscious hazard detection without
human-emotion baggage or decision authority.
**Consequence:** Constitution §9. Weighted attention signals (hazard
salience, novelty, attachment, curiosity) request attention; they never
decide truth.

---

**Decision:** Adopted Q's principle — "Reality has authority over QD.
QD has authority only over her current understanding of reality."
**Reason:** Generative principle behind the Falsifier, Evidence Policy,
ledger, and self-override — makes the derivation explicit instead of
leaving it implicit.
**Consequence:** Constitution §2, with a scope note limiting it to
epistemic claims — it does not govern constitutional value commitments
like Layer 3.

---

**Decision:** Epistemic status expanded to four tiers — Axiom,
Established Result, Working Hypothesis, Open Problem.
**Reason:** "Established vs. explicitly open" (original Constitution
§12 framing) didn't distinguish a chosen ground rule from a tested
result. Conflating them lets yesterday's guess quietly become today's
assumed fact.
**Consequence:** This project folder's file structure (03 through 06,
08) directly implements this.

---

**Decision:** Split "layers" into two explicitly separate, differently
named stacks.
**Reason:** Last night's seven-part cognitive breakdown (Kernel,
Cognition, Ledger, Frame Selection, Expression Spine, Character,
Personality) and today's three-part safety breakdown (Curiosity,
Exploration Aggressiveness, Human Safety) were both called "layers"
despite measuring completely different axes — a naming collision
waiting to cause real confusion.
**Consequence:** Renamed to **Cognitive Stack** and **Behavioral
Governance**. They can now evolve independently without the word
"layer" meaning two things in the same folder.

---

**Decision:** Adopted a third independent tagging axis — Ontology /
Governance / Epistemology — for classifying any design statement.
**Reason:** Proposed by Q as a generalization of the epistemic-tier and
stack-naming fixes above; lets any statement carry where it lives, what
it permits, and how certain it is, independently.
**Consequence:** Agreed as method. Not yet applied retroactively to
existing documents — see 05_WORKING_HYPOTHESES.

---

**Decision:** Reality-authority axiom refined as a "bootstrap axiom" —
distinct from an arbitrary preference axiom.
**Reason:** Q's pushback: the axiom isn't just chosen, it's chosen
specifically to commit the system to future empirical correction. That
purpose distinguishes it from an axiom like "always maximize
happiness."
**Consequence:** Distinction preserved in Constitution §2 framing.

---

**Decision:** Project folder structure adopted; "Bootstrap Prompt"
language dropped in favor of "Orientation."
**Reason:** Bootstrap implies starting from nothing. Orientation
implies you're already somewhere and need bearings — more accurate to
what these documents actually do.
**Consequence:** 01 and 02 in this folder are titled Orientation, not
Bootstrap.

---

**Decision:** Added this decision log and 08_FAILED_HYPOTHESES as
permanent, growing artifacts.
**Reason:** Operationalizes the Constitution §5 principle — "being
wrong is a positive event when provable and repeatable" — as an actual
file instead of just a sentence.
**Consequence:** Future sessions append here rather than re-deriving
or re-litigating settled decisions.

---

**Decision:** Funnel-based Assessor rework implemented (bake-off
between Claude Agent and Codex, identical task spec, both on isolated
git branches from the same clean baseline).
**Reason:** Working Hypothesis confirmed viable in code, not just
design. Verified via actual `git diff --stat` and `pytest -v` output,
not either agent's self-reported summary.
**Consequence:** Role split adopted per Q's ruling — Claude Agent as
primary implementer for precision-heavy kernel work, Codex as patch-
discipline reviewer pushing toward smaller/simpler equivalents.
Darrell accepts only after tests are individually named, edge cases
are explicit, and no unrequested behavior ships unratified.

---

**Decision:** Funnel implementation must reject or safely ignore
hypothesis IDs that do not exist or were already eliminated.
**Reason:** Originated as unprompted defensive code from Claude Agent
during the bake-off — not in the original task spec. Q flagged this as
a real risk category: unrequested initiative can become silent
architecture drift if adopted by default rather than by decision.
Darrell reviewed and ratified it explicitly: "I'm a data person. Leave
it in."
**Consequence:** This protection is now a requirement for any future
implementation of the Assessor, not a one-off feature specific to
whichever branch happened to include it.

---

**Decision:** Funnel Assessor status reconciled — moved from Working
Hypothesis (05) to Established Result (06) at the mechanics/deterministic
level only; 03 and Constitution §12 updated to match; §12 narrowed (not
struck) to keep live confirmation explicitly open.
**Reason:** Direct repo check (origin/main @ 678fd37, 30/30 in
test_funnel.py, `_assess` path integration, defensive-id test all
verified) showed the July-4 bakeoff entry was accurate while 03, 05, and
§12 had lagged four days — documentation drift, the failure mode this
folder exists to catch. Q reviewed independently and converged, supplying
the controlling rule (Established at behavioral-test level only; no
implication of live validation) and the narrowed §12 wording, adopted
verbatim.
**Consequence:** Docs now match code and each other. The "mechanics
confirmed / live behavior pending" split is preserved everywhere rather
than rounded up to "validated." Live Qwen + Tavily funnel run remains the
open item. §12 edit carries Q's sign-off; applied with Darrell's approval
as the third party. Separately: the evidence-endorsement fix (found live —
a satirical flat-earth source mislabeled as endorsing) is stashed WIP,
deterministically passing (40 tests) but live-run still owed — tracked as
the next job, not part of this reconciliation.
