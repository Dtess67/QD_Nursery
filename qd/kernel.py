from __future__ import annotations

import uuid
from typing import Optional

from .schema import (
    Claim, Evidence, EvidenceSource,
    AssessmentMessage, KernelVerdict,
    TruthSign, EpistemicReason,
)
from .falsifier import Falsifier
from .ollama_client import OllamaClient
from .ledger import Ledger, EventType
from .exceptions import StructuralViolationError, FalsifierSkippedError, ModelUnavailableError, ModelResponseError


_ASSESSOR_PROMPT = """You are an epistemic assessor in the QD kernel.

Evaluate the claim. Return ONLY a JSON object with these exact fields:

{
  "assessment": "your analysis of the claim",
  "sign": 1 or 0 or -1,
  "reason": "supported" | "uncertain" | "contested" | "refuted",
  "confidence": 0.0 to 1.0,
  "evidence": [
    {
      "content": "what this evidence says",
      "source_url": "https://... or null",
      "source_type": "external" or "model_memory",
      "supports_claim": true or false,
      "confidence": 0.0 to 1.0
    }
  ]
}

Critical distinctions:
  sign=1  → reason must be "supported"
  sign=0  → reason must be "uncertain" OR "contested"
              "uncertain" = knowledge gap (not enough info to decide)
              "contested" = credible, authoritative sources actively disagree
              THESE ARE NOT THE SAME. Do not conflate them.
  sign=-1 → reason must be "refuted"

Evidence rules:
  "external"     → you have a real, verifiable URL — include it in source_url
  "model_memory" → you are citing training data — set source_url to null
  Be honest. If you cannot cite a real URL, use model_memory.

Return ONLY the JSON object. No preamble."""


class QDKernel:
    """
    The QD epistemic kernel. v0.1.2

    Constitutional layer. Newsroom, Carto, and any future QD-powered stacks
    derive their epistemic authority from this kernel — they do not replace it.

    One claim in. One verified verdict out.
    The Falsifier is required at every evaluation. It cannot be bypassed.
    Every epistemic event is recorded in the flight recorder ledger.
    """

    VERSION = "0.1.2"

    def __init__(
        self,
        model:  str            = "qwen2.5:32b",
        host:   str            = "http://localhost:11434",
        ledger: Optional[Ledger] = None,
    ):
        self.ollama = OllamaClient(model=model, host=host)
        self.ledger = ledger or Ledger()

    def evaluate(self, claim_text: str, submitted_confidence: float = 0.5) -> KernelVerdict:
        """
        Main kernel loop.

        1. Log claim received
        2. Assess claim via Ollama — log assessor output
        3. Build proposed verdict
        4. Falsifier review — required — log result
        5. Structural check: confirm Falsifier was not bypassed
        6. Log final verdict
        7. Return verified verdict
        """
        run_id    = str(uuid.uuid4())
        claim     = Claim(text=claim_text, confidence=submitted_confidence)
        falsifier = Falsifier(self.ollama)

        # Event 1: Claim received
        self._log(run_id, claim.id, EventType.CLAIM_RECEIVED, {
            "text":                 claim_text,
            "submitted_confidence": submitted_confidence,
        })

        try:
            # Step 1: Assess
            print(f"  [KERNEL] Assessing...")
            assessment = self._assess(claim, run_id)

            print(
                f"  [KERNEL] Assessor → "
                f"sign={assessment.proposed_sign.value}, "
                f"reason={assessment.proposed_reason.value}, "
                f"confidence={assessment.confidence:.2f}, "
                f"evidence={len(assessment.evidence)}"
            )

            # Step 2: Build proposed verdict
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

            # Step 3: Falsifier review — required
            print(f"  [KERNEL] Sending to Falsifier...")
            verdict = falsifier.review(claim.text, assessment, proposed)
            verdict = verdict.model_copy(update={"run_id": run_id})

            # Log policy event
            if verdict.policy_violated:
                self._log(run_id, claim.id, EventType.POLICY_VIOLATION, {
                    "notes": verdict.falsifier_notes,
                    "proposed_sign":   proposed.sign.value,
                    "proposed_reason": proposed.reason.value,
                })
            else:
                self._log(run_id, claim.id, EventType.POLICY_PASS, {
                    "verdict_sign":   verdict.sign.value,
                    "verdict_reason": verdict.reason.value,
                })

            # Log falsifier output
            self._log(run_id, claim.id, EventType.FALSIFIER_OUTPUT, {
                "approved":   verdict.falsifier_approved,
                "sign":       verdict.sign.value,
                "reason":     verdict.reason.value,
                "confidence": verdict.confidence,
                "notes":      verdict.falsifier_notes or "",
            })

            # Step 4: Structural guarantee
            falsifier.assert_was_called()

            status = "APPROVED" if verdict.falsifier_approved else "REJECTED"
            print(f"  [KERNEL] Falsifier → {status}")

            # Event: Verdict issued
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
            raise  # already a StructuralViolationError
        except (ModelUnavailableError, ModelResponseError) as e:
            self._log(run_id, claim.id, EventType.EMERGENCY_STOP, {
                "error": f"{type(e).__name__}: {e}",
                "severity": "runtime",
            })
            raise  # operational — let caller decide
        except StructuralViolationError:
            raise
        except Exception as e:
            self._log(run_id, claim.id, EventType.EMERGENCY_STOP, {
                "error": f"{type(e).__name__}: {e}",
                "severity": "unexpected",
            })
            raise StructuralViolationError(
                f"Unexpected kernel error — {type(e).__name__}: {e}"
            ) from e

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _assess(self, claim: Claim, run_id: str) -> AssessmentMessage:
        result = self.ollama.complete_json(
            system_prompt=_ASSESSOR_PROMPT,
            user_message=f'Evaluate this claim: "{claim.text}"',
            temperature=0.3,
        )

        evidence = []
        for e in result.get("evidence", []):
            try:
                evidence.append(Evidence(
                    content=str(e.get("content", ""))[:500],
                    source_url=e.get("source_url") or None,
                    source_type=EvidenceSource(e.get("source_type", "model_memory")),
                    supports_claim=bool(e.get("supports_claim", True)),
                    confidence=float(e.get("confidence", 0.5)),
                ))
            except Exception:
                continue

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

        # Reconcile sign/reason — sign wins if they conflict
        sign, reason, scar = self._reconcile(sign, reason)

        # Log reconciliation scar if one occurred
        if scar:
            self._log(run_id, claim.id, EventType.RECONCILE_SCAR, scar)

        # Log assessor output
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
        """
        Enforce sign/reason consistency. Sign takes precedence.
        Returns (corrected_sign, corrected_reason, scar_or_None).
        A scar is returned whenever a correction was made — that mismatch
        is epistemic information and belongs in the ledger.
        """
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
            scar = {
                "original_sign":     original[0].value,
                "original_reason":   original[1].value,
                "corrected_sign":    sign.value,
                "corrected_reason":  reason.value,
                "note": "Assessor sign/reason conflict. Sign took precedence.",
            }
            return sign, reason, scar

        return sign, reason, None

    def _log(self, run_id: str, claim_id: str, event_type: EventType, payload: dict) -> None:
        """Write to ledger. Never raises — ledger failure must not crash the kernel."""
        try:
            self.ledger.log(run_id, claim_id, event_type, payload)
        except Exception as e:
            print(f"  [LEDGER WARNING] Failed to log {event_type.value}: {e}")
