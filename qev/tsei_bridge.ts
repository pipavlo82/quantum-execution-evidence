import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import {
  defineTransformationProfileV0,
  evaluateTransformationStabilityV0,
} from "../vendor/tsei-v0/src/receiptos/challenge/transformation-stability"

type Artifact = Record<string, any>
type Mode = "stable" | "allowed_variant" | "history_sensitive" | "violation"

function readJson(path: string) {
  return JSON.parse(readFileSync(resolve(path), "utf8"))
}

function project(bundle: Artifact) {
  const receipt = bundle.receipt
  const result = bundle.canonicalResult
  return {
    normative: {
      verificationProfileDigest: receipt.verificationProfileDigest,
      outcome: receipt.outcome,
      reasonCode: receipt.reasonCode,
      resultDigest: receipt.resultDigest,
    },
    stability: {
      evidenceSetDigest: receipt.evidenceSetDigest,
    },
    allowed: {
      payloadOrder: Object.keys(bundle.payloadsBase64 ?? {}),
    },
    forbidden: {
      claimDigest: receipt.claimDigest,
    },
    result,
  }
}
function transform(source: Artifact, mode: Mode): Artifact {
  const target = structuredClone(source)
  if (mode === "allowed_variant") {
    const entries = Object.entries(target.payloadsBase64 ?? {}).reverse()
    target.payloadsBase64 = Object.fromEntries(entries)
  } else if (mode === "history_sensitive") {
    target.receipt.evidenceSetDigest = "1".repeat(64)
  } else if (mode === "violation") {
    target.receipt.resultDigest = "2".repeat(64)
  }
  return target
}

async function evaluate(source: Artifact, mode: Mode) {
  const profile = defineTransformationProfileV0<Artifact, Artifact, ReturnType<typeof project>>({
    transformation_profile_id: "qev-rvr-artifact-preservation-v0",
    transformation_family: "qev-rvr-representation-transform",
    source_object_kind: "rvr-qev-bundle",
    target_object_kind: "rvr-qev-bundle",
    recompute_procedure_id: "qev-rvr-protected-surface-recompute-v0",
    comparison_rule_id: "canonicalIdentityJson@tsei-v0",
    history_sensitive_policy: "classify",
    precondition: (artifact) => artifact?.receipt && artifact?.canonicalResult
      ? { ok: true } : { ok: false, reason: "not_rvr_qev_bundle" },
    transform: (artifact) => transform(artifact, mode),
    recompute_source: (artifact) => ({ state: "evaluated", value: project(artifact) }),
    recompute_target: (artifact) => ({ state: "evaluated", value: project(artifact) }),
    normative_projection: (result) => result.normative,
    stability_projection: (result) => result.stability,
    allowed_variant_projection: (result) => result.allowed,
    forbidden_variant_projection: (result) => result.forbidden,
  })
  return evaluateTransformationStabilityV0(profile, source)
}
async function main() {
  const [sourcePath, modeArg = "stable"] = process.argv.slice(2)
  if (!sourcePath) throw new Error("usage: bun qev/tsei_bridge.ts <rvr-bundle.json> [stable|allowed_variant|history_sensitive|violation]")
  if (!["stable", "allowed_variant", "history_sensitive", "violation"].includes(modeArg)) {
    throw new Error("unsupported mode")
  }
  const source = readJson(sourcePath)
  const result = await evaluate(source, modeArg as Mode)
  process.stdout.write(JSON.stringify({
    tseiSourceCommit: "45b46bf7df3a60b32583291f577a36bf19d22f00",
    profileId: "qev-rvr-artifact-preservation-v0",
    mode: modeArg,
    result,
  }, null, 2) + "\n")
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
