"""Fixture authoring only. Explicit hand-derived outcomes; NOT author-independent.

Does not import/call the production verifier to predict any expectation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'fixtures'

def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def digest(v): return hashlib.sha256(canonical(v)).hexdigest()

def seal(p):
    p['payload_sha256'] = digest({k:v for k,v in p.items() if k != 'payload_sha256'})
    return p

def request():
    return {'marker':'SYNTHETIC', 'request_id':'local-request-1', 'program':{'codec':'qev-lines.v0', 'source':'H 0\nCX 0 1\nRZ 1 theta_quarters\nMEASURE_ALL\n'},
            'parameters':{'theta_quarters':1}, 'width':2, 'shots':8, 'source_to_output':[0,1],
            'endianness':'source-index-ascending', 'provider':'synthetic-provider', 'backend':'offline-sample-table', 'job':'local-job-1'}

def package():
    r = request()
    raw = '00\n01\n11\n01\n10\n00\n11\n01\n'
    return seal({'marker':'SYNTHETIC', 'profile':'quantum-evidence.v0', 'hash_algorithm':'sha256', 'json_codec':'qev-json.v0',
                 'request':r, 'request_sha256':digest(r), 'raw':{'codec':'ascii-bit-lines-lf.v0','data':raw,'sha256':hashlib.sha256(raw.encode()).hexdigest()},
                 'output_to_raw':[0,1], 'counts':{'00':2,'01':3,'10':1,'11':2}, 'postprocessor':'integer-score-parity.v0',
                 'result':{'shots':8,'weighted_sum':13,'parity_ones':4}, 'claimed_execution':'SYNTHETIC',
                 'provider_evidence':None, 'desired_claim':'FINITE_POSTPROCESSING'})

def build():
    corpus = ROOT/'corpus'
    corpus.mkdir(exist_ok=True)
    rows = []
    positive = ['sample-a','sample-b','shot-order','bit-permutation','key-order']
    def add(name, p=None, r=None, expected=None, raw_bytes=None):
        p = package() if p is None else p
        r = request() if r is None else r
        reqpath, packpath = corpus/(name+'.request.json'), corpus/(name+'.package.json')
        reqpath.write_bytes(canonical(r)+b'\n')
        packpath.write_bytes(canonical(p)+b'\n' if raw_bytes is None else raw_bytes)
        expectation = {'input_status':'VALID','request_binding':'SATISFIED','integrity':'SATISFIED','deterministic_verification':'SATISFIED',
                       'claim_support':'ESTABLISHED_OVER_SUPPLIED_BYTES','native_link_valid':True}
        expectation.update(expected or {})
        rows.append({'id':name,'marker':'SYNTHETIC','request':reqpath.name,'package':packpath.name,'expected':expectation,
                     'request_sha256':hashlib.sha256(reqpath.read_bytes()).hexdigest(), 'package_sha256':hashlib.sha256(packpath.read_bytes()).hexdigest()})
    def raw_change(p, data):
        p['raw']['data'] = data
        p['raw']['sha256'] = hashlib.sha256(data.encode()).hexdigest()
        return seal(p)
    add('sample-a')
    p = package(); p['counts']={'00':1,'01':1,'10':4,'11':2}; p['result']={'shots':8,'weighted_sum':12,'parity_ones':5}
    add('sample-b',raw_change(p,'00\n10\n10\n11\n01\n10\n11\n10\n'))
    p=package(); add('shot-order',raw_change(p,'\n'.join(reversed(p['raw']['data'][:-1].split('\n')))+'\n'))
    p=package(); p['output_to_raw']=[1,0]; add('bit-permutation',raw_change(p,'\n'.join(b[::-1] for b in p['raw']['data'][:-1].split('\n'))+'\n'))
    p=package(); p['counts']=dict(reversed(list(p['counts'].items())))
    add('key-order',p,raw_bytes=(json.dumps(p,indent=1)+'\n').encode())
    for name, field, value in [('source-swap','program',{'codec':'qev-lines.v0','source':'X 0\nMEASURE_ALL\n'}),
                                ('parameters-swap','parameters',{'theta_quarters':2}),('mapping-swap','source_to_output',[1,0]),
                                ('provider-swap','provider','other-provider'),('backend-swap','backend','other-backend'),
                                ('job-swap','job','other-job'),('request-id-swap','request_id','other-request')]:
        p=package(); p['request'][field]=value; p['request_sha256']=digest(p['request']); seal(p)
        e={'request_binding':'REFUTED','claim_support':'NOT_ESTABLISHED'}
        if field=='source_to_output': e['deterministic_verification']='REFUTED'
        add(name,p,expected=e)
    # Same histogram and integer projection as A; protected job relation differs.
    p=package(); p['request']['job']='unrelated-job'; p['request_sha256']=digest(p['request'])
    add('weak-projection',seal(p),expected={'request_binding':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    p=package(); p['request']['width']=3; p['request']['source_to_output']=[0,1,2]; p['output_to_raw']=[0,1,2]
    p['request_sha256']=digest(p['request']); p['counts']={'000':8}; p['result']={'shots':8,'weighted_sum':0,'parity_ones':0}
    add('width-swap',raw_change(p,'000\n'*8),expected={'request_binding':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    p=package(); p['request']['shots']=9; p['request_sha256']=digest(p['request'])
    add('shots-mismatch',seal(p),r=p['request'],expected={'deterministic_verification':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    for name, change in [('counts-corrupt',lambda p:p['counts'].update({'00':3,'01':2})),
                         ('result-corrupt',lambda p:p['result'].update(weighted_sum=14)),
                         ('mapping-corrupt',lambda p:p.update(output_to_raw=[1,0]))]:
        p=package(); change(p); add(name,seal(p),expected={'deterministic_verification':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    for name, key in [('raw-digest','raw'),('request-digest','request_sha256')]:
        p=package()
        if key=='raw': p['raw']['sha256']='0'*64
        else: p[key]='0'*64
        add(name,seal(p),expected={'integrity':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    p=package(); p['payload_sha256']='0'*64
    add('package-digest',p,expected={'integrity':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    p=package(); p['raw']['data']=p['raw']['data'].replace('00','10',1)
    add('raw-corrupt',seal(p),expected={'integrity':'REFUTED','deterministic_verification':'REFUTED','claim_support':'NOT_ESTABLISHED'})
    p=package(); p['raw']=None
    add('missing-raw',seal(p),expected={'deterministic_verification':'CANNOT_ESTABLISH','claim_support':'NOT_ESTABLISHED'})
    for execution in ('SIMULATOR','QPU'):
        p=package(); p['claimed_execution']=execution; add('label-'+execution.lower(),seal(p))
    p=package(); p['provider_evidence']={'kind':'UNVERIFIED_TEXT','text':'SYNTHETIC supplied assertion, no signature'}
    add('unverified-provider',seal(p))
    for claim in ('AUTHENTIC_QPU_EXECUTION','SAMPLER_INDEPENDENCE','DISTRIBUTION_EQUALITY','MIN_ENTROPY','CRYPTOGRAPHIC_RNG','DEVICE_CERTIFICATION'):
        p=package(); p['desired_claim']=claim
        add('elevate-'+claim.lower(),seal(p),expected={'input_status':'UNSUPPORTED','claim_support':'NOT_ESTABLISHED','native_link_valid':False})
    for name, change, status in [
        ('boolean-count',lambda p:p['counts'].update({'00':True}),'INVALID'),
        ('negative-count',lambda p:p['counts'].update({'00':-1}),'INVALID'),
        ('float-count',lambda p:p['counts'].update({'00':2.0}),'INVALID'),
        ('out-of-range-bits',lambda p:p['counts'].update({'20':1}),'INVALID'),
        ('postprocessor',lambda p:p.update(postprocessor='eval-expression.v1'),'UNSUPPORTED'),
        ('codec',lambda p:p['raw'].update(codec='base64'),'UNSUPPORTED'),
        ('endianness',lambda p:p['request'].update(endianness='little'),'UNSUPPORTED'),
        ('expression',lambda p:p['request']['program'].update(source='eval(1+1)\nMEASURE_ALL\n'),'UNSUPPORTED'),
        ('path-reference',lambda p:p.update(raw_ref='../secret'),'INVALID'),
        ('expected-injection',lambda p:p.update(expected='SATISFIED'),'INVALID'),
    ]:
        p=package(); change(p)
        add(name,p,expected={'input_status':status,'request_binding':'CANNOT_ESTABLISH','integrity':'CANNOT_ESTABLISH',
                            'deterministic_verification':'CANNOT_ESTABLISH','claim_support':'NOT_ESTABLISHED','native_link_valid':None})
    invalid={'input_status':'INVALID','request_binding':'CANNOT_ESTABLISH','integrity':'CANNOT_ESTABLISH',
             'deterministic_verification':'CANNOT_ESTABLISH','claim_support':'NOT_ESTABLISHED','native_link_valid':None}
    add('duplicate-key',raw_bytes=canonical(package())[:-1]+b',"marker":"SYNTHETIC"}\n',expected=invalid)
    add('nonfinite',raw_bytes=canonical(package()).replace(b'"00":2',b'"00":NaN'),expected=invalid)
    manifest={'marker':'SYNTHETIC','expectation_authorship':'SAME_TASK_AUTHOR_NOT_INDEPENDENT', 'controls':positive,'cases':rows,
              'manual_arithmetic':{'sample-a':'2*0+3*2+1*1+2*3=13; odd parity 3+1=4', 'sample-b':'1*0+1*2+4*1+2*3=12; odd parity 1+4=5'}}
    (ROOT/'manifest.json').write_bytes(json.dumps(manifest,indent=2,sort_keys=True).encode()+b'\n')
    return len(rows)

if __name__=='__main__': print(build())
