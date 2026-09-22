from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from qev import checker as c, corpus, mutations
from tools.build_corpus import package, request, seal, digest

class ProfileTests(unittest.TestCase):
    def check(self,p=None,r=None):
        return c.verify(c.canonical(request() if r is None else r),c.canonical(package() if p is None else p))

    def test_corpus_and_pair_relations(self):
        report=corpus.report()
        self.assertEqual(report['summary'],{'cases':44,'matched':44,'failed':0,'positive_controls':5})
        self.assertTrue(all(report['pairs'].values()))

    def test_manual_integer_answers(self):
        out=self.check()
        self.assertEqual(out['recomputed'],{'counts':{'00':2,'01':3,'10':1,'11':2},'result':{'shots':8,'weighted_sum':13,'parity_ones':4}})

    def test_native_link_preserved_and_explicit_elevation_boundary(self):
        p=package(); p['desired_claim']='AUTHENTIC_QPU_EXECUTION'
        out=self.check(seal(p))
        self.assertFalse(out['native_link']['result']['valid'])
        self.assertEqual(out['native_link']['result']['error'],'TYPE_ERROR')
        self.assertTrue(out['native_link']['result']['counterexample']['explicit_boundary_hit'])

    def test_all_physical_axes_never_elevate(self):
        _,cases=corpus.load_cases()
        for row,req,pack in cases:
            with self.subTest(case=row['id']):
                out=c.verify(req,pack)
                self.assertTrue(all(v in ('NOT_ESTABLISHED','NOT_EVALUATED') for v in out['physical'].values()))
                self.assertEqual(out['provider_authenticity'],'NOT_ESTABLISHED')
                self.assertNotIn('verified',out)

    def test_rewritten_package_does_not_replace_independent_request(self):
        for field,value in [('provider','evil'),('backend','evil'),('job','evil'),('parameters',{'theta_quarters':3}),('program',{'codec':'qev-lines.v0','source':'MEASURE_ALL\n'})]:
            with self.subTest(field=field):
                p=package(); p['request'][field]=value; p['request_sha256']=digest(p['request'])
                out=self.check(seal(p))
                self.assertEqual(out['integrity'],'SATISFIED')
                self.assertEqual(out['request_binding'],'REFUTED')
                self.assertEqual(out['claim_support'],'NOT_ESTABLISHED')

    def test_changing_both_inputs_explicitly_changes_trust_root(self):
        p=package(); p['request']['job']='other'; p['request_sha256']=digest(p['request'])
        out=self.check(seal(p),p['request'])
        self.assertEqual(out['request_binding'],'SATISFIED')
        self.assertEqual(out['provider_authenticity'],'NOT_ESTABLISHED')

    def test_missing_raw_is_unknown_not_refutation(self):
        p=package(); p['raw']=None
        out=self.check(seal(p))
        self.assertEqual(out['deterministic_verification'],'CANNOT_ESTABLISH')
        self.assertEqual(out['request_binding'],'SATISFIED')

    def test_corrupt_raw_remains_refuted_after_package_rehash(self):
        p=package(); p['raw']['data']=p['raw']['data'].replace('00','10',1)
        out=self.check(seal(p)); self.assertEqual(out['integrity'],'REFUTED')
        self.assertEqual(out['deterministic_verification'],'REFUTED')

    def test_request_mapping_and_representation_compose(self):
        p=package(); p['request']['source_to_output']=[1,0]; p['output_to_raw']=[1,0]
        p['request_sha256']=digest(p['request'])
        out=self.check(seal(p),p['request'])
        self.assertEqual(out['deterministic_verification'],'SATISFIED')
        self.assertEqual(out['recomputed']['result']['weighted_sum'],13)

    def test_width_eight_max_shots_exact_integer(self):
        p=package(); p['request'].update(width=8,shots=4096,source_to_output=list(range(8)))
        p['request_sha256']=digest(p['request']); p['output_to_raw']=list(range(8))
        p['raw']['data']='11111111\n'*4096; p['raw']['sha256']=c.sha(p['raw']['data'].encode())
        p['counts']={'11111111':4096}; p['result']={'shots':4096,'weighted_sum':147456,'parity_ones':0}
        self.assertEqual(self.check(seal(p),p['request'])['deterministic_verification'],'SATISFIED')

    def test_duplicate_keys_rejected_in_request_and_package(self):
        req=c.canonical(request()); pack=c.canonical(package())
        self.assertEqual(c.verify(req[:-1]+b',"width":2}',pack)['input_status'],'INVALID')
        self.assertEqual(c.verify(req,pack[:-1]+b',"marker":"SYNTHETIC"}')['input_status'],'INVALID')

    def test_floats_nonfinite_boolean_and_negative(self):
        for token in (b'true',b'false',b'2.0',b'NaN',b'Infinity',b'-Infinity',b'-1',b'0'):
            out=c.verify(c.canonical(request()),c.canonical(package()).replace(b'"00":2',b'"00":'+token))
            self.assertEqual(out['input_status'],'INVALID',token)

    def test_depth_size_integer_and_node_limits(self):
        for raw in (b'['*17+b'0'+b']'*17,b' '*262145,b'1234567890123',b'['+b'0,'*20000+b'0]'):
            with self.assertRaises(c.InputError): c.strict_load(raw)

    def test_raw_width_and_count_range(self):
        for raw in ('00\r\n','000\n','02\n','00\n\n','00','\ufeff00\n'):
            p=package(); p['raw']['data']=raw
            self.assertEqual(self.check(p)['input_status'],'INVALID')

    def test_malformed_type_matrix_no_crashes(self):
        p=package()
        for key in p:
            for value in (None,[],{},42):
                q=deepcopy(p); q[key]=value
                out=self.check(q)
                self.assertIn(out['input_status'],('INVALID','UNSUPPORTED','VALID'))
                if key not in ('raw','provider_evidence'): self.assertNotEqual(out['input_status'],'VALID')

    def test_closed_fields_do_not_execute_expressions(self):
        p=package(); p['request']['program']['source']='__import__("os")\nMEASURE_ALL\n'
        self.assertEqual(self.check(p)['input_status'],'UNSUPPORTED')
        p=package(); p['raw_ref']='https://example.invalid/raw'
        self.assertEqual(self.check(p)['input_status'],'INVALID')

    def test_unsafe_paths_rejected(self):
        for path in ('../x','/x','X'+':/x','a/../x','a//x','a/./x','a\\x','//server/share','a:b',''):
            with self.subTest(path=path), self.assertRaises(c.InputError): c.read_input(path)

    def test_file_input_size_is_bounded(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as directory:
            p=Path(directory)/'big.json'; p.write_bytes(b' '*262145)
            with self.assertRaises(c.InputError): c.read_input(p.relative_to(Path.cwd()).as_posix())

    def test_missing_node_is_availability_not_fabricated_link(self):
        with patch.object(c.adapters,'run_semantic_link',side_effect=c.adapters.AdapterUnavailable('missing')):
            out=self.check()
        self.assertEqual(out['native_link']['status'],'UNAVAILABLE')
        self.assertEqual(out['deterministic_verification'],'SATISFIED')

    def test_missing_source_is_availability(self):
        with patch.object(c.adapters,'verify_sources',side_effect=c.adapters.AdapterUnavailable('missing')):
            out=self.check()
        self.assertEqual(out['source_provenance']['status'],'UNAVAILABLE')
        self.assertEqual(out['native_link']['status'],'UNAVAILABLE')

    def test_checker_does_not_read_expectations(self):
        original=Path.read_bytes
        def guarded(path):
            self.assertNotIn(path.name,('manifest.json','expected.json'))
            self.assertNotEqual(path.parent.name,'corpus')
            return original(path)
        with patch.object(Path,'read_bytes',guarded):
            out=self.check()
        self.assertEqual(out['deterministic_verification'],'SATISFIED')

    def test_tampered_expectations_change_conformance_not_verification(self):
        manifest,cases=corpus.load_cases()
        before=c.verify(cases[0][1],cases[0][2])
        altered=deepcopy(cases)
        altered[0][0]['expected']['deterministic_verification']='REFUTED'
        with patch.object(corpus,'load_cases',return_value=(manifest,altered)):
            report=corpus.report()
            self.assertEqual(report['admission']['status'],'INVENTORY_INVALID')
            self.assertEqual(report['runs'],[])
        self.assertEqual(c.verify(cases[0][1],cases[0][2]),before)

    def test_tampered_expectations_cannot_create_mutation_kills(self):
        manifest,cases=corpus.load_cases(); altered=deepcopy(cases)
        altered[0][0]['expected']['deterministic_verification']='REFUTED'
        with patch.object(corpus,'load_cases',return_value=(manifest,altered)):
            report=mutations.run()
        self.assertEqual(report['admission']['status'],'INVENTORY_INVALID')
        self.assertEqual(report['mutations'],[])
        self.assertEqual(report['summary']['KILLED'],0)

    def test_mutation_statuses_are_distinct(self):
        f=mutations.classify
        self.assertEqual(f(False,False,True,True,True,True),'NOT_APPLIED')
        self.assertEqual(f(True,True,True,True,True,True),'CRASHED')
        self.assertEqual(f(True,False,False,True,True,True),'CONTROL_BROKEN')
        self.assertEqual(f(True,False,True,False,True,True),'BASELINE_FAILED')
        self.assertEqual(f(True,False,True,True,False,False),'SURVIVED')
        self.assertEqual(f(True,False,True,True,True,False),'VACUOUS')
        self.assertEqual(f(True,False,True,True,True,True),'KILLED')

    def test_source_mutants_kill_semantically_preserve_five_full_controls(self):
        report=mutations.run()
        self.assertEqual(report['summary']['KILLED'],7)
        self.assertEqual(sum(report['summary'].values()),7)
        self.assertEqual(len({row['mutated_source_sha256'] for row in report['mutations']}),7)
        for row in report['mutations']:
            self.assertEqual(len(row['controls']),5); self.assertTrue(all(row['controls'].values()))
            self.assertNotEqual(row['baseline'][row['axis']],row['actual'][row['axis']])

    def test_invalid_digest_and_unsupported_codecs(self):
        for key,value in [('payload_sha256','ABC'),('hash_algorithm','sha1'),('json_codec','jcs'),('profile','unknown')]:
            p=package(); p[key]=value
            self.assertIn(self.check(p)['input_status'],('INVALID','UNSUPPORTED'))

    def test_declared_bit_permutation_must_be_bijective(self):
        for value in ([0,0],[1],[0,2],['0',1],[True,1]):
            p=package(); p['output_to_raw']=value
            self.assertEqual(self.check(p)['input_status'],'INVALID')

    def test_no_mutation_of_caller_objects(self):
        p=package(); r=request(); before=deepcopy((p,r))
        self.check(p,r); self.assertEqual((p,r),before)

if __name__=='__main__': unittest.main()
