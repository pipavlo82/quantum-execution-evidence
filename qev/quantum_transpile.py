"""Vendor-neutral logical -> physical layout transpilation boundary v0."""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any

PROFILE = "qev-quantum-layout-transpilation-v0"
GATE = re.compile(r"^(H|X) ([0-7])$|^CX ([0-7]) ([0-7])$|^RZ ([0-7]) theta_quarters$")

class CircuitError(ValueError):
    pass

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def parse_logical(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("marker") != "SYNTHETIC":
        raise CircuitError("REQUEST_MARKER")
    width = request.get("width")
    if type(width) is not int or not 1 <= width <= 8:
        raise CircuitError("WIDTH")
    program = request.get("program")
    if type(program) is not dict or program.get("codec") != "qev-lines.v0":
        raise CircuitError("PROGRAM_CODEC")
    source = program.get("source")
    if type(source) is not str or not source.endswith("\n"):
        raise CircuitError("PROGRAM_SOURCE")
    lines = source[:-1].split("\n")
    if not lines or lines[-1] != "MEASURE_ALL":
        raise CircuitError("PROGRAM_TERMINATOR")
    operations = []
    for index, line in enumerate(lines[:-1]):
        m = GATE.fullmatch(line)
        if not m:
            raise CircuitError("PROGRAM_EXPRESSION")
        if m.group(1):
            gate, qubits = m.group(1), [int(m.group(2))]
            parameter = None
        elif m.group(3) is not None:
            gate, qubits = "CX", [int(m.group(3)), int(m.group(4))]
            parameter = None
        else:
            gate, qubits = "RZ", [int(m.group(5))]
            parameter = {"theta_quarters": request["parameters"]["theta_quarters"]}
        if any(q >= width for q in qubits) or (gate == "CX" and qubits[0] == qubits[1]):
            raise CircuitError("QUBIT_RANGE")
        operations.append({"ordinal": index, "gate": gate, "logical_qubits": qubits, "parameter": parameter})
    return {
        "schema": "qev.logical-circuit.v0",
        "width": width,
        "operations": operations,
        "measurement": {"kind": "MEASURE_ALL", "logical_order": list(range(width))},
    }
def validate_layout(layout: list[int], width: int) -> None:
    if type(layout) is not list or len(layout) != width:
        raise CircuitError("LAYOUT")
    if any(type(q) is not int or q < 0 or q > 63 for q in layout) or len(set(layout)) != width:
        raise CircuitError("LAYOUT")

def transpile_layout(logical: dict[str, Any], layout: list[int]) -> dict[str, Any]:
    width = logical["width"]
    validate_layout(layout, width)
    operations = []
    for op in logical["operations"]:
        operations.append({
            "ordinal": op["ordinal"],
            "gate": op["gate"],
            "physical_qubits": [layout[q] for q in op["logical_qubits"]],
            "parameter": op["parameter"],
        })
    return {
        "schema": "qev.physical-circuit.v0",
        "logical_width": width,
        "physical_layout": list(layout),
        "operations": operations,
        "measurement": {
            "kind": "MEASURE_ALL",
            "physical_order_for_logical": list(layout),
        },
    }

def normalize_physical(target: dict[str, Any]) -> dict[str, Any]:
    if target.get("schema") != "qev.physical-circuit.v0":
        raise CircuitError("TARGET_SCHEMA")
    width = target.get("logical_width")
    layout = target.get("physical_layout")
    if type(width) is not int:
        raise CircuitError("TARGET_WIDTH")
    validate_layout(layout, width)
    inverse = {physical: logical for logical, physical in enumerate(layout)}
    operations = []
    source_ops = target.get("operations")
    if type(source_ops) is not list:
        raise CircuitError("TARGET_OPERATIONS")
    for expected_ordinal, op in enumerate(source_ops):
        if type(op) is not dict or set(op) != {"ordinal", "gate", "physical_qubits", "parameter"}:
            raise CircuitError("TARGET_OPERATION_SHAPE")
        if op["ordinal"] != expected_ordinal or op["gate"] not in {"H", "X", "CX", "RZ"}:
            raise CircuitError("TARGET_OPERATION")
        try:
            logical_qubits = [inverse[q] for q in op["physical_qubits"]]
        except (KeyError, TypeError):
            raise CircuitError("TARGET_PHYSICAL_QUBIT")
        expected_arity = 2 if op["gate"] == "CX" else 1
        if len(logical_qubits) != expected_arity:
            raise CircuitError("TARGET_ARITY")
        operations.append({
            "ordinal": op["ordinal"], "gate": op["gate"],
            "logical_qubits": logical_qubits, "parameter": op["parameter"],
        })
    measurement = target.get("measurement")
    if measurement != {"kind": "MEASURE_ALL", "physical_order_for_logical": layout}:
        raise CircuitError("MEASUREMENT_MAPPING")
    return {
        "schema": "qev.logical-circuit.v0",
        "width": width,
        "operations": operations,
        "measurement": {"kind": "MEASURE_ALL", "logical_order": list(range(width))},
    }
def binding(logical: dict[str, Any], physical: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_physical(physical)
    preserved = normalized == logical
    return {
        "schema": "qev.quantum-transpilation-binding.v0",
        "profile": PROFILE,
        "logicalCircuitDigest": digest(logical),
        "physicalCircuitDigest": digest(physical),
        "normalizedTargetDigest": digest(normalized),
        "requestProgramDigest": digest(request["program"]),
        "protectedLogicalRelation": "EXACT_ORDERED_OPERATION_AND_MEASUREMENT_EQUIVALENCE_UNDER_LAYOUT_BIJECTION",
        "preserved": preserved,
        "logicalCircuit": logical,
        "physicalCircuit": physical,
        "normalizedTarget": normalized,
    }
