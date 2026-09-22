"""Native RVR v0 envelope + QEV preserved-observation profile.

RVR canonicalization, profile audit, evidence closure, receipt validation, and
recomputation status semantics come from exact vendored RVR v0 adapter bytes.
QEV domain evaluation is profile-specific and remains narrower than full QEV CLI.
"""
from __future__ import annotations
import base64
import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

from . import checker

ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "profiles/qev-preserved-observation-v0"
PROFILE_PATH = PROFILE_DIR / "verification-profile.json"
MANIFEST_SCHEMA_PATH = ROOT / "vendor/rvr-v0/verification-profile-manifest.schema.json"
VENDOR_ADAPTER_PATH = ROOT / "vendor/rvr-v0/adapter.py"

def _load_rvr():
    spec = importlib.util.spec_from_file_location("qev_vendored_rvr_v0", VENDOR_ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("vendored RVR adapter unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROFILE_PACKAGE_ROOT = ROOT
    return module

rvr = _load_rvr()

def _load_json(path: Path) -> Any:
    return rvr.parse_json_bytes(path.read_bytes(), path.as_posix())
def load_profile_context():
    manifest_bytes = MANIFEST_SCHEMA_PATH.read_bytes()
    manifest_schema = rvr.parse_json_bytes(manifest_bytes, MANIFEST_SCHEMA_PATH.as_posix())
    profile = _load_json(PROFILE_PATH)
    profile_digest, constraints, pinned = rvr.audit_profile(
        profile, manifest_schema, manifest_bytes
    )
    schema = rvr.parse_json_bytes(pinned["rvr-schema"], "rvr-schema")
    return profile, profile_digest, constraints, pinned, schema, manifest_schema, manifest_bytes

def _axis_result(input_status: str, request_binding: str, integrity: str, deterministic: str,
                 claim: dict[str, Any], outcome: str, reason: str) -> dict[str, Any]:
    return {
        "schema": "rvr.qev.canonical-result.v0",
        "outcome": outcome,
        "reasonCode": reason,
        "evaluation": {
            "operation": "QEV_RECOMPUTE_PRESERVED",
            "requestEvidenceMember": claim["requestEvidenceMember"],
            "packageEvidenceMember": claim["packageEvidenceMember"],
            "inputStatus": input_status,
            "requestBinding": request_binding,
            "integrity": integrity,
            "deterministicVerification": deterministic,
        },
    }

def evaluate_qev(claim: dict[str, Any], evidence_set: dict[str, Any],
                 payloads: dict[str, bytes], schema: dict[str, Any]) -> dict[str, Any]:
    request_id = claim["requestEvidenceMember"]
    package_id = claim["packageEvidenceMember"]
    by_id = {member["id"]: member for member in evidence_set["members"]}
    if request_id not in by_id or package_id not in by_id:
        raise rvr.GateRejection("rvr.gate.evidence_closure_incomplete", "claim evidence member absent")
    if by_id[request_id]["status"] == "UNAVAILABLE" or by_id[package_id]["status"] == "UNAVAILABLE":
        result = _axis_result("CANNOT_ESTABLISH", "CANNOT_ESTABLISH", "CANNOT_ESTABLISH",
                              "CANNOT_ESTABLISH", claim, "UNVERIFIABLE",
                              "rvr.qev.v0.required_evidence_unavailable")
        rvr.require_schema(result, schema, "#/$defs/canonicalResult", "QEV canonical result")
        return result
    out = checker.verify(payloads[request_id], payloads[package_id])
    if out["input_status"] == "INVALID":
        raise rvr.GateRejection("rvr.gate.schema_invalid", "QEV input invalid")
    if out["input_status"] != "VALID":
        raise rvr.GateRejection("rvr.qev.gate.unsupported_input", "QEV input unsupported")

    request_binding = out["request_binding"]
    integrity = out["integrity"]
    deterministic = out["deterministic_verification"]

    if request_binding == "REFUTED" or integrity == "REFUTED" or deterministic == "REFUTED":
        outcome, reason = "REFUTED", "rvr.qev.v0.relation_refuted"
    elif deterministic == "CANNOT_ESTABLISH":
        outcome, reason = "UNVERIFIABLE", "rvr.qev.v0.raw_evidence_unavailable"
    elif request_binding == integrity == deterministic == "SATISFIED":
        outcome, reason = "VERIFIED", "rvr.qev.v0.relation_satisfied"
    else:
        raise rvr.GateRejection("rvr.gate.schema_invalid", "unexpected QEV axis combination")

    result = _axis_result("VALID", request_binding, integrity, deterministic, claim, outcome, reason)
    rvr.require_schema(result, schema, "#/$defs/canonicalResult", "QEV canonical result")
    return result

def make_bundle(case: dict[str, Any], profile: dict[str, Any], profile_digest: str,
                schema: dict[str, Any]) -> dict[str, Any]:
    claim = copy.deepcopy(case["claim"])
    evidence_set = copy.deepcopy(case["evidenceSet"])
    payloads_base64 = copy.deepcopy(case["payloadsBase64"])
    rvr.require_schema(claim, schema, "#/$defs/claim", "QEV claim")
    rvr.require_schema(evidence_set, schema, "#/$defs/evidenceSet", "QEV evidence set")
    payloads = rvr.validate_evidence_closure(evidence_set, payloads_base64)
    result = evaluate_qev(claim, evidence_set, payloads, schema)
    receipt = {
        "claimDigest": rvr.canonical_digest(claim),
        "evidenceSetDigest": rvr.evidence_set_digest(evidence_set),
        "verificationProfileDigest": profile_digest,
        "outcome": result["outcome"],
        "reasonCode": result["reasonCode"],
        "resultDigest": rvr.canonical_digest(result),
    }
    rvr.require_schema(receipt, schema, label="QEV RVR receipt")
    bundle = {
        "receipt": receipt,
        "claim": claim,
        "evidenceSet": evidence_set,
        "payloadsBase64": payloads_base64,
        "verificationProfile": profile,
        "canonicalResult": result,
    }
    rvr.validate_receipt_envelope(bundle, profile_digest, schema)
    return bundle

def recompute(original_bundle: dict[str, Any], candidate_case: dict[str, Any],
              profile_digest: str, schema: dict[str, Any],
              unavailable_dependency_ids: set[str] | None = None,
              outcome_relevant_inputs: list[dict[str, Any]] | None = None,
              candidate_dependency_bytes: dict[str, bytes] | None = None) -> dict[str, Any]:
    rvr.validate_receipt_envelope(original_bundle, profile_digest, schema)
    profile = original_bundle["verificationProfile"]
    failure = rvr.required_dependency_failure(
        profile, unavailable_dependency_ids or set(), candidate_dependency_bytes
    )
    if failure is not None:
        mismatch = failure["kind"] == "IDENTITY_MISMATCH"
        return {
            "recomputationStatus": "CANNOT_RECOMPUTE",
            "reasonCode": (
                "rvr.recompute.normative_dependency_identity_mismatch"
                if mismatch else "rvr.recompute.normative_dependency_unavailable"
            ),
            "dependencyId": failure["dependencyId"],
            "dependencyFailureKind": failure["kind"],
            "evaluationPerformed": False,
        }

    claim = copy.deepcopy(candidate_case["claim"])
    evidence_set = copy.deepcopy(candidate_case["evidenceSet"])
    payloads_base64 = copy.deepcopy(candidate_case["payloadsBase64"])
    rvr.require_schema(claim, schema, "#/$defs/claim", "candidate QEV claim")
    rvr.require_schema(evidence_set, schema, "#/$defs/evidenceSet", "candidate QEV evidence set")
    unresolved = rvr.unresolved_present_member(evidence_set, payloads_base64)
    if unresolved is not None:
        return {
            "recomputationStatus": "CANNOT_RECOMPUTE",
            "reasonCode": "rvr.recompute.committed_evidence_unavailable",
            "unavailableEvidenceMemberId": unresolved,
            "evidenceFailureKind": "UNRESOLVED_COMMITTED_PRESENT",
            "evaluationPerformed": False,
        }
    payloads = rvr.validate_evidence_closure(evidence_set, payloads_base64, outcome_relevant_inputs)
    result = evaluate_qev(claim, evidence_set, payloads, schema)
    recomputed = {
        "claimDigest": rvr.canonical_digest(claim),
        "evidenceSetDigest": rvr.evidence_set_digest(evidence_set),
        "verificationProfileDigest": profile_digest,
        "resultDigest": rvr.canonical_digest(result),
    }
    receipt = original_bundle["receipt"]
    reproduced = all(receipt[field] == digest for field, digest in recomputed.items())
    return {
        "verificationOutcome": result["outcome"],
        "verificationReasonCode": result["reasonCode"],
        "recomputationStatus": "REPRODUCED" if reproduced else "DIVERGED",
        "reasonCode": (
            "rvr.recompute.identical"
            if reproduced else "rvr.recompute.canonical_result_diverged"
        ),
        "evaluationPerformed": True,
        "canonicalResultDigest": recomputed["resultDigest"],
    }

def assert_expected(actual: dict[str, Any], expected: dict[str, Any], name: str) -> None:
    for key, value in expected.items():
        if actual.get(key) != value:
            raise AssertionError(f"{name}.{key}: expected {value!r}, got {actual.get(key)!r}")
def _profile_schema_boundary(profile, constraints, manifest_schema, manifest_bytes, vectors):
    vector = vectors["profileSchemaBoundary"]
    alternate = copy.deepcopy(profile)
    alternate["profileId"] = vector["alternateProfileId"]
    generic_valid = not rvr.validate_schema(alternate, manifest_schema)
    qev_valid = not rvr.validate_schema(alternate, constraints)
    if generic_valid != vector["genericManifestMustAccept"]:
        raise AssertionError("generic profile manifest boundary")
    if qev_valid != vector["qevConstraintsMustAccept"]:
        raise AssertionError("QEV profile constraints boundary")
    tampered = copy.deepcopy(profile)
    tampered["profileSchemaContract"]["constraints"]["sha256"] = vector["tamperedConstraintsDigest"]
    try:
        rvr.audit_profile(tampered, manifest_schema, manifest_bytes)
    except rvr.GateRejection as exc:
        rejected = exc.reason_code == "rvr.gate.identity_mismatch"
    else:
        rejected = False
    if rejected != vector["tamperedConstraintsPinMustReject"]:
        raise AssertionError("tampered QEV profile constraints pin boundary")
    return {
        "genericManifestAccepted": generic_valid,
        "qevConstraintsAccepted": qev_valid,
        "tamperedConstraintsPinRejected": rejected,
    }

def _package_unavailable_case(case, member_id, reason_code):
    candidate = copy.deepcopy(case)
    member = next(item for item in candidate["evidenceSet"]["members"] if item["id"] == member_id)
    member.clear()
    member.update({"id": member_id, "status": "UNAVAILABLE", "reasonCode": reason_code})
    candidate["payloadsBase64"].pop(member_id, None)
    return candidate

def _payload_identity_mismatch_case(case, member_id, replacement_base64):
    candidate = copy.deepcopy(case)
    candidate["payloadsBase64"][member_id] = replacement_base64
    return candidate
def run_gate() -> dict[str, Any]:
    profile, profile_digest, constraints, pinned, schema, manifest_schema, manifest_bytes = load_profile_context()
    vectors = rvr.parse_json_bytes(pinned["verification-vectors"], "verification-vectors")
    expected = rvr.parse_json_bytes(pinned["expected-results"], "expected-results")
    mutants = rvr.parse_json_bytes(pinned["adversarial-mutants"], "adversarial-mutants")

    canonical = rvr.run_canonical_vectors(vectors)
    resolver = rvr.run_resolver_vectors(vectors)
    boundary = _profile_schema_boundary(
        profile, constraints, manifest_schema, manifest_bytes, vectors
    )

    cases = vectors["verificationCases"]
    original_case = cases["reproduced"]
    original_bundle = make_bundle(original_case, profile, profile_digest, schema)
    reproduced = recompute(original_bundle, original_case, profile_digest, schema)
    assert_expected(reproduced, expected["cases"]["REPRODUCED"], "REPRODUCED")

    alternate = recompute(
        original_bundle, cases["alternateValidSample"], profile_digest, schema
    )
    assert_expected(
        alternate, expected["cases"]["ALTERNATE_VALID_SAMPLE"], "ALTERNATE_VALID_SAMPLE"
    )
    shot_order = recompute(original_bundle, cases["shotOrder"], profile_digest, schema)
    assert_expected(shot_order, expected["cases"]["SHOT_ORDER"], "SHOT_ORDER")
    refuted_counts = recompute(
        original_bundle, cases["refutedCounts"], profile_digest, schema
    )
    assert_expected(refuted_counts, expected["cases"]["REFUTED_COUNTS"], "REFUTED_COUNTS")
    refuted_integrity = recompute(
        original_bundle, cases["refutedIntegrity"], profile_digest, schema
    )
    assert_expected(
        refuted_integrity, expected["cases"]["REFUTED_INTEGRITY"], "REFUTED_INTEGRITY"
    )
    refuted_binding = recompute(
        original_bundle, cases["refutedRequestBinding"], profile_digest, schema
    )
    assert_expected(
        refuted_binding,
        expected["cases"]["REFUTED_REQUEST_BINDING"],
        "REFUTED_REQUEST_BINDING",
    )
    raw_unavailable = recompute(
        original_bundle, cases["rawUnavailable"], profile_digest, schema
    )
    assert_expected(
        raw_unavailable, expected["cases"]["RAW_UNAVAILABLE"], "RAW_UNAVAILABLE"
    )

    control = vectors["negativeControls"]["packageUnavailable"]
    package_unavailable_case = _package_unavailable_case(
        original_case, control["memberId"], control["reasonCode"]
    )
    package_unavailable = recompute(
        original_bundle, package_unavailable_case, profile_digest, schema
    )
    assert_expected(
        package_unavailable,
        expected["cases"]["PACKAGE_UNAVAILABLE"],
        "PACKAGE_UNAVAILABLE",
    )

    dep = vectors["negativeControls"]["requiredDependencyUnavailable"]
    cannot = recompute(
        original_bundle,
        original_case,
        profile_digest,
        schema,
        unavailable_dependency_ids={dep["dependencyId"]},
    )
    assert_expected(cannot, expected["cases"]["CANNOT_RECOMPUTE"], "CANNOT_RECOMPUTE")

    unresolved_control = vectors["negativeControls"]["presentPayloadUnresolved"]
    unresolved_case = copy.deepcopy(original_case)
    unresolved_case["payloadsBase64"].pop(
        unresolved_control["removePayloadMemberId"]
    )
    unresolved = recompute(original_bundle, unresolved_case, profile_digest, schema)
    assert_expected(
        unresolved,
        expected["cases"]["PRESENT_PAYLOAD_UNRESOLVED"],
        "PRESENT_PAYLOAD_UNRESOLVED",
    )
    mismatch_control = vectors["negativeControls"]["resolvedPayloadIdentityMismatch"]
    mismatch_case = _payload_identity_mismatch_case(
        original_case,
        mismatch_control["replacePayloadMemberId"],
        mismatch_control["replacementBase64"],
    )
    try:
        recompute(original_bundle, mismatch_case, profile_digest, schema)
    except rvr.GateRejection as exc:
        mismatch = {
            "gateStatus": "REJECTED",
            "reasonCode": exc.reason_code,
            "evaluationPerformed": False,
        }
    else:
        raise AssertionError("resolved payload identity mismatch accepted")
    assert_expected(
        mismatch,
        expected["cases"]["RESOLVED_PAYLOAD_IDENTITY_MISMATCH"],
        "RESOLVED_PAYLOAD_IDENTITY_MISMATCH",
    )

    projection_control = vectors["negativeControls"]["projectionContradiction"]
    contradictory = copy.deepcopy(original_bundle)
    contradictory["receipt"][projection_control["mutateReceiptField"]] = (
        projection_control["replacement"]
    )
    try:
        rvr.validate_receipt_envelope(
            contradictory, profile_digest, schema
        )
    except rvr.GateRejection as exc:
        projection = {"gateStatus": "REJECTED", "reasonCode": exc.reason_code}
    else:
        raise AssertionError("contradictory receipt projection accepted")
    assert_expected(
        projection,
        expected["cases"]["PROJECTION_NEGATIVE_CONTROL"],
        "PROJECTION_NEGATIVE_CONTROL",
    )
    hidden_control = vectors["negativeControls"]["hiddenState"]
    try:
        recompute(
            original_bundle,
            original_case,
            profile_digest,
            schema,
            outcome_relevant_inputs=[hidden_control["outcomeRelevantInput"]],
        )
    except rvr.GateRejection as exc:
        hidden = {
            "gateStatus": "REJECTED",
            "reasonCode": exc.reason_code,
            "evaluationPerformed": False,
        }
    else:
        raise AssertionError("uncommitted outcome-relevant input accepted")
    assert_expected(
        hidden,
        expected["cases"]["HIDDEN_STATE_NEGATIVE_CONTROL"],
        "HIDDEN_STATE_NEGATIVE_CONTROL",
    )

    optional = recompute(
        original_bundle,
        original_case,
        profile_digest,
        schema,
        unavailable_dependency_ids={"expected-results"},
        candidate_dependency_bytes={"expected-results": b"tampered"},
    )
    if not rvr.json_same(optional, reproduced):
        raise AssertionError("optional expected-results dependency affected recomputation")

    original_result_digest = original_bundle["receipt"]["resultDigest"]
    if alternate["canonicalResultDigest"] != original_result_digest:
        raise AssertionError("alternate valid stochastic sample changed semantic result digest")
    if shot_order["canonicalResultDigest"] != original_result_digest:
        raise AssertionError("shot-order representation changed semantic result digest")
    alt_evidence_digest = rvr.evidence_set_digest(cases["alternateValidSample"]["evidenceSet"])
    if alt_evidence_digest == original_bundle["receipt"]["evidenceSetDigest"]:
        raise AssertionError("alternate sample did not change evidence identity")

    return {
        "gate": "RVR_QEV_NATIVE_PROFILE_PASS",
        "profileId": profile["profileId"],
        "verificationProfileDigest": profile_digest,
        "rvrCore": {
            "commit": "549a7e150ddc75df88dc90ee93f331fea7464567",
            "adapterSha256": rvr.sha256_hex(VENDOR_ADAPTER_PATH.read_bytes()),
            "role": "VENDORED_NATIVE_RVR_V0_PRIMITIVES",
        },
        "canonicalByteVectors": canonical,
        "dependencyResolver": resolver,
        "profileSchemaBoundary": boundary,
        "cases": {
            "REPRODUCED": reproduced,
            "ALTERNATE_VALID_SAMPLE": alternate,
            "SHOT_ORDER": shot_order,
            "REFUTED_COUNTS": refuted_counts,
            "REFUTED_INTEGRITY": refuted_integrity,
            "REFUTED_REQUEST_BINDING": refuted_binding,
            "RAW_UNAVAILABLE": raw_unavailable,
            "PACKAGE_UNAVAILABLE": package_unavailable,
            "CANNOT_RECOMPUTE": cannot,
            "PRESENT_PAYLOAD_UNRESOLVED": unresolved,
            "RESOLVED_PAYLOAD_IDENTITY_MISMATCH": mismatch,
            "PROJECTION_NEGATIVE_CONTROL": projection,
            "HIDDEN_STATE_NEGATIVE_CONTROL": hidden,
            "OPTIONAL_EXPECTED_RESULTS_NONSEMANTIC": optional,
        },
        "stochasticBoundary": {
            "alternateSampleVerificationOutcome": alternate["verificationOutcome"],
            "alternateSampleRecomputationStatus": alternate["recomputationStatus"],
            "sameCanonicalResultDigest": alternate["canonicalResultDigest"]
            == original_result_digest,
            "differentEvidenceSetDigest": alt_evidence_digest
            != original_bundle["receipt"]["evidenceSetDigest"],
        },
        "mutantInventory": mutants["mutants"],
        "implementationIndependence": "NOT_ESTABLISHED",
        "physicalQpuExecution": "NOT_ESTABLISHED",
        "entropy": "NOT_ESTABLISHED",
    }

def main() -> int:
    try:
        print(json.dumps(run_gate(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"RVR QEV gate failed: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
