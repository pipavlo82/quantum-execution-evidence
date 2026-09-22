"""Offline Moth Comet counts consistency. No network, entropy or hardware proof."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime

PROFILE = 'qev-moth-comet-counts-v0'
REQUEST = {'mode': 'qpu', 'params': {'num_qubits': 12, 'shots': 2048,
    'output_bytes': 32, 'bell_witness': True, 'include_raw_counts': True, 'epsilon_log2': 64}}
SPEC = {'bell_witness': True, 'n_rand': 12, 'n_total': 20,
        'witness_pairs': [[12, 13], [14, 15], [16, 17], [18, 19]]}
LIMITS = {
    'providerAuthentication': 'NOT_ESTABLISHED',
    'physicalQpuExecution': 'UPSTREAM_REPORTED_NOT_INDEPENDENTLY_AUTHENTICATED',
    'entropyQualification': 'NOT_ESTABLISHED',
    'cryptographicRandomness': 'NOT_ESTABLISHED',
    'deviceIndependentCertification': 'NOT_ESTABLISHED',
    'orderedMeasurements': 'UNAVAILABLE_COUNTS_ONLY',
    'circuitHashRecomputation': 'CANNOT_ESTABLISH_NO_CIRCUIT_BYTES',
    'commitmentHashRecomputation': 'CANNOT_ESTABLISH_ENCODING_NOT_SPECIFIED',
    'commitmentTiming': 'NOT_ESTABLISHED',
    'toeplitzRecomputation': 'NOT_ESTABLISHED_NO_PINNED_SEED_OR_IMPLEMENTATION',
    'nativeRvrReceiptosTsei': 'NOT_INTEGRATED_FOR_THIS_COUNTS_PROFILE',
}


class MothError(ValueError):
    def __init__(self, reason, state='REJECTED'):
        self.reason, self.state = reason, state
        super().__init__(reason)


def need(value, reason, state='REJECTED'):
    if not value:
        raise MothError(reason, state)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('utf-8')


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def same(a, b):
    return compact(a) == compact(b)


def parse(data):
    need(type(data) is bytes and len(data) <= 4_194_304, 'INPUT_SIZE')
    depth = 0
    quoted = escaped = False
    for ch in data:
        if quoted:
            if escaped:
                escaped = False
            elif ch == 92:
                escaped = True
            elif ch == 34:
                quoted = False
        elif ch == 34:
            quoted = True
        elif ch in (91, 123):
            depth += 1
            need(depth <= 32, 'INPUT_DEPTH')
        elif ch in (93, 125):
            depth -= 1
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'DUPLICATE_KEY')
            out[key] = value
        return out
    def invalid(_):
        raise MothError('NONFINITE')
    def walk(value):
        if type(value) is float:
            need(math.isfinite(value), 'NONFINITE')
        elif type(value) is int:
            need(abs(value) <= 2**53 - 1, 'INTEGER_RANGE')
        elif type(value) is str:
            need(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), 'SURROGATE')
        elif type(value) is dict:
            need(len(value) <= 10000, 'OBJECT_SIZE')
            for k, v in value.items():
                walk(k)
                # These fields may occur as null in provider build metadata.
                if k in ('qpu_token', 'qpu_instance', 'api_key', 'access_token', 'authorization'):
                    need(v is None, 'SECRET_FIELD')
                walk(v)
        elif type(value) is list:
            need(len(value) <= 20000, 'ARRAY_SIZE')
            for v in value:
                walk(v)
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
        walk(value)
        return value
    except (UnicodeError, RecursionError, json.JSONDecodeError) as exc:
        raise MothError('MALFORMED_JSON') from exc


def integer(value, low, high, reason):
    need(type(value) is int and low <= value <= high, reason)
    return value


def number(value, reason):
    need(type(value) in (int, float) and math.isfinite(value), reason)
    return value


def equal(actual, expected, reason):
    need(same(actual, expected), reason, 'REFUTED')


def close(actual, expected, reason):
    number(actual, reason)
    need(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), reason, 'REFUTED')


def digest(value, reason):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, reason)


def timestamp(value):
    need(type(value) is str, 'TIMESTAMP_TYPE')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise MothError('TIMESTAMP_FORMAT') from exc
    need(result.tzinfo is not None, 'TIMESTAMP_ZONE')
    return result


def _evaluate(request, submit, statuses, job, result, expected_job):
    equal(request, REQUEST, 'REQUEST_PROFILE_MISMATCH')
    need(type(expected_job) is str and bool(expected_job), 'EXPECTED_JOB')
    equal(submit['job_id'], expected_job, 'SUBMIT_JOB_BINDING')
    need(submit['status'] in ('pending', 'queued', 'processing', 'submitted'), 'SUBMIT_STATUS')
    need(type(statuses) is list and 1 <= len(statuses) <= 1000, 'STATUS_INVENTORY')
    terminal = False
    early_commit = False
    for status in statuses:
        equal(status['job_id'], expected_job, 'STATUS_JOB_BINDING')
        equal(status['engine_id'], 'comet-qrng-v1', 'STATUS_ENGINE_BINDING')
        equal(status['submitted_at'], submit['submitted_at'], 'SUBMISSION_TIME_BINDING')
        need(status['status'] in ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled'),
             'STATUS_VALUE')
        need(not terminal or status['status'] == statuses[-1]['status'], 'TERMINAL_REGRESSION', 'REFUTED')
        terminal = status['status'] in ('completed', 'failed', 'cancelled')
        if not terminal and '"commit"' in compact(status).decode():
            early_commit = True
    final = statuses[-1]
    need(final['status'] == 'completed', 'JOB_NOT_COMPLETED', 'UNVERIFIABLE')
    equal(job['job_id'], expected_job, 'JOB_BINDING')
    equal(job['engine_id'], 'comet-qrng-v1', 'JOB_ENGINE_BINDING')
    equal(job['status'], 'completed', 'JOB_STATUS_BINDING')
    equal(final['result'], result['result'], 'STATUS_RESULT_AGREEMENT')
    out = result['result']['output']
    p, raw, pulse = out['provenance'], out['raw'], out['pulse']
    equal(p['engine'], 'comet-qrng-v1', 'PROVENANCE_ENGINE')
    equal(p['mode'], 'qpu', 'PROVENANCE_MODE')
    equal(p['shots'], 2048, 'PROVENANCE_SHOTS')
    equal(p['circuit'], SPEC, 'PROVENANCE_CIRCUIT')
    equal(p['readout'], 'counts', 'READOUT_MODE')
    equal(raw['memory_available'], False, 'MEMORY_LABEL')
    for key in ('backend', 'provider_job_id', 'engine_version'):
        need(type(p[key]) is str and bool(p[key]), 'PROVENANCE_' + key)
    need(number(p['qpu_seconds'], 'QPU_SECONDS') >= 0, 'QPU_SECONDS')
    digest(p['circuit_hash'], 'CIRCUIT_HASH_FORMAT')
    builds = []
    for status in statuses:
        steps = status['steps']
        need(type(steps) is list and len({s['name'] for s in steps}) == len(steps), 'STEP_INVENTORY')
        builds.extend(s['extra'] for s in steps if s['name'] == 'build' and s.get('extra'))
    need(bool(builds), 'BUILD_EVIDENCE_MISSING', 'UNVERIFIABLE')
    for build in builds:
        for key, expected in {'spec': SPEC, 'mode': 'qpu', 'shots': 2048,
                'requested_bytes': 32, 'include_raw_counts': True, 'epsilon_log2': 64,
                'circuit_hash': p['circuit_hash'], 'built_at': p['built_at'],
                'qpu_token': None, 'qpu_instance': None}.items():
            equal(build[key], expected, 'BUILD_' + key)
    counts = raw.get('counts')
    need(counts is not None, 'COUNTS_MISSING', 'UNVERIFIABLE')
    need(type(counts) is dict and 1 <= len(counts) <= 2048, 'COUNTS_SHAPE')
    for bitstring, count in counts.items():
        need(type(bitstring) is str and re.fullmatch('[01]{20}', bitstring) is not None, 'COUNT_WIDTH')
        integer(count, 1, 2048, 'COUNT_VALUE')
    equal(sum(counts.values()), 2048, 'COUNT_TOTAL')
    equal(raw['n_unique_bitstrings'], len(counts), 'UNIQUE_COUNTS')
    counts_hash = sha(compact(counts))
    equal(raw['counts_sha256'], counts_hash, 'COUNTS_HASH')
    equal(pulse['raw_counts_hash'], counts_hash, 'PULSE_COUNTS_HASH')
    equal(pulse['provenance'], p, 'PULSE_PROVENANCE')
    equal(pulse['extractor'], out['extractor'], 'PULSE_EXTRACTOR')
    commit = out['commitment']
    digest(commit['commit'], 'COMMITMENT_FORMAT')
    digest(commit['salt'], 'SALT_FORMAT')
    equal(commit['binds'], ['circuit_hash', 'backend', 'provider_job_id', 'salt'], 'COMMITMENT_BINDS')
    equal(pulse['commitment'], {k: commit[k] for k in ('commit', 'salt')}, 'PULSE_COMMITMENT')
    equal(commit['committed_at'], p['committed_at'], 'COMMITMENT_TIME_AGREEMENT')
    times = [timestamp(p[k]) for k in ('built_at', 'committed_at', 'collected_at', 'formatted_at')]
    need(times == sorted(times), 'PROVIDER_TIME_ORDER', 'REFUTED')
    equal(pulse['timestamp'], p['formatted_at'], 'PULSE_TIMESTAMP')
    equal(pulse['version'], 2, 'PULSE_VERSION')
    equal(pulse['index'], None, 'PULSE_INDEX')
    equal(pulse['prev_hash'], '0' * 64, 'PULSE_PREVIOUS')
    pulse_hash = sha(compact({k: v for k, v in pulse.items() if k != 'pulse_hash'}))
    equal(pulse['pulse_hash'], pulse_hash, 'PULSE_HASH')
    rnd, ext, ent, report = out['random'], out['extractor'], out['entropy'], out['entropy_report']
    integer(rnd['bytes'], 0, 32, 'OUTPUT_BYTES')
    need(type(rnd['hex']) is str and re.fullmatch('[0-9a-f]*', rnd['hex']) is not None, 'OUTPUT_HEX')
    equal(len(rnd['hex']), rnd['bytes'] * 2, 'OUTPUT_HEX_LENGTH')
    equal(rnd['bits'], rnd['bytes'] * 8, 'OUTPUT_BITS')
    equal(rnd['requested_bytes'], 32, 'REQUESTED_BYTES')
    equal(pulse['output_hash'], sha(bytes.fromhex(rnd['hex'])), 'OUTPUT_HASH')
    equal(ext['kind'], 'toeplitz', 'EXTRACTOR_KIND')
    equal(ext['input_serialisation'], 'sorted bitstrings repeated by count (canonical multiset)', 'EXTRACTOR_SERIALISATION')
    for obj in (ext, report):
        equal(obj['epsilon_log2'], 64, 'EPSILON')
        equal(obj['output_bits'], rnd['bits'], 'EXTRACTOR_OUTPUT_BITS')
    for key, value in {'n_rand': 12, 'shots': 2048, 'raw_bits': 24576, 'readout': 'counts'}.items():
        equal(ent[key], value, 'ENTROPY_' + key)
    equal(ext['input_bits'], 24576, 'EXTRACTOR_INPUT_BITS')
    equal(report['raw_bits'], 24576, 'REPORT_RAW_BITS')
    for key in ('budget_bits', 'budget_bits_assumption_free', 'budget_bits_modelled', 'h_bit', 'h_shot_assumption_free'):
        need(number(ent[key], 'ENTROPY_NUMERIC') >= 0, 'ENTROPY_NONNEGATIVE')
        equal(report[key], ent[key], 'ENTROPY_REPORT_AGREEMENT_' + key)
    need(ent['h_bit'] <= 1, 'H_BIT_RANGE')
    close(ent['ordering_penalty_bits'], math.lgamma(2049) / math.log(2), 'ORDERING_PENALTY')
    # Algebra using an upstream entropy estimate, never a min-entropy proof.
    budget = max(0, ent['h_bit'] * 24576 - ent['ordering_penalty_bits'])
    close(ent['budget_bits_modelled'], budget, 'MODELLED_BUDGET_ARITHMETIC')
    expected_bytes = min(32, max(0, math.floor((ent['budget_bits'] - 128) / 8)))
    equal(rnd['bytes'], expected_bytes, 'BUDGET_OUTPUT_LENGTH')
    for key in ('budget_bits', 'budget_bits_assumption_free', 'h_bit', 'readout'):
        equal(pulse['entropy'][key], ent[key], 'PULSE_ENTROPY_' + key)
    equal(pulse['entropy']['basis'], report['accounting_basis'], 'ENTROPY_BASIS')
    equal(pulse['entropy']['health_passed'], report['health_passed'], 'HEALTH_LABEL')
    for key in ('entropy_accounted', 'health_passed', 'independence_model_falsified', 'public_output', 'witness_violates_classical'):
        need(type(report[key]) is bool, 'REPORT_BOOL')
    if rnd['bytes'] == 0:
        equal(report['entropy_accounted'], False, 'EMPTY_ENTROPY_LABEL')
        equal(report['grade'], 'hardware-insufficient-entropy', 'EMPTY_OUTPUT_GRADE')
    fingerprint = out['device_fingerprint']
    equal(fingerprint['n_qubits'], 20, 'FINGERPRINT_WIDTH')
    equal(fingerprint['roles'], {'randomness': list(range(12)), 'witness_pairs': SPEC['witness_pairs']}, 'FINGERPRINT_ROLES')
    for key in ('p1', 'z_expectations'):
        need(type(fingerprint[key]) is list and len(fingerprint[key]) == 20, 'FINGERPRINT_SIZE')
    ones = [sum(count for bits, count in counts.items() if bits[q] == '1') for q in range(20)]
    for q in range(20):
        close(fingerprint['p1'][q], ones[q] / 2048, 'MARGINAL_P1')
        close(fingerprint['z_expectations'][q], 1 - 2 * ones[q] / 2048, 'MARGINAL_Z')
    witness = out['bell_witness']
    equal(witness['enabled'], True, 'WITNESS_ENABLED')
    equal(witness['kind'], 'chsh_fidelity_witness', 'WITNESS_KIND')
    need(len(witness['correlators']) == 4, 'WITNESS_INVENTORY')
    es = []
    for row, pair, setting in zip(witness['correlators'], SPEC['witness_pairs'], ("E(a,b)", "E(a,b')", "E(a',b)", "E(a',b')")):
        equal(row['qubits'], pair, 'WITNESS_PAIR')
        equal(row['setting'], setting, 'WITNESS_SETTING')
        marginal = Counter({'00': 0, '01': 0, '10': 0, '11': 0})
        for bits, count in counts.items():
            marginal[bits[pair[0]] + bits[pair[1]]] += count
        equal(row['counts'], dict(marginal), 'WITNESS_COUNTS')
        e = (marginal['00'] + marginal['11'] - marginal['01'] - marginal['10']) / 2048
        close(row['E'], e, 'WITNESS_E')
        close(row['sigma'], math.sqrt((1 - e * e) / 2048), 'WITNESS_SIGMA_ALGEBRA')
        es.append(e)
    s = abs(es[0] - es[1] + es[2] + es[3])
    sigma = math.sqrt(sum((1 - e * e) / 2048 for e in es))
    close(witness['S'], s, 'WITNESS_S')
    close(witness['sigma_S'], sigma, 'WITNESS_SIGMA_S_ALGEBRA')
    equal(witness['violates_classical_3sigma'], s - 3 * sigma > 2, 'WITNESS_3SIGMA_ALGEBRA')
    equal(report['witness_violates_classical'], witness['violates_classical_3sigma'], 'WITNESS_REPORT')
    return {
        'consistency': 'CONSISTENT', 'reason': 'PRESERVED_COUNTS_AND_REPORT_ARITHMETIC',
        'jobId': expected_job, 'countsSha256': counts_hash, 'pulseSha256': pulse_hash,
        'shots': 2048, 'uniqueBitstrings': len(counts), 'width': 20,
        'randomnessQubits': 12, 'witnessQubits': 8,
        'requestedBytes': 32, 'deliveredBytes': rnd['bytes'],
        'delivery': 'EMPTY_BUDGET_LIMITED' if rnd['bytes'] == 0 else 'UPSTREAM_OUTPUT_PRESERVED',
        'witnessS': s, 'witnessSigmaAlgebra': sigma,
        'hashEncodingAuthority': 'LOCAL_PROFILE_OBSERVED_MATCH_NOT_UPSTREAM_SOURCE_VERIFIED',
        'commitmentObservation': 'PRESENT_IN_NONTERMINAL_STATUS' if early_commit else 'FIRST_SEEN_WITH_RESULT',
        'certificatePresence': 'PRESENT_UPSTREAM_ONLY' if 'certificate' in out else 'ABSENT',
        'upstreamReported': {'provenance': p, 'entropyReport': report,
                             'commitment': commit, 'certificate': out.get('certificate')},
    }


def evaluate(request, submit, statuses, job, result, expected_job):
    """Assess supplied objects; callers bind the original bytes separately."""
    try:
        # A shared strict boundary also applies to programmatic callers.
        for value in (request, submit, statuses, job, result):
            parse(compact(value))
        report = _evaluate(request, submit, statuses, job, result, expected_job)
    except MothError as exc:
        report = {'consistency': exc.state, 'reason': exc.reason}
    except (KeyError, TypeError, IndexError, ValueError, OverflowError, RecursionError):
        report = {'consistency': 'REJECTED', 'reason': 'REQUIRED_FIELD_OR_TYPE'}
    return {'schema': 'qev.moth-comet-report.v0', 'profile': PROFILE,
            **report, 'limits': dict(LIMITS)}
