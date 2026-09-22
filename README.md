# Quantum Execution Evidence

`quantum-execution-evidence` is an offline, synthetic, experimental verifier for evidence produced by stochastic execution pipelines.

Its core boundary is simple:

```text
recomputable verification of preserved observations
!= regeneration of the same stochastic outcome
!= authenticated physical execution
!= entropy or cryptographic randomness
```

The v0 profile binds an independently supplied request to preserved ordered bitstrings, explicit bit mappings, counts, and deterministic integer post-processing. A second valid sample may differ from the first and still satisfy the same declared procedure.## Quick start

Requirements: Python 3.12+ and Node.js 22+. Runtime networking and dynamic dependency installation are not used.

```bash
python -m qev demo
python -m qev verify --request fixtures/corpus/sample-a.request.json fixtures/corpus/sample-a.package.json
python -m qev mutation-check
python -m qev sources
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
```

The native Semantic ABI linker is executed from byte-pinned vendored source. Its result establishes declaration compatibility only.## What v0 establishes

A successful finite check can establish that the supplied request matches the embedded request; preserved raw bytes match their declared digest; raw observations deterministically map to the supplied histogram and integer result; and the bounded claim edge is compatible with the pinned Semantic ABI declaration contract.

The verifier keeps request binding, integrity, deterministic verification, source identity, declaration compatibility, provider authenticity, hardware execution, distribution claims, entropy, and device certification as separate axes. There is no global `verified=true`.## What v0 does not establish

It does **not** establish authentic QPU execution, honest provider identity, sampler independence, distribution equality, min-entropy, cryptographic RNG, device certification, independent authorship, production security, or correctness of an arbitrary quantum compiler.

ReceiptOS, TSEI, PRF, RSI, Chronicle and PQ remain source-pinned integration references only. Native RVR is executed through the separate QEV profile described below. See [docs/INTEGRATION_MAP.md](docs/INTEGRATION_MAP.md).

The root license for newly authored repository code is intentionally **pending**. Vendored upstream license boundaries are preserved; see [LICENSING.md](LICENSING.md).

## Native RVR QEV profile

The repository now includes the experimental native RVR profile `rvr-qev-preserved-observation-v0`.
It uses exact vendored RVR v0 canonicalization, profile-audit, evidence-closure, receipt-envelope, and recomputation primitives pinned to RVR commit `549a7e150ddc75df88dc90ee93f331fea7464567`.

Run:

```bash
python -m qev rvr-demo
python -m qev rvr-mutation-check
```

The profile demonstrates the stochastic boundary directly: a different valid preserved sample can be **VERIFIED + DIVERGED**. `DIVERGED` records receipt-identity divergence; it is not itself a semantic refutation.

This RVR profile remains scoped to request binding, byte integrity, and deterministic post-processing over preserved QEV observations. It does not establish physical QPU execution, entropy, distribution correctness, or provider authenticity. ReceiptOS/TSEI/RSI/PRF/Chronicle/PQ remain separate integrations.
