"""Native ReceiptOS packaging for a native QEV RVR artifact."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from . import rvr_native

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "qev/receiptos_bridge.ts"
CAPSULE_SCHEMA = ROOT / "vendor/receiptos-v0/schemas/evidence-capsule.v0.schema.json"

def _native_rvr_artifact():
    profile, digest, _, pinned, schema, _, _ = rvr_native.load_profile_context()
    vectors = rvr_native.rvr.parse_json_bytes(pinned["verification-vectors"], "verification-vectors")
    case = vectors["verificationCases"]["reproduced"]
    bundle = rvr_native.make_bundle(case, profile, digest, schema)
    recomputation = rvr_native.recompute(bundle, case, digest, schema)
    return bundle, recomputation, schema

def _run_bridge(bundle: dict[str, Any], recomputation: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="qev-receiptos-") as temp:
        temp = Path(temp)
        bundle_path = temp / "bundle.json"
        recomputation_path = temp / "recomputation.json"
        output_path = temp / "output.json"
        bundle_path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")
        recomputation_path.write_text(json.dumps(recomputation, sort_keys=True), encoding="utf-8")
        completed = subprocess.run(
            ["bun", str(BRIDGE), str(bundle_path), str(recomputation_path), str(output_path)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode("utf-8", "replace"))
        return json.loads(output_path.read_bytes())
def run_gate():
    bundle, recomputation, schema = _native_rvr_artifact()
    out = _run_bridge(bundle, recomputation)
    evidence = out["evidence"]
    proof = out["portableProofObject"]
    capsule = proof["evidence_capsule"]

    rvr_native.rvr.require_schema(
        capsule,
        rvr_native.rvr.parse_json_bytes(CAPSULE_SCHEMA.read_bytes(), "evidence capsule schema"),
        label="ReceiptOS evidence capsule",
    )

    if proof["schema"] != "receiptos.portable_proof_object.v0":
        raise AssertionError("portable proof object schema")
    if proof["proof_system"] != "ReceiptOS":
        raise AssertionError("proof system")
    if proof["receipt_root"] != capsule["receipt_root"]["stored"]:
        raise AssertionError("portable/capsule root mismatch")
    if capsule["receipt_root"]["match"] is not True:
        raise AssertionError("ReceiptOS root not verified")
    if capsule["verifier_result"] != {"ok": True, "status": "verified"}:
        raise AssertionError("ReceiptOS verifier result")
    if bundle["receipt"]["outcome"] != "VERIFIED":
        raise AssertionError("native RVR source artifact not VERIFIED")
    if recomputation["recomputationStatus"] != "REPRODUCED":
        raise AssertionError("native RVR source artifact not REPRODUCED")

    return {
        "gate": "RECEIPTOS_QEV_NATIVE_CAPSULE_PASS",
        "receiptosSource": {
            "commit": "45b46bf7df3a60b32583291f577a36bf19d22f00",
            "evidenceCapsuleSchema": "receiptos.evidence_capsule.v0",
            "portableProofObjectSchema": "receiptos.portable_proof_object.v0",
        },
        "rvr": {
            "outcome": bundle["receipt"]["outcome"],
            "reasonCode": bundle["receipt"]["reasonCode"],
            "recomputationStatus": recomputation["recomputationStatus"],
            "resultDigest": bundle["receipt"]["resultDigest"],
        },
        "receiptos": {
            "receiptRoot": proof["receipt_root"],
            "receiptRootMatch": capsule["receipt_root"]["match"],
            "verifierStatus": capsule["verifier_result"]["status"],
            "proofObjectId": proof["proof_object_id"],
            "proofRef": proof["proof_ref"],
            "anchorRef": proof["anchor_ref"],
        },
        "claimBoundary": {
            "physicalQpuExecution": "NOT_ESTABLISHED",
            "providerAuthenticity": "NOT_ESTABLISHED",
            "entropy": "NOT_ESTABLISHED",
            "receiptosPackaging": "ESTABLISHED_OVER_NATIVE_RVR_ARTIFACT",
        },
        "portableProofObject": proof,
        "normalizedReceiptOsEvidence": evidence,
    }

def main():
    try:
        print(json.dumps(run_gate(), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"ReceiptOS QEV gate failed: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
