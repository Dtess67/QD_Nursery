# Archived — pre-four-state endorsement diagnostics

These scripts are **historical evidence for the Boolean-era kernel** (the
`source_endorses_claim: bool` label and its single-call endorsement read,
kernel ≤ v0.1.3). They are the reproducible record behind the July 8, 2026
endorsement context-contamination investigation and the ledger scars it
produced; the investigation itself is documented in
[`2026-07-08_endorsement_investigation.md`](2026-07-08_endorsement_investigation.md).

Their contents are preserved unchanged. They are **not expected to run**
against the four-state schema (kernel v0.1.4+): `Evidence.source_endorses_claim`
and `QDKernel._read_endorsement` no longer exist, replaced by
`Evidence.source_relation` (`SUPPORTS` / `REFUTES` / `NEUTRAL` / `UNCLEAR`)
and a clean-room classifier (`QDKernel._classify_source_relation` /
`_read_relation`).

Do not port these scripts or rewrite their conclusions — the point of this
archive is that the evidence stays exactly as it was when the decision was
made. The clean-room cure they validated (`endorsement_cleanroom.py`, 6/6
correct) is what the production classifier is built on.
