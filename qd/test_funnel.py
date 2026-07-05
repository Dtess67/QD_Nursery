"""
Tests for the elimination-funnel Assessor (qd/kernel.py::QDKernel._assess).

These are automated pytest tests — unlike the manual run-scripts in
qd/test_kernel.py / test_kernel.py, they inject a fake Ollama client and a
temp ledger so the funnel can be exercised deterministically with no live
model, network, or Tavily key.

Coverage:
  * the funnel genuinely narrows a candidate set across multiple evidence items
    (not a single-shot guess wearing new terminology)
  * all four outcome mappings (one→SUPPORTED/REFUTED, many→CONTESTED, none→UNCERTAIN)
  * existing kernel behavior is unaffected — symmetric Evidence Policy, ledger
    logging, and reconciliation-scar logging still work unchanged.
"""
from __future__ import annotations

import pytest

from qd import (
    QDKernel, Ledger, EventType,
    Claim, Evidence, EvidenceSource,
    TruthSign, EpistemicReason,
    EvidencePolicy, EvidencePolicyViolation,
)
from qd.kernel import _Explanation


# --------------------------------------------------------------------------- #
# Test doubles                                                                 #
# --------------------------------------------------------------------------- #

class FakeOllama:
    """Returns queued JSON dicts in call order; records every call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete_json(self, system_prompt, user_message, temperature=0.3):
        self.calls.append({"system": system_prompt, "user": user_message})
        if not self._responses:
            raise AssertionError("FakeOllama: ran out of queued responses")
        return self._responses.pop(0)

    def complete(self, *args, **kwargs):
        return ""


def make_kernel(tmp_path, responses):
    """A kernel wired to a temp ledger and a fake Ollama, no real retriever."""
    ledger = Ledger(str(tmp_path / "ledger.db"))
    kernel = QDKernel(ledger=ledger, retriever=object())  # retriever unused here
    kernel.ollama = FakeOllama(responses)
    return kernel, ledger


def ev(url, content, supports=True, tier=1):
    return Evidence(
        content=content,
        source_url=url,
        source_type=EvidenceSource.EXTERNAL,
        supports_claim=supports,
        confidence=0.8,
        source_tier=tier,
    )


def exp(hid, polarity, statement="explanation"):
    return _Explanation(id=hid, statement=statement, polarity=polarity)


# --------------------------------------------------------------------------- #
# 1. The funnel genuinely narrows across multiple evidence items               #
# --------------------------------------------------------------------------- #

def test_run_funnel_narrows_monotonically_across_evidence():
    base = [
        exp("h1", TruthSign.SUPPORTED),
        exp("h2", TruthSign.REFUTED),
        exp("h3", TruthSign.REFUTED),
        exp("h4", TruthSign.REFUTED),
    ]
    # three evidence items, each eliminating one different explanation
    eliminations = [["h2"], ["h3"], ["h4"]]

    survivors, trace = QDKernel._run_funnel(base, eliminations)

    counts = [len(stage["surviving"]) for stage in trace]
    # base + one stage per evidence item
    assert counts == [4, 3, 2, 1]
    # strictly decreasing → real narrowing, not a single-shot guess
    assert all(counts[i] > counts[i + 1] for i in range(len(counts) - 1))
    assert [h.id for h in survivors] == ["h1"]
    # trace attributes each elimination to the evidence item that caused it
    assert trace[1]["eliminated"] == ["h2"]
    assert trace[2]["eliminated"] == ["h3"]
    assert trace[3]["eliminated"] == ["h4"]


def test_run_funnel_ignores_unknown_and_already_eliminated_ids():
    base = [exp("h1", TruthSign.SUPPORTED), exp("h2", TruthSign.REFUTED)]
    # 1st evidence eliminates h2 plus a bogus id; 2nd re-lists the dead h2
    survivors, trace = QDKernel._run_funnel(base, [["h2", "does-not-exist"], ["h2"]])

    assert [h.id for h in survivors] == ["h1"]
    assert trace[1]["eliminated"] == ["h2"]   # unknown id dropped
    assert trace[2]["eliminated"] == []       # already-dead id not re-counted


def test_elimination_calls_see_only_surviving_candidates(tmp_path):
    """Regression for bug #1: each elimination call must be shown ONLY the
    candidates still alive at that point, never the full original base.

    This inspects the candidate set passed *into* every elimination call — not
    the final survivor count — because a stale, non-narrowing candidate list
    produces the right end state in some cases while still being the bug.
    """
    # Base of 3: h1 supported, h2 refuted, h3 refuted (hypothesis call is faked).
    kernel, _ = make_kernel(tmp_path, [
        {"explanations": [
            {"statement": "true",    "polarity": "supported"},
            {"statement": "false A", "polarity": "refuted"},
            {"statement": "false B", "polarity": "refuted"},
        ]},
    ])

    # Intercept the elimination step and record the candidate ids it was handed.
    seen_candidate_ids: list[list[str]] = []
    scripted = [
        {"eliminated": ["h2"], "supports_claim": True, "note": "evidence 1 kills h2"},
        {"eliminated": [],     "supports_claim": True, "note": "evidence 2 sees fewer"},
    ]
    step = {"i": 0}

    def spy_eliminate(claim, evidence, candidates):
        seen_candidate_ids.append([h.id for h in candidates])
        result = scripted[step["i"]]
        step["i"] += 1
        return result

    kernel._eliminate_with_evidence = spy_eliminate

    kernel._assess(Claim(text="X"), [ev("http://a", "c1"), ev("http://b", "c2")], "run-prog")

    assert len(seen_candidate_ids) == 2
    # First evidence item sees the full base.
    assert seen_candidate_ids[0] == ["h1", "h2", "h3"]
    # Second evidence item must see ONLY the survivors after h2 was eliminated.
    # Under the bug (static base) this would be ["h1", "h2", "h3"] and fail.
    assert seen_candidate_ids[1] == ["h1", "h3"]
    assert "h2" not in seen_candidate_ids[1]


def test_assess_end_to_end_narrows_across_two_evidence_items(tmp_path):
    """Full _assess path: a wide base of 3 shrinks to 1 as two evidence items land."""
    responses = [
        {"explanations": [
            {"statement": "claim is true",          "polarity": "supported"},
            {"statement": "claim false, reason A",   "polarity": "refuted"},
            {"statement": "claim false, reason B",   "polarity": "refuted"},
        ]},
        {"eliminated": ["h2"], "supports_claim": True, "note": "rules out A"},
        {"eliminated": ["h3"], "supports_claim": True, "note": "rules out B"},
    ]
    kernel, ledger = make_kernel(tmp_path, responses)
    run_id = "run-narrow"

    kernel._assess(Claim(text="X"), [ev("http://a", "c1"), ev("http://b", "c2")], run_id)

    # 1 hypothesis call + 1 elimination call per evidence item = 3 total.
    assert len(kernel.ollama.calls) == 3

    events = ledger.get_run(run_id)
    ao = [e for e in events if e["event_type"] == "ASSESSOR_OUTPUT"][-1]
    trace = ao["payload"]["funnel_trace"]
    counts = [len(stage["surviving"]) for stage in trace]
    assert counts == [3, 2, 1]                     # narrowing is recorded in the ledger
    assert ao["payload"]["explanations_initial"] == 3
    assert ao["payload"]["explanations_surviving"] == 1


# --------------------------------------------------------------------------- #
# 2. All four outcome mappings                                                 #
# --------------------------------------------------------------------------- #

def test_outcome_one_survivor_supported():
    out = QDKernel._funnel_outcome([exp("h1", TruthSign.SUPPORTED)])
    assert out == (TruthSign.SUPPORTED, EpistemicReason.SUPPORTED)


def test_outcome_one_survivor_refuted():
    out = QDKernel._funnel_outcome([exp("h1", TruthSign.REFUTED)])
    assert out == (TruthSign.REFUTED, EpistemicReason.REFUTED)


def test_outcome_multiple_survivors_contested():
    out = QDKernel._funnel_outcome([
        exp("h1", TruthSign.SUPPORTED),
        exp("h2", TruthSign.REFUTED),
    ])
    assert out == (TruthSign.UNCERTAIN, EpistemicReason.CONTESTED)


def test_outcome_no_survivors_uncertain():
    out = QDKernel._funnel_outcome([])
    assert out == (TruthSign.UNCERTAIN, EpistemicReason.UNCERTAIN)


@pytest.mark.parametrize(
    "responses, retrieved, expected_sign, expected_reason",
    [
        # one survivor, supported
        (
            [
                {"explanations": [
                    {"statement": "true", "polarity": "supported"},
                    {"statement": "false", "polarity": "refuted"},
                ]},
                {"eliminated": ["h2"], "supports_claim": True, "note": "n"},
            ],
            [("http://a", "c1")],
            TruthSign.SUPPORTED, EpistemicReason.SUPPORTED,
        ),
        # one survivor, refuted
        (
            [
                {"explanations": [
                    {"statement": "true", "polarity": "supported"},
                    {"statement": "false", "polarity": "refuted"},
                ]},
                {"eliminated": ["h1"], "supports_claim": False, "note": "n"},
            ],
            [("http://a", "c1")],
            TruthSign.REFUTED, EpistemicReason.REFUTED,
        ),
        # multiple survivors → contested
        (
            [
                {"explanations": [
                    {"statement": "true", "polarity": "supported"},
                    {"statement": "false", "polarity": "refuted"},
                ]},
                {"eliminated": [], "supports_claim": True, "note": "n"},
                {"eliminated": [], "supports_claim": False, "note": "n"},
            ],
            [("http://a", "c1"), ("http://b", "c2")],
            TruthSign.UNCERTAIN, EpistemicReason.CONTESTED,
        ),
        # none survive → uncertain
        (
            [
                {"explanations": [
                    {"statement": "true", "polarity": "supported"},
                    {"statement": "false", "polarity": "refuted"},
                ]},
                {"eliminated": ["h1", "h2"], "supports_claim": False, "note": "n"},
            ],
            [("http://a", "c1")],
            TruthSign.UNCERTAIN, EpistemicReason.UNCERTAIN,
        ),
    ],
    ids=["supported", "refuted", "contested", "uncertain"],
)
def test_assess_outcome_mappings_end_to_end(
    tmp_path, responses, retrieved, expected_sign, expected_reason
):
    kernel, _ = make_kernel(tmp_path, responses)
    evidence = [ev(url, content) for url, content in retrieved]

    a = kernel._assess(Claim(text="X"), evidence, "run-map")

    assert a.proposed_sign == expected_sign
    assert a.proposed_reason == expected_reason
    assert 0.0 <= a.confidence <= 1.0
    assert len(a.evidence) == len(retrieved)


def test_assess_evidence_labels_follow_elimination_calls(tmp_path):
    """The per-evidence supports_claim flag flows from the elimination step."""
    responses = [
        {"explanations": [
            {"statement": "true", "polarity": "supported"},
            {"statement": "false", "polarity": "refuted"},
        ]},
        {"eliminated": ["h2"], "supports_claim": True,  "note": "n"},
        {"eliminated": [],     "supports_claim": False, "note": "n"},
    ]
    kernel, _ = make_kernel(tmp_path, responses)
    a = kernel._assess(Claim(text="X"), [ev("http://a", "c1"), ev("http://b", "c2")], "r")

    assert [e.supports_claim for e in a.evidence] == [True, False]
    # evidence stays EXTERNAL with real urls preserved
    assert all(e.source_type == EvidenceSource.EXTERNAL for e in a.evidence)
    assert [e.source_url for e in a.evidence] == ["http://a", "http://b"]


# --------------------------------------------------------------------------- #
# Knowledge-gap edges                                                          #
# --------------------------------------------------------------------------- #

def test_assess_no_evidence_is_uncertain_without_calling_model(tmp_path):
    kernel, _ = make_kernel(tmp_path, [])
    a = kernel._assess(Claim(text="X"), [], "run-empty")

    assert a.proposed_sign == TruthSign.UNCERTAIN
    assert a.proposed_reason == EpistemicReason.UNCERTAIN
    assert a.evidence == []
    assert kernel.ollama.calls == []   # funnel short-circuits, no LLM burn


def test_assess_empty_hypothesis_base_is_uncertain(tmp_path):
    kernel, _ = make_kernel(tmp_path, [{"explanations": []}])
    a = kernel._assess(Claim(text="X"), [ev("http://a", "c1")], "run-nohyp")

    assert a.proposed_sign == TruthSign.UNCERTAIN
    assert a.proposed_reason == EpistemicReason.UNCERTAIN
    # only the hypothesis call happened; no elimination calls without a base
    assert len(kernel.ollama.calls) == 1


# --------------------------------------------------------------------------- #
# 3. Existing kernel behavior is unaffected                                    #
# --------------------------------------------------------------------------- #

def test_evidence_policy_symmetric_supported_requires_supporting_source():
    # SUPPORTED verdict but every item opposes the claim → violation
    evidence = [ev("http://a", "c", supports=False)]
    with pytest.raises(EvidencePolicyViolation):
        EvidencePolicy.validate_for_verdict(
            evidence, TruthSign.SUPPORTED, EpistemicReason.SUPPORTED
        )


def test_evidence_policy_symmetric_refuted_rejects_model_memory():
    # REFUTED verdict backed only by model memory → violation (v0.2 symmetry)
    memory = Evidence(
        content="I recall this is false",
        source_url=None,
        source_type=EvidenceSource.MODEL_MEMORY,
        supports_claim=False,
        confidence=0.5,
    )
    with pytest.raises(EvidencePolicyViolation):
        EvidencePolicy.validate_for_verdict(
            [memory], TruthSign.REFUTED, EpistemicReason.REFUTED
        )


def test_evidence_policy_contested_requires_both_sides():
    one_sided = [ev("http://a", "c", supports=True)]
    with pytest.raises(EvidencePolicyViolation):
        EvidencePolicy.validate_for_verdict(
            one_sided, TruthSign.UNCERTAIN, EpistemicReason.CONTESTED
        )


def test_evidence_policy_supported_passes_with_external_source():
    good = [ev("http://a", "c", supports=True)]
    # should not raise
    EvidencePolicy.validate_for_verdict(good, TruthSign.SUPPORTED, EpistemicReason.SUPPORTED)


def test_reconcile_produces_scar_on_mismatch():
    sign, reason, scar = QDKernel._reconcile(
        TruthSign.SUPPORTED, EpistemicReason.CONTESTED
    )
    assert sign == TruthSign.SUPPORTED
    assert reason == EpistemicReason.SUPPORTED           # sign takes precedence
    assert scar is not None
    assert scar["original_reason"] == "contested"
    assert scar["corrected_reason"] == "supported"


def test_reconcile_no_scar_when_consistent():
    sign, reason, scar = QDKernel._reconcile(
        TruthSign.SUPPORTED, EpistemicReason.SUPPORTED
    )
    assert (sign, reason) == (TruthSign.SUPPORTED, EpistemicReason.SUPPORTED)
    assert scar is None


def test_ledger_records_reconcile_scar(tmp_path):
    ledger = Ledger(str(tmp_path / "l.db"))
    kernel = QDKernel(ledger=ledger, retriever=object())
    _, _, scar = QDKernel._reconcile(TruthSign.REFUTED, EpistemicReason.UNCERTAIN)
    assert scar is not None

    kernel._log("run-scar", "claim-scar", EventType.RECONCILE_SCAR, scar)
    events = ledger.get_run("run-scar")
    assert any(e["event_type"] == "RECONCILE_SCAR" for e in events)


def test_assess_logs_assessor_output_to_ledger(tmp_path):
    responses = [
        {"explanations": [
            {"statement": "true", "polarity": "supported"},
            {"statement": "false", "polarity": "refuted"},
        ]},
        {"eliminated": ["h2"], "supports_claim": True, "note": "n"},
    ]
    kernel, ledger = make_kernel(tmp_path, responses)
    kernel._assess(Claim(text="X"), [ev("http://a", "c1")], "run-log")

    events = ledger.get_run("run-log")
    assessor_events = [e for e in events if e["event_type"] == "ASSESSOR_OUTPUT"]
    assert assessor_events, "expected an ASSESSOR_OUTPUT ledger event"
    payload = assessor_events[-1]["payload"]
    assert payload["sign"] == TruthSign.SUPPORTED.value
    assert payload["reason"] == EpistemicReason.SUPPORTED.value
    assert "funnel_trace" in payload
