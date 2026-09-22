"""Vendor-neutral Provider Execution Binding v0."""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z0-9._:/-]{1,200}$")

class BindingError(ValueError):
    pass

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def digest_json(value: Any) -> str:
    return digest_bytes(canonical(value))

def _token(value: Any, name: str) -> str:
    if type(value) is not str or TOKEN.fullmatch(value) is None:
        raise BindingError(name)
    return value

def _digest(value: Any, name: str) -> str:
    if type(value) is not str or HEX64.fullmatch(value) is None:
        raise BindingError(name)
    return value

def make_submission(request: dict[str, Any], physical_circuit: dict[str, Any],
                    transpiler: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": "qev.provider-submission.v0",
        "provider": _token(request["provider"], "provider"),
        "backend": _token(request["backend"], "backend"),
        "requested_job": _token(request["job"], "job"),
        "request_id": _token(request["request_id"], "request_id"),
        "shots": request["shots"],
        "physicalCircuitDigest": digest_json(physical_circuit),
        "transpiler": {
            "name": _token(transpiler["name"], "transpiler.name"),
            "version": _token(transpiler["version"], "transpiler.version"),
            "profile": _token(transpiler["profile"], "transpiler.profile"),
        },
    }
def make_provider_artifact(submission: dict[str, Any], raw_bytes: bytes,
                           *, provider_job_id: str, status: str = "COMPLETED",
                           authentication: dict[str, Any] | None = None) -> dict[str, Any]:
    if status not in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise BindingError("status")
    return {
        "schema": "qev.provider-execution-artifact.v0",
        "provider": submission["provider"],
        "backend": submission["backend"],
        "provider_job_id": _token(provider_job_id, "provider_job_id"),
        "request_id": submission["request_id"],
        "shots": submission["shots"],
        "submittedPhysicalCircuitDigest": submission["physicalCircuitDigest"],
        "transpiler": submission["transpiler"],
        "status": status,
        "rawMeasurementDigest": digest_bytes(raw_bytes),
        "rawMeasurementBytes": len(raw_bytes),
        "authentication": authentication,
    }

def verify_binding(submission: dict[str, Any], artifact: dict[str, Any],
                   raw_bytes: bytes) -> dict[str, Any]:
    required_submission = {
        "schema","provider","backend","requested_job","request_id","shots",
        "physicalCircuitDigest","transpiler",
    }
    required_artifact = {
        "schema","provider","backend","provider_job_id","request_id","shots",
        "submittedPhysicalCircuitDigest","transpiler","status",
        "rawMeasurementDigest","rawMeasurementBytes","authentication",
    }
    if type(submission) is not dict or set(submission) != required_submission:
        raise BindingError("submission_shape")
    if type(artifact) is not dict or set(artifact) != required_artifact:
        raise BindingError("artifact_shape")
    if submission["schema"] != "qev.provider-submission.v0" or artifact["schema"] != "qev.provider-execution-artifact.v0":
        raise BindingError("schema")

    axes = {
        "provider": artifact["provider"] == submission["provider"],
        "backend": artifact["backend"] == submission["backend"],
        "request": artifact["request_id"] == submission["request_id"],
        "shots": artifact["shots"] == submission["shots"],
        "physicalCircuit": artifact["submittedPhysicalCircuitDigest"] == submission["physicalCircuitDigest"],
        "transpiler": artifact["transpiler"] == submission["transpiler"],
        "rawMeasurements": artifact["rawMeasurementDigest"] == digest_bytes(raw_bytes)
            and artifact["rawMeasurementBytes"] == len(raw_bytes),
        "completed": artifact["status"] == "COMPLETED",
    }
    execution_bound = all(axes.values())
    auth = artifact["authentication"]
    if auth is None:
        provider_auth = "NOT_ESTABLISHED"
    elif type(auth) is dict and auth.get("kind") == "UNVERIFIED_ASSERTION":
        provider_auth = "NOT_ESTABLISHED"
    else:
        provider_auth = "UNSUPPORTED_AUTHENTICATION_EVIDENCE"

    return {
        "schema": "qev.provider-execution-binding-result.v0",
        "executionBinding": "BOUND" if execution_bound else "REFUTED",
        "providerAuthentication": provider_auth,
        "axes": axes,
        "submissionDigest": digest_json(submission),
        "providerArtifactDigest": digest_json(artifact),
        "rawMeasurementDigest": digest_bytes(raw_bytes),
        "claimBoundary": {
            "executionBound": execution_bound,
            "providerAuthenticated": False,
            "physicalQpuExecutionAuthenticated": False,
            "entropyEstablished": False,
        },
    }
