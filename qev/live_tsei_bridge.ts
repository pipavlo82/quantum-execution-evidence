import { readFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import { defineTransformationProfileV0, evaluateTransformationStabilityV0 } from '../vendor/tsei-v0/src/receiptos/challenge/transformation-stability'

const [python, root] = process.argv.slice(2)
const input = JSON.parse(readFileSync(0, 'utf8'))
function recompute(snapshot: unknown) {
  // Execute the exact arithmetic implementation separately for each side,
  // inside the native evaluator callbacks. Stored projections are never input.
  const run = spawnSync(python, ['-B', ...(input.optimized ? ['-O'] : []), '-m', 'qev.live_math'], {
    cwd: root, input: JSON.stringify(snapshot), encoding: 'utf8', timeout: 30000,
    maxBuffer: 4194304,
  })
  if (run.status !== 0) return { state: 'unresolved' as const, reason: 'operator_process_failed' }
  return JSON.parse(run.stdout)
}
const profile = defineTransformationProfileV0<any, any, any>({
  transformation_profile_id: 'qev-live-ideal-two-qubit-isa-v1',
  transformation_family: 'logical-to-isa-ideal-operator',
  source_object_kind: 'sdk-operation-snapshot', target_object_kind: 'sdk-operation-snapshot',
  recompute_procedure_id: 'qev-exact-q-zeta8-full-operator-v1',
  comparison_rule_id: 'canonicalIdentityJson@tsei-v0', history_sensitive_policy: 'classify',
  precondition: () => ({ ok: true }),
  transform: () => input.target,
  recompute_source: recompute, recompute_target: recompute,
  normative_projection: value => ({ operator: value.operator, measurement: value.measurement,
    basis: value.basis, angleMap: value.angleMap, globalPhasePolicy: value.globalPhasePolicy }),
  stability_projection: () => null,
  allowed_variant_projection: value => ({ tokens: value.tokens, originalWidth: value.originalWidth }),
  forbidden_variant_projection: () => null,
})
const result = await evaluateTransformationStabilityV0(profile, input.source)
process.stdout.write(JSON.stringify(result) + '\n')
