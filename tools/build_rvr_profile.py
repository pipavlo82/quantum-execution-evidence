from pathlib import Path
import json, hashlib

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"profiles/qev-preserved-observation-v0"
def sha(rel): return hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
members=[
 {"id":"expected-results","path":"profiles/qev-preserved-observation-v0/expected.json","sha256":sha("profiles/qev-preserved-observation-v0/expected.json"),"requiredForRecomputation":False},
 {"id":"adversarial-mutants","path":"profiles/qev-preserved-observation-v0/mutants.json","sha256":sha("profiles/qev-preserved-observation-v0/mutants.json"),"requiredForRecomputation":False},
 {"id":"verification-vectors","path":"profiles/qev-preserved-observation-v0/vectors.json","sha256":sha("profiles/qev-preserved-observation-v0/vectors.json"),"requiredForRecomputation":False},
]
rows="".join(f"{m['path']}\t{m['sha256']}\n" for m in sorted(members,key=lambda x:x["path"]))
rvr_schema_sha=sha("profiles/qev-preserved-observation-v0/rvr-qev.schema.json")
profile={
 "schema":"rvr.verification-profile.v0",
 "profileId":"rvr-qev-preserved-observation-v0",
 "profileSchemaContract":{
   "manifest":{"id":"verification-profile-manifest-schema","path":"vendor/rvr-v0/verification-profile-manifest.schema.json",
      "sha256":sha("vendor/rvr-v0/verification-profile-manifest.schema.json"),"requiredForRecomputation":True},
   "constraints":{"id":"rvr-qev-profile-schema","path":"profiles/qev-preserved-observation-v0/profile.schema.json",
      "sha256":sha("profiles/qev-preserved-observation-v0/profile.schema.json"),"requiredForRecomputation":True}
 },
 "dependencyResolution":{"base":"SUPPLIED_PROFILE_PACKAGE_ROOT",
   "pathFormat":"relative-posix-no-empty-dot-dotdot-or-colon-segments",
   "locatorRole":"NORMATIVE_PACKAGE_RELATIVE_PATH","verificationOrder":"resolve-read-sha256-match-use"},
 "verificationSpecification":{"id":"verification-specification","path":"docs/RVR_QEV_PROFILE_V0.md",
   "sha256":sha("docs/RVR_QEV_PROFILE_V0.md"),"requiredForRecomputation":True},
 "conformanceVectorSet":{"id":"rvr-qev-v0-falsification-set","members":members,
   "digest":hashlib.sha256(rows.encode()).hexdigest(),"digestRule":"sha256-utf8-sorted-path-tab-file-sha256-lf-rows"},
 "canonicalByteContract":{"id":"rvr-canonical-json-v0","encoding":"UTF-8",
   "domain":"null-boolean-unicode-scalar-string-array-object","objectKeyOrder":"unicode-scalar-value-ascending",
   "arrayOrder":"preserved-with-duplicates","unicode":"scalar-values-only-no-normalization","numbers":"forbidden",
   "stringEscaping":"rvr-json-string-escaping-v0","solidus":"literal","lineSeparators":"U+2028-and-U+2029-literal","whitespace":"none"},
 "schemaContracts":[{"id":"rvr-schema","path":"profiles/qev-preserved-observation-v0/rvr-qev.schema.json",
   "sha256":rvr_schema_sha,"requiredForRecomputation":True}],
 "evidenceSetContract":{"schemaPath":"profiles/qev-preserved-observation-v0/rvr-qev.schema.json","schemaSha256":rvr_schema_sha,
   "schemaPointer":"#/$defs/evidenceSet","digestRule":"sha256-utf8-rvr-canonical-json-v0-normalized-member-order"},
 "canonicalResultContract":{"schemaPath":"profiles/qev-preserved-observation-v0/rvr-qev.schema.json","schemaSha256":rvr_schema_sha,
   "schemaPointer":"#/$defs/canonicalResult","outcomeProjection":"/outcome","reasonCodeProjection":"/reasonCode"},
 "resultHashRules":{"algorithm":"SHA-256","input":"rvr-canonical-json-v0(canonicalResult)",
   "encoding":"UTF-8-exactly-once","output":"lowercase-hex-no-prefix"},
 "reasonCodeNamespace":{
   "verification":["rvr.qev.v0.relation_satisfied","rvr.qev.v0.relation_refuted",
      "rvr.qev.v0.raw_evidence_unavailable","rvr.qev.v0.required_evidence_unavailable"],
   "recomputation":["rvr.recompute.identical","rvr.recompute.canonical_result_diverged",
      "rvr.recompute.normative_dependency_unavailable","rvr.recompute.normative_dependency_identity_mismatch",
      "rvr.recompute.committed_evidence_unavailable"],
   "gateRejections":["rvr.gate.schema_invalid","rvr.gate.identity_mismatch","rvr.gate.result_projection_mismatch",
      "rvr.gate.evidence_closure_incomplete","rvr.qev.gate.unsupported_input"]
 },
 "externalContextPolicy":{"mode":"FORBIDDEN_UNLESS_COMMITTED","ambientInputs":"FORBIDDEN","immutableCommitments":[]}
}
data=(json.dumps(profile,ensure_ascii=False,indent=2)+"\n").encode()

def generate():
    return data

def main():
    (P/"verification-profile.json").write_bytes(data)
    print(json.dumps({"profile_sha256":hashlib.sha256(data).hexdigest(),"vector_set_digest":profile["conformanceVectorSet"]["digest"]},indent=2))

if __name__=="__main__":
    main()
