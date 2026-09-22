"""Production verifier. Deliberately has no dependency on the fixture corpus."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from qev import adapters

PROFILE = 'quantum-evidence.v0'
POSTPROCESSOR = 'integer-score-parity.v0'
MAX_BYTES = 262144
CLAIM = 'FINITE_POSTPROCESSING'
ELEVATIONS = ('AUTHENTIC_QPU_EXECUTION', 'SAMPLER_INDEPENDENCE', 'DISTRIBUTION_EQUALITY',
              'MIN_ENTROPY', 'CRYPTOGRAPHIC_RNG', 'DEVICE_CERTIFICATION')

class InputError(ValueError):
    def __init__(self, reason, category='INVALID'):
        self.reason, self.category = reason, category
        super().__init__(reason)

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def digest(value):
    return sha(canonical(value))

def require(condition, reason, category='INVALID'):
    if not condition:
        raise InputError(reason, category)

def strict_load(data):
    require(type(data) is bytes and len(data) <= MAX_BYTES, 'INPUT_SIZE_LIMIT')
    try:
        text = data.decode('utf-8')
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped: escaped = False
                elif char == '\\': escaped = True
                elif char == '"': quoted = False
            elif char == '"': quoted = True
            elif char in '[{':
                depth += 1
                require(depth <= 16, 'DEPTH_LIMIT')
            elif char in ']}': depth -= 1
        def pairs(items):
            obj = {}
            for key, val in items:
                require(key not in obj, 'DUPLICATE_JSON_KEY')
                obj[key] = val
            return obj
        def integer(s):
            require(len(s) <= 12, 'INTEGER_TOKEN_LIMIT')
            return int(s)
        def unsupported_number(s):
            raise InputError('FLOAT_OR_NONFINITE')
        obj = json.loads(text, object_pairs_hook=pairs, parse_int=integer,
                         parse_float=unsupported_number, parse_constant=unsupported_number)
        nodes, todo = 0, [obj]
        while todo:
            val = todo.pop()
            nodes += 1
            require(nodes <= 20000, 'NODE_LIMIT')
            require(type(val) is not bool, 'BOOLEAN_FORBIDDEN')
            if type(val) is dict: todo.extend(val.keys()); todo.extend(val.values())
            elif type(val) is list: todo.extend(val)
            elif type(val) is str: require(len(val) <= 40000, 'STRING_LIMIT')
        return obj
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InputError('MALFORMED_JSON') from exc

def fields(obj, names):
    require(type(obj) is dict and set(obj) == set(names.split()), 'OBJECT_FIELDS')

def uint(value, lo, hi):
    require(type(value) is int and lo <= value <= hi, 'INTEGER_RANGE')

def label(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9_.:-]{1,120}', value) is not None, 'LABEL')

def hash_value(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None, 'SHA256_FORMAT')

def permutation(value, width):
    require(type(value) is list and len(value) == width and
            all(type(i) is int for i in value) and sorted(value) == list(range(width)), 'BIT_PERMUTATION')

def validate_request(req):
    fields(req, 'marker request_id program parameters width shots source_to_output endianness provider backend job')
    require(req['marker'] == 'SYNTHETIC', 'SYNTHETIC_MARKER')
    for key in ('request_id', 'provider', 'backend', 'job'): label(req[key])
    uint(req['width'], 1, 8); uint(req['shots'], 1, 4096)
    permutation(req['source_to_output'], req['width'])
    require(req['endianness'] == 'source-index-ascending', 'ENDIANNESS', 'UNSUPPORTED')
    fields(req['parameters'], 'theta_quarters')
    uint(req['parameters']['theta_quarters'], 0, 3)
    fields(req['program'], 'codec source')
    require(req['program']['codec'] == 'qev-lines.v0', 'PROGRAM_CODEC', 'UNSUPPORTED')
    source = req['program']['source']
    require(type(source) is str and len(source) <= 2048 and source.isascii() and '\r' not in source and source.endswith('\n'), 'PROGRAM_BYTES')
    lines = source[:-1].split('\n')
    require(1 <= len(lines) <= 64 and lines[-1] == 'MEASURE_ALL', 'PROGRAM_TERMINATOR')
    for line in lines[:-1]:
        match = re.fullmatch(r'(H|X) ([0-7])|CX ([0-7]) ([0-7])|RZ ([0-7]) theta_quarters', line)
        require(match is not None, 'PROGRAM_EXPRESSION', 'UNSUPPORTED')
        indices = [int(v) for v in match.groups()[1:] if v is not None]
        require(all(i < req['width'] for i in indices), 'QUBIT_RANGE')
        if line.startswith('CX '): require(indices[0] != indices[1], 'CX_DISTINCT')

def validate_package(pack):
    fields(pack, 'marker profile hash_algorithm json_codec request request_sha256 raw output_to_raw counts postprocessor result claimed_execution provider_evidence desired_claim payload_sha256')
    require(pack['marker'] == 'SYNTHETIC', 'SYNTHETIC_MARKER')
    for key, expected in [('profile', PROFILE), ('hash_algorithm', 'sha256'), ('json_codec', 'qev-json.v0'), ('postprocessor', POSTPROCESSOR)]:
        require(pack[key] == expected, key.upper(), 'UNSUPPORTED')
    validate_request(pack['request'])
    width = pack['request']['width']
    permutation(pack['output_to_raw'], width)
    hash_value(pack['request_sha256']); hash_value(pack['payload_sha256'])
    require(pack['claimed_execution'] in ('SYNTHETIC', 'SIMULATOR', 'QPU'), 'EXECUTION_LABEL', 'UNSUPPORTED')
    label(pack['desired_claim'])
    if pack['provider_evidence'] is not None:
        fields(pack['provider_evidence'], 'kind text')
        require(pack['provider_evidence']['kind'] == 'UNVERIFIED_TEXT', 'PROVIDER_CODEC', 'UNSUPPORTED')
        require(type(pack['provider_evidence']['text']) is str and len(pack['provider_evidence']['text']) <= 4096, 'PROVIDER_TEXT')
    if pack['raw'] is not None:
        fields(pack['raw'], 'codec data sha256')
        require(pack['raw']['codec'] == 'ascii-bit-lines-lf.v0', 'RAW_CODEC', 'UNSUPPORTED')
        hash_value(pack['raw']['sha256'])
        require(type(pack['raw']['data']) is str and len(pack['raw']['data']) <= 36864, 'RAW_LIMIT')
        require(re.fullmatch(r'(?:[01]{'+str(width)+r'}\n){1,4096}', pack['raw']['data']) is not None, 'RAW_BITS')
    require(type(pack['counts']) is dict and 1 <= len(pack['counts']) <= 2**width, 'COUNTS_SHAPE')
    for bitstring, count in pack['counts'].items():
        require(re.fullmatch('[01]{'+str(width)+'}', bitstring) is not None, 'COUNT_BITS')
        uint(count, 1, 4096)
    require(sum(pack['counts'].values()) <= 4096, 'COUNT_LIMIT')
    fields(pack['result'], 'shots weighted_sum parity_ones')
    for val in pack['result'].values(): uint(val, 0, 147456)

def declarations(scope, desired):
    # Fixed subset constructed in code; validated against the source-pinned schema
    # structure/enums before invoking the native linker (which is not a validator).
    claim = {'claim_type': CLAIM, 'authority_class': 'INDEPENDENT_RECOMPUTATION',
             'scope': scope, 'verification_time': 'preserved-observation-check.v0'}
    negatives = [{'claim_type': name, 'authority_class': 'SEMANTIC_VERIFICATION', 'scope': scope} for name in ELEVATIONS]
    producer = {'endpoint': 'offline/check', 'consumes': [], 'establishes': [claim], 'does_not_establish': negatives}
    consumer = {**claim, 'claim_type': desired, 'authority_class': 'SEMANTIC_VERIFICATION'}
    schema = adapters.manifest_schema()
    authorities = schema['$defs']['authorityClass']['enum']
    fields(producer, 'endpoint consumes establishes does_not_establish')
    for c in [claim, consumer]:
        fields(c, 'claim_type authority_class scope verification_time')
        require(c['authority_class'] in authorities and all(type(v) is str and v for v in c.values()), 'DECLARATION')
    for n in negatives:
        fields(n, 'claim_type authority_class scope')
        require(n['authority_class'] in authorities, 'DECLARATION')
    return producer, consumer

def empty_result():
    return {'profile': PROFILE, 'marker': 'SYNTHETIC', 'input_status': 'VALID', 'reasons': [],
            'source_provenance': {'status': 'NOT_CHECKED'}, 'supplied_claims': {},
            'integrity': 'CANNOT_ESTABLISH', 'request_binding': 'CANNOT_ESTABLISH',
            'deterministic_verification': 'CANNOT_ESTABLISH', 'claim_support': 'NOT_ESTABLISHED',
            'native_link': {'status': 'NOT_EVALUATED'}, 'provider_authenticity': 'NOT_ESTABLISHED',
            'physical': {k: ('NOT_EVALUATED' if k == 'DISTRIBUTION_EQUALITY' else 'NOT_ESTABLISHED') for k in ELEVATIONS},
            'native_rvr': 'NATIVE_RVR_NOT_INTEGRATED', 'author_independence': 'NOT_ESTABLISHED',
            'identities': {}, 'recomputed': None}

def native_result_status(result, producer, consumer):
    """Validate returned native shape without promoting compatibility to truth."""
    if type(result) is not dict or type(result.get('valid')) is not bool:
        return 'MALFORMED'
    if result['valid'] is False:
        if not set(result)<= {'valid','error','counterexample'}: return 'MALFORMED'
        error=result.get('error')
        # Native TYPE_ERROR string, or a controlled adapter error-code diagnostic.
        diagnostic=(type(error) is str and bool(error)) or (
            type(error) is dict and set(error)=={'code'} and type(error['code']) is str and bool(error['code']))
        if not diagnostic or ('counterexample' in result and type(result['counterexample']) is not dict):
            return 'MALFORMED'
        return 'REJECTED'
    if set(result)!= {'valid','edge'} or type(result['edge']) is not dict:
        return 'MALFORMED'
    edge=result['edge']
    if (set(edge)!= {'producer_claim','consumer_requirement'}
            or edge['producer_claim'] not in producer['establishes']
            or edge['consumer_requirement']!=consumer): return 'MALFORMED'
    return 'EXECUTED'

def verify(request_bytes, package_bytes):
    out = empty_result()
    try:
        req, pack = strict_load(request_bytes), strict_load(package_bytes)
        validate_request(req); validate_package(pack)
        out['identities'] = {'request_input_bytes_sha256': sha(request_bytes), 'package_input_bytes_sha256': sha(package_bytes),
                             'trusted_request_sha256': digest(req), 'embedded_request_sha256': digest(pack['request'])}
        out['supplied_claims'] = {'execution': pack['claimed_execution'], 'desired_claim': pack['desired_claim'],
                                  'provider_evidence': 'MISSING' if pack['provider_evidence'] is None else 'UNVERIFIED_TEXT',
                                  'provider': pack['request']['provider'], 'backend': pack['request']['backend'], 'job': pack['request']['job']}
        bound = pack['request'] == req
        out['request_binding'] = 'SATISFIED' if bound else 'REFUTED'
        if not bound: out['reasons'].append('INDEPENDENT_REQUEST_MISMATCH')
        payload = {k:v for k,v in pack.items() if k != 'payload_sha256'}
        package_ok = digest(payload) == pack['payload_sha256']
        request_hash_ok = digest(pack['request']) == pack['request_sha256']
        raw_ok = pack['raw'] is None or sha(pack['raw']['data'].encode('ascii')) == pack['raw']['sha256']
        out['integrity'] = 'SATISFIED' if package_ok and request_hash_ok and raw_ok else 'REFUTED'
        if not package_ok: out['reasons'].append('PACKAGE_DIGEST_MISMATCH')
        if not request_hash_ok: out['reasons'].append('REQUEST_DIGEST_MISMATCH')
        if not raw_ok: out['reasons'].append('RAW_DIGEST_MISMATCH')
        if pack['raw'] is None:
            out['reasons'].append('RAW_MISSING')
        else:
            r = pack['request']
            width = r['width']
            raw_shots = pack['raw']['data'][:-1].split('\n')
            mapped = [''.join(bits[pack['output_to_raw'][r['source_to_output'][i]]] for i in range(width)) for bits in raw_shots]
            counts = dict(sorted(Counter(mapped).items()))
            derived = {'shots': len(mapped),
                       'weighted_sum': sum(n*sum((i+1)*int(b[i]) for i in range(width)) for b,n in counts.items()),
                       'parity_ones': sum(n for b,n in counts.items() if b.count('1') % 2)}
            out['recomputed'] = {'counts': counts, 'result': derived}
            out['identities']['ordered_raw_sha256'] = sha(pack['raw']['data'].encode('ascii'))
            out['identities']['canonical_ordered_sha256'] = sha(('\n'.join(mapped)+'\n').encode('ascii'))
            out['identities']['histogram_sha256'] = digest(counts)
            shots_ok = len(raw_shots) == r['shots']
            counts_ok = counts == pack['counts']
            result_ok = derived == pack['result']
            out['deterministic_verification'] = 'SATISFIED' if shots_ok and counts_ok and result_ok else 'REFUTED'
            if not shots_ok: out['reasons'].append('SHOT_COUNT_MISMATCH')
            if not counts_ok: out['reasons'].append('COUNTS_MISMATCH')
            if not result_ok: out['reasons'].append('RESULT_MISMATCH')
        try:
            sources = adapters.verify_sources()
            out['source_provenance'] = {'status': 'BYTE_PINS_VALID', 'sources': sources}
            producer, consumer = declarations('request:'+digest(req)+'/postprocessing', pack['desired_claim'])
        except (adapters.AdapterUnavailable, OSError) as exc:
            out['source_provenance'] = {'status': 'UNAVAILABLE', 'reason': type(exc).__name__}
            out['native_link'] = {'status': 'UNAVAILABLE'}
        else:
            try:
                native = adapters.run_semantic_link(producer, consumer)
            except Exception as exc:
                # Adapter availability is not loss of the already verified source pins.
                out['native_link'] = {'status':'UNAVAILABLE','reason':type(exc).__name__}
            else:
                native_status=native_result_status(native,producer,consumer)
                out['native_link']={'status':native_status,'producer':producer,'consumer':consumer,
                                    'meaning':'DECLARATION_COMPATIBILITY_ONLY'}
                # Preserve serializable diagnostics, not arbitrary Python test-double objects.
                try:
                    encoded=canonical(native)
                    if len(encoded)<=262144: out['native_link']['result']=native
                    else: out['native_link']['status']='MALFORMED'
                except (TypeError,ValueError,RecursionError):
                    out['native_link']['status']='MALFORMED'
                if out['native_link']['status']=='MALFORMED': out['native_link']['reason']='NATIVE_RESULT_CONTRACT'
        if pack['desired_claim'] != CLAIM:
            out['input_status'] = 'UNSUPPORTED'
            out['reasons'].append('CLAIM_ELEVATION_UNSUPPORTED')
        if (out['input_status'] == 'VALID' and bound and out['integrity'] == 'SATISFIED'
                and out['deterministic_verification'] == 'SATISFIED'):
            out['claim_support'] = 'ESTABLISHED_OVER_SUPPLIED_BYTES'
        return out
    except InputError as exc:
        out['input_status'] = exc.category
        out['reasons'].append(exc.reason)
        return out

def read_input(relative):
    require(type(relative) is str and relative != '' and '\\' not in relative and ':' not in relative, 'UNSAFE_PATH')
    parts = relative.split('/')
    require(all(p not in ('', '.', '..') for p in parts), 'UNSAFE_PATH')
    root = Path.cwd().resolve()
    path = root.joinpath(*parts)
    require(path.resolve().is_relative_to(root), 'UNSAFE_PATH')
    for parent in [path, *path.parents]:
        if parent == root: break
        require(not parent.is_symlink(), 'UNSAFE_PATH')
    require(path.is_file(), 'INPUT_NOT_FILE')
    with path.open('rb') as f:
        data = f.read(MAX_BYTES+1)
    require(len(data) <= MAX_BYTES, 'INPUT_SIZE_LIMIT')
    return data
