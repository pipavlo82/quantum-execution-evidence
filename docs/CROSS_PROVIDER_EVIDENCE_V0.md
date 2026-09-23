# Cross-provider evidence model v0

This additive, finite model gives the existing IBM direct and Moth Comet live
captures a common evidence projection. It consumes their preserved bytes
offline; it makes no new QPU request and reads no credentials. It does not
replace either profile, create a new RVR profile, or certify a provider.

## Common contract

`qev.cross-provider-evidence.v0` has six closed top-level fields: `schema`,
`identity`, `common`, `capabilities`, `nativeLayers`, `providerSpecific`.

`identity` contains provider adapter ID, external claim digest, evidence-set
digest, `LOCAL_UNSIGNED_CLAIM` authority and the complete finite member
inventory. Every present member carries SHA-256 and byte length; every absent
member is explicitly `MISSING`. The evidence-set digest covers the role-sorted
inventory, including missing markers. The claim and inventory use sorted-key,
compact, ensure-ASCII JSON without a newline. Raw member hashes cover the exact
bytes. These are new model identities, not native RVR digests or ReceiptOS roots.

`common` contains `consistency`, `issues`, `providerAuthentication` and
`observation`. Observation is populated only after the provider relation
succeeds. It includes explicitly upstream-reported job/backend/completion,
consistency with the local request, and independently recomputed sample width,
requested/observed shots, unique bitstrings and counts digest. Counts use
`sha256-sorted-compact-ascii-json-counts-v0`; this does not equate shot order,
bit semantics, circuits, experiments or distributions across providers.

`ORDERED_SHOTS` and `COUNTS_ONLY` are distinct sample representations. Shared
counts fields never imply a shared circuit or an interchangeable sample.
The two captures have different requests, widths and shot counts. This model
provides no cross-provider quality score, entropy ranking or distribution test.

## Evidence state is separate from capability

All observed issues remain in separate arrays, including simultaneous failures:

| Issue class | Meaning | Summary / CLI exit |
| --- | --- | --- |
| malformed | Invalid shape/type/encoding; admission not satisfied | MALFORMED / 2 |
| contradiction | Available valid evidence disagrees with a commitment/relation | CONTRADICTED / 1 |
| unavailable | Local source/runtime cannot execute verification | CANNOT_RECOMPUTE / 3 |
| missing | Required evidence absent or a required relation unresolved | INCOMPLETE / 3 |
| none | Supplied profile relation passed | CONSISTENT / 0 |

Summary precedence follows this table; it never deletes lower-priority issues.
Preflight scans all role bytes and anchors before provider evaluation. A missing
file cannot hide a contradiction in another present committed member. The
legacy provider evaluators retain their original first-failure behavior; the
new projection does not claim an exhaustive list of semantic contradictions.
Unsupported providers, extra roles, nonbyte/oversize payloads and invalid outer
JSON are rejected at the outer boundary (CLI 2). Source-lock failure is CLI 3.

Capability absence is not a malformed capture or a proven contradiction. In
particular, Moth's unavailable circuit bytes, shot order and measurement map
do not prevent counts consistency. An unresolved commitment encoding is not
a proven hash mismatch. A self-reported certificate is not authentication.

## Provider-specific capabilities and executed layers

| Surface | IBM direct | Moth Comet |
| --- | --- | --- |
| Raw evidence | SDK-decoded operations and ordered bitstrings | Preserved HTTP entity bodies and counts |
| Circuit bytes | Captured operation snapshots | UNAVAILABLE; reported hash only |
| Shot order | Captured BitArray sequence | UNAVAILABLE; counts are not a sequence |
| Measurement map | Finite logical/ISA/intent map checked | UNAVAILABLE; no inferred hardware map |
| Ideal circuit relation | Native TSEI, finite two-qubit ideal relation | UNAVAILABLE |
| Native RVR | Executed per evaluation, actual outcome/digests | NOT_INTEGRATED |
| Native ReceiptOS | Created and verified after successful IBM relation | NOT_INTEGRATED |
| Provider authentication | NOT_ESTABLISHED | NOT_ESTABLISHED |

Every capability has a status, an evidence basis and a scoped detail. Basis
distinguishes `INDEPENDENTLY_RECOMPUTED`, `UPSTREAM_REPORTED`, `LOCAL_INFERENCE`,
`PROFILE_LIMIT` and `NONE`. Moth counts/pulse hash encoding remains a local
inference from an observed match, not an audited upstream implementation.
Its commitment timing, seed provenance, nonempty extraction and entropy
qualification remain NOT_ESTABLISHED. The actual capture requested 32 bytes
and delivered **0 bytes**, grade `hardware-insufficient-entropy`; witness
S = 2.2890625 is conditional arithmetic, not RNG certification.

`nativeLayers` records actual executions and their existing-profile scope.
IBM RVR and TSEI can execute on partial or refuted evidence; `EXECUTED` does not
mean success. ReceiptOS is attempted only after VERIFIED IBM semantics. A root
proves its defined byte commitment, not physical execution or provider identity.
Moth never calls those native layers. The new cross-provider report itself is
not a native RVR receipt, a TSEI proof or a ReceiptOS-root-bound artifact.

Authentication is always NOT_ESTABLISHED in v0: neither adapter implements a
separate cryptographic attestation verifier. Supporting one requires a new
explicit contract, not changing a supplied report label. No physical QPU,
sampler independence, cryptographic randomness or production security follows.

## Replay and trust boundary

`evaluate(provider, claim, payloads)` accepts only a provider ID, a separate
local unsigned claim and a role-to-bytes map. The map is bounded to 8 MiB total,
4 MiB per member, and a finite role allowlist. No URL is fetched. Moth's v0 role
names are those of its pinned existing capture profile, so this is deliberately
not an arbitrary Moth-job importer. Claims are local anchors, not signatures.

`replay(saved, provider, claim, payloads)` regenerates the entire projection
from these external inputs, executes applicable native layers again, and
compares all fields with type-sensitive canonical JSON equality. Forged
capabilities, provenance labels, results and native statuses fail. A schema
check, stored PASS, attached certificate or source hash alone is insufficient.

```
python -B -m qev.cross_cli demo
python -B -m qev.cross_cli demo --provider ibm-direct > cross-ibm.json
python -B -m qev.cross_cli replay --provider ibm-direct --artifact cross-ibm.json
python -B -m qev.cross_cli demo --provider moth-comet > cross-moth.json
python -B -m qev.cross_cli replay --provider moth-comet --artifact cross-moth.json
python -B -m qev.cross_cli sources
python -B -m qev.cross_mutations
```

Without custom inputs, the explicitly selected preserved fixture claim is the
external anchor. A custom capture requires both `--capture` and `--claim`.
Only source-locked local code and bytes are used. Python 3.12+ and the existing
Bun/Node runtimes suffice; no Qiskit, provider SDK or provider account is needed.

## Preservation and validation

All earlier profiles, fixtures, vendor files and runtime source files remain
byte-identical. The new files use a separate finite lock, generated by
`python -B -m tools.pin_cross_profile`. The existing source lock is refreshed
only for the README and CI additions; its inventory and native dependency
identities are unchanged. Neither lock authenticates authorship.

Tests cover both actual captures; native execution and nonintegration;
missing/contradictory/malformed evidence; unavailable runtimes; source-lock
closure; claim substitution; type confusion; report tampering; ordering;
and rejection of unknown roles and paths. Twelve exact-site source mutations
exercise eight stored-projection comparisons and four issue-classification
branches. Each requires three valid controls to remain accepted; crashes,
unapplied changes and broken controls never count as kills. This mutation scope
does not replace the legacy IBM/Moth relation mutation gates.

CI runs normal and optimized suites, every legacy gate, new report/replay and
mutation gates, and normal/repeat/optimized byte equality. Validation shares
implementation authorship; independent authorship is not claimed.
