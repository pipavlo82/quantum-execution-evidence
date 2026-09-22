"""Build the additive live profile from declared dependencies, without self hashes."""
import copy
import json
from pathlib import Path
from qev.live_common import ROOT, PROFILE, ANCHORS, encode, sha
from qev.live_native import RUNTIME
from qev.source_inventory import ALL_VENDOR_FILES


def closed(properties):
    return {'type': 'object', 'additionalProperties': False,
            'required': list(properties), 'properties': properties}


def schemas():
    old = json.loads((ROOT / 'profiles/qev-preserved-observation-v0/rvr-qev.schema.json').read_bytes())
    schema = copy.deepcopy(old)
    schema['$id'] = 'urn:qev:rvr-live-capture-replay-v1'
    schema['title'] = 'Native RVR live capture replay v1'
    defs = schema['$defs']
    defs['verificationReasonCode'] = {'enum': ['qev.live.v1.' + x for x in ('verified', 'refuted', 'unverifiable')]}
    defs['unavailableEvidenceMember']['properties']['reasonCode'] = {'const': 'qev.live.v1.evidence_unavailable'}
    string = {'type': 'string'}
    defs['claim'] = closed({
        'schema': {'const': 'qev.live-claim.v1'}, 'jobId': string, 'backend': string,
        'requestId': string, 'shots': {'type': 'string', 'pattern': '^[1-9][0-9]*$'},
        'anchors': closed({k: {'$ref': '#/$defs/digest'} for k in ANCHORS}),
        'captureOrigin': {'const': 'LIVE_IBM_RUNTIME_API'},
        'providerAuthentication': {'const': 'NOT_ESTABLISHED'},
        'angleMap': {'const': 'qev-ideal-angle-literals-v1'},
    })
    axes = ('byteIdentity', 'declaredCaptureOrigin', 'jobRequestBinding', 'providerArtifactConsistency',
            'rawCommitment', 'orderedRecordAgreement', 'histogramRecomputation', 'bitOrder',
            'completedObservation', 'isaRelation', 'measurementIntent', 'authenticationLabelConsistency')
    native = closed({**{k: string for k in ('schema', 'transformation_claim', 'transformation_profile_id',
        'transformation_family', 'source_object_kind', 'target_object_kind', 'recompute_procedure_id',
        'comparison_rule_id', 'evaluation_state', 'classification')},
        **{k: {'type': ['string', 'null']} for k in ('out_of_domain_reason', 'unresolved_reason')},
        **{k: {'type': ['boolean', 'null']} for k in ('normative_match', 'stability_match',
                                                     'forbidden_variant_match', 'allowed_variant_changed')}})
    defs['canonicalResult'] = closed({
        'schema': {'const': 'rvr.qev.live-result.v1'}, 'outcome': {'$ref': '#/$defs/outcome'},
        'reasonCode': {'$ref': '#/$defs/verificationReasonCode'},
        'axes': closed({k: {'$ref': '#/$defs/axis'} for k in axes}),
        'nativeTsei': {'oneOf': [{'type': 'null'}, native]},
        'providerAuthentication': {'const': 'NOT_ESTABLISHED'},
        'physicalNoiselessBehavior': {'const': 'NOT_ESTABLISHED'},
    })
    defs.pop('evaluation', None)
    defs.pop('inputStatus', None)
    (ROOT / PROFILE / 'rvr-live.schema.json').write_bytes(encode(schema))
    constraints = {'type': 'object', 'required': ['profileId'],
                   'properties': {'profileId': {'const': 'rvr-qev-live-capture-replay-v1'}}}
    (ROOT / PROFILE / 'profile.schema.json').write_bytes(encode(constraints))


def build():
    schemas()
    from qev.live_mutations import inventory
    (ROOT / PROFILE / 'conformance.json').write_bytes(encode(inventory()))
    def dep(identifier, path, required=True):
        return {'id': identifier, 'path': path, 'sha256': sha((ROOT / path).read_bytes()),
                'requiredForRecomputation': required}
    # Reuse only the generic RVR contract declaration, not the old evaluator.
    profile = json.loads((ROOT / 'profiles/qev-preserved-observation-v0/verification-profile.json').read_bytes())
    profile['profileId'] = 'rvr-qev-live-capture-replay-v1'
    profile['profileSchemaContract']['constraints'] = dep('live-profile-schema', PROFILE + '/profile.schema.json')
    profile['verificationSpecification'] = dep('live-specification', 'docs/LIVE_CAPTURE_REPLAY_V1.md')
    schema = dep('rvr-schema', PROFILE + '/rvr-live.schema.json')
    profile['schemaContracts'] = [schema]
    profile['schemaContracts'] += [dep('runtime-' + str(i), p) for i, p in enumerate(RUNTIME)]
    profile['schemaContracts'] += [dep('vendor-' + str(i), row['path']) for i, row in enumerate(ALL_VENDOR_FILES)
                                   if row['path'] != 'vendor/rvr-v0/verification-profile-manifest.schema.json']
    for contract in ('evidenceSetContract', 'canonicalResultContract'):
        profile[contract]['schemaPath'] = schema['path']
        profile[contract]['schemaSha256'] = schema['sha256']
    paths = (PROFILE + '/conformance.json', 'qev/live_mutations.py', 'tests/test_live_replay.py')
    members = [dep('conformance-' + str(i), path, False) for i, path in enumerate(paths)]
    rows = ''.join(x['path'] + '\t' + x['sha256'] + '\n' for x in sorted(members, key=lambda x: x['path']))
    profile['conformanceVectorSet'] = {'id': 'qev-live-finite-falsification-v1', 'members': members,
                                      'digest': sha(rows.encode()),
                                      'digestRule': 'sha256-utf8-sorted-path-tab-file-sha256-lf-rows'}
    profile['reasonCodeNamespace']['verification'] = ['qev.live.v1.' + x for x in ('verified', 'refuted', 'unverifiable')]
    profile['reasonCodeNamespace']['gateRejections'] = ['qev.live.v1.rejected']
    profile['externalContextPolicy'] = {'mode': 'COMMITTED_SNAPSHOTS_ONLY', 'ambientInputs': 'FORBIDDEN',
                                       'immutableCommitments': ['claim.anchors', 'claim.jobId', 'claim.backend',
                                                                'claim.requestId', 'claim.shots']}
    (ROOT / PROFILE / 'verification-profile.json').write_bytes(encode(profile))
    return profile


if __name__ == '__main__':
    profile = build()
    print(json.dumps({'profileId': profile['profileId'], 'profileFileSha256': sha(encode(profile))}))
