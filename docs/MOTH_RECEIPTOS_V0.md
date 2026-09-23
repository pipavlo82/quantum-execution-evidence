# Moth ReceiptOS portable packaging v0

`receiptos-qev-moth-counts-v0` packages the unchanged `rvr-qev-moth-counts-v0`
bundle into a native ReceiptOS evidence envelope, capsule summary and portable
proof object. It adds exact attachment binding and saved-artifact replay to
the existing counts-native RVR relation. It does not change the inner claim,
verdict, evidence, limitations or profile identity.

## Package and source identity

`qev.moth-portable-export.v0` is a closed object containing `schema`, `profile`,
`attachment`, `rvrReplay` and `nativeReceiptOs`. The attachment is the exact
input RVR bundle bytes, with ID `rvr-moth-counts-bundle`, media type
`application/json`, SHA-256 and canonical base64. The bundle includes the counts
capture members, native RVR receipt, claim, result and RVR verification profile.
The external claim is a separate replay input; it is never chosen from the bundle.

The packaging profile and its independent source lock live under
`profiles/moth-receiptos-v0/`. Nine additive files are locked; the lock excludes
itself. The profile pins its eight other files, the unchanged RVR profile and
RVR source lock, and all 12 ReceiptOS vendor files. The complete old RVR source
checker also runs before packaging/replay and before invoking the native bridge.
Missing or changed dependencies produce `CANNOT_RECOMPUTE`. Source pins identify
checkout bytes, not authenticated software authorship or a secure execution host.

The root-covered task description commits SHA-256 of the packaging profile's
sorted, indented, ASCII JSON plus LF (`qev.moth_comet.encode`). Replay requires
the saved profile to equal the locally selected profile. The profile is a QEV
packaging contract, not a new native RVR verification profile or a provider receipt.

## Executed native mechanisms

`qev/moth_receiptos_bridge.ts` calls the unchanged vendored ReceiptOS functions:
`computeReceiptRoot`, `verifyHandoffReceiptRoot`,
`createCapsuleSummaryFromEvidence` and `createPortableProofObjectV0`. The latter
executes the native capsule/provenance builders. Native source revision remains
`45b46bf7df3a60b32583291f577a36bf19d22f00`; no new upstream code is downloaded.

The QEV adapter supplies the envelope projection, exact inline attachment,
profile identity and independent claim. It does not locally reproduce the
native root algorithm or fabricate a successful native verification result.
`changes.diff_sha256` binds the exact attached bundle bytes, including captured
payloads. `changes.files_changed` names `inline:rvr-moth-counts-bundle`; these
historical envelope fields describe the attachment, not edits made to a provider.

The native root omits the entire top-level `anchor` field. Consequently, replay
also requires every anchor field to equal the profile's fixed local/off-chain,
unanchored, no-Merkle-proof values, except for the stored receipt root itself.
Native root validity alone does not enforce this boundary.

## Replay procedure

1. Check the finite source closure and admit bounded, duplicate-free JSON.
2. Check the closed export/profile/attachment fields, canonical base64 and exact
   attachment SHA-256; parse the attached bundle without rewriting its bytes.
3. Recompute native Moth RVR against the independent expected claim. The original
   saved RVR verdict must be recomputed, including rejection of rehashed forgeries.
4. Compare the complete recomputed RVR report to the saved `rvrReplay`.
5. Reconstruct the exact envelope from the bundle, raw-byte digest and selected
   packaging profile. Check the complete projection and fixed anchor fields.
6. Run native ReceiptOS verification anew, require a valid root, and compare
   the complete native verification result, summary and portable proof object
   with their saved counterparts.

`qev.moth-portable-replay.v0` keeps `receiptOs.rootStatus`, the full `rvr`
recomputation, its `observation` and `providerAuthentication` separate.
The existing Moth capture yields root `VERIFIED` and RVR `VERIFIED / REPRODUCED`,
with 32 bytes requested, **0 bytes delivered** and upstream grade
`hardware-insufficient-entropy`. Those values do not certify entropy or establish
nonempty randomness extraction. `REFUTED` and `UNVERIFIABLE` RVR bundles can also
have valid packaging roots; native capsule labels describe packaging surfaces.

## Admission, failures and limits

Malformed JSON, wrong field types, altered profiles, extra/missing attachment
fields, invalid base64, digest/root mismatches, changed projections and forged
saved verdicts are `REJECTED` with no successful replay outcome. Explicitly
unavailable inner evidence retains RVR `UNVERIFIABLE`; an unresolved committed
PRESENT payload retains `CANNOT_RECOMPUTE`. Missing Bun/native execution or
pinned dependencies also produce `CANNOT_RECOMPUTE`.

The exact attached bundle is limited to 2,000,000 bytes; the complete outer JSON
uses the existing 4 MiB bounded parser (depth 32, unique keys, finite numbers,
Unicode scalar strings). Creation and replay apply the same outer admission.
Canonical base64 is required; JSON representation changes to the attached bundle
produce a different attachment digest and ReceiptOS root even when native RVR
identities reproduce. Repackaging is a new packaging operation, not verification
of an earlier root. No online storage or external resolution of payloads occurs.

The ReceiptOS historical envelope requires a numeric authorization time.
This profile uses **0 as an explicit compatibility sentinel**; native
`proof.created_at` consequently equals `1970-01-01T00:00:00.000Z`. Neither field
is a capture/export/verification timestamp or proof of authorization. Execution
records and allowed actions are empty; authorization is not established. This
permits deterministic packaging of incomplete evidence without inventing a time.

`providerAuthentication` remains `NOT_ESTABLISHED`. Root integrity does not
authenticate Moth, a backend, hardware execution, shot order, circuit or physical
measurement provenance, commitment timing, seed provenance, min-entropy or general
compiler correctness. The native proof object's references are identifiers,
not network retrieval endpoints or on-chain attestations.

## Offline commands

Python 3.12+ and Bun 1.3.14 on PATH are sufficient for this path. Run from the
repository root. File-output options preserve exact bytes on Windows as well.

```sh
python -B -m qev.moth_receiptos_cli sources
python -B -m qev.moth_receiptos_cli demo --output moth-portable.json
python -B -m qev.moth_receiptos_cli replay --artifact moth-portable.json --claim profiles/rvr-qev-moth-counts-v0/claim.json
python -B -m qev.moth_rvr_cli demo --output moth-rvr.json
python -B -m qev.moth_receiptos_cli export --bundle moth-rvr.json --claim profiles/rvr-qev-moth-counts-v0/claim.json --output moth-portable.json
python -B -m qev.moth_receiptos_mutations
```

`demo` selects the existing fixture and its pinned independent claim. Both
custom `export` and `replay` require `--claim`. Exit codes: 0 VERIFIED, 1 REFUTED,
2 REJECTED, 3 UNVERIFIABLE or CANNOT_RECOMPUTE. Export can write a valid package
while returning 1 or 3 for its RVR outcome. Inspect both outcome and root status.

## Falsification and compatibility

Nine source mutants bypass attachment digest, root-covered envelope, actual
native root verification, saved RVR result, native verification/summary/proof
projections, packaging profile identity and independent-claim selection. Three
positive controls per mutant preserve complete VERIFIED, REFUTED and UNVERIFIABLE
packages. A crash, unchanged mutant, unapplied edit or broken control fails the
gate. Tests also cover stripped evidence, rehashed fabricated RVR results, false
authorization/anchor claims, source/runtime failures, CLI outcomes and exact bytes.
CI repeats export/replay/mutations normally and under `-O` and compares exact output.

Original IBM, Moth counts, Moth RVR and cross-provider v0 sources and profile bytes
remain unchanged. The inner RVR limit `receiptOS: NOT_INTEGRATED_FOR_THIS_PROFILE`
still describes that evaluator, which does not call ReceiptOS. This outer profile
adds ReceiptOS execution without rewriting the inner result. Cross-provider v0
still invokes its old Moth counts path; no capability is retroactively added.

The next distinct change can expose actual Moth native execution in a new version
of the common projection. Provider authentication remains conditional on obtaining
cryptographically verifiable provider evidence. No new QPU job or provider call
is required for this package, its tests or replay.
