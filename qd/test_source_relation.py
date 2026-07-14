"""
Focused tests for the four-state source-to-claim relation and its clean-room
classifier (qd/kernel.py::QDKernel._classify_source_relation / _read_relation).

The relation — SUPPORTS / REFUTES / NEUTRAL / UNCLEAR — describes what ONE
source says about ONE claim. It never decides the final truth verdict.

Coverage:
  * all four relations flow from the classifier into Evidence.source_relation
  * strict token read: trimmed, case-normalized enum values only; booleans,
    numbers, synonyms, and approximate strings → UNCLEAR + scar
  * missing and unparsable model output → UNCLEAR + scar, never a stance
  * clean-room boundary is structural: the classifier call carries only the
    claim text and the single evidence item's content, and runs before any
    funnel state exists
  * scenario semantics: quoted claims, rumor discussion, satire (both kinds),
    and explicit factual denial
  * Evidence Policy: NEUTRAL and UNCLEAR satisfy neither side
  * relation labels do not move the funnel verdict
  * every classification is ledgered (ASSESSOR_OUTPUT stage=source_relation)
  * the retired Boolean field cannot be smuggled back in
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from qd import (
    QDKernel, Ledger,
    Claim, Evidence, EvidenceSource, SourceRelation,
    TruthSign, EpistemicReason,
    EvidencePolicy, EvidencePolicyViolation,
    ModelResponseError, ModelUnavailableError,
)
from qd.kernel import _RELATION_PROMPT, _HYPOTHESIS_PROMPT


# --------------------------------------------------------------------------- #
# Test doubles                                                                 #
# --------------------------------------------------------------------------- #

class FakeOllama:
    """Returns queued JSON dicts in call order; records every call.

    A queued item that is an Exception instance is raised instead of returned,
    so classifier failure paths can be scripted per call.
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete_json(self, system_prompt, user_message, temperature=0.3):
        self.calls.append({"system": system_prompt, "user": user_message})
        if not self._responses:
            raise AssertionError("FakeOllama: ran out of queued responses")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def complete(self, *args, **kwargs):
        return ""


def make_kernel(tmp_path, responses):
    ledger = Ledger(str(tmp_path / "ledger.db"))
    kernel = QDKernel(ledger=ledger, retriever=object())  # retriever unused here
    kernel.ollama = FakeOllama(responses)
    return kernel, ledger


def ev(url, content, relation=SourceRelation.UNCLEAR, tier=1):
    """Retrieved-item stand-in: pre-classification evidence, honest UNCLEAR."""
    return Evidence(
        content=content,
        source_url=url,
        source_type=EvidenceSource.EXTERNAL,
        source_relation=relation,
        confidence=0.8,
        source_tier=tier,
    )


def rel(token, note="n"):
    return {"source_relation": token, "note": note}


HYPOTHESIS = {"explanations": [
    {"statement": "the claim is a documented fact", "polarity": "supported"},
    {"statement": "the claim is a debunked rumor",  "polarity": "refuted"},
]}

NO_ELIMINATION = {"eliminated": [], "note": "n"}


# --------------------------------------------------------------------------- #
# 1. All four relations flow into Evidence                                     #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("token, expected", [
    ("supports", SourceRelation.SUPPORTS),
    ("refutes",  SourceRelation.REFUTES),
    ("neutral",  SourceRelation.NEUTRAL),
    ("unclear",  SourceRelation.UNCLEAR),
])
def test_each_relation_flows_into_evidence(tmp_path, token, expected):
    kernel, ledger = make_kernel(tmp_path, [rel(token), HYPOTHESIS, NO_ELIMINATION])
    a = kernel._assess(Claim(text="X"), [ev("http://a", "c1")], f"run-{token}")

    assert a.evidence[0].source_relation is expected
    # A well-formed label is a clean classification — no scar.
    events = ledger.get_run(f"run-{token}")
    assert not [e for e in events if e["event_type"] == "EVIDENCE_LABEL_SCAR"]


@pytest.mark.parametrize("token, expected", [
    (" SUPPORTS ", SourceRelation.SUPPORTS),
    ("Refutes",    SourceRelation.REFUTES),
    ("NEUTRAL",    SourceRelation.NEUTRAL),
    ("  unclear\n", SourceRelation.UNCLEAR),
])
def test_read_relation_trims_whitespace_and_normalizes_case(token, expected):
    assert QDKernel._read_relation({"source_relation": token}) == (expected, False)


# --------------------------------------------------------------------------- #
# 2. Malformed / missing / unparsable output → UNCLEAR + scar                  #
# --------------------------------------------------------------------------- #

def test_unparsable_classifier_output_becomes_unclear_with_scar(tmp_path):
    """ModelResponseError from the classifier call is a classification
    failure, not a kernel failure: UNCLEAR + scar, and the funnel continues."""
    responses = [
        ModelResponseError("Model returned invalid JSON"),
        HYPOTHESIS,
        NO_ELIMINATION,
    ]
    kernel, ledger = make_kernel(tmp_path, responses)
    a = kernel._assess(Claim(text="X"), [ev("http://a", "c1")], "run-badjson")

    assert a.evidence[0].source_relation is SourceRelation.UNCLEAR
    events = ledger.get_run("run-badjson")
    scars = [e for e in events if e["event_type"] == "EVIDENCE_LABEL_SCAR"]
    assert len(scars) == 1
    assert scars[0]["payload"]["defaulted_to"] == "unclear"
    assert "ModelResponseError" in scars[0]["payload"]["raw_label"]
    # The funnel still ran to a verdict.
    assert a.proposed_sign in (TruthSign.SUPPORTED, TruthSign.REFUTED, TruthSign.UNCERTAIN)


def test_model_unavailable_during_classification_propagates(tmp_path):
    # Infrastructure failure is not a classification outcome.
    kernel, _ = make_kernel(tmp_path, [ModelUnavailableError("Ollama not reachable")])
    with pytest.raises(ModelUnavailableError):
        kernel._assess(Claim(text="X"), [ev("http://a", "c1")], "run-down")


def test_only_the_malformed_item_gets_a_scar(tmp_path):
    responses = [
        rel("supports"),
        {"source_relation": "kinda true", "note": "garbage token"},
        HYPOTHESIS,
        NO_ELIMINATION, NO_ELIMINATION,
    ]
    kernel, ledger = make_kernel(tmp_path, responses)
    a = kernel._assess(
        Claim(text="X"), [ev("http://a", "c1"), ev("http://b", "c2")], "run-mixed"
    )

    assert [e.source_relation for e in a.evidence] == [
        SourceRelation.SUPPORTS, SourceRelation.UNCLEAR,
    ]
    scars = [
        e for e in ledger.get_run("run-mixed")
        if e["event_type"] == "EVIDENCE_LABEL_SCAR"
    ]
    assert len(scars) == 1
    assert scars[0]["payload"]["source_url"] == "http://b"


# --------------------------------------------------------------------------- #
# 3. The clean room is structural                                              #
# --------------------------------------------------------------------------- #

def test_classifier_calls_carry_only_claim_and_single_source_content(tmp_path):
    responses = [
        rel("neutral"), rel("neutral"),
        HYPOTHESIS,
        NO_ELIMINATION, NO_ELIMINATION,
    ]
    kernel, _ = make_kernel(tmp_path, responses)
    items = [
        ev("http://secret-url-a", "unique-content-alpha"),
        ev("http://secret-url-b", "unique-content-beta"),
    ]
    kernel._assess(Claim(text="the-claim-text"), items, "run-cleanroom")

    relation_calls = [c for c in kernel.ollama.calls if c["system"] == _RELATION_PROMPT]
    assert len(relation_calls) == 2

    for call, own, other in (
        (relation_calls[0], "unique-content-alpha", "unique-content-beta"),
        (relation_calls[1], "unique-content-beta", "unique-content-alpha"),
    ):
        # Only the claim and THIS item's content…
        assert "the-claim-text" in call["user"]
        assert own in call["user"]
        # …never the other source, any URL, tier, or confidence.
        assert other not in call["user"]
        assert "http://" not in call["user"]
        assert "tier" not in call["user"].lower()
        assert "confidence" not in call["user"].lower()
        # No hypothesis statements or prior labels either.
        assert "documented fact" not in call["user"]
        assert "debunked rumor" not in call["user"]


def test_classification_happens_before_any_funnel_state_exists(tmp_path):
    """Both relation calls precede the hypothesis call — the clean-room
    boundary is enforced by call order, not just prompt wording."""
    responses = [
        rel("supports"), rel("refutes"),
        HYPOTHESIS,
        NO_ELIMINATION, NO_ELIMINATION,
    ]
    kernel, _ = make_kernel(tmp_path, responses)
    kernel._assess(Claim(text="X"), [ev("http://a", "c1"), ev("http://b", "c2")], "r")

    systems = [c["system"] for c in kernel.ollama.calls]
    assert systems[0] == _RELATION_PROMPT
    assert systems[1] == _RELATION_PROMPT
    assert systems[2] == _HYPOTHESIS_PROMPT


# --------------------------------------------------------------------------- #
# 4. Scenario semantics (quotation, rumor, satire, denial)                     #
# --------------------------------------------------------------------------- #
#
# Deterministic tests can't certify live label quality (that's the
# four_state_clean_room_relation_v1 benchmark gate). What they lock down is:
# the prompt instructs the correct mapping, and the pipeline stores whatever
# stance the classifier returns without distortion.

@pytest.mark.parametrize("scenario, token, expected", [
    ("quotes the claim without endorsing it",          "neutral", SourceRelation.NEUTRAL),
    ("reports the claim as a circulating rumor",       "neutral", SourceRelation.NEUTRAL),
    ("satire that does not clearly reject the claim",  "neutral", SourceRelation.NEUTRAL),
    ("satire that clearly communicates the claim is false",
                                                       "refutes", SourceRelation.REFUTES),
    ("explicit factual denial / fact-check as false",  "refutes", SourceRelation.REFUTES),
    ("directly asserts the claim is true",             "supports", SourceRelation.SUPPORTS),
], ids=["quotation", "rumor", "satire-ambiguous", "satire-rejecting",
        "explicit-denial", "direct-assertion"])
def test_scenario_stances_are_stored_undistorted(tmp_path, scenario, token, expected):
    kernel, _ = make_kernel(tmp_path, [
        rel(token, scenario), HYPOTHESIS, NO_ELIMINATION,
    ])
    a = kernel._assess(Claim(text="X"), [ev("http://a", scenario)], "run-scenario")
    assert a.evidence[0].source_relation is expected


def test_relation_prompt_encodes_the_ratified_scenario_rules():
    p = _RELATION_PROMPT
    # Quotation / rumor / attribution without a side → neutral.
    assert "quoting someone else making the claim without endorsing it" in p
    assert "rumor" in p
    assert "attributing the claim to others" in p
    # Satire is neutral unless it clearly communicates rejection.
    assert 'Satire is "neutral" unless it clearly communicates that the' in p
    # Denial / correction / fact-check → refutes.
    assert "denies, corrects, or fact-checks" in p
    # Stance, not verdict; and never guess a stance.
    assert "NOT deciding whether the claim is actually true" in p
    assert 'Never guess "supports"' in p


# --------------------------------------------------------------------------- #
# 5. Evidence Policy: NEUTRAL and UNCLEAR satisfy neither side                 #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("relation", [SourceRelation.NEUTRAL, SourceRelation.UNCLEAR])
def test_supported_verdict_not_satisfied_by_neutral_or_unclear(relation):
    with pytest.raises(EvidencePolicyViolation):
        EvidencePolicy.validate_for_verdict(
            [ev("http://a", "c", relation=relation)],
            TruthSign.SUPPORTED, EpistemicReason.SUPPORTED,
        )


@pytest.mark.parametrize("relation", [SourceRelation.NEUTRAL, SourceRelation.UNCLEAR])
def test_refuted_verdict_not_satisfied_by_neutral_or_unclear(relation):
    # The old Boolean's information loss: satire/quotation/malformed all
    # collapsed to False and counted as refuting evidence. Locked out here.
    with pytest.raises(EvidencePolicyViolation):
        EvidencePolicy.validate_for_verdict(
            [ev("http://a", "c", relation=relation)],
            TruthSign.REFUTED, EpistemicReason.REFUTED,
        )


def test_contested_needs_explicit_supports_and_refutes():
    supporting = ev("http://a", "c", relation=SourceRelation.SUPPORTS)
    neutral    = ev("http://b", "c", relation=SourceRelation.NEUTRAL)
    refuting   = ev("http://c", "c", relation=SourceRelation.REFUTES)

    # SUPPORTS + NEUTRAL is not a contest.
    with pytest.raises(EvidencePolicyViolation):
        EvidencePolicy.validate_for_verdict(
            [supporting, neutral], TruthSign.UNCERTAIN, EpistemicReason.CONTESTED
        )
    # SUPPORTS + REFUTES is. (Should not raise.)
    EvidencePolicy.validate_for_verdict(
        [supporting, refuting], TruthSign.UNCERTAIN, EpistemicReason.CONTESTED
    )


def test_refuted_verdict_satisfied_by_explicit_refutes():
    # Should not raise.
    EvidencePolicy.validate_for_verdict(
        [ev("http://a", "c", relation=SourceRelation.REFUTES)],
        TruthSign.REFUTED, EpistemicReason.REFUTED,
    )


# --------------------------------------------------------------------------- #
# 6. The relation never decides the verdict                                    #
# --------------------------------------------------------------------------- #

def test_relation_labels_do_not_move_the_funnel_verdict(tmp_path):
    """Identical eliminations with opposite relation labels → identical
    (sign, reason, confidence). The label describes sources; the funnel's
    survivor polarity authors the proposed verdict."""
    elimination = {"eliminated": ["h2"], "note": "kills the refuted branch"}

    outcomes = []
    for token in ("supports", "neutral"):
        kernel, _ = make_kernel(tmp_path, [rel(token), HYPOTHESIS, elimination])
        a = kernel._assess(Claim(text="X"), [ev("http://a", "c1")], f"run-{token}")
        outcomes.append((a.proposed_sign, a.proposed_reason, a.confidence))

    assert outcomes[0] == outcomes[1]
    assert outcomes[0][0] == TruthSign.SUPPORTED  # single supported survivor


# --------------------------------------------------------------------------- #
# 7. Traceability: every classification is ledgered                            #
# --------------------------------------------------------------------------- #

def test_every_classification_is_ledgered_with_url_relation_and_note(tmp_path):
    responses = [
        rel("supports", "asserts it outright"),
        {"note": "label missing"},                      # malformed
        HYPOTHESIS,
        NO_ELIMINATION, NO_ELIMINATION,
    ]
    kernel, ledger = make_kernel(tmp_path, responses)
    kernel._assess(
        Claim(text="X"), [ev("http://a", "c1"), ev("http://b", "c2")], "run-ledger"
    )

    events = ledger.get_run("run-ledger")
    relation_events = [
        e for e in events
        if e["event_type"] == "ASSESSOR_OUTPUT"
        and e["payload"].get("stage") == "source_relation"
    ]
    assert len(relation_events) == 2

    first, second = (e["payload"] for e in relation_events)
    assert first == {
        "stage": "source_relation",
        "source_url": "http://a",
        "relation": "supports",
        "note": "asserts it outright",
        "malformed": False,
    }
    assert second["source_url"] == "http://b"
    assert second["relation"] == "unclear"
    assert second["malformed"] is True


# --------------------------------------------------------------------------- #
# 8. No Boolean back-compat                                                    #
# --------------------------------------------------------------------------- #

def test_retired_boolean_field_is_a_hard_error():
    with pytest.raises(ValidationError):
        Evidence(
            content="c",
            source_url="http://a",
            source_type=EvidenceSource.EXTERNAL,
            source_endorses_claim=True,   # retired field must not be accepted
            source_relation=SourceRelation.SUPPORTS,
        )


def test_source_relation_is_required():
    with pytest.raises(ValidationError):
        Evidence(
            content="c",
            source_url="http://a",
            source_type=EvidenceSource.EXTERNAL,
        )
