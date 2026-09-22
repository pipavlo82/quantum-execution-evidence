# Licensing

No blanket repository license has been selected for newly authored Quantum Execution Evidence code in this initial experimental snapshot. Do not infer permission to copy, redistribute, sublicense, or relicense repository-authored files beyond rights granted by applicable law or a later explicit license.

Vendored upstream material keeps its own license boundaries.

## Vendored Semantic ABI

Files under `vendor/semantic-abi/` originate from the pinned `trustless-ai/semantic-abi` source snapshot.

- `vendor/semantic-abi/LICENSE` is the upstream Apache-2.0 license text for the applicable code.
- `vendor/semantic-abi/schema/LICENSE-CC0.txt` is the upstream CC0 text for the applicable schema material.

The exact byte identities and upstream commit are recorded in `qev/source_inventory.py` and `sources.lock.json`.

Source-pinned references in `docs/reference-pins.json` are references only; their bytes are not copied into this repository.

## Vendored RVR v0

Files under `vendor/rvr-v0/` originate from pinned commit `549a7e150ddc75df88dc90ee93f331fea7464567` of `pipavlo82/recomputable-verification-receipts`.

`vendor/rvr-v0/LICENSE` preserves the upstream license bytes. The vendored adapter and generic Verification Profile Manifest schema are used as native RVR v0 primitives; repository-authored QEV profile files remain under the root-license status described above.
## Vendored ReceiptOS v0

Files under `vendor/receiptos-v0/` originate from pinned commit `45b46bf7df3a60b32583291f577a36bf19d22f00` of `pipavlo82/crystal-receipt`.

`vendor/receiptos-v0/LICENSE` preserves the upstream Apache-2.0 license bytes. The vendored ReceiptOS files are used to execute the existing receipt-root, Evidence Capsule, Provenance Summary, and portable-proof-object semantics. Repository-authored QEV-to-ReceiptOS adapter files remain under the root-license status described above.

## Vendored TSEI v0

Files under `vendor/tsei-v0/` originate from pinned commit `45b46bf7df3a60b32583291f577a36bf19d22f00` of `pipavlo82/crystal-receipt`.

`vendor/tsei-v0/LICENSE` preserves the upstream Apache-2.0 license bytes. The vendored generic transformation-stability core, comparator, conformance vectors, and standalone TSEI v0 specification are used as the native preservation mechanism. QEV-specific profile and bridge files remain under the root-license status described above.
