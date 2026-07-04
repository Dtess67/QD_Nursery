from __future__ import annotations

from typing import Optional

from .schema import Evidence, AssessmentMessage, KernelVerdict, TruthSign, EpistemicReason
from .evidence_policy import EvidencePolicy
from .exceptions import FalsifierSkippedError, EvidencePolicyViolation, ModelResponseError
from .ollama_client import OllamaClient


_SYSTEM_PROMPT = """You are the Falsifier in the QD epistemic kernel.

Your role is STRUCTURALLY ADVERSARIAL. You cannot be skipped or overridden.

Your job:
1. Review the claim and the assessor's proposed verdict
2. ACTIVELY attempt to find reasons the verdict is WRONG
3. Check: does supporting evidence actually support the claim, or is it laundered through secondary sources?
4. Check: are sources circular? (A cites B, B cites A)
5. Check: is confidence appropriate given evidence quality?

Return ONLY a JSON object with these exact fields:
{
  "approved": true or false,
  "challenge": "your adversarial challenge — required even if you approve",
  "confidence_in_approval": 0.0 to 1.0,
  "rejection_reason": "insufficient_evidence" | "source_laundering" | "circular_sources" | "active_disagreement" | "other",
  "notes": "additional concerns"
}

Rules:
- You are not a rubber stamp
- Low-confidence approval is honest — use it
- Model memory is not evidence, yours or the assessor's
- Return ONLY the JSON object"""


class Falsifier:
    """
    Structurally adversarial gate. Required. Cannot be bypassed.

    The Falsifier has review authority over all verdicts before they exit the kernel.
    assert_was_called() is the structural guarantee — the kernel checks it at verdict time.
    """

    def __init__(self, ollama_client: OllamaClient):
        self.client      = ollama_client
        self._was_called = False

    def review(
        self,
        claim_text:       str,
        assessment:       AssessmentMessage,
        proposed_verdict: KernelVerdict,
    ) -> KernelVerdict:
        """
        Review proposed verdict. Returns final KernelVerdict.

        Evidence Policy violation  → UNCERTAIN verdict, no LLM call
        Falsifier approves         → proposed verdict (confidence possibly adjusted down)
        Falsifier rejects          → 0/UNCERTAIN or 0/CONTESTED depending on rejection_reason
        """
        self._was_called = True

        # Evidence Policy: symmetric check based on verdict direction
        try:
            EvidencePolicy.validate_for_verdict(
                assessment.evidence,
                proposed_verdict.sign,
                proposed_verdict.reason,
            )
        except EvidencePolicyViolation as e:
            return self._policy_violation_verdict(proposed_verdict, str(e))

        # Call LLM for adversarial review
        try:
            result = self.client.complete_json(
                system_prompt=_SYSTEM_PROMPT,
                user_message=self._build_prompt(claim_text, assessment, proposed_verdict),
                temperature=0.2,
            )
        except (ModelResponseError, ValueError) as e:
            # Model returned unparseable JSON — conservative: reject
            return KernelVerdict(
                claim_id=proposed_verdict.claim_id,
                sign=TruthSign.UNCERTAIN,
                reason=EpistemicReason.UNCERTAIN,
                confidence=0.0,
                evidence=proposed_verdict.evidence,
                falsifier_approved=False,
                falsifier_notes=f"Falsifier ModelResponseError: {str(e)[:200]}",
            )

        approved               = bool(result.get("approved", False))
        challenge              = str(result.get("challenge", "none"))
        confidence_in_approval = float(result.get("confidence_in_approval", 0.5))
        rejection_reason       = str(result.get("rejection_reason", "other"))
        notes                  = str(result.get("notes", ""))

        falsifier_notes = f"Challenge: {challenge} | Notes: {notes}"

        if approved:
            return KernelVerdict(
                claim_id=proposed_verdict.claim_id,
                sign=proposed_verdict.sign,
                reason=proposed_verdict.reason,
                # Falsifier's confidence acts as a ceiling on the final confidence
                confidence=min(proposed_verdict.confidence, confidence_in_approval),
                evidence=proposed_verdict.evidence,
                falsifier_approved=True,
                falsifier_notes=falsifier_notes,
            )
        else:
            # Map rejection_reason → UNCERTAIN vs CONTESTED
            reason = (
                EpistemicReason.CONTESTED
                if rejection_reason == "active_disagreement"
                else EpistemicReason.UNCERTAIN
            )
            return KernelVerdict(
                claim_id=proposed_verdict.claim_id,
                sign=TruthSign.UNCERTAIN,
                reason=reason,
                confidence=max(0.1, confidence_in_approval),
                evidence=proposed_verdict.evidence,
                falsifier_approved=False,
                falsifier_notes=f"REJECTED ({rejection_reason}): {falsifier_notes}",
            )

    def assert_was_called(self) -> None:
        """
        Structural guarantee. Called by kernel at verdict time.
        Raises FalsifierSkippedError if Falsifier was not invoked.
        No verdict exits the kernel without passing this check.
        """
        if not self._was_called:
            raise FalsifierSkippedError(
                "Falsifier gate was not invoked. "
                "Kernel integrity violation — verdict cannot be issued."
            )

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _policy_violation_verdict(proposed: KernelVerdict, reason: str) -> KernelVerdict:
        return KernelVerdict(
            claim_id=proposed.claim_id,
            sign=TruthSign.UNCERTAIN,
            reason=EpistemicReason.UNCERTAIN,
            confidence=0.0,
            evidence=proposed.evidence,
            falsifier_approved=False,
            falsifier_notes=reason,
            policy_violated=True,
        )

    @staticmethod
    def _build_prompt(
        claim_text: str,
        assessment: AssessmentMessage,
        proposed:   KernelVerdict,
    ) -> str:
        evidence_lines = "\n".join(
            f"  [{i+1}] {'SUPPORTING' if e.supports_claim else 'OPPOSING'}: "
            f"{e.content[:300]} "
            f"(source: {e.source_url or 'NONE'}, type: {e.source_type.value}, "
            f"tier: {e.source_tier or 'unclassified'})"
            for i, e in enumerate(assessment.evidence)
        ) or "  [no evidence provided]"

        return (
            f'Claim: "{claim_text}"\n\n'
            f"Assessor analysis: {assessment.content[:500]}\n"
            f"Assessor confidence: {assessment.confidence:.2f}\n\n"
            f"Proposed verdict:\n"
            f"  sign:       {proposed.sign.value} ({proposed.sign.name})\n"
            f"  reason:     {proposed.reason.value}\n"
            f"  confidence: {proposed.confidence:.2f}\n\n"
            f"Evidence ({len(assessment.evidence)} items):\n"
            f"{evidence_lines}\n\n"
            f"Challenge this. Return your JSON review."
        )
