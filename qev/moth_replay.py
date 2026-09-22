"""Replay the pinned raw HTTP capture offline, with an external local claim."""
import argparse
import re
import sys
from pathlib import Path

from . import sources
from .moth_comet import PROFILE, REQUEST, LIMITS, MothError, compact, encode, equal, evaluate, need, parse, sha

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/moth-comet-v0'


def safe_read(root, name):
    need(type(name) is str and re.fullmatch('[A-Za-z0-9_.-]+', name) is not None
         and name not in ('.', '..'), 'CAPTURE_PATH')
    root = Path(root).absolute()
    path = root / name
    for part in (path, *path.parents):
        need(not part.is_symlink() and not part.is_junction(), 'CAPTURE_LINK')
    need(path.resolve().is_relative_to(root.resolve()), 'CAPTURE_PATH')
    need(path.stat().st_size <= 4_194_304, 'CAPTURE_SIZE')
    return path.read_bytes()


def load_capture(directory, claim):
    need(type(claim) is dict and set(claim) == {'schema', 'profile', 'jobId', 'manifestSha256',
         'requestSha256', 'origin', 'authority'}, 'CLAIM_FIELDS')
    equal(claim['schema'], 'qev.moth-comet-claim.v0', 'CLAIM_SCHEMA')
    equal(claim['profile'], PROFILE, 'CLAIM_PROFILE')
    equal(claim['origin'], 'LIVE_MOTH_API_CAPTURE', 'CLAIM_ORIGIN')
    equal(claim['authority'], 'LOCAL_UNSIGNED_CAPTURE_COMMITMENT', 'CLAIM_AUTHORITY')
    manifest_bytes = safe_read(directory, 'manifest.json')
    equal(sha(manifest_bytes), claim['manifestSha256'], 'MANIFEST_ANCHOR')
    manifest = parse(manifest_bytes)
    need(set(manifest) == {'schema', 'roles', 'files'}, 'MANIFEST_FIELDS')
    equal(manifest['schema'], 'qev.moth-http-capture.v0', 'MANIFEST_SCHEMA')
    files, roles = manifest['files'], manifest['roles']
    need(type(files) is dict and 8 <= len(files) <= 4000, 'FILE_INVENTORY')
    need(set(roles) == {'request', 'submit', 'statuses', 'job', 'result'}, 'ROLE_INVENTORY')
    need(type(roles['statuses']) is list and 1 <= len(roles['statuses']) <= 1000, 'STATUS_INVENTORY')
    role_names = [roles[k] for k in ('request', 'submit', 'job', 'result')] + roles['statuses']
    need(all(type(n) is str for n in role_names) and len(set(role_names)) == len(role_names), 'DUPLICATE_ROLE')
    need(set(role_names) <= set(files), 'MISSING_ROLE')
    actual = {p.name for p in Path(directory).iterdir()}
    need(actual == set(files) | {'manifest.json'}, 'CAPTURE_FILE_INVENTORY')
    payloads = {}
    total = 0
    for name, row in sorted(files.items()):
        need(type(row) is dict and set(row) == {'sha256', 'bytes'}, 'FILE_IDENTITY_FIELDS')
        raw = safe_read(directory, name)
        total += len(raw)
        need(total <= 8_388_608, 'CAPTURE_TOTAL_SIZE')
        equal(len(raw), row['bytes'], 'FILE_LENGTH:' + name)
        equal(sha(raw), row['sha256'], 'FILE_HASH:' + name)
        payloads[name] = parse(raw)
    request = payloads[roles['request']]
    equal(sha(safe_read(directory, roles['request'])), claim['requestSha256'], 'REQUEST_ANCHOR')
    equal(request, REQUEST, 'REQUEST_PROFILE_MISMATCH')
    marker = payloads['SUBMIT_ATTEMPTED.json']
    equal(marker, {'post_attempt_authorized': 1, 'retry_allowed': False, 'ibm_token_sent': False}, 'SUBMIT_MARKER')
    equal(payloads['job-reference.json']['submit_calls'], 1, 'SUBMIT_COUNT')
    equal(payloads['job-reference.json']['job_id'], claim['jobId'], 'REFERENCE_JOB_BINDING')
    posts = []
    for name, value in payloads.items():
        if not name.endswith('.http.json'):
            continue
        body = value['body_file']
        need(body == name.replace('.http.json', '.body.json') and body in files, 'HTTP_BODY_BINDING')
        equal(value['sha256'], files[body]['sha256'], 'HTTP_BODY_HASH')
        equal(value['byte_length'], files[body]['bytes'], 'HTTP_BODY_LENGTH')
        if value['method'] == 'POST':
            posts.append(name)
    equal(posts, ['submit.http.json'], 'HTTP_POST_INVENTORY')
    expected_paths = {
        roles['submit']: ('POST', '/api/v1/engines/comet-qrng-v1/process', 202),
        roles['job']: ('GET', '/api/v1/jobs/' + claim['jobId'], 200),
        roles['result']: ('GET', '/api/v1/jobs/' + claim['jobId'] + '/result', 200),
        **{n: ('GET', '/api/v1/jobs/' + claim['jobId'] + '/status', 200) for n in roles['statuses']},
    }
    for name, (method, path, status) in expected_paths.items():
        meta = payloads[name.replace('.body.json', '.http.json')]
        equal([meta['method'], meta['path'], meta['status']], [method, path, status], 'HTTP_REQUEST_BINDING')
    return (request, payloads[roles['submit']], [payloads[n] for n in roles['statuses']],
            payloads[roles['job']], payloads[roles['result']], claim['jobId'])


def replay(directory, claim):
    try:
        source_report = sources.validate()
        need(sources.successful(source_report), 'SOURCE_LOCK_UNAVAILABLE_OR_MISMATCH', 'CANNOT_RECOMPUTE')
        args = load_capture(directory, claim)
        report = evaluate(*args)
        report['captureIntegrity'] = 'MATCH_LOCAL_UNSIGNED_CLAIM'
        report['manifestSha256'] = claim['manifestSha256']
        report['sourceLock'] = 'MATCH'
        return report
    except MothError as exc:
        state, reason = exc.state, exc.reason
    except OSError:
        state, reason = 'UNVERIFIABLE', 'CAPTURE_OR_SOURCE_UNAVAILABLE'
    except (KeyError, TypeError, ValueError):
        state, reason = 'REJECTED', 'CAPTURE_SHAPE'
    return {'schema': 'qev.moth-comet-report.v0', 'profile': PROFILE,
            'consistency': state, 'reason': reason, 'limits': dict(LIMITS)}


def main():
    parser = argparse.ArgumentParser(description='Offline Moth Comet preserved counts replay')
    parser.add_argument('capture', nargs='?')
    parser.add_argument('--claim', help='Independent local claim; required for a custom capture')
    args = parser.parse_args()
    if args.capture and not args.claim:
        parser.error('--claim is required for a custom capture')
    try:
        claim = parse(Path(args.claim or FIXTURE / 'claim.json').read_bytes())
        report = replay(Path(args.capture or FIXTURE / 'capture'), claim)
    except (OSError, MothError):
        report = {'consistency': 'REJECTED', 'reason': 'CLAIM_UNAVAILABLE_OR_INVALID', 'limits': dict(LIMITS)}
    sys.stdout.buffer.write(encode(report))
    return {'CONSISTENT': 0, 'REFUTED': 1, 'REJECTED': 2,
            'UNVERIFIABLE': 3, 'CANNOT_RECOMPUTE': 3}.get(report['consistency'], 2)


if __name__ == '__main__':
    sys.exit(main())
