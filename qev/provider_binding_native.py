"""Finite adversarial gate for Provider Execution Binding v0."""
from __future__ import annotations
import copy
import json
from pathlib import Path

from . import checker
from .provider_binding import make_provider_artifact, make_submission, verify_binding
from .quantum_transpile import parse_logical, transpile_layout

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/"fixtures/corpus/sample-a.request.json"
PACKAGE=ROOT/"fixtures/corpus/sample-a.package.json"

def run_gate():
    request=checker.strict_load(REQUEST.read_bytes())
    package=checker.strict_load(PACKAGE.read_bytes())
    raw=package["raw"]["data"].encode("ascii")
    logical=parse_logical(request)
    physical=transpile_layout(logical,[3,7])
    submission=make_submission(request,physical,{
        "name":"qev-layout-transpiler","version":"0","profile":"qev-quantum-layout-transpilation-v0",
    })
    artifact=make_provider_artifact(
        submission,raw,provider_job_id="provider-job-0001",
        authentication=None,
    )
    positive=verify_binding(submission,artifact,raw)
    if positive["executionBinding"]!="BOUND" or positive["providerAuthentication"]!="NOT_ESTABLISHED":
        raise AssertionError("positive binding")

    mutations={}
    cases={
        "provider":("provider","other-provider"),
        "backend":("backend","other-backend"),
        "request":("request_id","other-request"),
        "shots":("shots",submission["shots"]+1),
        "physicalCircuit":("submittedPhysicalCircuitDigest","0"*64),
        "transpiler":("transpiler",{"name":"other","version":"0","profile":"other"}),
        "completed":("status","FAILED"),
    }
    for name,(field,value) in cases.items():
        candidate=copy.deepcopy(artifact);candidate[field]=value
        result=verify_binding(submission,candidate,raw)
        if result["executionBinding"]!="REFUTED" or result["axes"][name] is not False:
            raise AssertionError(name)
        mutations[name]=result
    raw_changed=raw.replace(b"00\n",b"11\n",1)
    raw_result=verify_binding(submission,artifact,raw_changed)
    if raw_result["executionBinding"]!="REFUTED" or raw_result["axes"]["rawMeasurements"] is not False:
        raise AssertionError("rawMeasurements")
    mutations["rawMeasurements"]=raw_result

    assertion=copy.deepcopy(artifact)
    assertion["authentication"]={"kind":"UNVERIFIED_ASSERTION","text":"provider says valid"}
    assertion_result=verify_binding(submission,assertion,raw)
    if assertion_result["executionBinding"]!="BOUND" or assertion_result["providerAuthentication"]!="NOT_ESTABLISHED":
        raise AssertionError("unverified authentication elevation")

    return {
        "gate":"QEV_PROVIDER_EXECUTION_BINDING_V0_PASS",
        "positive":positive,
        "mutations":mutations,
        "unverifiedAuthentication":assertion_result,
        "counts":{"bindingAxes":8,"mutationsRefuted":len(mutations)},
        "boundaries":{
            "executionBinding":"ESTABLISHED_OVER_SUPPLIED_PROVIDER_ARTIFACT",
            "providerAuthentication":"NOT_ESTABLISHED",
            "physicalQpuExecutionAuthentication":"NOT_ESTABLISHED",
            "entropy":"NOT_ESTABLISHED",
            "providerSpecificAdapter":"NOT_INTEGRATED",
        },
    }

def main():
    try:
        print(json.dumps(run_gate(),indent=2,sort_keys=True));return 0
    except Exception as exc:
        print(f"Provider binding gate failed: {exc}");return 1

if __name__=="__main__": raise SystemExit(main())
