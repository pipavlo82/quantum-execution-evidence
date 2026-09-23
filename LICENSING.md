# Licensing

Repository-authored Quantum Execution Evidence material is licensed under the
Apache License, Version 2.0, unless a file or directory is explicitly identified
below as third-party or preserved upstream evidence.

- Root license text: [LICENSE](LICENSE)
- Attribution and scope notice: [NOTICE](NOTICE)
- SPDX identifier for the repository-authored grant: `Apache-2.0`

This grant covers repository-authored runtime code, profiles, tests, tooling,
synthetic fixtures, project documentation, configuration, and locally authored
claim/manifest metadata. It does **not** relicense third-party material merely
because that material is stored in this repository. A more specific license or
rights notice attached to a file or directory controls for that material.

## Preserved provider evidence

The 15 IBM live-capture files named as keys in
`fixtures/live-capture-v1/seed-manifest.json` are preserved historical evidence.
Their inclusion is not a claim that QEV owns or relicenses provider-originated
content. Repository-authored wrapper material such as the independent QEV claim
and seed manifest remains under the root Apache-2.0 grant.

Files under `fixtures/moth-comet-v0/capture/` are preserved Moth/API execution
evidence. `docs/moth-comet-v0/openapi.raw.json` is a preserved upstream OpenAPI
snapshot. Those preserved upstream materials are not relicensed by the root
LICENSE. Repository-authored Moth adapters, profiles, tests, claims, analysis and
documentation remain under Apache-2.0.

## Vendored Semantic ABI

Files under `vendor/semantic-abi/` originate from the pinned
`trustless-ai/semantic-abi` source snapshot.

- `vendor/semantic-abi/LICENSE` is the upstream Apache-2.0 license text for the
  applicable code.
- `vendor/semantic-abi/schema/LICENSE-CC0.txt` is the upstream CC0 text for the
  applicable schema material.

The exact byte identities and upstream commit are recorded in
`qev/source_inventory.py` and `sources.lock.json`.

The 16 records in `docs/reference-pins.json` are inherited reference metadata,
not a license grant or execution inventory. Referencing an upstream project does
not grant QEV permission to relicense that project's material.

## Vendored RVR v0

Files under `vendor/rvr-v0/` originate from pinned commit
`549a7e150ddc75df88dc90ee93f331fea7464567` of
`pipavlo82/recomputable-verification-receipts`.

`vendor/rvr-v0/LICENSE` preserves the upstream license bytes. The vendored
adapter and Verification Profile Manifest schema retain that upstream license;
QEV-authored profiles and adapters use the root Apache-2.0 grant.

## Vendored ReceiptOS v0

Files under `vendor/receiptos-v0/` originate from pinned commit
`45b46bf7df3a60b32583291f577a36bf19d22f00` of
`pipavlo82/crystal-receipt`.

`vendor/receiptos-v0/LICENSE` preserves the upstream Apache-2.0 license bytes.
The vendored ReceiptOS implementation retains its upstream license. QEV-specific
bridges, profiles and tests use the root Apache-2.0 grant.

## Vendored TSEI v0

Files under `vendor/tsei-v0/` originate from pinned commit
`45b46bf7df3a60b32583291f577a36bf19d22f00` of
`pipavlo82/crystal-receipt`.

`vendor/tsei-v0/LICENSE` preserves the upstream Apache-2.0 license bytes. The
vendored generic transformation-stability implementation, conformance data and
specification retain their upstream license. QEV-specific profiles and bridge
files use the root Apache-2.0 grant.

## What this change does not do

Selecting Apache-2.0 for repository-authored QEV material does not alter frozen
evidence bytes, vendor licenses, upstream copyrights, provider terms, or the
technical evidence claims made by any profile. It also does not imply that
captured IBM/Moth data, an upstream OpenAPI document, or referenced repositories
are owned by or relicensed by QEV.

The 28-file vendor inventory includes licenses and data as well as code; see
[the source map](docs/INTEGRATION_MAP.md#source-identities).
