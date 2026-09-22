import unittest
from qev import ibm_runtime_native

class IbmRuntimeAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.report=ibm_runtime_native.run_gate()

    def test_gate(self):
        self.assertEqual(self.report["gate"],"QEV_IBM_RUNTIME_ADAPTER_V0_PASS")

    def test_recorded_fixture_binds_without_authentication(self):
        p=self.report["positive"]
        self.assertEqual(p["executionBinding"]["executionBinding"],"BOUND")
        self.assertEqual(p["providerAuthentication"],"NOT_ESTABLISHED")
        self.assertEqual(self.report["fixtureAuthority"],"OFFLINE_CONFORMANCE_FIXTURE_NOT_LIVE_IBM")

    def test_six_adapter_mutations_refute(self):
        self.assertEqual(len(self.report["mutations"]),6)
        for name,result in self.report["mutations"].items():
            self.assertEqual(result["executionBinding"]["executionBinding"],"REFUTED",name)

    def test_malformed_bitstrings_rejected(self):
        self.assertEqual(self.report["malformedBitstrings"],"REJECTED")

    def test_live_execution_not_claimed(self):
        b=self.report["boundaries"]
        self.assertEqual(b["liveIBMJob"],"NOT_EXECUTED")
        self.assertEqual(b["realQpuExecution"],"NOT_ESTABLISHED")
        self.assertEqual(b["providerAuthentication"],"NOT_ESTABLISHED")

if __name__=="__main__": unittest.main()
