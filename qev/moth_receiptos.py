"""Native ReceiptOS packaging of unchanged Moth counts RVR artifacts."""
import base64
import subprocess
from pathlib import Path

from . import moth_rvr
from .live_common import ROOT, CannotRecompute, Rejected, fields, need, read, json_same, parse
from .moth_comet import MothError, encode, parse as parse_bundle, sha
from .source_inventory import ALL_VENDOR_FILES

PROFILE = 'profiles/moth-receiptos-v0'
PROFILE_ID = 'receiptos-qev-moth-counts-v0'
SCHEMA = 'qev.moth-portable-export.v0'
ATTACHMENT = 'rvr-moth-counts-bundle'
REFERENCE = 'inline:' + ATTACHMENT
MAX_BUNDLE_BYTES = 2_000_000
FILES = ('qev/moth_receiptos.py', 'qev/moth_receiptos_cli.py',
         'qev/moth_receiptos_bridge.ts', 'qev/moth_receiptos_mutations.py',
         'tests/test_moth_receiptos.py', 'docs/MOTH_RECEIPTOS_V0.md',
         'tools/pin_moth_receiptos_profile.py', PROFILE + '/profile.json',
         PROFILE + '/conformance.json')
VENDOR = tuple({'path': r['path'], 'sha256': r['sha256']} for r in ALL_VENDOR_FILES
               if r['path'].startswith('vendor/receiptos-v0/'))
RVR_PINS = (moth_rvr.PROFILE + '/verification-profile.json', moth_rvr.PROFILE + '/sources.json')


def check_sources(root=ROOT):
    moth_rvr.check_sources(root)
    try:
        lock = parse(read(root, PROFILE + '/sources.json'))
        fields(lock, FILES)
        for path in FILES:
            if sha(read(root, path)) != lock[path]:
                raise CannotRecompute('PACKAGING_SOURCE_IDENTITY:' + path)
        profile = parse(read(root, PROFILE + '/profile.json'))
        fields(profile, ('schema', 'profileId', 'artifactSchema', 'rvrProfileId', 'dependencies', 'vendorFiles', 'rvrPins'))
        need(profile['schema'] == 'qev.moth-receiptos-profile.v0' and profile['profileId'] == PROFILE_ID
             and profile['artifactSchema'] == SCHEMA and profile['rvrProfileId'] == moth_rvr.PROFILE_ID,
             'PACKAGING_PROFILE_CONTRACT')
        expected = set(FILES) - {PROFILE + '/profile.json'}
        paths = [r['path'] for r in profile['dependencies']]
        need(len(paths) == len(set(paths)) and set(paths) == expected, 'PACKAGING_DEPENDENCY_INVENTORY')
        need([r['path'] for r in profile['rvrPins']] == list(RVR_PINS), 'RVR_PIN_INVENTORY')
        need(json_same(profile['vendorFiles'], list(VENDOR)), 'RECEIPTOS_VENDOR_INVENTORY')
        for row in [*profile['dependencies'], *profile['vendorFiles'], *profile['rvrPins']]:
            fields(row, ('path', 'sha256'))
            if sha(read(root, row['path'])) != row['sha256']:
                raise CannotRecompute('PACKAGING_DEPENDENCY_IDENTITY:' + row['path'])
    except (OSError, Rejected, MothError, KeyError, TypeError) as exc:
        raise CannotRecompute('PACKAGING_SOURCE_UNAVAILABLE_OR_INVALID:' + str(exc)) from exc
    return profile


def bridge(mode, evidence, root=ROOT):
    check_sources(root)
    need(mode in ('create', 'verify'), 'BRIDGE_MODE')
    try:
        result = subprocess.run(['bun', str(Path(root) / 'qev/moth_receiptos_bridge.ts')],
                                input=encode({'mode': mode, 'evidence': evidence}), cwd=root,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CannotRecompute('RECEIPTOS_RUNTIME_UNAVAILABLE') from exc
    if result.returncode:
        raise CannotRecompute('RECEIPTOS_BRIDGE_FAILED')
    return parse(result.stdout)


def unbase64(value):
    need(type(value) is str and len(value) <= 4 * ((MAX_BUNDLE_BYTES + 2) // 3), 'ATTACHMENT_SIZE')
    try:
        raw = base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise Rejected('ATTACHMENT_BASE64') from exc
    need(len(raw) <= MAX_BUNDLE_BYTES and base64.b64encode(raw).decode('ascii') == value,
         'ATTACHMENT_CANONICAL_BASE64')
    return raw


def anchor():
    return {'receipt_root': '', 'merkle_proof_status': 'not attached', 'merkle_root': None,
            'merkle_leaf_index': None, 'merkle_proof': [], 'onchain_anchor_status': 'not anchored',
            'network': 'local/off-chain', 'contract': None, 'tx_hash': None, 'verifier_status': 'not verified'}


def envelope(bundle, raw, profile_digest):
    receipt = bundle['receipt']
    observation = bundle['canonicalResult']['observation']
    delivery = ('NOT_ESTABLISHED_FOR_THIS_OUTCOME' if observation is None else
                observation['deliveredBytes'] + ' bytes; upstream grade ' + observation['reportedGrade'])
    return {
        'schema': 'stealth.session.evidence.v1',
        'session_id': 'qev-moth-' + bundle['claim']['captureClaim']['jobId'], 'directory': PROFILE_ID,
        'task': {'title': 'Offline Moth counts RVR portable evidence',
                 'prompt': 'Packaging profile sha256=' + profile_digest + '; RVR ' + receipt['outcome'] +
                           '; delivery ' + delivery + '; providerAuthentication NOT_ESTABLISHED. '
                           'changes.diff_sha256 binds exact inline RVR bundle bytes and captured payloads. '
                           'authorization_checked_at=0 and proof.created_at epoch are compatibility sentinels; '
                           'no creation time, authorization or provider attestation is claimed.'},
        'agent': {'id': PROFILE_ID, 'runtime': 'qev-offline-moth-receiptos-v0'},
        'scope': {'permission': None},
        'authorization': {'delegation_ref': None, 'delegator': None, 'agent_operator': None,
                          'target': 'preserved-moth-counts', 'allowed_actions': [],
                          'authorization_valid_from': None, 'authorization_expiry': None,
                          'authorization_checked_at': 0, 'authorization_state_hash': receipt['claimDigest'],
                          'authorized_at_execution': None},
        'execution': [],
        'commands': [{'command': 'python -B -m qev.moth_receiptos_cli replay', 'stdout_summary':
                      'RVR ' + receipt['outcome'] + '; ' + receipt['reasonCode'] +
                      '; resultDigest=' + receipt['resultDigest'] + '; delivery ' + delivery}],
        'changes': {'files_changed': [REFERENCE], 'diff_sha256': sha(raw)},
        'anchor': anchor(),
        'metadata': {'message_count': 0, 'diff_count': 1, 'generated_by': PROFILE_ID},
    }


def create(raw_bundle, expected_claim, root=ROOT):
    """Preserve caller-supplied bundle bytes exactly, after native RVR replay."""
    profile = check_sources(root)
    need(type(raw_bundle) is bytes and len(raw_bundle) <= MAX_BUNDLE_BYTES, 'BUNDLE_SIZE')
    bundle = parse_bundle(raw_bundle)
    result = moth_rvr.recompute(bundle, expected_claim, root=root)
    native = bridge('create', envelope(bundle, raw_bundle, sha(encode(profile))), root)
    need(native['verification']['ok'] is True, 'NATIVE_ROOT_CREATE')
    saved = {'schema': SCHEMA, 'profile': profile,
             'attachment': {'id': ATTACHMENT, 'mediaType': 'application/json',
                            'sha256': sha(raw_bundle), 'base64': base64.b64encode(raw_bundle).decode('ascii')},
             'rvrReplay': result, 'nativeReceiptOs': native}
    # Apply the same outer bounded JSON boundary as the replay entry point.
    parse(encode(saved))
    return saved


def replay(saved, expected_claim, root=ROOT):
    profile = check_sources(root)
    saved = parse(encode(saved))
    fields(saved, ('schema', 'profile', 'attachment', 'rvrReplay', 'nativeReceiptOs'))
    need(saved['schema'] == SCHEMA, 'EXPORT_SCHEMA')
    need(json_same(saved['profile'], profile), 'PACKAGING_PROFILE_IDENTITY')
    attachment = saved['attachment']
    fields(attachment, ('id', 'mediaType', 'sha256', 'base64'))
    need(attachment['id'] == ATTACHMENT and attachment['mediaType'] == 'application/json', 'ATTACHMENT_ROLE')
    raw = unbase64(attachment['base64'])
    need(sha(raw) == attachment['sha256'], 'ATTACHMENT_DIGEST')
    bundle = parse_bundle(raw)
    computed = moth_rvr.recompute(bundle, expected_claim, root=root)
    need(json_same(computed, saved['rvrReplay']), 'STORED_RVR_REPLAY')
    native = saved['nativeReceiptOs']
    fields(native, ('evidence', 'verification', 'summary', 'proof'))
    expected = envelope(bundle, raw, sha(encode(profile)))
    fields(native['evidence'], expected)
    fields(native['evidence']['anchor'], anchor())
    stored_root = native['evidence'].get('anchor', {}).get('receipt_root')
    need(type(stored_root) is str and stored_root.startswith('0x') and len(stored_root) == 66
         and all(c in '0123456789abcdef' for c in stored_root[2:]), 'RECEIPT_ROOT_FORMAT')
    # Native ReceiptOS omits the whole anchor from its root; constrain it here.
    expected['anchor']['receipt_root'] = stored_root
    need(json_same(native['evidence'], expected), 'ENVELOPE_PROJECTION_OR_ANCHOR')
    fresh = bridge('verify', native['evidence'], root)
    need(fresh['verification']['ok'] is True, 'RECEIPT_ROOT_MISMATCH')
    need(json_same(fresh['verification'], native['verification']), 'NATIVE_VERIFICATION_PROJECTION')
    need(json_same(fresh['summary'], native['summary']), 'NATIVE_SUMMARY_PROJECTION')
    need(json_same(fresh['proof'], native['proof']), 'NATIVE_PROOF_PROJECTION')
    return {'schema': 'qev.moth-portable-replay.v0', 'profileId': PROFILE_ID,
            'rvr': computed, 'receiptOs': {'rootStatus': 'VERIFIED',
                'root': fresh['verification']['recomputed_root'], 'attachmentDigest': sha(raw),
                'nativeStatus': 'EXECUTED', 'anchor': 'NOT_CLAIMED'},
            'observation': computed['canonicalResult']['observation'],
            'providerAuthentication': 'NOT_ESTABLISHED'}
