"""Seven applied source mutants with unchanged positive controls; no crash kills."""
import copy
import types
from . import moth_rvr as native, moth_rvr_relation as relation
from .moth_comet import parse, encode, sha

MUTANTS = (
    ('manifest-anchor', "sha(payloads['manifest.json']) == old['manifestSha256']", 'True'),
    ('request-anchor', "sha(payloads[request]) == old['requestSha256']", 'True'),
    ('member-identity', "sha(payloads[name]) == row['sha256'] and len(payloads[name]) == row['bytes']", 'True'),
    ('assigned-job', "data[name]['job_id'] == old['jobId']", 'True'),
    ('missing-outcome', "'UNVERIFIABLE' if missing", "'VERIFIED' if missing"),
    ('contradiction-outcome', "'REFUTED' if contradictions", "'VERIFIED' if contradictions"),
    ('counts-refutation', "contradictions.append('COUNTS:' + reason)", 'pass'),
)
CONTROLS = ('preserved-capture', 'payload-map-order', 'counts-key-order')


def inventory():
    return {'schema': 'qev.moth-rvr-falsification.v0', 'controls': list(CONTROLS),
            'mutants': [{'id': name, 'source': 'qev/moth_rvr_relation.py', 'before': before, 'after': after}
                        for name, before, after in MUTANTS]}


def reanchor(claim, payloads):
    """Synthetic test record with newly committed HTTP and manifest bytes."""
    claim, payloads = copy.deepcopy(claim), dict(payloads)
    manifest = parse(payloads['manifest.json'])
    for name in payloads:
        if name.endswith('.http.json'):
            meta = parse(payloads[name])
            body = payloads[meta['body_file']]
            meta.update(sha256=sha(body), byte_length=len(body))
            payloads[name] = encode(meta)
    for name in manifest['files']:
        manifest['files'][name] = {'sha256': sha(payloads[name]), 'bytes': len(payloads[name])}
    payloads['manifest.json'] = encode(manifest)
    claim['captureClaim'].update(manifestSha256=sha(payloads['manifest.json']),
                                requestSha256=sha(payloads[manifest['roles']['request']]))
    return claim, payloads


def edit_result(claim, payloads, change):
    payloads = dict(payloads)
    roles = native.contract()['roles']
    result = parse(payloads[roles['result']])
    change(result['result']['output'])
    payloads[roles['result']] = encode(result)
    status = parse(payloads[roles['statuses'][-1]])
    status['result'] = copy.deepcopy(result['result'])
    payloads[roles['statuses'][-1]] = encode(status)
    return reanchor(claim, payloads)


def controls():
    claim, payloads = native.fixture()
    reordered = edit_result(claim, payloads, lambda out: out['raw'].update(
        counts=dict(reversed(list(out['raw']['counts'].items())))))
    return dict(zip(CONTROLS, ((claim, payloads), (claim, dict(reversed(list(payloads.items())))), reordered)))


def negative(name):
    claim, payloads = native.fixture()
    roles = native.contract()['roles']
    if name in ('manifest-anchor', 'contradiction-outcome'):
        claim['captureClaim']['manifestSha256'] = '0' * 64
    elif name == 'request-anchor':
        claim['captureClaim']['requestSha256'] = '0' * 64
    elif name == 'member-identity':
        payloads['terminal-observation.json'] += b' '
        del payloads[roles['result']]
    elif name == 'assigned-job':
        claim['captureClaim']['jobId'] = 'different-job'
        del payloads['manifest.json']
    elif name == 'missing-outcome':
        payloads = {}
    elif name == 'counts-refutation':
        return edit_result(claim, payloads, lambda out: out['entropy_report'].update(grade='hardware'))
    else:
        raise ValueError(name)
    if name in ('manifest-anchor', 'request-anchor'):
        del payloads['terminal-observation.json']
    return claim, payloads


def run():
    native.check_sources()
    raw = (native.ROOT / 'qev/moth_rvr_relation.py').read_text(encoding='utf-8')
    contract = native.contract()
    cases = controls()
    expected = {key: relation.evaluate(*args, contract) for key, args in cases.items()}
    rows = []
    for name, before, after in MUTANTS:
        row = {'id': name, 'status': 'UNAPPLIED', 'controls': []}
        rows.append(row)
        if raw.count(before) != 1:
            continue
        module = types.ModuleType('qev.moth_rvr_relation_mutant')
        module.__package__ = 'qev'
        try:
            exec(compile(raw.replace(before, after), '<moth-rvr-mutant>', 'exec'), module.__dict__)
            row['controls'] = [{'id': key, 'preserved': module.evaluate(*args, contract) == expected[key]
                                and expected[key]['outcome'] == 'VERIFIED'} for key, args in cases.items()]
            args = negative(name)
            baseline = relation.evaluate(*args, contract)
            changed = module.evaluate(*args, contract)
            wanted = 'UNVERIFIABLE' if name == 'missing-outcome' else 'REFUTED'
            after_outcome = 'UNVERIFIABLE' if name in ('assigned-job', 'member-identity', 'manifest-anchor', 'request-anchor') else 'VERIFIED'
            row.update(baseline=baseline['outcome'], mutant=changed['outcome'])
            row['status'] = ('CONTROL_BROKEN' if not all(r['preserved'] for r in row['controls'])
                             else 'INVALID_BASELINE' if baseline['outcome'] != wanted
                             else 'KILLED' if changed['outcome'] == after_outcome else 'SURVIVED')
        except Exception as exc:
            row.update(status='CRASHED', errorType=type(exc).__name__)
    return {'schema': 'qev.moth-rvr-mutations.v0', 'mutations': rows,
            'expectedMutants': len(MUTANTS), 'expectedControlsPerMutant': len(CONTROLS)}


def successful(report):
    rows = report.get('mutations', [])
    return (len(rows) == len(MUTANTS) and {r['id'] for r in rows} == {m[0] for m in MUTANTS}
            and all(r['status'] == 'KILLED' and len(r['controls']) == len(CONTROLS)
                    and {c['id'] for c in r['controls']} == set(CONTROLS)
                    and all(c['preserved'] is True for c in r['controls']) for r in rows))


if __name__ == '__main__':
    import sys
    report = run()
    sys.stdout.buffer.write(encode(report))
    sys.exit(0 if successful(report) else 1)
