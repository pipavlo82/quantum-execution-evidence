"""Root integrity, RVR semantics and delivery remain separate axes."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from qev import moth_receiptos as portable, moth_receiptos_mutations as mutants, moth_rvr
from qev.moth_comet import encode, parse, sha, MothError
from qev.live_common import Rejected, CannotRecompute


class MothReceiptOsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = mutants.cases()
        cls.seed_saved, cls.seed_claim = cls.cases['verified']
        cls.raw = portable.unbase64(cls.seed_saved['attachment']['base64'])
        cls.bundle = parse(cls.raw)

    def setUp(self):
        self.saved = copy.deepcopy(self.seed_saved)
        self.claim = copy.deepcopy(self.seed_claim)

    def reject(self, name, reason):
        saved, claim = mutants.negative(name, self.saved, self.claim)
        with self.assertRaisesRegex(Rejected, reason):
            portable.replay(saved, claim)

    def test_native_root_and_rvr_reproduced(self):
        result = portable.replay(self.saved, self.claim)
        self.assertEqual(result['receiptOs']['rootStatus'], 'VERIFIED')
        self.assertEqual(result['receiptOs']['nativeStatus'], 'EXECUTED')
        self.assertEqual((result['rvr']['verificationOutcome'], result['rvr']['recomputationStatus']),
                         ('VERIFIED', 'REPRODUCED'))

    def test_exact_original_bundle_bytes_attached(self):
        self.assertEqual(self.raw, encode(self.bundle))
        native = self.saved['nativeReceiptOs']
        self.assertEqual(native['evidence']['changes']['diff_sha256'], sha(self.raw))
        self.assertEqual(native['summary']['source_evidence'], portable.REFERENCE)
        self.assertEqual(native['proof']['source_evidence_ref'], portable.REFERENCE)

    def test_reencoded_bundle_remains_distinct_but_valid(self):
        raw = json.dumps(self.bundle, separators=(',', ':')).encode() + b'\n'
        changed = portable.create(raw, self.claim)
        self.assertEqual(portable.unbase64(changed['attachment']['base64']), raw)
        result = portable.replay(changed, self.claim)
        self.assertEqual(result['rvr']['recomputationStatus'], 'REPRODUCED')
        self.assertNotEqual(result['receiptOs']['root'], self.saved['nativeReceiptOs']['verification']['receipt_root'])

    def test_payload_map_order_has_same_native_rvr_identity(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['evidenceSet']['members'].reverse()
        saved = portable.create(encode(bundle), self.claim)
        result = portable.replay(saved, self.claim)
        self.assertEqual(result['rvr']['identities'], self.saved['rvrReplay']['identities'])
        self.assertNotEqual(saved['attachment']['sha256'], self.saved['attachment']['sha256'])

    def test_zero_delivery_and_insufficient_entropy_retained(self):
        result = portable.replay(self.saved, self.claim)
        observation = result['observation']
        self.assertEqual((observation['requestedBytes'], observation['deliveredBytes'], observation['reportedGrade']),
                         ('32', '0', 'hardware-insufficient-entropy'))
        self.assertEqual(result['providerAuthentication'], 'NOT_ESTABLISHED')

    def test_refuted_rvr_can_have_valid_packaging_root(self):
        result = portable.replay(*self.cases['refuted'])
        self.assertEqual((result['receiptOs']['rootStatus'], result['rvr']['verificationOutcome']), ('VERIFIED', 'REFUTED'))
        self.assertEqual(result['rvr']['recomputationStatus'], 'REPRODUCED')
        self.assertIsNone(result['observation'])

    def test_unverifiable_rvr_can_have_valid_packaging_root(self):
        result = portable.replay(*self.cases['unverifiable'])
        self.assertEqual((result['receiptOs']['rootStatus'], result['rvr']['verificationOutcome']), ('VERIFIED', 'UNVERIFIABLE'))
        self.assertEqual(result['rvr']['recomputationStatus'], 'REPRODUCED')

    def test_no_clock_authorization_or_anchor_claim(self):
        native = self.saved['nativeReceiptOs']
        evidence = native['evidence']
        self.assertEqual(evidence['authorization']['authorization_checked_at'], 0)
        self.assertIsNone(evidence['authorization']['authorized_at_execution'])
        self.assertEqual(evidence['execution'], [])
        self.assertEqual(native['proof']['created_at'], '1970-01-01T00:00:00.000Z')
        self.assertIsNone(native['proof']['anchor_ref'])
        self.assertIn('compatibility sentinels', evidence['task']['prompt'])

    def test_original_rvr_limits_stay_frozen(self):
        inner = self.bundle['canonicalResult']['limits']
        self.assertEqual(inner['receiptOS'], 'NOT_INTEGRATED_FOR_THIS_PROFILE')
        self.assertEqual(inner['shotOrder'], 'UNAVAILABLE_COUNTS_ONLY')
        self.assertEqual(inner['providerAuthentication'], 'NOT_ESTABLISHED')

    def test_attachment_digest_tamper(self):
        self.reject('attachment-digest', 'ATTACHMENT_DIGEST')

    def test_unbound_reencoded_attachment(self):
        self.reject('root-covered-envelope', 'ENVELOPE_PROJECTION')

    def test_invalid_root_with_refreshed_native_projections(self):
        self.reject('native-root', 'RECEIPT_ROOT_MISMATCH')

    def test_stored_rvr_verdict(self):
        self.reject('saved-rvr-result', 'STORED_RVR_REPLAY')

    def test_stored_native_verification(self):
        self.reject('native-verification', 'NATIVE_VERIFICATION_PROJECTION')

    def test_stored_native_summary(self):
        self.reject('native-summary', 'NATIVE_SUMMARY_PROJECTION')

    def test_stored_native_proof(self):
        self.reject('native-proof', 'NATIVE_PROOF_PROJECTION')

    def test_packaging_profile_substitution(self):
        self.reject('packaging-profile', 'PACKAGING_PROFILE_IDENTITY')

    def test_independent_claim_substitution(self):
        self.reject('independent-claim', 'INDEPENDENT_CLAIM_MISMATCH')

    def test_create_also_requires_independent_claim(self):
        self.claim['captureClaim']['jobId'] = 'wrong-job'
        with self.assertRaisesRegex(Rejected, 'INDEPENDENT_CLAIM_MISMATCH'):
            portable.create(self.raw, self.claim)

    def test_rehashed_fabricated_rvr_result_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['canonicalResult']['observation']['deliveredBytes'] = '32'
        rvr, _, _, _ = moth_rvr.context()
        bundle['receipt']['resultDigest'] = rvr.canonical_digest(bundle['canonicalResult'])
        with self.assertRaisesRegex(Rejected, 'STORED_RESULT_FABRICATED'):
            portable.create(encode(bundle), self.claim)

    def test_valid_root_cannot_hide_forged_bundle(self):
        # Construct a self-consistent outer envelope without calling create.
        bundle = copy.deepcopy(self.bundle)
        bundle['canonicalResult']['observation']['deliveredBytes'] = '32'
        rvr, _, _, _ = moth_rvr.context()
        bundle['receipt']['resultDigest'] = rvr.canonical_digest(bundle['canonicalResult'])
        raw = encode(bundle)
        self.saved['attachment'].update(base64=base64.b64encode(raw).decode('ascii'), sha256=sha(raw))
        evidence = portable.envelope(bundle, raw, sha(encode(self.saved['profile'])))
        self.saved['nativeReceiptOs'] = portable.bridge('create', evidence)
        with self.assertRaisesRegex(Rejected, 'STORED_RESULT_FABRICATED'):
            portable.replay(self.saved, self.claim)

    def test_whole_bundle_replacement_needs_original_claim(self):
        replacement, _ = self.cases['refuted']
        with self.assertRaisesRegex(Rejected, 'INDEPENDENT_CLAIM_MISMATCH'):
            portable.replay(replacement, self.claim)

    def test_payload_removal_is_not_unverifiable(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['payloadsBase64'].pop('manifest.json')
        with self.assertRaisesRegex(CannotRecompute, 'COMMITTED_PRESENT_UNAVAILABLE'):
            portable.create(encode(bundle), self.claim)

    def test_anchor_ignored_by_native_root_but_rejected_by_profile(self):
        for field, value in (('tx_hash', '0xfake'), ('merkle_proof', ['0xfake']), ('network', 'sepolia')):
            with self.subTest(field=field):
                saved = copy.deepcopy(self.saved)
                evidence = saved['nativeReceiptOs']['evidence']
                evidence['anchor'][field] = value
                self.assertTrue(portable.bridge('verify', evidence)['verification']['ok'])
                with self.assertRaisesRegex(Rejected, 'ENVELOPE_PROJECTION_OR_ANCHOR'):
                    portable.replay(saved, self.claim)

    def test_rehashed_envelope_with_false_authorization_rejected(self):
        evidence = self.saved['nativeReceiptOs']['evidence']
        evidence['authorization']['authorized_at_execution'] = True
        self.saved['nativeReceiptOs'] = portable.bridge('create', evidence)
        with self.assertRaisesRegex(Rejected, 'ENVELOPE_PROJECTION'):
            portable.replay(self.saved, self.claim)

    def test_invalid_base64_and_attachment_bounds(self):
        for value in ('%', 'Zg===', 'A' * (4 * ((portable.MAX_BUNDLE_BYTES + 2) // 3) + 1)):
            with self.subTest(length=len(value)), self.assertRaises(Rejected):
                portable.unbase64(value)
        with self.assertRaises(Rejected):
            portable.create(b' ' * (portable.MAX_BUNDLE_BYTES + 1), self.claim)

    def test_malformed_json_and_duplicate_keys(self):
        for raw in (b'{', b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":"\\ud800"}'):
            with self.subTest(raw=raw), self.assertRaises(MothError):
                portable.create(raw, self.claim)

    def test_closed_shapes_and_wrong_types(self):
        changes = (lambda s: s.update(extra=True), lambda s: s.pop('attachment'),
                   lambda s: s['nativeReceiptOs'].update(evidence=None),
                   lambda s: s['nativeReceiptOs']['evidence'].update(anchor=[]),
                   lambda s: s['attachment'].update(id='other'),
                   lambda s: s['nativeReceiptOs']['verification'].update(ok=1))
        for change in changes:
            saved = copy.deepcopy(self.saved)
            change(saved)
            with self.subTest(change=change), self.assertRaises(Rejected):
                portable.replay(saved, self.claim)

    def test_malformed_root_format(self):
        for value in (None, True, '', '0X' + 'a' * 64, '0x' + 'G' * 64):
            self.saved['nativeReceiptOs']['evidence']['anchor']['receipt_root'] = value
            with self.subTest(value=value), self.assertRaisesRegex(Rejected, 'RECEIPT_ROOT_FORMAT'):
                portable.replay(self.saved, self.claim)

    def test_replay_executes_native_verification(self):
        with patch.object(portable, 'bridge', wraps=portable.bridge) as native:
            portable.replay(self.saved, self.claim)
            self.assertEqual(native.call_count, 1)
            self.assertEqual(native.call_args.args[0], 'verify')

    def test_runtime_unavailable_and_failure_are_cannot_recompute(self):
        with patch.object(portable.subprocess, 'run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(CannotRecompute, 'RECEIPTOS_RUNTIME_UNAVAILABLE'):
                portable.replay(self.saved, self.claim)
        with patch.object(portable.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, b'', b'failed')):
            with self.assertRaisesRegex(CannotRecompute, 'RECEIPTOS_BRIDGE_FAILED'):
                portable.replay(self.saved, self.claim)

    def test_changed_dependency_is_cannot_recompute(self):
        original = portable.read
        def altered(root, name):
            raw = original(root, name)
            return raw + b'\n' if name.endswith('/canon/receipt-root.ts') else raw
        with patch.object(portable, 'read', side_effect=altered):
            with self.assertRaisesRegex(CannotRecompute, 'PACKAGING_DEPENDENCY_IDENTITY'):
                portable.replay(self.saved, self.claim)

    def test_missing_dependency_is_cannot_recompute(self):
        original = portable.read
        def missing(root, name):
            if name.endswith('/verify/verify-receipt.ts'):
                raise FileNotFoundError(name)
            return original(root, name)
        with patch.object(portable, 'read', side_effect=missing):
            with self.assertRaises(CannotRecompute):
                portable.replay(self.saved, self.claim)

    def test_source_inventory_cannot_be_reduced(self):
        original = portable.read
        def reduced(root, name):
            raw = original(root, name)
            if name == portable.PROFILE + '/sources.json':
                lock = parse(raw)
                lock.pop('qev/moth_receiptos_bridge.ts')
                return encode(lock)
            return raw
        with patch.object(portable, 'read', side_effect=reduced):
            with self.assertRaises(CannotRecompute):
                portable.check_sources()

    def test_no_provider_network(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            result = portable.replay(self.saved, self.claim)
        self.assertEqual(result['rvr']['recomputationStatus'], 'REPRODUCED')

    def test_cli_outcomes_and_exact_export(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, (saved, claim) in self.cases.items():
                (root / 'claim.json').write_bytes(encode(claim))
                (root / 'artifact.json').write_bytes(encode(saved))
                p = subprocess.run([sys.executable, '-B', '-m', 'qev.moth_receiptos_cli', 'replay',
                    '--artifact', str(root / 'artifact.json'), '--claim', str(root / 'claim.json')],
                    cwd=portable.ROOT, capture_output=True, timeout=30)
                self.assertEqual(p.returncode, {'verified': 0, 'refuted': 1, 'unverifiable': 3}[name], p.stderr)
                self.assertEqual(parse(p.stdout)['rvr']['verificationOutcome'], name.upper())
            (root / 'claim.json').write_bytes(encode(self.claim))
            (root / 'bundle.json').write_bytes(self.raw)
            p = subprocess.run([sys.executable, '-B', '-m', 'qev.moth_receiptos_cli', 'export', '--bundle',
                str(root / 'bundle.json'), '--claim', str(root / 'claim.json'), '--output', str(root / 'export.json')],
                cwd=portable.ROOT, capture_output=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout, b'')
            self.assertEqual((root / 'export.json').read_bytes(), encode(self.saved))

    def test_source_mutants_and_controls(self):
        inventory = parse((portable.ROOT / portable.PROFILE / 'conformance.json').read_bytes())
        self.assertEqual(inventory, mutants.inventory())
        result = mutants.run()
        self.assertTrue(mutants.successful(result), result)


if __name__ == '__main__':
    unittest.main()
