"""Capture a real IBM Quantum SamplerV2 job as a local QEV record.

Opt-in only. Requires qiskit-ibm-runtime and an already configured IBM account.
No credentials are written by this script.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--job-id",required=True)
    ap.add_argument("--request-id",required=True)
    ap.add_argument("--physical-circuit-digest",required=True)
    ap.add_argument("--transpiler-name",default="qiskit-preset-pass-manager")
    ap.add_argument("--transpiler-version",required=True)
    ap.add_argument("--transpiler-profile",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    try:
        import qiskit
        import qiskit_ibm_runtime
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise SystemExit("Install qiskit-ibm-runtime in a separate environment before live capture.") from exc

    service=QiskitRuntimeService()
    job=service.job(args.job_id)
    result=job.result()
    backend=job.backend()
    if backend is None: raise SystemExit("IBM job backend unavailable")
    if len(result)!=1: raise SystemExit("v0 capture supports exactly one Sampler PUB")
    data=result[0].data
    registers=list(data.keys())
    if len(registers)!=1: raise SystemExit("v0 capture supports exactly one classical register")
    register=registers[0]
    bits=data[register]
    bitstrings=bits.get_bitstrings()
    record={
      "schema":"qev.ibm-runtime-sampler-v2-record.v0",
      "capture_kind":"RECORDED_PROVIDER_API_ARTIFACT",
      "sdk":{"qiskit":getattr(qiskit,"__version__","unknown"),
             "qiskit_ibm_runtime":getattr(qiskit_ibm_runtime,"__version__","unknown"),
             "source":"LIVE_IBM_RUNTIME_API"},
      "runtime":{"primitive":"SamplerV2","primitive_version":2},
      "job":{"job_id":job.job_id(),"provider":"ibm-quantum",
             "backend":backend.name,"request_id":args.request_id,"status":str(job.status())},
      "result":{"register":register,"shots":bits.num_shots,"bitstrings":bitstrings,
                "metadata":result[0].metadata},
      "isa_circuit":{"physicalCircuitDigest":args.physical_circuit_digest,
        "transpiler":{"name":args.transpiler_name,"version":args.transpiler_version,
                      "profile":args.transpiler_profile},
        "representation":"external-isa-circuit-digest"},
    }
    Path(args.output).write_text(json.dumps(record,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps({"job_id":job.job_id(),"backend":backend.name,"shots":bits.num_shots,
                      "output":args.output},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
