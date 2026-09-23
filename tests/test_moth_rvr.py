"""Counts relation, native receipt identities and replay admission boundaries."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from qev import moth_rvr as native, moth_rvr_mutations as mutants
from qev.moth_comet import parse, encode, MothError
from qev.moth_rvr_relation import evaluate


class MothNativeRvrTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_claim, cls.seed_payloads = native.fixture()
        cls.roles = native.contract()
        cls.bundle = native.make_bundle(native.case_from_payloads(cls.seed_claim, cls.seed_payloads))

    def setUp(self):
        self.claim = copy.deepcopy(self.seed_claim)
        self.payloads = dict(self.seed_payloads)

    def result(self):
        return evaluate(self.claim, self.payloads, self.roles)

    def case(self):
        return native.case_from_payloads(self.claim, self.payloads)

    def bundle_for(self):
        return native.make_bundle(self.case())

    def test_preserved_native_replay(self):
        report = native.recompute(self.bundle, self.claim)
        self.assertEqual((report['verificationOutcome'], report['recomputationStatus']), ('VERIFIED', 'REPRODUCED'))
        self.assertEqual(report['identities']['resultDigest'], self.bundle['receipt']['resultDigest'])

    def test_empty_output_is_verified_consistency(self):
        report = self.result()
        self.assertEqual(report['outcome'], 'VERIFIED')
        out = report['observation']
        self.assertEqual((out['requestedBytes'], out['deliveredBytes'], out['reportedGrade']),
                         ('32', '0', 'hardware-insufficient-entropy'))
        self.assertEqual(out['delivery'], 'EMPTY_BUDGET_LIMITED')

    def test_recomputed_counts_and_witness(self):
        out = self.result()['observation']
        self.assertEqual((out['shots'], out['uniqueBitstrings'], out['width'], out['witnessS']),
                         ('2048', '2040', '20', '2.2890625'))

    def test_no_order_or_authentication_inferred(self):
        limits = self.result()['limits']
        self.assertEqual(limits['shotOrder'], 'UNAVAILABLE_COUNTS_ONLY')
        for key in ('providerAuthentication', 'entropyQualification', 'cryptographicRandomness', 'measurementProvenance'):
            self.assertEqual(limits[key], 'NOT_ESTABLISHED')

    def test_explicit_missing_member(self):
        del self.payloads[self.roles['roles']['result']]
        bundle = self.bundle_for()
        self.assertEqual(bundle['canonicalResult']['outcome'], 'UNVERIFIABLE')
        self.assertEqual(native.recompute(bundle, self.claim)['recomputationStatus'], 'REPRODUCED')

    def test_all_evidence_explicitly_missing(self):
        self.payloads = {}
        report = self.bundle_for()['canonicalResult']
        self.assertEqual(report['outcome'], 'UNVERIFIABLE')
        self.assertEqual(len(report['issues']['missing']), 17)

    def test_missing_does_not_erase_contradiction(self):
        self.claim, self.payloads = mutants.negative('member-identity')
        report = self.result()
        self.assertEqual(report['outcome'], 'REFUTED')
        self.assertTrue(report['issues']['missing'])
        self.assertTrue(report['issues']['contradiction'])

    def test_missing_present_payload_is_cannot_recompute(self):
        case = self.case()
        case['payloadsBase64'].pop('manifest.json')
        with self.assertRaises(native.CannotRecompute):
            native.make_bundle(case)

    def test_undeclared_role_is_rejected(self):
        case = self.case()
        case['evidenceSet']['members'].pop()
        with self.assertRaises(native.Rejected):
            native.make_bundle(case)

    def test_duplicate_role_is_rejected(self):
        case = self.case()
        case['evidenceSet']['members'][-1] = copy.deepcopy(case['evidenceSet']['members'][0])
        with self.assertRaises(native.Rejected):
            native.make_bundle(case)

    def test_unavailable_with_payload_is_rejected(self):
        case = self.case()
        role = case['evidenceSet']['members'][0]['id']
        case['evidenceSet']['members'][0] = {'id': role, 'status': 'UNAVAILABLE',
            'reasonCode': 'qev.moth.rvr.v0.evidence_unavailable'}
        with self.assertRaises(Exception) as caught:
            native.make_bundle(case)
        self.assertEqual(caught.exception.reason_code, 'rvr.gate.evidence_closure_incomplete')

    def test_uncommitted_payload_is_rejected(self):
        case = self.case()
        case['payloadsBase64']['extra.json'] = 'e30='
        with self.assertRaises(Exception) as caught:
            native.make_bundle(case)
        self.assertEqual(caught.exception.reason_code, 'rvr.gate.evidence_closure_incomplete')

    def test_payload_identity_tamper(self):
        case = self.case()
        case['payloadsBase64']['manifest.json'] = 'e30='
        with self.assertRaises(Exception) as caught:
            native.make_bundle(case)
        self.assertEqual(caught.exception.reason_code, 'rvr.gate.identity_mismatch')

    def test_invalid_base64(self):
        case = self.case()
        case['payloadsBase64']['manifest.json'] = '%'
        with self.assertRaises(Exception) as caught:
            native.make_bundle(case)
        self.assertEqual(caught.exception.reason_code, 'rvr.gate.schema_invalid')

    def test_malformed_json_is_not_unverifiable(self):
        self.payloads['manifest.json'] = b'{'
        with self.assertRaises(MothError):
            self.bundle_for()

    def test_duplicate_json_key(self):
        self.payloads['terminal-observation.json'] = b'{"a":1,"a":2}'
        with self.assertRaises(MothError):
            self.bundle_for()

    def test_malformed_with_missing_still_rejected(self):
        for role in ('manifest.json', self.roles['roles']['result']):
            with self.subTest(role=role):
                self.payloads = {role: b'null'}
                with self.assertRaises(native.Rejected):
                    self.bundle_for()
        self.payloads = {self.roles['roles']['request']: b'{"mode":"qpu","params":false}'}
        with self.assertRaises(native.Rejected):
            self.bundle_for()

    def test_boolean_count_is_malformed(self):
        def edit(out):
            out['raw']['counts'][next(iter(out['raw']['counts']))] = True
        self.claim, self.payloads = mutants.edit_result(self.claim, self.payloads, edit)
        with self.assertRaises(native.Rejected):
            self.bundle_for()

    def test_counts_hash_contradiction(self):
        self.claim, self.payloads = mutants.edit_result(self.claim, self.payloads,
            lambda out: out['raw'].update(counts_sha256='0' * 64))
        report = self.bundle_for()['canonicalResult']
        self.assertEqual(report['outcome'], 'REFUTED')
        self.assertIn('COUNTS:COUNTS_HASH', report['issues']['contradiction'])

    def test_empty_grade_contradiction(self):
        self.claim, self.payloads = mutants.negative('counts-refutation')
        report = self.bundle_for()['canonicalResult']
        self.assertEqual(report['outcome'], 'REFUTED')
        self.assertIn('COUNTS:EMPTY_OUTPUT_GRADE', report['issues']['contradiction'])

    def test_nested_counts_missing(self):
        self.claim, self.payloads = mutants.edit_result(self.claim, self.payloads,
            lambda out: out['raw'].pop('counts'))
        self.assertEqual(self.bundle_for()['canonicalResult']['outcome'], 'UNVERIFIABLE')

    def test_certificate_assertion_is_not_authentication(self):
        self.claim, self.payloads = mutants.edit_result(self.claim, self.payloads,
            lambda out: out.update(certificate={'certified': True, 'grade': 'hardware'}))
        report = self.bundle_for()['canonicalResult']
        self.assertEqual(report['outcome'], 'VERIFIED')
        self.assertEqual(report['limits']['providerAuthentication'], 'NOT_ESTABLISHED')

    def test_member_order_is_normalized(self):
        case = self.case()
        case['evidenceSet']['members'].reverse()
        report = native.recompute(self.bundle, self.claim, case)
        self.assertEqual(report['recomputationStatus'], 'REPRODUCED')

    def test_reencoded_consistent_record_diverges(self):
        self.claim, self.payloads = mutants.controls()['counts-key-order']
        changed = self.bundle_for()
        self.assertEqual(changed['canonicalResult']['outcome'], 'VERIFIED')
        # A new independently selected claim is a different record, not a
        # candidate for the original claim. Same claim with changed unused
        # JSON whitespace is instead a contradiction, and still DIVERGED.
        self.assertNotEqual(changed['receipt']['claimDigest'], self.bundle['receipt']['claimDigest'])
        self.claim = copy.deepcopy(self.seed_claim)
        report = native.recompute(self.bundle, self.claim, self.case())
        self.assertEqual((report['verificationOutcome'], report['recomputationStatus']), ('REFUTED', 'DIVERGED'))

    def test_independent_claim_required(self):
        self.claim['captureClaim']['jobId'] = 'substituted'
        with self.assertRaisesRegex(native.Rejected, 'INDEPENDENT_CLAIM_MISMATCH'):
            native.recompute(self.bundle, self.claim)

    def test_candidate_cannot_substitute_claim(self):
        self.claim['captureClaim']['jobId'] = 'substituted'
        with self.assertRaisesRegex(native.Rejected, 'INDEPENDENT_CLAIM_MISMATCH'):
            native.recompute(self.bundle, self.seed_claim, self.case())

    def test_fabricated_result_even_with_rehashed_receipt(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['canonicalResult']['observation']['deliveredBytes'] = '32'
        rvr, _, _, _ = native.context()
        bundle['receipt']['resultDigest'] = rvr.canonical_digest(bundle['canonicalResult'])
        with self.assertRaisesRegex(native.Rejected, 'STORED_RESULT_FABRICATED'):
            native.recompute(bundle, self.claim, self.case())

    def test_receipt_projection_tamper(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['receipt']['outcome'] = 'REFUTED'
        with self.assertRaises(Exception) as caught:
            native.recompute(bundle, self.claim)
        self.assertEqual(caught.exception.reason_code, 'rvr.gate.result_projection_mismatch')

    def test_profile_identity_tamper(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['verificationProfile']['profileId'] = 'other'
        with self.assertRaisesRegex(native.Rejected, 'PROFILE_IDENTITY'):
            native.recompute(bundle, self.claim)

    def test_authentication_claim_rejected(self):
        self.claim['providerAuthentication'] = 'AUTHENTICATED'
        with self.assertRaises(native.Rejected):
            self.bundle_for()

    def test_unknown_role_cannot_be_written(self):
        self.payloads['../escape.json'] = b'{}'
        with self.assertRaises(native.Rejected):
            self.case()

    def test_no_provider_network(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            self.assertEqual(native.recompute(self.bundle, self.claim)['recomputationStatus'], 'REPRODUCED')

    def test_source_dependency_identity_and_unavailability(self):
        profile = native.check_sources()
        names = set(native.FILES) | {native.PROFILE + '/sources.json'}
        names.update(row['path'] for row in native.dependencies(profile))
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in names:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes((native.ROOT / name).read_bytes())
            self.assertEqual(native.context(root)[1]['profileId'], native.PROFILE_ID)
            path = root / 'qev/moth_comet.py'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(native.CannotRecompute):
                native.context(root)
            path.unlink()
            with self.assertRaises(native.CannotRecompute):
                native.context(root)

    def test_mutation_inventory_and_kills(self):
        recorded = parse((native.ROOT / native.PROFILE / 'conformance.json').read_bytes())
        self.assertEqual(recorded, mutants.inventory())
        report = mutants.run()
        self.assertTrue(mutants.successful(report), report)


if __name__ == '__main__':
    unittest.main()
