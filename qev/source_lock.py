"""Closed structural contract for the standalone source lock."""
import re
from . import source_inventory as pins

class SourceError(ValueError):
    def __init__(self, reason, status="INVENTORY_INVALID"):
        self.reason = reason
        self.status = status
        super().__init__(reason)

def need(condition, reason, status="INVENTORY_INVALID"):
    if not condition:
        raise SourceError(reason, status)

def _hash(value, length):
    need(type(value) is str and re.fullmatch(r"[0-9a-f]{%d}" % length, value) is not None, "HASH_FORMAT")

def _size(value):
    need(type(value) is int and 0 <= value <= 4_194_304, "BYTE_LENGTH_TYPE_RANGE")

def _fields(obj, names):
    need(type(obj) is dict and set(obj) == set(names), "CLOSED_OBJECT_FIELDS")
def validate_lock(lock):
    _fields(lock, ("format", "boundary", "self_digest", "local_files", "vendor_files"))
    need(lock["format"] == "quantum-execution-evidence.sources.v0", "LOCK_FORMAT")
    need(lock["boundary"] == "Byte identity only; no authentication, execution provenance, entropy, or hardware claim.", "LOCK_BOUNDARY")
    need(lock["self_digest"] == "EXCLUDED_TO_AVOID_CIRCULARITY", "LOCK_SELF_DIGEST")
    need(type(lock["local_files"]) is list and type(lock["vendor_files"]) is list, "LOCK_INVENTORY_TYPE")

    local_paths = []
    for row in lock["local_files"]:
        _fields(row, ("path", "sha256", "git_blob_sha1", "size_bytes"))
        need(type(row["path"]) is str, "LOCAL_PATH_TYPE")
        _hash(row["sha256"], 64); _hash(row["git_blob_sha1"], 40); _size(row["size_bytes"])
        local_paths.append(row["path"])
    need(len(local_paths) == len(pins.LOCAL_FILES), "LOCAL_FILES_COMPLETE_UNIQUE")
    need(len(set(local_paths)) == len(local_paths) and set(local_paths) == set(pins.LOCAL_FILES), "LOCAL_FILES_COMPLETE_UNIQUE")

    expected = {(row["path"], row["commit"]): row for row in pins.VENDOR_FILES}
    keys = []
    for row in lock["vendor_files"]:
        _fields(row, ("path", "source_path", "repository", "commit", "sha256", "git_blob_sha1", "size_bytes"))
        need(all(type(row[k]) is str for k in ("path", "source_path", "repository", "commit")), "VENDOR_STRING_TYPE")
        _hash(row["commit"], 40); _hash(row["sha256"], 64); _hash(row["git_blob_sha1"], 40); _size(row["size_bytes"])
        key = (row["path"], row["commit"]); keys.append(key)
        need(key in expected and row == expected[key], "VENDOR_IDENTITY_BINDING")
    need(len(keys) == len(expected) and len(set(keys)) == len(keys) and set(keys) == set(expected), "VENDOR_COMPLETE_UNIQUE")
    return True
