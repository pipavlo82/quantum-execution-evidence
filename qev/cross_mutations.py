"""Exact-site projection and classification mutations; errors are not kills."""
import copy
import types

from . import cross_provider as model
from .cross_adapters import fixture
from .live_common import ROOT, Rejected
from .moth_comet import encode

CONTROLS = ('ibm-direct', 'moth-comet', 'reordered-moth')
MUTANTS = (
    ('identity', "equal(saved['identity'], fresh['identity'], 'IDENTITY')", 'IDENTITY'),
    ('authentication', "equal(saved['common']['providerAuthentication'], fresh['common']['providerAuthentication'], 'AUTHENTICATION')", 'AUTHENTICATION'),
    ('consistency', "equal(saved['common']['consistency'], fresh['common']['consistency'], 'CONSISTENCY')", 'CONSISTENCY'),
    ('issues', "equal(saved['common']['issues'], fresh['common']['issues'], 'ISSUES')", 'ISSUES'),
    ('observation', "equal(saved['common']['observation'], fresh['common']['observation'], 'OBSERVATION')", 'OBSERVATION'),
    ('capabilities', "equal(saved['capabilities'], fresh['capabilities'], 'CAPABILITIES')", 'CAPABILITIES'),
    ('native_layers', "equal(saved['nativeLayers'], fresh['nativeLayers'], 'NATIVE_LAYERS')", 'NATIVE_LAYERS'),
    ('provider_specific', "equal(saved['providerSpecific'], fresh['providerSpecific'], 'PROVIDER_SPECIFIC')", 'PROVIDER_SPECIFIC'),
    ('missing', "if issues['missing']:", 'INCOMPLETE'),
    ('contradiction', "if issues['contradiction']:", 'CONTRADICTED'),
    ('malformed', "if issues['malformed']:", 'MALFORMED'),
    ('unavailable', "if issues['unavailable']:", 'CANNOT_RECOMPUTE'),
)


def controls():
    result = {provider: model.evaluate(provider, *fixture(provider)) for provider in model.PROVIDERS}
    result['reordered-moth'] = dict(reversed(list(result['moth-comet'].items())))
    return result


def attack(name, fresh):
    saved = copy.deepcopy(fresh)
    if name == 'identity':
        saved['identity']['provider'] = 'ibm-direct'
    elif name == 'authentication':
        saved['common']['providerAuthentication'] = 'ESTABLISHED'
    elif name == 'consistency':
        saved['common']['consistency'] = 'VERIFIED'
    elif name == 'issues':
        saved['common']['issues']['contradiction'] = ['fabricated']
    elif name == 'observation':
        saved['common']['observation']['sample']['observedShots'] = 256
    elif name == 'capabilities':
        saved['capabilities']['measurementMapping']['status'] = 'ESTABLISHED'
    elif name == 'native_layers':
        saved['nativeLayers']['RVR']['status'] = 'EXECUTED'
    elif name == 'provider_specific':
        saved['providerSpecific']['result']['deliveredBytes'] = 32
    else:
        raise ValueError(name)
    return saved


def run():
    raw = (ROOT / 'qev/cross_provider.py').read_text(encoding='utf-8')
    cases = controls()
    rows = []
    for name, target, expected in MUTANTS:
        row = {'id': name, 'status': 'UNAPPLIED', 'controls': []}
        if raw.count(target) != 1:
            rows.append(row)
            continue
        module = types.ModuleType('qev._cross_mutant')
        module.__package__ = 'qev'
        replacement = 'if False:' if name in model.KINDS else 'pass  # disabled semantic comparison'
        try:
            exec(compile(raw.replace(target, replacement), '<cross-mutant>', 'exec'), module.__dict__)
            for key, fresh in cases.items():
                preserved = (fresh['common']['consistency'] == 'CONSISTENT'
                             and module.compare_report(fresh, fresh) is True
                             and module.consistency(fresh['common']['issues']) == 'CONSISTENT')
                row['controls'].append({'id': key, 'preserved': preserved})
            if name in model.KINDS:
                issues = {kind: [] for kind in model.KINDS}
                issues[name] = ['targeted-evidence-failure']
                baseline, changed = model.consistency(issues), module.consistency(issues)
            else:
                fresh = cases['moth-comet']
                saved = attack(name, fresh)
                try:
                    model.compare_report(saved, fresh)
                    baseline = 'ACCEPTED'
                except Rejected as exc:
                    baseline = str(exc)
                changed = 'ACCEPTED' if module.compare_report(saved, fresh) is True else 'NOT_ACCEPTED'
            row.update(baseline=baseline, mutant=changed)
            row['status'] = ('CONTROL_BROKEN' if not all(c['preserved'] for c in row['controls'])
                             else 'INVALID_BASELINE' if baseline != expected
                             else 'KILLED' if changed == ('CONSISTENT' if name in model.KINDS else 'ACCEPTED')
                             else 'SURVIVED')
        except Exception as exc:
            row.update(status='CRASHED', errorType=type(exc).__name__)
        rows.append(row)
    return {'schema': 'qev.cross-provider-mutations.v0', 'mutations': rows,
            'expectedMutants': len(MUTANTS), 'expectedControlsPerMutant': len(CONTROLS)}


def successful(report):
    rows = report.get('mutations', [])
    return (len(MUTANTS) == 12 and len(CONTROLS) == 3
            and len(rows) == 12 and len({m[0] for m in MUTANTS}) == 12
            and {r.get('id') for r in rows} == {m[0] for m in MUTANTS}
            and all(r.get('status') == 'KILLED' and len(r.get('controls', [])) == len(CONTROLS)
                    and {c.get('id') for c in r['controls']} == set(CONTROLS)
                    and all(c.get('preserved') is True for c in r['controls']) for r in rows))


if __name__ == '__main__':
    import sys
    report = run()
    sys.stdout.buffer.write(encode(report))
    sys.exit(0 if successful(report) else 1)
