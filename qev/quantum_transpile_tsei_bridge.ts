import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import {
  defineTransformationProfileV0,
  evaluateTransformationStabilityV0,
} from "../vendor/tsei-v0/src/receiptos/challenge/transformation-stability"

type LogicalOp = { ordinal: number; gate: string; logical_qubits: number[]; parameter: any }
type PhysicalOp = { ordinal: number; gate: string; physical_qubits: number[]; parameter: any }
type Logical = { schema: string; width: number; operations: LogicalOp[]; measurement: any }
type Physical = { schema: string; logical_width: number; physical_layout: number[]; operations: PhysicalOp[]; measurement: any }

function readJson(path: string) {
  return JSON.parse(readFileSync(resolve(path), "utf8"))
}

function assertLayout(layout: number[], width: number) {
  if (!Array.isArray(layout) || layout.length !== width ||
      !layout.every((q) => Number.isInteger(q) && q >= 0 && q <= 63) ||
      new Set(layout).size !== width) throw new Error("invalid physical layout")
}

function normalizeTarget(target: Physical): Logical {
  if (target.schema !== "qev.physical-circuit.v0") throw new Error("target schema")
  assertLayout(target.physical_layout, target.logical_width)
  const inverse = new Map(target.physical_layout.map((physical, logical) => [physical, logical]))
  const operations = target.operations.map((op, ordinal) => {
    if (op.ordinal !== ordinal || !["H","X","CX","RZ"].includes(op.gate)) throw new Error("target operation")
    const logical = op.physical_qubits.map((q) => {
      const mapped = inverse.get(q)
      if (mapped === undefined) throw new Error("unmapped physical qubit")
      return mapped
    })
    const arity = op.gate === "CX" ? 2 : 1
    if (logical.length !== arity) throw new Error("target arity")
    return { ordinal, gate: op.gate, logical_qubits: logical, parameter: op.parameter }
  })
  const expectedMeasurement = JSON.stringify({
    kind: "MEASURE_ALL", physical_order_for_logical: target.physical_layout,
  })
  if (JSON.stringify(target.measurement) !== expectedMeasurement) throw new Error("measurement mapping")
  return {
    schema: "qev.logical-circuit.v0", width: target.logical_width, operations,
    measurement: { kind: "MEASURE_ALL", logical_order: Array.from({length: target.logical_width}, (_, i) => i) },
  }
}
async function main() {
  const [logicalPath, physicalPath] = process.argv.slice(2)
  if (!logicalPath || !physicalPath) {
    throw new Error("usage: bun qev/quantum_transpile_tsei_bridge.ts <logical.json> <physical.json>")
  }
  const logical = readJson(logicalPath) as Logical
  const physical = readJson(physicalPath) as Physical
  const profile = defineTransformationProfileV0<Logical, Physical, Logical>({
    transformation_profile_id: "qev-quantum-layout-transpilation-v0",
    transformation_family: "logical-to-physical-layout-transpilation",
    source_object_kind: "qev.logical-circuit.v0",
    target_object_kind: "qev.physical-circuit.v0",
    recompute_procedure_id: "normalize-physical-layout-to-logical-v0",
    comparison_rule_id: "canonicalIdentityJson@tsei-v0",
    history_sensitive_policy: "classify",
    precondition: (artifact) => artifact?.schema === "qev.logical-circuit.v0"
      ? { ok: true } : { ok: false, reason: "not_logical_circuit" },
    transform: () => physical,
    recompute_source: (artifact) => ({ state: "evaluated", value: artifact }),
    recompute_target: (artifact) => ({ state: "evaluated", value: normalizeTarget(artifact) }),
    normative_projection: (value) => value,
    stability_projection: (value) => ({
      schema: value.schema, width: value.width, operation_count: value.operations.length,
      measurement_kind: value.measurement.kind,
    }),
    allowed_variant_projection: () => ({ representation: "logical-vs-physical-layout" }),
    forbidden_variant_projection: (value) => ({
      operation_sequence: value.operations.map((op) => [op.gate, op.logical_qubits, op.parameter]),
      measurement: value.measurement,
    }),
  })
  const result = await evaluateTransformationStabilityV0(profile, logical)
  process.stdout.write(JSON.stringify({
    tseiSourceCommit: "45b46bf7df3a60b32583291f577a36bf19d22f00",
    profileId: "qev-quantum-layout-transpilation-v0",
    result,
  }, null, 2) + "\n")
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
