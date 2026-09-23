"""Offline projection/replay CLI; no SDK, credentials or provider network."""
import argparse
import sys
from pathlib import Path

from . import cross_provider as model
from .cross_adapters import fixture, roles_for
from .live_common import read, Rejected, CannotRecompute
from .moth_comet import parse, encode, MothError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('demo', 'replay', 'sources'))
    parser.add_argument('--provider', choices=model.PROVIDERS)
    parser.add_argument('--artifact')
    parser.add_argument('--capture')
    parser.add_argument('--claim')
    args = parser.parse_args()
    if bool(args.capture) != bool(args.claim):
        parser.error('Custom capture and independent --claim must be supplied together')
    if args.command == 'replay' and (not args.artifact or not args.provider):
        parser.error('Replay requires --artifact and --provider')
    if (args.capture or args.claim) and not args.provider:
        parser.error('Custom inputs require --provider')
    try:
        model.check_sources()
        if args.command == 'sources':
            result, code = {'sourceLock': 'MATCH', 'profile': model.PROFILE}, 0
        else:
            reports = {}
            for provider in (args.provider,) if args.provider else model.PROVIDERS:
                if args.capture:
                    claim_path = Path(args.claim).absolute()
                    claim = parse(read(claim_path.parent, claim_path.name))
                    directory = Path(args.capture)
                    names = {p.name for p in directory.iterdir()}
                    if not names <= set(roles_for(provider)) | {'claim.json', 'seed-manifest.json'}:
                        raise Rejected('UNKNOWN_CAPTURE_FILES')
                    payloads = {name: read(directory, name) for name in roles_for(provider) if name in names}
                else:
                    claim, payloads = fixture(provider)
                if args.command == 'replay':
                    path = Path(args.artifact).absolute()
                    saved = parse(read(path.parent, path.name))
                    result = model.replay(saved, provider, claim, payloads)
                    code = model.exit_code({'common': {'consistency': result['consistency']}})
                else:
                    reports[provider] = model.evaluate(provider, claim, payloads)
            if args.command == 'demo':
                result = reports[args.provider] if args.provider else reports
                code = max(model.exit_code(row) for row in reports.values())
    except CannotRecompute as exc:
        result, code = {'status': 'CANNOT_RECOMPUTE', 'reason': str(exc)}, 3
    except (Rejected, MothError, OSError, TypeError, ValueError) as exc:
        result, code = {'status': 'REJECTED', 'reason': str(exc)}, 2
    sys.stdout.buffer.write(encode(result))
    return code


if __name__ == '__main__':
    sys.exit(main())
