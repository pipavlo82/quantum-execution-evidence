import unittest
from qev import provider_binding_native

class ProviderExecutionBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=provider_binding_native.run_gate()

    def test_gate_passes(self):
        self.assertEqual(self.report["gate"],"QEV_PROVIDER_EXECUTION_BINDING_V0_PASS")

    def test_positive_is_bound_but_not_authenticated(self):
        x=self.report["positive"]
        self.assertEqual(x["executionBinding"],"BOUND")
        self.assertEqual(x["providerAuthentication"],"NOT_ESTABLISHED")
        self.assertTrue(all(x["axes"].values()))
        self.assertFalse(x["claimBoundary"]["providerAuthenticated"])
        self.assertFalse(x["claimBoundary"]["physicalQpuExecutionAuthenticated"])

    def test_all_eight_binding_mutations_refute(self):
        self.assertEqual(self.report["counts"],{"bindingAxes":8,"mutationsRefuted":8})
        for name,result in self.report["mutations"].items():
            self.assertEqual(result["executionBinding"],"REFUTED",name)
            self.assertFalse(result["axes"][name],name)

    def test_unverified_provider_assertion_cannot_elevate_authentication(self):
        x=self.report["unverifiedAuthentication"]
        self.assertEqual(x["executionBinding"],"BOUND")
        self.assertEqual(x["providerAuthentication"],"NOT_ESTABLISHED")
        self.assertFalse(x["claimBoundary"]["providerAuthenticated"])

    def test_provider_specific_adapter_is_not_faked(self):
        b=self.report["boundaries"]
        self.assertEqual(b["providerSpecificAdapter"],"NOT_INTEGRATED")
        self.assertEqual(b["executionBinding"],"ESTABLISHED_OVER_SUPPLIED_PROVIDER_ARTIFACT")
        self.assertEqual(b["entropy"],"NOT_ESTABLISHED")

if __name__=="__main__": unittest.main()
