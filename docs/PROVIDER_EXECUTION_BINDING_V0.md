# Provider Execution Binding v0

This profile closes a specific evidence boundary between a submitted physical circuit and returned measurement bytes.

It binds:
- provider identity;
- backend identity;
- request identity;
- requested shot count;
- physical-circuit digest;
- transpiler name/version/profile;
- provider job id;
- completion state;
- raw-measurement digest and byte length.

A successful result is `EXECUTION_BOUND` only **over the supplied provider artifact**.

## Authentication is a separate axis

`EXECUTION_BOUND` does not mean `PROVIDER_AUTHENTICATED`.

An unsigned JSON response, copied API response, or provider-name string can establish internal consistency of supplied evidence but cannot authenticate who produced it. `UNVERIFIED_ASSERTION` therefore never upgrades provider authentication.

The v0 result keeps:
- execution binding;
- provider authentication;
- authenticated physical-QPU execution;
- entropy

as separate claims.

## Adversarial contract

The finite gate mutates each bound dimension independently: provider, backend, request, shots, physical-circuit digest, transpiler identity, completion status, and raw measurements. Every mutation must refute the binding while leaving provider authentication independently unresolved.

## Next step

A provider-specific adapter may map a real API/job artifact into this vendor-neutral schema. Its authentication status must be derived only from evidence actually supplied by that provider path. The adapter must not infer authentication merely because a job id is syntactically valid or because an API response was obtained over a client session.

v0 does not claim a real provider adapter, real QPU execution, min-entropy, distribution equality, or cryptographic randomness.
