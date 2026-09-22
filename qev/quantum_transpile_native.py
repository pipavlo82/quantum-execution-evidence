"""Quantum layout-transpilation preservation gate v0."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import subprocess
import tempfile

from . import checker
from .quantum_transpile import binding, parse_logical, transpile_layout

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "qev/quantum_transpile_tsei_bridge.ts"
REQUEST = ROOT / "fixtures/corpus/sample-a.request.json"
PACKAGE = ROOT / "fixtures/corpus/sample-a.package.json"

def _tsei(logical, physical):
    with tempfile.TemporaryDirectory(prefix="qev-transpile-") as temp:
        temp = Path(temp)
        logical_path, physical_path = temp/"logical.json", temp/"physical.json"
        logical_path.write_text(json.dumps(logical, sort_keys=True), encoding="utf-8")
        physical_path.write_text(json.dumps(physical, sort_keys=True), encoding="utf-8")
        completed = subprocess.run(
            ["bun", str(BRIDGE), str(logical_path), str(physical_path)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
        )
        if completed.returncode:
            return {"status": "REJECTED", "reason": completed.stderr.decode("utf-8", "replace").strip()}
        return {"status": "EVALUATED", **json.loads(completed.stdout)}

def _execution_binding(request, physical):
    return {
        "schema": "qev.quantum-execution-binding.v0",
        "request_id": request["request_id"],
        "provider": request["provider"],
        "backend": request["backend"],
        "job": request["job"],
        "physicalCircuitDigest": binding(parse_logical(request), physical, request)["physicalCircuitDigest"],
        "authority": "SUPPLIED_SIDECAR_NOT_PROVIDER_AUTHENTICATED",
    }
def run_gate():
    request_bytes = REQUEST.read_bytes()
    package_bytes = PACKAGE.read_bytes()
    request = checker.strict_load(request_bytes)
    qev_result = checker.verify(request_bytes, package_bytes)
    if qev_result["claim_support"] != "ESTABLISHED_OVER_SUPPLIED_BYTES":
        raise AssertionError("base QEV fixture not established")

    logical = parse_logical(request)
    layout_a = [3, 7]
    layout_b = [11, 2]
    physical_a = transpile_layout(logical, layout_a)
    physical_b = transpile_layout(logical, layout_b)

    stable_a = _tsei(logical, physical_a)
    stable_b = _tsei(logical, physical_b)

    gate_mutation = copy.deepcopy(physical_a)
    gate_mutation["operations"][0]["gate"] = "X"
    gate_changed = _tsei(logical, gate_mutation)

    measurement_mutation = copy.deepcopy(physical_a)
    measurement_mutation["measurement"]["physical_order_for_logical"] = list(reversed(layout_a))
    measurement_changed = _tsei(logical, measurement_mutation)

    non_bijective = copy.deepcopy(physical_a)
    non_bijective["physical_layout"] = [3, 3]
    non_bijective_rejected = _tsei(logical, non_bijective)

    for name, result in (("layout_a", stable_a), ("layout_b", stable_b)):
        if result["status"] != "EVALUATED" or result["result"]["classification"] != "stable":
            raise AssertionError(f"{name} not stable")
    if gate_changed["result"]["classification"] != "violation":
        raise AssertionError("gate mutation not violation")
    if (measurement_changed["status"] != "EVALUATED"
            or measurement_changed["result"]["classification"] != "unresolved"
            or measurement_changed["result"]["unresolved_reason"] != "target_recompute_failed"):
        raise AssertionError("measurement mapping mutation not unresolved")
    if (non_bijective_rejected["status"] != "EVALUATED"
            or non_bijective_rejected["result"]["classification"] != "unresolved"
            or non_bijective_rejected["result"]["unresolved_reason"] != "target_recompute_failed"):
        raise AssertionError("non-bijective layout not unresolved")

    bind_a = binding(logical, physical_a, request)
    bind_b = binding(logical, physical_b, request)
    if not bind_a["preserved"] or not bind_b["preserved"]:
        raise AssertionError("layout normalization did not preserve logical circuit")
    if bind_a["logicalCircuitDigest"] != bind_b["logicalCircuitDigest"]:
        raise AssertionError("logical identity changed across layouts")
    if bind_a["physicalCircuitDigest"] == bind_b["physicalCircuitDigest"]:
        raise AssertionError("physical representations unexpectedly identical")
    execution_a = _execution_binding(request, physical_a)
    return {
        "gate": "QEV_QUANTUM_LAYOUT_TRANSPILATION_BOUNDARY_PASS",
        "profileId": "qev-quantum-layout-transpilation-v0",
        "logicalCircuitDigest": bind_a["logicalCircuitDigest"],
        "layouts": {
            "layoutA": {"layout": layout_a, "physicalCircuitDigest": bind_a["physicalCircuitDigest"],
                        "tseiClassification": stable_a["result"]["classification"]},
            "layoutB": {"layout": layout_b, "physicalCircuitDigest": bind_b["physicalCircuitDigest"],
                        "tseiClassification": stable_b["result"]["classification"]},
        },
        "negativeControls": {
            "gateMutation": gate_changed,
            "measurementMappingMutation": measurement_changed,
            "nonBijectiveLayout": non_bijective_rejected,
        },
        "executionBinding": execution_a,
        "boundaries": {
            "logicalSemantics": "EXACT_ORDERED_GATE_AND_MEASUREMENT_RELATION_UNDER_LAYOUT_BIJECTION",
            "arbitraryGateOptimizationEquivalence": "NOT_ESTABLISHED",
            "routingSwapEquivalence": "NOT_ESTABLISHED",
            "physicalQpuExecution": "NOT_ESTABLISHED",
            "providerAuthenticity": "NOT_ESTABLISHED",
            "executionToPhysicalCircuit": "BOUND_BY_SUPPLIED_SIDECAR_NOT_PROVIDER_AUTHENTICATED",
            "entropy": "NOT_ESTABLISHED",
        },
    }

def main():
    try:
        print(json.dumps(run_gate(), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"Quantum transpilation gate failed: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
