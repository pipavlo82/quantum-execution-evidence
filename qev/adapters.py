"""Offline adapter for the exact vendored Semantic ABI linker."""
from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any
from . import source_inventory as pins

ROOT = Path(__file__).resolve().parents[1]

class AdapterUnavailable(RuntimeError):
    pass

def _identity(data: bytes) -> dict[str, Any]:
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest(),
        "size_bytes": len(data),
    }

def _verified_vendor() -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    records, payloads = [], {}
    for row in pins.VENDOR_FILES:
        path = ROOT / row["path"]
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to((ROOT / "vendor").resolve()):
                raise ValueError("vendor path escape")
            data = path.read_bytes()
        except (OSError, ValueError) as exc:
            raise AdapterUnavailable("Vendored Semantic ABI source unavailable") from exc
        actual = _identity(data)
        if any(actual[k] != row[k] for k in actual):
            raise AdapterUnavailable("Vendored Semantic ABI source identity mismatch: " + row["path"])
        payloads[row["path"]] = data
        records.append(dict(row))
    return records, payloads
def verify_sources() -> list[dict[str, Any]]:
    return _verified_vendor()[0]

def manifest_schema() -> dict[str, Any]:
    _, payloads = _verified_vendor()
    try:
        value = json.loads(payloads["vendor/semantic-abi/schema/manifest.schema.json"])
    except (ValueError, TypeError) as exc:
        raise AdapterUnavailable("Pinned Semantic ABI schema is not readable JSON") from exc
    if type(value) is not dict:
        raise AdapterUnavailable("Pinned Semantic ABI schema is not an object")
    return value

def run_semantic_link(producer: dict[str, Any], consumer: dict[str, Any]) -> dict[str, Any]:
    _, payloads = _verified_vendor()
    request = {
        "source_base64": base64.b64encode(payloads["vendor/semantic-abi/runner/src/linker.mjs"]).decode("ascii"),
        "producer": producer,
        "consumer": consumer,
    }
    try:
        completed = subprocess.run(
            ["node", str(ROOT / "qev" / "semantic_link.mjs")],
            input=json.dumps(request, allow_nan=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
        if completed.returncode != 0:
            raise AdapterUnavailable("Native Semantic ABI linker failed")
        result = json.loads(completed.stdout)
        if type(result) is not dict or type(result.get("valid")) is not bool:
            raise AdapterUnavailable("Native Semantic ABI linker returned malformed result")
        return result
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError) as exc:
        if isinstance(exc, AdapterUnavailable):
            raise
        raise AdapterUnavailable("Native Semantic ABI linker unavailable") from exc
