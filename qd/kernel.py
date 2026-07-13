from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from .schema import (
    Claim, Evidence, EvidenceSource, SourceRelation,
    AssessmentMessage, KernelVerdict,
    TruthSign, EpistemicReason,
)
from .falsifier import Falsifier
from .retriever import Retriever
from .ollama_client import OllamaClient
from .ledger import Ledger, EventType
from .exceptions import (
    StructuralViolationError, FalsifierSkippedError,
    ModelUnavailableError, ModelResponseError, KernelRuntimeError,
)


_HYPOTHESIS_PROMPT = """You are the Assessor in the QD kernel, running an elimination funnel.

You are NOT guessing an answer. Before seeing any evidence, your job is to lay
out a WIDE BASE of plausible, competing explanations for whether the claim is
true or false. Cast a broad net — include explanations you personally doubt.
Later, evidence will eliminate the explanations it contradicts, and whatever
survives determines the verdict. A narrow base defeats the whole method.

Each explanation must take a side on the claim itself:
  polarity = "supported"  → this explanation, if true, means the claim is TRUE
  polarity = "refuted"    → this explanation, if true, means the claim is FALSE

Aim for 3–6 explanations spanning BOTH polarities where that is at all plausible.

Return ONLY a JSON object with this exact shape:

{
  "explanations": [
    {"statement": "a specific explanation of the claim's truth", "polarity": "supported" | "refuted"},
    ...
  ]
}

Return ONLY the JSON object. No preamble."""


_ELIMINATION_PROMPT = """You are the Assessor in the QD kernel, running an elimination funnel.

You are given the claim, ONE piece of retrieved external evidence, and the
explanations still in play. Your ONLY job for this evidence item is to decide
which explanations it CONTRADICTS — i.e. which ones this evidence rules out.

Rules:
- Eliminate an explanation ONLY when the evidence genuinely contradicts it.
- Do NOT eliminate an explanation just because the evidence is silent on it.
- Judge only against THIS evidence item. Do not import outside knowledge.
- Use the exact explanation ids given to you.

Return ONLY a JSON object with this exact shape:

{
  "eliminated": ["id", ...],   // explanation ids this evidence contradicts (may be empty)
  "note": "one sentence on what this evidence rules out and why"
}

Return ONLY the JSON object. No preamble."""


_RELATION_PROMPT = """You are the source-relation classifier in the QD kernel.

You are given a claim and the text of ONE source. Your ONLY job is to decide
what THIS SOURCE ITSELF says about THIS claim. You are describing the
source's stance — you are NOT deciding whether the claim is actually true
or false. That verdict is made elsewhere, by other means.

Use exactly one of these four labels:

  "supports" — the source itself directly asserts or concludes that the
               claim is true.

  "refutes"  — the source itself directly denies, corrects, or fact-checks
               the claim as false.

  "neutral"  — the source is relevant or discusses the topic, but takes no
               side on the claim itself. This includes:
                - quoting someone else making the claim without endorsing it,
                - reporting on the claim as a belief, rumor, theory,
                  controversy, or misinformation,
                - attributing the claim to others,
                - explaining why people believe the claim,
                - discussing the topic without asserting the claim true or false.
               Satire is "neutral" unless it clearly communicates that the
               claim is false — in that case it is "refutes".

  "unclear"  — the source text is insufficient, ambiguous, or too off-topic
               to determine its stance.

Rules:
- Judge ONLY this source's own words against this claim. No outside knowledge.
- Do NOT answer "supports" merely because the source mentions the claim,
  describes believers, or contains quoted language asserting the claim.
- When you genuinely cannot decide, answer "unclear". Never guess "supports"
  or "refutes".

Return ONLY a JSON object with this exact shape:

{
  "source_relation": "supports" | "refutes" | "neutral" | "unclear",
  "note": "one sentence on why"
}

Return ONLY the JSON object. No preamble."""


@dataclass
class _Explanation:
    """One candidate explanation in the funnel base."""
    id:        str
    statement: str
    polarity:  TruthSign   # SUPPORTED (claim true) or REFUTED (claim false)


def _format_evidence_for_prompt(evidence: list[Evidence]) -> str:
    if not evidence:
        return "  [No evidence retrieved]"
    lines = []
    for i, e in enumerate(evidence, 1):
        tier_note = f" (tier {e.source_tier})" if e.source_tier else ""
        lines.append(f"  [{i}] {e.source_url}{tier_note}\n      {e.content[:300]}")
    return "\n".join(lines)


class QDKernel:
    """
    The QD epistemic kernel. v0.1.4

    Constitutional layer. Newsroom, Carto, and any future QD-powered stacks
    derive their epistemic authority from this kernel — they do not replace it.

    Flow:
      Claim → Retriever (real sources) → Assessor (reasons over sources)
      → Falsifier (adversarial review) → KernelVerdict

    The Falsifier is required at every evaluation. It cannot be bypassed.
    Every epistemic event is recorded in the flight recorder ledger.
    """

    VERSION = "0.1.4"

    def __init__(
        self,
        model:     str             = "qwen2.5:32b",
        host:      str             = "http://localhost:11434",
        ledger:    Optional[Ledger]    = None,
        retriever: Optional[Retriever] = None,
    ):
        self.ollama    = OllamaClient(model=model, host=host)
        self.ledger    = ledger    or Ledger()
        self.retriever = retriever or Retriever()

    def evaluate(self, claim_text: str, submitted_confidence: float = 0.5) -> KernelVerdict:
        """
        Main kernel loop.

        1. Log claim received
        2. Retrieve real external evidence (Tavily)
        3. Assess claim by reasoning over retrieved evidence
        4. Build proposed verdict
        5. Falsifier review — required
        6. Structural check
        7. Log and return final verdict
        """
        run_id = str(uuid.uuid4())
        claim  = Claim(text=claim_text, confidence=submitted_confidence)
        falsifier = Falsifier(self.ollama)

        self._log(run_id, claim.id, EventType.CLAIM_RECEIVED, {
            "text":                 claim_text,
            "submitted_confidence": submitted_confidence,
        })

        try:
            # Step 1: Retrieve real sources
            print(f"  [KERNEL] Retrieving sources...")
            retrieved, filtered_out = self.retriever.fetch(claim_text)
            print(
                f"  [KERNEL] Retrieved {len(retrieved)} source(s), "
                f"filtered {len(filtered_out)} low-tier"
            )

            self._log(run_id, claim.id, EventType.ASSESSOR_OUTPUT, {
                "stage":             "retrieval",
                "sources_retrieved": len(retrieved),
                "urls":              [e.source_url for e in retrieved],
                "tiers":             [e.source_tier for e in retrieved],
            })

            for f in filtered_out:
                self._log(run_id, claim.id, EventType.SOURCE_FILTERED, f)

            # Step 2: Assess — reason over retrieved evidence
            print(f"  [KERNEL] Assessing...")
            assessment = self._assess(claim, retrieved, run_id)

            print(
                f"  [KERNEL] Assessor → "
                f"sign={assessment.proposed_sign.value}, "
                f"reason={assessment.proposed_reason.value}, "
                f"confidence={assessment.confidence:.2f}, "
                f"evidence={len(assessment.evidence)}"
            )

            # Step 3: Build proposed verdict
            proposed = KernelVerdict(
                claim_id=claim.id,
                sign=assessment.proposed_sign,
                reason=assessment.proposed_reason,
                confidence=assessment.confidence,
                evidence=assessment.evidence,
                falsifier_approved=False,
                falsifier_notes="pending falsifier review",
                run_id=run_id,
            )

            # Step 4: Falsifier review — required
            print(f"  [KERNEL] Sending to Falsifier...")
            verdict = falsifier.review(claim.text, assessment, proposed)
            verdict = verdict.model_copy(update={"run_id": run_id})

            # Log policy/falsifier events
            if verdict.policy_violated:
                self._log(run_id, claim.id, EventType.POLICY_VIOLATION, {
                    "notes":           verdict.falsifier_notes,
                    "proposed_sign":   proposed.sign.value,
                    "proposed_reason": proposed.reason.value,
                })
            else:
                self._log(run_id, claim.id, EventType.POLICY_PASS, {
                    "verdict_sign":   verdict.sign.value,
                    "verdict_reason": verdict.reason.value,
                })

            self._log(run_id, claim.id, EventType.FALSIFIER_OUTPUT, {
                "approved":   verdict.falsifier_approved,
                "sign":       verdict.sign.value,
                "reason":     verdict.reason.value,
                "confidence": verdict.confidence,
                "notes":      verdict.falsifier_notes or "",
            })

            # Step 5: Structural guarantee
            falsifier.assert_was_called()

            status = "APPROVED" if verdict.falsifier_approved else "REJECTED"
            print(f"  [KERNEL] Falsifier → {status}")

            self._log(run_id, claim.id, EventType.VERDICT_ISSUED, {
                "sign":               verdict.sign.value,
                "reason":             verdict.reason.value,
                "confidence":         verdict.confidence,
                "falsifier_approved": verdict.falsifier_approved,
                "policy_violated":    verdict.policy_violated,
            })

            return verdict

        except FalsifierSkippedError:
            self._log(run_id, claim.id, EventType.EMERGENCY_STOP, {
                "error": "FalsifierSkippedError — constitutional violation"
            })
            raise

        except (ModelUnavailableError, ModelResponseError, KernelRuntimeError) as e:
            self._log(run_id, claim.id, EventType.EMERGENCY_STOP, {
                "error":    f"{type(e).__name__}: {e}",
                "severity": "runtime",
            })
            raise

        except StructuralViolationError:
            raise

        except Exception as e:
            self._log(run_id, claim.id, EventType.EMERGENCY_STOP, {
                "error":    f"{type(e).__name__}: {e}",
                "severity": "unexpected",
            })
            raise StructuralViolationError(
                f"Unexpected kernel error — {type(e).__name__}: {e}"
            ) from e

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _assess(
        self,
        claim:     Claim,
        retrieved: list[Evidence],
        run_id:    str,
    ) -> AssessmentMessage:
        """
        Assess the claim with an elimination funnel — not a single-shot guess.

          0. Classify each source's relation to the claim in a CLEAN ROOM —
             one claim, one evidence item, no hypothesis base, no other
             sources, no prior labels. Runs before any funnel state exists,
             so the boundary is structural, not prompt wording.
          1. Generate a WIDE base of plausible, polarity-tagged explanations.
          2. Use each evidence item to eliminate the explanations it contradicts.
             Evidence narrows the candidate set; it does not vote on a pre-picked
             answer.
          3. Converge on the survivors:
               exactly one survivor  → SUPPORTED / REFUTED (per its polarity)
               more than one         → UNCERTAIN / CONTESTED (can't be separated)
               none                  → UNCERTAIN / UNCERTAIN (base wiped out)

        The assessor does not generate evidence — it reasons over the retrieved
        sources only.
        """
        # No evidence → the funnel has nothing to narrow with. Knowledge gap.
        if not retrieved:
            return self._empty_assessment(
                claim, run_id, "No evidence retrieved; funnel could not run."
            )

        # Step 0: clean-room source-relation classification, BEFORE hypothesis
        # generation or elimination. The relation label describes what each
        # source says about the claim; it never decides the verdict.
        evidence: list[Evidence] = []
        for e in retrieved:
            relation = self._classify_source_relation(claim, e, run_id)
            evidence.append(Evidence(
                content=e.content,
                source_url=e.source_url,
                source_type=EvidenceSource.EXTERNAL,
                source_relation=relation,
                confidence=e.confidence,
                source_tier=e.source_tier,
            ))

        # Step 1: wide base of competing explanations.
        base = self._generate_explanations(claim)
        if not base:
            return self._empty_assessment(
                claim, run_id, "Assessor produced no explanations; funnel could not run."
            )

        # Step 2: each evidence item eliminates the explanations it contradicts.
        # The candidate set narrows incrementally — every elimination call is
        # shown ONLY the explanations still alive at that point, never the full
        # original base. Judging fresh evidence against already-dead candidates
        # is what collapsed real claims to 0 survivors / UNCERTAIN.
        eliminations: list[list[str]] = []
        alive:        list[_Explanation] = list(base)   # survivors so far
        for e in retrieved:
            elim = self._eliminate_with_evidence(claim, e, alive)
            hit  = [str(i) for i in elim.get("eliminated", [])]
            eliminations.append(hit)
            # Narrow the live set before the NEXT evidence item sees it. Only
            # ids that are still alive can be removed (the id-safety guard).
            dead  = set(hit)
            alive = [h for h in alive if h.id not in dead]

        # Step 3: run the funnel and converge. _run_funnel replays the same
        # eliminations over the base as the single source of truth for the
        # trace; because each hit only names then-alive ids, it agrees with the
        # incremental `alive` set above.
        survivors, trace = self._run_funnel(base, eliminations)
        sign, reason     = self._funnel_outcome(survivors)
        n_eliminating    = sum(1 for stage in trace[1:] if stage["eliminated"])
        confidence       = self._funnel_confidence(
            base, survivors, sign, reason, len(retrieved), n_eliminating
        )

        # Reconcile stays in the loop as a structural guarantee. The funnel
        # produces matching sign/reason by construction, so this is normally a
        # no-op — but the scar path is preserved unchanged.
        sign, reason, scar = self._reconcile(sign, reason)
        if scar:
            self._log(run_id, claim.id, EventType.RECONCILE_SCAR, scar)

        assessment_text = self._summarize_funnel(base, survivors, trace)

        self._log(run_id, claim.id, EventType.ASSESSOR_OUTPUT, {
            "stage":                  "funnel",
            "sign":                   sign.value,
            "reason":                 reason.value,
            "confidence":             confidence,
            "evidence_count":         len(evidence),
            "explanations_initial":   len(base),
            "explanations_surviving": len(survivors),
            "funnel_trace":           trace,
            "assessment":             assessment_text[:500],
        })

        return AssessmentMessage(
            agent="assessor",
            claim_id=claim.id,
            content=assessment_text[:1000],
            proposed_sign=sign,
            proposed_reason=reason,
            confidence=confidence,
            evidence=evidence,
        )

    # ------------------------------------------------------------------ #
    # Funnel                                                               #
    # ------------------------------------------------------------------ #

    def _generate_explanations(self, claim: Claim) -> list[_Explanation]:
        """LLM step 1 — cast a wide base of polarity-tagged explanations.

        Ids (h1, h2, ...) are assigned here, kernel-side, so the elimination
        step references a stable id space the model cannot corrupt.
        """
        result = self.ollama.complete_json(
            system_prompt=_HYPOTHESIS_PROMPT,
            user_message=(
                f'Claim: "{claim.text}"\n\n'
                f"Generate the wide base of competing explanations."
            ),
            temperature=0.4,
        )

        base: list[_Explanation] = []
        for i, item in enumerate(result.get("explanations", []), 1):
            pol = str(item.get("polarity", "")).strip().lower()
            if pol == "supported":
                polarity = TruthSign.SUPPORTED
            elif pol == "refuted":
                polarity = TruthSign.REFUTED
            else:
                continue  # skip malformed / neutral entries
            base.append(_Explanation(
                id=f"h{i}",
                statement=str(item.get("statement", ""))[:300],
                polarity=polarity,
            ))
        return base

    def _eliminate_with_evidence(
        self,
        claim:    Claim,
        evidence: Evidence,
        base:     list[_Explanation],
    ) -> dict:
        """LLM step 2 — one evidence item vs. the explanation base.

        Returns the raw model dict ({"eliminated": [...], "note": str}).
        Narrowing itself is done in pure Python by _run_funnel.
        """
        candidates = "\n".join(
            f"  [{h.id}] ({h.polarity.name}) {h.statement}" for h in base
        )
        user_message = (
            f'Claim: "{claim.text}"\n\n'
            f"Explanations still in play:\n{candidates}\n\n"
            f"Evidence item:\n"
            f"  source: {evidence.source_url or 'NONE'}\n"
            f"  {evidence.content[:400]}\n\n"
            f"Which explanations does THIS evidence contradict?"
        )
        return self.ollama.complete_json(
            system_prompt=_ELIMINATION_PROMPT,
            user_message=user_message,
            temperature=0.2,
        )

    def _classify_source_relation(
        self,
        claim:  Claim,
        item:   Evidence,
        run_id: str,
    ) -> SourceRelation:
        """Clean-room classification of one source's relation to the claim.

        The model sees ONLY the claim text and this one evidence item's
        content — no source URL, tier, or confidence; no hypothesis base; no
        other sources; no prior labels; no funnel state. The July 8
        investigation (diagnostics/archive/pre_four_state/) proved that
        sharing context with the elimination step contaminates this label.

        Every classification is ledgered. Malformed, missing, ambiguous, or
        unparsable output becomes UNCLEAR — never SUPPORTS or REFUTES — and
        additionally leaves an EVIDENCE_LABEL_SCAR, so "the model returned
        garbage" never looks like a clean stance.
        """
        try:
            result = self.ollama.complete_json(
                system_prompt=_RELATION_PROMPT,
                user_message=(
                    f'Claim: "{claim.text}"\n\n'
                    f"Source text:\n{item.content}\n\n"
                    f"What is this source's relation to the claim?"
                ),
                temperature=0.2,
            )
            raw_label = result.get("source_relation") if isinstance(result, dict) else result
            note      = str(result.get("note", ""))[:300] if isinstance(result, dict) else ""
        except ModelResponseError as e:
            # Unparsable model output is a classification failure, not a
            # kernel failure. It must become UNCLEAR + scar, never a stance.
            # (ModelUnavailableError still propagates — infrastructure
            # failure is not a classification outcome.)
            result    = {}
            raw_label = f"<ModelResponseError: {str(e)[:150]}>"
            note      = ""

        relation, malformed = self._read_relation(result if isinstance(result, dict) else {})

        self._log(run_id, claim.id, EventType.ASSESSOR_OUTPUT, {
            "stage":      "source_relation",
            "source_url": item.source_url,
            "relation":   relation.value,
            "note":       note,
            "malformed":  malformed,
        })
        if malformed:
            self._log(run_id, claim.id, EventType.EVIDENCE_LABEL_SCAR, {
                "source_url":   item.source_url,
                "raw_label":    repr(raw_label)[:200],
                "defaulted_to": "unclear",
                "note": "Source-relation label missing, malformed, or not one "
                        "of supports/refutes/neutral/unclear; defaulted to UNCLEAR.",
            })
        return relation

    @staticmethod
    def _read_relation(payload: dict) -> tuple[SourceRelation, bool]:
        """Read the source-relation label from a classifier result.

        Returns (relation, malformed). Only a string token equal to one of
        the four enum values — after trimming whitespace and normalizing
        case — is accepted. Booleans, numbers, null, synonyms, and
        approximate strings are all malformed and become UNCLEAR. This is
        deliberately strict: for a truth-seeking kernel, garbage output must
        never silently become a stance for or against the claim.
        """
        raw = payload.get("source_relation")
        if isinstance(raw, str):
            token = raw.strip().lower()
            for relation in SourceRelation:
                if token == relation.value:
                    return relation, False
        return SourceRelation.UNCLEAR, True

    @staticmethod
    def _run_funnel(
        base:         list[_Explanation],
        eliminations: list[list[str]],
    ) -> tuple[list[_Explanation], list[dict]]:
        """Pure funnel mechanics: narrow the base by applying each evidence
        item's eliminations, in order.

        Returns (survivors, trace). The trace records the surviving id set
        after every evidence item — this is what makes the narrowing auditable
        and proves the funnel is not a single-shot guess.
        """
        by_id = {h.id: h for h in base}
        alive = [h.id for h in base]
        trace = [{"stage": "base", "eliminated": [], "surviving": list(alive)}]

        for idx, elim in enumerate(eliminations, 1):
            # Only ids that are real AND still alive can be eliminated.
            hit = [i for i in dict.fromkeys(elim) if i in by_id and i in alive]
            alive = [i for i in alive if i not in hit]
            trace.append({
                "stage":     f"evidence_{idx}",
                "eliminated": hit,
                "surviving":  list(alive),
            })

        survivors = [by_id[i] for i in alive]
        return survivors, trace

    @staticmethod
    def _funnel_outcome(
        survivors: list[_Explanation],
    ) -> tuple[TruthSign, EpistemicReason]:
        """Map the surviving candidate set to a (sign, reason) verdict.

        Multiple survivors are NOT automatically a contest. Two hypotheses that
        both conclude the claim is false (e.g. "round — satellite imagery" and
        "round — eclipse shadow") corroborate each other; they don't conflict.
        Polarity — the structured TruthSign already set on each _Explanation at
        generation time — is read here to tell corroboration from contest.
        """
        # Base wiped out and nothing replaced it → knowledge gap.
        if not survivors:
            return TruthSign.UNCERTAIN, EpistemicReason.UNCERTAIN

        # Single survivor → its own polarity (unchanged).
        if len(survivors) == 1:
            h = survivors[0]
            if h.polarity == TruthSign.SUPPORTED:
                return TruthSign.SUPPORTED, EpistemicReason.SUPPORTED
            return TruthSign.REFUTED, EpistemicReason.REFUTED

        # Multiple survivors — inspect polarity, do not merely count.
        # Read only the structured field; never infer from wording/tone.
        valid = {TruthSign.SUPPORTED, TruthSign.REFUTED}
        polarities = [h.polarity for h in survivors]

        # Any missing/neutral polarity → we cannot classify. Do not guess.
        if any(p not in valid for p in polarities):
            return TruthSign.UNCERTAIN, EpistemicReason.UNCERTAIN

        distinct = set(polarities)
        if len(distinct) == 1:
            # All survivors agree via independent reasoning paths → corroboration.
            shared = polarities[0]
            if shared == TruthSign.SUPPORTED:
                return TruthSign.SUPPORTED, EpistemicReason.SUPPORTED
            return TruthSign.REFUTED, EpistemicReason.REFUTED

        # Survivors genuinely disagree (both polarities present) → contest.
        return TruthSign.UNCERTAIN, EpistemicReason.CONTESTED

    @staticmethod
    def _funnel_confidence(
        base:          list[_Explanation],
        survivors:     list[_Explanation],
        sign:          TruthSign,
        reason:        EpistemicReason = EpistemicReason.UNCERTAIN,
        n_evidence:    int = 0,
        n_eliminating: int = 0,
    ) -> float:
        """Confidence reflects how decisively the funnel converged.

        Every branch scales with real evidence — none returns a bare constant:
          * single survivor → how much of the base the evidence ruled out
          * multiple survivors, agreeing → corroboration; confidence rises with
            each independent survivor that reaches the same verdict
          * multiple survivors, contested → how sharply the base was narrowed
            before ≥2 opposed candidates proved inseparable
          * multiple survivors, unclear polarity → we can't classify; low
          * zero survivors → how much of the evidence actually did the wiping;
            one item nuking the whole base is weak signal, a gradual whittle-
            down across many items is a more considered "nothing coheres".

        n_evidence    — number of evidence items processed.
        n_eliminating — number of those items that removed ≥1 candidate.
        """
        n = len(base)
        if n == 0:
            return 0.1
        eliminated_frac = (n - len(survivors)) / n
        n_survivors = len(survivors)

        # Decisive verdict (SUPPORTED / REFUTED).
        if sign in (TruthSign.SUPPORTED, TruthSign.REFUTED):
            # Single survivor out of a wide base → decisive result. (unchanged)
            if n_survivors <= 1:
                return round(min(0.95, 0.55 + 0.40 * eliminated_frac), 2)
            # Multiple survivors agreeing on one polarity → corroboration.
            # Each additional independent survivor that agrees lifts confidence,
            # capped at a reasonable ceiling below the single-survivor max.
            return round(
                min(0.90, 0.55 + 0.12 * (n_survivors - 1) + 0.08 * eliminated_frac),
                2,
            )

        # Multiple survivors that genuinely disagree → contested. The more of
        # the base eliminated while ≥2 opposed candidates remain, the sharper
        # the contest. (unchanged formula)
        if reason == EpistemicReason.CONTESTED:
            return round(min(0.60, 0.20 + 0.40 * eliminated_frac), 2)

        # Multiple survivors of unclear/neutral polarity → cannot classify. Low.
        if n_survivors > 1:
            return round(min(0.30, 0.10 + 0.20 * eliminated_frac), 2)

        # Zero survivors → base wiped out. Confidence in the UNCERTAIN verdict
        # scales with how spread-out the elimination work was across evidence.
        spread = (n_eliminating / n_evidence) if n_evidence else 0.0
        return round(min(0.40, 0.10 + 0.30 * spread), 2)

    @staticmethod
    def _summarize_funnel(
        base:      list[_Explanation],
        survivors: list[_Explanation],
        trace:     list[dict],
    ) -> str:
        surviving = "; ".join(f"[{h.id}] {h.statement}" for h in survivors) or "none"
        return (
            f"Elimination funnel: began with {len(base)} explanation(s), "
            f"{len(survivors)} survived after {len(trace) - 1} evidence item(s). "
            f"Surviving: {surviving}"
        )

    def _empty_assessment(
        self,
        claim:  Claim,
        run_id: str,
        note:   str,
    ) -> AssessmentMessage:
        """Knowledge-gap assessment when the funnel cannot run."""
        sign, reason = TruthSign.UNCERTAIN, EpistemicReason.UNCERTAIN
        self._log(run_id, claim.id, EventType.ASSESSOR_OUTPUT, {
            "stage":                  "funnel",
            "sign":                   sign.value,
            "reason":                 reason.value,
            "confidence":             0.1,
            "evidence_count":         0,
            "explanations_initial":   0,
            "explanations_surviving": 0,
            "funnel_trace":           [],
            "assessment":             note,
        })
        return AssessmentMessage(
            agent="assessor",
            claim_id=claim.id,
            content=note,
            proposed_sign=sign,
            proposed_reason=reason,
            confidence=0.1,
            evidence=[],
        )

    @staticmethod
    def _reconcile(
        sign:   TruthSign,
        reason: EpistemicReason,
    ) -> tuple[TruthSign, EpistemicReason, Optional[dict]]:
        original = (sign, reason)

        if sign == TruthSign.SUPPORTED and reason != EpistemicReason.SUPPORTED:
            reason = EpistemicReason.SUPPORTED
        elif sign == TruthSign.REFUTED and reason != EpistemicReason.REFUTED:
            reason = EpistemicReason.REFUTED
        elif sign == TruthSign.UNCERTAIN and reason not in (
            EpistemicReason.UNCERTAIN, EpistemicReason.CONTESTED
        ):
            reason = EpistemicReason.UNCERTAIN

        if (sign, reason) != original:
            return sign, reason, {
                "original_sign":    original[0].value,
                "original_reason":  original[1].value,
                "corrected_sign":   sign.value,
                "corrected_reason": reason.value,
                "note": "Assessor sign/reason conflict. Sign took precedence.",
            }

        return sign, reason, None

    def _log(self, run_id: str, claim_id: str, event_type: EventType, payload: dict) -> None:
        try:
            self.ledger.log(run_id, claim_id, event_type, payload)
        except Exception as e:
            print(f"  [LEDGER WARNING] Failed to log {event_type.value}: {e}")
