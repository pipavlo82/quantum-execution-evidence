# IBM Quantum Runtime adapter v0

This adapter maps a recorded IBM Quantum SamplerV2 job/result artifact into Provider Execution Binding v0.

The API model follows current IBM Quantum Compute documentation: SamplerV2 submits PUBs and returns RuntimeJobV2; completed results are PrimitiveResult objects containing SamplerPubResult data, with measurement registers represented as BitArray. Shot-order-preserving bitstrings are obtained with BitArray.get_bitstrings().

## Offline conformance vs live capture

CI uses an explicitly synthetic/offline IBM-shaped fixture. It proves adapter behavior, not IBM execution.

`tools/capture_ibm_runtime_job.py` is a separate opt-in utility for retrieving an existing IBM Runtime job by job ID from an already configured QiskitRuntimeService account. Credentials are neither accepted as command-line arguments nor written to repository artifacts.

## Binding

The adapter preserves job id, backend, request id, shot count, ISA/physical-circuit digest, transpiler identity, completion status, and ordered measurement bitstrings.

The ordered bitstrings are canonicalized as one binary string per LF-terminated line before entering Provider Execution Binding v0.

## Authentication boundary

A record retrieved through an authenticated SDK session is still classified by QEV as a recorded provider API artifact, not a cryptographically authenticated execution receipt.

Therefore:

`executionBinding = BOUND` does not imply `providerAuthentication = ESTABLISHED`.

A future authentication profile requires provider evidence with independently verifiable authenticity semantics.

## Scope

v0 supports one Sampler PUB and one classical BitArray register. Multi-PUB and multi-register jobs are rejected by the live capture utility rather than silently flattened.

No live IBM job is included in the repository.