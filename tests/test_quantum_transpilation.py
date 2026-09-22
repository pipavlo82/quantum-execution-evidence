import unittest
from qev import quantum_transpile_native

class QuantumTranspilationBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = quantum_transpile_native.run_gate()

    def test_gate_passes(self):
        self.assertEqual(self.report["gate"], "QEV_QUANTUM_LAYOUT_TRANSPILATION_BOUNDARY_PASS")

    def test_two_distinct_physical_layouts_preserve_logical_relation(self):
        a,b=self.report["layouts"]["layoutA"],self.report["layouts"]["layoutB"]
        self.assertEqual(a["tseiClassification"],"stable"); self.assertEqual(b["tseiClassification"],"stable")
        self.assertNotEqual(a["layout"],b["layout"]); self.assertNotEqual(a["physicalCircuitDigest"],b["physicalCircuitDigest"])

    def test_gate_mutation_is_violation(self):
        x=self.report["negativeControls"]["gateMutation"]["result"]
        self.assertEqual(x["classification"],"violation"); self.assertFalse(x["normative_match"])

    def test_invalid_measurement_and_layout_are_unresolved(self):
        for name in ("measurementMappingMutation","nonBijectiveLayout"):
            x=self.report["negativeControls"][name]["result"]
            self.assertEqual(x["classification"],"unresolved")
            self.assertEqual(x["unresolved_reason"],"target_recompute_failed")

    def test_execution_binding_does_not_claim_provider_authenticity(self):
        x=self.report["executionBinding"]
        self.assertEqual(x["authority"],"SUPPLIED_SIDECAR_NOT_PROVIDER_AUTHENTICATED")
        self.assertEqual(self.report["boundaries"]["physicalQpuExecution"],"NOT_ESTABLISHED")
        self.assertEqual(self.report["boundaries"]["providerAuthenticity"],"NOT_ESTABLISHED")

    def test_scope_does_not_claim_general_compiler_equivalence(self):
        b=self.report["boundaries"]
        self.assertEqual(b["arbitraryGateOptimizationEquivalence"],"NOT_ESTABLISHED")
        self.assertEqual(b["routingSwapEquivalence"],"NOT_ESTABLISHED")
        self.assertEqual(b["logicalSemantics"],"EXACT_ORDERED_GATE_AND_MEASUREMENT_RELATION_UNDER_LAYOUT_BIJECTION")

if __name__=="__main__": unittest.main()
