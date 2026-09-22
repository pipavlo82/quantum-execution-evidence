# Integration map

This map records **evidence status**, not product marketing. Repository existence, a source pin, or a compatible declaration never upgrades a component to an executed integration.

| Component | Status in this repository | Boundary |
|---|---|---|
| QEV finite verifier | **EXECUTED** | Request binding, byte integrity, raw observations -> counts -> integer result |
| Semantic ABI | **EXECUTED** | Exact vendored linker; declaration compatibility only |
| RVR / ERC-8404 | **EXECUTED — native profile rvr-qev-preserved-observation-v0** | Exact vendored RVR v0 primitives + QEV profile; implementation diversity remains NOT_ESTABLISHED |
| ReceiptOS / Crystal Receipt | **SOURCE_PINNED_REFERENCE / NOT_INTEGRATED** | QEV JSON is not an Evidence Capsule or native receipt |
| TSEI | **SOURCE_PINNED_REFERENCE / NOT_INTEGRATED** | Bit-permutation controls here are not a native TSEI evaluation |
| Protected Relation Fixtures | **SOURCE_PINNED_REFERENCE / NOT_INTEGRATED** | PRF ideas inform adversarial fixtures; no PRF adapter runs |
| RSI / RBCF | **SOURCE_PINNED_REFERENCE / NOT_INTEGRATED** | No RSI admission/profile/adapter execution |
| Chronicle | **SOURCE_PINNED_REFERENCE / NOT_INTEGRATED** | No Chronicle admission or history claim |
| PQ receipt profile | **SOURCE_PINNED_REFERENCE / NOT_INTEGRATED** | Signature/key attribution is separate from QPU provenance |
## Exact reference pins

`docs/reference-pins.json` contains the 16 inherited source identities used to map the next seams. Those referenced bytes are **not vendored and not executed** by this repository.

The only vendored executable external surface is Semantic ABI at commit:

`d15c666dfccff17f7350fe97d2fc7b71cb2cbaee`

The exact vendored file identities are hard-coded in `qev/source_inventory.py` and reproduced in the finite source lock.

## Semantic boundary

The result of the QEV deterministic relation may be locally established over supplied bytes even when a Semantic ABI edge is rejected, malformed, or unavailable. Conversely, a compatible Semantic ABI edge cannot establish provider honesty, authentic QPU execution, entropy, distribution equality, or device certification.

A future composition should preserve the native outcome vocabulary of each layer instead of projecting everything into one boolean.
