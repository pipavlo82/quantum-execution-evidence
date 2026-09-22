import copy
import json
import unittest

from qev import receiptos_native, rvr_native

class NativeReceiptOsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = receiptos_native.run_gate()

    def test_native_receiptos_gate_passes(self):
        self.assertEqual(self.report["gate"], "RECEIPTOS_QEV_NATIVE_CAPSULE_PASS")
        self.assertEqual(
            self.report["receiptosSource"]["commit"],
            "45b46bf7df3a60b32583291f577a36bf19d22f00",
        )

    def test_native_capsule_and_portable_proof_object_shapes(self):
        proof = self.report["portableProofObject"]
        capsule = proof["evidence_capsule"]
        self.assertEqual(proof["schema"], "receiptos.portable_proof_object.v0")
        self.assertEqual(proof["proof_system"], "ReceiptOS")
        self.assertEqual(capsule["schema"], "receiptos.evidence_capsule.v0")
        self.assertTrue(capsule["receipt_root"]["match"])
        self.assertEqual(capsule["verifier_result"], {"ok": True, "status": "verified"})
        self.assertIsNone(proof["anchor_ref"])

    def test_rvr_identity_is_preserved_as_source_relation(self):
        self.assertEqual(self.report["rvr"]["outcome"], "VERIFIED")
        self.assertEqual(self.report["rvr"]["recomputationStatus"], "REPRODUCED")
        self.assertEqual(
            self.report["rvr"]["reasonCode"], "rvr.qev.v0.relation_satisfied"
        )
    def test_receiptos_packaging_does_not_elevate_qpu_or_entropy(self):
        boundary = self.report["claimBoundary"]
        self.assertEqual(boundary["physicalQpuExecution"], "NOT_ESTABLISHED")
        self.assertEqual(boundary["providerAuthenticity"], "NOT_ESTABLISHED")
        self.assertEqual(boundary["entropy"], "NOT_ESTABLISHED")
        self.assertEqual(
            boundary["receiptosPackaging"], "ESTABLISHED_OVER_NATIVE_RVR_ARTIFACT"
        )

    def test_anchor_independence(self):
        evidence = copy.deepcopy(self.report["normalizedReceiptOsEvidence"])
        root = self.report["receiptos"]["receiptRoot"]
        evidence["anchor"]["tx_hash"] = "0x" + "ab" * 32
        evidence["anchor"]["contract"] = "0x" + "12" * 20
        evidence["anchor"]["receipt_root"] = "0x" + "ff" * 32
        # The native bridge computes ReceiptOS root over evidence with top-level anchor removed.
        from pathlib import Path
        bridge = Path(receiptos_native.BRIDGE).read_text(encoding="utf-8")
        self.assertIn("delete clone.anchor", bridge)
        # Stored root mutation is observation metadata and cannot rewrite the already packaged proof root.
        self.assertEqual(self.report["portableProofObject"]["receipt_root"], root)

    def test_provenance_verifier_status_is_receipt_root_status_only(self):
        summary = self.report["portableProofObject"]["provenance_summary"]
        self.assertEqual(summary["verifier_status"], "verified")
        self.assertEqual(summary["receipt_root_status"], "verified")
        self.assertEqual(summary["anchor_status"], "missing")
        self.assertEqual(summary["risk_flags"], [])
    def test_refuted_rvr_is_not_silently_promoted(self):
        profile, digest, _, pinned, schema, _, _ = rvr_native.load_profile_context()
        vectors = rvr_native.rvr.parse_json_bytes(
            pinned["verification-vectors"], "verification-vectors"
        )
        refuted = vectors["verificationCases"]["refutedCounts"]
        bundle = rvr_native.make_bundle(refuted, profile, digest, schema)
        recomputation = rvr_native.recompute(bundle, refuted, digest, schema)
        self.assertEqual(bundle["receipt"]["outcome"], "REFUTED")
        self.assertEqual(recomputation["verificationOutcome"], "REFUTED")
        packaged = receiptos_native._run_bridge(bundle, recomputation)
        proof = packaged["portableProofObject"]
        result = next(
            section for section in proof["evidence_capsule"]["capsule"]["sections"]
            if section["id"] == "result"
        )
        self.assertEqual(result["status"], "invalid")
        self.assertNotEqual(result["summary"], "Native RVR relation is VERIFIED.")

if __name__ == "__main__":
    unittest.main()
