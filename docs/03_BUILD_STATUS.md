# Build Status

**As of July 13, 2026. Verified against baseline commit
`1e7f6259a4af2e0fbed0a535d44c84325d212104`.**

## Verified foundation

- Ternary verdict carries sign, epistemic reason, and confidence.
- Falsifier gate is structurally required and strictly parsed.
- Evidence Policy v0.2 is symmetric at the policy layer.
- SQLite ledger is append-only and preserves reconciliation scars.
- Tavily retrieval includes source-tier classification and filtering.
- Elimination-funnel mechanics are integrated and deterministically tested.
- Baseline benchmark instrumentation includes live and controlled lanes.
- Deterministic suite: 57 passed.

## Pre-rearchitecture baseline completed

Command: `py benchmarks/baseline_v1.py`

Results:

- 36 of 36 evaluations completed.
- Zero execution errors.
- Live Qwen `qwen2.5:32b` plus Tavily lane completed.
- Controlled duplicate-family and evidence-permutation lanes completed.
- Human-readable record:
  `docs/baselines/2026-07-10_baseline_v1.md`
- Raw archive:
  `docs/baselines/baseline_v1_20260710T175347Z.zip`

## Established baseline findings

- Evidence order affected controlled funnel outcomes.
- Some fixed-evidence repetitions changed without retrieval variance.
- Repeated live runs sometimes received different source sets.
- The Assessor confidently supported obvious false or fictional claims.
- Claim framing materially changed the MMR result.
- Equal high confidence appeared on opposite alcohol-health verdicts.
- The Falsifier rejected every live evaluation and varied in controlled
  repetitions.
- The duplicate-family fixture did not demonstrate confidence inflation.

## Architectural ruling

The funnel remains useful as an auditable diagnostic and
possibility-generation instrument.

Funnel survivor polarity does not have earned authority to declare truth.
The generated hypothesis base is non-exhaustive and order-sensitive.

Disagreement diagnosis may eliminate possible explanations, but must not
appoint a causal winner. The last survivor remains a suspect, not a
conviction.

## Next gate

1. Four-state source relation:
   `SUPPORTS`, `REFUTES`, `NEUTRAL`, `UNCLEAR`.
2. Clean-room per-source relation classification.
3. Deterministic tests covering satire, quotation, neutral reporting,
   malformed output, polarity symmetry, order independence, and stability.

The classifier receives no verdict authority until controlled and live
benchmarks earn it.

## Still parked

- Approval TTL
- Claim decomposition
- Source-family identity
- Confidence redesign
- Disagreement hypothesis ledger
- Idle recombination
- Minority live-claim lane
- Additional cognitive organs
- Rover cognition integration

The canonical source of truth is `qd_state.yaml`.
