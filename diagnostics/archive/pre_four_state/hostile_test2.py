"""
Hostile Test 2  —  Q-ruled confound killer. Decides cheap-reorder vs. separate-call.

Q's ruling: Test 2 (reordered one-call) passed 4/4, but in 3/4 passes the
sympathetic SUPPORTED explanations had already been narrowed away before
Guardian was reached. So ordering was never tested against the FULL hostile
base. This experiment forces exactly that condition.

DESIGN (per Q spec):
- Claim: "The Earth is flat."
- Source: the Guardian satire article (fetched live).
- Alive base: a DELIBERATELY hostile, FIXED, fully-alive set of SUPPORTED
  explanations phrased in believer-voice — the exact kind that lexically
  aligns with the satire's surface. Hard-coded, NOT generated, NOT narrowed,
  so the poison is at full strength every single run.
- Endorsement asked FIRST, base still present later in the same prompt.
- Explicit instruction: "Alignment with an explanation is NOT endorsement."

PASS BAR (Q): 6/6 minimum, 10/10 better. EVERY run must label Guardian
source_endorses_claim=False, with notes showing the right mechanism
(satire / voiced-not-endorsed). ANY single ENDORSES = Test 2 fails for
kernel purposes -> implement Test 1 (separate call), stop polishing.

Run once; it loops 10 times internally. ~10 model calls.
Touches NO committed code. Run from repo root:  python hostile_test2.py
"""

from qd import QDKernel, Claim
from qd.kernel import _Explanation
from qd.schema import TruthSign

CLAIM = "The Earth is flat."
MODEL = "qwen2.5:32b"
RUNS = 10

# DELIBERATELY HOSTILE fixed base: SUPPORTED-heavy, believer-voiced, phrased to
# lexically align with the satire's surface. This is the worst case — the
# sympathetic explanations the original bug latched onto, kept fully alive.
HOSTILE_BASE = [
    _Explanation(id="h1", polarity=TruthSign.SUPPORTED,
        statement="The Earth is flat and the globe model is a deception promoted by institutions."),
    _Explanation(id="h2", polarity=TruthSign.SUPPORTED,
        statement="You only need to look at the evidence to conclude the Earth is flat."),
    _Explanation(id="h3", polarity=TruthSign.SUPPORTED,
        statement="Flat Earth societies argue governments and NASA conspire to hide the truth."),
    _Explanation(id="h4", polarity=TruthSign.SUPPORTED,
        statement="From the ground the horizon looks flat, so the Earth is flat."),
    _Explanation(id="h5", polarity=TruthSign.REFUTED,
        statement="Satellite imagery and space missions show the Earth is a sphere."),
]

REORDERED_PROMPT = """You are the Assessor in the QD kernel, running an elimination funnel.

You are given the claim, ONE piece of retrieved external evidence, and the
explanations still in play.

FIRST, before anything else, decide whether the SOURCE ITSELF endorses the
claim — a strict test, not "is it about the topic". Judge the source's own
authorial stance on the claim WITHOUT reference to the explanation list below.

  source_endorses_claim: true ONLY if the source itself endorses or
  concludes that the claim is true.

  false if the source:
   - denies the claim,
   - argues against the claim,
   - fact-checks the claim as false,
   - quotes someone else making the claim without endorsing it,
   - explains why people believe the claim,
   - satirizes the claim,
   - discusses the claim as a belief, rumor, theory, controversy, or
     misinformation.

  Do NOT mark true merely because the evidence mentions the claim, describes
  believers, or contains quoted language asserting the claim. Alignment with
  an explanation in the list below is NOT source endorsement. A source can
  lexically resemble a SUPPORTED explanation while its author does not endorse
  the claim (e.g. satire, quotation, reported belief).

SECOND, decide which explanations this evidence CONTRADICTS:
- Eliminate an explanation ONLY when the evidence genuinely contradicts it.
- Do NOT eliminate an explanation just because the evidence is silent on it.
- Use the exact explanation ids given to you.

Return ONLY a JSON object with this exact shape (endorsement first):

{
  "source_endorses_claim": true or false,
  "eliminated": ["id", ...],
  "note": "one sentence on the source's authorial stance and what it rules out"
}

Return ONLY the JSON object. No preamble."""


def run_once(kernel, claim, guardian):
    candidates = "\n".join(
        f"  [{h.id}] ({h.polarity.name}) {h.statement}" for h in HOSTILE_BASE
    )
    user_message = (
        f'Claim: "{claim.text}"\n\n'
        f"Evidence item:\n"
        f"  source: {guardian.source_url}\n"
        f"  {guardian.content[:400]}\n\n"
        f"Explanations still in play:\n{candidates}\n"
    )
    result = kernel.ollama.complete_json(
        system_prompt=REORDERED_PROMPT,
        user_message=user_message,
        temperature=0.2,
    )
    endorses, malformed = QDKernel._read_endorsement(result)
    verdict = "MALFORMED" if malformed else ("ENDORSES" if endorses else "does NOT endorse")
    return verdict, str(result.get("note", ""))[:150]


def main() -> None:
    kernel = QDKernel(model=MODEL)
    claim = Claim(text=CLAIM)

    retrieved, _ = kernel.retriever.fetch(claim.text)
    guardian = next((e for e in retrieved if "theguardian.com" in (e.source_url or "")), None)
    if guardian is None:
        print("Guardian not retrieved this run — re-run (retrieval varies).")
        return

    print("HOSTILE TEST 2 — reorder vs. FULL sympathetic SUPPORTED base (fixed, un-narrowed)")
    print(f"Source: {guardian.source_url}")
    print("Hostile base held fully alive every run:")
    for h in HOSTILE_BASE:
        print(f"   [{h.id}] ({h.polarity.name}) {h.statement}")
    print("=" * 72)

    passes, fails = 0, 0
    for r in range(1, RUNS + 1):
        verdict, note = run_once(kernel, claim, guardian)
        ok = verdict == "does NOT endorse"
        passes += ok
        fails += (not ok)
        flag = "PASS" if ok else "*** FAIL ***"
        print(f"\nrun {r:>2}: {verdict:>16}  [{flag}]")
        print(f"        note: {note}")

    print("\n" + "=" * 72)
    print(f"RESULT: {passes}/{RUNS} passed, {fails} failed.")
    if fails > 0:
        print("VERDICT: Test 2 FAILS hostile condition. Ordering does NOT immunize")
        print("against an in-context sympathetic base. Per Q's decision rule ->")
        print("implement Test 1 (separate clean-room call). Stop polishing one-call.")
    elif passes >= 6:
        print("VERDICT: Test 2 SURVIVES the hostile base (>=6/6). Per Q's decision")
        print("rule -> reorder one-call is safe to implement; keep Test 1 as")
        print("documented fallback. (10/10 is the stronger bar — check the count.)")
    else:
        print("VERDICT: inconclusive — fewer than 6 clean runs recorded.")
    print("=" * 72)


if __name__ == "__main__":
    main()
