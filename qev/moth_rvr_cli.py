"""Offline native Moth counts RVR export and independent-claim replay."""
import argparse
import sys
from pathlib import Path
from . import moth_rvr as native
from .moth_comet import parse, encode
from .live_common import CannotRecompute


def load(path):
    path = Path(path)
    native.need(path.stat().st_size <= 4_194_304, 'INPUT_SIZE')
    return parse(path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    demo = sub.add_parser('demo')
    demo.add_argument('--output', help='Write exact UTF-8 bytes to this file')
    replay = sub.add_parser('replay')
    replay.add_argument('--artifact', required=True)
    replay.add_argument('--claim', required=True, help='Separately trusted Moth RVR claim')
    replay.add_argument('--candidate', help='Optional separate case to compare with saved receipt')
    sub.add_parser('sources')
    args = parser.parse_args()
    try:
        if args.command == 'sources':
            native.check_sources()
            report = {'status': 'MATCH', 'profileId': native.PROFILE_ID, 'localFiles': len(native.FILES)}
        elif args.command == 'demo':
            claim, payloads = native.fixture()
            report = native.make_bundle(native.case_from_payloads(claim, payloads))
            if args.output:
                Path(args.output).write_bytes(encode(report))
                return 0
        else:
            report = native.recompute(load(args.artifact), load(args.claim),
                                      load(args.candidate) if args.candidate else None)
        status = report.get('verificationOutcome', report.get('canonicalResult', {}).get('outcome', 'VERIFIED'))
        code = {'VERIFIED': 0, 'REFUTED': 1, 'UNVERIFIABLE': 3}[status]
    except CannotRecompute as exc:
        report = {'recomputationStatus': 'CANNOT_RECOMPUTE', 'evaluationPerformed': False, 'reason': str(exc)}
        code = 3
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report = {'admission': 'REJECTED', 'evaluationPerformed': False, 'reason': str(exc)}
        code = 2
    except Exception as exc:
        # Audited native RVR exceptions have their own class hierarchy.
        if exc.__class__.__module__ != 'moth_counts_pinned_rvr':
            raise
        report = {'admission': 'REJECTED', 'evaluationPerformed': False,
                  'reason': getattr(exc, 'reason_code', str(exc))}
        code = 2
    sys.stdout.buffer.write(encode(report))
    return code


if __name__ == '__main__':
    sys.exit(main())
