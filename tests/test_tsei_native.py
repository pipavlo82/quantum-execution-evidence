import unittest
from qev import tsei_native

class NativeTseiQevTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = tsei_native.run_gate()

    def test_gate_passes_and_exact_source_is_pinned(self):
        self.assertEqual(self.report["gate"], "TSEI_QEV_NATIVE_PRESERVATION_PASS")
        self.assertEqual(
            self.report["tseiSource"]["commit"],
            "45b46bf7df3a60b32583291f577a36bf19d22f00",
        )

    def test_stable_control(self):
        case = self.report["cases"]["stable"]
        self.assertEqual(case["classification"], "stable")
        self.assertTrue(case["normative_match"])
        self.assertTrue(case["stability_match"])
        self.assertTrue(case["forbidden_variant_match"])
        self.assertFalse(case["allowed_variant_changed"])

    def test_allowed_representation_change_stays_stable(self):
        case = self.report["cases"]["allowed_variant"]
        self.assertEqual(case["classification"], "stable")
        self.assertTrue(case["allowed_variant_changed"])
        self.assertTrue(case["normative_match"])
    def test_evidence_identity_change_is_history_sensitive(self):
        case = self.report["cases"]["history_sensitive"]
        self.assertEqual(case["classification"], "history_sensitive")
        self.assertTrue(case["normative_match"])
        self.assertFalse(case["stability_match"])
        self.assertTrue(case["forbidden_variant_match"])

    def test_semantic_result_digest_change_is_violation(self):
        case = self.report["cases"]["violation"]
        self.assertEqual(case["classification"], "violation")
        self.assertFalse(case["normative_match"])

    def test_tsei_does_not_elevate_lower_layer_claims(self):
        boundary = self.report["boundaries"]
        self.assertEqual(boundary["rvrVerification"], "LOWER_LAYER_INPUT")
        self.assertEqual(boundary["receiptosPackaging"], "SEPARATE_LAYER")
        self.assertEqual(boundary["physicalQpuExecution"], "NOT_ESTABLISHED")
        self.assertEqual(boundary["providerAuthenticity"], "NOT_ESTABLISHED")
        self.assertEqual(boundary["entropy"], "NOT_ESTABLISHED")

    def test_profile_declares_protected_relation_explicitly(self):
        relation = self.report["protectedRelation"]
        self.assertIn("semantic outcome", relation["normative"])
        self.assertEqual(relation["stability"], "evidence-set identity")
        self.assertEqual(relation["allowedVariant"], "payload-map representation order")
        self.assertEqual(relation["forbidden"], "claim identity")

if __name__ == "__main__":
    unittest.main()
