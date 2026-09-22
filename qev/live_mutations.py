"""Finite source-mutation falsification harness; never used by live verification."""
import copy
import types
from .live_common import ROOT, PROFILE, encode, parse, read, need, sha, physical_bytes
from .live_cli import fixture
from .live_native import tsei
from .live_relation import evaluate

MUTANTS = (
    ('assigned-job', "record['job']['job_id'] == claim['jobId']", 'True', 'jobRequestBinding'),
    ('ordered-raw', "lines == record['result']['bitstrings']", 'True', 'orderedRecordAgreement'),
    ('histogram', 'dict(Counter(lines)) == counts', 'True', 'histogramRecomputation'),
    ('raw-anchor', "sha(raw) == claim['anchors'][raw_name]", 'True', 'rawCommitment'),
    ('live-origin', "record['sdk']['source'] == 'LIVE_IBM_RUNTIME_API'", 'True', 'declaredCaptureOrigin'),
    ('auth-label', "provenance['provider_signature'] == 'NOT_ESTABLISHED'", 'True', 'authenticationLabelConsistency'),
    ('submitted-returned', 'submitted == returned', 'True', 'providerArtifactConsistency'),
)
CONTROLS = ('original', 'payload-order', 'historical-booleans')


def inventory():
    return {'schema': 'qev.live-falsification.v1',
            'mutants': [{'id': m[0], 'source': 'qev/live_relation.py', 'before': m[1], 'after': m[2], 'axis': m[3]} for m in MUTANTS],
            'controls': list(CONTROLS)}


def admit(value):
    need(value == inventory(), 'MUTATION_COMPLETE_UNIQUE_INVENTORY')


def edit(payloads, name, change):
    value = parse(payloads[name])
    change(value)
    payloads[name] = encode(value)


def refresh_record(payloads):
    edit(payloads, 'normalization-provenance.json', lambda v: v.update(live_record_sha256=sha(payloads['ibm-live-record.normalized.json'])))


def negative(payloads, mutant):
    p = dict(payloads)
    if mutant == 'assigned-job':
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['job'].update(job_id='different-assigned-job'))
        refresh_record(p)
    elif mutant == 'ordered-raw':
        def swap(v):
            bits = v['result']['bitstrings']
            i = next(i for i, b in enumerate(bits) if b != bits[0])
            bits[0], bits[i] = bits[i], bits[0]
        edit(p, 'ibm-live-record.normalized.json', swap)
        refresh_record(p)
    elif mutant == 'histogram':
        edit(p, 'measurement-counts.json', lambda v: v.update({'00': v['00'] + 1, '11': v['11'] - 1}))
    elif mutant == 'raw-anchor':
        name = 'measurements-ordered.c1c0.txt'
        p[name] = (b'0' if p[name][:1] == b'1' else b'1') + p[name][1:]
        edit(p, 'measurement-metadata.json', lambda v: v.update(canonical_raw_sha256=sha(p[name])))
    elif mutant == 'live-origin':
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['sdk'].update(source='FABRICATED_ORIGIN'))
        refresh_record(p)
    elif mutant == 'auth-label':
        edit(p, 'normalization-provenance.json', lambda v: v.update(provider_signature='AUTHENTICATED_HARDWARE'))
    elif mutant == 'submitted-returned':
        edit(p, 'isa-returned.json', lambda v: v['operations'].insert(0, {'name': 'x', 'qubits': [0], 'clbits': [], 'params': []}))
        digest = sha(physical_bytes(parse(p['isa-returned.json'])))
        edit(p, 'ibm-live-record.normalized.json', lambda v: v['isa_circuit'].update(physicalCircuitDigest=digest))
        refresh_record(p)
    else:
        raise ValueError(mutant)
    return p


def controls(payloads):
    historical = dict(payloads)
    # The intent's exact committed bytes stay fixed; change only the supplemental
    # comparison booleans, which are never an oracle.
    edit(historical, 'provider-input-comparison.json', lambda v: v.update(input_circuit_snapshot_equal=False, job_id_matches=False))
    return {'original': payloads, 'payload-order': dict(reversed(list(payloads.items()))),
            'historical-booleans': historical}


def run(declared=None, baseline=evaluate, positive=None):
    declared = parse(read(ROOT, PROFILE + '/conformance.json')) if declared is None else declared
    admit(declared)
    claim, payloads = fixture()
    positive = controls(payloads) if positive is None else positive
    need(tuple(positive) == CONTROLS, 'CONTROL_COMPLETE_UNIQUE_INVENTORY')
    native = lambda s, t: tsei(s, t)
    baseline_controls = {key: baseline(claim, p, ROOT, native) for key, p in positive.items()}
    need(all(r['outcome'] == 'VERIFIED' and set(r['axes'].values()) == {'SATISFIED'}
             and r['nativeTsei']['classification'] == 'stable' for r in baseline_controls.values()), 'BROKEN_BASELINE_CONTROLS')
    source = read(ROOT, 'qev/live_relation.py').decode('utf-8')
    results = []
    for identifier, before, after, axis in MUTANTS:
        need(source.count(before) == 1, 'MUTATION_EXACT_ONE_SITE')
        candidate = negative(payloads, identifier)
        original = baseline(claim, candidate, ROOT, native)
        need(original['axes'][axis] == 'REFUTED', 'BROKEN_NEGATIVE_BASELINE')
        altered = source.replace(before, after)
        module = types.ModuleType('qev.live_source_mutant')
        module.__package__ = 'qev'
        exec(compile(altered, '<live-source-mutant>', 'exec'), module.__dict__)
        try:
            observed = module.evaluate(claim, candidate, ROOT, native)
            preserved = {key: module.evaluate(claim, p, ROOT, native) for key, p in positive.items()}
        except Exception as exc:
            results.append({'id': identifier, 'status': 'CRASHED', 'errorType': type(exc).__name__})
            continue
        status = ('CONTROL_BROKEN' if preserved != baseline_controls else
                  'KILLED' if observed['axes'][axis] == 'SATISFIED' else 'SURVIVED')
        results.append({'id': identifier, 'status': status, 'axis': axis,
                        'mutatedSourceSha256': sha(altered.encode()), 'baseline': original,
                        'observed': observed, 'controls': preserved})
    return {'schema': 'qev.live-source-mutation-report.v1',
            'status': 'PASS' if len(results) == len(MUTANTS) and all(r['status'] == 'KILLED' for r in results) else 'FAIL',
            'sourceSha256': sha(source.encode()), 'baselineControls': baseline_controls,
            'declaredInventory': declared, 'mutants': results,
            'killed': sum(r['status'] == 'KILLED' for r in results)}
