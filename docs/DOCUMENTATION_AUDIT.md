# Documentation and consistency audit after PR #10

## Verified baseline

Canonical `origin/main` and PR #10 merge:
`44b25926be923a9cab846bca36a8a7a665774b22`.
Direct parents are PR #9 main `6a4e1206a4d002be90b8884774e15fdada9deef6` and
PR #10 head `d934e41f4faad0f6a93df268563c56f753e98458`.
[Merge CI 35802120341](https://github.com/pipavlo82/quantum-execution-evidence/actions/runs/35802120341)
completed successfully. Feature-head CI runs 35801816218 and 35801831320 also
succeeded. These are verified historical checkpoints, not assertions about
future branch heads. The documentation PR remains a separate reviewable change.

## Coverage and corrected claims

All 16 pre-existing Markdown files were inspected: the sole README, root
licensing, 13 project documents and the vendored TSEI specification. There are
no additional README variants or examples/profile Markdown files at this base.
CLI examples, profile JSON, source inventories, reference metadata, licenses,
runtime bridges, tests and every CI step were also checked. This new report
makes 17 Markdown files. [documentation-audit.json](documentation-audit.json)
enumerates every document, profile ID, frozen byte hash and expected count.

| Document | Correction or preservation decision |
| --- | --- |
| [README](../README.md) | Replaced synthetic-only overview and concatenated headings; added canonical architecture, actual IBM/Moth/common paths, runtimes, replay, validation, limitations and next work |
| [Integration map](INTEGRATION_MAP.md) | Replaced ReceiptOS/TSEI NOT_INTEGRATED and Semantic-ABI-only vendor claims with scoped executed surfaces; retained actual reference-only components |
| [RVR handoff](NEXT_NATIVE_RVR.md) | Replaced completed-on-feature/pending ReceiptOS wording with merged history and current status links; original planning is retained in Git history |
| [Provenance](PROVENANCE.md) | Scoped original extraction to its historical time; documented subsequent integrations, captures, 28 vendors and two source locks; retained original SHAs |
| [Licensing](../LICENSING.md) | Retained pending root license and upstream licenses; clarified inherited reference metadata versus later vendoring and Moth evidence/OpenAPI boundaries |
| [Synthetic contract](CONTRACT.md) | Scoped synthetic-only restrictions to quantum-evidence.v0; replaced obsolete four-vendor/all-technical-files inventory claim with current finite inventories |
| [Provider binding](PROVIDER_EXECUTION_BINDING_V0.md) | Corrected EXECUTION_BOUND to actual BOUND; described eight axes and lack of independent expected-job-ID comparison; IBM adapter is implemented |
| [IBM adapter](IBM_QUANTUM_RUNTIME_ADAPTER_V0.md) | Removed no-live-job claim; distinguished synthetic demo from preserved live replay and caller-supplied capture arguments; utility retrieves, does not submit |
| [Layout profile](QUANTUM_TRANSPILATION_BOUNDARY_V0.md) | Identified implemented profile and command; distinguished later live ideal relation; provider artifacts alone cannot establish stronger claims |
| [Legacy ReceiptOS](RECEIPTOS_QEV_CAPSULE_V0.md) | Corrected independent-native-root-verifier claim: capsule/provenance builders and ID helpers execute, root/summary/proof assembly remains local; explained epoch placeholders and full-payload difference |
| [TSEI artifact profile](TSEI_QEV_PROFILE_V0.md) | Replaced future stack wording with actual evaluation/composition order and command; ReceiptOS is a separate layer |
| [RVR specification](RVR_QEV_PROFILE_V0.md) | Correct profile-scoped contract; frozen normative dependency retained byte-for-byte |
| [IBM live specification](LIVE_CAPTURE_REPLAY_V1.md) | Correct finite ideal/replay contract; frozen normative dependency retained byte-for-byte |
| [Moth specification](MOTH_COMET_COUNTS_V0.md) | Correct counts/provenance/nonintegration limits retained; source-lock-refresh paragraph records PR #9 history |
| [Cross-provider specification](CROSS_PROVIDER_EVIDENCE_V0.md) | Correct capabilities and actual execution limits retained; preservation paragraph describes PR #10's additive implementation |
| [Vendored TSEI specification](../vendor/tsei-v0/docs/TRANSFORMATION_STABLE_EVIDENCE_INTEROPERABILITY_V0.md) | Exact upstream bytes retained, including upstream status, future-work and conformance references; these are not new QEV implementation claims |

Package metadata now describes synthetic and preserved live verification.
The frozen legacy CLI help string still says OFFLINE SYNTHETIC: it predates the
additive live subcommands and is not the canonical project status. Changing its
runtime bytes would change a live-profile dependency. Likewise legacy demo
fields such as `providerSpecificAdapter = NOT_INTEGRATED` and
`liveIBMJob = NOT_EXECUTED` describe their finite demo, not the whole repository.
Their bytes and semantics have not been retroactively rewritten.

The legacy ReceiptOS document's required-control list is a design obligation,
not a claim that each item is an independently executed saved-artifact test.
Its anchor-independence unit test inspects the bridge's anchor-removal source
and the existing packaged root; it does not recompute a mutated saved capsule.
The legacy bridge has no saved-export replay CLI. The live profile supplies
actual native root and attachment replay/tamper controls for its own artifacts.

## Identities and source closure

All pre-existing runtime, tests, profiles, corpus/capture bytes, vendor bytes,
OpenAPI observation and reference-pin metadata remain identical to the exact
baseline. In particular, neither RVR profile nor the cross-provider eight-file
lock is repinned. Main source-lock changes cover only modified documentation,
package description and workflow. No inventory entry is removed or reinterpreted.
The audit report, metadata and checker are new Git-bound maintainer artifacts
outside the runtime source inventories; this avoids altering native profile
identity just to add documentation QA. The checker rejects changes to every
pre-existing path outside the explicitly reviewed mutable set.

The source counts remain 214 local + 28 vendored and eight cross-provider files;
both source locks exclude themselves. The 16 inherited reference records are
not executable dependency counts or freshly fetched upstream source evidence.
All four vendor families retain exact upstream commits and license hashes.
Upstream paths inside the frozen TSEI specification refer to crystal-receipt
at `45b46bf7df3a60b32583291f577a36bf19d22f00`, not missing QEV implementation files.
Only the declared vendored subset is present; upstream Rust/tests are not run
or claimed as independent QEV implementation evidence.

## Reproducible validation contract

The full suite is 259 normal and 259 optimized tests, including 41 cross-provider
tests. All legacy demos remain required. The synthetic corpus is 44/44 cases.
Source mutations require QEV 7/7 (five controls each), RVR 7/7 (three), IBM live
7/7 (three), Moth 7/7 (three) and cross-provider 12/12 (three): 40 total, zero
survived/crashed/unapplied/control-broken. Input-mutation demos separately require
eight provider-binding refutations and six IBM adapter refutations plus malformed
bit rejection. TSEI artifact cases cover stable, allowed variant, history-sensitive
and violation; layout cases cover two stable layouts, one violation and two unresolved.

Run the commands in [README validation](../README.md#validation).
[CI](../.github/workflows/ci.yml) runs Python 3.12/3.13 with Node 22 and Bun 1.3.14,
all legacy gates, source locks, IBM export/replay/mutations, Moth replay/mutations,
both cross-provider reports/replays and mutations. The live/Moth/cross outputs
are compared byte-for-byte across normal/repeat/optimized execution.
`python -B -m tools.check_docs` checks full document inventory, internal links and
anchors, code-path references, CLI module/subcommand names, discovered test count,
profile IDs/dependency digests, source counts, exact frozen hashes and CI steps.
It is a finite consistency check, not a semantic proof of all prose or external
URL availability. `git diff --check` remains the final workflow gate.

The audit performs no provider requests, credential reads or new QPU jobs.
GitHub metadata/CI observations are distinct from provider-network access.
`providerAuthentication` stays NOT_ESTABLISHED for both captures. Moth remains
counts-only with no circuit/measurement provenance or native receipt integration;
the common model does not add capabilities. No entropy, hardware authenticity,
general compiler correctness or independent authorship claim is introduced.
