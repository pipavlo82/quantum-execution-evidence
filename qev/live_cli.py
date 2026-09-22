"""Offline entry points. Fixture trust anchors are supplied here, not in evaluation."""
from pathlib import Path
from .live_common import ROOT, ROLES, Rejected, CannotRecompute, read, parse, sha, need

FIXTURE = 'fixtures/live-capture-v1'


def fixture(root=ROOT):
    pins = parse(read(root, FIXTURE + '/seed-manifest.json'))
    need(set(pins) == set(ROLES), 'SEED_ROLE_INVENTORY')
    payloads = {name: read(root, FIXTURE + '/' + name) for name in ROLES}
    need(all(sha(payloads[name]) == pins[name] for name in ROLES), 'SEED_BYTES')
    return parse(read(root, FIXTURE + '/claim.json')), payloads


def dispatch(args):
    from .live_native import case_from_payloads, make_bundle
    from .live_portable import create, replay
    try:
        if args.command == 'live-demo':
            claim, payloads = fixture()
            saved = create(make_bundle(case_from_payloads(claim, payloads)), claim)
            outcome = saved['rvrReplay']['verificationOutcome']
            return saved, {'VERIFIED': 0, 'REFUTED': 1, 'UNVERIFIABLE': 3}[outcome]
        if args.command == 'live-mutation-check':
            from .live_mutations import run
            out = run()
            return out, 0 if out['status'] == 'PASS' else 1
        path = Path(args.artifact).absolute()
        claim_path = Path(args.claim).absolute() if args.claim else ROOT / FIXTURE / 'claim.json'
        claim = parse(read(claim_path.parent, claim_path.name))
        saved = parse(read(path.parent, path.name))
        out = replay(saved, claim)
        return out, {'VERIFIED': 0, 'REFUTED': 1, 'UNVERIFIABLE': 3}[out['rvr']['verificationOutcome']]
    except CannotRecompute as exc:
        return {'status': 'CANNOT_RECOMPUTE', 'reason': str(exc)}, 3
    except (Rejected, OSError, KeyError, TypeError, ValueError) as exc:
        return {'status': 'REJECTED', 'reason': str(exc)}, 2
    except Exception as exc:
        if getattr(exc, 'reason_code', None):
            return {'status': 'REJECTED', 'reason': exc.reason_code}, 2
        raise
