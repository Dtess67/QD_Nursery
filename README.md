# QD Nursery

QD_Nursery is the supervised research repository for QD's epistemic kernel. The current system retrieves external sources, narrows a generated hypothesis set, proposes a ternary verdict, routes it through a required adversarial Falsifier, and records the run in an append-only ledger.

QD is **pre-alpha**. Deterministic mechanics are tested; dependable live truth behavior is not yet established.

## Canonical state

Read [`qd_state.yaml`](qd_state.yaml) before relying on narrative status documents. It records the verified commit, test result, known failures, build freeze, and next experimental gate.

When documentation disagrees with `qd_state.yaml`, verify the repository and update the state file plus the decision record. Do not silently choose whichever document is newer.

## Setup

Windows PowerShell from the repository root:

```powershell
py -m pip install -r requirements.txt
```

The live kernel additionally requires:

- Ollama running locally with `qwen2.5:32b`
- a Tavily API key in the current shell

```powershell
$env:TAVILY_API_KEY='tvly-...'
```

## Deterministic verification

```powershell
py -m pytest -q
```

This is the mechanical regression gate. The verified result recorded on July 10, 2026 against commit `9e80f28` is **49 passed, 0 failed**.

A passing deterministic suite does **not** establish live Qwen plus Tavily behavior.

## Live kernel run

```powershell
py test_kernel.py
```

This exercises real retrieval and the local model. Live outputs vary with retrieval and model behavior. Preserve the ledger and treat the current run as experimental evidence, not a release certification.

The next required experiment is the current-kernel baseline benchmark listed in `qd_state.yaml`. The baseline must be recorded before the evidence-relation and dual-key verdict rearchitecture, so later changes can be compared against the machine that actually existed.

## Baseline benchmark

The benchmark runner has two lanes:

- **Live:** repeated Qwen plus Tavily runs across the required claim categories.
- **Controlled:** fixed evidence for duplicate-family and evidence-order probes.

```powershell
py benchmarks/baseline_v1.py --live-repeats 1 --controlled-repeats 1 --shuffle-limit 3
```

Generated artifacts are written under `benchmark_results/baseline_v1/` and are ignored by Git. See [`benchmarks/README.md`](benchmarks/README.md) before running the full baseline.

The benchmark records current behavior. It does not certify correctness, and expected failures are not regressions.

## Project evidence classes

The documents under `docs/` intentionally separate:

- Constitution: chosen commitments and boundaries
- Build Status: merged implementation summary
- Working Hypotheses: proposed but unearned architecture
- Established Results: results supported by stated tests or observations
- Failed Hypotheses: attractive ideas that did not survive scrutiny
- Open Problems: questions without an adopted answer
- Decision Log: explicit choices, reversals, and their reasons

No architectural proposal becomes an established result merely because it appears in a plan or prompt.

## Current build freeze

Until the baseline benchmark is recorded, work is limited to reproducibility, benchmark instrumentation, and fixes required to make measurements trustworthy. Idle recombination, minority-live lanes, additional cognitive organs, and rover cognition integration remain parked.
