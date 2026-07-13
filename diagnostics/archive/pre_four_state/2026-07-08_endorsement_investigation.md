# Diagnostics — endorsement context-contamination investigation (July 8, 2026)

Standalone, read-only diagnostic scripts. They touch no kernel logic; each
instruments the real kernel (`qd/`) against the live model to isolate one
variable. They are the reproducible evidence behind the scar recorded in
`docs/06_ESTABLISHED_RESULTS.md` and `docs/07_DECISION_LOG_2026-07-01.md`.

Run from the repo root with local Ollama (`qwen2.5:32b`) + Tavily configured,
e.g. `python diagnostics/hostile_test2.py`. Retrieval varies run-to-run, so
several scripts are meant to be run 2–3× (or loop internally).

## The investigation, in order

The committed endorsement fix (`d4dc0d3`) was deterministically sound but its
live goal — stop the Guardian satire source on "The Earth is flat" being
labeled as endorsing the claim — failed 3/3 live. These scripts found why.

| Script | Question it answered | Result |
|---|---|---|
| `live_endorsement_check.py` | Does the fix work live? Shows per-source endorsement labels the ledger doesn't persist. | Guardian satire labeled ENDORSES 3/3. Failure reproduced. |
| `truncation_sweep.py` | Is it caused by content truncation (400 chars)? | No — correct at 400/800/1500/full. Truncation **falsified**. |
| `funnel_replay.py` | Is it the explanation base / sequential narrowing? | Yes — Guardian ENDORSES against the real base, does-NOT-endorse against a generic true/false pair. Cause **isolated**: context contamination. |
| `endorsement_cleanroom.py` | Does a separate call with no base fix it? (Test 1) | 6/6 correct. Clean-room cure works; mechanically airtight. |
| `endorsement_reorder.py` | Does reordering endorsement-first in one call fix it? (Test 2) | 4/4 correct, but confounded — base had narrowed away in 3/4. |
| `hostile_test2.py` | Does reorder survive a FIXED, fully-alive, believer-voiced SUPPORTED base? (Q-ruled confound killer) | **10/10 correct.** Ordering alone immunizes the read. Cure chosen. |

## What was established vs. still open

- **Established (diagnostic level):** cause is context contamination — the
  elimination call's believer-voiced SUPPORTED explanations pull the model
  toward reading lexical alignment as endorsement. Not truncation, not general
  satire incapacity (both falsified above).
- **Cure chosen (per Q's decision rule):** reorder endorsement-first in one
  call; keep the separate clean-room call (Test 1) as documented fallback.
- **Still open:** the cure is not yet implemented in `qd/kernel.py`, and the
  live end-to-end kernel run on the committed change is still owed before this
  is a kernel-level established result. Follow-on hygiene (separate commit,
  per Q, not the main cure): neutralize believer-voice in SUPPORTED explanation
  phrasing — plausible hypotheses, not advocacy copy.
