# Licensing

No blanket repository license has been selected for newly authored Quantum Execution Evidence code in this experimental repository. Do not infer permission to copy, redistribute, sublicense, or relicense repository-authored files beyond rights granted by applicable law or a later explicit license.

Vendored upstream material keeps its own license boundaries.

## Vendored Semantic ABI

Files under `vendor/semantic-abi/` originate from the pinned `trustless-ai/semantic-abi` source snapshot.

- `vendor/semantic-abi/LICENSE` is the upstream Apache-2.0 license text for the applicable code.
- `vendor/semantic-abi/schema/LICENSE-CC0.txt` is the upstream CC0 text for the applicable schema material.

The exact byte identities and upstream commit are recorded in `qev/source_inventory.py` and `sources.lock.json`.

The 16 records in `docs/reference-pins.json` are inherited reference metadata,
not a licensing or execution inventory. Some upstream license/spec bytes were
subsequently copied under the explicit vendor inventories below; the records
themselves confer no license or integration status.

## Vendored RVR v0

Files under `vendor/rvr-v0/` originate from pinned commit `549a7e150ddc75df88dc90ee93f331fea7464567` of `pipavlo82/recomputable-verification-receipts`.

`vendor/rvr-v0/LICENSE` preserves the upstream license bytes. The vendored adapter and generic Verification Profile Manifest schema are used as native RVR v0 primitives; repository-authored QEV profile files remain under the root-license status described above.
## Vendored ReceiptOS v0

Files under `vendor/receiptos-v0/` originate from pinned commit `45b46bf7df3a60b32583291f577a36bf19d22f00` of `pipavlo82/crystal-receipt`.

`vendor/receiptos-v0/LICENSE` preserves the upstream Apache-2.0 license bytes. The vendored ReceiptOS files are used to execute the existing receipt-root, Evidence Capsule, Provenance Summary, and portable-proof-object semantics. Repository-authored QEV-to-ReceiptOS adapter files remain under the root-license status described above.

## Vendored TSEI v0

Files under `vendor/tsei-v0/` originate from pinned commit `45b46bf7df3a60b32583291f577a36bf19d22f00` of `pipavlo82/crystal-receipt`.

`vendor/tsei-v0/LICENSE` preserves the upstream Apache-2.0 license bytes. The vendored generic transformation-stability core, comparator, conformance vectors, and standalone TSEI v0 specification are used as the native preservation mechanism. QEV-specific profile and bridge files remain under the root-license status described above.
## Additive live replay scope

New live replay modules, profile, documentation and tests follow this repository's
existing newly authored-code licensing status. No vendor license or source bytes
are changed. The 15 copied capture files retain their historical bytes and labels.

## Moth capture, common model and documentation audit

Repository-authored Moth/cross-provider adapters, tests and documentation retain
the same pending root-license status. Preserved Moth HTTP bodies and the upstream
OpenAPI snapshot are evidence/documentation observations, not newly authored
engine code and not a grant to relicense upstream material. Their inclusion
does not imply an upstream software license was inspected or granted.

This audit selects no license and changes no vendored license or captured bytes.
The 28-file vendor inventory includes licenses and data as well as code; see
[the source map](docs/INTEGRATION_MAP.md#source-identities).
