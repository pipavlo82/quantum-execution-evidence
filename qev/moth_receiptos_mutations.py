"""Nine applied packaging source mutants; crashes never count as kills."""
import copy
import types
from . import moth_receiptos as portable, moth_rvr
from .moth_comet import encode, parse
from .live_common import Rejected

MUTANTS = (
    ('attachment-digest', "sha(raw) == attachment['sha256']", 'True', 'ATTACHMENT_DIGEST'),
    ('root-covered-envelope', "json_same(native['evidence'], expected)", 'True', 'ENVELOPE_PROJECTION_OR_ANCHOR'),
    ('native-root', "fresh['verification']['ok'] is True", 'True', 'RECEIPT_ROOT_MISMATCH'),
    ('saved-rvr-result', "json_same(computed, saved['rvrReplay'])", 'True', 'STORED_RVR_REPLAY'),
    ('native-verification', "json_same(fresh['verification'], native['verification'])", 'True', 'NATIVE_VERIFICATION_PROJECTION'),
    ('native-summary', "json_same(fresh['summary'], native['summary'])", 'True', 'NATIVE_SUMMARY_PROJECTION'),
    ('native-proof', "json_same(fresh['proof'], native['proof'])", 'True', 'NATIVE_PROOF_PROJECTION'),
    ('packaging-profile', "json_same(saved['profile'], profile)", 'True', 'PACKAGING_PROFILE_IDENTITY'),
    ('independent-claim', 'computed = moth_rvr.recompute(bundle, expected_claim, root=root)',
                          "computed = moth_rvr.recompute(bundle, bundle['claim'], root=root)", 'INDEPENDENT_CLAIM_MISMATCH'),
)
CONTROLS = ('verified', 'refuted', 'unverifiable')


def inventory():
    return {'schema': 'qev.moth-receiptos-falsification.v0', 'controls': list(CONTROLS),
            'mutants': [{'id': name, 'source': 'qev/moth_receiptos.py', 'before': before, 'after': after,
                        'expectedRejection': reason} for name, before, after, reason in MUTANTS]}


def cases():
    from .moth_rvr_mutations import negative
    claim, payloads = moth_rvr.fixture()
    refuted_claim, refuted_payloads = negative('counts-refutation')
    inputs = ((claim, payloads), (refuted_claim, refuted_payloads), (claim, {}))
    return {name: (portable.create(encode(moth_rvr.make_bundle(moth_rvr.case_from_payloads(c, p))), c), c)
            for name, (c, p) in zip(CONTROLS, inputs)}


def negative(name, saved, claim):
    saved, claim = copy.deepcopy(saved), copy.deepcopy(claim)
    native = saved['nativeReceiptOs']
    if name == 'attachment-digest':
        saved['attachment']['sha256'] = '0' * 64
    elif name == 'root-covered-envelope':
        # Bundle is semantically identical; the exact raw attachment changed.
        import base64
        raw = portable.unbase64(saved['attachment']['base64']) + b' '
        saved['attachment'].update(base64=base64.b64encode(raw).decode('ascii'), sha256=portable.sha(raw))
    elif name == 'native-root':
        native['evidence']['anchor']['receipt_root'] = '0x' + '0' * 64
        saved['nativeReceiptOs'] = portable.bridge('verify', native['evidence'])
    elif name == 'saved-rvr-result':
        saved['rvrReplay']['verificationOutcome'] = 'REFUTED'
    elif name == 'native-verification':
        native['verification']['ok'] = False
    elif name == 'native-summary':
        native['summary']['source_evidence'] = 'inline:unrelated'
    elif name == 'native-proof':
        native['proof']['provenance_summary']['what_happened'] = 'fabricated'
    elif name == 'packaging-profile':
        saved['profile']['profileId'] = 'unrelated-profile'
    elif name == 'independent-claim':
        claim['captureClaim']['jobId'] = 'independent-claim-substitution'
    else:
        raise ValueError(name)
    return saved, claim


def run():
    portable.check_sources()
    raw = (portable.ROOT / 'qev/moth_receiptos.py').read_text(encoding='utf-8')
    controls = cases()
    expected = {key: portable.replay(*args) for key, args in controls.items()}
    rows = []
    for name, before, after, reason in MUTANTS:
        row = {'id': name, 'status': 'UNAPPLIED', 'controls': []}
        rows.append(row)
        if raw.count(before) != 1:
            continue
        module = types.ModuleType('qev.moth_receiptos_mutant')
        module.__package__ = 'qev'
        try:
            exec(compile(raw.replace(before, after), '<moth-receiptos-mutant>', 'exec'), module.__dict__)
            row['controls'] = [{'id': key, 'preserved': module.replay(*args) == expected[key]
                                and expected[key]['receiptOs']['rootStatus'] == 'VERIFIED'
                                and expected[key]['rvr']['verificationOutcome'] == key.upper()}
                               for key, args in controls.items()]
            args = negative(name, *controls['verified'])
            try:
                portable.replay(*args)
            except Rejected as exc:
                row['baselineReason'] = str(exc)
            else:
                row['baselineReason'] = 'NOT_REJECTED'
            changed = module.replay(*args)
            row['mutantOutcome'] = changed['rvr']['verificationOutcome']
            row['status'] = ('CONTROL_BROKEN' if not all(r['preserved'] for r in row['controls'])
                             else 'INVALID_BASELINE' if row['baselineReason'] != reason
                             else 'KILLED' if changed['receiptOs']['rootStatus'] == 'VERIFIED'
                             and changed['rvr']['verificationOutcome'] == 'VERIFIED' else 'SURVIVED')
        except Exception as exc:
            row.update(status='CRASHED', errorType=type(exc).__name__)
    return {'schema': 'qev.moth-receiptos-mutations.v0', 'mutations': rows,
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
