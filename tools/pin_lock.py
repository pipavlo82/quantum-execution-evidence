"""Regenerate the finite standalone source lock from declared paths only."""
import json
from pathlib import Path
from qev import admission, source_inventory as pins
from qev.sources import identity

ROOT = Path(__file__).resolve().parents[1]

def generate():
    rows = []
    for name in pins.LOCAL_FILES:
        path = ROOT / name
        admission.need(path.resolve().is_relative_to(ROOT) and not path.is_symlink(), "LOCK_SOURCE_PATH")
        data = path.read_bytes()
        rows.append({"path": name, **identity(data)})
    lock = {
        "format": "quantum-execution-evidence.sources.v0",
        "boundary": "Byte identity only; no authentication, execution provenance, entropy, or hardware claim.",
        "self_digest": "EXCLUDED_TO_AVOID_CIRCULARITY",
        "local_files": rows,
        "vendor_files": [dict(row) for row in pins.VENDOR_FILES],
    }
    admission.validate_lock(lock)
    return (json.dumps(lock, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")

def main():
    target = ROOT / "sources.lock.json"
    data = generate()
    target.write_bytes(data)
    print(json.dumps({"local_files": len(pins.LOCAL_FILES), "vendor_files": len(pins.VENDOR_FILES),
                      "sha256": identity(data)["sha256"], "procedure": "fixed qev.source_inventory.LOCAL_FILES"}))

if __name__ == "__main__":
    main()
