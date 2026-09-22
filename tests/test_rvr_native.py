import copy
import hashlib
import json
from pathlib import Path
import unittest

from qev import rvr_native, rvr_mutations

ROOT = Path(__file__).resolve().parents[1]

class NativeRvrTests(unittest.TestCase):
    def context(self):
        profile, digest, constraints, pinned, schema, manifest, manifest_bytes = (
            rvr_native.load_profile_context()
        )
        vectors = rvr_native.rvr.parse_json_bytes(
            pinned["verification-vectors"], "verification-vectors"
        )
        return profile, digest, schema, vectors

    def test_native_profile_gate(self):
        report = rvr_native.run_gate()
        self.assertEqual(report["gate"], "RVR_QEV_NATIVE_PROFILE_PASS")
        self.assertEqual(report["profileId"], "rvr-qev-preserved-observation-v0")
        self.assertEqual(report["rvrCore"]["adapterSha256"],
                         "03505efc8ee993f118fad2c71f706870d25de0da61a393a1f18f7b310bded235")

    def test_stochastic_boundary_verified_but_diverged(self):
        report = rvr_native.run_gate()
        boundary = report["stochasticBoundary"]
        self.assertEqual(boundary["alternateSampleVerificationOutcome"], "VERIFIED")
        self.assertEqual(boundary["alternateSampleRecomputationStatus"], "DIVERGED")
        self.assertTrue(boundary["sameCanonicalResultDigest"])
        self.assertTrue(boundary["differentEvidenceSetDigest"])
    def test_receipt_is_native_six_field_rvr_envelope(self):
        profile, digest, schema, vectors = self.context()
        case = vectors["verificationCases"]["reproduced"]
        bundle = rvr_native.make_bundle(case, profile, digest, schema)
        self.assertEqual(
            set(bundle["receipt"]),
            {"claimDigest","evidenceSetDigest","verificationProfileDigest",
             "outcome","reasonCode","resultDigest"},
        )
        self.assertEqual(bundle["receipt"]["outcome"], "VERIFIED")
        rvr_native.rvr.validate_receipt_envelope(bundle, digest, schema)

    def test_same_semantic_result_does_not_mean_reproduced(self):
        profile, digest, schema, vectors = self.context()
        original = vectors["verificationCases"]["reproduced"]
        bundle = rvr_native.make_bundle(original, profile, digest, schema)
        alternate = rvr_native.recompute(
            bundle, vectors["verificationCases"]["alternateValidSample"], digest, schema
        )
        self.assertEqual(alternate["verificationOutcome"], "VERIFIED")
        self.assertEqual(alternate["recomputationStatus"], "DIVERGED")
        self.assertEqual(alternate["canonicalResultDigest"], bundle["receipt"]["resultDigest"])

    def test_refuted_and_unverifiable_are_distinct(self):
        report = rvr_native.run_gate()["cases"]
        self.assertEqual(report["REFUTED_COUNTS"]["verificationOutcome"], "REFUTED")
        self.assertEqual(report["RAW_UNAVAILABLE"]["verificationOutcome"], "UNVERIFIABLE")
        self.assertEqual(report["CANNOT_RECOMPUTE"]["recomputationStatus"], "CANNOT_RECOMPUTE")
        self.assertFalse(report["CANNOT_RECOMPUTE"]["evaluationPerformed"])
    def test_uncommitted_ambient_input_rejected(self):
        report = rvr_native.run_gate()["cases"]["HIDDEN_STATE_NEGATIVE_CONTROL"]
        self.assertEqual(report["gateStatus"], "REJECTED")
        self.assertEqual(report["reasonCode"], "rvr.gate.evidence_closure_incomplete")

    def test_optional_conformance_material_nonsemantic(self):
        report = rvr_native.run_gate()["cases"]
        self.assertEqual(
            report["OPTIONAL_EXPECTED_RESULTS_NONSEMANTIC"],
            report["REPRODUCED"],
        )

    def test_profile_is_portable_and_machine_path_free(self):
        paths = [
            ROOT/"profiles/qev-preserved-observation-v0/verification-profile.json",
            ROOT/"profiles/qev-preserved-observation-v0/profile.schema.json",
            ROOT/"profiles/qev-preserved-observation-v0/rvr-qev.schema.json",
            ROOT/"docs/RVR_QEV_PROFILE_V0.md",
        ]
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("C:" + "/Users/", text)
            self.assertNotIn("D:" + "/PAVLO", text)
            self.assertNotIn("\\" + "Users" + "\\msi", text)

    def test_vendored_rvr_core_exact_pin(self):
        path = ROOT/"vendor/rvr-v0/adapter.py"
        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "03505efc8ee993f118fad2c71f706870d25de0da61a393a1f18f7b310bded235",
        )
    def test_profile_constraints_reject_alternate_profile(self):
        report = rvr_native.run_gate()["profileSchemaBoundary"]
        self.assertTrue(report["genericManifestAccepted"])
        self.assertFalse(report["qevConstraintsAccepted"])
        self.assertTrue(report["tamperedConstraintsPinRejected"])

    def test_profile_regeneration_is_byte_exact(self):
        from tools.build_rvr_profile import generate
        current = (ROOT/"profiles/qev-preserved-observation-v0/verification-profile.json").read_bytes()
        self.assertEqual(generate(), current)

    def test_native_rvr_mutation_gate(self):
        report = rvr_mutations.run()
        self.assertTrue(rvr_mutations.successful(report), report["summary"])
        self.assertEqual(report["summary"]["KILLED"], 7)
        self.assertEqual(report["positiveControls"],
                         ["exact","reversed-members","reversed-payload-map"])
        for row in report["mutations"]:
            self.assertEqual(row["status"], "KILLED")
            self.assertTrue(all(row["controls"].values()))

    def test_elevated_physical_claim_is_not_native_rvr_success(self):
        profile, digest, schema, vectors = self.context()
        original = vectors["verificationCases"]["reproduced"]
        elevated = copy.deepcopy(original)
        package = json.loads(
            __import__("base64").b64decode(elevated["payloadsBase64"]["package"])
        )
        package["desired_claim"] = "AUTHENTIC_QPU_EXECUTION"
        package.pop("payload_sha256", None)
        from qev.checker import digest as qdigest, canonical
        package["payload_sha256"] = qdigest(package)
        raw = canonical(package)
        elevated["payloadsBase64"]["package"] = __import__("base64").b64encode(raw).decode()
        member = next(m for m in elevated["evidenceSet"]["members"] if m["id"]=="package")
        member["byteLength"] = str(len(raw))
        member["digest"] = hashlib.sha256(raw).hexdigest()
        bundle = rvr_native.make_bundle(original, profile, digest, schema)
        with self.assertRaises(rvr_native.rvr.GateRejection) as caught:
            rvr_native.recompute(bundle, elevated, digest, schema)
        self.assertEqual(caught.exception.reason_code, "rvr.qev.gate.unsupported_input")

if __name__ == "__main__":
    unittest.main()
