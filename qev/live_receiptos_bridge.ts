import { readFileSync } from 'node:fs'
import { computeReceiptRoot } from '../vendor/receiptos-v0/src/receiptos/canon/receipt-root'
import { verifyHandoffReceiptRoot } from '../vendor/receiptos-v0/src/receiptos/verify/verify-receipt'
import { createCapsuleSummaryFromEvidence } from '../vendor/receiptos-v0/src/receiptos/capsule/evidence-capsule-v0'
import { createPortableProofObjectV0 } from '../vendor/receiptos-v0/src/receiptos/capsule/portable-proof-object-v0'

const input = JSON.parse(readFileSync(0, 'utf8'))
const evidence = input.evidence
if (input.mode === 'create') evidence.anchor.receipt_root = computeReceiptRoot(evidence)
if (input.mode === 'root-probe') {
  process.stdout.write(JSON.stringify({ root: computeReceiptRoot(evidence) }) + '\n')
} else {
  const verification = await verifyHandoffReceiptRoot(evidence)
  const summary = await createCapsuleSummaryFromEvidence(evidence, 'inline:rvr-live-bundle')
  const proof = await createPortableProofObjectV0(evidence, { sourceEvidenceRef: 'inline:rvr-live-bundle' })
  process.stdout.write(JSON.stringify({ evidence, verification, summary, proof }) + '\n')
}
