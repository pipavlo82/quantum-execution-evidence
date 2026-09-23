"""Build the additive counts-native RVR profile and its finite source closure."""
import copy
import json
from qev.moth_rvr import ROOT, PROFILE, PROFILE_ID, RUNTIME, FILES
from qev.moth_rvr_relation import LIMITS
from qev.moth_rvr_mutations import inventory
from qev.moth_comet import encode, sha
from qev.source_inventory import ALL_VENDOR_FILES


def closed(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def build():
    directory = ROOT / PROFILE
    directory.mkdir(exist_ok=True)
    def save(name, obj):
        (directory / name).write_bytes(encode(obj))
    capture = json.loads((ROOT / 'fixtures/moth-comet-v0/capture/manifest.json').read_bytes())
    roles = {'members': sorted([*capture['files'], 'manifest.json']), 'roles': capture['roles']}
    save('roles.json', roles)
    claim = {'schema': 'rvr.claim.qev-moth-counts.v0', 'profile': PROFILE_ID,
             'relation': 'preserved-counts-and-report-consistency',
             'providerAuthentication': 'NOT_ESTABLISHED',
             'captureClaim': json.loads((ROOT / 'fixtures/moth-comet-v0/claim.json').read_bytes())}
    save('claim.json', claim)
    schema = json.loads((ROOT / 'profiles/qev-preserved-observation-v0/rvr-qev.schema.json').read_bytes())
    schema['$id'], schema['title'] = 'urn:qev:rvr-moth-counts-v0', 'Native RVR Moth counts v0'
    defs = schema['$defs']
    defs['identifier'] = {'enum': roles['members']}
    defs['presentEvidenceMember']['properties']['mediaType'] = {'const': 'application/json'}
    defs['verificationReasonCode'] = {'enum': ['qev.moth.rvr.v0.' + x for x in ('verified', 'refuted', 'unverifiable')]}
    defs['unavailableEvidenceMember']['properties']['reasonCode'] = {'const': 'qev.moth.rvr.v0.evidence_unavailable'}
    old = {key: {'const': value} for key, value in claim['captureClaim'].items()}
    old['jobId'] = {'type': 'string', 'minLength': 1, 'maxLength': 200}
    for key in ('manifestSha256', 'requestSha256'):
        old[key] = {'$ref': '#/$defs/digest'}
    defs['claim'] = closed({**{key: {'const': value} for key, value in claim.items() if key != 'captureClaim'},
                            'captureClaim': closed(old)})
    string = {'type': 'string'}
    observation = closed({
        **{key: {'$ref': '#/$defs/decimalLength'} for key in ('shots', 'uniqueBitstrings', 'width', 'requestedBytes', 'deliveredBytes')},
        **{key: string for key in ('witnessS', 'witnessSigmaAlgebra', 'delivery', 'reportedGrade')},
        'representation': {'const': 'COUNTS_ONLY'}, 'countsSha256': {'$ref': '#/$defs/digest'},
        'gradeAuthority': {'const': 'UPSTREAM_REPORTED_ARITHMETIC_CHECKED_NOT_ENTROPY_CERTIFIED'},
    })
    defs['canonicalResult'] = closed({
        'schema': {'const': 'rvr.qev.moth-counts-result.v0'},
        'outcome': {'$ref': '#/$defs/outcome'}, 'reasonCode': {'$ref': '#/$defs/verificationReasonCode'},
        'issues': closed({key: {'type': 'array', 'items': string, 'uniqueItems': True}
                          for key in ('missing', 'contradiction')}),
        'countsVerification': closed({'state': {'enum': ['NOT_EVALUATED', 'CONSISTENT', 'REFUTED', 'UNVERIFIABLE']}, 'reason': string}),
        'observation': {'oneOf': [{'type': 'null'}, observation]},
        'limits': closed({key: {'const': value} for key, value in LIMITS.items()}),
    })
    for key in ('evaluation', 'inputStatus'):
        defs.pop(key, None)
    save('rvr-moth.schema.json', schema)
    save('profile.schema.json', {'type': 'object', 'required': ['profileId'],
                                'properties': {'profileId': {'const': PROFILE_ID}}})
    save('conformance.json', inventory())
    def dep(identifier, path, required=True):
        return {'id': identifier, 'path': path, 'requiredForRecomputation': required,
                'sha256': sha((ROOT / path).read_bytes())}
    profile = copy.deepcopy(json.loads((ROOT / 'profiles/qev-preserved-observation-v0/verification-profile.json').read_bytes()))
    profile['profileId'] = PROFILE_ID
    profile['profileSchemaContract']['constraints'] = dep('moth-profile-schema', PROFILE + '/profile.schema.json')
    profile['verificationSpecification'] = dep('moth-specification', 'docs/MOTH_COUNTS_RVR_V0.md')
    schema_pin = dep('rvr-schema', PROFILE + '/rvr-moth.schema.json')
    profile['schemaContracts'] = [schema_pin, *[dep('runtime-' + str(i), p) for i, p in enumerate(RUNTIME)]]
    profile['schemaContracts'] += [dep('vendor-' + str(i), row['path']) for i, row in enumerate(ALL_VENDOR_FILES)
                                   if row['path'] in ('vendor/rvr-v0/adapter.py', 'vendor/rvr-v0/LICENSE')]
    for key in ('evidenceSetContract', 'canonicalResultContract'):
        profile[key]['schemaPath'], profile[key]['schemaSha256'] = schema_pin['path'], schema_pin['sha256']
    members = [dep('conformance-' + str(i), path, False) for i, path in enumerate(
        (PROFILE + '/conformance.json', 'qev/moth_rvr_mutations.py', 'tests/test_moth_rvr.py'))]
    rows = ''.join(r['path'] + '\t' + r['sha256'] + '\n' for r in sorted(members, key=lambda r: r['path']))
    profile['conformanceVectorSet'] = {'id': 'qev-moth-rvr-falsification-v0', 'members': members,
                                     'digestRule': 'sha256-utf8-sorted-path-tab-file-sha256-lf-rows', 'digest': sha(rows.encode())}
    profile['reasonCodeNamespace']['verification'] = defs['verificationReasonCode']['enum']
    profile['reasonCodeNamespace']['gateRejections'] = ['qev.moth.rvr.v0.rejected']
    profile['externalContextPolicy'] = {'mode': 'COMMITTED_SNAPSHOTS_ONLY', 'ambientInputs': 'FORBIDDEN',
                                       'immutableCommitments': ['claim.captureClaim', 'claim.relation', 'claim.providerAuthentication']}
    save('verification-profile.json', profile)
    save('sources.json', {path: sha((ROOT / path).read_bytes()) for path in FILES})
    print(PROFILE_ID)


if __name__ == '__main__':
    build()
