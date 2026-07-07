# Model Provenance Risks
**Proposed by Q, July 2026: "These aren't properties of QD. They're
properties of the instruments used to build QD. Scientists document
their instruments. We should too."**

**This file documents constraints, not verdicts.** "Known documented
limitations on specific political topics" is metadata. "Model X is
unreliable" is a judgment. This file contains only the former.

**Template, per Q's refinement:** Organization · Primary strengths ·
Known limitations · Documented evidence · Conflict-of-interest notes ·
Recommended roles · Recommended non-roles · Last reviewed.

Every entry below is drawn from a real conversation on this project,
not a hypothetical placeholder — same standard as everything else in
this folder.

---

## Claude (Anthropic)

**Role in this project:** Kernel architect, primary implementer for
precision-heavy code (per July 4 bake-off ruling), Observer Council
participant.

**Recommended roles:** Precision-heavy multi-file kernel
implementation; architectural decomposition; long-form technical
writing; contradiction detection.

**Recommended non-role:** Sole synthesizer of a Council result Claude
personally participated in — read raw Phase 1/2 transcripts directly
for anything load-bearing, not just Claude's summary of them.

**Known constraint — structural, not political:** In this specific
project, Claude is both a Council participant and typically the one
synthesizing council results for Darrell — the same structural overlap
flagged for Qwen (Assessor/Falsifier sharing an engine). When it
matters, read raw Phase 1/2 transcripts directly rather than relying
solely on Claude's summary.

**Known constraint — unverifiable from the inside:** Unlike Qwen and
DeepSeek, no independent outside research has audited Claude's
specific behavioral tendencies at the level of detail this registry
documents for those two. This entry is Anthropic-trained self-report,
not third-party verified, and Claude has no privileged access to its
own training process to fully audit this itself.

**Known constraint — general category concern:** RLHF-tuned assistant
models as a category have documented tendencies toward agreeableness
with the person they're talking to — a general, publicly discussed
concern, not specific evidence about this model.

**Confirmed in practice (July 4, 2026 bake-off):** Q reviewed Claude's
own scoring of a head-to-head comparison Claude was personally part of
and found one real instance of self-favorable scoring — full credit
given to an unprompted Claude Agent feature that should have been
scored as open scope, not automatic credit. Corrected on review. Logged
here as evidence the self-audit gap above is real, not theoretical.

---

## DeepSeek (DeepSeek AI)

**Role in this project:** Proposed Observer Council member (online/
hosted API, not self-hosted).

**Known constraint:** Restrictions are documented at the fine-tuning
stage, not an app-level filter — confirmed by independent research
(Cisco/UPenn, Promptfoo's public 1,360-prompt dataset, a separate
deep-dive tracing it to the SFT stage specifically). Bounded and
identifiable: Tiananmen Square, Taiwan, Xi Jinping, the Cultural
Revolution, and scripted non-answers on topics like Russia/Ukraine.
Base model and an earlier RL checkpoint were both uncensored prior to
that stage.

**Known constraint — data path:** Hosted API, not self-hosted — prompts
reach servers in the PRC. The company cannot legally resist state data
requests the way a Western provider could contest one in court.

**How to read a gap:** DeepSeek's silence or deflection on the topic
class above should be read as a known, documented gap — not as absence
of disagreement among the panel on that question.

---

## GPT (OpenAI) — "Q"

**Role in this project:** Systems integration and synthesis;
independent thinking partner alongside Claude; frequent scoring/
ruling voice in Observer Council disputes.

**Conflict-of-interest note — volunteered by Q himself, July 4, 2026,
unprompted, matching the same standard applied to Claude's own entry:**
*"Possible bias: may overweight architectural synthesis. May seek
coherent integration where genuine fragmentation exists. Trained
within OpenAI alignment objectives. Should not be sole reviewer of
OpenAI-related design choices."*

**Recommended non-role:** Sole judge of any dispute where an
OpenAI-family tool (e.g. Codex) is one of the parties being evaluated
— same conflict-of-interest logic applied to Claude scoring its own
bake-off entrant.

---

## Qwen (Alibaba)

**Role in this project:** Currently the actual reasoning engine behind
QD's kernel — both the Assessor and the Falsifier, today, in
production code. Not a Council candidate — already load-bearing.

**Known constraint — the one that matters most:** Independent research
(China Media Project, corroborated by Axios, an Estonian foreign
intelligence assessment, a USC study) found the Qwen3 family goes
beyond refusal — trained to deliver favorable framing on China-related
topics while claiming neutrality elsewhere, roughly 1.5x stronger in
Chinese than English, concentrated in geopolitics and economics. Not
yet directly verified against the specific `qwen2.5:32b` build this
kernel runs.

**Known constraint — structural, independent of the above:** The
Assessor and Falsifier share the same reasoning engine. Even if Qwen
carried no directional lean at all, one model checking its own work is
reduced independence by design — the same failure mode the Falsifier
gate exists to prevent, one layer further down, in the choice of
engine itself. This is the primary open concern, not the political
lean specifically.

---

## Format for future entries

Each entry should carry: role in the project, known strengths (if
established elsewhere), known constraints with their evidentiary basis,
and — where applicable — a note distinguishing structural
independence risk from documented behavioral tendency. Both matter;
they are not the same category, and neither should be silently folded
into the other.
