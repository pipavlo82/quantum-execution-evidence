"""Pin new files separately; do not repin or rewrite any legacy profile."""
from qev.cross_provider import FILES, PROFILE
from qev.live_common import ROOT, sha
from qev.moth_comet import encode


def main():
    result = {'schema': 'qev.cross-provider-sources.v0',
              'files': {name: sha((ROOT / name).read_bytes()) for name in FILES}}
    (ROOT / PROFILE / 'sources.json').write_bytes(encode(result))
    print(sha(encode(result)))


if __name__ == '__main__':
    main()
