# Native TSEI profile for QEV RVR artifacts

Status: experimental native integration.

This lane applies the standalone **Transformation-Stable Evidence Interoperability Specification v0** to native QEV RVR artifacts.

Pinned TSEI reference source:

`45b46bf7df3a60b32583291f577a36bf19d22f00`

The generic TSEI mechanism is used as a transformation-preservation layer. RVR remains the lower-layer verification relation. ReceiptOS remains a separate portable packaging layer.

## Protected relation

Profile: `qev-rvr-artifact-preservation-v0`.

The initial profile declares four surfaces:

- **normative** — RVR verification-profile identity plus semantic outcome, reason code, and canonical result digest.
- **stability/history-sensitive** — RVR evidence-set identity.
- **allowed variant** — payload-map representation order.
- **forbidden** — claim identity.

These choices are profile semantics, not universal TSEI semantics.
## Expected classification

The integration freezes four initial cases:

| case | expected TSEI classification |
|---|---|
| unchanged native RVR artifact | `stable` |
| payload-map representation reorder only | `stable`, with `allowed_variant_changed=true` |
| evidence-set identity changes while normative semantic result is preserved | `history_sensitive` |
| canonical semantic result digest changes | `violation` |

This directly preserves the distinction established by the native RVR profile: stochastic/evidence identity may change without automatically becoming a semantic-preservation violation.

## Trust boundary

TSEI independently recomputes the profile's declared projections from source and transformed target artifacts. It does not trust a stored transformation verdict.

It still trusts the QEV-specific adapter/profile code that declares:
- applicability;
- transformation;
- recomputation;
- protected projections.

Therefore this integration establishes preservation only under this declared profile and tested transformation family.
## Non-claims

A TSEI `stable` result does not establish:
- authentic QPU execution;
- provider authenticity;
- sampler independence;
- distribution equality;
- min-entropy;
- cryptographic RNG;
- device certification.

It also does not mean ReceiptOS packaging was verified; that is a separate layer.

The intended stack is:

```text
QEV evidence
  -> native RVR verification
  -> native ReceiptOS portable packaging
  -> native TSEI transformation-preservation evaluation
```

The arrows denote composition boundaries, not claim inheritance. Each layer may only establish its own declared relation.
