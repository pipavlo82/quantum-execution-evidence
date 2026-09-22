# Live capture replay v1

This additive offline profile admits `LIVE_IBM_RUNTIME_API` capture bytes without
changing the old synthetic checker, profile, adapters, fixtures, or vendors.
No SDK, account, service, network, new job, or package installation is required.

```
python -B -m qev live-demo > live-export.json
python -B -m qev live-replay live-export.json
python -B -m qev live-mutation-check
```

`live-demo` uses the reviewed claim in `fixtures/live-capture-v1/claim.json`.
`live-replay` uses the same independent claim by default; `--claim claim.json`
supplies another independently reviewed commitment. A candidate cannot supply
its own expectations. The claim pins the original intent, immediate submit
receipt, logical snapshot, submitted ISA snapshot, and separately preserved raw
bytes. It binds expected IBM job ID, backend, local request ID and shots. Local
`requested_job` is a caller request label, never the assigned IBM job ID.
Neither an attacker refreshing package hashes nor changing the bundled claim
can replace this external trust input. Replacing that trust input is a new claim,
not verification of the original observation.

The initial dataset is the single already-captured job `dapdeqcak42c73cid5qg`,
backend `ibm_fez`, 256 shots. Raw SHA-256 is
`2d3a5d289662f4c8bebd20654f3a975e82efb795d58ba2a5d552f907927ad324`.
Fifteen selected files are copied byte-for-byte; fixture seed-manifest pins them.
Historical preflight and input-comparison booleans are supplemental observations,
never semantic oracles. QASM files are preserved opaque attachments, not parsed
or substituted for the snapshot. QPY hashes in historical intent remain historical
references; QPY bytes are not in this selected evidence set and are not verified.

Input admission rejects duplicate JSON keys, nonfinite values, surrogate strings,
bool/int confusion, unrecognized or missing fields, duplicate/missing role
inventory, invalid base64, path escapes, symlinks and directory junctions.
Maximum JSON input is 4 MiB, depth 32, arrays 16384, objects 1024; each capture
role is at most 256 KiB. Shots are bounded at 4096 and circuit operations at 128.
Roles must be explicitly PRESENT or UNAVAILABLE. Missing committed PRESENT bytes
give CANNOT_RECOMPUTE. Decisive evidence declared UNAVAILABLE gives UNVERIFIABLE
with CANNOT_ESTABLISH axes. Resolved contradictions give REFUTED. Malformed input
is REJECTED. A noncompleted job makes observation completion unresolved; it does
not refute the physical or mathematical relation by itself.

Independent axes cover byte identity, declared capture origin, assigned-job and
request binding, provider-artifact consistency, ordered raw commitment/agreement,
histogram recomputation, bit order, completion, ideal ISA preservation and
authentication-label consistency. Provider authentication remains NOT_ESTABLISHED.
Every available expected anchor is checked even when another role is missing:
an available mismatch is REFUTED and takes precedence over missing evidence.
Job, origin, circuit, raw and authentication-label checks likewise evaluate each
available role or required pair independently; an unrelated missing role cannot
erase an available contradiction. Missing comparisons remain CANNOT_ESTABLISH.
The logical, submitted and returned measurement maps must each match the declared
intent, as well as satisfying the native source/target relation. Matching but
jointly swapped maps do not establish an unswapped declaration.
The physical digest is SHA-256 of UTF-8 `json.dumps(snapshot, sort_keys=True,
separators=(',', ':'), ensure_ascii=True, allow_nan=False)`. This is the recorded
operation-snapshot surface, not QPY or QASM bytes. Declared live acquisition is
not portable signed provider attestation.

The finite ISA relation uses exact arithmetic in Q(zeta_8), zeta_8^4 = -1, with
rational coefficients, no tolerances, expression evaluation or angle rounding.
The literal `1.5707963267948966` maps to ideal pi/2; phase
`2.3561944901923475` maps to ideal 3*pi/4 under `qev-ideal-angle-literals-v1`.
The complete finite token maps are in pinned `qev/live_math.py`. Other tokens are
UNSUPPORTED, including numerically nearby decimals. This interpretation does
not assert equality of finite decimal numbers with pi.

Supported unitary gates are H, X, CX, CZ, SX and RZ(k*pi/2) for declared literals.
All four input basis columns in q1q0 order are compared, modulo one explicitly
declared global phase. Per-column relative phase is protected. Terminal mapping
from each active qubit to classical bits is independently derived on each side
and compared. Only active physical wires 0 and 1 are supported. Every operation
is checked before idle wires are removed from widths 2 through 156. Repeated,
mid-circuit or missing measurements, wrong arity, duplicate/out-of-domain qubits,
clbit misuse and unmapped active operations reject. Dynamic control, reset and
measure_2 also reject admission. Other gates remain unsupported/unresolved,
never rounded into a pass.

Official mathematical references (supplied for this task, no browsing in worker):
[SX](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.SXGate),
[RZ](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.RZGate),
[CZ](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.CZGate),
[bit ordering](https://quantum.cloud.ibm.com/docs/en/guides/bit-ordering).
Exact idealized matrix equivalence does not prove physical noiseless behavior,
measurement probabilities, hardware authenticity or general compiler correctness.

The actual pinned TSEI evaluator invokes separate source and target exact
recomputations inside its relation callbacks. It receives snapshots, not saved
verdicts. The generic native evaluator decides stable/violation/unresolved.
All 28 vendor files and the complete required dependency inventory are checked
before loading native RVR or executing bridges. Unavailable or changed sources
give CANNOT_RECOMPUTE. The new `rvr-qev-live-capture-replay-v1` profile executes
native RVR canonicalization, profile audit, evidence closure, evidence-set digest,
six-field receipt and result projections. QEV supplies domain evaluation without
monkeypatching RVR's old evaluator. Recompute compares claim, evidence, profile
and result identities. Optional conformance expectations are not semantic inputs.
The same valid preserved outcome with different supplemental evidence can be
VERIFIED+DIVERGED. The original saved result is independently checked first.

The new ReceiptOS bridge directly imports and executes vendored computeReceiptRoot,
verifyHandoffReceiptRoot, createCapsuleSummaryFromEvidence and
createPortableProofObjectV0. It does not use the legacy bridge's approximations.
The native historical `stealth.session.evidence.v1` envelope carries QEV producer
identity. Root-covered `changes.diff_sha256` binds the exact native RVR JSON bundle
attachment, which includes all captured payload bytes, not URI-only locators.
Native capsule summaries describe that compatibility envelope and root validity;
they are not the domain semantic verdict. RVR outcome remains separately visible,
including REFUTED and UNVERIFIABLE exports with valid ReceiptOS roots.

Replay consumes the saved export, checks its attachment digest and independent
claim, source dependencies, native envelope, closure and stored projections,
recomputes the live relation, recomputes the native root, and compares the saved
summary and portable object to native results. It does not silently replace a
bad saved artifact with a fresh good one. Top-level anchor is excluded by native
root semantics; execution tests demonstrate this, while replay separately rejects
fabricated anchor claims. No external anchor is claimed.
Saved-result and native-envelope comparisons use type-sensitive JSON serialization;
integer 0/1 cannot stand in for Boolean false/true. Complete comparisons also
reject added, removed or changed fields. The CLI returns exit 0 for VERIFIED,
1 for REFUTED, 3 for UNVERIFIABLE/CANNOT_RECOMPUTE and 2 for malformed/rejected
input; a valid ReceiptOS root alone cannot make live-demo succeed.

No local verification timestamp is claimed. For the native envelope's required
compatibility timestamp slot, authorization_checked_at carries the captured
intent recorded_at; authorized_at_execution is null and no authorization proof
is claimed. Native portable created_at consequently represents that capture
timestamp, not observed replay execution. An absent capture timestamp prevents
portable creation; epoch observations are never fabricated.

Mutation and adversarial tests have shared authorship with this implementation.
They are finite falsification evidence, not independent test authorship, entropy
qualification, sampler independence, production security or quantum certification.
The fixed source inventory includes new runtime, profile, tests, docs and fixtures.
Profile pins exclude the profile itself; the source lock excludes its own digest.
