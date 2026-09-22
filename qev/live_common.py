"""Bounded offline input boundary for live-capture replay v1."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE = 'profiles/live-capture-replay-v1'
MAX_BYTES = 4_194_304
ROLES = (
    'submission-intent.json', 'job-receipt.json', 'logical.json',
    'isa-submitted.json', 'isa-returned.json', 'provider-submission.normalized.json',
    'ibm-live-record.normalized.json', 'measurements-ordered.c1c0.txt',
    'measurement-counts.json', 'measurement-metadata.json',
    'normalization-provenance.json', 'provider-input-comparison.json',
    'job-metrics.json', 'isa-submitted.qasm3', 'logical.qasm3',
)
ANCHORS = ('submission-intent.json', 'job-receipt.json', 'logical.json',
           'isa-submitted.json', 'measurements-ordered.c1c0.txt')


class Rejected(ValueError):
    pass


class CannotRecompute(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Rejected(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + '\n').encode('utf-8')


def physical_bytes(value):
    # Exactly the recorded qev.provider_binding.canonical serialization surface.
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('utf-8')


def json_same(left, right):
    """Type-sensitive JSON comparison; booleans never equal numeric 0 or 1.

    This is an admission comparison, not a replacement for native RVR or
    ReceiptOS canonicalization/root calculation.
    """
    return physical_bytes(left) == physical_bytes(right)


def parse(data):
    need(type(data) is bytes and len(data) <= MAX_BYTES, 'INPUT_SIZE')
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'DUPLICATE_KEY')
            out[key] = value
        return out
    def invalid(_):
        raise Rejected('NONFINITE')
    # Bound depth before the JSON decoder recurses, respecting string escapes.
    depth = 0
    quoted = escaped = False
    for char in data:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            need(depth <= 32, 'INPUT_DEPTH')
        elif char in (93, 125):
            depth -= 1
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise Rejected(str(exc)) from exc
    def walk(item):
        if type(item) is str:
            need(len(item) <= MAX_BYTES and not any(0xD800 <= ord(c) <= 0xDFFF for c in item), 'STRING')
        elif type(item) is float:
            need(math.isfinite(item), 'NONFINITE')
        elif type(item) is int:
            need(abs(item) <= 2**53 - 1, 'INTEGER_RANGE')
        elif type(item) is list:
            need(len(item) <= 16384, 'ARRAY_SIZE')
            for child in item:
                walk(child)
        elif type(item) is dict:
            need(len(item) <= 1024, 'OBJECT_SIZE')
            for key, child in item.items():
                walk(key)
                walk(child)
    walk(value)
    return value


def fields(obj, names):
    need(type(obj) is dict and set(obj) == set(names), 'CLOSED_FIELDS')


def shape(obj, spec):
    if type(spec) is str:
        kinds = {'str': str, 'int': int, 'bool': bool, 'float': float}
        need(spec in kinds and type(obj) is kinds[spec], 'STRICT_TYPE_' + spec)
    elif type(spec) is list:
        need(type(obj) is list, 'ARRAY_TYPE')
        if not spec:
            need(not obj, 'EMPTY_ARRAY_REQUIRED')
        else:
            for item in obj:
                shape(item, spec[0])
    else:
        need(type(obj) is dict, 'OBJECT_TYPE')
        if set(spec) == {'*'}:
            for value in obj.values():
                shape(value, spec['*'])
        else:
            fields(obj, spec)
            for key in spec:
                shape(obj[key], spec[key])


def safe_file(root, relative):
    need(type(relative) is str and '\\' not in relative and ':' not in relative,
         'PATH_FORMAT')
    parts = relative.split('/')
    need(all(p not in ('', '.', '..') for p in parts), 'PATH_ESCAPE')
    root = Path(root).absolute()
    path = root.joinpath(*parts)
    # Inspect every ancestor, including root: also rejects directory junctions.
    for entry in (path, *path.parents):
        need(not entry.is_symlink() and not entry.is_junction(), 'PATH_SYMLINK')
    need(path.resolve().is_relative_to(root.resolve()), 'PATH_ESCAPE')
    return path


def read(root, relative):
    path = safe_file(root, relative)
    need(path.stat().st_size <= MAX_BYTES, 'INPUT_SIZE')
    return path.read_bytes()


def validate_claim(claim):
    fields(claim, ('schema', 'jobId', 'backend', 'requestId', 'shots', 'anchors',
                   'captureOrigin', 'providerAuthentication', 'angleMap'))
    need(claim['schema'] == 'qev.live-claim.v1', 'CLAIM_SCHEMA')
    for key in ('jobId', 'backend', 'requestId'):
        need(type(claim[key]) is str and 0 < len(claim[key]) <= 200, 'CLAIM_TOKEN')
    need(type(claim['shots']) is str and 1 <= len(claim['shots']) <= 4
         and claim['shots'].isascii() and claim['shots'].isdecimal()
         and 1 <= int(claim['shots']) <= 4096, 'CLAIM_SHOTS')
    fields(claim['anchors'], ANCHORS)
    for value in claim['anchors'].values():
        need(type(value) is str and len(value) == 64
             and all(c in '0123456789abcdef' for c in value), 'CLAIM_DIGEST')
    need(claim['captureOrigin'] == 'LIVE_IBM_RUNTIME_API', 'CLAIM_ORIGIN')
    need(claim['providerAuthentication'] == 'NOT_ESTABLISHED', 'CLAIM_AUTHENTICATION')
    need(claim['angleMap'] == 'qev-ideal-angle-literals-v1', 'ANGLE_MAP_ID')
