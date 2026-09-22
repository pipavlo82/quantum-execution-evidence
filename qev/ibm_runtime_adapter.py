"""IBM Quantum Runtime recorded-artifact adapter v0.

No network dependency. It normalizes a saved IBM SamplerV2 job/result record
into Provider Execution Binding v0. Authentication is not inferred.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .provider_binding import BindingError, make_provider_artifact, verify_binding

def canonical_raw_bitstrings(bitstrings: list[str]) -> bytes:
    if type(bitstrings) is not list or not bitstrings:
        raise BindingError("ibm.bitstrings")
    width = None
    out = []
    for value in bitstrings:
        if type(value) is not str or not value or any(ch not in "01" for ch in value):
            raise BindingError("ibm.bitstring")
        width = len(value) if width is None else width
        if len(value) != width:
            raise BindingError("ibm.bitstring_width")
        out.append(value)
    return ("\n".join(out) + "\n").encode("ascii")

def normalize_record(record: dict[str, Any], submission: dict[str, Any]):
    required = {
        "schema","capture_kind","sdk","runtime","job","result","isa_circuit",
    }
    if type(record) is not dict or set(record) != required:
        raise BindingError("ibm.record_shape")
    if record["schema"] != "qev.ibm-runtime-sampler-v2-record.v0":
        raise BindingError("ibm.schema")
    if record["capture_kind"] != "RECORDED_PROVIDER_API_ARTIFACT":
        raise BindingError("ibm.capture_kind")
    job = record["job"]
    result = record["result"]
    if type(job) is not dict or type(result) is not dict:
        raise BindingError("ibm.job_result")
    bitstrings = result.get("bitstrings")
    raw = canonical_raw_bitstrings(bitstrings)
    status = job.get("status")
    mapped = {"DONE":"COMPLETED","ERROR":"FAILED","CANCELLED":"CANCELLED"}.get(status)
    if mapped is None:
        raise BindingError("ibm.job_status")
    artifact = make_provider_artifact(
        submission, raw,
        provider_job_id=job.get("job_id"),
        status=mapped,
        authentication={
            "kind":"UNVERIFIED_ASSERTION",
            "source":"IBM_QUANTUM_RUNTIME_RECORDED_API_ARTIFACT",
            "transport":"not_reauthenticated_by_qev",
        },
    )
    artifact["provider"] = job.get("provider")
    artifact["backend"] = job.get("backend")
    artifact["request_id"] = job.get("request_id")
    artifact["shots"] = result.get("shots")
    artifact["submittedPhysicalCircuitDigest"] = record["isa_circuit"].get("physicalCircuitDigest")
    artifact["transpiler"] = record["isa_circuit"].get("transpiler")
    return artifact, raw
def verify_record(record: dict[str, Any], submission: dict[str, Any]):
    artifact, raw = normalize_record(record, submission)
    result = verify_binding(submission, artifact, raw)
    return {
        "schema":"qev.ibm-runtime-adapter-result.v0",
        "adapter":"IBM_QUANTUM_RUNTIME_SAMPLER_V2_RECORDED_ARTIFACT",
        "ibmJobId":artifact["provider_job_id"],
        "ibmBackend":artifact["backend"],
        "executionBinding":result,
        "providerAuthentication":"NOT_ESTABLISHED",
        "captureAuthority":"RECORDED_PROVIDER_API_ARTIFACT_NOT_CRYPTOGRAPHICALLY_AUTHENTICATED",
    }

def load_record(path: Path):
    return json.loads(path.read_bytes())
