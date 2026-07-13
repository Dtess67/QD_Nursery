"""
Funnel replay  —  find the real variable behind the Guardian ENDORSES label.

WHAT WE LEARNED SO FAR
----------------------
- Live full-kernel runs: Guardian satire labeled ENDORSES, 3/3 (stable).
- A simplified sweep (generic "true/false" explanation base, no narrowing):
  Guardian labeled does-NOT-endorse at 400/800/1500/full chars.
=> Context length is NOT the variable. The difference was the EXPLANATION BASE
   and/or the sequential narrowing the real _assess funnel does. The simplified
   sweep accidentally removed the very thing that causes the bug.

WHAT THIS SCRIPT DOES
---------------------
Reproduces the REAL elimination conditions and instruments them, so we can see
which input tips the Guardian label:

  1. Runs the real _generate_explanations(claim) to get the actual wide base.
  2. Runs the real retrieval, finds the Guardian item and its POSITION in the
     evidence order.
  3. Replays the funnel exactly like _assess: each evidence item sees only the
     still-alive explanations; we print, per step, what the model was shown and
     what it labeled — with special focus on the Guardian step.
  4. Then runs a controlled contrast for the Guardian item ALONE against:
       (a) the full generated base,
       (b) the base as narrowed when Guardian is actually reached,
       (c) a generic true/false pair (the sweep's condition, for comparison).

Run it a few times: the base is generated at temperature 0.4, so it varies.
We're looking for WHICH condition produces ENDORSES.

Touches NO committed code. Standalone. Run from repo root:
    python funnel_replay.py
"""

from qd import QDKernel, Claim

CLAIM = "The Earth is flat."
MODEL = "qwen2.5:32b"


def label_one(kernel, claim, evidence, alive):
    """Call the REAL _eliminate_with_evidence and read the endorsement label."""
    elim = kernel._eliminate_with_evidence(claim, evidence, alive)
    endorses, malformed = kernel._read_endorsement(elim)
    verdict = "MALFORMED" if malformed else ("ENDORSES" if endorses else "does NOT endorse")
    return verdict, elim


def show_base(base):
    for h in base:
        print(f"      [{h.id}] ({h.polarity.name}) {h.statement}")


def main() -> None:
    kernel = QDKernel(model=MODEL)
    claim = Claim(text=CLAIM)

    # --- Step 1: the real generated explanation base -----------------------
    print("=" * 72)
    print("STEP 1  —  real _generate_explanations base (temp 0.4, varies per run)")
    print("=" * 72)
    base = kernel._generate_explanations(claim)
    print(f"  {len(base)} explanations generated:")
    show_base(base)

    # --- Step 2: real retrieval + Guardian position ------------------------
    print("\n" + "=" * 72)
    print("STEP 2  —  real retrieval order")
    print("=" * 72)
    retrieved, _ = kernel.retriever.fetch(claim.text)
    guardian_idx = None
    for i, e in enumerate(retrieved):
        tag = ""
        if "theguardian.com" in (e.source_url or ""):
            guardian_idx = i
            tag = "   <-- GUARDIAN (satire)"
        print(f"  [{i}] {e.source_url}{tag}")
    if guardian_idx is None:
        print("\n  Guardian not retrieved this run — re-run (retrieval varies).")
        return

    # --- Step 3: replay the funnel exactly like _assess --------------------
    print("\n" + "=" * 72)
    print("STEP 3  —  funnel replay (each item sees only still-alive explanations)")
    print("=" * 72)
    alive = list(base)
    for i, e in enumerate(retrieved):
        is_guardian = (i == guardian_idx)
        marker = "  <<< GUARDIAN" if is_guardian else ""
        print(f"\n  --- evidence [{i}] {e.source_url}{marker}")
        print(f"      alive before: {[h.id for h in alive]}")
        verdict, elim = label_one(kernel, claim, e, alive)
        print(f"      ENDORSEMENT: {verdict}")
        print(f"      note: {str(elim.get('note',''))[:140]}")
        # narrow alive set exactly like _assess does
        hit = {str(x) for x in elim.get("eliminated", [])}
        alive = [h for h in alive if h.id not in hit]
        print(f"      eliminated: {sorted(hit) or 'none'}   alive after: {[h.id for h in alive]}")

    # --- Step 4: controlled contrast for the Guardian item alone -----------
    print("\n" + "=" * 72)
    print("STEP 4  —  Guardian labeled against three different explanation sets")
    print("=" * 72)
    g = retrieved[guardian_idx]

    print("\n  (a) against the FULL generated base:")
    va, _ = label_one(kernel, claim, g, list(base))
    print(f"      -> {va}")

    # Rebuild the narrowed set as it was when Guardian was reached (re-run funnel
    # up to guardian_idx, fresh, since Step 3 mutated alive).
    alive2 = list(base)
    for i in range(guardian_idx):
        _, elim = label_one(kernel, claim, retrieved[i], alive2)
        hit = {str(x) for x in elim.get("eliminated", [])}
        alive2 = [h for h in alive2 if h.id not in hit]
    print(f"\n  (b) against the NARROWED base as reached in sequence "
          f"(alive: {[h.id for h in alive2]}):")
    vb, _ = label_one(kernel, claim, g, alive2)
    print(f"      -> {vb}")

    print("\n  (c) against a generic true/false pair (the earlier sweep's condition):")
    # minimal two-item base
    from qd.kernel import _Explanation
    from qd.schema import TruthSign
    generic = [
        _Explanation(id="h1", statement="the claim is true", polarity=TruthSign.SUPPORTED),
        _Explanation(id="h2", statement="the claim is false", polarity=TruthSign.REFUTED),
    ]
    vc, _ = label_one(kernel, claim, g, generic)
    print(f"      -> {vc}")

    print("\n" + "=" * 72)
    print("READ: if (a) or (b) = ENDORSES but (c) = does NOT endorse, the")
    print("explanation base is the variable — the real wide/narrowed candidate")
    print("set tips the label, not context length. Compare (a) vs (b) to see")
    print("whether it's the base itself or the sequential narrowing.")
    print("=" * 72)


if __name__ == "__main__":
    main()
