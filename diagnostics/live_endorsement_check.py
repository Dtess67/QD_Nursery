"""
Live endorsement-label diagnostic  —  step 2 of the endorsement fix.

WHY THIS EXISTS
---------------
The endorsement bug was NOT visible in the final verdict. On "The Earth is
flat" the Falsifier already caught the mislabel, so the verdict came out
REFUTED *with* the bug present. The bug lived one layer up: a satirical /
explanatory flat-earth source was labelled source_endorses_claim=True.

A well-formed endorsement label is not persisted anywhere in the ledger
(only *malformed* labels raise EVIDENCE_LABEL_SCAR). So the stock
test_kernel.py driver cannot show us what we need. This script calls the
same path the unit tests use (_assess) against the REAL model and prints
the per-evidence endorsement label directly.

WHAT A PASS LOOKS LIKE
----------------------
For "The Earth is flat", any retrieved source that argues AGAINST the claim,
fact-checks it, explains why people believe it, or satirises it should come
back  source_endorses_claim = False.  A source is only True if it itself
concludes the earth is flat. Eyeball the URLs: if a Guardian/Snopes/NASA-type
source is marked True, the prompt fix has NOT worked. If those read False and
only genuine flat-earth-advocacy pages (if any were retrieved) read True,
the fix is doing its job on the live model.

This does NOT change any kernel logic. Read-only diagnostic.
Run from the repo root:  python live_endorsement_check.py
"""

from qd import QDKernel, Claim

# The claim the bug lives on. Add others if you want, but Earth-flat is the
# one that produced the original mislabel.
CLAIMS = [
    "The Earth is flat.",
]

MODEL = "qwen2.5:32b"   # match the engine the kernel actually runs


def check(kernel: QDKernel, claim_text: str) -> None:
    print("\n" + "=" * 70)
    print(f"CLAIM: {claim_text}")
    print("=" * 70)

    # 1. Real retrieval (Tavily), same call evaluate() makes internally.
    retrieved, filtered = kernel.retriever.fetch(claim_text)
    print(f"\nRetrieved {len(retrieved)} source(s); filtered {len(filtered)} low-tier.\n")
    for i, e in enumerate(retrieved, 1):
        print(f"  [{i}] tier={e.source_tier}  {e.source_url}")
        print(f"      {e.content[:160].strip()}...")

    if not retrieved:
        print("\n  (no sources retrieved — check Tavily key / network; nothing to label)")
        return

    # 2. Real assessment through the live model. This is where the prompt
    #    rewrite is exercised: each source gets a source_endorses_claim label.
    run_id = f"live-endorse-{claim_text[:20]}"
    assessment = kernel._assess(Claim(text=claim_text), retrieved, run_id)

    # 3. The thing we actually came to see: per-source endorsement labels.
    print("\n" + "-" * 70)
    print("ENDORSEMENT LABELS  (True = source concludes the claim is TRUE)")
    print("-" * 70)
    endorsing = 0
    for i, e in enumerate(assessment.evidence, 1):
        flag = e.source_endorses_claim
        if flag:
            endorsing += 1
        mark = "ENDORSES" if flag else "does NOT endorse"
        print(f"  [{i}] {mark:>18}  {e.source_url}")
        print(f"      {e.content[:160].strip()}...")

    print("\n" + "-" * 70)
    print(f"SUMMARY: {endorsing} of {len(assessment.evidence)} source(s) labelled as "
          f"ENDORSING '{claim_text}'.")
    print("Now eyeball the URLs above: is anything that argues AGAINST / fact-checks /")
    print("satirises the claim wrongly marked ENDORSES? If yes, the prompt fix failed.")
    print("If the against/satire sources all read 'does NOT endorse', the fix works live.")
    print("-" * 70)


def main() -> None:
    kernel = QDKernel(model=MODEL)
    for c in CLAIMS:
        try:
            check(kernel, c)
        except Exception as exc:  # noqa: BLE001 — diagnostic, surface everything
            print(f"\nERROR while checking {c!r}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
