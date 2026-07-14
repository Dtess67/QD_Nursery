"""
Test 1  —  clean-room endorsement classification (the proposed cure).

HYPOTHESIS (Claude + Q converged): the Guardian satire is mislabeled ENDORSES
only because the endorsement question is asked in the SAME model call as the
elimination step, whose explanation base voices the flat-earth position in
believer-voice. Asked in isolation — claim + source only, no explanations —
the model labels it correctly (condition (c) did this 3/3).

This tests the fix directly: ask endorsement in a clean room for ALL FIVE
retrieved sources, no explanation base anywhere in context. Uses the SAME
endorsement rules as the production prompt, just lifted out of the elimination
job.

PASS  = Guardian flips to 'does NOT endorse' AND the other four stay correct,
        stable across runs.
FAIL  = Guardian still ENDORSES  -> separation alone isn't the cure, rethink.
PARTIAL = a previously-correct source breaks -> the clean room has its own
          problem; note which.

Run 2-3 times (label is not fully deterministic). Five model calls per run.
Touches NO committed code. Run from repo root:  python endorsement_cleanroom.py
"""

from qd import QDKernel, Claim

CLAIM = "The Earth is flat."
MODEL = "qwen2.5:32b"

# Endorsement rules lifted VERBATIM from the production _ELIMINATION_PROMPT,
# with the elimination job and explanation base removed. This is the ONLY
# question the model is asked here.
CLEANROOM_PROMPT = """You are the endorsement classifier in the QD kernel.

You are given a claim and ONE retrieved source. Your ONLY job is to decide
whether the SOURCE ITSELF endorses the claim. This is a strict test, not "is
the source about the topic".

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

  Do NOT mark true merely because the evidence mentions the claim,
  describes believers, or contains quoted language asserting the claim.

Return ONLY a JSON object with this exact shape:

{
  "source_endorses_claim": true or false,
  "note": "one sentence on why"
}
"""


def classify(kernel, claim_text, evidence):
    user_message = (
        f'Claim: "{claim_text}"\n\n'
        f"Source:\n"
        f"  url: {evidence.source_url}\n"
        f"  content: {evidence.content}\n\n"
        f"Does this source endorse the claim?"
    )
    result = kernel.ollama.complete_json(
        system_prompt=CLEANROOM_PROMPT,
        user_message=user_message,
        temperature=0.2,
    )
    endorses, malformed = QDKernel._read_endorsement(result)
    verdict = "MALFORMED" if malformed else ("ENDORSES" if endorses else "does NOT endorse")
    return verdict, str(result.get("note", ""))[:130]


def main() -> None:
    kernel = QDKernel(model=MODEL)
    claim = Claim(text=CLAIM)

    retrieved, _ = kernel.retriever.fetch(claim.text)
    print(f"Claim: {CLAIM}")
    print(f"Retrieved {len(retrieved)} sources. Classifying endorsement in a")
    print("clean room (claim + source only, NO explanation base).\n")
    print("=" * 72)

    endorsing = []
    for i, e in enumerate(retrieved):
        is_guardian = "theguardian.com" in (e.source_url or "")
        verdict, note = classify(kernel, claim.text, e)
        tag = "  <<< GUARDIAN (satire — must read 'does NOT endorse')" if is_guardian else ""
        print(f"\n[{i}] {verdict}{tag}")
        print(f"    {e.source_url}")
        print(f"    note: {note}")
        if verdict == "ENDORSES":
            endorsing.append(e.source_url)

    print("\n" + "=" * 72)
    print(f"{len(endorsing)} of {len(retrieved)} labeled ENDORSES.")
    guardian_bad = any("theguardian.com" in u for u in endorsing)
    if guardian_bad:
        print("RESULT: Guardian STILL endorses in clean room — separation is NOT")
        print("the cure by itself. Report back; we rethink.")
    elif endorsing:
        print("RESULT: Guardian is fixed, but another source now reads ENDORSES —")
        print("check whether that source genuinely advocates the claim (could be")
        print("correct) or is a new false positive.")
    else:
        print("RESULT: 0 endorse. If a genuine flat-earth-advocacy page were in the")
        print("set it SHOULD read ENDORSES, so 0 is right only if none advocate.")
        print("Guardian reading 'does NOT endorse' = the cure works this run.")
    print("Run 2-3x to confirm stability.")
    print("=" * 72)


if __name__ == "__main__":
    main()
