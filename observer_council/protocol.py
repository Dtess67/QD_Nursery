from __future__ import annotations

import uuid

from .provenance import ObserverProvenance
from .clients import call_observer
from .orientation import load_orientation, build_system_prompt
from .ledger import CouncilLedger
from .exceptions import ObserverUnavailableError, ObserverResponseError


_CROSS_REVIEW_PROMPT_TEMPLATE = """Original question:
{question}

All independent responses (each observer answered without seeing the others):

{all_responses}

Your task is NOT to debate or persuade. Answer only these four questions:

1. Where do you independently converge with other observers?
2. Where do you disagree?
3. Which disagreement matters most?
4. What evidence would resolve it?

Do not try to win. Review honestly."""


class ObserverCouncil:
    """
    Q's protocol, July 2026:

      Phase 1 — Independent Analysis. Same prompt to every observer.
                No one sees anyone else's answer. Preserves independence.

      Phase 2 — Cross Review. Every observer receives the original
                question plus all Phase 1 responses. Only reviews —
                convergence, disagreement, what would resolve it.
                No debating.

      Phase 3 — Synthesis. Built by Darrell — never by a contributing
                observer. Keeps synthesis distinct from advocacy.

    Bounded by design: two phases, then it stops and hands the human
    the full transcript. Not an open channel — a structured protocol
    with a beginning, a procedure, and a stopping condition.
    """

    def __init__(self, orientation_folder: str, ledger: CouncilLedger = None):
        self.orientation = load_orientation(orientation_folder)
        self.ledger = ledger or CouncilLedger()

    def run(self, question: str, observers: list[ObserverProvenance]) -> dict:
        """
        Runs Phase 1 and Phase 2. Returns everything — does NOT
        synthesize. That step is yours, on purpose.
        """
        session_id = str(uuid.uuid4())

        self.ledger.log(session_id, "SESSION_STARTED", {
            "question": question,
            "observers": [o.name for o in observers],
        })

        # ---- Phase 1: Independent Analysis ----
        print("\n[COUNCIL] Phase 1 — Independent Analysis")
        phase1_responses: dict[str, str] = {}
        phase1_failures: dict[str, str] = {}

        for observer in observers:
            print(f"  Asking {observer.name}...")
            system_prompt = build_system_prompt(self.orientation, observer.to_context_line())
            try:
                response = call_observer(observer, system_prompt, question)
                phase1_responses[observer.name] = response
                self.ledger.log(session_id, "PHASE1_RESPONSE", {
                    "observer": observer.name,
                    "response": response,
                })
                print(f"    -> got response ({len(response)} chars)")
            except (ObserverUnavailableError, ObserverResponseError) as e:
                phase1_failures[observer.name] = str(e)
                self.ledger.log(session_id, "PHASE1_FAILURE", {
                    "observer": observer.name,
                    "error": str(e),
                })
                print(f"    -> FAILED: {e}")

        if len(phase1_responses) < 2:
            self.ledger.log(session_id, "SESSION_ABORTED", {
                "reason": "fewer than 2 observers responded — cross-review needs "
                          "at least 2 independent perspectives to compare",
            })
            print("\n[COUNCIL] Aborted — fewer than 2 successful responses. "
                  "Check API keys / connectivity.")
            return {
                "session_id": session_id,
                "phase1": phase1_responses,
                "phase1_failures": phase1_failures,
                "phase2": {},
                "aborted": True,
            }

        # ---- Phase 2: Cross Review ----
        print("\n[COUNCIL] Phase 2 — Cross Review")
        all_responses_text = "\n\n".join(
            f"--- {name} ---\n{resp}" for name, resp in phase1_responses.items()
        )
        cross_review_prompt = _CROSS_REVIEW_PROMPT_TEMPLATE.format(
            question=question, all_responses=all_responses_text
        )

        phase2_responses: dict[str, str] = {}
        phase2_failures: dict[str, str] = {}

        for observer in observers:
            if observer.name not in phase1_responses:
                continue  # skip observers who failed Phase 1
            print(f"  Cross-review from {observer.name}...")
            system_prompt = build_system_prompt(self.orientation, observer.to_context_line())
            try:
                response = call_observer(observer, system_prompt, cross_review_prompt)
                phase2_responses[observer.name] = response
                self.ledger.log(session_id, "PHASE2_RESPONSE", {
                    "observer": observer.name,
                    "response": response,
                })
                print(f"    -> got response ({len(response)} chars)")
            except (ObserverUnavailableError, ObserverResponseError) as e:
                phase2_failures[observer.name] = str(e)
                self.ledger.log(session_id, "PHASE2_FAILURE", {
                    "observer": observer.name,
                    "error": str(e),
                })
                print(f"    -> FAILED: {e}")

        self.ledger.log(session_id, "SESSION_COMPLETE", {
            "phase1_count": len(phase1_responses),
            "phase2_count": len(phase2_responses),
        })

        print(f"\n[COUNCIL] Complete. Session: {session_id}")
        print("[COUNCIL] Phase 3 (Synthesis) is yours — not built by any observer, on purpose.")

        return {
            "session_id": session_id,
            "phase1": phase1_responses,
            "phase1_failures": phase1_failures,
            "phase2": phase2_responses,
            "phase2_failures": phase2_failures,
            "aborted": False,
        }

    def run_falsifier_pass(self, synthesis_text: str, observers: list[ObserverProvenance],
                            session_id: str = None) -> dict:
        """
        Q's addition: not another model, another mode. Runs even when
        everyone agreed — especially then. Only job: assume the
        synthesis is wrong, find the weakest point. Invoked explicitly
        by the human, not automatic — same oversight pattern as the
        rest of this project.
        """
        session_id = session_id or str(uuid.uuid4())
        prompt = (
            f"Here is a synthesis produced from a council review:\n\n{synthesis_text}\n\n"
            "Your only job: assume this synthesis is wrong. Do not propose an "
            "alternative architecture or a replacement. Find the weakest beam — "
            "the single claim in this synthesis most likely to be false, and say why."
        )

        results = {}
        for observer in observers:
            print(f"  Falsifier pass — {observer.name}...")
            system_prompt = build_system_prompt(self.orientation, observer.to_context_line())
            try:
                response = call_observer(observer, system_prompt, prompt)
                results[observer.name] = response
                self.ledger.log(session_id, "FALSIFIER_PASS", {
                    "observer": observer.name,
                    "response": response,
                })
            except (ObserverUnavailableError, ObserverResponseError) as e:
                results[observer.name] = f"FAILED: {e}"
                self.ledger.log(session_id, "FALSIFIER_FAILURE", {
                    "observer": observer.name,
                    "error": str(e),
                })

        return results
