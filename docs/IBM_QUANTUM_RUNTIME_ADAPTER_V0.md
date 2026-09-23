# IBM Quantum Runtime adapter v0

This adapter maps a recorded IBM Quantum SamplerV2 job/result artifact into Provider Execution Binding v0.

The recorded adapter models the IBM Quantum Compute acquisition surface used by the preserved capture: SamplerV2 submits PUBs and returns RuntimeJobV2; completed results are PrimitiveResult objects containing SamplerPubResult data, with measurement registers represented as BitArray. Shot-order-preserving bitstrings are obtained with BitArray.get_bitstrings().

## Offline conformance vs live capture

`python -B -m qev ibm-runtime-demo` uses an explicitly synthetic IBM-shaped
fixture. CI also runs the separate preserved live replay described below.
The legacy demo's `liveIBMJob = NOT_EXECUTED` describes its own fixture run.

`tools/capture_ibm_runtime_job.py` is a separate opt-in utility for retrieving an existing IBM Runtime job by job ID from an already configured QiskitRuntimeService account. Credentials are neither accepted as command-line arguments nor written to repository artifacts.

## Binding

The adapter preserves job id, backend, request id, shot count, ISA/physical-circuit
digest, transpiler identity, completion status, and ordered measurement bitstrings.
In the retrieval utility, request ID, circuit digest and transpiler labels are
caller-supplied arguments, not values independently authenticated by IBM. It
retrieves an existing job; it does not submit a new job. The utility is not part
of offline replay or CI and requires provider access when explicitly used.
Legacy binding retains the assigned job ID without an independent expected-ID
comparison; the live profile checks that additional boundary.

The ordered bitstrings are canonicalized as one binary string per LF-terminated line before entering Provider Execution Binding v0.

## Authentication boundary

A record retrieved through an authenticated SDK session is still classified by QEV as a recorded provider API artifact, not a cryptographically authenticated execution receipt.

Therefore:

`executionBinding = BOUND` does not imply `providerAuthentication = ESTABLISHED`.

A future authentication profile requires provider evidence with independently verifiable authenticity semantics.

## Scope

v0 supports one Sampler PUB and one classical BitArray register. Multi-PUB and multi-register jobs are rejected by the live capture utility rather than silently flattened.

## Preserved live capture now included

Merged PR #8 includes the saved job `dapdeqcak42c73cid5qg` under
`fixtures/live-capture-v1/`, reported backend `ibm_fez`, 256 ordered shots.
`python -B -m qev live-demo` and saved `live-replay` execute native RVR,
finite ideal TSEI and native ReceiptOS over those bytes without an SDK or account.
See [live replay v1](LIVE_CAPTURE_REPLAY_V1.md). This does not turn the original
synthetic adapter fixture into a live record or establish provider authentication.