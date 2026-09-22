# Next native RVR step

Status: **NOT INTEGRATED**.

The current QEV result is not an RVR receipt and must not be relabeled as one. The inspected RVR generic profile uses its own canonical encoding and verification relation; QEV's integer-bearing observation package does not satisfy that profile merely because it is deterministic to re-check.

A native integration should be additive and profile-defined, without changing the generic RVR core.## Required work

1. Define a Quantum Execution Evidence Verification Profile with an explicit canonical byte contract for request identity, ordered observation identity, mapping identity, counts, deterministic post-processing, provider-evidence references, and unresolved physical/entropy claims.
2. Define which dependencies are required for recomputation and how their exact bytes or immutable identities are resolved.
3. Map the QEV deterministic result into the native RVR separation between verification outcome and recomputation status.
4. Add vectors where the same declared procedure has different valid samples; both must remain valid without claiming identical outcome reproduction.
5. Add vectors for missing evidence, contradictory evidence, unsupported claim elevation, profile drift, and changed mapping/provider/job identities.
6. Execute the actual native RVR adapter against the profile and preserve its native result without a local compatibility shim pretending to be RVR.Only after that pass should ReceiptOS package the native RVR artifact while preserving upstream byte identities. TSEI/RSI/PRF integration should follow their own native contracts, not be inferred from this profile's existence.