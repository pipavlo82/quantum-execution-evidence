"""Saved-artifact replay, including native roots and exact attached bundle bytes."""
import base64
from datetime import datetime
from .live_common import ROOT, Rejected, CannotRecompute, need, fields, parse, encode, sha, json_same
from .live_native import bridge, recompute


def unbase64(value):
    need(type(value) is str and len(value) <= 4_194_304, 'ATTACHMENT_SIZE')
    try:
        return base64.b64decode(value, validate=True)
    except ValueError as exc:
        raise Rejected('ATTACHMENT_BASE64') from exc


def anchor():
    return {'receipt_root': '', 'merkle_proof_status': 'not attached', 'merkle_root': None,
            'merkle_leaf_index': None, 'merkle_proof': [], 'onchain_anchor_status': 'not anchored',
            'network': 'local/off-chain', 'contract': None, 'tx_hash': None, 'verifier_status': 'not verified'}


def envelope(bundle, raw_bundle):
    payloads = bundle['payloadsBase64']
    if 'submission-intent.json' not in payloads:
        raise CannotRecompute('CAPTURE_TIMESTAMP_UNAVAILABLE')
    intent = parse(unbase64(payloads['submission-intent.json']))
    try:
        stamp = datetime.fromisoformat(intent['recorded_at'])
        need(stamp.tzinfo is not None and stamp.year >= 2020, 'CAPTURE_TIMESTAMP')
        seconds = stamp.timestamp()
    except (ValueError, KeyError) as exc:
        raise Rejected('CAPTURE_TIMESTAMP') from exc
    receipt = bundle['receipt']
    return {
        'schema': 'stealth.session.evidence.v1', 'session_id': 'qev-live-' + bundle['claim']['jobId'],
        'directory': 'qev-live-capture-v1',
        'task': {'title': 'Offline replay of preserved LIVE_IBM_RUNTIME_API capture',
                 'prompt': 'RVR outcome ' + receipt['outcome'] + '; providerAuthentication NOT_ESTABLISHED. '
                           'changes.diff_sha256 binds exact inline rvr-live-bundle bytes, including all captured payloads. '
                           'authorization_checked_at carries capture intent recorded_at for envelope compatibility; '
                           'no observed local verification time or authorization proof is claimed.'},
        'agent': {'id': 'qev-live-replay-v1', 'runtime': 'qev-offline-standard-library'},
        'scope': {'permission': None},
        'authorization': {'delegation_ref': None, 'delegator': None, 'agent_operator': None,
                          'target': 'preserved-capture', 'allowed_actions': [],
                          'authorization_valid_from': None, 'authorization_expiry': None,
                          'authorization_checked_at': seconds, 'authorization_state_hash': receipt['claimDigest'],
                          'authorized_at_execution': None},
        'execution': [],
        'commands': [{'command': 'qev live-replay', 'stdout_summary':
                      'RVR ' + receipt['outcome'] + '; ' + receipt['reasonCode'] +
                      '; resultDigest=' + receipt['resultDigest'] + '; providerAuthentication=NOT_ESTABLISHED'}],
        'changes': {'files_changed': ['inline:rvr-live-bundle'], 'diff_sha256': sha(raw_bundle)},
        'anchor': anchor(),
        'metadata': {'message_count': 0, 'diff_count': 1, 'generated_by': 'qev-live-capture-replay-v1'},
    }


def create(bundle, expected_claim, root=ROOT):
    rvr = recompute(bundle, expected_claim, root=root)
    raw = encode(bundle)
    native = bridge('live_receiptos_bridge.ts', {'mode': 'create', 'evidence': envelope(bundle, raw)}, root)
    need(native['verification']['ok'] is True, 'NATIVE_ROOT_CREATE')
    return {'schema': 'qev.live-portable-export.v1',
            'attachment': {'id': 'rvr-live-bundle', 'mediaType': 'application/json',
                           'sha256': sha(raw), 'base64': base64.b64encode(raw).decode('ascii')},
            'rvrReplay': rvr, 'nativeReceiptOs': native}


def replay(saved, expected_claim, root=ROOT):
    fields(saved, ('schema', 'attachment', 'rvrReplay', 'nativeReceiptOs'))
    need(saved['schema'] == 'qev.live-portable-export.v1', 'EXPORT_SCHEMA')
    attachment = saved['attachment']
    fields(attachment, ('id', 'mediaType', 'sha256', 'base64'))
    need(attachment['id'] == 'rvr-live-bundle' and attachment['mediaType'] == 'application/json', 'ATTACHMENT_ROLE')
    raw = unbase64(attachment['base64'])
    need(sha(raw) == attachment['sha256'], 'ATTACHMENT_DIGEST')
    bundle = parse(raw)
    computed = recompute(bundle, expected_claim, root=root)
    need(json_same(computed, saved['rvrReplay']), 'STORED_REPLAY_RESULT')
    native = saved['nativeReceiptOs']
    fields(native, ('evidence', 'verification', 'summary', 'proof'))
    expected = envelope(bundle, raw)
    stored_root = native['evidence'].get('anchor', {}).get('receipt_root')
    need(type(stored_root) is str and stored_root.startswith('0x') and len(stored_root) == 66
         and all(c in '0123456789abcdef' for c in stored_root[2:]), 'RECEIPT_ROOT_FORMAT')
    expected['anchor']['receipt_root'] = stored_root
    need(json_same(native['evidence'], expected), 'ENVELOPE_PROJECTION_OR_ANCHOR')
    need(native['evidence']['changes']['diff_sha256'] == sha(raw), 'ROOT_COVERED_ATTACHMENT')
    fresh = bridge('live_receiptos_bridge.ts', {'mode': 'verify', 'evidence': native['evidence']}, root)
    need(fresh['verification']['ok'] is True, 'RECEIPT_ROOT_MISMATCH')
    need(json_same(fresh, native), 'NATIVE_SUMMARY_OR_PROOF_MISMATCH')
    return {'schema': 'qev.live-replay-result.v1', 'rvr': computed,
            'receiptOs': {'rootStatus': 'VERIFIED', 'root': fresh['verification']['recomputed_root'],
                          'attachmentDigest': sha(raw), 'nativeStatus': 'EXECUTED', 'anchor': 'NOT_CLAIMED'},
            'providerAuthentication': 'NOT_ESTABLISHED'}
