# Provider Execution Binding v0

This profile closes a specific evidence boundary between a submitted physical circuit and returned measurement bytes.

It binds:
- provider identity;
- backend identity;
- request identity;
- requested shot count;
- physical-circuit digest;
- transpiler name/version/profile;
- completion state;
- raw-measurement digest and byte length.

A successful result is `executionBinding = BOUND` only **over the supplied
provider artifact**. Eight axes are compared. The artifact also retains a
provider-assigned job ID, but this legacy verifier does not compare it with an
independent expected job ID or use `requested_job` as an assigned-job anchor.
The separate [live profile](LIVE_CAPTURE_REPLAY_V1.md) adds that claim/job check.

## Authentication is a separate axis

`BOUND` does not mean provider authentication is established.

An unsigned JSON response, copied API response, or provider-name string can establish internal consistency of supplied evidence but cannot authenticate who produced it. `UNVERIFIED_ASSERTION` therefore never upgrades provider authentication.

The v0 result keeps:
- execution binding;
- provider authentication;
- authenticated physical-QPU execution;
- entropy

as separate claims.

## Adversarial contract

The finite gate mutates each bound dimension independently: provider, backend, request, shots, physical-circuit digest, transpiler identity, completion status, and raw measurements. Every mutation must refute the binding while leaving provider authentication independently unresolved.

## Implemented adapter and retained limits

The [IBM Runtime adapter](IBM_QUANTUM_RUNTIME_ADAPTER_V0.md) is implemented and
merged. Its synthetic conformance fixture and the separate preserved IBM live
path are distinct. Run `python -B -m qev provider-binding-demo` and
`python -B -m qev ibm-runtime-demo` for their finite controls.

The legacy demo's `providerSpecificAdapter = NOT_INTEGRATED` describes that
standalone vendor-neutral demo, not the repository's integration status.
Null authentication and `UNVERIFIED_ASSERTION` yield `NOT_ESTABLISHED`; other
authentication objects yield `UNSUPPORTED_AUTHENTICATION_EVIDENCE`, never a
successful authentication claim. A job ID or an SDK session is not an attestation.
No physical QPU authenticity, min-entropy, distribution equality or cryptographic
randomness is established by this binding.
