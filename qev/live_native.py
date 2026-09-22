"""Audited native RVR primitives and native TSEI execution for live replay v1."""
import base64
import subprocess
import sys
import types
from pathlib import Path
from .live_common import (ROOT, PROFILE, ROLES, Rejected, CannotRecompute, need,
                          fields, sha, read, parse, encode, validate_claim)
from .source_inventory import ALL_VENDOR_FILES

RUNTIME = ('qev/live_common.py', 'qev/live_math.py', 'qev/live_relation.py',
           'qev/live_native.py', 'qev/live_portable.py', 'qev/live_cli.py',
           'qev/live_tsei_bridge.ts', 'qev/live_receiptos_bridge.ts',
           'qev/source_inventory.py', 'qev/__init__.py', 'qev/__main__.py',
           'qev/checker.py', 'qev/adapters.py', PROFILE + '/capture-shapes.json')


def dependencies(profile):
    return [profile['profileSchemaContract']['manifest'], profile['profileSchemaContract']['constraints'],
            profile['verificationSpecification'], *profile['schemaContracts'],
            *profile['conformanceVectorSet']['members']]


def check_sources(root=ROOT):
    # Check every vendored file before importing or executing any native code.
    for item in ALL_VENDOR_FILES:
        try:
            raw = read(root, item['path'])
        except (OSError, Rejected) as exc:
            raise CannotRecompute('SOURCE_UNAVAILABLE:' + item['path']) from exc
        if sha(raw) != item['sha256']:
            raise CannotRecompute('SOURCE_IDENTITY_MISMATCH:' + item['path'])
    try:
        profile_bytes = read(root, PROFILE + '/verification-profile.json')
    except OSError as exc:
        raise CannotRecompute('PROFILE_UNAVAILABLE') from exc
    profile = parse(profile_bytes)
    entries = dependencies(profile)
    required = {PROFILE + '/profile.schema.json', PROFILE + '/rvr-live.schema.json',
                'docs/LIVE_CAPTURE_REPLAY_V1.md', 'vendor/rvr-v0/verification-profile-manifest.schema.json',
                *RUNTIME, *(row['path'] for row in ALL_VENDOR_FILES
                            if row['path'] != 'vendor/rvr-v0/verification-profile-manifest.schema.json')}
    actual = [x['path'] for x in entries if x['requiredForRecomputation'] is True]
    need(len(actual) == len(set(actual)) and set(actual) == required, 'REQUIRED_DEPENDENCY_INVENTORY')
    for item in entries:
        if item['requiredForRecomputation'] is not True:
            continue
        try:
            raw = read(root, item['path'])
        except (OSError, Rejected) as exc:
            raise CannotRecompute('DEPENDENCY_UNAVAILABLE:' + item['path']) from exc
        if sha(raw) != item['sha256']:
            raise CannotRecompute('DEPENDENCY_IDENTITY_MISMATCH:' + item['path'])
    return profile


def context(root=ROOT):
    root = Path(root)
    profile = check_sources(root)
    path = root / 'vendor/rvr-v0/adapter.py'
    raw = read(root, 'vendor/rvr-v0/adapter.py')
    expected = next(row['sha256'] for row in ALL_VENDOR_FILES if row['path'] == 'vendor/rvr-v0/adapter.py')
    if sha(raw) != expected:
        raise CannotRecompute('SOURCE_IDENTITY_MISMATCH:vendor/rvr-v0/adapter.py')
    # Execute the audited source bytes, never an uncommitted cached .pyc.
    module = types.ModuleType('live_pinned_rvr')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    module.PROFILE_PACKAGE_ROOT = root
    manifest_bytes = read(root, 'vendor/rvr-v0/verification-profile-manifest.schema.json')
    digest, _, pinned = module.audit_profile(profile, parse(manifest_bytes), manifest_bytes)
    schema = parse(pinned['rvr-schema'])
    return module, profile, digest, schema


def bridge(name, value, root=ROOT):
    check_sources(root)
    try:
        result = subprocess.run(['bun', str(Path(root) / ('qev/' + name)), sys.executable, str(root)],
                                input=encode(value), cwd=root, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CannotRecompute('NATIVE_RUNTIME_UNAVAILABLE') from exc
    if result.returncode:
        raise CannotRecompute('NATIVE_BRIDGE_FAILED:' + result.stderr.decode('utf-8', 'replace')[:1000])
    return parse(result.stdout)


def tsei(source, target, root=ROOT):
    return bridge('live_tsei_bridge.ts', {'source': source, 'target': target, 'optimized': bool(sys.flags.optimize)}, root)


def case_from_payloads(claim, payloads):
    validate_claim(claim)
    need(set(payloads) <= set(ROLES), 'ROLE_INVENTORY')
    members = []
    for role in ROLES:
        if role in payloads:
            raw = payloads[role]
            members.append({'id': role, 'status': 'PRESENT', 'mediaType': 'application/octet-stream',
                            'byteLength': str(len(raw)), 'digest': sha(raw)})
        else:
            members.append({'id': role, 'status': 'UNAVAILABLE', 'reasonCode': 'qev.live.v1.evidence_unavailable'})
    return {'claim': claim, 'evidenceSet': {'schema': 'rvr.evidence-set.v0', 'members': members},
            'payloadsBase64': {k: base64.b64encode(v).decode('ascii') for k, v in payloads.items()}}


def evaluate_case(case, rvr, schema, root):
    from .live_relation import evaluate
    fields(case, ('claim', 'evidenceSet', 'payloadsBase64'))
    validate_claim(case['claim'])
    rvr.require_schema(case['claim'], schema, '#/$defs/claim', 'live claim')
    rvr.require_schema(case['evidenceSet'], schema, '#/$defs/evidenceSet', 'live evidence set')
    ids = [m['id'] for m in case['evidenceSet']['members']]
    need(len(ids) == len(ROLES) and set(ids) == set(ROLES), 'ROLE_INVENTORY')
    unresolved = rvr.unresolved_present_member(case['evidenceSet'], case['payloadsBase64'])
    if unresolved:
        raise CannotRecompute('COMMITTED_PRESENT_UNAVAILABLE:' + unresolved)
    payloads = rvr.validate_evidence_closure(case['evidenceSet'], case['payloadsBase64'])
    result = evaluate(case['claim'], payloads, root, lambda s, t: tsei(s, t, root))
    rvr.require_schema(result, schema, '#/$defs/canonicalResult', 'live result')
    return result


def make_bundle(case, root=ROOT):
    rvr, profile, digest, schema = context(root)
    result = evaluate_case(case, rvr, schema, root)
    receipt = {'claimDigest': rvr.canonical_digest(case['claim']),
               'evidenceSetDigest': rvr.evidence_set_digest(case['evidenceSet']),
               'verificationProfileDigest': digest, 'outcome': result['outcome'],
               'reasonCode': result['reasonCode'], 'resultDigest': rvr.canonical_digest(result)}
    bundle = {**case, 'receipt': receipt, 'verificationProfile': profile, 'canonicalResult': result}
    rvr.validate_receipt_envelope(bundle, digest, schema)
    return bundle


def recompute(bundle, expected_claim, candidate=None, root=ROOT):
    rvr, profile, digest, schema = context(root)
    fields(bundle, ('claim', 'evidenceSet', 'payloadsBase64', 'receipt', 'verificationProfile', 'canonicalResult'))
    validate_claim(expected_claim)
    need(rvr.json_same(bundle['claim'], expected_claim), 'INDEPENDENT_CLAIM_MISMATCH')
    need(rvr.json_same(bundle['verificationProfile'], profile), 'PROFILE_IDENTITY')
    rvr.validate_receipt_envelope(bundle, digest, schema)
    failure = rvr.required_dependency_failure(profile, set())
    if failure:
        raise CannotRecompute('NORMATIVE_DEPENDENCY:' + failure['kind'])
    original_case = {k: bundle[k] for k in ('claim', 'evidenceSet', 'payloadsBase64')}
    # A saved verdict must be checked, even when a different candidate is supplied.
    original_result = evaluate_case(original_case, rvr, schema, root)
    need(rvr.json_same(original_result, bundle['canonicalResult']), 'STORED_RESULT_FABRICATED')
    candidate = original_case if candidate is None else candidate
    need(rvr.json_same(candidate['claim'], expected_claim), 'INDEPENDENT_CLAIM_MISMATCH')
    result = original_result if candidate is original_case else evaluate_case(candidate, rvr, schema, root)
    identities = {'claimDigest': rvr.canonical_digest(candidate['claim']),
                  'evidenceSetDigest': rvr.evidence_set_digest(candidate['evidenceSet']),
                  'verificationProfileDigest': digest, 'resultDigest': rvr.canonical_digest(result)}
    same = all(bundle['receipt'][key] == value for key, value in identities.items())
    return {'verificationOutcome': result['outcome'], 'verificationReasonCode': result['reasonCode'],
            'recomputationStatus': 'REPRODUCED' if same else 'DIVERGED',
            'reasonCode': 'rvr.recompute.identical' if same else 'rvr.recompute.canonical_result_diverged',
            'evaluationPerformed': True, 'identities': identities, 'canonicalResult': result}
