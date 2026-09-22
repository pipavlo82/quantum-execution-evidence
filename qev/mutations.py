"""Actual source mutations; no disk mutation, expected-answer lookup or fake kills."""
from collections import Counter
from . import checker, corpus, admission, inventory

MUTATIONS = [
 ('M1_REQUEST_BINDING','bound = pack[\'request\'] == req','bound = True','source-swap','request_binding','SATISFIED'),
 ('M2_REQUEST_DIGEST','request_hash_ok = digest(pack[\'request\']) == pack[\'request_sha256\']','request_hash_ok = True','request-digest','integrity','SATISFIED'),
 ('M3_RAW_DIGEST',"raw_ok = pack['raw'] is None or sha(pack['raw']['data'].encode('ascii')) == pack['raw']['sha256']",'raw_ok = True','raw-digest','integrity','SATISFIED'),
 ('M4_PACKAGE_DIGEST',"package_ok = digest(payload) == pack['payload_sha256']",'package_ok = True','package-digest','integrity','SATISFIED'),
 ('M5_SHOTS',"shots_ok = len(raw_shots) == r['shots']",'shots_ok = True','shots-mismatch','deterministic_verification','SATISFIED'),
 ('M6_COUNTS',"counts_ok = counts == pack['counts']",'counts_ok = True','counts-corrupt','deterministic_verification','SATISFIED'),
 ('M7_RESULT',"result_ok = derived == pack['result']",'result_ok = True','result-corrupt','deterministic_verification','SATISFIED'),
]
STATUSES=('KILLED','SURVIVED','CRASHED','NOT_APPLIED','VACUOUS','CONTROL_BROKEN','BASELINE_FAILED')

def classify(applied, crashed, controls_ok, baseline_ok, changed, semantic):
    if not applied: return 'NOT_APPLIED'
    if crashed: return 'CRASHED'
    if not baseline_ok: return 'BASELINE_FAILED'
    if not controls_ok: return 'CONTROL_BROKEN'
    if not changed: return 'SURVIVED'
    if not semantic: return 'VACUOUS'
    return 'KILLED'

def run():
    try:
        admission.validate_mutations(MUTATIONS)
        manifest,cases=corpus.load_cases()
        admission.validate_loaded(manifest,cases)
    except admission.AdmissionError as exc:
        return rejected(exc)
    inputs={r['id']:(req,pack) for r,req,pack in cases}
    expectations={r['id']:r['expected'] for r,req,pack in cases}
    try:
        baseline={name:checker.verify(*data) for name,data in inputs.items()}
    except Exception as exc:
        return rejected(admission.AdmissionError('BASELINE_EXCEPTION_'+type(exc).__name__,'BASELINE_FAILED'))
    baseline_ok=all(corpus.projection(res)==expectations[name] for name,res in baseline.items())
    controls_ok=all(admission.positive_signature(corpus.projection(baseline[cid])) for cid in inventory.CONTROL_IDS)
    if not baseline_ok or not controls_ok:
        return rejected(admission.AdmissionError('BASELINE_EXPECTATIONS_OR_POSITIVE_CONTROLS','BASELINE_FAILED'))
    try: source=__import__('pathlib').Path(checker.__file__).read_bytes()
    except OSError:
        return rejected(admission.AdmissionError('CHECKER_SOURCE_UNAVAILABLE','EVIDENCE_UNAVAILABLE'))
    text=source.decode()
    rows=[]
    for name,old,new,killer,axis,target in MUTATIONS:
        applied=text.count(old)==1
        row={'id':name,'killer':killer,'axis':axis,'target':target,'applied':applied,'controls':{},'baseline':baseline[killer]}
        if not applied:
            row['status']='NOT_APPLIED'; rows.append(row); continue
        mutated=text.replace(old,new,1)
        row['mutated_source_sha256']=checker.sha(mutated.encode())
        ns={'__file__':checker.__file__,'__name__':'quantum_source_mutant'}
        try:
            exec(compile(mutated,checker.__file__,'exec'),ns)
            row['controls']={cid:ns['verify'](*inputs[cid])==baseline[cid] for cid in manifest['controls']}
            actual=ns['verify'](*inputs[killer]); row['actual']=actual
            row['status']=classify(True,False,all(row['controls'].values()),baseline_ok,
                                    actual!=baseline[killer],actual[axis]==target and baseline[killer][axis]!=target)
        except Exception as exc:
            row['status']='CRASHED'; row['error']=type(exc).__name__
        rows.append(row)
    counts=Counter(r['status'] for r in rows)
    return {'marker':'SYNTHETIC','admission':admission.status(),'source_sha256':checker.sha(source),'expectation_authorship':'SAME_TASK_AUTHOR_NOT_INDEPENDENT',
            'positive_controls':manifest['controls'],'summary':{s:counts[s] for s in STATUSES},'mutations':rows}

def rejected(exc):
    return {'marker':'SYNTHETIC','admission':admission.status(exc),'positive_controls':[],
            'required_mutations':len(inventory.MUTATION_OBLIGATIONS),'summary':{s:0 for s in STATUSES},'mutations':[]}

def successful(report):
    if report.get('admission',{}).get('status')!='ADMITTED': return False
    required={row[0] for row in inventory.MUTATION_OBLIGATIONS}
    rows=report.get('mutations',[])
    if len(rows)!=len(required): return False
    ids=[r.get('id') for r in rows]
    if len(set(ids))!=len(ids) or set(ids)!=required: return False
    if report.get('summary')!={s:(len(required) if s=='KILLED' else 0) for s in STATUSES}: return False
    if (len(report.get('positive_controls',[]))!=len(inventory.CONTROL_IDS)
            or set(report['positive_controls'])!=set(inventory.CONTROL_IDS)): return False
    return all(row.get('status')=='KILLED' and row.get('applied') is True
               and set(row.get('controls',{}))==set(inventory.CONTROL_IDS)
               and all(v is True for v in row['controls'].values()) for row in rows)
