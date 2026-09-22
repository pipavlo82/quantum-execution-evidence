# Moth Comet preserved counts profile v0

This additive profile verifies consistency of preserved Moth HTTP evidence.
It does not authenticate Moth, IBM or physical execution, certify entropy,
reconstruct measurement order, or execute a QPU. It is separate from the older
ordered-bitstring profiles; no live record is relabeled synthetic.

## Actual observation

One POST was accepted (202) for Moth job
`4daf7153-f837-4f5a-bf65-a0525bd9dd7a` on 2026-09-22. Two processing status
observations and one completed status, plus job and result responses, are saved
as the original HTTP entity-body bytes. These are not TLS packet captures.
Safe HTTP metadata is stored separately; authorization/cookies are excluded.
The local exclusive-create submit marker prevents a repeated submit even after
an uncertain network failure. There was no retry, simulator run or IBM token.

Exact caller request: mode qpu; num_qubits 12; shots 2048; output_bytes 32;
bell_witness true; include_raw_counts true; epsilon_log2 64. Backend and IBM
credentials were omitted. The witness adds eight qubits, making 20 total.

The provider reports IBM backend `ibm_kingston`, provider job
`dapgt48r7bnc73b3ei0g`, three QPU seconds, engine version 1.0.0, counts-only
readout, and completion. These remain upstream assertions.

Independently recomputed from the preserved counts: 2048 shots, 2040 distinct
20-bit strings, all 20 one-bit marginals and Z expectations, all four witness
pair histograms and correlators, and S = 2.2890625. The profile checks the
reported sigma algebra (0.03559737809875312) and 3-sigma comparison, conditional
on the provider's statistical model; this does not establish independence,
loophole-free Bell violation, device certification or physical bit mapping.
No p-value, confidence interval, full entropy estimator or higher-order health
test is claimed independently reproduced.

The observed response has **no `certificate` field**. Its `entropy_report`
reports `hardware-insufficient-entropy`, budget_bits 0, entropy_accounted false.
The requested 32 bytes yielded **zero bytes**, empty hex and zero output bits.
This is a consistent budget-limited observation, not successful delivery of
32 random bytes. QEV does not promote its h_bit estimate to proven min-entropy.
No replacement QPU run is warranted by this profile.

## Offline replay

```sh
python -B -m qev.moth_replay
python -B -O -m qev.moth_replay
python -B -m qev.moth_mutations
python -B -m unittest tests.test_moth_comet -v
```

A custom capture requires an explicit separately supplied local claim:

```sh
python -B -m qev.moth_replay path/to/capture --claim path/to/claim.json
```

The claim pins the raw request and complete manifest and fixes the expected
Moth job ID. The manifest inventories every captured file and identifies the
request, submit, ordered status observations, final job and result roles.
Replay checks exact inventory, unique roles, byte lengths and SHA-256, safe
paths, HTTP method/path/status/body binding, exactly one recorded POST,
caller request and every returned job identity. The local claim and HTTP
metadata are unsigned and do not establish an independent trusted timestamp.
Changing evidence and its claim together can create another local record;
that is why the expected claim must come from outside untrusted capture data.

Inputs have bounded depth/size, unique JSON keys, finite numbers, strict integer
and boolean types, and secret-field rejection. Absent counts or an incomplete
job are UNVERIFIABLE; malformed input is REJECTED; contradictory evidence is
REFUTED; missing or mismatching source pins are CANNOT_RECOMPUTE. CONSISTENT
means the declared finite checks passed. There is no global verified flag.
CLI exit codes: 0 consistent, 1 refuted, 2 rejected, 3 unavailable.

## Hash and claim boundaries

Counts SHA-256 is
`f59283d499682628bb55df99f14e503ada5a16156425ee09b824ce94669558e2`.
Pulse SHA-256 is
`30453623b6b73947cfebad10da5116fc3c0361623d2d06c1a1bf5bde2ff9cf4a`.
Both match UTF-8 Python JSON with sorted keys, compact separators, ASCII
escaping and no terminal newline (pulse excludes its own pulse_hash member).
This encoding is a **local profile rule inferred from observed hash matches**,
not an audited upstream implementation or a general cross-language float
canonicalization standard. Only finite representable JSON values are admitted.
The output hash is SHA-256 of decoded hex; here it is SHA-256 of empty bytes.

The circuit hash agrees across build metadata, result and pulse, but no circuit
bytes were returned. Circuit-hash preimage and transpilation equivalence are
therefore not established. All available provenance, initial_layout, commitment,
entropy, witness, device fingerprint, pulse and counts fields remain in raw
evidence even where this profile evaluates only a subset of them.

The returned commitment is
`6d7f306e8e5fe8ac005c2a9bb0983d5c150f3589619f19138d188ef04cd9d291`.
Its repeated value/salt and timestamp agree, but the OpenAPI concatenation
description does not define exact preimage encoding. Straight concatenation,
common separators and compact/default JSON encodings did not reproduce it.
This is **CANNOT_ESTABLISH**, not a declared hash contradiction. The commitment
was first visible in our completed status/result, not the two earlier polls.
The provider's committed_at-before-collected_at timestamps do not prove an
externally witnessed commitment before outcomes. No publication or anchor exists.

The profile checks output-length arithmetic against the **reported** entropy
budget and modelled-budget subtraction, including log2(2048!). It does not
validate the min-entropy estimate, seed ceremony or Toeplitz implementation.
Zero-length output does not exercise a nonempty extractor computation.

Native RVR, ReceiptOS and TSEI remain available for their existing profiles.
They are **not integrated for this Moth counts profile**. A histogram is not
ordered shot memory; manufacturing an order would change the evidence claim.

## Source and regression boundary

The pre-submit upstream OpenAPI snapshot is preserved byte-for-byte at
`docs/moth-comet-v0/openapi.raw.json`, with URL and digest in `source.json`.
It is an upstream schema/documentation observation, not engine source,
license grant, hardware attestation or executable dependency. No downloaded
code runs during replay. No networking or credentials are needed in CI.

The finite profile and capture files are in the repository's source inventory
and lock. Existing profile semantics and prior raw fixtures are unchanged.
The older live verification-profile dependency digest is refreshed solely
because it commits to the shared source inventory. Seven exact-site source
mutations must each be killed by a semantic contradiction while preserving
three positive controls. Missing mutants/controls and crashes cannot pass.
All original suites remain in CI; replay and mutations repeat byte-identically
under normal and optimized Python.
