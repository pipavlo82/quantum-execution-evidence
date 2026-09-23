# Provenance

The historical extraction below is distinct from the current integrated project.
See [canonical status](../README.md#current-project-status-and-architecture).

## Original extraction boundary

This repository is a **new Git root**, not a fork and not a continuation of another Git history.

The implementation was extracted from a locally reviewed Quantum Execution Evidence lane that lived inside a separate Verifiable Composition prototype. The source project was pinned at commit:

`7e2830c9fe0b30b6b2db9417ebe02b282a57787a`

The reviewed pre-extraction checker SHA-256 was:

`d13bda9e710d6d70f43b2e9fdb3ecee6f3d99e06c777d38c57c8094d7fc16789`

The reviewed pre-extraction experiment source-lock SHA-256 was:

`562b9e79a1f64e173215f8f9f82594e9a6d297a6634d734b8e6724f1d28e8e03`.

Extraction was performed from a read-only seed snapshot whose complete manifest was independently checked before repository construction. The standalone package changes import/layout and source-lock mechanics so it has no runtime dependency on the former composition project or on machine-specific absolute paths.

This provenance statement does **not** claim that every standalone file is byte-identical to the former lane. Corpus request/package bytes and their manifest semantics were preserved; standalone code and documentation were deliberately adapted for independent execution.

At the original extraction, the only copied executable upstream dependency was
the minimal byte-pinned Semantic ABI linker under `vendor/semantic-abi/`.
Its original license files remain retained. That extraction did not invoke a
QPU/provider API, RVR, ReceiptOS or TSEI; later integrations are recorded below.
These historical statements do not describe the current runtime inventory.

Expectation authorship remains `SAME_TASK_AUTHOR_NOT_INDEPENDENT`. Source hashes prove byte identity, not authorship independence or semantic correctness.

## RVR v0 primitive vendoring

Native RVR profile work vendors three exact files from RVR commit `549a7e150ddc75df88dc90ee93f331fea7464567`: the upstream license, independent Python adapter, and generic Verification Profile Manifest schema. The adapter SHA-256 is `03505efc8ee993f118fad2c71f706870d25de0da61a393a1f18f7b310bded235`.

The QEV-specific Verification Profile, schema, vectors, expected results, and mutation witnesses are authored in this repository. They do not alter the vendored RVR bytes.

## Current integrated source and capture provenance

PR #1 added native RVR, #2 ReceiptOS capsule/provenance builders and proof helpers,
#3 native TSEI artifact preservation, #4 native layout preservation, #6 provider
binding, #7 the recorded IBM adapter, #8 IBM live replay, #9 Moth counts and
#10 the common evidence model. All are merged at the audited baseline
`44b25926be923a9cab846bca36a8a7a665774b22`; no publication status is inferred from
the older feature-branch handoffs.

There are now 28 vendored files: Semantic ABI 4, RVR 3, ReceiptOS 12 and TSEI 9.
ReceiptOS and TSEI use `45b46bf7df3a60b32583291f577a36bf19d22f00`;
Semantic ABI uses `d15c666dfccff17f7350fe97d2fc7b71cb2cbaee`.
See [the integration map](INTEGRATION_MAP.md) for executable versus data surfaces
and the legacy/live ReceiptOS distinction. No runtime dependency on the former
workspace has been reintroduced.

The IBM selected capture preserves 15 historical payload files plus its seed
manifest and independent claim. The Moth capture manifest preserves 16 original
acquisition files; the manifest itself and the independent claim are separate.
Moth OpenAPI bytes are an upstream documentation observation, not engine source
or a license grant. Acquisition labels and reported backend/job fields are not
cryptographic provider authentication. Hash-encoding inference is identified in
[the Moth contract](MOTH_COMET_COUNTS_V0.md).

The main lock covers 214 local + 28 vendor files; the additive cross-provider
lock covers eight files. Historical `reference-pins.json` records remain unchanged
as inherited metadata. Some referenced bytes were subsequently vendored under
their own explicit runtime inventory; the metadata's old extraction wording
must not be read as a current nonintegration claim.

The documentation audit preserves every runtime file, profile, fixture, vendor
byte and captured source snapshot. It updates current prose, package description,
CI documentation checks and the corresponding main source-lock entries only.
New audit documentation/checker metadata is Git-bound outside runtime profiles.
No new capture, provider-network access or credential use is part of replay or
this audit. Source identity and locally reproduced results do not establish
hardware authenticity, entropy or independent authorship.

## Additive Moth counts-native RVR

The new `rvr-qev-moth-counts-v0` implementation starts from PR #12 merge
`68c306b6b25d392f4de290e904f57e20fa3c0a0f`, after merged documentation audit
PR #11 and Apache-2.0 licensing PR #12. It adds repository-authored profile,
relation, replay, tests and seven source mutants. The original capture, counts
verifier, vendor bytes and older profile identities remain unchanged. Native
RVR primitives use the already pinned adapter above; no new upstream code is
downloaded. The 13-file additive lock and native transitive dependency manifest
are documented in [the new specification](MOTH_COUNTS_RVR_V0.md). No new QPU job,
provider network, credential use or cryptographic provider authentication is
part of this implementation. Apache-2.0 applies to new authored code and prose,
not as a relicensing of the preserved acquisition evidence.
