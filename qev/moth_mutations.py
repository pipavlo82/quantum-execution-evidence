"""Seven exact-site semantic mutations; errors are never counted as kills."""
import copy
import json
import types
from pathlib import Path

from . import moth_comet as adapter

ROOT = Path(__file__).resolve().parents[1]
MUTANTS = (
    ('request', "equal(request, REQUEST, 'REQUEST_PROFILE_MISMATCH')", 'REQUEST_PROFILE_MISMATCH'),
    ('submit_job', "equal(submit['job_id'], expected_job, 'SUBMIT_JOB_BINDING')", 'SUBMIT_JOB_BINDING'),
    ('counts_hash', "equal(raw['counts_sha256'], counts_hash, 'COUNTS_HASH')", 'COUNTS_HASH'),
    ('pulse_hash', "equal(pulse['pulse_hash'], pulse_hash, 'PULSE_HASH')", 'PULSE_HASH'),
    ('witness_s', "close(witness['S'], s, 'WITNESS_S')", 'WITNESS_S'),
    ('empty_grade', "equal(report['grade'], 'hardware-insufficient-entropy', 'EMPTY_OUTPUT_GRADE')", 'EMPTY_OUTPUT_GRADE'),
    ('output_hash', "equal(pulse['output_hash'], sha(bytes.fromhex(rnd['hex'])), 'OUTPUT_HASH')", 'OUTPUT_HASH'),
)
CONTROLS = ('captured', 'representation_reorder', 'upstream_certificate_is_not_proof')


def seed():
    root = ROOT / 'fixtures/moth-comet-v0/capture'
    manifest = json.loads((root / 'manifest.json').read_bytes())
    roles = manifest['roles']
    read = lambda n: adapter.parse((root / n).read_bytes())
    submit = read(roles['submit'])
    return [read(roles['request']), submit, [read(n) for n in roles['statuses']],
            read(roles['job']), read(roles['result']), submit['job_id']]


def sync(args, pulse=False):
    output = args[4]['result']['output']
    if pulse:
        value = output['pulse']
        value['pulse_hash'] = adapter.sha(adapter.compact({k: v for k, v in value.items() if k != 'pulse_hash'}))
    args[2][-1]['result'] = copy.deepcopy(args[4]['result'])
    return args


def negative(name):
    args = seed()
    out = args[4]['result']['output']
    if name == 'request':
        args[0]['params']['include_raw_counts'] = False
    elif name == 'submit_job':
        args[1]['job_id'] = 'substituted-job'
    elif name == 'counts_hash':
        out['raw']['counts_sha256'] = '0' * 64
    elif name == 'pulse_hash':
        out['pulse']['pulse_hash'] = '0' * 64
    elif name == 'witness_s':
        out['bell_witness']['S'] += 0.25
    elif name == 'empty_grade':
        out['entropy_report']['grade'] = 'hardware'
    elif name == 'output_hash':
        out['pulse']['output_hash'] = '0' * 64
        sync(args, pulse=True)
    else:
        raise ValueError('unknown mutant')
    return sync(args)


def controls():
    original = seed()
    reordered = copy.deepcopy(original)
    out = reordered[4]['result']['output']
    out['raw']['counts'] = dict(reversed(list(out['raw']['counts'].items())))
    sync(reordered)
    asserted = copy.deepcopy(original)
    asserted[4]['result']['output']['certificate'] = {'certified': True, 'grade': 'hardware'}
    sync(asserted)
    return dict(zip(CONTROLS, (original, reordered, asserted)))


def run():
    raw = (ROOT / 'qev/moth_comet.py').read_text(encoding='utf-8')
    cases = controls()
    expected = {name: adapter.evaluate(*args) for name, args in cases.items()}
    rows = []
    for name, target, reason in MUTANTS:
        row = {'id': name, 'status': 'UNAPPLIED', 'controls': []}
        if raw.count(target) != 1:
            rows.append(row)
            continue
        module = types.ModuleType('moth_semantic_mutant')
        try:
            exec(compile(raw.replace(target, 'pass  # exact-site semantic mutation'), '<moth-mutant>', 'exec'), module.__dict__)
            control_rows = [{'id': key, 'preserved': module.evaluate(*args) == expected[key]
                             and expected[key]['consistency'] == 'CONSISTENT'} for key, args in cases.items()]
            case = negative(name)
            baseline, changed = adapter.evaluate(*case), module.evaluate(*case)
            row.update({'controls': control_rows, 'baseline': baseline['consistency'],
                        'baselineReason': baseline['reason'], 'mutant': changed['consistency']})
            row['status'] = ('CONTROL_BROKEN' if not all(c['preserved'] for c in control_rows)
                             else 'INVALID_BASELINE' if baseline['consistency'] != 'REFUTED' or baseline['reason'] != reason
                             else 'KILLED' if changed['consistency'] == 'CONSISTENT' else 'SURVIVED')
        except Exception as exc:
            row.update({'status': 'CRASHED', 'errorType': type(exc).__name__})
        rows.append(row)
    return {'schema': 'qev.moth-semantic-mutations.v0', 'mutations': rows,
            'expectedMutants': 7, 'expectedControlsPerMutant': 3}


def successful(report):
    rows = report.get('mutations', [])
    return (len(rows) == len(MUTANTS) and {r.get('id') for r in rows} == {m[0] for m in MUTANTS}
            and all(r.get('status') == 'KILLED' and len(r.get('controls', [])) == len(CONTROLS)
                    and {c.get('id') for c in r['controls']} == set(CONTROLS)
                    and all(c.get('preserved') is True for c in r['controls']) for r in rows))


if __name__ == '__main__':
    import sys
    report = run()
    sys.stdout.buffer.write(adapter.encode(report))
    sys.exit(0 if successful(report) else 1)
