"""
Run a QD Observer Council session.

Usage:
    python run_council.py "Should Layer 3 broaden beyond human safety?" \\
        --observers claude gpt gemini deepseek \\
        --orientation ./QD_Who_Am_I

Falsifier pass on a synthesis you wrote yourself:
    python run_council.py --falsifier synthesis.txt \\
        --observers claude gpt --orientation ./QD_Who_Am_I
"""
from __future__ import annotations

import argparse
import sys

from observer_council import ObserverCouncil, CouncilLedger, get_registered


def main():
    parser = argparse.ArgumentParser(description="QD Observer Council")
    parser.add_argument("question", nargs="?", help="Question to put to the council")
    parser.add_argument("--observers", nargs="+", required=True,
                         help="Observer keys from provenance registry, e.g. claude gpt gemini")
    parser.add_argument("--orientation", required=True,
                         help="Path to folder containing the QD orientation .md files")
    parser.add_argument("--ledger", default="council_ledger.jsonl",
                         help="Path to the append-only session ledger")
    parser.add_argument("--falsifier", metavar="FILE",
                         help="Run a Falsifier pass on a synthesis text file instead of Phase 1/2")

    args = parser.parse_args()

    try:
        observers = get_registered(args.observers)
    except KeyError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    ledger = CouncilLedger(args.ledger)
    council = ObserverCouncil(orientation_folder=args.orientation, ledger=ledger)

    if args.falsifier:
        with open(args.falsifier, "r", encoding="utf-8") as f:
            synthesis_text = f.read()
        print(f"\nRunning Falsifier pass on: {args.falsifier}\n")
        results = council.run_falsifier_pass(synthesis_text, observers)
        print("\n" + "="*70)
        print("FALSIFIER PASS RESULTS")
        print("="*70)
        for name, response in results.items():
            print(f"\n--- {name} ---\n{response}\n")
        return

    if not args.question:
        print("ERROR: question required unless using --falsifier")
        sys.exit(1)

    result = council.run(args.question, observers)

    if result["aborted"]:
        print("\nSession aborted. See ledger for details.")
        sys.exit(1)

    print("\n" + "="*70)
    print("PHASE 1 — INDEPENDENT ANALYSIS")
    print("="*70)
    for name, resp in result["phase1"].items():
        print(f"\n--- {name} ---\n{resp}\n")

    print("\n" + "="*70)
    print("PHASE 2 — CROSS REVIEW")
    print("="*70)
    for name, resp in result["phase2"].items():
        print(f"\n--- {name} ---\n{resp}\n")

    print("\n" + "="*70)
    print(f"Session ID: {result['session_id']}")
    print("Phase 3 (Synthesis) is yours. Read both phases above, write your own.")
    print("Ledger has the full record if you need to revisit anything.")
    print("="*70)


if __name__ == "__main__":
    main()
