"""
Truncation sweep  —  is the satire mislabel caused by cutting off context?

BACKGROUND
----------
The live endorsement labeler reads only evidence.content[:400]. Before that,
the retriever stores only Tavily's content[:500]. So the model judged the
Guardian satire piece on ~400 chars of an already-short extract — and those
first chars are pure fake-earnest flat-earth voice, with the satirical "tell"
plausibly cut off.

This script isolates the truncation variable. It re-fetches the Guardian URL
fresh, then asks the REAL elimination prompt + REAL model to label endorsement
at increasing context lengths: 400 (current behaviour, the control), 800,
1500, and the full extract Tavily returns. Nothing else changes.

READING THE RESULT
------------------
- Flips to "does NOT endorse" at 800/1500  -> truncation is the cause.
  Fix is widening the caps (cheap). Q's stance-ambiguity architecture becomes
  maybe-later, not now.
- Still "ENDORSES" at full length -> the model genuinely can't read this
  satire even with the whole extract. Q's capability-boundary call is right;
  the Boolean label is inadequate and the ambiguity lane is earned.
- Note the length of the full extract. If Tavily itself only returns a few
  hundred chars, then "full" is still shallow and the real finding is
  "our source extract is too thin for stance detection" — also useful.

Touches NO committed code. Standalone experiment. Run from repo root:
    python truncation_sweep.py
"""

from qd import QDKernel, Claim
from qd.kernel import _ELIMINATION_PROMPT
from qd.schema import Evidence, EvidenceSource

CLAIM = "The Earth is flat."
GUARDIAN_URL = "theguardian.com/science/brain-flapping/2016/jan/26/earth-totally-flat-conspiracy-bob"
LENGTHS = [400, 800, 1500, None]   # None = full available extract
MODEL = "qwen2.5:32b"


def build_user_message(claim_text: str, content: str, url: str) -> str:
    """Reproduce the kernel's elimination user-message exactly, minus the
    per-item [:400] truncation (we control length ourselves here). We give the
    model a minimal two-explanation base so the prompt is well-formed; the
    endorsement label does not depend on the explanation set."""
    candidates = "  [h1] (SUPPORTED) the claim is true\n  [h2] (REFUTED) the claim is false"
    return (
        f'Claim: "{claim_text}"\n\n'
        f"Explanations still in play:\n{candidates}\n\n"
        f"Evidence item:\n"
        f"  source: {url}\n"
        f"  {content}\n\n"
        f"Which explanations does THIS evidence contradict?"
    )


def main() -> None:
    kernel = QDKernel(model=MODEL)

    # 1. Re-fetch fresh so we get the fullest extract Tavily will give us,
    #    NOT the [:500] the retriever would have stored.
    print(f"Re-fetching: {GUARDIAN_URL}\n")
    retrieved, _ = kernel.retriever.fetch(CLAIM)
    guardian = next((e for e in retrieved if "theguardian.com" in (e.source_url or "")), None)

    if guardian is None:
        print("Guardian source not in this retrieval. Re-run (retrieval can vary),")
        print("or the source dropped out of the top results this time.")
        print("Retrieved URLs were:")
        for e in retrieved:
            print(f"   {e.source_url}")
        return

    full = guardian.content or ""
    print(f"Full extract available from retriever: {len(full)} characters.")
    print("NOTE: the retriever already caps Tavily at content[:500], so 'full'")
    print("here is at most ~500 chars. If the tell lives past 500, even this")
    print("sweep can't see it — that would itself be the finding (storage cap).\n")
    print("First 500 chars of what we have:")
    print("-" * 70)
    print(full[:500])
    print("-" * 70 + "\n")

    # 2. Sweep the length knob. Only content length changes.
    print("ENDORSEMENT LABEL vs. CONTEXT LENGTH")
    print("=" * 70)
    for n in LENGTHS:
        content = full if n is None else full[:n]
        label_len = "full" if n is None else str(n)

        user_message = build_user_message(CLAIM, content, guardian.source_url)
        try:
            result = kernel.ollama.complete_json(
                system_prompt=_ELIMINATION_PROMPT,
                user_message=user_message,
                temperature=0.2,
            )
            endorses, malformed = QDKernel._read_endorsement(result)
            verdict = "MALFORMED" if malformed else ("ENDORSES" if endorses else "does NOT endorse")
            note = str(result.get("note", ""))[:120]
        except Exception as exc:  # noqa: BLE001
            verdict = f"ERROR: {type(exc).__name__}: {exc}"
            note = ""

        print(f"  chars sent = {label_len:>4}  ->  {verdict}")
        if note:
            print(f"                     model note: {note}")
    print("=" * 70)
    print("\nIf the label flips as chars increase, truncation was the cause.")
    print("If it stays ENDORSES throughout, it's a model stance-limit, not truncation.")


if __name__ == "__main__":
    main()
