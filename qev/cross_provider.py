"""Provider-neutral evidence projection v0; never a provider attestation."""
from .live_common import ROOT, CannotRecompute, Rejected, fields, read, sha
from .moth_comet import compact, encode, parse, MothError

SCHEMA = 'qev.cross-provider-evidence.v0'
PROFILE = 'profiles/cross-provider-evidence-v0'
PROVIDERS = ('ibm-direct', 'moth-comet')
FILES = (
    'qev/cross_provider.py', 'qev/cross_adapters.py', 'qev/cross_cli.py',
    'qev/cross_mutations.py', 'tests/test_cross_provider.py',
    'docs/CROSS_PROVIDER_EVIDENCE_V0.md', PROFILE + '/profile.json',
    'tools/pin_cross_profile.py',
)
KINDS = ('missing', 'contradiction', 'malformed', 'unavailable')


def check_sources():
    """Separate additive lock keeps every legacy profile/runtime byte frozen."""
    from . import sources
    if not sources.successful(sources.validate()):
        raise CannotRecompute('LEGACY_SOURCE_LOCK')
    try:
        lock = parse(read(ROOT, PROFILE + '/sources.json'))
        fields(lock, ('schema', 'files'))
        if lock['schema'] != 'qev.cross-provider-sources.v0':
            raise Rejected('CROSS_SOURCE_SCHEMA')
        fields(lock['files'], FILES)
        for name in FILES:
            if sha(read(ROOT, name)) != lock['files'][name]:
                raise Rejected('CROSS_SOURCE_IDENTITY:' + name)
    except (OSError, Rejected, MothError) as exc:
        raise CannotRecompute('CROSS_SOURCE_LOCK') from exc


def issue(issues, kind, reason):
    if reason not in issues[kind]:
        issues[kind].append(reason)


def consistency(issues):
    # Shape admission takes precedence, but every observed issue is retained.
    if issues['malformed']:
        return 'MALFORMED'
    if issues['contradiction']:
        return 'CONTRADICTED'
    if issues['unavailable']:
        return 'CANNOT_RECOMPUTE'
    if issues['missing']:
        return 'INCOMPLETE'
    return 'CONSISTENT'


def fact(status, basis, detail):
    return {'status': status, 'basis': basis, 'detail': detail}


def initial(provider, claim, payloads, roles):
    issues = {kind: [] for kind in KINDS}
    members = []
    for name in sorted(roles):
        raw = payloads.get(name)
        if raw is None:
            issue(issues, 'missing', 'EVIDENCE:' + name)
            members.append({'role': name, 'availability': 'MISSING'})
        else:
            members.append({'role': name, 'availability': 'PRESENT',
                            'sha256': sha(raw), 'bytes': len(raw)})
    native_state = 'NOT_INTEGRATED' if provider == 'moth-comet' else 'NOT_EXECUTED'
    return {
        'schema': SCHEMA,
        'identity': {'provider': provider, 'claimSha256': sha(compact(claim)),
                     'evidenceSetSha256': sha(compact(members)),
                     'authority': 'LOCAL_UNSIGNED_CLAIM', 'members': members},
        'common': {'consistency': 'INCOMPLETE', 'issues': issues,
                   'providerAuthentication': 'NOT_ESTABLISHED',
                   'observation': None},
        'capabilities': {},
        'nativeLayers': {name: {'status': native_state, 'scope': provider,
                               'result': None} for name in ('RVR', 'TSEI', 'ReceiptOS')},
        'providerSpecific': {'profile': ('rvr-qev-live-capture-replay-v1' if provider == 'ibm-direct'
                                        else 'qev-moth-comet-counts-v0'), 'result': None},
    }


def evaluate(provider, claim, payloads):
    """Only raw bytes plus an external claim enter; no supplied verdict trusted."""
    from .cross_adapters import assess, roles_for
    if type(provider) is not str or provider not in PROVIDERS:
        raise Rejected('PROVIDER_UNSUPPORTED')
    if type(payloads) is not dict:
        raise Rejected('PAYLOAD_MAP')
    # Strict JSON admission for programmatic claims, including booleans/numbers.
    claim = parse(compact(claim))
    roles = roles_for(provider)
    if not set(payloads) <= set(roles):
        raise Rejected('UNKNOWN_EVIDENCE_ROLE')
    if any(type(raw) is not bytes or len(raw) > 4_194_304 for raw in payloads.values()):
        raise Rejected('PAYLOAD_TYPE_OR_SIZE')
    if sum(map(len, payloads.values())) > 8_388_608:
        raise Rejected('PAYLOAD_TOTAL_SIZE')
    report = initial(provider, claim, payloads, roles)
    check_sources()
    assess(report, claim, payloads)
    issues = report['common']['issues']
    for reasons in issues.values():
        reasons.sort()
    report['common']['consistency'] = consistency(issues)
    return report


def compare_report(saved, fresh):
    """Closed, type-sensitive comparison after recomputation, not schema-only QA."""
    fields(saved, fresh)
    fields(saved['common'], fresh['common'])
    def equal(actual, expected, reason):
        if compact(actual) != compact(expected):
            raise Rejected(reason)
    equal(saved['schema'], SCHEMA, 'SCHEMA')
    equal(saved['identity'], fresh['identity'], 'IDENTITY')
    equal(saved['common']['providerAuthentication'], fresh['common']['providerAuthentication'], 'AUTHENTICATION')
    equal(saved['common']['consistency'], fresh['common']['consistency'], 'CONSISTENCY')
    equal(saved['common']['issues'], fresh['common']['issues'], 'ISSUES')
    equal(saved['common']['observation'], fresh['common']['observation'], 'OBSERVATION')
    equal(saved['capabilities'], fresh['capabilities'], 'CAPABILITIES')
    equal(saved['nativeLayers'], fresh['nativeLayers'], 'NATIVE_LAYERS')
    equal(saved['providerSpecific'], fresh['providerSpecific'], 'PROVIDER_SPECIFIC')
    return True


def replay(saved, provider, claim, payloads):
    fresh = evaluate(provider, claim, payloads)
    compare_report(saved, fresh)
    return {'schema': 'qev.cross-provider-replay.v0', 'projection': 'REPRODUCED',
            'consistency': fresh['common']['consistency'],
            'providerAuthentication': 'NOT_ESTABLISHED',
            'reportSha256': sha(encode(fresh))}


def exit_code(report):
    return {'CONSISTENT': 0, 'CONTRADICTED': 1, 'MALFORMED': 2,
            'INCOMPLETE': 3, 'CANNOT_RECOMPUTE': 3}[report['common']['consistency']]
