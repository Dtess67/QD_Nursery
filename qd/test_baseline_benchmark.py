from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.baseline_v1 import (
    BENCHMARK_ID,
    FixedRetriever,
    duplicate_family_variants,
    load_live_cases,
    ordered_shuffle_variants,
    summarize_records,
    summary_markdown,
    verdict_payload,
)
from qd import (
    EpistemicReason,
    Evidence,
    EvidenceSource,
    KernelVerdict,
    TruthSign,
)


def _item(url: str = "https://example.test/source") -> Evidence:
    return Evidence(
        content="Controlled evidence excerpt.",
        source_url=url,
        source_type=EvidenceSource.EXTERNAL,
        source_endorses_claim=True,
        confidence=0.8,
        source_tier=1,
    )


def test_live_case_manifest_is_valid_and_unique(tmp_path: Path):
    path = tmp_path / "cases.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": "one",
                    "dimension": "simple_supported_fact",
                    "claim": "Water contains hydrogen.",
                    "submitted_confidence": 0.8,
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = load_live_cases(path)

    assert cases[0]["id"] == "one"


def test_live_case_manifest_rejects_duplicate_ids(tmp_path: Path):
    case = {
        "id": "duplicate",
        "dimension": "test",
        "claim": "A claim.",
        "submitted_confidence": 0.5,
    }
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([case, case]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate case id"):
        load_live_cases(path)


def test_fixed_retriever_returns_deep_copies():
    original = _item()
    retriever = FixedRetriever((original,))

    first, _ = retriever.fetch("claim")
    second, _ = retriever.fetch("claim")
    first[0].source_endorses_claim = False

    assert original.source_endorses_claim is True
    assert second[0].source_endorses_claim is True


def test_controlled_variants_cover_duplicate_and_all_shuffle_orders():
    duplicate_variants = duplicate_family_variants()
    shuffle_variants = ordered_shuffle_variants()

    assert [len(case["evidence"]) for case in duplicate_variants] == [1, 3]
    assert len(shuffle_variants) == 6
    assert len({tuple(case["order_urls"]) for case in shuffle_variants}) == 6


def test_verdict_payload_hashes_evidence_urls_independent_of_order():
    one = _item("https://example.test/a")
    two = _item("https://example.test/b")

    def make_verdict(evidence):
        return KernelVerdict(
            claim_id="claim",
            run_id="run",
            sign=TruthSign.SUPPORTED,
            reason=EpistemicReason.SUPPORTED,
            confidence=0.7,
            evidence=evidence,
            falsifier_approved=True,
        )

    left = verdict_payload(make_verdict([one, two]))
    right = verdict_payload(make_verdict([two, one]))

    assert left["evidence_url_hash"] == right["evidence_url_hash"]


def test_summary_preserves_variance_and_errors():
    records = [
        {
            "case_id": "case-a",
            "lane": "live",
            "dimension": "simple",
            "pair_id": None,
            "status": "completed",
            "verdict": {
                "sign": 1,
                "reason": "supported",
                "confidence": 0.8,
                "falsifier_approved": True,
                "evidence_url_hash": "set-a",
            },
        },
        {
            "case_id": "case-a",
            "lane": "live",
            "dimension": "simple",
            "pair_id": None,
            "status": "completed",
            "verdict": {
                "sign": 0,
                "reason": "uncertain",
                "confidence": 0.4,
                "falsifier_approved": False,
                "evidence_url_hash": "set-b",
            },
        },
        {
            "case_id": "case-a",
            "lane": "live",
            "dimension": "simple",
            "pair_id": None,
            "status": "error",
            "error": {"type": "KernelRuntimeError", "message": "offline"},
        },
    ]

    summary = summarize_records(records)
    case = summary["cases"]["case-a"]

    assert summary["benchmark_id"] == BENCHMARK_ID
    assert case["attempted"] == 3
    assert case["completed"] == 2
    assert case["errors"] == 1
    assert len(case["distinct_outcomes"]) == 2
    assert case["distinct_evidence_sets"] == 2
    assert "truth certification" in summary_markdown(summary)
