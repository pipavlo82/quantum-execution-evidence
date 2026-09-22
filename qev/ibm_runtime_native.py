"""IBM Runtime SamplerV2 adapter conformance gate."""
from __future__ import annotations
import copy,json
from pathlib import Path
from .ibm_runtime_adapter import load_record,verify_record
from .provider_binding import BindingError

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/"fixtures/provider/ibm-runtime-sampler-v2"

def run_gate():
    submission=load_record(DIR/"submission.json")
    record=load_record(DIR/"record.json")
    positive=verify_record(record,submission)
    if positive["executionBinding"]["executionBinding"]!="BOUND":
        raise AssertionError("IBM fixture not bound")
    if positive["providerAuthentication"]!="NOT_ESTABLISHED":
        raise AssertionError("IBM fixture authentication elevated")

    mutations={}
    paths={
      "backend":("job","backend","other-backend"),
      "request_id":("job","request_id","other-request"),
      "shots":("result","shots",9),
      "physicalCircuit":("isa_circuit","physicalCircuitDigest","0"*64),
      "transpiler":("isa_circuit","transpiler",{"name":"other","version":"x","profile":"x"}),
      "status":("job","status","ERROR"),
    }
    for name,(section,key,value) in paths.items():
        candidate=copy.deepcopy(record);candidate[section][key]=value
        result=verify_record(candidate,submission)
        if result["executionBinding"]["executionBinding"]!="REFUTED":
            raise AssertionError(name)
        mutations[name]=result
    malformed=copy.deepcopy(record)
    malformed["result"]["bitstrings"]=["00","2x"]
    try:
        verify_record(malformed,submission)
    except BindingError:
        malformed_status="REJECTED"
    else:
        raise AssertionError("malformed bitstrings accepted")

    return {
      "gate":"QEV_IBM_RUNTIME_ADAPTER_V0_PASS",
      "fixtureAuthority":"OFFLINE_CONFORMANCE_FIXTURE_NOT_LIVE_IBM",
      "positive":positive,
      "mutations":mutations,
      "malformedBitstrings":malformed_status,
      "ibmApiModel":{
        "primitive":"SamplerV2",
        "job":"RuntimeJobV2",
        "result":"PrimitiveResult / SamplerPubResult / BitArray",
        "shotOrderSurface":"BitArray.get_bitstrings()",
      },
      "boundaries":{
        "liveIBMJob":"NOT_EXECUTED",
        "providerAuthentication":"NOT_ESTABLISHED",
        "realQpuExecution":"NOT_ESTABLISHED",
        "liveSubmitScript":"SEPARATE_OPT_IN",
      },
    }

def main():
    try: print(json.dumps(run_gate(),indent=2,sort_keys=True));return 0
    except Exception as exc: print(f"IBM adapter gate failed: {exc}");return 1

if __name__=="__main__": raise SystemExit(main())
