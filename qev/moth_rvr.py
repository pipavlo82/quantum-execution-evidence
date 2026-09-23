"""Native RVR receipts for the finite preserved Moth counts capture."""
import base64
import types
from pathlib import Path
from .live_common import ROOT, Rejected, CannotRecompute, need, fields, sha, read, encode
from .moth_comet import parse, MothError
from .source_inventory import ALL_VENDOR_FILES

PROFILE = 'profiles/rvr-qev-moth-counts-v0'
PROFILE_ID = 'rvr-qev-moth-counts-v0'
RUNTIME = ('qev/moth_rvr.py', 'qev/moth_rvr_relation.py', 'qev/moth_rvr_cli.py',
           'qev/moth_comet.py', 'qev/moth_replay.py', 'qev/live_common.py',
           'qev/sources.py', 'qev/source_inventory.py', 'qev/admission.py', 'qev/inventory.py',
           'qev/adapters.py', 'qev/__init__.py', PROFILE + '/roles.json')
FILES = ('qev/moth_rvr.py', 'qev/moth_rvr_relation.py', 'qev/moth_rvr_cli.py',
         'qev/moth_rvr_mutations.py', 'tests/test_moth_rvr.py',
         'tools/pin_moth_rvr_profile.py', 'docs/MOTH_COUNTS_RVR_V0.md',
         PROFILE + '/profile.schema.json', PROFILE + '/rvr-moth.schema.json',
         PROFILE + '/verification-profile.json', PROFILE + '/roles.json',
         PROFILE + '/conformance.json', PROFILE + '/claim.json')


def dependencies(profile):
    return [profile['profileSchemaContract']['manifest'], profile['profileSchemaContract']['constraints'],
            profile['verificationSpecification'], *profile['schemaContracts'],
            *profile['conformanceVectorSet']['members']]


def check_sources(root=ROOT):
    try:
        lock = parse(read(root, PROFILE + '/sources.json'))
        need(type(lock) is dict and set(lock) == set(FILES), 'SOURCE_INVENTORY')
        for path in FILES:
            if sha(read(root, path)) != lock[path]:
                raise CannotRecompute('SOURCE_IDENTITY_MISMATCH:' + path)
        profile = parse(read(root, PROFILE + '/verification-profile.json'))
        required = {PROFILE + '/profile.schema.json', PROFILE + '/rvr-moth.schema.json',
                    'docs/MOTH_COUNTS_RVR_V0.md', *RUNTIME,
                    *(r['path'] for r in ALL_VENDOR_FILES if r['path'].startswith('vendor/rvr-v0/'))}
        entries = dependencies(profile)
        actual = [r['path'] for r in entries if r['requiredForRecomputation']]
        need(len(actual) == len(set(actual)) and set(actual) == required, 'DEPENDENCY_INVENTORY')
        for row in entries:
            if sha(read(root, row['path'])) != row['sha256']:
                raise CannotRecompute('DEPENDENCY_IDENTITY_MISMATCH:' + row['path'])
        for row in ALL_VENDOR_FILES:
            if row['path'].startswith('vendor/rvr-v0/') and sha(read(root, row['path'])) != row['sha256']:
                raise CannotRecompute('VENDOR_IDENTITY_MISMATCH:' + row['path'])
    except (OSError, Rejected, MothError, KeyError, TypeError) as exc:
        raise CannotRecompute('SOURCE_UNAVAILABLE_OR_INVALID:' + str(exc)) from exc
    return profile


def context(root=ROOT):
    root = Path(root)
    profile = check_sources(root)
    raw = read(root, 'vendor/rvr-v0/adapter.py')
    expected = next(r['sha256'] for r in ALL_VENDOR_FILES if r['path'] == 'vendor/rvr-v0/adapter.py')
    if sha(raw) != expected:
        raise CannotRecompute('VENDOR_IDENTITY_MISMATCH')
    module = types.ModuleType('moth_counts_pinned_rvr')
    module.__file__ = str(root / 'vendor/rvr-v0/adapter.py')
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    module.PROFILE_PACKAGE_ROOT = root
    manifest = read(root, 'vendor/rvr-v0/verification-profile-manifest.schema.json')
    digest, _, pinned = module.audit_profile(profile, parse(manifest), manifest)
    return module, profile, digest, parse(pinned['rvr-schema'])


def validate_claim(claim):
    fields(claim, ('schema', 'profile', 'relation', 'captureClaim', 'providerAuthentication'))
    need(claim['schema'] == 'rvr.claim.qev-moth-counts.v0' and claim['profile'] == PROFILE_ID and
         claim['relation'] == 'preserved-counts-and-report-consistency' and
         claim['providerAuthentication'] == 'NOT_ESTABLISHED', 'CLAIM_CONTRACT')
    old = claim['captureClaim']
    fields(old, ('schema', 'profile', 'jobId', 'manifestSha256', 'requestSha256', 'origin', 'authority'))
    need(old['schema'] == 'qev.moth-comet-claim.v0' and old['profile'] == 'qev-moth-comet-counts-v0'
         and old['origin'] == 'LIVE_MOTH_API_CAPTURE' and old['authority'] == 'LOCAL_UNSIGNED_CAPTURE_COMMITMENT',
         'CAPTURE_CLAIM_CONTRACT')
    from .moth_comet import digest
    for key in ('manifestSha256', 'requestSha256'):
        digest(old[key], 'CLAIM_DIGEST')
    need(type(old['jobId']) is str and 0 < len(old['jobId']) <= 200, 'CLAIM_JOB')


def contract(root=ROOT):
    return parse(read(root, PROFILE + '/roles.json'))


def fixture(root=ROOT):
    check_sources(root)
    return (parse(read(root, PROFILE + '/claim.json')),
            {name: read(root, 'fixtures/moth-comet-v0/capture/' + name)
             for name in contract(root)['members']})


def case_from_payloads(claim, payloads, root=ROOT):
    validate_claim(claim)
    roles = contract(root)['members']
    need(type(payloads) is dict and set(payloads) <= set(roles), 'ROLE_INVENTORY')
    need(all(type(v) is bytes for v in payloads.values()), 'PAYLOAD_TYPE')
    members = []
    for role in roles:
        if role in payloads:
            raw = payloads[role]
            members.append({'id': role, 'status': 'PRESENT', 'mediaType': 'application/json',
                            'byteLength': str(len(raw)), 'digest': sha(raw)})
        else:
            members.append({'id': role, 'status': 'UNAVAILABLE', 'reasonCode': 'qev.moth.rvr.v0.evidence_unavailable'})
    return {'claim': claim, 'evidenceSet': {'schema': 'rvr.evidence-set.v0', 'members': members},
            'payloadsBase64': {k: base64.b64encode(v).decode('ascii') for k, v in payloads.items()}}


def evaluate_case(case, rvr, schema, root):
    from .moth_rvr_relation import evaluate
    fields(case, ('claim', 'evidenceSet', 'payloadsBase64'))
    # The same bounded JSON/Unicode boundary applies to Python and CLI callers.
    case = parse(encode(case))
    validate_claim(case['claim'])
    rvr.require_schema(case['claim'], schema, '#/$defs/claim', 'Moth counts claim')
    rvr.require_schema(case['evidenceSet'], schema, '#/$defs/evidenceSet', 'Moth evidence set')
    roles = contract(root)
    ids = [m['id'] for m in case['evidenceSet']['members']]
    need(len(ids) == len(roles['members']) and set(ids) == set(roles['members']), 'ROLE_INVENTORY')
    unresolved = rvr.unresolved_present_member(case['evidenceSet'], case['payloadsBase64'])
    if unresolved:
        raise CannotRecompute('COMMITTED_PRESENT_UNAVAILABLE:' + unresolved)
    payloads = rvr.validate_evidence_closure(case['evidenceSet'], case['payloadsBase64'])
    need(sum(len(raw) for raw in payloads.values()) <= 2_000_000, 'CAPTURE_TOTAL_SIZE')
    result = evaluate(case['claim'], payloads, roles)
    rvr.require_schema(result, schema, '#/$defs/canonicalResult', 'Moth counts result')
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
    bundle = parse(encode(bundle))
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
