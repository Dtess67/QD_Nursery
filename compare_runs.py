"""
Compare all ledger runs for a given claim text — useful for spotting
run-to-run variance like the Earth-flat inconsistency.

Usage: python compare_runs.py "The Earth is flat."
"""
import sys
from qd import Ledger

def compare(claim_substring: str):
    ledger = Ledger("qd_ledger.db")

    # Pull recent runs and find ones matching the claim
    all_runs = ledger.recent_runs(50)
    matches = []

    for run_id in all_runs:
        events = ledger.get_run(run_id)
        for e in events:
            if e["event_type"] == "CLAIM_RECEIVED":
                if claim_substring.lower() in e["payload"].get("text", "").lower():
                    matches.append((run_id, events))
                break

    if not matches:
        print(f"No runs found matching: {claim_substring}")
        return

    print(f"\nFound {len(matches)} run(s) matching '{claim_substring}'\n")

    for i, (run_id, events) in enumerate(matches, 1):
        print(f"{'='*70}")
        print(f"RUN {i}  ({run_id})")
        print(f"{'='*70}")

        for e in events:
            t = e["event_type"]
            p = e["payload"]

            if t == "CLAIM_RECEIVED":
                print(f"  CLAIM: {p['text']}  (submitted_conf={p['submitted_confidence']})")

            elif t == "SOURCE_FILTERED":
                print(f"  FILTERED: {p['url']}  [{p['label']}]")

            elif t == "ASSESSOR_OUTPUT" and p.get("stage") == "retrieval":
                print(f"  RETRIEVED {p['sources_retrieved']} sources, tiers={p.get('tiers')}")
                for url in p.get("urls", []):
                    print(f"    - {url}")

            elif t == "ASSESSOR_OUTPUT":
                print(f"  ASSESSOR: sign={p['sign']} reason={p['reason']} conf={p['confidence']:.2f}")
                print(f"    \"{p['assessment'][:200]}\"")

            elif t == "FALSIFIER_OUTPUT":
                print(f"  FALSIFIER: approved={p['approved']} sign={p['sign']} conf={p['confidence']:.2f}")
                print(f"    {p['notes'][:300]}")

            elif t == "VERDICT_ISSUED":
                print(f"  >>> FINAL: sign={p['sign']} reason={p['reason']} "
                      f"conf={p['confidence']:.2f} approved={p['falsifier_approved']}")

        print()

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "Earth is flat"
    compare(query)
