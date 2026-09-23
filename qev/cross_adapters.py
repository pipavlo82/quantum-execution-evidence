"""Finite offline adapters over the unchanged IBM and Moth live profiles."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from . import live_common as live, moth_comet as moth
from .cross_provider import fact, issue

MOTH_ROOT = 'fixtures/moth-comet-v0/capture'


def moth_manifest():
    return moth.parse(live.read(live.ROOT, MOTH_ROOT + '/manifest.json'))


def roles_for(provider):
    if provider == 'ibm-direct':
        return live.ROLES
    # This v0 maps precisely the existing finite capture profile. Role names
    # come from pinned source bytes, never from untrusted traversal paths.
    return tuple(sorted((*moth_manifest()['files'], 'manifest.json')))


def fixture(provider):
    from .cross_provider import check_sources, PROVIDERS
    check_sources()
    if provider not in PROVIDERS:
        raise live.Rejected('PROVIDER_UNSUPPORTED')
    root = 'fixtures/live-capture-v1' if provider == 'ibm-direct' else MOTH_ROOT
    claim_path = ('fixtures/live-capture-v1/claim.json' if provider == 'ibm-direct'
                  else 'fixtures/moth-comet-v0/claim.json')
    return (moth.parse(live.read(live.ROOT, claim_path)),
            {name: live.read(live.ROOT, root + '/' + name) for name in roles_for(provider)})


def classify(report, state, reason):
    kind = {'REFUTED': 'contradiction', 'REJECTED': 'malformed',
            'UNVERIFIABLE': 'missing', 'CANNOT_RECOMPUTE': 'unavailable'}[state]
    issue(report['common']['issues'], kind, reason)


def capabilities(provider):
    absent = 'UNAVAILABLE' if provider == 'moth-comet' else 'NOT_EVALUATED'
    basis = 'PROFILE_LIMIT' if provider == 'moth-comet' else 'NONE'
    caps = {key: fact(absent, basis, detail) for key, detail in {
        'circuitBytes': 'No circuit bytes in Moth counts evidence; IBM uses captured operation snapshots.',
        'orderedShots': 'Counts do not determine shot order.',
        'measurementMapping': 'Provider-specific mapping requires circuit and measurement evidence.',
        'idealCircuitRelation': 'Finite IBM ideal two-qubit relation only.',
    }.items()}
    caps.update({key: fact('NOT_ESTABLISHED', 'PROFILE_LIMIT', detail) for key, detail in {
        'commitmentTiming': 'No independent prior-publication attestation.',
        'seedProvenance': 'No pinned seed ceremony.',
        'nonemptyExtraction': 'No established nonempty extraction relation.',
        'entropyQualification': 'Counts consistency and witness algebra do not certify entropy.',
    }.items()})
    return caps


def preflight(report, claim, payloads):
    """Collect all byte contradictions, missing roles and malformed JSON together."""
    provider = report['identity']['provider']
    issues = report['common']['issues']
    if provider == 'ibm-direct':
        live.validate_claim(claim)
        anchors = claim['anchors']
    else:
        live.fields(claim, ('schema', 'profile', 'jobId', 'manifestSha256',
                            'requestSha256', 'origin', 'authority'))
        expected = {'schema': 'qev.moth-comet-claim.v0', 'profile': moth.PROFILE,
                    'origin': 'LIVE_MOTH_API_CAPTURE', 'authority': 'LOCAL_UNSIGNED_CAPTURE_COMMITMENT'}
        if any(claim[k] != v for k, v in expected.items()):
            raise live.Rejected('MOTH_CLAIM_CONTRACT')
        if type(claim['jobId']) is not str or not 0 < len(claim['jobId']) <= 200:
            raise live.Rejected('MOTH_CLAIM_JOB')
        for key in ('manifestSha256', 'requestSha256'):
            moth.digest(claim[key], 'MOTH_CLAIM_DIGEST')
        anchors = {'manifest.json': claim['manifestSha256'],
                   moth_manifest()['roles']['request']: claim['requestSha256']}
    for name, expected in anchors.items():
        if name in payloads and live.sha(payloads[name]) != expected:
            issue(issues, 'contradiction', 'CLAIM_ANCHOR:' + name)
    data = {}
    for name, raw in payloads.items():
        if name.endswith('.json'):
            try:
                data[name] = moth.parse(raw)
            except moth.MothError as exc:
                issue(issues, 'malformed', name + ':' + exc.reason)
    if provider == 'moth-comet' and 'manifest.json' in data:
        manifest = data['manifest.json']
        try:
            live.fields(manifest, ('schema', 'roles', 'files'))
            reference = moth_manifest()
            live.fields(manifest['files'], reference['files'])
            if manifest['schema'] != reference['schema'] or moth.compact(manifest['roles']) != moth.compact(reference['roles']):
                raise live.Rejected('MANIFEST_CONTRACT')
            for name, row in manifest['files'].items():
                live.fields(row, ('sha256', 'bytes'))
                moth.digest(row['sha256'], 'MANIFEST_DIGEST')
                moth.integer(row['bytes'], 0, 4_194_304, 'MANIFEST_LENGTH')
                if name in payloads and (live.sha(payloads[name]) != row['sha256'] or len(payloads[name]) != row['bytes']):
                    issue(issues, 'contradiction', 'MANIFEST_MEMBER:' + name)
        except (live.Rejected, moth.MothError, TypeError, KeyError) as exc:
            issue(issues, 'malformed', 'MANIFEST:' + str(exc))
    return data


def ibm(report, claim, payloads, data):
    from .live_native import case_from_payloads, make_bundle, recompute
    from .live_portable import create, replay
    bundle = make_bundle(case_from_payloads(claim, payloads))
    result = recompute(bundle, claim)
    canonical = result['canonicalResult']
    report['providerSpecific']['result'] = result
    report['nativeLayers']['RVR'].update(status='EXECUTED', result={
        'verificationOutcome': result['verificationOutcome'],
        'recomputationStatus': result['recomputationStatus'], 'identities': result['identities']})
    native = canonical['nativeTsei']
    if native is not None:
        report['nativeLayers']['TSEI'].update(status='EXECUTED', result=native)
    for axis, state in canonical['axes'].items():
        if state == 'REFUTED':
            issue(report['common']['issues'], 'contradiction', 'IBM:' + axis)
        elif state == 'CANNOT_ESTABLISH':
            issue(report['common']['issues'], 'missing', 'IBM:' + axis)
    if canonical['outcome'] != 'VERIFIED':
        return
    # Native root verification runs now. A stored EXECUTED label is insufficient.
    portable = replay(create(bundle, claim), claim)
    report['nativeLayers']['ReceiptOS'].update(status='EXECUTED', result=portable['receiptOs'])
    counts = dict(Counter(payloads['measurements-ordered.c1c0.txt'].decode('ascii').splitlines()))
    report['common']['observation'] = observation(
        claim['jobId'], claim['backend'], int(claim['shots']), counts, 2, 'ORDERED_SHOTS', 'DONE')
    for key, detail in {
        'circuitBytes': 'Captured logical, submitted and returned operation snapshots; byte consistency only.',
        'orderedShots': 'Captured IBM BitArray order; no authentication of physical acquisition.',
        'measurementMapping': 'c1c0 plus finite logical/ISA/intent measurement map agreement.',
        'idealCircuitRelation': 'Native TSEI executes finite ideal Q(zeta_8) relation modulo global phase.',
    }.items():
        report['capabilities'][key] = fact('ESTABLISHED', 'INDEPENDENTLY_RECOMPUTED', detail)


def observation(job, backend, requested, counts, width, representation, completion):
    return {'jobId': fact('REPORTED', 'UPSTREAM_REPORTED', job),
            'backend': fact('REPORTED', 'UPSTREAM_REPORTED', backend),
            'completion': fact('REPORTED', 'UPSTREAM_REPORTED', completion),
            'requestBinding': 'CONSISTENT_WITH_LOCAL_CLAIM',
            'sample': {'representation': representation, 'width': width,
                       'requestedShots': requested, 'observedShots': sum(counts.values()),
                       'uniqueBitstrings': len(counts), 'countsSha256': live.sha(moth.compact(counts)),
                       'digestRule': 'sha256-sorted-compact-ascii-json-counts-v0',
                       'basis': 'INDEPENDENTLY_RECOMPUTED'}}


def comet(report, claim, payloads, data):
    from .moth_replay import load_capture
    if report['common']['issues']['missing']:
        return
    # Run the unchanged byte/capture loader on this immutable in-memory snapshot.
    # Finite role allowlist was checked before any path is written.
    with TemporaryDirectory(prefix='qev-cross-moth-') as temporary:
        for name, raw in payloads.items():
            (Path(temporary) / name).write_bytes(raw)
        args = load_capture(temporary, claim)
    result = moth.evaluate(*args)
    report['providerSpecific']['result'] = result
    if result['consistency'] != 'CONSISTENT':
        classify(report, result['consistency'], 'MOTH:' + result['reason'])
        return
    out = args[4]['result']['output']
    p = out['provenance']
    report['common']['observation'] = observation(claim['jobId'], p['backend'],
        args[0]['params']['shots'], out['raw']['counts'], result['width'], 'COUNTS_ONLY', 'completed')
    report['capabilities']['circuitHash'] = fact('REPORTED', 'UPSTREAM_REPORTED', p['circuit_hash'])
    report['capabilities']['commitmentEncoding'] = fact('UNRESOLVED', 'PROFILE_LIMIT',
        'Cross-field agreement; preimage encoding unresolved, not a proven mismatch.')
    report['capabilities']['countsHashEncoding'] = fact('OBSERVED_MATCH', 'LOCAL_INFERENCE',
        result['hashEncodingAuthority'])
    report['capabilities']['outputDelivery'] = fact('PRESERVED', 'INDEPENDENTLY_RECOMPUTED',
        {'requestedBytes': result['requestedBytes'], 'deliveredBytes': result['deliveredBytes'],
         'delivery': result['delivery']})


def assess(report, claim, payloads):
    provider = report['identity']['provider']
    report['capabilities'] = capabilities(provider)
    try:
        data = preflight(report, claim, payloads)
        if report['common']['issues']['malformed']:
            return
        if provider == 'ibm-direct':
            ibm(report, claim, payloads, data)
        else:
            comet(report, claim, payloads, data)
    except live.CannotRecompute as exc:
        issue(report['common']['issues'], 'unavailable', str(exc))
    except moth.MothError as exc:
        classify(report, exc.state, exc.reason)
    except (live.Rejected, KeyError, TypeError, ValueError) as exc:
        issue(report['common']['issues'], 'malformed', str(exc))
    except OSError:
        issue(report['common']['issues'], 'unavailable', 'LOCAL_IO_UNAVAILABLE')
