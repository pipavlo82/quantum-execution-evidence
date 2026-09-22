"""Source-mutation gate for the native RVR QEV profile."""
from __future__ import annotations
from collections import Counter
import copy
import hashlib
from pathlib import Path

from . import rvr_native as native

STATUSES = (
    "KILLED", "SURVIVED", "CRASHED", "NOT_APPLIED",
    "VACUOUS", "CONTROL_BROKEN", "BASELINE_FAILED",
)

DECISION_BLOCK = """if request_binding == "REFUTED" or integrity == "REFUTED" or deterministic == "REFUTED":
        outcome, reason = "REFUTED", "rvr.qev.v0.relation_refuted"
    elif deterministic == "CANNOT_ESTABLISH":
        outcome, reason = "UNVERIFIABLE", "rvr.qev.v0.raw_evidence_unavailable"
    elif request_binding == integrity == deterministic == "SATISFIED":
        outcome, reason = "VERIFIED", "rvr.qev.v0.relation_satisfied"
    else:
        raise rvr.GateRejection("rvr.gate.schema_invalid", "unexpected QEV axis combination")"""

MUTATIONS = (
    ("R1_IGNORE_REQUEST_BINDING", DECISION_BLOCK,
     """if integrity == "REFUTED" or deterministic == "REFUTED":
        outcome, reason = "REFUTED", "rvr.qev.v0.relation_refuted"
    elif deterministic == "CANNOT_ESTABLISH":
        outcome, reason = "UNVERIFIABLE", "rvr.qev.v0.raw_evidence_unavailable"
    elif integrity == deterministic == "SATISFIED":
        outcome, reason = "VERIFIED", "rvr.qev.v0.relation_satisfied"
    else:
        raise rvr.GateRejection("rvr.gate.schema_invalid", "unexpected QEV axis combination")""",
     "refutedRequestBinding", "verificationOutcome", "VERIFIED"),
    ("R2_IGNORE_INTEGRITY", DECISION_BLOCK,
     """if request_binding == "REFUTED" or deterministic == "REFUTED":
        outcome, reason = "REFUTED", "rvr.qev.v0.relation_refuted"
    elif deterministic == "CANNOT_ESTABLISH":
        outcome, reason = "UNVERIFIABLE", "rvr.qev.v0.raw_evidence_unavailable"
    elif request_binding == deterministic == "SATISFIED":
        outcome, reason = "VERIFIED", "rvr.qev.v0.relation_satisfied"
    else:
        raise rvr.GateRejection("rvr.gate.schema_invalid", "unexpected QEV axis combination")""",
     "refutedIntegrity", "verificationOutcome", "VERIFIED"),
    ("R3_IGNORE_DETERMINISTIC", DECISION_BLOCK,
     """if request_binding == "REFUTED" or integrity == "REFUTED":
        outcome, reason = "REFUTED", "rvr.qev.v0.relation_refuted"
    elif deterministic == "CANNOT_ESTABLISH":
        outcome, reason = "UNVERIFIABLE", "rvr.qev.v0.raw_evidence_unavailable"
    elif request_binding == integrity == "SATISFIED":
        outcome, reason = "VERIFIED", "rvr.qev.v0.relation_satisfied"
    else:
        raise rvr.GateRejection("rvr.gate.schema_invalid", "unexpected QEV axis combination")""",
     "refutedCounts", "verificationOutcome", "VERIFIED"),
    ("R4_MISSING_RAW_VERIFIED",
     'elif deterministic == "CANNOT_ESTABLISH":\n        outcome, reason = "UNVERIFIABLE", "rvr.qev.v0.raw_evidence_unavailable"',
     'elif deterministic == "CANNOT_ESTABLISH":\n        outcome, reason = "VERIFIED", "rvr.qev.v0.relation_satisfied"',
     "rawUnavailable", "verificationOutcome", "VERIFIED"),
    ("R5_RESULT_ONLY_REPRODUCTION",
     'reproduced = all(receipt[field] == digest for field, digest in recomputed.items())',
     'reproduced = receipt["resultDigest"] == recomputed["resultDigest"]',
     "alternateValidSample", "recomputationStatus", "REPRODUCED"),
    ("R6_DIVERGED_VERIFIED_AS_REFUTED",
     '"verificationOutcome": result["outcome"],',
     '"verificationOutcome": ("REFUTED" if not reproduced else result["outcome"]),',
     "alternateValidSample", "verificationOutcome", "REFUTED"),
    ("R7_TRUST_ORIGINAL_RESULT",
     'payloads = rvr.validate_evidence_closure(evidence_set, payloads_base64, outcome_relevant_inputs)\n    result = evaluate_qev(claim, evidence_set, payloads, schema)',
     'payloads = rvr.validate_evidence_closure(evidence_set, payloads_base64, outcome_relevant_inputs)\n    result = copy.deepcopy(original_bundle["canonicalResult"])',
     "refutedCounts", "verificationOutcome", "VERIFIED"),
)

def _context(ns):
    profile, digest, _, pinned, schema, _, _ = ns["load_profile_context"]()
    vectors = ns["rvr"].parse_json_bytes(pinned["verification-vectors"], "verification-vectors")
    original = vectors["verificationCases"]["reproduced"]
    bundle = ns["make_bundle"](original, profile, digest, schema)
    return profile, digest, schema, vectors, original, bundle

def _controls(original):
    exact = copy.deepcopy(original)
    reversed_members = copy.deepcopy(original)
    reversed_members["evidenceSet"]["members"].reverse()
    reversed_payloads = copy.deepcopy(original)
    items = list(reversed_payloads["payloadsBase64"].items())
    reversed_payloads["payloadsBase64"] = dict(reversed(items))
    return {"exact": exact, "reversed-members": reversed_members, "reversed-payload-map": reversed_payloads}
def _run_candidate(ns, case_name):
    _, digest, schema, vectors, original, bundle = _context(ns)
    candidate = vectors["verificationCases"][case_name]
    return ns["recompute"](bundle, candidate, digest, schema)

def _run_controls(ns):
    _, digest, schema, _, original, bundle = _context(ns)
    return {
        name: ns["recompute"](bundle, candidate, digest, schema)
        for name, candidate in _controls(original).items()
    }

def run():
    source_path = Path(native.__file__)
    source = source_path.read_text(encoding="utf-8")
    baseline_controls = _run_controls(native.__dict__)
    rows = []
    for mid, old, new, witness, axis, target in MUTATIONS:
        applied = source.count(old) == 1
        row = {"id": mid, "witness": witness, "axis": axis, "target": target,
               "applied": applied, "controls": {}}
        if not applied:
            row["status"] = "NOT_APPLIED"; rows.append(row); continue
        mutated = source.replace(old, new, 1)
        row["mutatedSourceSha256"] = hashlib.sha256(mutated.encode()).hexdigest()
        ns = {
            "__name__": "qev.rvr_native_mutant",
            "__package__": "qev",
            "__file__": str(source_path),
        }
        try:
            exec(compile(mutated, str(source_path), "exec"), ns)
            controls = _run_controls(ns)
            row["controls"] = {
                name: controls[name] == baseline_controls[name]
                for name in baseline_controls
            }
            baseline = _run_candidate(native.__dict__, witness)
            actual = _run_candidate(ns, witness)
            row["baseline"] = baseline
            row["actual"] = actual
            changed = actual != baseline
            semantic = actual.get(axis) == target and baseline.get(axis) != target
            if not all(row["controls"].values()):
                row["status"] = "CONTROL_BROKEN"
            elif not changed:
                row["status"] = "SURVIVED"
            elif not semantic:
                row["status"] = "VACUOUS"
            else:
                row["status"] = "KILLED"
        except Exception as exc:
            row["status"] = "CRASHED"
            row["error"] = type(exc).__name__
            row["errorMessage"] = str(exc)
        rows.append(row)
    counts = Counter(row["status"] for row in rows)
    return {
        "profileId": "rvr-qev-preserved-observation-v0",
        "sourceSha256": hashlib.sha256(source.encode()).hexdigest(),
        "positiveControls": list(baseline_controls),
        "summary": {name: counts[name] for name in STATUSES},
        "mutations": rows,
        "independence": "SAME_TASK_SOURCE_MUTATION_NOT_INDEPENDENT_AUTHORSHIP",
    }

def successful(report):
    required = {row[0] for row in MUTATIONS}
    rows = report.get("mutations", [])
    if len(rows) != len(required) or {row.get("id") for row in rows} != required:
        return False
    if report.get("summary") != {
        name: (len(required) if name == "KILLED" else 0) for name in STATUSES
    }:
        return False
    return all(
        row.get("status") == "KILLED"
        and row.get("applied") is True
        and len(row.get("controls", {})) == 3
        and all(row["controls"].values())
        for row in rows
    )

if __name__ == "__main__":
    import json, sys
    report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if successful(report) else 1)
