"""Evidence boundaries over real saved captures; no provider SDK or network."""
import copy
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

from qev import cross_provider as model, cross_adapters as adapters, cross_mutations as mutations
from qev.live_common import ROOT, Rejected, CannotRecompute, sha
from qev.moth_comet import encode, parse


def reanchor_moth(claim, payloads):
    """New explicit local test claim, never modify the frozen capture on disk."""
    manifest = parse(payloads['manifest.json'])
    for name in list(payloads):
        if name.endswith('.http.json'):
            meta = parse(payloads[name])
            raw = payloads[meta['body_file']]
            meta.update(sha256=sha(raw), byte_length=len(raw))
            payloads[name] = encode(meta)
    for name in manifest['files']:
        manifest['files'][name] = {'sha256': sha(payloads[name]), 'bytes': len(payloads[name])}
    payloads['manifest.json'] = encode(manifest)
    claim['manifestSha256'] = sha(payloads['manifest.json'])
    claim['requestSha256'] = sha(payloads[manifest['roles']['request']])


class CrossProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = {provider: adapters.fixture(provider) for provider in model.PROVIDERS}
        cls.reports = {provider: model.evaluate(provider, *args) for provider, args in cls.inputs.items()}

    def seed(self, provider='moth-comet'):
        return copy.deepcopy(self.inputs[provider])

    def output_change(self, edit):
        claim, payloads = self.seed()
        roles = parse(payloads['manifest.json'])['roles']
        result = parse(payloads[roles['result']])
        edit(result['result']['output'])
        payloads[roles['result']] = encode(result)
        terminal = parse(payloads[roles['statuses'][-1]])
        terminal['result'] = copy.deepcopy(result['result'])
        payloads[roles['statuses'][-1]] = encode(terminal)
        reanchor_moth(claim, payloads)
        return model.evaluate('moth-comet', claim, payloads)

    def test_both_actual_captures_consistent(self):
        for provider, report in self.reports.items():
            self.assertEqual(report['common']['consistency'], 'CONSISTENT', (provider, report))
            self.assertEqual(model.exit_code(report), 0)
            self.assertTrue(all(not v for v in report['common']['issues'].values()))

    def test_common_shape_shared_but_provider_details_distinct(self):
        a, b = (self.reports[p] for p in model.PROVIDERS)
        self.assertEqual(set(a), set(b))
        self.assertEqual(set(a['common']), set(b['common']))
        self.assertNotEqual(a['providerSpecific']['profile'], b['providerSpecific']['profile'])
        self.assertNotEqual(a['identity']['evidenceSetSha256'], b['identity']['evidenceSetSha256'])

    def test_ibm_actual_sample(self):
        sample = self.reports['ibm-direct']['common']['observation']['sample']
        self.assertEqual((sample['requestedShots'], sample['observedShots'], sample['width']), (256, 256, 2))
        self.assertEqual(sample['representation'], 'ORDERED_SHOTS')

    def test_moth_actual_sample_and_zero_delivery(self):
        report = self.reports['moth-comet']
        sample = report['common']['observation']['sample']
        self.assertEqual((sample['observedShots'], sample['uniqueBitstrings'], sample['width']), (2048, 2040, 20))
        self.assertEqual(sample['representation'], 'COUNTS_ONLY')
        self.assertEqual(report['capabilities']['outputDelivery']['detail']['deliveredBytes'], 0)
        self.assertEqual(report['capabilities']['outputDelivery']['detail']['requestedBytes'], 32)

    def test_ibm_native_layers_really_execute(self):
        layers = self.reports['ibm-direct']['nativeLayers']
        self.assertTrue(all(row['status'] == 'EXECUTED' for row in layers.values()))
        self.assertEqual(layers['RVR']['result']['verificationOutcome'], 'VERIFIED')
        self.assertEqual(layers['RVR']['result']['recomputationStatus'], 'REPRODUCED')
        self.assertEqual(layers['TSEI']['result']['classification'], 'stable')
        self.assertEqual(layers['ReceiptOS']['result']['rootStatus'], 'VERIFIED')

    def test_moth_does_not_call_native_layers(self):
        with patch('qev.live_native.make_bundle', side_effect=AssertionError('native called')):
            report = model.evaluate('moth-comet', *self.seed())
        self.assertTrue(all(row['status'] == 'NOT_INTEGRATED' and row['result'] is None
                            for row in report['nativeLayers'].values()))

    def test_moth_unavailable_provenance_is_not_synthesized(self):
        caps = self.reports['moth-comet']['capabilities']
        for key in ('circuitBytes', 'orderedShots', 'measurementMapping', 'idealCircuitRelation'):
            self.assertEqual(caps[key]['status'], 'UNAVAILABLE')
        self.assertEqual(caps['commitmentEncoding']['status'], 'UNRESOLVED')
        for key in ('commitmentTiming', 'seedProvenance', 'nonemptyExtraction', 'entropyQualification'):
            self.assertEqual(caps[key]['status'], 'NOT_ESTABLISHED')

    def test_claims_do_not_authenticate_either_provider(self):
        for report in self.reports.values():
            self.assertEqual(report['common']['providerAuthentication'], 'NOT_ESTABLISHED')
            self.assertEqual(report['identity']['authority'], 'LOCAL_UNSIGNED_CLAIM')
            for key in ('jobId', 'backend', 'completion'):
                self.assertEqual(report['common']['observation'][key]['basis'], 'UPSTREAM_REPORTED')

    def test_input_mapping_order_does_not_change_report(self):
        claim, payloads = self.seed()
        report = model.evaluate('moth-comet', dict(reversed(list(claim.items()))), dict(reversed(list(payloads.items()))))
        self.assertEqual(encode(report), encode(self.reports['moth-comet']))

    def test_no_python_network_calls(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network forbidden')):
            for provider in model.PROVIDERS:
                self.assertEqual(model.evaluate(provider, *self.seed(provider)), self.reports[provider])

    def test_missing_capture_member_is_incomplete(self):
        claim, payloads = self.seed()
        payloads.pop('submit.body.json')
        report = model.evaluate('moth-comet', claim, payloads)
        self.assertEqual(report['common']['consistency'], 'INCOMPLETE')
        self.assertIn('EVIDENCE:submit.body.json', report['common']['issues']['missing'])

    def test_missing_does_not_erase_another_byte_contradiction(self):
        claim, payloads = self.seed()
        payloads.pop('submit.body.json')
        payloads['request.body.json'] += b' '
        report = model.evaluate('moth-comet', claim, payloads)
        self.assertEqual(report['common']['consistency'], 'CONTRADICTED')
        self.assertTrue(report['common']['issues']['missing'])
        self.assertTrue(report['common']['issues']['contradiction'])

    def test_malformed_missing_and_contradiction_retained_together(self):
        claim, payloads = self.seed()
        payloads.pop('submit.body.json')
        payloads['request.body.json'] = b'{'
        report = model.evaluate('moth-comet', claim, payloads)
        self.assertEqual(report['common']['consistency'], 'MALFORMED')
        for key in ('missing', 'contradiction', 'malformed'):
            self.assertTrue(report['common']['issues'][key])

    def test_missing_counts_with_new_local_claim_is_incomplete(self):
        report = self.output_change(lambda out: out['raw'].pop('counts'))
        self.assertEqual(report['common']['consistency'], 'INCOMPLETE')
        self.assertIn('MOTH:COUNTS_MISSING', report['common']['issues']['missing'])

    def test_boolean_count_is_malformed(self):
        def edit(out):
            counts = out['raw']['counts']
            counts[next(iter(counts))] = True
        report = self.output_change(edit)
        self.assertEqual(report['common']['consistency'], 'MALFORMED')

    def test_count_total_contradiction(self):
        def edit(out):
            counts = out['raw']['counts']
            counts[next(iter(counts))] += 1
        report = self.output_change(edit)
        self.assertEqual(report['common']['consistency'], 'CONTRADICTED')
        self.assertIn('MOTH:COUNT_TOTAL', report['common']['issues']['contradiction'])

    def test_unverified_certificate_does_not_promote_authentication(self):
        report = self.output_change(lambda out: out.update(certificate={'certified': True}))
        self.assertEqual(report['common']['consistency'], 'CONSISTENT')
        self.assertEqual(report['common']['providerAuthentication'], 'NOT_ESTABLISHED')
        self.assertEqual(report['capabilities']['entropyQualification']['status'], 'NOT_ESTABLISHED')

    def test_ibm_missing_raw_still_executes_rvr_without_success(self):
        claim, payloads = self.seed('ibm-direct')
        payloads.pop('measurements-ordered.c1c0.txt')
        report = model.evaluate('ibm-direct', claim, payloads)
        self.assertEqual(report['common']['consistency'], 'INCOMPLETE')
        self.assertEqual(report['nativeLayers']['RVR']['result']['verificationOutcome'], 'UNVERIFIABLE')
        self.assertEqual(report['nativeLayers']['ReceiptOS']['status'], 'NOT_EXECUTED')

    def test_ibm_missing_plus_contradiction(self):
        claim, payloads = self.seed('ibm-direct')
        payloads.pop('job-metrics.json')
        claim['jobId'] = 'different-job'
        report = model.evaluate('ibm-direct', claim, payloads)
        self.assertEqual(report['common']['consistency'], 'CONTRADICTED')
        self.assertTrue(report['common']['issues']['missing'])

    def test_ibm_malformed_shape_not_missing(self):
        claim, payloads = self.seed('ibm-direct')
        payloads['measurement-counts.json'] = b'{"00":true}'
        report = model.evaluate('ibm-direct', claim, payloads)
        self.assertEqual(report['common']['consistency'], 'MALFORMED')

    def test_native_unavailable_is_not_executed(self):
        with patch('qev.live_native.context', side_effect=CannotRecompute('RUNTIME_UNAVAILABLE')):
            report = model.evaluate('ibm-direct', *self.seed('ibm-direct'))
        self.assertEqual(report['common']['consistency'], 'CANNOT_RECOMPUTE')
        self.assertTrue(all(row['status'] == 'NOT_EXECUTED' for row in report['nativeLayers'].values()))

    def test_bad_and_unknown_provider_fail_closed(self):
        for value in ('ibm', '', None, [], True):
            with self.subTest(value=value), self.assertRaises(Rejected):
                model.evaluate(value, *self.seed())

    def test_role_injection_and_traversal_rejected(self):
        for name in ('../escape', 'https://provider/result', 'extra.json'):
            claim, payloads = self.seed()
            payloads[name] = b'{}'
            with self.subTest(name=name), self.assertRaises(Rejected):
                model.evaluate('moth-comet', claim, payloads)

    def test_nonbyte_and_oversize_payload_rejected(self):
        for raw in (None, '{}', {}, b'a' * 4_194_305):
            claim, payloads = self.seed()
            payloads['submit.body.json'] = raw
            with self.subTest(kind=type(raw)), self.assertRaises(Rejected):
                model.evaluate('moth-comet', claim, payloads)

    def test_saved_report_tampering_rejected(self):
        fresh = self.reports['moth-comet']
        for name, _, expected in mutations.MUTANTS:
            if name in model.KINDS:
                continue
            with self.subTest(name=name), self.assertRaisesRegex(Rejected, expected):
                model.compare_report(mutations.attack(name, fresh), fresh)

    def test_report_extra_fields_rejected(self):
        saved = copy.deepcopy(self.reports['moth-comet'])
        saved['common']['trusted'] = True
        with self.assertRaises(Rejected):
            model.compare_report(saved, self.reports['moth-comet'])

    def test_report_boolean_not_numeric(self):
        saved = copy.deepcopy(self.reports['moth-comet'])
        saved['providerSpecific']['result']['deliveredBytes'] = False
        with self.assertRaises(Rejected):
            model.compare_report(saved, self.reports['moth-comet'])

    def test_replay_reexecutes_and_reproduces(self):
        for provider in model.PROVIDERS:
            report = self.reports[provider]
            out = model.replay(report, provider, *self.seed(provider))
            self.assertEqual(out['projection'], 'REPRODUCED')
            self.assertEqual(out['reportSha256'], sha(encode(report)))

    def test_replay_rejects_wrong_external_claim(self):
        claim, payloads = self.seed()
        claim['jobId'] = 'different-job'
        with self.assertRaises(Rejected):
            model.replay(self.reports['moth-comet'], 'moth-comet', claim, payloads)

    def test_empty_evidence_is_incomplete_not_success(self):
        for provider in model.PROVIDERS:
            report = model.evaluate(provider, self.seed(provider)[0], {})
            self.assertEqual(report['common']['consistency'], 'INCOMPLETE')

    def test_all_issue_precedence_and_no_loss(self):
        cases = [(['missing'], 'INCOMPLETE'), (['missing', 'unavailable'], 'CANNOT_RECOMPUTE'),
                 (['missing', 'unavailable', 'contradiction'], 'CONTRADICTED'),
                 (list(model.KINDS), 'MALFORMED')]
        for present, expected in cases:
            issues = {key: ['found'] if key in present else [] for key in model.KINDS}
            before = copy.deepcopy(issues)
            self.assertEqual(model.consistency(issues), expected)
            self.assertEqual(issues, before)

    def test_duplicate_json_keys_rejected(self):
        from qev.moth_comet import MothError
        with self.assertRaises(MothError):
            parse(b'{"status":0,"status":1}')

    def test_sources_valid(self):
        model.check_sources()

    def test_source_unavailable_fails_closed(self):
        with patch('qev.cross_provider.read', side_effect=OSError('missing')):
            with self.assertRaises(CannotRecompute):
                model.check_sources()

    def test_source_inventory_cannot_be_empty_or_partial(self):
        original = parse((ROOT / model.PROFILE / 'sources.json').read_bytes())
        for files in ({}, {next(iter(original['files'])): '0' * 64}):
            with patch('qev.cross_provider.read', return_value=encode({**original, 'files': files})):
                with self.assertRaises(CannotRecompute):
                    model.check_sources()

    def test_source_hash_mismatch_fails_closed(self):
        original = parse((ROOT / model.PROFILE / 'sources.json').read_bytes())
        original['files'][model.FILES[0]] = '0' * 64
        from qev.live_common import read
        def tampered(root, name):
            return encode(original) if name.endswith('/sources.json') else read(root, name)
        with patch('qev.cross_provider.read', side_effect=tampered), self.assertRaises(CannotRecompute):
            model.check_sources()

    def test_mutation_gate(self):
        report = mutations.run()
        self.assertTrue(mutations.successful(report), report)
        self.assertEqual(len(report['mutations']), 12)

    def test_vacuous_mutation_gate_rejected(self):
        for report in ({}, {'mutations': []}, {'mutations': [{'id': 'identity', 'status': 'KILLED', 'controls': []}]}):
            self.assertFalse(mutations.successful(report))

    def test_empty_mutant_or_control_inventory_cannot_pass(self):
        with patch.object(mutations, 'MUTANTS', ()):
            self.assertFalse(mutations.successful({'mutations': []}))
        with patch.object(mutations, 'CONTROLS', ()):
            self.assertFalse(mutations.successful({'mutations': []}))

    def test_duplicate_mutant_or_control_reports_cannot_pass(self):
        rows = [{'id': row[0], 'status': 'KILLED',
                 'controls': [{'id': key, 'preserved': True} for key in mutations.CONTROLS]}
                for row in mutations.MUTANTS]
        rows[-1] = copy.deepcopy(rows[0])
        self.assertFalse(mutations.successful({'mutations': rows}))
        rows[-1]['id'] = mutations.MUTANTS[-1][0]
        rows[0]['controls'][-1] = copy.deepcopy(rows[0]['controls'][0])
        self.assertFalse(mutations.successful({'mutations': rows}))

    def test_cli_custom_capture_requires_external_claim(self):
        result = subprocess.run([sys.executable, '-B', '-m', 'qev.cross_cli', 'demo',
                                 '--provider', 'moth-comet', '--capture', '.'],
                                cwd=ROOT, capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
