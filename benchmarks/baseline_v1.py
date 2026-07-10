from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from qd import Evidence, EvidenceSource, Ledger, QDKernel


BENCHMARK_ID = "baseline_v1"
DEFAULT_MODEL = "qwen2.5:32b"
DEFAULT_CASES_PATH = Path(__file__).with_name("baseline_cases_v1.json")
DEFAULT_RESULTS_ROOT = Path("benchmark_results") / BENCHMARK_ID


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_value(*args: str, default: str = "unknown") -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() or default
    except (OSError, subprocess.CalledProcessError):
        return default


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_live_cases(path: Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("baseline case manifest must be a non-empty JSON list")

    required = {"id", "dimension", "claim", "submitted_confidence"}
    seen: set[str] = set()
    for case in data:
        if not isinstance(case, dict):
            raise ValueError("every baseline case must be a JSON object")
        missing = required - set(case)
        if missing:
            raise ValueError(f"case missing required fields {sorted(missing)}: {case!r}")
        if case["id"] in seen:
            raise ValueError(f"duplicate case id: {case['id']}")
        seen.add(case["id"])
        confidence = float(case["submitted_confidence"])
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"submitted_confidence out of range for {case['id']}")
    return data


@dataclass(frozen=True)
class FixedRetriever:
    """Duck-typed Retriever that returns one fixed evidence order."""

    evidence: tuple[Evidence, ...]

    def fetch(self, claim_text: str) -> tuple[list[Evidence], list[dict[str, Any]]]:
        # Deep copies prevent one run from leaking model-updated labels into another.
        return [item.model_copy(deep=True) for item in self.evidence], []


def _evidence(
    content: str,
    url: str,
    *,
    endorses: bool,
    confidence: float = 0.8,
    tier: int = 1,
) -> Evidence:
    return Evidence(
        content=content,
        source_url=url,
        source_type=EvidenceSource.EXTERNAL,
        source_endorses_claim=endorses,
        confidence=confidence,
        source_tier=tier,
    )


def duplicate_family_variants() -> list[dict[str, Any]]:
    claim = "Pure water boils at 100 degrees Celsius at standard atmospheric pressure."

    def item() -> Evidence:
        return _evidence(
            (
                "At standard atmospheric pressure, the normal boiling point of pure water "
                "is 100 degrees Celsius. Boiling temperature changes when pressure changes."
            ),
            "https://example.test/reference/water-boiling-point",
            endorses=True,
            confidence=0.9,
        )

    return [
        {
            "id": "duplicate_family_single",
            "dimension": "duplicate_source_families",
            "claim": claim,
            "submitted_confidence": 0.5,
            "evidence": (item(),),
            "fixture_note": "One evidence item from one source family.",
        },
        {
            "id": "duplicate_family_triplicate",
            "dimension": "duplicate_source_families",
            "claim": claim,
            "submitted_confidence": 0.5,
            "evidence": (item(), item(), item()),
            "fixture_note": (
                "The exact same evidence and URL are repeated three times. "
                "The current kernel has no family deduplication."
            ),
        },
    ]


def shuffle_fixture() -> dict[str, Any]:
    claim = "A city-wide curfew caused the reported 15 percent decline in incidents."
    evidence = (
        _evidence(
            (
                "The police department reported that incidents were 15 percent lower "
                "during the six months after the city-wide curfew began."
            ),
            "https://example.test/city/police-after-curfew",
            endorses=True,
            confidence=0.86,
        ),
        _evidence(
            (
                "Comparable nearby cities without a curfew reported declines of 13 to "
                "16 percent during the same period, consistent with a regional trend."
            ),
            "https://example.test/university/regional-comparison",
            endorses=False,
            confidence=0.84,
        ),
        _evidence(
            (
                "The city changed its incident-reporting definition when the curfew "
                "started, excluding several categories counted in the earlier period."
            ),
            "https://example.test/auditor/reporting-definition",
            endorses=False,
            confidence=0.82,
        ),
    )
    return {
        "id": "causal_attribution_shuffle",
        "dimension": "shuffle_stability",
        "claim": claim,
        "submitted_confidence": 0.5,
        "evidence": evidence,
        "fixture_note": (
            "Synthetic fixed excerpts isolate sequential evidence-order effects. "
            "They are benchmark stimuli, not claimed real-world sources."
        ),
    }


def ordered_shuffle_variants(limit: int | None = None) -> list[dict[str, Any]]:
    fixture = shuffle_fixture()
    permutations = list(itertools.permutations(fixture["evidence"]))
    if limit is not None:
        permutations = permutations[: max(0, limit)]

    variants: list[dict[str, Any]] = []
    for index, evidence in enumerate(permutations, start=1):
        variants.append(
            {
                **fixture,
                "id": f"{fixture['id']}_order_{index:02d}",
                "order_index": index,
                "order_urls": [item.source_url for item in evidence],
                "evidence": evidence,
            }
        )
    return variants


def verdict_payload(verdict: Any) -> dict[str, Any]:
    evidence = [
        {
            "id": item.id,
            "content": item.content,
            "source_url": item.source_url,
            "source_type": item.source_type.value,
            "source_endorses_claim": item.source_endorses_claim,
            "confidence": item.confidence,
            "source_tier": item.source_tier,
        }
        for item in verdict.evidence
    ]
    return {
        "claim_id": verdict.claim_id,
        "run_id": verdict.run_id,
        "sign": verdict.sign.value,
        "sign_name": verdict.sign.name,
        "reason": verdict.reason.value,
        "confidence": verdict.confidence,
        "falsifier_approved": verdict.falsifier_approved,
        "falsifier_notes": verdict.falsifier_notes,
        "policy_violated": verdict.policy_violated,
        "evidence": evidence,
        "evidence_url_hash": _sha256_json(
            sorted(item["source_url"] or "" for item in evidence)
        ),
    }


def _write_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def execute_case(
    *,
    kernel: QDKernel,
    ledger: Ledger,
    lane: str,
    case: dict[str, Any],
    repetition: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    record: dict[str, Any] = {
        "benchmark_id": BENCHMARK_ID,
        "recorded_at": _utcnow(),
        "lane": lane,
        "case_id": case["id"],
        "dimension": case["dimension"],
        "pair_id": case.get("pair_id"),
        "repetition": repetition,
        "claim": case["claim"],
        "submitted_confidence": float(case["submitted_confidence"]),
        "fixture_note": case.get("fixture_note") or case.get("notes"),
        "order_index": case.get("order_index"),
        "order_urls": case.get("order_urls"),
    }

    try:
        verdict = kernel.evaluate(
            case["claim"],
            float(case["submitted_confidence"]),
        )
        record["status"] = "completed"
        record["verdict"] = verdict_payload(verdict)
        record["ledger_events"] = (
            ledger.get_run(verdict.run_id) if verdict.run_id else []
        )
    except Exception as exc:  # benchmark must preserve failures as data
        record["status"] = "error"
        record["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

    record["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    return record


def _new_ledger(run_dir: Path, filename: str) -> Ledger:
    return Ledger(str(run_dir / filename))


def run_live_lane(
    *,
    run_dir: Path,
    results_path: Path,
    cases: Sequence[dict[str, Any]],
    model: str,
    repeats: int,
) -> None:
    ledger = _new_ledger(run_dir, "live_ledger.db")
    kernel = QDKernel(model=model, ledger=ledger)
    for case in cases:
        for repetition in range(1, repeats + 1):
            print(
                f"\n[LIVE] {case['id']} repetition {repetition}/{repeats}: "
                f"{case['claim']}"
            )
            record = execute_case(
                kernel=kernel,
                ledger=ledger,
                lane="live",
                case=case,
                repetition=repetition,
            )
            _write_jsonl(results_path, record)


def run_controlled_lane(
    *,
    run_dir: Path,
    results_path: Path,
    model: str,
    repeats: int,
    shuffle_limit: int | None,
) -> None:
    cases = duplicate_family_variants() + ordered_shuffle_variants(shuffle_limit)
    ledger = _new_ledger(run_dir, "controlled_ledger.db")

    for case in cases:
        for repetition in range(1, repeats + 1):
            print(
                f"\n[CONTROLLED] {case['id']} repetition {repetition}/{repeats}"
            )
            kernel = QDKernel(
                model=model,
                ledger=ledger,
                retriever=FixedRetriever(tuple(case["evidence"])),
            )
            record = execute_case(
                kernel=kernel,
                ledger=ledger,
                lane="controlled",
                case=case,
                repetition=repetition,
            )
            _write_jsonl(results_path, record)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def summarize_records(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_case.setdefault(record["case_id"], []).append(record)

    cases: dict[str, Any] = {}
    for case_id, case_records in sorted(by_case.items()):
        completed = [r for r in case_records if r.get("status") == "completed"]
        errors = [r for r in case_records if r.get("status") == "error"]
        triples = Counter(
            (
                r["verdict"]["sign"],
                r["verdict"]["reason"],
                round(float(r["verdict"]["confidence"]), 3),
                bool(r["verdict"]["falsifier_approved"]),
            )
            for r in completed
        )
        confidence_values = [
            float(r["verdict"]["confidence"]) for r in completed
        ]
        evidence_hashes = Counter(
            r["verdict"]["evidence_url_hash"] for r in completed
        )
        cases[case_id] = {
            "lane": case_records[0]["lane"],
            "dimension": case_records[0]["dimension"],
            "pair_id": case_records[0].get("pair_id"),
            "attempted": len(case_records),
            "completed": len(completed),
            "errors": len(errors),
            "distinct_outcomes": [
                {
                    "sign": key[0],
                    "reason": key[1],
                    "confidence": key[2],
                    "falsifier_approved": key[3],
                    "count": count,
                }
                for key, count in sorted(triples.items(), key=lambda item: str(item[0]))
            ],
            "confidence_min": min(confidence_values) if confidence_values else None,
            "confidence_max": max(confidence_values) if confidence_values else None,
            "confidence_mean": (
                round(statistics.mean(confidence_values), 4)
                if confidence_values
                else None
            ),
            "distinct_evidence_sets": len(evidence_hashes),
            "evidence_set_counts": dict(evidence_hashes),
            "error_types": dict(
                Counter(r["error"]["type"] for r in errors)
            ),
        }

    pair_groups: dict[str, list[str]] = {}
    for case_id, summary in cases.items():
        pair_id = summary.get("pair_id")
        if pair_id:
            pair_groups.setdefault(pair_id, []).append(case_id)

    return {
        "benchmark_id": BENCHMARK_ID,
        "generated_at": _utcnow(),
        "records": len(records),
        "completed": sum(r.get("status") == "completed" for r in records),
        "errors": sum(r.get("status") == "error" for r in records),
        "cases": cases,
        "pair_groups": pair_groups,
    }


def summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {BENCHMARK_ID} summary",
        "",
        f"- Records: {summary['records']}",
        f"- Completed: {summary['completed']}",
        f"- Errors: {summary['errors']}",
        "",
        "This is descriptive baseline evidence. It does not certify correctness.",
        "",
        "| Case | Lane | Dimension | Completed | Distinct outcomes | Confidence range | Evidence sets |",
        "|---|---|---|---:|---:|---|---:|",
    ]
    for case_id, case in summary["cases"].items():
        low = case["confidence_min"]
        high = case["confidence_max"]
        confidence = "n/a" if low is None else f"{low:.3f}–{high:.3f}"
        lines.append(
            f"| `{case_id}` | {case['lane']} | {case['dimension']} | "
            f"{case['completed']}/{case['attempted']} | "
            f"{len(case['distinct_outcomes'])} | {confidence} | "
            f"{case['distinct_evidence_sets']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- Different live evidence-set hashes show retrieval variance, not automatically model inconsistency.",
            "- Different outcomes with one fixed evidence set show kernel/model variance.",
            "- Different outcomes across shuffle orders are evidence of possible path dependence.",
            "- Single versus triplicate duplicate-family results expose whether repetition changes the outcome or confidence.",
            "- Expected failures are baseline observations, not regressions.",
            "",
        ]
    )
    return "\n".join(lines)


def write_summary(run_dir: Path) -> dict[str, Any]:
    records = read_jsonl(run_dir / "results.jsonl")
    summary = summarize_records(records)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (run_dir / "summary.md").write_text(
        summary_markdown(summary),
        encoding="utf-8",
    )
    return summary


def create_manifest(
    *,
    run_dir: Path,
    args: argparse.Namespace,
    cases_path: Path,
) -> dict[str, Any]:
    manifest = {
        "benchmark_id": BENCHMARK_ID,
        "started_at": _utcnow(),
        "model": args.model,
        "mode": args.mode,
        "live_repeats": args.live_repeats,
        "controlled_repeats": args.controlled_repeats,
        "shuffle_limit": args.shuffle_limit,
        "cases_path": str(cases_path),
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "output_directory": str(run_dir),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "git_commit": _git_value("rev-parse", "HEAD"),
            "git_branch": _git_value("branch", "--show-current"),
            "git_status_porcelain": _git_value(
                "status", "--porcelain", default=""
            ),
            "tavily_api_key_present": bool(os.environ.get("TAVILY_API_KEY")),
        },
        "guardrail": (
            "This run records current behavior before rearchitecture. "
            "It is not a truth certification and expected failures are not regressions."
        ),
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record QD's pre-rearchitecture baseline behavior."
    )
    parser.add_argument(
        "--mode",
        choices=("all", "live", "controlled", "summarize"),
        default="all",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--live-repeats", type=int, default=2)
    parser.add_argument("--controlled-repeats", type=int, default=2)
    parser.add_argument(
        "--shuffle-limit",
        type=int,
        default=6,
        help="Number of fixed-evidence permutations to run (maximum 6).",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES_PATH,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "New run directory. For --mode summarize, point to an existing run directory."
        ),
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.live_repeats < 1:
        raise ValueError("--live-repeats must be at least 1")
    if args.controlled_repeats < 1:
        raise ValueError("--controlled-repeats must be at least 1")
    if not 1 <= args.shuffle_limit <= 6:
        raise ValueError("--shuffle-limit must be between 1 and 6")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _validate_args(args)

    if args.mode == "summarize":
        if args.output_dir is None:
            raise SystemExit("--mode summarize requires --output-dir")
        summary = write_summary(args.output_dir)
        print(json.dumps(summary, indent=2))
        return 0

    cases_path = args.cases.resolve()
    live_cases = load_live_cases(cases_path)
    run_dir = args.output_dir or (DEFAULT_RESULTS_ROOT / _slug_timestamp())
    run_dir.mkdir(parents=True, exist_ok=False)
    results_path = run_dir / "results.jsonl"
    create_manifest(run_dir=run_dir, args=args, cases_path=cases_path)

    try:
        if args.mode in ("all", "live"):
            run_live_lane(
                run_dir=run_dir,
                results_path=results_path,
                cases=live_cases,
                model=args.model,
                repeats=args.live_repeats,
            )
        if args.mode in ("all", "controlled"):
            run_controlled_lane(
                run_dir=run_dir,
                results_path=results_path,
                model=args.model,
                repeats=args.controlled_repeats,
                shuffle_limit=args.shuffle_limit,
            )
    finally:
        summary = write_summary(run_dir)
        print(f"\nBaseline artifacts written to: {run_dir}")
        print(
            f"Completed {summary['completed']} of {summary['records']} records; "
            f"errors={summary['errors']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
