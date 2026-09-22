"""Native TSEI preservation gate over native QEV RVR artifacts."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any

from . import rvr_native

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "qev/tsei_bridge.ts"
TSEI_COMMIT = "45b46bf7df3a60b32583291f577a36bf19d22f00"

def _bundle():
    profile, digest, _, pinned, schema, _, _ = rvr_native.load_profile_context()
    vectors = rvr_native.rvr.parse_json_bytes(pinned["verification-vectors"], "verification-vectors")
    case = vectors["verificationCases"]["reproduced"]
    return rvr_native.make_bundle(case, profile, digest, schema)

def _evaluate(bundle: dict[str, Any], mode: str):
    with tempfile.TemporaryDirectory(prefix="qev-tsei-") as temp:
        path = Path(temp) / "bundle.json"
        path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")
        completed = subprocess.run(
            ["bun", str(BRIDGE), str(path), mode],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=30, check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode("utf-8", "replace"))
        return json.loads(completed.stdout)
def run_gate():
    bundle = _bundle()
    results = {
        mode: _evaluate(bundle, mode)
        for mode in ("stable", "allowed_variant", "history_sensitive", "violation")
    }
    expected = {
        "stable": "stable",
        "allowed_variant": "stable",
        "history_sensitive": "history_sensitive",
        "violation": "violation",
    }
    for mode, classification in expected.items():
        actual = results[mode]["result"]["classification"]
        if actual != classification:
            raise AssertionError(f"{mode}: expected {classification}, got {actual}")

    allowed = results["allowed_variant"]["result"]
    if allowed["allowed_variant_changed"] is not True:
        raise AssertionError("allowed variant was not observed")
    history = results["history_sensitive"]["result"]
    if history["stability_match"] is not False:
        raise AssertionError("history-sensitive mismatch was not observed")
    violation = results["violation"]["result"]
    if violation["normative_match"] is not False:
        raise AssertionError("normative violation was not observed")

    return {
        "gate": "TSEI_QEV_NATIVE_PRESERVATION_PASS",
        "tseiSource": {
            "commit": TSEI_COMMIT,
            "specification": "Transformation-Stable Evidence Interoperability Specification v0",
            "comparator": "canonicalIdentityJson",
        },
        "profileId": "qev-rvr-artifact-preservation-v0",
        "protectedRelation": {
            "normative": "verification profile + semantic outcome/reason/result digest",
            "stability": "evidence-set identity",
            "allowedVariant": "payload-map representation order",
            "forbidden": "claim identity",
        },
        "cases": {mode: report["result"] for mode, report in results.items()},
        "boundaries": {
            "rvrVerification": "LOWER_LAYER_INPUT",
            "receiptosPackaging": "SEPARATE_LAYER",
            "physicalQpuExecution": "NOT_ESTABLISHED",
            "providerAuthenticity": "NOT_ESTABLISHED",
            "entropy": "NOT_ESTABLISHED",
            "transformationPreservation": "ESTABLISHED_ONLY_FOR_DECLARED_PROFILE_AND_CASES",
        },
    }

def main():
    try:
        print(json.dumps(run_gate(), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"TSEI QEV gate failed: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
