"""Structural admission for finite experiment data; never imported by checker.py."""
import hashlib
import json
from pathlib import Path
import re
from . import inventory as fixed

class AdmissionError(ValueError):
    def __init__(self, reason, status='INVENTORY_INVALID'):
        self.reason, self.status = reason, status
        super().__init__(reason)

def need(condition, reason):
    if not condition: raise AdmissionError(reason)

def status(exc=None):
    return {'status':'ADMITTED' if exc is None else exc.status,
            'reason':'COMPLETE_UNIQUE_FINITE_INVENTORY' if exc is None else exc.reason}

def fields(obj, keys):
    need(type(obj) is dict and set(obj)==set(keys.split()), 'CLOSED_OBJECT_FIELDS')

def strict_json(data):
    need(type(data) is bytes and len(data)<=1048576, 'JSON_SIZE_LIMIT')
    def pairs(items):
        obj={}
        for key,value in items:
            need(key not in obj, 'DUPLICATE_JSON_KEY'); obj[key]=value
        return obj
    def integer(value):
        need(len(value)<=12, 'INTEGER_TOKEN_LIMIT'); return int(value)
    def reject(_): raise AdmissionError('FLOAT_OR_NONFINITE')
    try:
        text=data.decode('utf-8')
        depth=0; quoted=False; escaped=False
        for char in text:
            if quoted:
                if escaped: escaped=False
                elif char=='\\': escaped=True
                elif char=='"': quoted=False
            elif char=='"': quoted=True
            elif char in '[{':
                depth+=1; need(depth<=20,'JSON_DEPTH_LIMIT')
            elif char in ']}': depth-=1
        return json.loads(text,object_pairs_hook=pairs,parse_int=integer,parse_float=reject,parse_constant=reject)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AdmissionError('MALFORMED_JSON') from exc

def read_json(path):
    try:
        with Path(path).open('rb') as stream: data=stream.read(1048577)
    except OSError as exc:
        raise AdmissionError('INVENTORY_FILE_UNAVAILABLE','EVIDENCE_UNAVAILABLE') from exc
    return strict_json(data)

def complete_unique(values, required, reason):
    need(type(values) is list and all(type(v) is str for v in values),reason+'_TYPE')
    need(len(values)==len(required) and len(set(values))==len(values) and set(values)==set(required),reason+'_COMPLETE_UNIQUE')

def hash_string(value, length=64):
    need(type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None,'HASH_FORMAT')

def identity_fields(row):
    hash_string(row['sha256']); hash_string(row['git_blob_sha1'],40)
    need(type(row['size_bytes']) is int and 0<=row['size_bytes']<=4194304,'BYTE_LENGTH_TYPE_RANGE')

def expectation(obj):
    fields(obj,'input_status request_binding integrity deterministic_verification claim_support native_link_valid')
    enums={'input_status':('VALID','INVALID','UNSUPPORTED'),
           'request_binding':('SATISFIED','REFUTED','CANNOT_ESTABLISH'),
           'integrity':('SATISFIED','REFUTED','CANNOT_ESTABLISH'),
           'deterministic_verification':('SATISFIED','REFUTED','CANNOT_ESTABLISH'),
           'claim_support':('ESTABLISHED_OVER_SUPPLIED_BYTES','NOT_ESTABLISHED')}
    for key,allowed in enums.items(): need(type(obj[key]) is str and obj[key] in allowed,'EXPECTED_VALUE')
    need(obj['native_link_valid'] is None or type(obj['native_link_valid']) is bool,'EXPECTED_LINK_TYPE')

def positive_signature(obj):
    # A control must actually assert success on every required local/link axis.
    return (obj['input_status']=='VALID' and obj['native_link_valid'] is True
            and obj['claim_support']=='ESTABLISHED_OVER_SUPPLIED_BYTES'
            and all(obj[k]=='SATISFIED' for k in ('request_binding','integrity','deterministic_verification')))

def validate_manifest(manifest):
    fields(manifest,'cases controls expectation_authorship manual_arithmetic marker')
    need(manifest['marker']=='SYNTHETIC' and manifest['expectation_authorship']=='SAME_TASK_AUTHOR_NOT_INDEPENDENT','MANIFEST_IDENTITY')
    fields(manifest['manual_arithmetic'],'sample-a sample-b')
    need(all(type(v) is str and 0<len(v)<256 for v in manifest['manual_arithmetic'].values()),'ARITHMETIC_NOTE_TYPE')
    complete_unique(manifest['controls'],fixed.CONTROL_IDS,'CONTROLS')
    need(type(manifest['cases']) is list,'CASES_TYPE')
    pins={name:(sha,size) for name,sha,size in fixed.CORPUS_FILES}
    identifiers=[]
    for row in manifest['cases']:
        fields(row,'id marker request package request_sha256 package_sha256 expected')
        need(type(row['id']) is str and row['id'] in fixed.CASE_IDS,'CASE_ID')
        identifiers.append(row['id']); need(row['marker']=='SYNTHETIC','CASE_MARKER')
        expectation(row['expected'])
        for kind in ('request','package'):
            need(row[kind]==row['id']+'.'+kind+'.json','CASE_FILE_BINDING')
            hash_string(row[kind+'_sha256'])
            need(row[kind+'_sha256']==pins[row[kind]][0],'CASE_DECLARED_PIN')
        if row['id'] in fixed.CONTROL_IDS:
            need(positive_signature(row['expected']),'CONTROL_EXPECTATION_NOT_POSITIVE')
    complete_unique(identifiers,fixed.CASE_IDS,'CASES')

def validate_loaded(manifest,cases):
    validate_manifest(manifest)
    need(type(cases) is list,'LOADED_CASES_TYPE')
    need(len(cases)==len(fixed.CASE_IDS),'LOADED_CASES_COUNT')
    expected_rows={row['id']:row for row in manifest['cases']}
    names=[]; pins={name:(sha,size) for name,sha,size in fixed.CORPUS_FILES}
    for item in cases:
        need(type(item) in (tuple,list) and len(item)==3,'LOADED_CASE_TYPE')
        row,req,pack=item
        need(type(row) is dict and type(row.get('id')) is str and row['id'] in expected_rows,'LOADED_CASE_ID')
        need(row==expected_rows[row['id']],'LOADED_ROW_BINDING'); names.append(row['id'])
        for kind,data in (('request',req),('package',pack)):
            need(type(data) is bytes,'LOADED_BYTES_TYPE')
            sha,size=pins[row[kind]]
            if len(data)!=size or hashlib.sha256(data).hexdigest()!=sha:
                raise AdmissionError('CORPUS_BYTES_MISMATCH','EVIDENCE_MISMATCH')
    complete_unique(names,fixed.CASE_IDS,'LOADED_CASES')

def validate_mutations(configured):
    need(type(configured) in (list,tuple),'MUTATIONS_TYPE')
    ids=[]; expected={r[0]:r for r in fixed.MUTATION_OBLIGATIONS}
    for row in configured:
        need(type(row) in (list,tuple) and len(row)==6 and all(type(v) is str for v in row),'MUTATION_RECORD_TYPE')
        ids.append(row[0]); need(row[0] in expected and tuple(row)==expected[row[0]],'MUTATION_OBLIGATION_BINDING')
    complete_unique(ids,tuple(expected),'MUTATIONS')

def validate_lock(lock):
    from .source_lock import validate_lock as validate, SourceError
    try: validate(lock)
    except SourceError as exc: raise AdmissionError(exc.reason, exc.status) from exc
