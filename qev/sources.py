"""Validate the finite standalone source lock without network access."""
import hashlib
from pathlib import Path
from . import adapters, admission, source_inventory as pins

verify_sources = adapters.verify_sources
ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "sources.lock.json"

def identity(data: bytes):
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
        "size_bytes": len(data),
    }

def validate():
    try:
        lock = admission.read_json(LOCK_PATH)
        admission.validate_lock(lock)
    except admission.AdmissionError as exc:
        return {
            "format": "quantum-execution-evidence-source-validation.v0",
            "admission": admission.status(exc),
            "valid": False,
            "evidence_status": exc.status,
            "local_files": 0,
            "vendor_files": 0,
            "vendor_status": "NOT_EVALUATED",
            "vendor_runtime_status": "NOT_EVALUATED",
            "results": [],
        }

    results = []
    for row in lock["local_files"]:
        path = ROOT / row["path"]
        try:
            if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
                raise ValueError("unsafe source path")
            actual = identity(path.read_bytes())
            state = "MATCH" if all(actual[k] == row[k] for k in actual) else "MISMATCH"
        except (OSError, ValueError):
            state = "UNAVAILABLE"
        results.append({"path": row["path"], "status": state, "role": "LOCAL"})

    for row in lock["vendor_files"]:
        path = ROOT / row["path"]
        try:
            if not path.resolve().is_relative_to((ROOT / "vendor").resolve()) or path.is_symlink():
                raise ValueError("unsafe vendor path")
            actual = identity(path.read_bytes())
            state = "MATCH" if all(actual[k] == row[k] for k in actual) else "MISMATCH"
        except (OSError, ValueError):
            state = "UNAVAILABLE"
        results.append({
            "path": row["path"],
            "status": state,
            "role": "VENDORED_SEMANTIC_ABI",
        })

    try:
        vendor = verify_sources()
        vendor_ok = type(vendor) is list and len(vendor) == len(pins.VENDOR_FILES)
    except RuntimeError:
        vendor, vendor_ok = [], False

    state = (
        "EVIDENCE_MISMATCH" if any(row["status"] == "MISMATCH" for row in results)
        else "EVIDENCE_UNAVAILABLE"
        if (not vendor_ok or any(row["status"] == "UNAVAILABLE" for row in results))
        else "ADMITTED"
    )
    return {
        "format": "quantum-execution-evidence-source-validation.v0",
        "admission": admission.status(),
        "evidence_status": state,
        "valid": state == "ADMITTED",
        "local_files": len(lock["local_files"]),
        "vendor_files": len(lock["vendor_files"]),
        "vendor_status": "AVAILABLE" if vendor_ok else "UNAVAILABLE",
        "vendor_runtime_status": "AVAILABLE" if vendor_ok else "UNAVAILABLE",
        "results": results,
        "trust_boundary": (
            "Byte identity only; not correctness, provenance, entropy, "
            "or hardware authentication."
        ),
    }

def successful(report):
    rows = report.get("results", [])
    return (
        report.get("valid") is True
        and report.get("admission", {}).get("status") == "ADMITTED"
        and report.get("evidence_status") == "ADMITTED"
        and report.get("local_files") == len(pins.LOCAL_FILES)
        and report.get("vendor_files") == len(pins.VENDOR_FILES)
        and len(rows) == len(pins.LOCAL_FILES) + len(pins.VENDOR_FILES)
        and all(row.get("status") == "MATCH" for row in rows)
    )
