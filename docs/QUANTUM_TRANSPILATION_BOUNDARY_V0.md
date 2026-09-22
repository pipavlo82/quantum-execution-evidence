# Quantum layout transpilation boundary v0

This profile is the first concrete quantum transformation boundary in QEV.

It proves a deliberately narrow relation: an ordered logical `qev-lines.v0` circuit is preserved when it is relabeled onto a bijective physical-qubit layout and the physical artifact independently normalizes back to the exact same ordered logical gates and measurement relation.

Protected relation: `EXACT_ORDERED_GATE_AND_MEASUREMENT_EQUIVALENCE_UNDER_LAYOUT_BIJECTION`.

Two different physical layouts may therefore be TSEI `stable` while their physical-circuit digests differ.

## What v0 catches

- a changed logical gate after layout transpilation -> `violation`;
- a measurement mapping that cannot normalize -> `unresolved / target_recompute_failed`;
- a non-bijective physical layout -> `unresolved / target_recompute_failed`.

Unresolved is intentionally distinct from violation.

## Execution binding

The v0 sidecar binds the physical-circuit digest to the supplied request/provider/backend/job identifiers. Its authority is explicitly `SUPPLIED_SIDECAR_NOT_PROVIDER_AUTHENTICATED`.

This is not yet provider evidence that the named physical circuit actually executed.

## Non-claims

v0 does not establish arbitrary gate-optimization equivalence, routing/SWAP equivalence, approximate unitary equivalence, physical QPU execution, provider authenticity, entropy, or cryptographic randomness.

Those require additional transformation profiles or real provider execution artifacts.