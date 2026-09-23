# Quantum Execution Evidence

QEV is an experimental **offline verifier of preserved stochastic execution
evidence**. It includes a synthetic conformance corpus, one preserved IBM Runtime
capture, one preserved Moth Comet counts capture, and a provider-neutral evidence
projection. Replay uses local bytes; it does not regenerate a quantum outcome.

```text
recomputation of preserved evidence != repetition of a stochastic outcome
byte consistency != authenticated physical execution != entropy certification
```

## Current project status and architecture

This is the canonical project status, including the additive Moth counts-native
RVR implementation. Its verified base is merged PR #12:
`68c306b6b25d392f4de290e904f57e20fa3c0a0f` (2026-09-23 UTC).
[Base CI](https://github.com/pipavlo82/quantum-execution-evidence/actions/runs/35807258616)
passed on Python 3.12 and 3.13. PR #11 merged the documentation audit; PR #12
selected Apache-2.0 for authored material. These are exact checkpoints, not a
claim that this new feature is already merged. [Audit coverage](docs/DOCUMENTATION_AUDIT.md)
records frozen boundaries and the current additive extension.

| Path | What works now | Evidence boundary |
| --- | --- | --- |
| Synthetic QEV v0 | Independent caller request -> ordered bytes -> mapping -> counts -> integer result; native Semantic ABI declaration check | Synthetic procedure identity and deterministic postprocessing only |
| Native RVR v0 | Receipt envelope, profile audit, evidence closure, canonical result and recomputation | A different valid sample can be `VERIFIED + DIVERGED`; no hardware claim |
| Legacy ReceiptOS and TSEI | Capsule/provenance builders and proof-ID helpers; native RVR-artifact preservation and layout-bijection evaluation | Legacy ReceiptOS root/summary/proof assembly is partly local bridge code; each TSEI profile has its own relation |
| IBM direct live replay v1 (PR #8) | Captured intent/logical/ISA/returned snapshots and ordered shots -> native RVR + finite ideal TSEI -> native ReceiptOS export and saved-artifact replay | Exact two-qubit ideal relation; unsigned acquisition evidence |
| Moth Comet counts v0 (PR #9) | Preserved HTTP bodies -> request/job/hash/counts/witness/budget consistency | Counts only; no circuit bytes, shot order or established physical measurement map; native RVR/TSEI/ReceiptOS not integrated for this profile |
| Moth counts-native RVR v0 | Preserved counts capture -> native profile audit, evidence closure, receipt and independent-claim replay | `rvr-qev-moth-counts-v0`; counts consistency only; zero-byte delivery/insufficient-entropy grade preserved; no ReceiptOS/TSEI |
| Cross-provider model v0 (PR #10) | Both captures -> common identity/observation/issues + explicit capabilities + actual native-layer results; complete report replay | Comparable evidence fields, not equivalent circuits, distributions, trust scores or a new native receipt |

The [integration map](docs/INTEGRATION_MAP.md) maps every layer to its code,
commands and source pins. PRF, RSI/RBCF, Chronicle and PQ remain references only.

### IBM path

The saved IBM job is `dapdeqcak42c73cid5qg`, reported backend `ibm_fez`, with
256 ordered shots and counts `00=119, 01=2, 10=10, 11=125` in `c1c0` order.
Replay checks independent claim anchors, request/job agreement, raw bytes,
histogram and logical/submitted/returned measurement maps. Native TSEI compares
the complete ideal two-qubit operators in Q(zeta_8), modulo one global phase,
under the finite angle-literal map. Native RVR gives `VERIFIED / REPRODUCED` for
the preserved sample; the live ReceiptOS bridge binds the exact RVR bundle and
its capture payloads and verifies the saved export's root and projections.

The legacy `ibm-runtime-demo` still exercises a synthetic IBM-shaped fixture.
The separate `live-demo`/`live-replay` path checks the preserved live capture.
Provider execution binding is consistency over supplied fields; the legacy
binding alone does not compare an assigned job ID to an independent expected ID.
The live profile supplies that additional claim/job binding.

### Moth path

The saved Moth job is `4daf7153-f837-4f5a-bf65-a0525bd9dd7a`. Its provider reports
`ibm_kingston` and provider job `dapgt48r7bnc73b3ei0g`; those are upstream claims.
QEV recomputes 2048 shots, 2040 distinct 20-bit strings, marginals, four witness
histograms/correlators and `S = 2.2890625` from preserved counts. The request asked
for 32 output bytes and the response delivered **0 bytes**, with upstream grade
`hardware-insufficient-entropy`; it contains an `entropy_report`, no certificate.

Counts/pulse hash encoding is a local inference from matching hashes. Circuit
hash agreement does not reveal its preimage. Commitment encoding remains
unresolved, prior publication/timing and seed provenance are not established,
and empty output does not exercise nonempty Toeplitz extraction. Witness and
reported-budget arithmetic do not certify entropy or physical bit mapping.

The separate [counts-native RVR profile](docs/MOTH_COUNTS_RVR_V0.md) now wraps
this relation in a native receipt and re-evaluates saved artifacts against an
independently selected claim. The captured record is `VERIFIED / REPRODUCED`
with `hardware-insufficient-entropy` and zero-byte output retained separately.
No shot order is required. The original counts profile is unchanged.

```text
IBM capture -> QEV live + finite TSEI -> native RVR -> ReceiptOS
Moth capture -> counts verifier -> native RVR
                              -> cross-provider model v0
```

### Cross-provider common model

`qev-cross-provider-evidence-v0` emits `qev.cross-provider-evidence.v0`:
identity, common consistency/issues/observation, capabilities, native layers
and provider-specific results. `ORDERED_SHOTS` and `COUNTS_ONLY` stay distinct.
Missing, contradictory, malformed and unavailable evidence remain separate.
Replay recomputes the complete report from the selected independent claim and
capture bytes. IBM executes its existing native layers; Moth does not acquire
those capabilities by appearing beside IBM. This unchanged v0 adapter does not
invoke the new Moth RVR profile; its Moth native nonintegration labels remain
correct for that adapter. The common report itself is not
a native RVR receipt or a ReceiptOS-root-bound artifact.

## Evidence and threat boundaries

Independently recomputed means locally derived from supplied bytes, not
independent authorship or independent observation of the hardware. Provider
names, backend names, completion and acquisition labels remain reported facts.
Local unsigned claims are trust inputs: replacing both a claim and its evidence
creates a different record, not verification of the original one.

`providerAuthentication` remains **`NOT_ESTABLISHED`** for both captured paths.
No cryptographic provider attestation verifier runs. Unsupported authentication
objects in legacy binding are explicitly unsupported, never authenticated.
Hashes, native roots and compatible declarations do not establish physical QPU
authenticity, sampler independence, distribution equality, min-entropy,
cryptographic randomness, device certification, general compiler correctness
or production security. A ReceiptOS root can be valid over a refuted relation;
root validity, RVR outcome and TSEI classification are distinct axes.

## Offline quick start and replay

Run from the repository root with Python 3.12+, Node.js 22+ and Bun 1.3.14
(the CI-pinned Bun version) on PATH. No provider SDK, account, credentials,
package installation or runtime network is required for these commands.
For export/redirection examples on Windows, use `cmd.exe` to preserve stdout
bytes rather than legacy PowerShell text redirection.

```sh
python -B -m qev demo
python -B -m qev verify --request fixtures/corpus/sample-a.request.json fixtures/corpus/sample-a.package.json
python -B -m qev live-demo > live-export.json
python -B -m qev live-replay live-export.json
python -B -m qev.moth_replay
python -B -m qev.moth_rvr_cli demo --output moth-rvr.json
python -B -m qev.moth_rvr_cli replay --artifact moth-rvr.json --claim profiles/rvr-qev-moth-counts-v0/claim.json
python -B -m qev.cross_cli demo
python -B -m qev.cross_cli demo --provider ibm-direct > cross-ibm.json
python -B -m qev.cross_cli replay --provider ibm-direct --artifact cross-ibm.json
python -B -m qev.cross_cli demo --provider moth-comet > cross-moth.json
python -B -m qev.cross_cli replay --provider moth-comet --artifact cross-moth.json
```

Live replay supports a separately reviewed `--claim`. Moth custom capture replay
requires `--claim`; cross-provider custom input requires both `--capture` and
`--claim` plus `--provider`. The cross-provider Moth importer retains the finite
role names of this capture; it is not an arbitrary job importer. See the exact
[IBM live](docs/LIVE_CAPTURE_REPLAY_V1.md), [Moth](docs/MOTH_COMET_COUNTS_V0.md)
and [cross-provider](docs/CROSS_PROVIDER_EVIDENCE_V0.md) contracts.

## Validation

The current suite contains **293 tests** (259 at the PR #12 base + 34 Moth RVR tests).
Normal and optimized runs execute the same suite. The synthetic corpus has
44 cases. Six source-mutation gates require **47 kills**: QEV 7, RVR 7,
IBM live 7, Moth counts 7, cross-provider 12 and Moth native RVR 7. Positive
controls per mutant are 5/3/3/3/3/3 respectively. The provider-binding demo separately refutes eight
input mutations; the IBM adapter demo refutes six and rejects malformed bits.
These input controls are not additional source mutants.

```sh
python -B -m unittest discover -s tests -v
python -B -O -m unittest discover -s tests -v
python -B -m qev mutation-check
python -B -m qev rvr-demo
python -B -m qev rvr-mutation-check
python -B -m qev receiptos-demo
python -B -m qev tsei-demo
python -B -m qev quantum-transpile-demo
python -B -m qev provider-binding-demo
python -B -m qev ibm-runtime-demo
python -B -m qev live-mutation-check
python -B -m qev.moth_mutations
python -B -m qev.cross_mutations
python -B -m qev.moth_rvr_mutations
python -B -m qev.moth_rvr_cli sources
python -B -m qev sources
python -B -m qev.cross_cli sources
python -B -m tools.check_docs
git diff --check
```

[CI](.github/workflows/ci.yml) runs every legacy gate, both test modes and
normal/repeat/optimized byte comparisons for IBM export/replay/mutations,
Moth counts replay/mutations, Moth RVR export/replay/mutations and both
cross-provider projections/replays/mutations.
The main source lock has **214 local + 28 vendored files**; a separate
cross-provider lock covers **8 files** and the Moth RVR lock covers **13 files**.
These locks exclude themselves. The Moth native manifest additionally pins its
transitive runtime dependencies and unchanged RVR primitives. The
documentation audit adds a Git-bound coverage record and checker outside runtime
profile inventories, avoiding changes to frozen runtime/profile identities.
The 16 historical reference records are metadata, not 16 executed dependencies.

## Current limitations and next concrete work

The IBM ideal relation supports active wires 0/1 and a finite gate/angle set;
it is not a general compiler proof. Moth lacks the provenance needed for that
relation. Its native counts RVR receipt establishes a narrower relation. The legacy ReceiptOS bridge's
local root/summary/proof assembly is not the stronger live export/replay path.
Expectation authorship remains shared; no independent implementation is claimed.

Next work is to assess ReceiptOS packaging for the Moth RVR bundle. Provider
authentication is conditional on a real cryptographically verifiable provider
receipt, signature or attestation; none is available in this evidence. Broader
IBM circuit support is a separate later bounded profile. Precise upstream
Moth commitment encoding and circuit/measurement provenance remain unresolved
evidence requirements. This implementation uses only the preserved capture;
it submits no QPU jobs and uses no provider network or credentials.

## Documentation and licensing

Start with the [integration map](docs/INTEGRATION_MAP.md),
[provenance](docs/PROVENANCE.md), [synthetic contract](docs/CONTRACT.md),
[RVR profile](docs/RVR_QEV_PROFILE_V0.md),
[legacy ReceiptOS scope](docs/RECEIPTOS_QEV_CAPSULE_V0.md),
[TSEI artifact profile](docs/TSEI_QEV_PROFILE_V0.md),
[layout profile](docs/QUANTUM_TRANSPILATION_BOUNDARY_V0.md),
[binding contract](docs/PROVIDER_EXECUTION_BINDING_V0.md) and
[IBM adapter](docs/IBM_QUANTUM_RUNTIME_ADAPTER_V0.md).
[NEXT_NATIVE_RVR.md](docs/NEXT_NATIVE_RVR.md) is a superseded historical handoff.
Repository-authored QEV material is licensed under the
[Apache License 2.0](LICENSE), with attribution and scope recorded in
[NOTICE](NOTICE). Vendored software, preserved IBM/Moth evidence and upstream
OpenAPI material retain their separate rights and license boundaries; see
[LICENSING.md](LICENSING.md).
