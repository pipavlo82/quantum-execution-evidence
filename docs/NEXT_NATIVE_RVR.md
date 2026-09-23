# Superseded native RVR handoff

The native RVR step is implemented and merged in PR #1. Native ReceiptOS
packaging (PR #2), native TSEI artifact preservation (PR #3), layout preservation
(PR #4), provider binding (PR #6), IBM recorded adapter (PR #7), IBM live replay
(PR #8), Moth counts (PR #9) and the cross-provider model (PR #10) are also merged.
PR #5 removed an obsolete reference. None of these is a pending RVR next step.

Use [the canonical project status](../README.md#current-project-status-and-architecture)
and its [next concrete work](../README.md#current-limitations-and-next-concrete-work).
The [RVR profile](RVR_QEV_PROFILE_V0.md) remains scoped to the synthetic preserved
request/package relation; [live replay](LIVE_CAPTURE_REPLAY_V1.md) is a separate
profile. The additive [Moth counts-native RVR profile](MOTH_COUNTS_RVR_V0.md)
merged in PR #13 with its own counts-only relation, mutation gate and replay.
The separate [Moth ReceiptOS packaging](MOTH_RECEIPTOS_V0.md) now binds that exact
bundle and verifies its saved export through native ReceiptOS functions and
fresh RVR replay. TSEI integration remains absent for Moth; the old counts,
RVR and cross-provider profiles retain their scoped historical contracts.

The original design handoff remains available in
[the audited baseline](https://github.com/pipavlo82/quantum-execution-evidence/blob/44b25926be923a9cab846bca36a8a7a665774b22/docs/NEXT_NATIVE_RVR.md).
Its future-tense language records historical planning, not current project status.
