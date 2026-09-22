import { createHash } from "node:crypto"
import { readFileSync } from "node:fs"
import { basename, resolve } from "node:path"

import {
  createEvidenceCapsuleV0,
  createProvenanceSummaryV0,
} from "../vendor/receiptos-v0/src/receiptos/capsule/evidence-capsule-v0"
import {
  deriveProofObjectId,
  deriveProofRef,
} from "../vendor/receiptos-v0/src/receiptos/capsule/portable-proof-object-v0"

type JsonRecord = Record<string, any>

function canonicalize(value: any): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`
  return `{${Object.keys(value).filter((key) => value[key] !== undefined).sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalize(value[key])}`).join(",")}}`
}

function sha256Hex(value: string) {
  return createHash("sha256").update(value).digest("hex")
}

function stripAnchor<T extends JsonRecord>(value: T) {
  const clone = { ...value }
  delete clone.anchor
  return clone
}
function computeReceiptRoot(value: JsonRecord) {
  return `0x${sha256Hex(canonicalize(stripAnchor(value)))}`
}

function mapRvrStatus(outcome: string): "completed" | "error" {
  return outcome === "VERIFIED" ? "completed" : "error"
}

function makeEvidence(rvrBundle: JsonRecord, recomputation: JsonRecord): JsonRecord {
  const receipt = rvrBundle.receipt
  const result = rvrBundle.canonicalResult
  const evidenceSet = rvrBundle.evidenceSet
  const profileId = rvrBundle.verificationProfile.profileId
  const sourceDigest = sha256Hex(canonicalize({
    claimDigest: receipt.claimDigest,
    evidenceSetDigest: receipt.evidenceSetDigest,
    resultDigest: receipt.resultDigest,
  }))
  const now = 0

  const evidence: JsonRecord = {
    schema: "stealth.session.evidence.v1",
    session_id: `qev-rvr-${receipt.claimDigest.slice(0, 16)}`,
    directory: "receiptos://qev/native-rvr",
    task: {
      title: "QEV native RVR verification artifact",
      prompt: "Package the native RVR result without elevating stochastic or physical-QPU claims.",
    },
    agent: { id: "qev-rvr-adapter-v0", runtime: "QEV" },
    scope: { permission: null },
    authorization: {
      delegation_ref: null, delegator: null, agent_operator: "qev-rvr-adapter-v0",
      target: "receiptos://qev/native-rvr", allowed_actions: [],
      authorization_valid_from: null, authorization_expiry: null,
      authorization_checked_at: now,
      authorization_state_hash: receipt.verificationProfileDigest,
      authorized_at_execution: null,
    },
    execution: [{
      call_id: "native-rvr-qev-v0", tool: "rvr-qev-preserved-observation-v0",
      action_performed: `${result.outcome}:${result.reasonCode}`,
      target: profileId, execution_timestamp: now, completed_timestamp: now,
      status: mapRvrStatus(result.outcome), scope_match: null,
    }],
    commands: [{
      command: "python -m qev rvr-demo",
      exit_code: result.outcome === "VERIFIED" ? 0 : 1,
      stdout_summary: `RVR outcome=${result.outcome}; recomputation=${recomputation.recomputationStatus}`,
    }],
    changes: {
      files_changed: evidenceSet.members.map((member: JsonRecord) => `evidence:${member.id}`),
      diff_sha256: sourceDigest,
    },
    anchor: {
      receipt_root: "", merkle_proof_status: "not attached", merkle_root: null,
      merkle_leaf_index: null, merkle_proof: [], onchain_anchor_status: "not anchored",
      network: "local/off-chain", contract: null, tx_hash: null, verifier_status: "not verified",
    },
    metadata: { message_count: 1, diff_count: evidenceSet.members.length,
      generated_by: "qev.receiptos.native-rvr-adapter.v0" },
  }
  evidence.anchor.receipt_root = computeReceiptRoot(evidence)
  return evidence
}

function makeCapsuleSummary(evidence: JsonRecord): JsonRecord {
  const root = computeReceiptRoot(evidence)
  const stored = evidence.anchor.receipt_root
  const match = stored.toLowerCase() === root.toLowerCase()
  const outcome = evidence.execution[0].status === "completed"
  const sections = [
    { id: "payload", label: "Payload / Action", status: "present",
      summary: evidence.task.title, sourceFields: ["task.title", "task.prompt", "commands"] },
    { id: "policy_boundary", label: "Policy Boundary", status: "missing",
      summary: "No ReceiptOS scope lease asserted by the QEV adapter.", sourceFields: ["scope.permission", "scope.lease"] },
    { id: "authorization", label: "Authorization", status: "present",
      summary: "No execution authority is inferred from the RVR artifact.", sourceFields: ["authorization.allowed_actions"] },
    { id: "decision_trace", label: "Decision Trace", status: "present",
      summary: "Native RVR outcome and recomputation status are preserved.", sourceFields: ["execution", "commands"] },
    { id: "execution", label: "Execution", status: "present",
      summary: "One native RVR verification record packaged.", sourceFields: ["execution", "commands"] },
    { id: "evidence", label: "Evidence Record", status: "present",
      summary: `${evidence.changes.files_changed.length} committed RVR evidence member(s).`,
      sourceFields: ["changes.files_changed", "changes.diff_sha256"] },
    { id: "counterfactual", label: "Counterfactual / Denied Action", status: "missing",
      summary: "No denied-action claim is introduced.", sourceFields: ["execution.status"] },
    { id: "result", label: "Result", status: outcome ? "present" : "invalid",
      summary: outcome ? "Native RVR relation is VERIFIED." : "Native RVR relation is not VERIFIED.",
      sourceFields: ["commands.exit_code", "commands.stdout_summary"] },
    { id: "receipt_root", label: "Receipt Root", status: match ? "valid" : "mismatch",
      summary: match ? "Stored receipt_root matches recomputed canonical root." : "Receipt root mismatch.",
      sourceFields: ["anchor.receipt_root"] },
    { id: "merkle", label: "Merkle Proof", status: "pending",
      summary: "No local Merkle proof attached.", sourceFields: ["anchor.merkle_proof_status"] },
    { id: "anchor", label: "Anchor", status: "missing",
      summary: "No external anchor recorded.", sourceFields: ["anchor.onchain_anchor_status"] },
    { id: "replay_manifest", label: "Replay Manifest", status: "present",
      summary: "Replay requires the committed QEV RVR bundle and pinned profile dependencies.",
      sourceFields: ["session_id", "commands", "changes.diff_sha256", "anchor.receipt_root"] },
    { id: "verifier", label: "Verifier", status: match ? "verified" : "mismatch",
      summary: match ? "Portable verifier confirmed the ReceiptOS root." : "Portable verifier detected mismatch.",
      sourceFields: ["anchor.receipt_root"] },
  ]
  return {
    schema: "receiptos.capsule_summary.v0", source_evidence: "inline:qev-rvr-bundle",
    receipt_root: stored, computed_receipt_root: root,
    receipt_verification: { ok: match, status: match ? "verified" : "mismatch" },
    local_merkle: { present: false, ok: false, status: "missing" },
    capsule: { sections }, crystal_mapping: {}, render_plan: {},
  }
}

async function main() {
  const [bundlePath, recomputationPath, outputPath] = process.argv.slice(2)
  if (!bundlePath || !recomputationPath || !outputPath) {
    throw new Error("usage: bun qev/receiptos_bridge.ts <rvr-bundle.json> <recomputation.json> <output.json>")
  }
  const bundle = JSON.parse(readFileSync(resolve(bundlePath), "utf8"))
  const recomputation = JSON.parse(readFileSync(resolve(recomputationPath), "utf8"))
  const evidence = makeEvidence(bundle, recomputation)
  const summary = makeCapsuleSummary(evidence)
  const evidenceCapsule = createEvidenceCapsuleV0(summary as any)
  const provenanceSummary = createProvenanceSummaryV0(evidenceCapsule)
  const proofObjectId = deriveProofObjectId(summary.receipt_root)
  const object = {
    schema: "receiptos.portable_proof_object.v0",
    proof_object_id: proofObjectId,
    proof_system: "ReceiptOS",
    receipt_root: summary.receipt_root,
    proof_ref: deriveProofRef(proofObjectId),
    replay_ref: `receiptos://replay/${encodeURIComponent(evidence.session_id)}`,
    anchor_ref: null,
    created_at: new Date(0).toISOString(),
    relation_type: "imported",
    project_refs: ["qev-native-rvr"],
    source_evidence_ref: "inline:qev-rvr-bundle",
    producer: {
      runtime: "QEV", agent_id: "qev-rvr-adapter-v0",
      generated_by: evidence.metadata.generated_by,
      source_schema: evidence.schema,
    },
    metadata: {
      label: evidence.task.title, session_id: evidence.session_id,
      directory: evidence.directory, position_id: "qev-native-rvr",
    },
    evidence_capsule: evidenceCapsule,
    provenance_summary: provenanceSummary,
  }
  await Bun.write(resolve(outputPath), JSON.stringify({ evidence, portableProofObject: object }, null, 2) + "\n")
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
