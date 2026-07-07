# Working Hypotheses
**Plausible, proposed, agreed as the right direction — not yet built
or tested. If built and it holds, moves to 06_ESTABLISHED_RESULTS. If
built and it fails, moves to 08_FAILED_HYPOTHESES.**

- ~~**Funnel-based Assessor rework.**~~ **RESOLVED / SUPERSEDED BY 06
  (July 5, reconciled into docs July 6).** Implemented and
  deterministically tested; moved to 06_ESTABLISHED_RESULTS with narrowed
  wording — mechanics only, live Qwen + Tavily behavior still open.
  Tombstone kept so the move is traceable rather than a silent delete.
- **Approval TTL.** In the original kernel spec, never built.
- **Claim decomposition.** Complex claims (e.g. "moderate alcohol
  consumption has net health benefits") currently treated as atomic.
  Should decompose into sub-claims. Not yet built.
- **Three independent tagging axes** (Ontology / Governance /
  Epistemology) for every design statement in the project. Proposed by
  Q, July 1, agreed by Claude same night. Not yet applied retroactively
  to the Constitution or any orientation document — exists as an agreed
  method, not yet as an artifact.
- **Observer Independence Index.** Proposed by Q, July 4, 2026 —
  emerged from the bake-off and provenance work, not designed in
  advance. The insight: agreement among observers means something
  different depending on their lineage. Five genuinely independent
  lineages converging is a strong signal. Five variants of the same
  underlying model agreeing with each other is a much weaker one, even
  though the raw "4/5 agree" number looks identical. The index doesn't
  judge which answer is correct — it estimates how surprising the
  agreement itself is, given who's doing the agreeing. Not yet
  designed or built. Depends on `09_MODEL_PROVENANCE.md` lineage data
  and, likely, real entries in `10_ROUTING_EXPERIMENTS.md` before a
  concrete formula makes sense.

---

## Reality-architecture cluster (Darrell + Q + Claude, July 5, 2026)

These three are linked — one frame and two capabilities that fall out
of it. Architecture-level, further from buildable code than anything
above. Captured as candidate direction, explicitly NOT a build list.

- **Observer-projection model of reality.** `R_i(t) = O_i(E(t))` —
  each observer/source/sensor receives a partial projection of an
  underlying event that exists whether or not it's sampled. The event
  stays inside the parentheses: observers author projections, never the
  event itself. Keeps QD from collapsing into "everything is
  subjective" — the underlying world resists false models. Core
  consequence: adding a channel doesn't make a picture more *complete*,
  it makes it harder to *fool* — each channel is one more constraint a
  fabrication must satisfy at once. **Truth is what survives every
  competent independent channel trying to catch it lying.** Claude's
  key result: this is structurally the *same machine* as the
  elimination funnel already built — the claim-funnel and the
  observer-funnel are one shape, so QD needs one architecture, not two.
  Three falsifiable requirements this frame generates (the tell that
  it's a model, not a metaphor): (1) channel-competence assignments
  must be ledgered, challengeable claims, never hardcoded; (2) conflict
  handling must follow strict order — disprove the conflict is even
  real (different property? different vocabulary? channel fault?)
  *before* adjudicating it, and preserve both signals before ever
  privileging one, because privileging is irreversible and preservation
  is recoverable; (3) "novel pattern worth curiosity" is a *residual* —
  reachable only after the other explanations fail, never an early
  guess. Open and unsolved: the frame gives the *topology* of
  reconciliation (what to do, in what order) and says nothing yet about
  the *arithmetic* (what confidence number to hold when two real
  channels conflict). Structure first is correct, but the number is a
  separate unsolved problem — do not pretend otherwise.

- **Minority live claim lane.** A protected status for a fringe/minority
  claim that has survived adversarial checks — NOT a claim of truth,
  a claim of "not yet refuted and worth continued pressure." Guards
  against two symmetric failures: conformity (discounting a lone source
  because 500 repeaters disagree) and gullibility (crowning a lone claim
  because it's exciting). Load-bearing sub-principle, strongest single
  idea in the cluster: **repetition is not replication** — 500 posts
  tracing to one source collapse into one evidence family, not 500
  independent confirmations. Consensus is a pointer to evidence
  families, never a vote — and watch specifically for *manufactured*
  consensus (many independent-looking sources that are one funded
  campaign; incentive is a channel property the funnel must actually
  use). **The danger Claude flagged, non-negotiable to fix before this
  is built:** the lane is easier to enter (by "not yet refuted") than
  to leave (no defined exit), and "not yet refuted" is the natural
  resting state of every vague or under-tested claim — so without an
  exit the ledger silently fills with protected anomalies until QD
  can't close any question. The lane is only safe with three additions:
  (1) *cost of entry* — a claim must name the specific future evidence
  that would kill it; a claim that can't say what would disprove it is
  unfalsifiable, not live; (2) *a clock* — a live claim that generates
  no new independent contact decays to DORMANT (shelved, scar intact,
  not refuted, not believed); (3) *a budget* — but see the next entry,
  which supersedes the crude "cap the count" version with a better one.
  False binary to reject: "preserve until broken" (swamp) vs "discard
  until confirmed" (kills every fringe truth in its cradle). Real
  answer is three states — LIVE / DORMANT / REFUTED — where DORMANT is
  the exit that isn't a false verdict.

- **Idle recombination** (informal handle: "dreaming" — used knowingly
  as borrowed human vocabulary, like "scar" and "falsifier"; the
  architecture term is *idle recombination*, which claims only what it
  has earned: *when* without implying effortless/conscious, *what*
  without implying insight/understanding). Converged across a long
  Darrell + Q + Claude session, July 5, 2026. Status: **tightly-scoped
  Working Hypothesis awaiting experiment — parked until real archive/
  ledger runs produce results. Not established, not next on the build
  queue.**

  *The idea:* QD ponders outliers "at her leisure" (Darrell's phrase).
  Clean non-mystical definition: **idle recombination is QD running the
  existing funnel's wide-generation step on its own ledgered material
  during idle time** — the generate step pointed inward instead of
  outward. Adds no new organ; aims an existing one at the shelf during
  quiet hours. Reframes the minority-lane budget problem from the better
  angle: don't cap the shelf (dormant storage is cheap), limit the
  *compute* (reactivation is expensive). Two eventual trigger modes:
  *event-triggered* (a dormant claim wakes when new evidence touches its
  scar — matches how human free-time pondering actually works, you
  revisit a shelved problem when something new bumps into it) and
  *idle-time sweep* (in downtime, revisit oldest live claims, demote the
  stale to dormant, try dormant claims against each other).

  *The value mechanism (mature version, NOT v0):* the phrase QD lives by
  stays — "QD does not love being right, does not love being wrong,
  loves finding out." But testing itself is **not** the terminal reward:
  testing is infinite-supply and becomes busywork if rewarded directly.
  Value appears only when a test produces a ledgered, justified
  confidence change on a claim whose uncertainty **and** consequence were
  already independently warranted. That is scarce, reality-controlled,
  and symmetric across confirmation and refutation. This is mature-version
  accounting, explicitly deferred.

  *Non-negotiable safety rules:*
  (1) **Generates candidates, never verdicts.** A dream proposes; the
  Falsifier disposes. Output lands in the most provisional bin and
  returns to the front of the normal funnel — never skips the Falsifier
  because it "felt like" insight.
  (2) **The generator must not learn from its own hit rate.** "Candidates
  never verdicts" guards the *output*; it does not guard the *generator's
  distribution*. Without this second guard, the generator quietly
  optimizes toward self-flattering survivor types — ego as a feedback
  loop, invisible because each individual candidate still dutifully hits
  the Falsifier. In v0 this is achieved for free by making the generator
  **non-learning** — no survival signal, no confidence-change signal, no
  novelty signal, no Darrell-pleasing signal.
  (3) Superstition, defined mechanically: protecting a claim from the
  requirement to keep making falsifiable contact with reality, regardless
  of how scientific it sounds. The whole cluster exists to prevent this.

  *v0 experiment (the only thing to actually build first):* offline,
  silent, read-only, non-learning, no schema migration, no Falsifier
  bypass, no user-facing surfacing, no actions, no belief updates except
  through the existing funnel. Tests ONLY the cheap claim: *does idle
  recombination ever surface a connection that produces a real confidence
  change the front-door process likely would not have reached?* Not "is
  it high-value" — that comes later, only if this passes.
    - *Input:* existing ledger material only (scars, dormant claims,
      unresolved conflicts, minority-live claims, failed hypotheses,
      anomalies).
    - *Generator:* a deliberately **dumb, mechanical, non-selective**
      pairing/tripling generator (shared keywords, temporal proximity,
      same channel — simple mechanical rules). **Requirement, not
      description:** any "which pairs are worth proposing" intelligence is
      deferred, because a smart pair-picker is an assessor in disguise —
      then you'd be testing the hidden picker, not recombination itself.
    - *Output:* a candidate relation only — parent item IDs, proposed
      link, and a **kill condition** (what would falsify the link). The
      kill condition is essential and non-negotiable (Q's defended
      minimum): without it a candidate is "vibes with parent IDs," an
      association not a claim.
    - *Route:* through the existing Assessor/Falsifier funnel. If the
      funnel can't accept a candidate-pair as an input claim, that is the
      single real integration point — and it's small.
    - *Logs (only these five):* candidate relation; kill condition; funnel
      result / confidence movement if any; manual Darrell label ("would
      front door likely have found this? yes/no/unknown"); compute cost.
    - *Manual front-door comparison is correct for v0*, not a shortcut —
      automating "would the front door have found this?" is its own
      research project and must not be built before the experiment earns
      it. Caveat: Darrell is not a neutral judge of his own system's
      novelty (mild rapport bias, same shape flagged for Q) — when
      genuinely unsure, err toward "front door would have found it," so
      the thumb pushes against the system, not for it.
    - *Kill condition:* define the test window IN ADVANCE and honor it.
      If, over that pre-defined window, v0 produces zero non-redundant
      confidence changes, shelve/delete the script and move the
      hypothesis toward failed or dormant. It must fail cheaply — the
      cost of being wrong is a deleted script, not a rearchitected ledger.

  *Carry-forward safety tripwires — the safety analysis RESTARTS if anyone
  proposes:* learning from survival rate, learning from confidence-change
  reward, unprompted surfacing, Falsifier bypass, action from idle output,
  schema migration before measured need, or new assessors hidden as ledger
  fields. **Core lesson from the schema disagreement (Claude vs. the
  proposed 30-field v0, which Q conceded): a field that needs a verdict to
  populate is not a field — it is an assessor in disguise.** Do not add
  ledger fields until the experiment produces a failure or ambiguity that
  genuinely cannot be handled without that field.

  *Deferred mature-version concerns (real, but NOT earned until v0 shows
  the mechanism does anything useful):* consequence estimate, uncertainty
  reason, channel-independence score, downstream-reuse count, distribution-
  drift auditing, crowd-out tracking, automatic non-redundancy detection.

  *Compression:* A dream proposes. The Falsifier disposes. The ledger
  remembers. The generator does not learn pride. **(Footnote: that last
  line is currently true *by construction* — the v0 generator can't learn
  pride because it can't learn anything. If learning is ever added, the
  line stops being free and becomes something that must be actively
  engineered and audited for. True by construction now; true only by
  vigilance later.)**
