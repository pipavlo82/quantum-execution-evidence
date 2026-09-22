"""Test/demo runner only: expected values never enter the production checker."""
from pathlib import Path
from . import checker, admission, inventory

ROOT = Path(__file__).resolve().parents[1] / 'fixtures'

def load_cases():
    manifest = admission.read_json(ROOT/'manifest.json')
    admission.validate_manifest(manifest)
    cases=[]
    for row in manifest['cases']:
        data=[]
        for key in ('request','package'):
            path=ROOT/'corpus'/row[key]
            admission.need(path.resolve().is_relative_to((ROOT/'corpus').resolve()) and not path.is_symlink(),'CORPUS_PATH')
            try:
                with path.open('rb') as stream: data.append(stream.read(checker.MAX_BYTES+1))
            except OSError as exc:
                raise admission.AdmissionError('CORPUS_FILE_UNAVAILABLE','EVIDENCE_UNAVAILABLE') from exc
        req,pack=data
        cases.append((row,req,pack))
    admission.validate_loaded(manifest,cases)
    return manifest,cases

def projection(result):
    native=result['native_link'].get('result')
    valid=native.get('valid') if type(native) is dict else None
    return {**{key:result[key] for key in ('input_status','request_binding','integrity','deterministic_verification','claim_support')},
            'native_link_valid':valid if type(valid) is bool else None}

def report():
    try:
        manifest,cases=load_cases()
        admission.validate_loaded(manifest,cases)
    except admission.AdmissionError as exc:
        return {'marker':'SYNTHETIC','profile':checker.PROFILE,'admission':admission.status(exc),
                'summary':{'cases':0,'matched':0,'failed':0,'positive_controls':0},'pairs':{},'runs':[]}
    rows=[]
    for row,req,pack in cases:
        actual=checker.verify(req,pack)
        rows.append({'id':row['id'],'result':actual,'expected':row['expected'],'matched':projection(actual)==row['expected']})
    by_id={r['id']:r['result'] for r in rows}
    a,b,c,d=(by_id[n] for n in ('sample-a','sample-b','shot-order','bit-permutation'))
    pairs={'different_valid_samples':a['recomputed']!=b['recomputed'] and all(v['deterministic_verification']=='SATISFIED' for v in (a,b)),
           'order_histogram_equal':a['identities']['histogram_sha256']==c['identities']['histogram_sha256'],
           'order_identity_different':a['identities']['ordered_raw_sha256']!=c['identities']['ordered_raw_sha256'],
           'permutation_canonical_order_equal':a['identities']['canonical_ordered_sha256']==d['identities']['canonical_ordered_sha256'],
           'weak_projection_equal_protected_binding_refuted':a['recomputed']==by_id['weak-projection']['recomputed'] and by_id['weak-projection']['request_binding']=='REFUTED'}
    return {'marker':'SYNTHETIC','profile':checker.PROFILE,'admission':admission.status(),'expectation_authorship':manifest['expectation_authorship'],
            'summary':{'cases':len(rows),'matched':sum(r['matched'] for r in rows),'failed':sum(not r['matched'] for r in rows),'positive_controls':len(manifest['controls'])},
            'pairs':pairs,'runs':rows}

def successful(report):
    if report.get('admission',{}).get('status')!='ADMITTED': return False
    rows=report.get('runs',[])
    if len(rows)!=len(inventory.CASE_IDS): return False
    ids=[row.get('id') for row in rows]
    if len(set(ids))!=len(ids) or set(ids)!=set(inventory.CASE_IDS): return False
    return (report['summary']=={'cases':44,'matched':44,'failed':0,'positive_controls':5}
            and all(row['matched'] is True for row in rows)
            and len(report.get('pairs',{}))==5 and all(v is True for v in report['pairs'].values()))
