# Moth counts-native RVR v0

`rvr-qev-moth-counts-v0` is an additive native RVR profile over the preserved
Moth Comet counts capture. It executes the unchanged counts verifier and the
vendored RVR profile audit, schema admission, evidence closure, canonical
digests, evidence-member normalization and receipt-envelope verification.
The QEV adapter implements this profile's relation and replay orchestration;
it does not substitute the generic RVR evaluator's unrelated relation.

## Claim and evidence

The independent claim uses `rvr.claim.qev-moth-counts.v0`, names this profile
and the relation `preserved-counts-and-report-consistency`, and embeds the
original unsigned Moth capture claim with job ID, request and manifest anchors.
`providerAuthentication` is fixed to `NOT_ESTABLISHED`. The supplied claim is
a local trust input, not a provider signature. Replacing both claim and evidence
creates a different record.

The finite role inventory in
`profiles/rvr-qev-moth-counts-v0/roles.json` contains 17 members: the original
manifest and its 16 captured files. Names and the status-poll sequence are
pinned to this preserved capture. This is not an arbitrary new-job importer.
Poll chronology is not shot order. No ordered measurement member is required,
constructed, or inferred from the counts histogram.

Every role must occur exactly once in the native evidence set, either `PRESENT`
with raw-byte digest and decimal-string length, or explicitly `UNAVAILABLE`.
Payloads are base64-encoded exact captured bytes. Extraneous payloads,
duplicate/unknown roles, invalid base64 and byte-identity mismatches are rejected.
Input JSON has bounded size/depth, unique keys, finite numbers and scalar Unicode.
The case is limited to 4 MiB encoded JSON and 2,000,000 decoded payload bytes;
the individual counts parser retains its existing 4 MiB limit.

## Relation and separate states

Available claim anchors, manifest member identities and assigned-job fields are
checked before absent roles are considered. Their contradictions remain visible
alongside missing members. Malformed available JSON is rejected before a verdict.
With a complete consistent byte layer, the unchanged Moth loader and evaluator
check request/job/completion binding, counts/pulse/output hashes, shot totals,
marginals, Bell histograms/correlators, witness algebra and reported budget/output
arithmetic. The finite evaluator returns its first domain failure; this profile
does not claim exhaustive detection of every hidden contradiction in an
incomplete domain record.

| State | Meaning |
| --- | --- |
| `VERIFIED` | Preserved counts and report relation is consistent |
| `REFUTED` | An available admitted claim/manifest/job or counts-relation contradiction was found |
| `UNVERIFIABLE` | A decisive role is explicitly unavailable, or the counts verifier reports missing decisive data, without an observed contradiction |
| `REJECTED` | Malformed input, invalid evidence closure, forged saved result, claim/profile mismatch or invalid receipt; no RVR verification outcome is issued |
| `CANNOT_RECOMPUTE` | A committed PRESENT payload or pinned local source/dependency is unavailable or has the wrong identity |

The canonical result preserves separate `issues.missing` and
`issues.contradiction` lists, the counts verifier state/reason, observation and
fixed limitations. Malformed input never becomes `UNVERIFIABLE`. Source failures
never become domain `REFUTED`. RVR canonical JSON forbids numbers, so observation
metrics are decimal strings, including the existing verifier's Python float
rendering of witness algebra. Raw upstream numeric values remain in evidence bytes.

The preserved job verifies with 2048 shots, 2040 distinct 20-bit strings and
`S = 2.2890625`. Its request was for 32 bytes; delivery was **0 bytes**, marked
`EMPTY_BUDGET_LIMITED`, with separately retained upstream grade
`hardware-insufficient-entropy`. A `VERIFIED` receipt does not turn this into a
successful nonempty randomness extraction or a certified entropy estimate.

## Native receipt and replay

The native six-field receipt commits claim, normalized evidence set, verification
profile, outcome, reason and canonical result. Replay first checks the externally
selected claim and exact local profile, validates the receipt envelope, and
re-evaluates the saved evidence. Rehashing a fabricated saved verdict is insufficient.
An optional candidate case is evaluated only after the saved verdict is checked.
The same claim is required for both. `REPRODUCED` and `DIVERGED` compare native
identities and remain distinct from `VERIFIED`, `REFUTED` and `UNVERIFIABLE`.
Evidence-member list order is normalized by native RVR; payload bytes remain exact.

```sh
python -B -m qev.moth_rvr_cli sources
python -B -m qev.moth_rvr_cli demo --output moth-rvr.json
python -B -m qev.moth_rvr_cli replay --artifact moth-rvr.json --claim profiles/rvr-qev-moth-counts-v0/claim.json
python -B -m qev.moth_rvr_mutations
```

`demo` may also emit JSON to stdout. `replay` always requires `--claim` and
optionally accepts `--candidate` containing claim/evidenceSet/payloadsBase64.
Exit codes: 0 verified (inspect recomputationStatus separately), 1 refuted,
2 rejected, 3 unverifiable or cannot recompute. Missing artifact/claim files
are CLI admission failures; unavailable committed payloads are replay failures.

## Source closure and falsification

`profiles/rvr-qev-moth-counts-v0/sources.json` covers 13 additive source/profile,
test, specification and builder files. The native manifest separately pins its
transitive Python runtime dependencies and the three unchanged RVR vendor files.
It commits the conformance inventory, source mutation harness and tests. All are
checked before native vendor code is executed; conformance files are required by
this implementation's full profile audit even though their manifest flag is false.
The lock is a checkout consistency boundary, not an independently authenticated
software supply chain. A saved bundle also commits the complete profile identity.

Seven source mutants disable manifest/request anchors, member identity,
assigned-job binding, missing/contradiction outcomes and counts-refutation
propagation. Three positive controls per mutant preserve the captured record,
payload-map order variation and counts-key/JSON representation variation.
Crashes, unapplied mutations and broken controls are failures, never kills.
Tests additionally cover native envelope/closure attacks, external claim
substitution, fabricated saved results, missing sources and network-free replay.
CI runs both Python versions and normal/optimized tests, with exact-byte comparison
of repeated and optimized export, replay and mutation outputs.

## Evidence boundaries and compatibility

No provider cryptographic receipt, signature or attestation is available here.
Provider/backend/job/completion labels remain upstream reports. Circuit bytes,
physical measurement mapping and shot acquisition order are not established.
Commitment preimage encoding remains unresolved; timing, seed provenance and
nonempty Toeplitz extraction remain unestablished. Witness arithmetic does not
certify entropy, hardware authenticity, device independence or compiler correctness.

ReceiptOS and TSEI are not integrated for this new counts profile. Existing IBM
native paths, original Moth counts profile and cross-provider v0 are unchanged.
The old Moth profile's native nonintegration label still describes that old
profile. Cross-provider v0 still runs its existing counts path; it does not
invoke this new RVR profile or inherit its receipt. Current architecture is:

```text
Moth capture -> counts verifier -> native RVR (this profile)
                              -> cross-provider model v0 (unchanged)
```

Next concrete work is to assess ReceiptOS packaging for this established RVR
bundle. Provider authentication is conditional on obtaining an independently
cryptographically verifiable provider receipt/signature/attestation. IBM circuit
support beyond its finite two-qubit profile is a separate later change.
