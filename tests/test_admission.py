"""Coordinator review regressions: real CLI, disposable inputs, no source corruption."""
from contextlib import contextmanager
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from qev import admission as a, checker as c, corpus, inventory as fixed, mutations, sources
from qev import __main__ as cli
from qev import source_inventory as pins

def invoke(args):
    output=io.BytesIO()
    with patch.object(sys,'argv',['qev',*args]),patch.object(sys,'stdout',SimpleNamespace(buffer=output)):
        code=cli.main()
    return code,json.loads(output.getvalue())

@contextmanager
def manifest_copy(change=None,raw=None):
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        root=Path(temp)
        shutil.copytree(corpus.ROOT/'corpus',root/'corpus')
        data=(corpus.ROOT/'manifest.json').read_bytes()
        obj=json.loads(data)
        if change: change(obj)
        (root/'manifest.json').write_bytes(raw if raw is not None else json.dumps(obj).encode())
        with patch.object(corpus,'ROOT',root): yield root

@contextmanager
def lock_copy(change=None,raw=None):
    data=sources.LOCK_PATH.read_bytes()
    obj=json.loads(data)
    if change: change(obj)
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
        target=Path(temp)
        (target/'sources.lock.json').write_bytes(raw if raw is not None else json.dumps(obj).encode())
        with patch.object(sources,'LOCK_PATH',target/'sources.lock.json'): yield target

class AdmissionTests(unittest.TestCase):
    def reject_manifest(self,change=None,raw=None,status='INVENTORY_INVALID'):
        with manifest_copy(change,raw),patch.object(c,'verify',side_effect=AssertionError('must not execute')) as evaluated:
            for command in ('demo','mutation-check'):
                code,out=invoke([command]); self.assertNotEqual(code,0)
                self.assertEqual(out['admission']['status'],status)
            self.assertEqual(evaluated.call_count,0)

    def reject_lock(self,change=None,raw=None):
        with lock_copy(change,raw),patch.object(sources,'verify_sources',side_effect=AssertionError('must not execute')) as upstream:
            code,out=invoke(['sources'])
            self.assertNotEqual(code,0); self.assertFalse(out['valid'])
            self.assertEqual(out['admission']['status'],'INVENTORY_INVALID')
            self.assertEqual(out['results'],[])
            self.assertEqual(upstream.call_count,0)

    def reject_mutations(self,configured):
        with patch.object(mutations,'MUTATIONS',configured),patch.object(c,'verify',side_effect=AssertionError('must not execute')) as evaluated:
            code,out=invoke(['mutation-check'])
            self.assertNotEqual(code,0); self.assertEqual(out['admission']['status'],'INVENTORY_INVALID')
            self.assertEqual(out['summary']['KILLED'],0); self.assertEqual(out['mutations'],[])
            self.assertEqual(evaluated.call_count,0)

    def test_review01_empty_mutations_cli(self): self.reject_mutations([])
    def test_mutations_wrong_container_types(self):
        for value in (None,{},'seven',7): self.reject_mutations(value)
    def test_each_mutation_obligation_is_required(self):
        for i in range(7): self.reject_mutations(mutations.MUTATIONS[:i]+mutations.MUTATIONS[i+1:])
    def test_duplicate_mutations_and_ids(self):
        self.reject_mutations(mutations.MUTATIONS+[mutations.MUTATIONS[0]])
        self.reject_mutations([mutations.MUTATIONS[0]]*7)
    def test_mutation_wrong_killer_axis_target_patch_or_type(self):
        for index in range(6):
            bad=deepcopy(mutations.MUTATIONS); row=list(bad[0]); row[index]='unexpected'; bad[0]=tuple(row)
            self.reject_mutations(bad)
        for value in ([],{},None,True): self.reject_mutations([value,*mutations.MUTATIONS[1:]])

    def test_review02_empty_controls_cli(self): self.reject_manifest(lambda m:m.update(controls=[]))
    def test_omitted_controls(self): self.reject_manifest(lambda m:m.pop('controls'))
    def test_each_control_required(self):
        for i in range(5): self.reject_manifest(lambda m,i=i:m['controls'].pop(i))
    def test_duplicate_controls(self): self.reject_manifest(lambda m:m['controls'].__setitem__(1,m['controls'][0]))
    def test_unknown_and_negative_control_ids(self):
        for cid in ('unknown','source-swap','missing-raw','label-qpu'):
            self.reject_manifest(lambda m,cid=cid:m['controls'].__setitem__(0,cid))
    def test_controls_wrong_type(self):
        for value in (None,{},'sample-a',[None]*5): self.reject_manifest(lambda m,v=value:m.update(controls=v))
    def test_negative_expected_cannot_masquerade_as_control(self):
        self.reject_manifest(lambda m:m['cases'][0]['expected'].update(deterministic_verification='REFUTED'))
    def test_negative_bytes_cannot_masquerade_as_control(self):
        with manifest_copy() as root,patch.object(c,'verify',side_effect=AssertionError('must not execute')) as evaluated:
            (root/'corpus/sample-a.package.json').write_bytes((root/'corpus/source-swap.package.json').read_bytes())
            code,out=invoke(['mutation-check'])
            self.assertNotEqual(code,0); self.assertEqual(out['admission']['status'],'EVIDENCE_MISMATCH')
            self.assertEqual(evaluated.call_count,0)
    def test_empty_cases(self): self.reject_manifest(lambda m:m.update(cases=[]))
    def test_each_case_required(self):
        for i in range(44): self.reject_manifest(lambda m,i=i:m['cases'].pop(i))
    def test_duplicate_case_records(self): self.reject_manifest(lambda m:m['cases'].__setitem__(1,deepcopy(m['cases'][0])))
    def test_case_wrong_types(self):
        for value in (None,{},'x',True): self.reject_manifest(lambda m,v=value:m['cases'].__setitem__(6,v))
    def test_cases_wrong_container(self): self.reject_manifest(lambda m:m.update(cases={}))
    def test_unknown_case(self): self.reject_manifest(lambda m:m['cases'][6].update(id='unregistered'))
    def test_case_file_binding_and_hash_types(self):
        for key,value in (('package','../x'),('request','sample-b.request.json'),('request_sha256','0'*64),('package_sha256',[])):
            self.reject_manifest(lambda m,k=key,v=value:m['cases'][0].update({k:v}))
    def test_manifest_unknown_fields_and_malformed(self):
        self.reject_manifest(lambda m:m.update(unknown=True)); self.reject_manifest(raw=b'{')
        self.reject_manifest(raw=b'[]')
    def test_manifest_duplicate_json_keys(self):
        raw=(corpus.ROOT/'manifest.json').read_bytes().rstrip()
        self.reject_manifest(raw=raw[:-1]+b',"controls":[]}')
    def test_expected_types_strict_including_bool_vs_integer(self):
        for key,value in (('native_link_valid',1),('input_status',True),('integrity',{}),('claim_support',None)):
            self.reject_manifest(lambda m,k=key,v=value:m['cases'][6]['expected'].update({k:v}))
    def test_missing_corpus_file_is_unavailable(self):
        with manifest_copy() as root:
            (root/'corpus/sample-b.request.json').unlink()
            code,out=invoke(['demo'])
            self.assertNotEqual(code,0); self.assertEqual(out['admission']['status'],'EVIDENCE_UNAVAILABLE')
    def test_noncontrol_expectation_tamper_blocks_all_mutant_execution(self):
        manifest,cases=deepcopy(corpus.load_cases())
        # deepcopy preserves shared row identity across these two containers.
        row=next(r for r in manifest['cases'] if r['id']=='source-swap')
        row['expected']['request_binding']='SATISFIED'
        with patch.object(corpus,'load_cases',return_value=(manifest,cases)):
            out=mutations.run()
        self.assertEqual(out['admission']['status'],'BASELINE_FAILED')
        self.assertEqual(out['mutations'],[]); self.assertEqual(out['summary']['KILLED'],0)
    def test_baseline_fault_cannot_masquerade_as_successful_positive(self):
        real=c.verify
        def fault(*args):
            out=real(*args); out['deterministic_verification']='REFUTED'; return out
        with patch.object(c,'verify',side_effect=fault): out=mutations.run()
        self.assertEqual(out['admission']['status'],'BASELINE_FAILED'); self.assertEqual(out['mutations'],[])

    def native(self,value=None,error=None,package='sample-a'):
        args=['verify','--request','fixtures/corpus/sample-a.request.json',f'fixtures/corpus/{package}.package.json']
        with patch.object(c.adapters,'run_semantic_link',side_effect=error,return_value=value): return invoke(args)
    def test_review03_native_rejection_nonzero_keeps_local_truth(self):
        code,out=self.native({'valid':False,'error':{'code':'COORDINATOR_NEGATIVE_CONTROL'}})
        self.assertEqual(code,4); self.assertEqual(out['native_link']['status'],'REJECTED')
        self.assertEqual(out['claim_support'],'ESTABLISHED_OVER_SUPPLIED_BYTES')
        self.assertEqual(out['deterministic_verification'],'SATISFIED')
        self.assertEqual(out['physical']['AUTHENTIC_QPU_EXECUTION'],'NOT_ESTABLISHED')
    def test_native_unavailable_preserves_byte_provenance_and_local_truth(self):
        code,out=self.native(error=c.adapters.AdapterUnavailable('controlled'))
        self.assertEqual(code,3); self.assertEqual(out['native_link']['status'],'UNAVAILABLE')
        self.assertEqual(out['source_provenance']['status'],'BYTE_PINS_VALID')
        self.assertEqual(out['claim_support'],'ESTABLISHED_OVER_SUPPLIED_BYTES')
    def test_malformed_native_results_nonzero_without_crash(self):
        for value in (None,[],True,{}, {'valid':1}, {'valid':'yes'}, {'valid':True}, {'valid':False},
                      {'valid':True,'edge':{}},{'valid':True,'edge':{'producer_claim':{},'consumer_requirement':{}}},
                      {'valid':False,'error':[]},{'valid':False,'error':'TYPE_ERROR','unknown':1},object()):
            code,out=self.native(value)
            self.assertEqual(code,5); self.assertEqual(out['native_link']['status'],'MALFORMED')
            self.assertEqual(out['claim_support'],'ESTABLISHED_OVER_SUPPLIED_BYTES')
    def test_native_wrong_edge_is_malformed(self):
        producer,consumer=c.declarations('wrong-request','FINITE_POSTPROCESSING')
        code,out=self.native({'valid':True,'edge':{'producer_claim':producer['establishes'][0],'consumer_requirement':consumer}})
        self.assertEqual(code,5); self.assertEqual(out['native_link']['status'],'MALFORMED')
    def test_unexpected_adapter_exception_is_structured_unavailable(self):
        code,out=self.native(error=RuntimeError('controlled'))
        self.assertEqual(code,3); self.assertEqual(out['native_link']['status'],'UNAVAILABLE')
    def test_native_fault_during_demo_is_conformance_failure_not_crash(self):
        with patch.object(c.adapters,'run_semantic_link',return_value=[]):
            code,out=invoke(['demo'])
        self.assertEqual(code,1); self.assertGreater(out['summary']['failed'],0)
    def test_contradiction_and_link_precedence_keeps_both_axes(self):
        code,out=self.native({'valid':False,'error':'TYPE_ERROR'},package='counts-corrupt')
        self.assertEqual(code,1); self.assertEqual(out['deterministic_verification'],'REFUTED')
        self.assertEqual(out['native_link']['status'],'REJECTED')
    def test_native_rejection_and_missing_evidence_remain_separate(self):
        code,out=self.native({'valid':False,'error':'TYPE_ERROR'},package='missing-raw')
        self.assertEqual(code,4); self.assertEqual(out['deterministic_verification'],'CANNOT_ESTABLISH')
    def test_normal_and_mirror_imports_still_succeed(self):
        for cid in fixed.CONTROL_IDS:
            code,out=invoke(['verify','--request',f'fixtures/corpus/{cid}.request.json',f'fixtures/corpus/{cid}.package.json'])
            self.assertEqual(code,0); self.assertEqual(out['native_link']['status'],'EXECUTED')

    def test_review04_empty_source_inventories_cli(self): self.reject_lock(lambda l:l.update(local_files=[],vendor_files=[]))
    def test_each_local_source_required(self):
        lock=json.loads(sources.LOCK_PATH.read_bytes())
        for i in range(len(lock['local_files'])):
            bad=deepcopy(lock); bad['local_files'].pop(i)
            with self.assertRaises(a.AdmissionError): a.validate_lock(bad)
        self.reject_lock(lambda l:l['local_files'].pop())
    def test_each_vendor_source_required(self):
        for i in range(len(pins.ALL_VENDOR_FILES)): self.reject_lock(lambda l,i=i:l['vendor_files'].pop(i))
    def test_duplicate_local_and_external_records(self):
        for key in ('local_files','vendor_files'):
            self.reject_lock(lambda l,k=key:l[k].__setitem__(1,deepcopy(l[k][0])))
    def test_source_lock_wrong_types_and_missing_fields(self):
        for key in ('local_files','vendor_files'):
            for val in (None,{},'list',[None]): self.reject_lock(lambda l,k=key,v=val:l.update({k:v}))
        self.reject_lock(lambda l:l.pop('local_files'))
    def test_source_record_hash_length_and_type_validation(self):
        for key,value in (('sha256','ABC'),('git_blob_sha1',[]),('size_bytes',True),('size_bytes',-1),('size_bytes',1.5),('path',{})):
            self.reject_lock(lambda l,k=key,v=value:l['local_files'][0].update({k:v}))
    def test_lock_metadata_and_allowlisted_fields(self):
        for key in ('format','boundary','self_digest'):
            self.reject_lock(lambda l,k=key:l.update({k:'wrong'}))
        self.reject_lock(lambda l:l.update(unknown=True))
        self.reject_lock(lambda l:l['local_files'][0].update(unknown=True))
    def test_external_reference_exact_binding_no_redirect(self):
        for key,value in (('commit','0'*40),('repository','other'),('path','../x'),('sha256','0'*64),('size_bytes',10)):
            self.reject_lock(lambda l,k=key,v=value:l['vendor_files'][0].update({k:v}))
    def test_lock_duplicate_json_keys_and_malformed(self):
        raw=sources.LOCK_PATH.read_bytes().rstrip()
        self.reject_lock(raw=raw[:-1]+b',"local_files":[]}')
        self.reject_lock(raw=b'{'); self.reject_lock(raw=b'[]')
    def test_wrong_local_digest_is_mismatch_not_inventory_or_availability(self):
        with lock_copy(lambda l:l['local_files'][0].update(sha256='0'*64)):
            code,out=invoke(['sources'])
        self.assertEqual(code,1); self.assertEqual(out['admission']['status'],'ADMITTED')
        self.assertEqual(out['evidence_status'],'EVIDENCE_MISMATCH')
    def test_missing_lock_is_unavailable_not_valid_empty(self):
        with lock_copy() as directory:
            (directory/'sources.lock.json').unlink(); code,out=invoke(['sources'])
        self.assertEqual(code,1); self.assertEqual(out['admission']['status'],'EVIDENCE_UNAVAILABLE')
    def test_declared_but_unavailable_sources_are_structured(self):
        with lock_copy() as directory,patch.object(sources,'ROOT',directory/'absent-worktree'):
            code,out=invoke(['sources'])
        self.assertEqual(code,1); self.assertEqual(out['admission']['status'],'ADMITTED')
        self.assertEqual(out['evidence_status'],'EVIDENCE_UNAVAILABLE')
    def test_success_predicates_reject_vacuous_reports(self):
        self.assertFalse(mutations.successful({'admission':{'status':'ADMITTED'},'summary':{s:0 for s in mutations.STATUSES},'mutations':[]}))
        self.assertFalse(corpus.successful({'admission':{'status':'ADMITTED'},'runs':[]}))
        self.assertFalse(sources.successful({'valid':True,'admission':{'status':'ADMITTED'},'evidence_status':'ADMITTED','results':[]}))
    def test_source_mismatch_not_erased_by_other_unavailable_evidence(self):
        name=pins.LOCAL_FILES[0]
        catalog=(sources.ROOT/name).read_bytes()
        with lock_copy(lambda l:l['local_files'][0].update(sha256='0'*64)) as directory:
            target=directory/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(catalog)
            with patch.object(sources,'ROOT',directory): code,out=invoke(['sources'])
        self.assertEqual(code,1); self.assertEqual(out['evidence_status'],'EVIDENCE_MISMATCH')
        self.assertIn('MISMATCH',[r['status'] for r in out['results']])
        self.assertIn('UNAVAILABLE',[r['status'] for r in out['results']])
    def test_bad_upstream_inventory_result_is_structured_unavailable(self):
        for value in (None,[],{},False):
            with patch.object(sources,'verify_sources',return_value=value): code,out=invoke(['sources'])
            self.assertEqual(code,1); self.assertEqual(out['evidence_status'],'EVIDENCE_UNAVAILABLE')
            self.assertEqual(out['vendor_status'],'UNAVAILABLE')
    def test_lock_generation_is_finite_and_reproducible(self):
        from tools.pin_lock import generate
        first=generate(); self.assertEqual(first,generate())
        a.validate_lock(a.strict_json(first))
        self.assertGreater(len(pins.LOCAL_FILES),100)

if __name__=='__main__': unittest.main()
