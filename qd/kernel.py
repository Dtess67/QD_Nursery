from __future__ import annotations

import uuid
from typing import Optional

from .schema import (
    Claim, Evidence, EvidenceSource,
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


_ASSESSOR_PROMPT = """You are an epistemic assessor in the QD kernel.

You are given a claim and a set of retrieved evidence from external sources.
Your job: assess the claim based on the provided evidence only.
Do NOT generate new evidence. Do NOT cite sources not in the list.

For each piece of evidence, determine whether it supports or opposes the claim.

Return ONLY a JSON object with these exact fields:

{
  "assessment": "your analysis of the claim based on the evidence",
  "sign": 1 or 0 or -1,
  "reason": "supported" | "uncertain" | "contested" | "refuted",
  "confidence": 0.0 to 1.0,
  "evidence_labels": [
    {
      "source_url": "exact URL from the evidence list",
      "supports_claim": true or false,
      "note": "one sentence on why this supports or opposes"
    }
  ]
}

Verdict rules:
  sign=1,  reason="supported"  → evidence clearly supports the claim
  sign=0,  reason="uncertain"  → insufficient evidence to decide (knowledge gap)
  sign=0,  reason="contested"  → credible evidence exists on both sides
  sign=-1, reason="refuted"    → evidence clearly refutes the claim

If no relevant evidence was provided: sign=0, reason="uncertain", confidence=0.1

Return ONLY the JSON object. No preamble."""


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
    The QD epistemic kernel. v0.1.2

    Constitutional layer. Newsroom, Carto, and any future QD-powered stacks
    derive their epistemic authority from this kernel — they do not replace it.

    Flow:
      Claim → Retriever (real sources) → Assessor (reasons over sources)
      → Falsifier (adversarial review) → KernelVerdict

    The Falsifier is required at every evaluation. It cannot be bypassed.
    Every epistemic event is recorded in the flight recorder ledger.
    """

    VERSION = "0.1.3"

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
        Assess the claim by reasoning over pre-retrieved evidence.
        The assessor no longer generates evidence — it classifies and reasons.
        """
        user_message = (
            f'Claim: "{claim.text}"\n\n'
            f"Retrieved evidence ({len(retrieved)} sources):\n"
            f"{_format_evidence_for_prompt(retrieved)}\n\n"
            f"Assess the claim based on this evidence."
        )

        result = self.ollama.complete_json(
            system_prompt=_ASSESSOR_PROMPT,
            user_message=user_message,
            temperature=0.3,
        )

        # Build evidence list from retrieved + assessor's classification
        evidence_labels = {
            item.get("source_url", ""): item
            for item in result.get("evidence_labels", [])
        }

        evidence = []
        for e in retrieved:
            label = evidence_labels.get(e.source_url, {})
            evidence.append(Evidence(
                content=e.content,
                source_url=e.source_url,
                source_type=EvidenceSource.EXTERNAL,
                supports_claim=bool(label.get("supports_claim", True)),
                confidence=e.confidence,
            ))

        # Parse sign and reason
        raw_sign   = result.get("sign", 0)
        raw_reason = result.get("reason", "uncertain")

        try:
            sign = TruthSign(int(raw_sign))
        except (ValueError, TypeError):
            sign = TruthSign.UNCERTAIN

        try:
            reason = EpistemicReason(str(raw_reason).lower())
        except ValueError:
            reason = EpistemicReason.UNCERTAIN

        sign, reason, scar = self._reconcile(sign, reason)

        if scar:
            self._log(run_id, claim.id, EventType.RECONCILE_SCAR, scar)

        self._log(run_id, claim.id, EventType.ASSESSOR_OUTPUT, {
            "sign":           sign.value,
            "reason":         reason.value,
            "confidence":     max(0.0, min(1.0, float(result.get("confidence", 0.5)))),
            "evidence_count": len(evidence),
            "assessment":     str(result.get("assessment", ""))[:500],
        })

        return AssessmentMessage(
            agent="assessor",
            claim_id=claim.id,
            content=str(result.get("assessment", ""))[:1000],
            proposed_sign=sign,
            proposed_reason=reason,
            confidence=max(0.0, min(1.0, float(result.get("confidence", 0.5)))),
            evidence=evidence,
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
