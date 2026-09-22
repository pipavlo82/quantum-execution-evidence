import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qev import moth_comet as m, moth_mutations as mutations, moth_replay as replay


class MothCometTests(unittest.TestCase):
    def setUp(self):
        self.args = mutations.seed()

    def change_output(self, edit, pulse=False):
        edit(self.args[4]['result']['output'])
        mutations.sync(self.args, pulse=pulse)
        return m.evaluate(*self.args)

    def test_actual_empty_output_is_consistent_not_entropy_certification(self):
        out = m.evaluate(*self.args)
        self.assertEqual(out['consistency'], 'CONSISTENT')
        self.assertEqual((out['shots'], out['uniqueBitstrings'], out['deliveredBytes']), (2048, 2040, 0))
        self.assertEqual(out['witnessS'], 2.2890625)
        self.assertEqual(out['certificatePresence'], 'ABSENT')
        self.assertEqual(out['commitmentObservation'], 'FIRST_SEEN_WITH_RESULT')
        self.assertEqual(out['limits'], m.LIMITS)
        self.assertNotIn('verified', out)

    def test_upstream_certificate_does_not_promote_claim(self):
        out = m.evaluate(*mutations.controls()['upstream_certificate_is_not_proof'])
        self.assertEqual(out['consistency'], 'CONSISTENT')
        self.assertEqual(out['limits']['entropyQualification'], 'NOT_ESTABLISHED')
        self.assertEqual(out['limits']['providerAuthentication'], 'NOT_ESTABLISHED')

    def test_counts_are_never_reconstructed_as_ordered_measurements(self):
        out = m.evaluate(*self.args)
        self.assertEqual(out['limits']['orderedMeasurements'], 'UNAVAILABLE_COUNTS_ONLY')
        self.assertNotIn('bitstrings', out)

    def test_semantic_negative_controls(self):
        for name, _, reason in mutations.MUTANTS:
            with self.subTest(name=name):
                out = m.evaluate(*mutations.negative(name))
                self.assertEqual((out['consistency'], out['reason']), ('REFUTED', reason))

    def test_each_requested_parameter_bound(self):
        for key, value in self.args[0]['params'].items():
            args = copy.deepcopy(self.args)
            args[0]['params'][key] = not value if type(value) is bool else value + 1
            with self.subTest(key=key):
                self.assertEqual(m.evaluate(*args)['reason'], 'REQUEST_PROFILE_MISMATCH')

    def test_boolean_is_not_integer(self):
        for bad in (True, False, -1, 0, 1.0, '1'):
            args = copy.deepcopy(self.args)
            counts = args[4]['result']['output']['raw']['counts']
            counts[next(iter(counts))] = bad
            mutations.sync(args)
            with self.subTest(bad=bad):
                self.assertEqual(m.evaluate(*args)['reason'], 'COUNT_VALUE')

    def test_count_width(self):
        def edit(out):
            counts = out['raw']['counts']
            counts['0'] = counts.pop(next(iter(counts)))
        self.assertEqual(self.change_output(edit)['reason'], 'COUNT_WIDTH')

    def test_count_total(self):
        def edit(out):
            counts = out['raw']['counts']
            counts[next(iter(counts))] += 1
        self.assertEqual(self.change_output(edit)['reason'], 'COUNT_TOTAL')

    def test_missing_counts_is_unverifiable(self):
        out = self.change_output(lambda out: out['raw'].pop('counts'))
        self.assertEqual((out['consistency'], out['reason']), ('UNVERIFIABLE', 'COUNTS_MISSING'))

    def test_job_and_engine_substitution(self):
        for role in (2, 3):
            for key in ('job_id', 'engine_id'):
                args = copy.deepcopy(self.args)
                target = args[role][0] if role == 2 else args[role]
                target[key] = 'substitution'
                with self.subTest(role=role, key=key):
                    self.assertEqual(m.evaluate(*args)['consistency'], 'REFUTED')

    def test_failed_job_never_becomes_consistent(self):
        self.args[2][-1]['status'] = 'failed'
        out = m.evaluate(*self.args)
        self.assertEqual((out['consistency'], out['reason']), ('UNVERIFIABLE', 'JOB_NOT_COMPLETED'))

    def test_duplicate_steps_rejected(self):
        self.args[2][-1]['steps'].append(copy.deepcopy(self.args[2][-1]['steps'][0]))
        self.assertEqual(m.evaluate(*self.args)['reason'], 'STEP_INVENTORY')

    def test_status_result_disagreement(self):
        self.args[4]['result']['output']['random']['hex'] = 'ff'
        self.assertEqual(m.evaluate(*self.args)['reason'], 'STATUS_RESULT_AGREEMENT')

    def test_provenance_build_mismatch(self):
        self.args[2][0]['steps'][0]['extra']['circuit_hash'] = '0' * 64
        self.assertEqual(m.evaluate(*self.args)['reason'], 'BUILD_circuit_hash')

    def test_pulse_provenance_mismatch(self):
        out = self.change_output(lambda o: o['provenance'].__setitem__('backend', 'changed'))
        self.assertEqual(out['reason'], 'PULSE_PROVENANCE')

    def test_marginal_mismatch(self):
        out = self.change_output(lambda o: o['device_fingerprint']['p1'].__setitem__(0, 0.0))
        self.assertEqual(out['reason'], 'MARGINAL_P1')

    def test_bell_pair_counts_mismatch(self):
        out = self.change_output(lambda o: o['bell_witness']['correlators'][0]['counts'].__setitem__('00', 999))
        self.assertEqual(out['reason'], 'WITNESS_COUNTS')

    def test_bell_qubit_mapping_mismatch(self):
        out = self.change_output(lambda o: o['bell_witness']['correlators'][0].__setitem__('qubits', [0, 1]))
        self.assertEqual(out['reason'], 'WITNESS_PAIR')

    def test_bad_entropy_report_agreement(self):
        out = self.change_output(lambda o: o['entropy_report'].__setitem__('h_bit', 1.0))
        self.assertEqual(out['reason'], 'ENTROPY_REPORT_AGREEMENT_h_bit')

    def test_output_length_mismatch(self):
        out = self.change_output(lambda o: o['random'].__setitem__('bytes', 32))
        self.assertEqual(out['reason'], 'OUTPUT_HEX_LENGTH')

    def test_secret_fields_rejected_without_echo(self):
        self.args[0]['params']['qpu_token'] = 'test-secret-not-real'
        out = m.evaluate(*self.args)
        self.assertEqual(out['reason'], 'SECRET_FIELD')
        self.assertNotIn('test-secret-not-real', json.dumps(out))

    def test_strict_json_boundary(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'"\\ud800"', b'[' * 40 + b']' * 40):
            with self.subTest(raw=raw), self.assertRaises(m.MothError):
                m.parse(raw)

    def test_source_mutations_have_exact_controls(self):
        report = mutations.run()
        self.assertTrue(mutations.successful(report), report)
        self.assertEqual(len(report['mutations']), 7)
        self.assertFalse(mutations.successful({'mutations': []}))
        report['mutations'][0]['controls'] = []
        self.assertFalse(mutations.successful(report))


class MothReplayTests(unittest.TestCase):
    def setUp(self):
        self.claim = m.parse((replay.FIXTURE / 'claim.json').read_bytes())
        self.directory = replay.FIXTURE / 'capture'

    def test_actual_capture_replays(self):
        out = replay.replay(self.directory, self.claim)
        self.assertEqual(out['consistency'], 'CONSISTENT', out)
        self.assertEqual(out['captureIntegrity'], 'MATCH_LOCAL_UNSIGNED_CLAIM')

    def test_independent_request_and_manifest_anchors(self):
        for key in ('manifestSha256', 'requestSha256'):
            claim = copy.deepcopy(self.claim)
            claim[key] = '0' * 64
            with self.subTest(key=key):
                self.assertEqual(replay.replay(self.directory, claim)['consistency'], 'REFUTED')

    def test_claim_cannot_promote_authenticity(self):
        self.claim['authority'] = 'AUTHENTICATED_QPU'
        self.assertEqual(replay.replay(self.directory, self.claim)['reason'], 'CLAIM_AUTHORITY')

    def test_capture_tampering_and_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'capture'
            shutil.copytree(self.directory, root)
            path = root / 'submit.body.json'
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            self.assertEqual(replay.replay(root, self.claim)['consistency'], 'REFUTED')
            path.unlink()
            self.assertEqual(replay.replay(root, self.claim)['reason'], 'CAPTURE_FILE_INVENTORY')

    def test_source_mismatch_blocks_replay(self):
        with patch.object(replay.sources, 'validate', return_value={'valid': False}):
            self.assertEqual(replay.replay(self.directory, self.claim)['consistency'], 'CANNOT_RECOMPUTE')

    def test_paths_do_not_escape(self):
        for value in ('../secret', '..', 'C:\\secret', '/secret', 'x/y'):
            with self.subTest(value=value), self.assertRaises(m.MothError):
                replay.safe_read(self.directory, value)

    def test_custom_capture_requires_explicit_claim(self):
        proc = subprocess.run([sys.executable, '-B', '-m', 'qev.moth_replay', str(self.directory)],
                              cwd=replay.ROOT, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b'--claim is required', proc.stderr)


if __name__ == '__main__':
    unittest.main()
