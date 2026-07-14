"""
Test 2  —  single-call reordered prompt (the cheaper candidate fix).

Q's proposal: instead of a separate endorsement call (Test 1, confirmed 6/6),
keep ONE model call but restructure it so the model must answer endorsement
BEFORE it reasons about which explanations to eliminate.

Q's own warning, which this test must honestly reproduce, NOT design around:
  "if the explanation base is anywhere in-context, the model can still leak it
   backward into the endorsement read. So the cheap version may be fragile."

So this test keeps the explanation base IN the prompt (that is the real
production condition and the real risk). It only changes ORDER: endorsement
question first, elimination second, and the JSON demands source_endorses_claim
before eliminated. If the label is right here, reorder-in-one-call is enough.
If it's still ENDORSES, the base contaminates regardless of order — and Test 1
(separate call) is the principled fix, not this.

Compares against the SAME funnel condition that failed: real generated base,
Guardian judged against the still-alive explanations at its position.

PASS  = Guardian 'does NOT endorse' across runs, matching Test 1.
FAIL  = Guardian still ENDORSES -> order doesn't cure it; contamination leaks
        backward as Q predicted. Separate call (Test 1) wins.
"THE Q TRAP" = passes ONLY when you strip the base -> that's Test 1 in
        disguise, not a real single-call fix.

Run 2-3x. ~ (1 base-gen + N elimination) calls per run.
Touches NO committed code. Run from repo root:  python endorsement_reorder.py
"""

from qd import QDKernel, Claim

CLAIM = "The Earth is flat."
MODEL = "qwen2.5:32b"

# Same content as production _ELIMINATION_PROMPT, but the endorsement question
# is placed FIRST and the JSON requires source_endorses_claim before eliminated.
REORDERED_PROMPT = """You are the Assessor in the QD kernel, running an elimination funnel.

You are given the claim, ONE piece of retrieved external evidence, and the
explanations still in play.

FIRST, before anything else, decide whether the SOURCE ITSELF endorses the
claim — a strict test, not "is it about the topic". Judge the source's own
stance on the claim WITHOUT reference to the explanation list below.

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
  believers, contains quoted language asserting the claim, or resembles any
  explanation in the list below. Alignment with an explanation is NOT
  endorsement by the source.

SECOND, decide which explanations this evidence CONTRADICTS:
- Eliminate an explanation ONLY when the evidence genuinely contradicts it.
- Do NOT eliminate an explanation just because the evidence is silent on it.
- Use the exact explanation ids given to you.

Return ONLY a JSON object with this exact shape (endorsement first):

{
  "source_endorses_claim": true or false,
  "eliminated": ["id", ...],
  "note": "one sentence on the source's stance and what it rules out"
}

Return ONLY the JSON object. No preamble."""


def eliminate_reordered(kernel, claim, evidence, alive):
    candidates = "\n".join(
        f"  [{h.id}] ({h.polarity.name}) {h.statement}" for h in alive
    )
    user_message = (
        f'Claim: "{claim.text}"\n\n'
        f"Evidence item:\n"
        f"  source: {evidence.source_url}\n"
        f"  {evidence.content[:400]}\n\n"
        f"Explanations still in play:\n{candidates}\n"
    )
    result = kernel.ollama.complete_json(
        system_prompt=REORDERED_PROMPT,
        user_message=user_message,
        temperature=0.2,
    )
    endorses, malformed = QDKernel._read_endorsement(result)
    verdict = "MALFORMED" if malformed else ("ENDORSES" if endorses else "does NOT endorse")
    return verdict, result


def main() -> None:
    kernel = QDKernel(model=MODEL)
    claim = Claim(text=CLAIM)

    base = kernel._generate_explanations(claim)
    retrieved, _ = kernel.retriever.fetch(claim.text)
    guardian_idx = next((i for i, e in enumerate(retrieved)
                         if "theguardian.com" in (e.source_url or "")), None)
    if guardian_idx is None:
        print("Guardian not retrieved this run — re-run (retrieval varies).")
        return

    print(f"Claim: {CLAIM}")
    print(f"Base ({len(base)} explanations, IN CONTEXT — the real risk condition):")
    for h in base:
        print(f"   [{h.id}] ({h.polarity.name}) {h.statement[:80]}")
    print("\nReordered single call: endorsement asked FIRST, base still present.")
    print("=" * 72)

    # Replay the funnel to Guardian's position so it sees the real narrowed base.
    alive = list(base)
    for i in range(guardian_idx):
        _, r = eliminate_reordered(kernel, claim, retrieved[i], alive)
        hit = {str(x) for x in r.get("eliminated", [])}
        alive = [h for h in alive if h.id not in hit]

    g = retrieved[guardian_idx]
    print(f"\nGuardian judged against alive base {[h.id for h in alive]}:")
    verdict, r = eliminate_reordered(kernel, claim, g, alive)
    print(f"  ENDORSEMENT: {verdict}")
    print(f"  note: {str(r.get('note',''))[:150]}")

    print("\n" + "=" * 72)
    if verdict == "ENDORSES":
        print("FAIL: reorder did NOT cure it. Base contaminates backward despite")
        print("endorsement-first ordering, exactly as Q predicted. Separate call")
        print("(Test 1) is the principled fix.")
    else:
        print("PASS this run: reorder-in-one-call read the satire correctly WITH")
        print("the base in context. If stable across runs, the cheaper fix holds.")
        print("Run 2-3x — a single pass is not enough to trust a reorder patch.")
    print("=" * 72)


if __name__ == "__main__":
    main()
