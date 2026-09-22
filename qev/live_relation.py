"""Capture consistency is distinct from ideal ISA preservation and authentication."""
from collections import Counter
from .live_common import (ROLES, ANCHORS, PROFILE, Rejected, need, parse, shape,
                          sha, physical_bytes, validate_claim, read)
from .live_math import project, Unsupported


def evaluate(claim, payloads, root, tsei):
    validate_claim(claim)
    need(set(payloads) <= set(ROLES), 'ROLE_INVENTORY')
    shapes = parse(read(root, PROFILE + '/capture-shapes.json'))
    data = {}
    for name, raw in payloads.items():
        need(type(raw) is bytes and len(raw) <= 262144, 'ROLE_SIZE')
        if name.endswith('.json'):
            value = parse(raw)
            shape(value, shapes[name])
            data[name] = value
        else:
            data[name] = raw

    def check(names, predicate):
        if not all(n in data for n in names):
            return 'CANNOT_ESTABLISH'
        return 'SATISFIED' if predicate(*(data[n] for n in names)) else 'REFUTED'

    expected_shots = int(claim['shots'])
    # Evaluate every available anchor. Missing evidence cannot erase a resolved
    # contradiction in another, independently committed role.
    if any(sha(payloads[n]) != claim['anchors'][n] for n in ANCHORS if n in payloads):
        byte_identity = 'REFUTED'
    elif any(n not in payloads for n in ANCHORS):
        byte_identity = 'CANNOT_ESTABLISH'
    else:
        byte_identity = 'SATISFIED'
    def combine(*states):
        if 'REFUTED' in states:
            return 'REFUTED'
        return 'CANNOT_ESTABLISH' if 'CANNOT_ESTABLISH' in states else 'SATISFIED'

    origin = combine(
        check(('submission-intent.json',), lambda intent:
            intent['schema'] == 'qev.live-capture.intent.v0'
            and intent['capture_kind'] == claim['captureOrigin']),
        check(('ibm-live-record.normalized.json',), lambda record:
            record['schema'] == 'qev.ibm-runtime-sampler-v2-record.v0'
            and record['sdk']['source'] == 'LIVE_IBM_RUNTIME_API'
            and record['capture_kind'] == 'RECORDED_PROVIDER_API_ARTIFACT'
            and record['runtime'] == {'primitive': 'SamplerV2', 'primitive_version': 2}),
        check(('submission-intent.json', 'ibm-live-record.normalized.json'), lambda intent, record:
            record['sdk']['qiskit'] == intent['qiskit'] and record['sdk']['qiskit_ibm_runtime'] == intent['runtime']),
        check(('normalization-provenance.json',), lambda provenance:
            provenance['schema'] == 'qev.live-capture.normalization.v0'
            and provenance['request_and_transpiler_origin'] == 'LOCAL_SUBMISSION_INTENT_NOT_PROVIDER_ATTESTED'
            and provenance['physical_circuit_origin'] == 'fresh service.job(job_id).inputs[pubs][0][0] decoded QuantumCircuit'
            and provenance['raw_origin'] == 'fresh service.job(job_id).result()[0].data.meas.get_bitstrings()'
            and provenance['digest_surface'] == 'sha256 of qev.provider_binding.canonical(operation snapshot); distinct from QPY/QASM identity'
            and provenance['expected_job_id_origin'] == 'locally persisted immediate submit response; supplementary comparison, not enforced by legacy adapter'
            and provenance['scope'] == 'Live authenticated SDK acquisition plus offline byte consistency; no hardware attestation or entropy qualification'),
        check(('measurement-metadata.json',), lambda meta:
            meta['capture'] == 'DECODED_FROM_IBM_RUNTIME_SERVICE_NOT_WIRE_CAPTURE'))
    binding = combine(
        check(('submission-intent.json',), lambda intent:
            intent['backend'] == claim['backend']
            and intent['shots'] == intent['options']['default_shots'] == expected_shots
            and intent['options']['job_tag'] == claim['requestId'] and intent['authorized_jobs'] == 1),
        check(('job-receipt.json',), lambda receipt:
            receipt['job_id'] == claim['jobId'] and receipt['backend_requested'] == claim['backend']
            and receipt['intent_sha256'] == claim['anchors']['submission-intent.json']
            and receipt['shots_requested'] == expected_shots and receipt['submission_calls'] == 1),
        check(('provider-submission.normalized.json',), lambda submission:
            submission['schema'] == 'qev.provider-submission.v0' and submission['provider'] == 'ibm-quantum'
            and submission['backend'] == claim['backend'] and submission['shots'] == expected_shots
            and submission['request_id'] == submission['requested_job'] == claim['requestId']),
        check(('ibm-live-record.normalized.json',), lambda record:
            record['job']['job_id'] == claim['jobId'] and record['job']['backend'] == claim['backend']
            and record['job']['request_id'] == claim['requestId'] and record['job']['provider'] == 'ibm-quantum'
            and record['result']['shots'] == expected_shots),
        check(('measurement-metadata.json',), lambda meta:
            meta['job_id'] == claim['jobId'] and meta['backend'] == claim['backend'] and meta['shots'] == expected_shots),
        check(('normalization-provenance.json',), lambda provenance:
            provenance['expected_job_id'] == claim['jobId']
            and provenance['precommit_intent_sha256'] == claim['anchors']['submission-intent.json']),
        check(('normalization-provenance.json', 'ibm-live-record.normalized.json'), lambda provenance, record:
            provenance['live_record_sha256'] == sha(payloads['ibm-live-record.normalized.json'])),
        check(('provider-submission.normalized.json', 'ibm-live-record.normalized.json'), lambda submission, record:
            submission['transpiler'] == record['isa_circuit']['transpiler']))
    circuit = combine(
        check(('isa-submitted.json', 'isa-returned.json'), lambda submitted, returned: submitted == returned),
        check(('submission-intent.json', 'logical.json'), lambda intent, logical:
            intent['artifacts']['logical.json'] == sha(payloads['logical.json'])),
        check(('submission-intent.json', 'isa-submitted.json'), lambda intent, submitted:
            intent['artifacts']['isa-submitted.json'] == sha(payloads['isa-submitted.json'])),
        check(('isa-submitted.json', 'provider-submission.normalized.json'), lambda submitted, submission:
            sha(physical_bytes(submitted)) == submission['physicalCircuitDigest']),
        check(('isa-returned.json', 'ibm-live-record.normalized.json'), lambda returned, record:
            sha(physical_bytes(returned)) == record['isa_circuit']['physicalCircuitDigest']),
        check(('ibm-live-record.normalized.json',), lambda record:
            record['isa_circuit']['representation'] == 'sdk-decoded-operation-snapshot-v0'),
        check(('submission-intent.json',), lambda intent:
            intent['active_physical_qubits'] == [0, 1] and intent['logical_qubits'] == 2
            and intent['classical_register'] == 'meas'))
    raw_name = 'measurements-ordered.c1c0.txt'
    lines = None
    if raw_name in payloads:
        raw = payloads[raw_name]
        need(raw.endswith(b'\n') and b'\r' not in raw, 'RAW_LF')
        chunks = raw[:-1].split(b'\n')
        need(1 <= len(chunks) <= 4096 and all(len(s) == 2 and set(s) <= {48, 49} for s in chunks), 'RAW_WIDTH_DOMAIN')
        lines = [s.decode('ascii') for s in chunks]
    if 'measurement-counts.json' in data:
        counts = data['measurement-counts.json']
        need(set(counts) <= {'00', '01', '10', '11'} and all(0 <= n <= 4096 for n in counts.values()), 'COUNTS_DOMAIN')
    if 'ibm-live-record.normalized.json' in data:
        bits = data['ibm-live-record.normalized.json']['result']['bitstrings']
        need(len(bits) <= 4096 and all(s in ('00', '01', '10', '11') for s in bits), 'BITSTRINGS_DOMAIN')
    raw_identity = combine(
        check((raw_name,), lambda raw:
            sha(raw) == claim['anchors'][raw_name] and len(lines) == expected_shots),
        check((raw_name, 'measurement-metadata.json'), lambda raw, meta:
            sha(raw) == meta['canonical_raw_sha256'] and meta['raw_bytes'] == len(raw)),
        check(('measurement-metadata.json',), lambda meta: meta['width'] == 2))
    ordered = check((raw_name, 'ibm-live-record.normalized.json'),
                    lambda raw, record: lines == record['result']['bitstrings'])
    histogram = check((raw_name, 'measurement-counts.json'), lambda raw, counts: dict(Counter(lines)) == counts)
    order = combine(
        check(('submission-intent.json',), lambda intent: intent['bitstring_order'] == 'c1 c0'),
        check(('ibm-live-record.normalized.json',), lambda record:
            record['result']['metadata'] == {'bit_order': 'c1c0', 'capture': 'BitArray.get_bitstrings', 'pub_index': 0}
            and record['result']['register'] == 'meas'),
        check(('measurement-metadata.json',), lambda meta:
            meta['register'] == 'meas' and meta['num_pubs'] == 1 and meta['shape'] == []
            and meta['raw_order'] == 'c1c0 returned by BitArray.get_bitstrings, no reordering'))
    completion = check(('ibm-live-record.normalized.json', 'measurement-metadata.json'),
                       lambda record, meta: record['job']['status'] == meta['job_status'] == 'DONE')
    if completion == 'REFUTED':
        completion = 'CANNOT_ESTABLISH'
    auth = combine(
        check(('normalization-provenance.json',), lambda provenance: provenance['provider_signature'] == 'NOT_ESTABLISHED'),
        check(('provider-input-comparison.json',), lambda comparison: comparison['independent_provider_signature'] == 'NOT_ESTABLISHED'))
    isa = 'CANNOT_ESTABLISH'
    native = None
    projections = {}
    for name in ('logical.json', 'isa-submitted.json', 'isa-returned.json'):
        if name in data:
            try:
                projections[name] = project(data[name])
            except Unsupported:
                pass
    measurement_intent = 'CANNOT_ESTABLISH'
    if 'submission-intent.json' in data:
        intent = data['submission-intent.json']
        mapping = intent['measurement_mapping']
        need(len(mapping) == 2 and {m['physical_qubit'] for m in mapping} == {0, 1}
             and {m['classical_bit'] for m in mapping} == {0, 1}, 'INTENT_MEASUREMENT_MAPPING')
        declared = sorted([[str(m['physical_qubit']), str(m['classical_bit'])] for m in mapping])
        # Compare all three actual maps against the declaration. Native TSEI
        # source/target equality alone does not establish submission intent.
        if (intent['bitstring_order'] != 'c1 c0' or intent['classical_register'] != 'meas'
                or any(p['measurement'] != declared for p in projections.values())):
            measurement_intent = 'REFUTED'
        elif len(projections) == 3:
            measurement_intent = 'SATISFIED'
    if 'logical.json' in data and 'isa-returned.json' in data:
        native = tsei(data['logical.json'], data['isa-returned.json'])
        isa = {'stable': 'SATISFIED', 'violation': 'REFUTED'}.get(native['classification'], 'CANNOT_ESTABLISH')
    axes = {'byteIdentity': byte_identity, 'declaredCaptureOrigin': origin,
            'jobRequestBinding': binding, 'providerArtifactConsistency': circuit,
            'rawCommitment': raw_identity, 'orderedRecordAgreement': ordered,
            'histogramRecomputation': histogram, 'bitOrder': order,
            'completedObservation': completion, 'isaRelation': isa, 'measurementIntent': measurement_intent,
            'authenticationLabelConsistency': auth}
    if 'REFUTED' in axes.values():
        outcome = 'REFUTED'
    elif 'CANNOT_ESTABLISH' in axes.values():
        outcome = 'UNVERIFIABLE'
    else:
        outcome = 'VERIFIED'
    return {'schema': 'rvr.qev.live-result.v1', 'outcome': outcome,
            'reasonCode': 'qev.live.v1.' + outcome.lower(), 'axes': axes,
            'nativeTsei': native, 'providerAuthentication': 'NOT_ESTABLISHED',
            'physicalNoiselessBehavior': 'NOT_ESTABLISHED'}
