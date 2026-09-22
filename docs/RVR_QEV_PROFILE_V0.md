# RVR Quantum Execution Evidence Profile v0

Status: experimental profile for the standalone Quantum Execution Evidence repository.

Profile ID: `rvr-qev-preserved-observation-v0`.

This profile uses the RVR v0 receipt envelope, canonical-byte contract, dependency-resolution rules, evidence-set commitment rules, result projection rules, and recomputation status taxonomy. The generic RVR v0 implementation bytes are vendored and pinned from commit `549a7e150ddc75df88dc90ee93f331fea7464567`.

## Verification relation

The claim identifies two committed evidence members: `request` and `package`. Their exact payload bytes are interpreted using QEV profile `quantum-evidence.v0`.

The domain operation is `QEV_RECOMPUTE_PRESERVED`. It does not regenerate a physical stochastic execution. It deterministically checks the preserved request/package relation.

A semantic result is:

- `VERIFIED / rvr.qev.v0.relation_satisfied` when QEV request binding, integrity, and deterministic post-processing are all `SATISFIED`;
- `REFUTED / rvr.qev.v0.relation_refuted` when available committed bytes contradict any of those three axes;
- `UNVERIFIABLE / rvr.qev.v0.raw_evidence_unavailable` when the committed package is well formed and bound but its raw observation evidence is explicitly absent;
- `UNVERIFIABLE / rvr.qev.v0.required_evidence_unavailable` when either decisive RVR evidence member is committed as `UNAVAILABLE`.
Malformed or unsupported QEV inputs are gate rejections, not verification outcomes.

The RVR canonical result records only the profile-scoped deterministic axes. Semantic ABI compatibility, provider authenticity, physical QPU execution, distribution equality, entropy, device certification, ReceiptOS packaging, TSEI, RSI, PRF, Chronicle and PQ signatures are outside this profile's verification outcome.

## Stochastic recomputation boundary

RVR recomputation status is intentionally independent from verification outcome.

If the original receipt was built over sample A and a later candidate contains a different valid sample B under the same declared QEV procedure, the candidate can remain semantically `VERIFIED` while recomputation is `DIVERGED` because the evidence-set identity changed.

Therefore:

```text
VERIFIED + REPRODUCED
!=
VERIFIED + DIVERGED
!=
REFUTED + DIVERGED
```

`DIVERGED` means the candidate did not reproduce all receipt identities/canonical-result identity. It does not itself mean the domain claim is false.

The conformance vectors include a different valid sample and a shot-order variant specifically to enforce this distinction.
## Evidence closure and dependencies

RVR v0 dependency resolution is package-relative and ordered: resolve -> read -> SHA-256 match -> use. Required normative dependencies must match their pinned bytes before evaluation.

A committed `PRESENT` evidence member whose payload cannot be resolved produces `CANNOT_RECOMPUTE` without evaluation. Resolved bytes whose digest or byte length contradict the descriptor are gate-rejected. Uncommitted outcome-relevant ambient state is forbidden.

The QEV verifier implementation is adapter evidence, not profile identity. The profile instead commits this verification specification, the profile-specific constraints schema, the QEV RVR schema, and the conformance vector package. Adapter diversity is not established by v0.

## Claim limits

This profile does not establish that supplied measurement bytes came from a physical QPU, that a provider is honest, that samples are independent, that a distribution is correct, that min-entropy exists, or that output is cryptographic randomness.

Expectation authorship and implementation independence remain separate evidence questions.
