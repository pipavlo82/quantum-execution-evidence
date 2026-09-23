"""Counts-only relation; no provider calls, shot reconstruction or attestation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from . import moth_comet as moth
from .live_common import fields, need, Rejected, sha

LIMITS = {
    'providerAuthentication': 'NOT_ESTABLISHED',
    'physicalQpuExecution': 'UPSTREAM_REPORTED_NOT_INDEPENDENTLY_AUTHENTICATED',
    'entropyQualification': 'NOT_ESTABLISHED',
    'cryptographicRandomness': 'NOT_ESTABLISHED',
    'circuitProvenance': 'UNAVAILABLE_NO_CIRCUIT_BYTES',
    'measurementProvenance': 'NOT_ESTABLISHED',
    'shotOrder': 'UNAVAILABLE_COUNTS_ONLY',
    'commitmentEncoding': 'UNRESOLVED',
    'commitmentTiming': 'NOT_ESTABLISHED',
    'seedProvenance': 'NOT_ESTABLISHED',
    'nonemptyToeplitzExtraction': 'NOT_ESTABLISHED',
    'receiptOS': 'NOT_INTEGRATED_FOR_THIS_PROFILE',
    'TSEI': 'NOT_INTEGRATED_FOR_THIS_PROFILE',
}


def evaluate(claim, payloads, contract):
    """Preflight available bytes before considering missing decisive members."""
    from .moth_replay import load_capture
    missing = sorted(set(contract['members']) - set(payloads))
    contradictions = []
    def check(ok, reason):
        if not ok:
            contradictions.append(reason)
    old = claim['captureClaim']
    data = {name: moth.parse(raw) for name, raw in payloads.items()}
    for name, value in data.items():
        need(type(value) is dict, 'CAPTURE_JSON_OBJECT:' + name)
    if 'manifest.json' in payloads:
        check(sha(payloads['manifest.json']) == old['manifestSha256'], 'CLAIM_MANIFEST')
    request = contract['roles']['request']
    if request in payloads:
        fields(data[request], ('mode', 'params'))
        fields(data[request]['params'], moth.REQUEST['params'])
        need(type(data[request]['mode']) is str and all(
            type(data[request]['params'][key]) is type(value)
            for key, value in moth.REQUEST['params'].items()), 'REQUEST_FIELD_TYPES')
        check(sha(payloads[request]) == old['requestSha256'], 'CLAIM_REQUEST')
        check(moth.compact(data[request]) == moth.compact(moth.REQUEST), 'REQUEST_PROFILE')
    if 'manifest.json' in data:
        manifest = data['manifest.json']
        fields(manifest, ('schema', 'roles', 'files'))
        fields(manifest['files'], [n for n in contract['members'] if n != 'manifest.json'])
        need(manifest['schema'] == 'qev.moth-http-capture.v0' and
             moth.compact(manifest['roles']) == moth.compact(contract['roles']), 'MANIFEST_CONTRACT')
        for name, row in manifest['files'].items():
            fields(row, ('sha256', 'bytes'))
            moth.digest(row['sha256'], 'MANIFEST_DIGEST')
            moth.integer(row['bytes'], 0, 4_194_304, 'MANIFEST_LENGTH')
            if name in payloads:
                check(sha(payloads[name]) == row['sha256'] and len(payloads[name]) == row['bytes'],
                      'MANIFEST_MEMBER:' + name)
    # Assigned job contradictions remain visible even with another absent role.
    for name in [contract['roles']['submit'], contract['roles']['job'], *contract['roles']['statuses']]:
        if name in data:
            need(type(data[name]) is dict and type(data[name].get('job_id')) is str, 'JOB_SHAPE')
            check(data[name]['job_id'] == old['jobId'], 'JOB_BINDING:' + name)
    observation = None
    state, reason = 'NOT_EVALUATED', 'INCOMPLETE_OR_CONTRADICTORY_CAPTURE'
    if not missing and not contradictions:
        try:
            with TemporaryDirectory(prefix='qev-moth-rvr-') as temporary:
                for name, raw in payloads.items():
                    (Path(temporary) / name).write_bytes(raw)
                args = load_capture(temporary, old)
            report = moth.evaluate(*args)
            state, reason = report['consistency'], report['reason']
        except moth.MothError as exc:
            state, reason = exc.state, exc.reason
        except (KeyError, TypeError, ValueError) as exc:
            raise Rejected('CAPTURE_SHAPE') from exc
        if state == 'REJECTED':
            raise Rejected(reason)
        if state == 'REFUTED':
            contradictions.append('COUNTS:' + reason)
        elif state == 'UNVERIFIABLE':
            missing.append('COUNTS:' + reason)
        elif state == 'CONSISTENT':
            out = args[4]['result']['output']
            observation = {
                'representation': 'COUNTS_ONLY',
                'shots': str(report['shots']), 'uniqueBitstrings': str(report['uniqueBitstrings']),
                'width': str(report['width']), 'countsSha256': report['countsSha256'],
                'witnessS': str(report['witnessS']),
                'witnessSigmaAlgebra': str(report['witnessSigmaAlgebra']),
                'requestedBytes': str(report['requestedBytes']),
                'deliveredBytes': str(report['deliveredBytes']),
                'delivery': report['delivery'],
                'reportedGrade': out['entropy_report']['grade'],
                'gradeAuthority': 'UPSTREAM_REPORTED_ARITHMETIC_CHECKED_NOT_ENTROPY_CERTIFIED',
            }
        else:
            need(state == 'REFUTED', 'UNEXPECTED_COUNTS_STATE')
    outcome = 'REFUTED' if contradictions else 'UNVERIFIABLE' if missing else 'VERIFIED'
    return {'schema': 'rvr.qev.moth-counts-result.v0', 'outcome': outcome,
            'reasonCode': 'qev.moth.rvr.v0.' + outcome.lower(),
            'issues': {'missing': sorted(set(missing)), 'contradiction': sorted(set(contradictions))},
            'countsVerification': {'state': state, 'reason': reason},
            'observation': observation, 'limits': dict(LIMITS)}
