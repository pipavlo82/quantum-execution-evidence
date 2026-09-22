# Quantum execution evidence v0 — finite experimental contract

Adapted from the repaired local contract dated 2026-09-21. OFFLINE / SYNTHETIC / EXPERIMENTAL.
This standalone repository preserves the local profile; it is not a framework,
standard, native RVR receipt, ReceiptOS capsule, Chronicle entry or TSEI proof.

## Local trust roots and identities

The verifier receives TWO independent inputs: a supplied request file selected by
the caller as a local trust root, and a result package. A freely rewritten embedded
request is insufficient. The exact validated request object must equal the supplied
request, including request ID, program source, parameters, source-to-output mapping,
endianness, provider/backend/job, width and requested shots. Digest equality is not
authentication of either input. Replacing BOTH inputs changes the local trust root.

All fields are closed. Profile `quantum-evidence.v0`; postprocessor
`integer-score-parity.v0`. Request program codec `qev-lines.v0` is a finite declaration
language: H i, X i, CX i j, RZ i theta_quarters, and terminal MEASURE_ALL, one ASCII
instruction per LF-terminated line. No executable expressions, includes, imports,
paths or network references. Exactly one integer parameter theta_quarters in [0,3].
This profile checks declared procedure identity, not circuit execution/equivalence.

Request width 1..8; shots 1..4096; at most 64 instructions, valid qubit indices,
distinct CX operands. Endianness `source-index-ascending`: leftmost canonical bit
is source index 0. `source_to_output[i]` gives output position of source bit i.
It is a bijection. The independently supplied request binds this mapping.
Observation `output_to_raw[j]` gives raw column for output position j; it is an
explicit representation permutation, whose inverse is reconstructible. Canonical
source bit i = raw[output_to_raw[source_to_output[i]]]. This permits a representation
permutation with matching inverse mapping; it is not compiler equivalence.

Raw evidence codec `ascii-bit-lines-lf.v0`: exactly width ASCII 0/1 characters plus LF
per ordered shot, no CR/BOM/blank lines. Preserve these exact bytes in `raw.data`.
Raw SHA-256 binds those bytes. Request SHA-256 binds canonical request bytes.
Package SHA-256 binds canonical bytes of every package field EXCEPT its own
`payload_sha256` field, including markers, claims, raw envelope, maps, counts,
postprocessor, result and embedded request; no circular digest.
Canonical codec `qev-json.v0`: UTF-8, sorted object keys, compact separators,
ensure_ascii=True, no floats/nonfinite values/booleans/null except explicit optional
evidence, no duplicate keys. JSON key order is representational, not semantic.
SHA-256 is lowercase 64 hex. Report also records exact imported request/package
byte hashes, distinct from canonical identities.

## Deterministic relation

Map each preserved shot into canonical source order, then count exact bitstrings.
Counts must match the supplied histogram (positive integer counts, no zero entries).
Derived result has exact integer fields `shots`, `weighted_sum`, `parity_ones`.
weighted_sum = sum(count[b] * sum((i+1)*int(b[i]) for i in range(width))).
parity_ones = sum(count[b] for b with odd number of 1 bits).
No floats, probabilistic fitting, sampling test or repeated hardware runs.
Different independent samples from the same declared procedure may BOTH satisfy
this relation. Same histogram does not establish ordered sample identity.
Recomputation of preserved observations differs from regeneration of physical
outcomes; classical stochastic systems share this distinction.

## Independent axes and failure taxonomy

Keep input classification, source provenance, supplied claims, integrity,
request_binding, deterministic_verification, native Semantic ABI link and actual
hardware/entropy status separate. No global verified=true. Available contradictions
are REFUTED. Missing raw evidence is CANNOT_ESTABLISH. Malformed inputs are INVALID;
unsupported codecs/program syntax/profile/postprocessor/claim elevation are
UNSUPPORTED. Neither category is a hardware refutation.
Provider evidence may be absent or unverified text; never fabricated signatures.
Provider authenticity, authentic QPU execution, sampler independence, distribution
equality, min-entropy, cryptographic RNG and device certification remain
NOT_ESTABLISHED / NOT_EVALUATED for every input. Simulator/QPU labels are supplied
claims only. A valid digest, signature or histogram cannot elevate them.

Native Semantic ABI declarations follow the pinned manifest schema, use exact
scope and temporal labels, and are checked through the local byte-pinned adapter.
Its native result is compatibility, never claim truth/authentication. The production
checker must not import corpus/manifest/expected outputs. Expected outcomes are
separately authored test data, explicitly NOT author-independent.

## Import and experiment gates

At most 262144 bytes per input; depth 16; 20000 JSON nodes; bounded integer tokens,
string lengths and total shots. Reject duplicate keys, booleans, floating/nonfinite
numbers, negative/out-of-range counts/bits and unknown fields. No package references
are supported; CLI paths must be relative regular files inside the current worktree,
without dot/dotdot segments, drive/UNC/colon/backslash or symlink escapes.

Corpus includes different-sample positives, shot-order and representation mirrors,
same weak projection/different protected relation, recomputed-digest request swaps,
malformed and missing evidence, corruption, relabeling and unsupported elevations.
Source mutations run actual changed checker source in memory. KILLED requires the
designated semantic deviation and preservation of all full positive/mirror controls.
CRASHED, NOT_APPLIED, VACUOUS, CONTROL_BROKEN, SURVIVED and BASELINE_FAILED are failures.
No authored expectation may influence production verification.

## Additive coordinator-review hardening — 2026-09-21

The initial 28-test experiment did NOT detect QEV-REVIEW-01..04. Coordinator review
reproduced empty mutation success, zero-control kills, a rejected native edge with
CLI success, and empty source-lock success. Initial reports remain historical;
this section tightens admission without changing the 88 corpus bytes or expectations.

Before any case/native evaluation, manifests must have exactly the 44 declared
unique cases and exactly the five distinct declared positive/mirror controls.
Case paths and original corpus SHA-256/byte lengths are fixed separately from
expected values. Controls must assert the complete positive signature and their
actual baseline must match it. A negative/unknown/substitute control cannot qualify.
Mutation configuration must match all seven unique, fixed source-patch/killer/axis/
target obligations before execution. Success requires seven actual KILLED records
and all five complete controls per mutant, not an empty absence of failure counters.

`inventory.py` is trusted, finite declaration code, separate from fixture expected
results; it is not independent authorship. `admission.py` validates closed structures,
strict JSON (including duplicate-key rejection), exact identities and typed hashes/
lengths. No invalid set is filled from defaults. `INVENTORY_INVALID`,
`EVIDENCE_UNAVAILABLE`, `EVIDENCE_MISMATCH` and `BASELINE_FAILED` are explicit admission
failures; no mutation was killed when admission failed. They are not hardware verdicts.

The standalone source lock must contain every unique path in the separately fixed
`qev/source_inventory.py`: all local technical files and the four exact vendor
files (linker, manifest schema and their two licenses). Empty, partial, duplicate
or redirected inventories fail before native execution. Vendor origin identities
must exactly match the fixed source inventory. The lock excludes itself to avoid
circularity; its digest is recorded in external commit evidence, and Git binds it.
Regeneration uses `python -B -m tools.pin_lock` and reads only the fixed paths.
It never derives the required inventory from the lock being validated.

Byte identities are checked after structural admission. Available source mismatches
outrank missing evidence in the source report, with every per-file result retained.
Locks remain unsigned, local trust roots; byte identity is not correctness or
authentication. Historical reference identities in `docs/reference-pins.json` are
metadata, not runtime dependencies or newly verified reference-source bytes.
Production verification imports no corpus or expected outcomes. The adapter checks
the complete lock structure and exact vendor/bridge bytes, then executes the pinned
linker bytes. `qev sources` additionally checks every local locked file. The schema
is read from verified bytes; the linker remains unchanged. No dependency downloads,
network requests or path-dependent external repository reads occur at runtime.

Native results have separate `EXECUTED` (well-formed compatible), `REJECTED`,
`MALFORMED` and `UNAVAILABLE` statuses. Compatible results must bind the exact
producer claim and consumer requirement. `valid` must be a boolean, never an integer
or truthy substitute. Malformed/native errors cannot crash into apparent success.
Preserved local postprocessing may remain ESTABLISHED_OVER_SUPPLIED_BYTES when
the native edge is rejected or unavailable; compatibility and local truth differ.

Verification CLI precedence and exit codes: malformed/unsupported input 2; any
available deterministic/request/integrity contradiction 1; malformed native result
5; rejected native edge 4; unavailable native edge or missing raw evidence 3;
otherwise compatible native edge plus established local relation 0. All axes remain
serialized even when one determines the exit. Demo/mutation/source commands return
nonzero on incomplete admission; zero never means an empty gate succeeded.
