# Native ReceiptOS packaging of QEV RVR v0

Status: experimental native integration.

This lane packages the already-native `rvr-qev-preserved-observation-v0` artifact into the existing ReceiptOS proof substrate. It does not define a new ReceiptOS capsule schema.

Pinned ReceiptOS reference implementation commit:

`45b46bf7df3a60b32583291f577a36bf19d22f00`

The integration vendors and executes the existing ReceiptOS v0 capsule builders and portable-proof helpers needed for:
- `receiptos.evidence_capsule.v0`
- `receiptos.provenance_summary.v0`
- `receiptos.portable_proof_object.v0`
- ReceiptOS canonical `receipt_root` semantics.

## Boundary

The QEV adapter first constructs a producer-neutral ReceiptOS evidence envelope from a **native RVR artifact**. The envelope preserves the RVR outcome, reason code, recomputation status, profile identity, and committed evidence-member identities. ReceiptOS then computes its own anchor-independent receipt root and packages the evidence into the native capsule/proof-object surfaces.
The ReceiptOS root proves canonical consistency of the supplied normalized evidence. It does not upgrade the RVR result and does not establish the physical origin of quantum measurements.

In particular:

```text
ReceiptOS root verified
!= authentic QPU execution
!= provider authenticity
!= entropy established
!= cryptographic RNG
```

Likewise, `provenance_summary.verifier_status = verified` means the independent ReceiptOS receipt-root verifier confirmed the ReceiptOS root. It is not a statement that an external producer verifier was observed.

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

No external anchor is claimed in v0. `anchor_ref` remains null.

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
