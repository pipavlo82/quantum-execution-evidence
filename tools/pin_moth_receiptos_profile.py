"""Pin only the additive ReceiptOS packaging profile; never repin Moth RVR."""
from qev.moth_receiptos import ROOT, PROFILE, PROFILE_ID, SCHEMA, FILES, RVR_PINS, VENDOR
from qev.moth_receiptos_mutations import inventory
from qev.moth_comet import encode, sha
from qev.moth_rvr import PROFILE_ID as RVR_ID


def build():
    directory = ROOT / PROFILE
    directory.mkdir(exist_ok=True)
    (directory / 'conformance.json').write_bytes(encode(inventory()))
    def pin(path):
        return {'path': path, 'sha256': sha((ROOT / path).read_bytes())}
    profile = {'schema': 'qev.moth-receiptos-profile.v0', 'profileId': PROFILE_ID,
               'artifactSchema': SCHEMA, 'rvrProfileId': RVR_ID,
               'dependencies': [pin(path) for path in FILES if path != PROFILE + '/profile.json'],
               'vendorFiles': list(VENDOR), 'rvrPins': [pin(path) for path in RVR_PINS]}
    (directory / 'profile.json').write_bytes(encode(profile))
    (directory / 'sources.json').write_bytes(encode({path: sha((ROOT / path).read_bytes()) for path in FILES}))
    print(PROFILE_ID)


if __name__ == '__main__':
    build()
