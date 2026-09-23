import { readFileSync } from 'node:fs'
import { computeReceiptRoot } from '../vendor/receiptos-v0/src/receiptos/canon/receipt-root'
import { verifyHandoffReceiptRoot } from '../vendor/receiptos-v0/src/receiptos/verify/verify-receipt'
import { createCapsuleSummaryFromEvidence } from '../vendor/receiptos-v0/src/receiptos/capsule/evidence-capsule-v0'
import { createPortableProofObjectV0 } from '../vendor/receiptos-v0/src/receiptos/capsule/portable-proof-object-v0'

const input = JSON.parse(readFileSync(0, 'utf8'))
if (input.mode !== 'create' && input.mode !== 'verify') throw new Error('BRIDGE_MODE')
const evidence = input.evidence
if (input.mode === 'create') evidence.anchor.receipt_root = computeReceiptRoot(evidence)
const verification = await verifyHandoffReceiptRoot(evidence)
const ref = 'inline:rvr-moth-counts-bundle'
const summary = await createCapsuleSummaryFromEvidence(evidence, ref)
const proof = await createPortableProofObjectV0(evidence, { sourceEvidenceRef: ref })
process.stdout.write(JSON.stringify({ evidence, verification, summary, proof }) + '\n')
