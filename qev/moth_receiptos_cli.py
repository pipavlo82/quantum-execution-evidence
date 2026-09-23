"""Offline Moth ReceiptOS export/replay with a separately supplied RVR claim."""
import argparse
from pathlib import Path
import sys
from . import moth_receiptos as portable, moth_rvr
from .moth_comet import encode
from .live_common import CannotRecompute, need, parse


def load(path, limit=4_194_304):
    path = Path(path)
    need(path.stat().st_size <= limit, 'INPUT_SIZE')
    raw = path.read_bytes()
    need(len(raw) <= limit, 'INPUT_SIZE')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo')
    demo.add_argument('--output')
    export = sub.add_parser('export')
    export.add_argument('--bundle', required=True)
    export.add_argument('--claim', required=True)
    export.add_argument('--output')
    replay = sub.add_parser('replay')
    replay.add_argument('--artifact', required=True)
    replay.add_argument('--claim', required=True)
    sub.add_parser('sources')
    args = parser.parse_args()
    try:
        if args.command == 'sources':
            portable.check_sources()
            report = {'status': 'MATCH', 'profileId': portable.PROFILE_ID, 'localFiles': len(portable.FILES)}
        elif args.command == 'demo':
            claim, payloads = moth_rvr.fixture()
            bundle = moth_rvr.make_bundle(moth_rvr.case_from_payloads(claim, payloads))
            report = portable.create(encode(bundle), claim)
        elif args.command == 'export':
            report = portable.create(load(args.bundle, portable.MAX_BUNDLE_BYTES), parse(load(args.claim)))
        else:
            report = portable.replay(parse(load(args.artifact)), parse(load(args.claim)))
        outcome = report.get('rvr', report.get('rvrReplay', {})).get('verificationOutcome', 'VERIFIED')
        code = {'VERIFIED': 0, 'REFUTED': 1, 'UNVERIFIABLE': 3}[outcome]
        if getattr(args, 'output', None):
            Path(args.output).write_bytes(encode(report))
            return code
    except CannotRecompute as exc:
        report, code = {'recomputationStatus': 'CANNOT_RECOMPUTE', 'evaluationPerformed': False, 'reason': str(exc)}, 3
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report, code = {'admission': 'REJECTED', 'evaluationPerformed': False, 'reason': str(exc)}, 2
    except Exception as exc:
        if exc.__class__.__module__ != 'moth_counts_pinned_rvr':
            raise
        report, code = {'admission': 'REJECTED', 'evaluationPerformed': False,
                        'reason': getattr(exc, 'reason_code', str(exc))}, 2
    sys.stdout.buffer.write(encode(report))
    return code


if __name__ == '__main__':
    sys.exit(main())
