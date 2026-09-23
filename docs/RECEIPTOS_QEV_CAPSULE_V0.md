# Native ReceiptOS packaging of QEV RVR v0

Status: experimental native integration.

This lane packages the already-native `rvr-qev-preserved-observation-v0` artifact into the existing ReceiptOS proof substrate. It does not define a new ReceiptOS capsule schema.

Pinned ReceiptOS reference implementation commit:

`45b46bf7df3a60b32583291f577a36bf19d22f00`

The legacy `qev/receiptos_bridge.ts` executes vendored `createEvidenceCapsuleV0`,
`createProvenanceSummaryV0`, `deriveProofObjectId` and `deriveProofRef`. It locally
implements canonical root calculation and capsule summary, and assembles the
portable object itself. It does not call the native root verifier or full native
portable-object constructor. Run `python -B -m qev receiptos-demo`.

It produces the following existing ReceiptOS surfaces:
- `receiptos.evidence_capsule.v0`
- `receiptos.provenance_summary.v0`
- `receiptos.portable_proof_object.v0`
- ReceiptOS canonical `receipt_root` semantics.

## Boundary

The QEV adapter first constructs a producer-neutral ReceiptOS evidence envelope from a **native RVR artifact**. The envelope preserves the RVR outcome, reason code, recomputation status, profile identity, and committed evidence-member identities. The local bridge computes the anchor-independent root and supplies its summary to the native capsule/provenance builders, then assembles the portable object.
The ReceiptOS root proves canonical consistency of the supplied normalized evidence. It does not upgrade the RVR result and does not establish the physical origin of quantum measurements.

In particular:

```text
ReceiptOS root verified
!= authentic QPU execution
!= provider authenticity
!= entropy established
!= cryptographic RNG
```

In this legacy bridge, `provenance_summary.verifier_status = verified` reflects
the locally constructed root-comparison summary. It is not evidence that the
independent native ReceiptOS root verifier or an external producer verifier ran.
The distinct [live replay bridge](LIVE_CAPTURE_REPLAY_V1.md) calls the actual
vendored root/verifier/summary/portable functions and replays the saved export.

## Producer naming

The historical/current ReceiptOS input envelope id remains `stealth.session.evidence.v1`. Per the ReceiptOS integration manifest, this is a compatibility marker rather than a Stealth-only trust boundary.

The QEV adapter therefore uses that historical envelope id while setting producer identity separately:
- `agent.runtime = QEV`
- `metadata.generated_by = qev.receiptos.native-rvr-adapter.v0`

Producer naming remains provenance metadata, not proof.
## Portable proof object

The portable proof object is derived from the ReceiptOS receipt root:
- `proof_object_id = proofobj-<receipt_root without 0x>`
- `proof_ref = receiptos://portable-proof-object/<proof_object_id>`
- `proof_system = ReceiptOS`
- `relation_type = imported`

No external anchor is claimed in v0. `anchor_ref` remains null. Epoch timestamps
in this legacy bridge are deterministic placeholders, not observed execution
times. Its root binds a normalized summary of RVR identities; it does not embed
and bind the full capture payloads as the later live export does.

## Required controls

The integration must demonstrate:
1. native RVR VERIFIED/REPRODUCED input packages into a schema-valid native Evidence Capsule;
2. stored and recomputed ReceiptOS roots match;
3. top-level ReceiptOS anchor changes do not change the recomputed root;
4. tampering with normalized evidence changes the recomputed root and is detected;
5. RVR REFUTED or UNVERIFIABLE state cannot be silently promoted to a successful QEV/ReceiptOS semantic claim;
6. ReceiptOS packaging does not add physical-QPU or entropy claims;
7. source pins for the vendored ReceiptOS implementation remain exact.

ReceiptOS packaging and RVR verification remain separate evidence axes.
