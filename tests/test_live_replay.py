"""Offline adversarial tests. Expectations are not production semantic inputs."""
import base64
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from qev.live_common import ROOT, PROFILE, ROLES, Rejected, CannotRecompute, parse, encode, sha, read, physical_bytes
from qev.live_cli import fixture
from qev.live_math import project, E, Z, Unsupported
from qev.live_native import case_from_payloads, make_bundle, recompute, context, tsei, bridge
from qev.live_portable import create, replay, unbase64
from qev.live_mutations import inventory, admit, controls, negative, edit, refresh_record, run


class ParserTests(unittest.TestCase):
    def test_duplicate(self):
        with self.assertRaises(Rejected): parse(b'{"a":1,"a":2}')

    def test_nonfinite(self):
        for data in (b'NaN', b'Infinity', b'-Infinity', b'1e999'):
            with self.subTest(data=data), self.assertRaises(Rejected): parse(data)

    def test_size(self):
        with self.assertRaises(Rejected): parse(b' ' * 4_194_305)

    def test_depth(self):
        with self.assertRaises(Rejected): parse(b'['*33 + b'0' + b']'*33)

    def test_unicode(self):
        for raw in (b'"\xff"', b'"\\ud800"'):
            with self.subTest(raw=raw), self.assertRaises(Rejected): parse(raw)

    def test_integer_range(self):
        with self.assertRaises(Rejected): parse(b'9007199254740992')

    def test_paths(self):
        for name in ('../claim.json', '/tmp/x', 'https://example/x', 'a\\b', 'a//b', './a'):
            with self.subTest(name=name), self.assertRaises(Rejected): read(ROOT, name)

    def test_symlink(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            p = Path(tmp)
            (p/'target').write_bytes(b'{}')
            try:
                (p/'link').symlink_to(p/'target')
            except OSError:
                # Windows without symlink privilege: exercise the actual ancestor
                # guard with a filesystem predicate, never count an unrun OS probe.
                with patch.object(Path, 'is_symlink', return_value=True):
                    with self.assertRaises(Rejected): read(p, 'target')
            else:
                with self.assertRaises(Rejected): read(p, 'link')


class MathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.payloads = fixture()
        cls.logical = parse(cls.payloads['logical.json'])
        cls.target = parse(cls.payloads['isa-returned.json'])

    def test_field_inverse(self):
        for value in (Z, Z+1, E((2, 3, 5, 7)), Z*Z):
            self.assertEqual(value*value.inverse(), E(1))
        self.assertEqual(Z*Z*Z*Z, E(-1))

    def test_gate_identities_and_endianness(self):
        def snapshot(operations):
            value = copy.deepcopy(self.logical)
            value['operations'] = operations + copy.deepcopy(self.logical['operations'][-2:])
            return value
        def gate(name, qs, params=None):
            return {'name': name, 'qubits': qs, 'clbits': [], 'params': params or []}
        identity = project(snapshot([]))['operator']
        for name, qs in (('h', [0]), ('x', [1]), ('cx', [0, 1]), ('cz', [0, 1])):
            op = gate(name, qs)
            self.assertEqual(project(snapshot([op, op]))['operator'], identity)
        sx = gate('sx', [0])
        x = gate('x', [0])
        self.assertEqual(project(snapshot([sx, sx]))['operator'], project(snapshot([x]))['operator'])
        rz = gate('rz', [0], ['1.5707963267948966'])
        self.assertEqual(project(snapshot([rz, rz]))['operator'],
                         project(snapshot([gate('rz', [0], ['3.141592653589793'])]))['operator'])
        matrix = project(snapshot([x]))['operator']
        self.assertEqual([row[0] for row in matrix], [E().wire(), E(1).wire(), E().wire(), E().wire()])

    def test_captured_full_operator(self):
        self.assertEqual(project(self.logical)['operator'], project(self.target)['operator'])
        self.assertEqual(tsei(self.logical, self.target)['classification'], 'stable')

    def test_full_columns_relative_phase(self):
        source = copy.deepcopy(self.logical)
        source['operations'].insert(0, {'name': 'rz', 'params': ['3.141592653589793'], 'qubits': [0], 'clbits': []})
        a, b = project(source)['operator'], project(self.target)['operator']
        self.assertEqual([row[0] for row in a], [row[0] for row in b])
        self.assertNotEqual(a, b)
        self.assertEqual(tsei(source, self.target)['classification'], 'violation')

    def test_measurement_mapping(self):
        target = copy.deepcopy(self.target)
        for op in target['operations']:
            if op['name'] == 'measure': op['clbits'][0] = 1-op['clbits'][0]
        self.assertEqual(tsei(self.logical, target)['classification'], 'violation')

    def test_global_phase_quotient(self):
        source = copy.deepcopy(self.logical)
        source['global_phase'] = '1.5707963267948966'
        self.assertEqual(tsei(source, self.target)['classification'], 'stable')

    def test_global_phase_types_and_structured_failure(self):
        for value in ([], {}, None, True, 0, 1.5):
            source = copy.deepcopy(self.logical)
            source['global_phase'] = value
            with self.subTest(value=value), self.assertRaisesRegex(Rejected, 'GLOBAL_PHASE_TYPE'):
                project(source)
        source['global_phase'] = 'unsupported literal'
        with self.assertRaisesRegex(Unsupported, 'GLOBAL_PHASE_LITERAL'): project(source)
        source['global_phase'] = []
        process = subprocess.run([sys.executable, '-B', '-m', 'qev.live_math'],
                                 cwd=ROOT, input=encode(source), capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(parse(process.stdout), {'state': 'unresolved', 'reason': 'REJECTED:GLOBAL_PHASE_TYPE'})

    def test_unsupported_literal_not_rounded(self):
        target = copy.deepcopy(self.target)
        target['operations'][0]['params'] = ['1.5707963267948967']
        with self.assertRaises(Unsupported): project(target)
        self.assertEqual(tsei(self.logical, target)['classification'], 'unresolved')

    def test_unsupported_gates(self):
        for name in ('unknown', 'arbitrary_unitary'):
            target = copy.deepcopy(self.target)
            target['operations'][0]['name'] = name
            with self.subTest(name=name), self.assertRaises(Unsupported): project(target)

    def test_dynamic_and_reset_rejected(self):
        for name in ('reset', 'if_else', 'measure_2', 'measure_reset'):
            target = copy.deepcopy(self.target)
            target['operations'][0]['name'] = name
            with self.subTest(name=name), self.assertRaises(Rejected): project(target)

    def test_idle_wire_proof(self):
        target = copy.deepcopy(self.target)
        target['operations'][0]['qubits'] = [155]
        with self.assertRaisesRegex(Rejected, 'UNMAPPED'): project(target)

    def test_wrong_arity_duplicate_and_domain(self):
        for qs in ([], [0, 1], [0, 0], [-1], [156], [True]):
            target = copy.deepcopy(self.target)
            target['operations'][0]['qubits'] = qs
            with self.subTest(qs=qs), self.assertRaises(Rejected): project(target)

    def test_terminal_measurements(self):
        for mode in ('repeat', 'mid', 'missing', 'clbit-bool'):
            target = copy.deepcopy(self.target)
            if mode == 'repeat': target['operations'].append(copy.deepcopy(target['operations'][-1]))
            if mode == 'mid': target['operations'].insert(0, target['operations'].pop())
            if mode == 'missing': target['operations'].pop()
            if mode == 'clbit-bool': target['operations'][-1]['clbits'] = [True]
            with self.subTest(mode=mode), self.assertRaises(Rejected): project(target)


class LiveReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.claim, cls.payloads = fixture()
        cls.case = case_from_payloads(cls.claim, cls.payloads)
        cls.bundle = make_bundle(cls.case)
        cls.saved = create(cls.bundle, cls.claim)

    def result(self, payloads):
        return make_bundle(case_from_payloads(self.claim, payloads))['canonicalResult']

    def test_native_chain(self):
        out = replay(self.saved, self.claim)
        self.assertEqual(out['rvr']['verificationOutcome'], 'VERIFIED')
        self.assertEqual(out['rvr']['recomputationStatus'], 'REPRODUCED')
        self.assertEqual(out['rvr']['canonicalResult']['nativeTsei']['classification'], 'stable')
        self.assertEqual(out['receiptOs']['rootStatus'], 'VERIFIED')
        self.assertEqual(out['providerAuthentication'], 'NOT_ESTABLISHED')
        self.assertEqual(len(self.bundle['receipt']), 6)

    def test_exact_seed_bytes(self):
        self.assertEqual(len(self.payloads), 15)
        self.assertEqual(sha(self.payloads['measurements-ordered.c1c0.txt']), self.claim['anchors']['measurements-ordered.c1c0.txt'])
        actual = parse(unbase64(self.saved['attachment']['base64']))
        self.assertEqual({k: unbase64(v) for k, v in actual['payloadsBase64'].items()}, self.payloads)

    def test_job_binding(self):
        out = self.result(negative(self.payloads, 'assigned-job'))
        self.assertEqual(out['axes']['jobRequestBinding'], 'REFUTED')

    def test_raw_refresh_all_package_hashes(self):
        p = negative(self.payloads, 'raw-anchor')
        raw = p['measurements-ordered.c1c0.txt']
        bits = raw.decode().splitlines()
        from collections import Counter
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['result'].update(bitstrings=bits))
        p['measurement-counts.json'] = encode(dict(Counter(bits)))
        refresh_record(p)
        out = self.result(p)
        self.assertEqual(out['axes']['orderedRecordAgreement'], 'SATISFIED')
        self.assertEqual(out['axes']['histogramRecomputation'], 'SATISFIED')
        self.assertEqual(out['axes']['rawCommitment'], 'REFUTED')
        self.assertEqual(out['outcome'], 'REFUTED')

    def test_order_not_histogram(self):
        out = self.result(negative(self.payloads, 'ordered-raw'))
        self.assertEqual(out['axes']['orderedRecordAgreement'], 'REFUTED')
        self.assertEqual(out['axes']['histogramRecomputation'], 'SATISFIED')

    def test_histogram(self):
        self.assertEqual(self.result(negative(self.payloads, 'histogram'))['axes']['histogramRecomputation'], 'REFUTED')

    def test_boolean_shots(self):
        p = dict(self.payloads)
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['result'].update(shots=True))
        with self.assertRaises(Rejected): self.result(p)

    def test_false_bool_metadata(self):
        p = dict(self.payloads)
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['result']['metadata'].update(pub_index=False))
        with self.assertRaises(Rejected): self.result(p)

    def test_schema_and_unknown_fields(self):
        p = dict(self.payloads)
        edit(p, 'measurement-metadata.json', lambda v: v.update(verified=True))
        with self.assertRaises(Rejected): self.result(p)
        p = dict(self.payloads)
        edit(p, 'ibm-live-record.normalized.json', lambda v: v.update(schema='other'))
        self.assertEqual(self.result(p)['axes']['declaredCaptureOrigin'], 'REFUTED')

    def test_raw_format(self):
        for raw in (b'00\r\n', b'0\n', b'02\n', b'00'):
            p = dict(self.payloads)
            p['measurements-ordered.c1c0.txt'] = raw
            with self.subTest(raw=raw), self.assertRaises(Rejected): self.result(p)

    def test_origin_and_fabricated_authentication(self):
        self.assertEqual(self.result(negative(self.payloads, 'live-origin'))['axes']['declaredCaptureOrigin'], 'REFUTED')
        self.assertEqual(self.result(negative(self.payloads, 'auth-label'))['axes']['authenticationLabelConsistency'], 'REFUTED')
        claim = copy.deepcopy(self.claim)
        claim['providerAuthentication'] = 'ESTABLISHED'
        with self.assertRaises(Rejected): case_from_payloads(claim, self.payloads)
        p = dict(self.payloads)
        edit(p, 'normalization-provenance.json', lambda v: v.update(scope='Signed hardware authenticity established'))
        self.assertEqual(self.result(p)['axes']['declaredCaptureOrigin'], 'REFUTED')

    def test_circuits_and_mapping(self):
        self.assertEqual(self.result(negative(self.payloads, 'submitted-returned'))['axes']['providerArtifactConsistency'], 'REFUTED')
        p = dict(self.payloads)
        edit(p, 'isa-submitted.json', lambda v: v.update(name='changed-submitted'))
        self.assertEqual(self.result(p)['axes']['providerArtifactConsistency'], 'REFUTED')
        p = dict(self.payloads)
        def swap(v):
            for op in v['operations']:
                if op['name'] == 'measure': op['clbits'][0] = 1-op['clbits'][0]
        edit(p, 'isa-returned.json', swap)
        self.assertEqual(self.result(p)['axes']['isaRelation'], 'REFUTED')

    def test_noncompleted_is_not_isa_refutation(self):
        p = dict(self.payloads)
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['job'].update(status='RUNNING'))
        edit(p, 'measurement-metadata.json', lambda v: v.update(job_status='RUNNING'))
        refresh_record(p)
        out = self.result(p)
        self.assertEqual(out['outcome'], 'UNVERIFIABLE')
        self.assertEqual(out['axes']['isaRelation'], 'SATISFIED')

    def test_unavailable_and_unresolved(self):
        p = dict(self.payloads)
        p.pop('measurements-ordered.c1c0.txt')
        self.assertEqual(self.result(p)['outcome'], 'UNVERIFIABLE')
        case = copy.deepcopy(self.case)
        case['payloadsBase64'].pop('logical.json')
        with self.assertRaises(CannotRecompute): make_bundle(case)

    def test_partial_evidence_cannot_hide_anchor_contradiction(self):
        from qev.live_relation import evaluate
        p = dict(self.payloads)
        p.pop('measurements-ordered.c1c0.txt')
        edit(p, 'job-receipt.json', lambda v: v.update(submitted_at_observed='2026-09-22T00:00:00Z'))
        direct = evaluate(self.claim, p, ROOT, lambda s, t: tsei(s, t))
        bundle = make_bundle(case_from_payloads(self.claim, p))
        self.assertEqual(bundle['canonicalResult'], direct)
        self.assertEqual(bundle['receipt']['outcome'], 'REFUTED')
        self.assertEqual(direct['axes']['byteIdentity'], 'REFUTED')
        self.assertEqual(direct['axes']['rawCommitment'], 'CANNOT_ESTABLISH')
        self.assertEqual(recompute(bundle, self.claim)['verificationOutcome'], 'REFUTED')

    def test_partial_roles_preserve_available_contradictions(self):
        cases = (('assigned-job', 'measurement-metadata.json', 'jobRequestBinding'),
                 ('live-origin', 'measurement-metadata.json', 'declaredCaptureOrigin'),
                 ('auth-label', 'provider-input-comparison.json', 'authenticationLabelConsistency'),
                 ('submitted-returned', 'provider-submission.normalized.json', 'providerArtifactConsistency'))
        for mutation, missing, axis in cases:
            p = negative(self.payloads, mutation)
            p.pop(missing)
            bundle = make_bundle(case_from_payloads(self.claim, p))
            with self.subTest(mutation=mutation):
                self.assertEqual(bundle['receipt']['outcome'], 'REFUTED')
                self.assertEqual(bundle['canonicalResult']['axes'][axis], 'REFUTED')
                self.assertEqual(recompute(bundle, self.claim)['verificationOutcome'], 'REFUTED')
        p = dict(self.payloads)
        p.pop('measurement-metadata.json')
        self.assertEqual(self.result(p)['outcome'], 'UNVERIFIABLE')

    def test_measurement_maps_must_match_independent_intent(self):
        from qev.live_common import ANCHORS
        from qev.live_relation import evaluate
        p = dict(self.payloads)
        def swap(v):
            for op in v['operations']:
                if op['name'] == 'measure': op['clbits'][0] = 1-op['clbits'][0]
        for role in ('logical.json', 'isa-submitted.json', 'isa-returned.json'):
            edit(p, role, swap)
        edit(p, 'submission-intent.json', lambda v: v['artifacts'].update({
            'logical.json': sha(p['logical.json']), 'isa-submitted.json': sha(p['isa-submitted.json'])}))
        def commit_intent():
            edit(p, 'job-receipt.json', lambda v: v.update(intent_sha256=sha(p['submission-intent.json'])))
            edit(p, 'normalization-provenance.json', lambda v: v.update(precommit_intent_sha256=sha(p['submission-intent.json'])))
            claim = copy.deepcopy(self.claim)
            claim['anchors'] = {role: sha(p[role]) for role in ANCHORS}
            return claim
        physical = sha(physical_bytes(parse(p['isa-submitted.json'])))
        edit(p, 'provider-submission.normalized.json', lambda v: v.update(physicalCircuitDigest=physical))
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['isa_circuit'].update(physicalCircuitDigest=physical))
        refresh_record(p)
        claim = commit_intent()  # A new explicit test claim, never the original trusted claim.
        direct = evaluate(claim, p, ROOT, lambda s, t: tsei(s, t))
        bundle = make_bundle(case_from_payloads(claim, p))
        self.assertEqual(bundle['canonicalResult'], direct)
        self.assertEqual(direct['nativeTsei']['classification'], 'stable')
        self.assertEqual(direct['axes']['byteIdentity'], 'SATISFIED')
        self.assertEqual(direct['axes']['measurementIntent'], 'REFUTED')
        self.assertEqual(bundle['receipt']['outcome'], 'REFUTED')
        self.assertEqual(recompute(bundle, claim)['verificationOutcome'], 'REFUTED')
        # A consistently declared swap is in-domain under its own new claim.
        edit(p, 'submission-intent.json', lambda v: v.update(measurement_mapping=[
            {'physical_qubit': 0, 'classical_bit': 1}, {'physical_qubit': 1, 'classical_bit': 0}]))
        claim = commit_intent()
        self.assertEqual(make_bundle(case_from_payloads(claim, p))['receipt']['outcome'], 'VERIFIED')

    def test_role_inventory(self):
        for transform in (lambda m: m.clear(), lambda m: m.pop(), lambda m: m.append(m[0])):
            case = copy.deepcopy(self.case)
            transform(case['evidenceSet']['members'])
            with self.subTest(case=len(case['evidenceSet']['members'])):
                try:
                    make_bundle(case)
                except Rejected as exc:
                    self.assertEqual(str(exc), 'ROLE_INVENTORY')
                except Exception as exc:
                    self.assertEqual(getattr(exc, 'reason_code', None), 'rvr.gate.schema_invalid')
                else:
                    self.fail('bad role inventory accepted')
        with self.assertRaises(Rejected): case_from_payloads(self.claim, {**self.payloads, '../bad': b'x'})

    def test_different_identity_same_outcome(self):
        p = controls(self.payloads)['historical-booleans']
        out = recompute(self.bundle, self.claim, case_from_payloads(self.claim, p))
        self.assertEqual(out['verificationOutcome'], 'VERIFIED')
        self.assertEqual(out['recomputationStatus'], 'DIVERGED')
        self.assertEqual(out['identities']['resultDigest'], self.bundle['receipt']['resultDigest'])
        self.assertNotEqual(out['identities']['evidenceSetDigest'], self.bundle['receipt']['evidenceSetDigest'])

    def test_stored_result_even_refreshed_receipt(self):
        bundle = copy.deepcopy(self.bundle)
        rvr, _, _, _ = context()
        bundle['canonicalResult']['axes']['isaRelation'] = 'REFUTED'
        bundle['receipt']['resultDigest'] = rvr.canonical_digest(bundle['canonicalResult'])
        with self.assertRaisesRegex(Rejected, 'STORED_RESULT'): recompute(bundle, self.claim)

    def test_independent_claim(self):
        bundle = copy.deepcopy(self.bundle)
        rvr, _, _, _ = context()
        bundle['claim']['jobId'] = 'new-job'
        bundle['receipt']['claimDigest'] = rvr.canonical_digest(bundle['claim'])
        with self.assertRaisesRegex(Rejected, 'INDEPENDENT_CLAIM'): recompute(bundle, self.claim)

    def test_receipt_projection(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['receipt']['outcome'] = 'REFUTED'
        # context loads the pinned class afresh, so inspect its stable reason code.
        try:
            recompute(bundle, self.claim)
        except Exception as exc:
            self.assertEqual(getattr(exc, 'reason_code', None), 'rvr.gate.result_projection_mismatch')
        else:
            self.fail('receipt projection accepted')

    def test_profile_identity(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['verificationProfile']['profileId'] = 'fake'
        with self.assertRaisesRegex(Rejected, 'PROFILE_IDENTITY'): recompute(bundle, self.claim)

    def test_saved_root(self):
        saved = copy.deepcopy(self.saved)
        saved['nativeReceiptOs']['evidence']['anchor']['receipt_root'] = '0x' + '0'*64
        with self.assertRaisesRegex(Rejected, 'ROOT'): replay(saved, self.claim)

    def test_saved_summary_proof_and_provenance(self):
        for field in ('summary', 'proof'):
            saved = copy.deepcopy(self.saved)
            saved['nativeReceiptOs'][field]['schema'] = 'fabricated'
            with self.subTest(field=field), self.assertRaises(Rejected): replay(saved, self.claim)
        saved = copy.deepcopy(self.saved)
        saved['nativeReceiptOs']['proof']['provenance_summary']['what_happened'] = 'authenticated hardware'
        with self.assertRaises(Rejected): replay(saved, self.claim)

    def test_saved_attachment(self):
        saved = copy.deepcopy(self.saved)
        raw = unbase64(saved['attachment']['base64']) + b' '
        saved['attachment']['base64'] = base64.b64encode(raw).decode()
        with self.assertRaisesRegex(Rejected, 'ATTACHMENT_DIGEST'): replay(saved, self.claim)
        saved['attachment']['sha256'] = sha(raw)
        with self.assertRaisesRegex(Rejected, 'ENVELOPE'): replay(saved, self.claim)

    def test_saved_replay_verdict(self):
        saved = copy.deepcopy(self.saved)
        saved['rvrReplay']['verificationOutcome'] = 'REFUTED'
        with self.assertRaisesRegex(Rejected, 'STORED_REPLAY'): replay(saved, self.claim)

    def test_stored_replay_boolean_is_not_integer(self):
        saved = copy.deepcopy(self.saved)
        saved['rvrReplay']['canonicalResult']['nativeTsei']['normative_match'] = 1
        with self.assertRaisesRegex(Rejected, 'STORED_REPLAY'): replay(saved, self.claim)

    def test_stored_native_boolean_is_not_integer(self):
        paths = (('verification', 'ok'), ('summary', 'receipt_verification', 'ok'),
                 ('proof', 'evidence_capsule', 'receipt_root', 'match'))
        for path in paths:
            saved = copy.deepcopy(self.saved)
            obj = saved['nativeReceiptOs']
            for key in path[:-1]: obj = obj[key]
            self.assertIs(obj[path[-1]], True)
            obj[path[-1]] = 1
            with self.subTest(path=path), self.assertRaisesRegex(Rejected, 'NATIVE_SUMMARY_OR_PROOF'):
                replay(saved, self.claim)

    def test_stored_envelope_numeric_is_not_boolean(self):
        saved = copy.deepcopy(self.saved)
        saved['nativeReceiptOs']['evidence']['metadata']['message_count'] = False
        with self.assertRaisesRegex(Rejected, 'ENVELOPE'): replay(saved, self.claim)

    def test_demo_exit_tracks_semantics_not_root(self):
        from types import SimpleNamespace
        from qev.live_cli import dispatch
        negatives = ((negative(self.payloads, 'histogram'), 'REFUTED', 1),
                     ({k: v for k, v in self.payloads.items() if k != 'measurements-ordered.c1c0.txt'}, 'UNVERIFIABLE', 3))
        for payloads, outcome, code in negatives:
            with patch('qev.live_cli.fixture', return_value=(self.claim, payloads)):
                out, actual = dispatch(SimpleNamespace(command='live-demo'))
            self.assertEqual(actual, code)
            self.assertEqual(out['rvrReplay']['verificationOutcome'], outcome)
            self.assertIs(out['nativeReceiptOs']['verification']['ok'], True)
        p = dict(self.payloads)
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['result'].update(shots=True))
        with patch('qev.live_cli.fixture', return_value=(self.claim, p)):
            out, code = dispatch(SimpleNamespace(command='live-demo'))
        self.assertEqual(code, 2)
        self.assertEqual(out['status'], 'REJECTED')

    def test_native_anchor_independence(self):
        evidence = copy.deepcopy(self.saved['nativeReceiptOs']['evidence'])
        root1 = bridge('live_receiptos_bridge.ts', {'mode': 'root-probe', 'evidence': evidence})
        evidence['anchor']['tx_hash'] = 'fabricated-anchor'
        evidence['anchor']['receipt_root'] = 'altered'
        root2 = bridge('live_receiptos_bridge.ts', {'mode': 'root-probe', 'evidence': evidence})
        self.assertEqual(root1, root2)
        saved = copy.deepcopy(self.saved)
        saved['nativeReceiptOs']['evidence']['anchor']['tx_hash'] = 'fabricated-anchor'
        with self.assertRaises(Rejected): replay(saved, self.claim)

    def test_root_is_not_rvr_verified(self):
        for p in (negative(self.payloads, 'histogram'), {k:v for k,v in self.payloads.items() if k != 'measurements-ordered.c1c0.txt'}):
            bundle = make_bundle(case_from_payloads(self.claim, p))
            saved = create(bundle, self.claim)
            out = replay(saved, self.claim)
            self.assertIn(out['rvr']['verificationOutcome'], ('REFUTED', 'UNVERIFIABLE'))
            self.assertEqual(out['receiptOs']['rootStatus'], 'VERIFIED')

    def test_native_source_mismatch_before_execution(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            copied = Path(tmp)/'repo'
            shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            path = copied/'vendor/rvr-v0/adapter.py'
            path.write_bytes(b'raise RuntimeError("MUST_NOT_EXECUTE")\n')
            with self.assertRaisesRegex(CannotRecompute, 'SOURCE_IDENTITY_MISMATCH'): context(copied)
            path.unlink()
            with self.assertRaisesRegex(CannotRecompute, 'SOURCE_UNAVAILABLE'): context(copied)

    def test_native_non_rvr_dependency_mismatch(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            copied = Path(tmp)/'repo'
            shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            path = copied/'vendor/receiptos-v0/src/receiptos/canon/receipt-root.ts'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(CannotRecompute, 'SOURCE_IDENTITY_MISMATCH'): context(copied)

    def test_copied_location_replay(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as tmp:
            copied = Path(tmp)/'independent'
            shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns('.git', '__pycache__'))
            artifact = Path(tmp)/'saved.json'
            artifact.write_bytes(encode(self.saved))
            command = [sys.executable, '-B', *(['-O'] if sys.flags.optimize else []), '-m', 'qev', 'live-replay', str(artifact)]
            process = subprocess.run(command, cwd=copied, capture_output=True, timeout=60)
            self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
            self.assertEqual(parse(process.stdout), replay(self.saved, self.claim))


class MutationAdmissionTests(unittest.TestCase):
    def test_empty_subset_duplicate_inventory(self):
        for change in (lambda v: v['mutants'].clear(), lambda v: v['mutants'].pop(),
                       lambda v: v['mutants'].append(v['mutants'][0]),
                       lambda v: v['controls'].clear(), lambda v: v['controls'].pop(),
                       lambda v: v['controls'].append(v['controls'][0])):
            value = inventory()
            change(value)
            with self.assertRaises(Rejected): admit(value)

    def test_broken_baseline(self):
        def broken(*args): return {'outcome': 'REFUTED'}
        with self.assertRaisesRegex(Rejected, 'BROKEN_BASELINE'): run(baseline=broken)

    def test_broken_controls(self):
        claim, payloads = fixture()
        positive = controls(payloads)
        positive['historical-booleans'] = negative(payloads, 'histogram')
        with self.assertRaisesRegex(Rejected, 'BROKEN_BASELINE'): run(positive=positive)

    def test_broken_negative_baseline(self):
        from qev.live_relation import evaluate
        claim, payloads = fixture()
        constant = evaluate(claim, payloads, ROOT, lambda s,t: tsei(s,t))
        with self.assertRaisesRegex(Rejected, 'BROKEN_NEGATIVE'): run(baseline=lambda *args: constant)


if __name__ == '__main__': unittest.main()
