# Integration map

Current status is centralized in [README](../README.md#current-project-status-and-architecture).
This map names executed mechanisms and their exact scope including the additive Moth counts-native RVR profile.
An executed mechanism is not automatically a successful or authenticated claim.

| Component | Executed surface / command | Boundary |
| --- | --- | --- |
| Synthetic QEV | `qev/checker.py`; `python -B -m qev demo` | `quantum-evidence.v0`: request, bytes, mappings, counts, integer postprocessing |
| Semantic ABI | `qev/semantic_link.mjs`; included in synthetic checks | Vendored declaration compatibility, not claim truth |
| Native RVR | `qev/rvr_native.py`; `python -B -m qev rvr-demo` | `rvr-qev-preserved-observation-v0`; outcome and recomputation differ |
| Legacy ReceiptOS | `qev/receiptos_bridge.ts`; `python -B -m qev receiptos-demo` | Native capsule/provenance builders and proof-ID helpers; local root/summary/proof assembly, no independent native root-verifier invocation |
| Native TSEI artifact preservation | `qev/tsei_bridge.ts`; `python -B -m qev tsei-demo` | `qev-rvr-artifact-preservation-v0`; normative/evidence/variant projections |
| Native TSEI layout relation | `qev/quantum_transpile_tsei_bridge.ts`; `python -B -m qev quantum-transpile-demo` | `qev-quantum-layout-transpilation-v0`; ordered gates/measurements under a layout bijection |
| Provider binding | `qev/provider_binding.py`; `python -B -m qev provider-binding-demo` | Eight consistency axes; assigned job ID retained but not independently compared by this legacy verifier |
| IBM recorded adapter | `qev/ibm_runtime_adapter.py`; `python -B -m qev ibm-runtime-demo` | Synthetic adapter conformance; caller-origin circuit/transpiler labels remain caller-origin |
| IBM live replay | `qev/live_native.py`, `qev/live_relation.py`; `python -B -m qev live-demo` | `rvr-qev-live-capture-replay-v1`; independent claim/job/raw anchors and native RVR |
| IBM live ideal TSEI | `qev/live_tsei_bridge.ts`, `qev/live_math.py`; included in live replay | `qev-live-ideal-two-qubit-isa-v1`; finite exact ideal full-operator and measurement relation |
| IBM live ReceiptOS | `qev/live_receiptos_bridge.ts`, `qev/live_portable.py`; `python -B -m qev live-replay live-export.json` after export | Actual native root/verifier/summary/portable functions; complete RVR/capture attachment checked |
| Moth counts | `qev/moth_comet.py`, `qev/moth_replay.py`; `python -B -m qev.moth_replay` | `qev-moth-comet-counts-v0`; no native RVR/TSEI/ReceiptOS for this counts profile |
| Moth native RVR | `qev/moth_rvr.py`, `qev/moth_rvr_relation.py`; `python -B -m qev.moth_rvr_cli demo` | `rvr-qev-moth-counts-v0`; counts-only native receipt/replay; insufficient-entropy delivery is a separate observation |
| Cross-provider model | `qev/cross_provider.py`, `qev/cross_adapters.py`; `python -B -m qev.cross_cli demo` | `qev-cross-provider-evidence-v0`; explicit capabilities and actual per-provider native results, not a new native receipt |
| PRF | SOURCE_PINNED_REFERENCE / NOT_INTEGRATED | No PRF adapter runs |
| RSI / RBCF | SOURCE_PINNED_REFERENCE / NOT_INTEGRATED | No RSI admission/profile execution |
| Chronicle | SOURCE_PINNED_REFERENCE / NOT_INTEGRATED | No history/admission claim |
| PQ receipt profile | SOURCE_PINNED_REFERENCE / NOT_INTEGRATED | No signature verifier; key attribution would not itself authenticate a QPU |

## Source identities

| Vendored family | Exact upstream commit | Files |
| --- | --- | ---: |
| Semantic ABI | `d15c666dfccff17f7350fe97d2fc7b71cb2cbaee` | 4 |
| RVR v0 | `549a7e150ddc75df88dc90ee93f331fea7464567` | 3 |
| ReceiptOS v0 | `45b46bf7df3a60b32583291f577a36bf19d22f00` | 12 |
| TSEI v0 | `45b46bf7df3a60b32583291f577a36bf19d22f00` | 9 |

The 28 files include licenses, schemas and conformance data as well as executable
code. Exact source paths and hashes are in [source_inventory.py](../qev/source_inventory.py)
and [sources.lock.json](../sources.lock.json). The latter locks 214 local files.
[Cross-provider sources](../profiles/cross-provider-evidence-v0/sources.json)
separately lock eight additive files.
[Moth native RVR sources](../profiles/rvr-qev-moth-counts-v0/sources.json) lock
13 additive files; its native manifest also pins the unchanged counts runtime
and three RVR vendor files. No older profile identity is changed.

[reference-pins.json](reference-pins.json) retains 16 inherited source-reference
records. Those records are historical metadata; they do not control runtime
integration status. Some upstream material, including license/spec bytes, was
subsequently vendored separately under the explicit inventories above. A
reference record is neither a fresh upstream-source verification nor execution.

## Composition and limits

IBM live evaluation runs native TSEI within the live relation and native RVR
over the committed evidence. Live export then packages the bundle with native
ReceiptOS functions; replay checks the saved artifact. Cross-provider IBM only
attempts ReceiptOS after VERIFIED semantics, whereas the standalone live export
can represent REFUTED/UNVERIFIABLE outcomes with a valid root. The original Moth
counts and cross-provider v0 adapters remain unchanged and make no native RVR,
TSEI or ReceiptOS call. The separate [Moth RVR path](MOTH_COUNTS_RVR_V0.md)
executes native receipt primitives over the counts relation. ReceiptOS packaging
and TSEI are not integrated for that new profile.

`providerAuthentication = NOT_ESTABLISHED` on both captured paths. Neither
source identity, a compatible Semantic ABI declaration, native execution,
root validity nor counts consistency establishes hardware authenticity or
entropy. See [the precise profile distinctions](DOCUMENTATION_AUDIT.md).
