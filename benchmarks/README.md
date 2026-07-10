# QD Baseline Benchmark v1

This directory records the behavior of the current kernel **before** the planned evidence-relation, clean-room classification, dual-key verdict, confidence, and family-deduplication changes.

The benchmark is descriptive. It does not certify truth performance, and expected failures are not regressions.

## Two lanes

### Live lane

Runs the unchanged kernel against real Tavily retrieval and the configured Ollama model. Repeated runs expose:

- verdict variance,
- confidence variance,
- retrieval-set variance,
- satire and quotation handling,
- neutral reporting,
- contested claims,
- loaded wording,
- stale evidence,
- compound claims.

### Controlled lane

Uses fixed synthetic evidence excerpts through a duck-typed retriever. It isolates:

- one source family repeated once versus three times,
- all six orders of one identical three-item evidence set.

The controlled excerpts are benchmark stimuli, not claimed real-world sources.

## Run

From the repository root with Ollama running:

```powershell
git switch q/baseline-benchmark
py -m pytest -q
```

Live plus controlled baseline:

```powershell
$env:TAVILY_API_KEY='tvly-...'
py benchmarks/baseline_v1.py
```

A smaller first pass:

```powershell
py benchmarks/baseline_v1.py --live-repeats 1 --controlled-repeats 1 --shuffle-limit 3
```

Controlled-only does not require Tavily:

```powershell
py benchmarks/baseline_v1.py --mode controlled
```

Each run creates a timestamped directory under:

```text
benchmark_results/baseline_v1/
```

The directory contains:

- `manifest.json` — model, git state, environment, case-manifest hash, and run settings.
- `results.jsonl` — one append-only record per attempted kernel evaluation.
- `summary.json` and `summary.md` — descriptive aggregation.
- `live_ledger.db` and/or `controlled_ledger.db` — the kernel's ordinary append-only event ledger.

The runner writes the summary in a `finally` block, so partial runs remain inspectable after an interruption or error.

## Interpretation rules

- A different live evidence-set hash is retrieval variance, not automatically model inconsistency.
- Different verdicts for one fixed evidence set show model or kernel variance.
- Different outcomes across fixed-evidence orders indicate possible path dependence.
- A confidence or verdict change between one and three identical copies shows that repetition is affecting the kernel before family deduplication exists.
- Do not rewrite the baseline after architecture changes. Create a new benchmark version and compare.
