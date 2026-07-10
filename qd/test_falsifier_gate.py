from __future__ import annotations

import pytest

from qd.falsifier import Falsifier
from qd.schema import (
    AssessmentMessage,
    Evidence,
    EvidenceSource,
    KernelVerdict,
    TruthSign,
    EpistemicReason,
)


class FakeClient:
    def __init__(self, response):
        self.response = response

    def complete_json(self, **_kwargs):
        return self.response


def supporting_evidence() -> Evidence:
    return Evidence(
        content="A primary source supports the claim.",
        source_url="https://example.gov/source",
        source_type=EvidenceSource.EXTERNAL,
        source_endorses_claim=True,
        confidence=0.9,
        source_tier=1,
    )


def assessment() -> AssessmentMessage:
    return AssessmentMessage(
        agent="assessor",
        claim_id="claim-1",
        content="The evidence supports the claim.",
        proposed_sign=TruthSign.SUPPORTED,
        proposed_reason=EpistemicReason.SUPPORTED,
        confidence=0.8,
        evidence=[supporting_evidence()],
    )


def proposed() -> KernelVerdict:
    return KernelVerdict(
        claim_id="claim-1",
        sign=TruthSign.SUPPORTED,
        reason=EpistemicReason.SUPPORTED,
        confidence=0.8,
        evidence=[supporting_evidence()],
    )


def review(response: dict) -> KernelVerdict:
    return Falsifier(FakeClient(response)).review("The claim is true.", assessment(), proposed())


def valid_response(**overrides) -> dict:
    response = {
        "approved": True,
        "challenge": "No decisive weakness found.",
        "confidence_in_decision": 0.7,
        "rejection_reason": "other",
        "notes": "",
    }
    response.update(overrides)
    return response


def test_string_false_cannot_approve_verdict():
    verdict = review(valid_response(approved="false"))

    assert verdict.falsifier_approved is False
    assert verdict.sign == TruthSign.UNCERTAIN
    assert verdict.reason == EpistemicReason.UNCERTAIN
    assert verdict.confidence == 0.0
    assert "ModelResponseError" in verdict.falsifier_notes


@pytest.mark.parametrize("bad_confidence", ["0.9", 2, -0.1, None])
def test_invalid_decision_confidence_is_conservative_rejection(bad_confidence):
    verdict = review(valid_response(confidence_in_decision=bad_confidence))

    assert verdict.falsifier_approved is False
    assert verdict.sign == TruthSign.UNCERTAIN
    assert verdict.confidence == 0.0


def test_old_confidence_field_is_rejected_instead_of_silently_reused():
    response = valid_response()
    response["confidence_in_approval"] = response.pop("confidence_in_decision")

    verdict = review(response)

    assert verdict.falsifier_approved is False
    assert verdict.confidence == 0.0
    assert "ModelResponseError" in verdict.falsifier_notes


def test_approval_confidence_remains_a_ceiling():
    verdict = review(valid_response(confidence_in_decision=0.6))

    assert verdict.falsifier_approved is True
    assert verdict.sign == TruthSign.SUPPORTED
    assert verdict.confidence == 0.6


def test_rejection_uses_confidence_in_rejection_without_floor_or_inversion():
    verdict = review(valid_response(
        approved=False,
        confidence_in_decision=0.03,
        rejection_reason="insufficient_evidence",
    ))

    assert verdict.falsifier_approved is False
    assert verdict.sign == TruthSign.UNCERTAIN
    assert verdict.reason == EpistemicReason.UNCERTAIN
    assert verdict.confidence == 0.03


def test_active_disagreement_routes_to_contested():
    verdict = review(valid_response(
        approved=False,
        confidence_in_decision=0.85,
        rejection_reason="active_disagreement",
    ))

    assert verdict.sign == TruthSign.UNCERTAIN
    assert verdict.reason == EpistemicReason.CONTESTED
    assert verdict.confidence == 0.85
