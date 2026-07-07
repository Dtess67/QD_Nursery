from __future__ import annotations

from .schema import Evidence, EvidenceSource, TruthSign, EpistemicReason
from .exceptions import EvidencePolicyViolation


class EvidencePolicy:
    """
    Evidence Policy v0.2

    Symmetric. Model memory is not valid evidence in any direction.

    Rule 1: SUPPORTED verdict  → supporting side must have external sources.
    Rule 2: REFUTED verdict    → refuting side must have external sources.
    Rule 3: CONTESTED verdict  → BOTH sides checked independently.
    Rule 4: UNCERTAIN verdict  → no external evidence required.
                                 UNCERTAIN means we don't have enough — that's honest.

    The asymmetry bug (v0.1 only checked the supporting side) meant model memory
    could refute a claim without the gate firing. Fixed here.
    """

    VERSION = "0.2"

    @staticmethod
    def validate_for_verdict(
        evidence: list[Evidence],
        sign: TruthSign,
        reason: EpistemicReason,
    ) -> None:
        """
        Symmetric policy enforcement. Routes to the correct check based on verdict.
        Raises EvidencePolicyViolation on failure.
        """
        if sign == TruthSign.SUPPORTED:
            EvidencePolicy._validate_side(evidence, source_endorses_claim=True, label="supporting")

        elif sign == TruthSign.REFUTED:
            EvidencePolicy._validate_side(evidence, source_endorses_claim=False, label="refuting")

        elif sign == TruthSign.UNCERTAIN and reason == EpistemicReason.CONTESTED:
            # Contested: credible sources actively disagree.
            # Both sides must have external sources — otherwise it's not a real contest.
            EvidencePolicy._validate_side(evidence, source_endorses_claim=True,  label="supporting")
            EvidencePolicy._validate_side(evidence, source_endorses_claim=False, label="refuting")

        # UNCERTAIN (not contested) — no external evidence required.
        # The kernel is saying "we don't know." That's not a claim. No source required.

    @staticmethod
    def validate_all(evidence: list[Evidence]) -> None:
        """
        Strictest check — no model memory anywhere.
        Used by the Falsifier: cannot invoke model memory to challenge either.
        """
        memory_items = [e for e in evidence if e.source_type == EvidenceSource.MODEL_MEMORY]
        if memory_items:
            raise EvidencePolicyViolation(
                f"[EvidencePolicy v{EvidencePolicy.VERSION}] "
                f"{len(memory_items)} item(s) sourced from model_memory. "
                "Falsifier requires external sources for all evidence."
            )

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_side(evidence: list[Evidence], source_endorses_claim: bool, label: str) -> None:
        """
        Validate one side (supporting or refuting).
        Checks: side exists, no model memory, no missing URLs.
        """
        side = [e for e in evidence if e.source_endorses_claim == source_endorses_claim]

        if not side:
            raise EvidencePolicyViolation(
                f"[EvidencePolicy v{EvidencePolicy.VERSION}] "
                f"No {label} evidence provided."
            )

        memory_items = [e for e in side if e.source_type == EvidenceSource.MODEL_MEMORY]
        if memory_items:
            raise EvidencePolicyViolation(
                f"[EvidencePolicy v{EvidencePolicy.VERSION}] "
                f"{len(memory_items)} {label} item(s) sourced from model_memory. "
                f"External verifiable sources required on the {label} side."
            )

        unsourced = [e for e in side if not e.source_url]
        if unsourced:
            raise EvidencePolicyViolation(
                f"[EvidencePolicy v{EvidencePolicy.VERSION}] "
                f"{len(unsourced)} {label} item(s) missing source_url. "
                "External sources must include a URL."
            )
