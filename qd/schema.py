from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import datetime, timezone

import uuid
from pydantic import BaseModel, Field, model_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TruthSign(int, Enum):
    SUPPORTED = 1
    UNCERTAIN = 0
    REFUTED = -1


class EpistemicReason(str, Enum):
    SUPPORTED  = "supported"
    UNCERTAIN  = "uncertain"   # knowledge gap — not enough evidence either way
    CONTESTED  = "contested"   # credible sources actively disagree
    REFUTED    = "refuted"


class EvidenceSource(str, Enum):
    EXTERNAL     = "external"      # verifiable, citable
    MODEL_MEMORY = "model_memory"  # LLM training data — not valid evidence


class Evidence(BaseModel):
    id:             str            = Field(default_factory=lambda: str(uuid.uuid4()))
    content:        str
    source_url:     Optional[str]  = None
    source_type:    EvidenceSource
    supports_claim: bool
    confidence:     float          = Field(ge=0.0, le=1.0, default=0.5)
    source_tier:    Optional[int]  = None   # 1=authoritative .. 4=social/low-trust; None=not classified


class Claim(BaseModel):
    id:           str             = Field(default_factory=lambda: str(uuid.uuid4()))
    text:         str
    submitted_at: datetime        = Field(default_factory=_utcnow)
    confidence:   float           = Field(ge=0.0, le=1.0, default=0.5)


class AssessmentMessage(BaseModel):
    """Mid-loop message from assessor. Confidence is required."""
    agent:           str
    claim_id:        str
    content:         str
    proposed_sign:   TruthSign
    proposed_reason: EpistemicReason
    confidence:      float          = Field(ge=0.0, le=1.0)
    evidence:        list[Evidence] = Field(default_factory=list)
    created_at:      datetime       = Field(default_factory=_utcnow)


class KernelVerdict(BaseModel):
    """
    Final output of the QD kernel.

    The triple — (sign, reason, confidence) — not sign alone.
    Sign alone collapses UNCERTAIN and CONTESTED into identical zeros.
    They are not the same epistemic state. Both must survive the boundary.
    """
    claim_id:           str
    sign:               TruthSign
    reason:             EpistemicReason
    confidence:         float          = Field(ge=0.0, le=1.0)
    evidence:           list[Evidence] = Field(default_factory=list)
    falsifier_approved: bool           = False
    falsifier_notes:    Optional[str]  = None
    policy_violated:    bool           = False
    run_id:             Optional[str]  = None
    created_at:         datetime       = Field(default_factory=_utcnow)

    @model_validator(mode='after')
    def reason_must_match_sign(self) -> KernelVerdict:
        if self.sign == TruthSign.SUPPORTED and self.reason != EpistemicReason.SUPPORTED:
            raise ValueError(f"Sign +1 requires reason=SUPPORTED, got {self.reason.value!r}")
        if self.sign == TruthSign.REFUTED and self.reason != EpistemicReason.REFUTED:
            raise ValueError(f"Sign -1 requires reason=REFUTED, got {self.reason.value!r}")
        if self.sign == TruthSign.UNCERTAIN and self.reason not in (
            EpistemicReason.UNCERTAIN, EpistemicReason.CONTESTED
        ):
            raise ValueError(
                f"Sign 0 requires reason=UNCERTAIN or CONTESTED, got {self.reason.value!r}"
            )
        return self

    def display(self) -> str:
        sign_label = {1: "+1 SUPPORTED", 0: "0  UNCERTAIN", -1: "-1 REFUTED"}[self.sign.value]
        status     = "✓ FALSIFIER APPROVED" if self.falsifier_approved else "✗ FALSIFIER REJECTED"
        return (
            f"\n{'='*60}\n"
            f"VERDICT:    {sign_label}\n"
            f"REASON:     {self.reason.value.upper()}\n"
            f"CONFIDENCE: {self.confidence:.2f}\n"
            f"STATUS:     {status}\n"
            f"NOTES:      {self.falsifier_notes or 'none'}\n"
            f"EVIDENCE:   {len(self.evidence)} item(s)\n"
            f"{'='*60}\n"
        )
