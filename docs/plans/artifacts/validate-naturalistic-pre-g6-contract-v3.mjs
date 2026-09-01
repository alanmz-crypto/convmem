#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const contractPath = join(here, "naturalistic-pre-g6-contract-v3.json");
const schemaPath = join(here, "naturalistic-pre-g6-contract-v3.schema.json");
const conformancePath = join(here, "naturalistic-pre-g6-contract-v3.conformance.json");
const sidecarPath = join(here, "naturalistic-pre-g6-contract-v3.json.sha256");
const amendmentManifestPath = join(here, "naturalistic-pre-g6-contract-v3.amendment.json");
const priorContractPath = join(here, "naturalistic-pre-g6-contract-v2.json");
const priorConformancePath = join(here, "naturalistic-pre-g6-contract-v2.conformance.json");
const priorCanonicalDigest = "917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e";

function fail(message) {
  throw new Error(message);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

function hasValidUnicode(value, path = "$") {
  if (typeof value === "string") {
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        const next = value.charCodeAt(index + 1);
        assert(next >= 0xdc00 && next <= 0xdfff, `lone high surrogate at ${path}`);
        index += 1;
      } else {
        assert(!(code >= 0xdc00 && code <= 0xdfff), `lone low surrogate at ${path}`);
      }
    }
  } else if (Array.isArray(value)) {
    value.forEach((item, index) => hasValidUnicode(item, `${path}[${index}]`));
  } else if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      hasValidUnicode(key, `${path}.<key>`);
      hasValidUnicode(item, `${path}.${key}`);
    }
  }
}

// RFC 8785 uses ECMAScript primitive serialization and UTF-16 code-unit key order.
// JSON.parse has already reduced numbers to IEEE-754 doubles, as JCS requires.
function jcs(value) {
  if (value === null || typeof value === "boolean" || typeof value === "string") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    assert(Number.isFinite(value), "JCS forbids non-finite numbers");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map(jcs).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${jcs(value[key])}`).join(",")}}`;
  }
  fail(`unsupported JCS value type: ${typeof value}`);
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function deepEqual(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function typeMatches(value, expected) {
  const candidates = Array.isArray(expected) ? expected : [expected];
  return candidates.some((candidate) => {
    if (candidate === "null") return value === null;
    if (candidate === "array") return Array.isArray(value);
    if (candidate === "object") return value !== null && typeof value === "object" && !Array.isArray(value);
    if (candidate === "integer") return Number.isInteger(value);
    return typeof value === candidate;
  });
}

// This validator implements every JSON Schema keyword used by the companion schema.
function validateSchema(value, schema, path = "$") {
  if (Object.hasOwn(schema, "const")) assert(deepEqual(value, schema.const), `${path}: const mismatch`);
  if (schema.enum) assert(schema.enum.some((item) => deepEqual(value, item)), `${path}: enum mismatch`);
  if (schema.type) assert(typeMatches(value, schema.type), `${path}: type mismatch`);
  if (typeof value === "string") {
    if (schema.minLength !== undefined) assert(value.length >= schema.minLength, `${path}: minLength`);
    if (schema.pattern) assert(new RegExp(schema.pattern).test(value), `${path}: pattern`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined) assert(value.length >= schema.minItems, `${path}: minItems`);
    if (schema.maxItems !== undefined) assert(value.length <= schema.maxItems, `${path}: maxItems`);
    if (schema.uniqueItems) {
      const unique = new Set(value.map((item) => JSON.stringify(item)));
      assert(unique.size === value.length, `${path}: uniqueItems`);
    }
    if (schema.items) value.forEach((item, index) => validateSchema(item, schema.items, `${path}[${index}]`));
  }
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    const keys = Object.keys(value);
    if (schema.minProperties !== undefined) assert(keys.length >= schema.minProperties, `${path}: minProperties`);
    for (const required of schema.required ?? []) assert(Object.hasOwn(value, required), `${path}: missing ${required}`);
    if (schema.additionalProperties === false) {
      const allowed = new Set(Object.keys(schema.properties ?? {}));
      for (const key of keys) assert(allowed.has(key), `${path}: unexpected property ${key}`);
    }
    for (const [key, childSchema] of Object.entries(schema.properties ?? {})) {
      if (Object.hasOwn(value, key)) validateSchema(value[key], childSchema, `${path}.${key}`);
    }
  }
}

const contract = JSON.parse(readFileSync(contractPath, "utf8"));
const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const conformance = JSON.parse(readFileSync(conformancePath, "utf8"));
const amendmentManifest = JSON.parse(readFileSync(amendmentManifestPath, "utf8"));
const priorContract = JSON.parse(readFileSync(priorContractPath, "utf8"));
const priorConformance = JSON.parse(readFileSync(priorConformancePath, "utf8"));
hasValidUnicode(contract);
validateSchema(contract, schema);
assert(sha256(Buffer.from(jcs(priorContract), "utf8")) === priorCanonicalDigest, "historical V2 authority digest differs");

const rfc8785Sample = JSON.parse('{"numbers":[333333333.33333329,1E30,4.50,2e-3,0.000000000000000000000000001],"literals":[null,true,false]}');
const rfc8785Expected = '{"literals":[null,true,false],"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27]}';
assert(jcs(rfc8785Sample) === rfc8785Expected, "RFC 8785 numeric serialization and property ordering sample failed");

const canonicalBytes = Buffer.from(jcs(contract), "utf8");
const digest = sha256(canonicalBytes);
if (process.argv.includes("--digest-only")) {
  process.stdout.write(`${digest}\n`);
  process.exit(0);
}

const sidecar = readFileSync(sidecarPath, "utf8");
assert(/^[0-9a-f]{64}  naturalistic-pre-g6-contract-v3\.json\n$/.test(sidecar), "sidecar format must be sha256sum-compatible with exactly one terminal LF");
const sidecarDigest = sidecar.slice(0, 64);
assert(sidecarDigest === digest, "sidecar digest does not match RFC 8785 canonical bytes");
assert(sha256(Buffer.concat([canonicalBytes, Buffer.from("\n")])) !== digest, "newline-appended canonical bytes must hash differently");

const expectedStages = [
  "P0_T0_CONSTRUCT_FREEZE",
  "P1_T1_EVIDENCE_SEAL",
  "P2_OPAQUE_RESOLUTION",
  "P3_T2_BLINDED_ADJUDICATION_REGISTRY_SEAL",
  "T3_SAMPLE_SEAL",
  "T4_PROBE_KEY_SCORER_SEAL",
  "T5_C1_SNAPSHOT_CAPTURE_DIAGNOSIS",
  "T6_C0_C1_READINESS",
  "T7_EXECUTION",
  "T8_MASKED_SCORING",
  "T9_AGGREGATION",
  "T10_INFORMATION_GATE"
];
assert(deepEqual(contract.stage_graph.map((stage) => stage.id), expectedStages), "stage graph IDs or order differ");
const producedAt = new Map();
contract.stage_graph.forEach((stage, index) => {
  assert(stage.parent === (index === 0 ? null : contract.stage_graph[index - 1].id), `${stage.id}: parent is not immediate predecessor`);
  if (index === 0) {
    assert(stage.parent_artifact === null && stage.parent_digest_field === null, "P0 must have no stage parent");
  } else {
    assert(typeof stage.parent_artifact === "string" && typeof stage.parent_digest_field === "string", `${stage.id}: exact parent artifact/digest field required`);
    assert(stage.consumes.includes(stage.parent_artifact), `${stage.id}: parent artifact is not consumed`);
    assert(stage.required_fields.includes(stage.parent_digest_field), `${stage.id}: parent digest field is not required`);
  }
  assert(new Set(stage.required_fields.filter((field) => stage.forbidden_fields.includes(field))).size === 0, `${stage.id}: field both required and forbidden`);
  for (const consumed of stage.consumes) {
    if (!consumed.startsWith("EXTERNAL:")) assert(producedAt.has(consumed), `${stage.id}: consumes ${consumed} before production`);
  }
  for (const produced of stage.produces) {
    assert(!producedAt.has(produced), `${stage.id}: duplicate producer for ${produced}`);
    producedAt.set(produced, index);
  }
});
const p1 = contract.stage_graph[1];
const canonicalP2FirewallFields = ["resolver_result", "capability_vector"];
assert(p1.forbidden_fields.includes("resolver_output_digest") && p1.forbidden_fields.includes("target_census"), "P1 must forbid P2/P3 knowledge");
for (const field of canonicalP2FirewallFields) {
  assert(p1.forbidden_fields.includes(field), `P1 must forbid canonical P2 field ${field}`);
}
assert(contract.stage_graph[2].produces.includes("OpaqueResolverManifestV2"), "P2 must produce resolver authority");
assert(contract.stage_graph[3].produces.includes("TargetRegistryV2"), "P3/T2 must produce registry authority");
assert(contract.amendment_policy.same_authority_identity_with_changed_estimand === "PROHIBITED", "estimand amendment cannot retain authority identity");
assert(contract.amendment_policy.construct_amendment_requires.includes("new_contract_version") && contract.amendment_policy.construct_amendment_requires.includes("new_canonical_digest_and_sidecar") && contract.amendment_policy.construct_amendment_requires.includes("outcome_blind_independent_review"), "construct amendment controls incomplete");
assert(contract.role_access_policy.adjudication_interface.artifact === "AdjudicationEvidenceViewV1", "adjudication interface artifact differs");
assert(contract.role_access_policy.adjudication_interface.constant_shape === true && contract.role_access_policy.adjudication_interface.all_resolver_derived_fields_hidden === true, "role access does not enforce a constant blind interface");
assert(contract.role_access_policy.roles.adjudicator.may_not_read.includes("resolver_retry_count_and_timing") && contract.role_access_policy.roles.adjudicator.may_not_read.includes("resolver_missing_file_signals"), "adjudicator side-channel deny list incomplete");

const firewallPolicy = contract.role_access_policy.canonical_field_name_enforcement;
assert(deepEqual(firewallPolicy.canonical_forbidden_p2_fields, canonicalP2FirewallFields), "canonical P2 firewall field set differs");
assert(firewallPolicy.rule === "normalize_known_aliases_to_canonical_names_before_any_P1_or_adjudicator_allow_deny_decision", "canonical alias enforcement rule differs");
assert(firewallPolicy.unknown_alias === "DENY_AND_FAIL_CLOSED", "unknown aliases must fail closed");

function canonicalFirewallField(field) {
  if (canonicalP2FirewallFields.includes(field)) return field;
  for (const [canonical, aliases] of Object.entries(firewallPolicy.aliases)) {
    if (aliases.includes(field)) return canonical;
  }
  return field;
}

const adjudicatorDeny = contract.role_access_policy.roles.adjudicator.may_not_read;
const adjudicationViewDeny = contract.adjudication_view.forbidden_fields;
for (const field of canonicalP2FirewallFields) {
  assert(adjudicatorDeny.includes(field), `adjudicator RoleAccess must deny canonical P2 field ${field}`);
  assert(adjudicationViewDeny.includes(field), `AdjudicationEvidenceViewV1 must forbid canonical P2 field ${field}`);
  for (const alias of firewallPolicy.aliases[field] ?? []) {
    assert(canonicalFirewallField(alias) === field, `alias ${alias} must canonicalize to ${field}`);
    assert(p1.forbidden_fields.includes(canonicalFirewallField(alias)), `P1 alias ${alias} bypasses canonical firewall`);
    assert(adjudicatorDeny.includes(canonicalFirewallField(alias)), `RoleAccess alias ${alias} bypasses canonical firewall`);
    assert(adjudicationViewDeny.includes(canonicalFirewallField(alias)), `adjudication-view alias ${alias} bypasses canonical firewall`);
  }
}

const decisionFields = ["id", "name", "semantics", "allowed_domain", "units", "allowed_states", "preferred", "owner_authority", "freeze_stage", "evidence_required", "validator", "failure_transition", "accepted_downside", "overturning_evidence"];
const decisionIds = new Set();
for (const decision of contract.decision_registry) {
  for (const field of decisionFields) assert(Object.hasOwn(decision, field), `${decision.id ?? "decision"}: missing ${field}`);
  assert(!decisionIds.has(decision.id), `duplicate decision ID ${decision.id}`);
  decisionIds.add(decision.id);
  assert(decision.freeze_stage === "P0_T0_CONSTRUCT_FREEZE", `${decision.id}: wrong freeze stage`);
}

const multiplicityCases = [
  "multiplicity_exact_zero_valid",
  "multiplicity_exact_one_valid",
  "multiplicity_unbounded_known_equal_lower_valid",
  "multiplicity_unbounded_lower_exceeds_known_valid",
  "multiplicity_finite_lower_exceeds_known_valid",
  "multiplicity_finite_known_zero_lower_positive_valid",
  "multiplicity_negative_known_invalid",
  "multiplicity_negative_lower_invalid",
  "multiplicity_known_exceeds_lower_invalid",
  "multiplicity_lower_exceeds_upper_invalid",
  "multiplicity_exact_null_upper_invalid",
  "multiplicity_exact_counts_differ_invalid",
  "multiplicity_finite_upper_without_proof_invalid"
];
const requiredCases = [...priorConformance.cases.map((item) => item.id), ...multiplicityCases];
assert(priorConformance.case_count === priorConformance.cases.length, "historical V2 conformance count differs");
assert(deepEqual(conformance.cases.slice(0, priorConformance.cases.length), priorConformance.cases), "historical V2 conformance cases changed");
assert(conformance.case_count === requiredCases.length, "conformance case_count mismatch");
assert(deepEqual(conformance.cases.map((item) => item.id), requiredCases), "conformance cases differ or are out of order");
for (const item of conformance.cases) {
  for (const field of ["id", "scenario", "input", "expected", "blocked_transition"]) assert(Object.hasOwn(item, field), `${item.id}: missing ${field}`);
  assert(contract.verification_controls.includes(item.id), `${item.id}: missing verification control`);
}

function hasProofAuthority(value) {
  return value !== null
    && typeof value === "object"
    && !Array.isArray(value)
    && ["proof_id", "parent_digest", "completeness_claim"].every(
      (field) => typeof value[field] === "string" && value[field].length > 0
    );
}

function validateMultiplicityRecord(record) {
  const statuses = new Set(["EXACT", "FINITE_BOUNDED", "UNBOUNDED_UNKNOWN"]);
  if (!record || typeof record !== "object" || Array.isArray(record)) return false;
  if (!statuses.has(record.multiplicity_status)) return false;
  if (!Number.isInteger(record.known_count) || !Number.isInteger(record.lower_bound)) return false;
  if (record.known_count < 0 || record.lower_bound < 0) return false;
  if (record.known_count > record.lower_bound) return false;
  if (record.lower_bound > record.known_count && !hasProofAuthority(record.lower_bound_proof_authority)) return false;

  if (record.multiplicity_status === "UNBOUNDED_UNKNOWN") {
    return record.upper_bound === null;
  }
  if (!Number.isInteger(record.upper_bound) || record.upper_bound < 0) return false;
  if (record.lower_bound > record.upper_bound) return false;
  if (record.multiplicity_status === "EXACT") {
    return record.known_count === record.lower_bound
      && record.lower_bound === record.upper_bound
      && hasProofAuthority(record.exact_completeness_proof_authority);
  }
  return hasProofAuthority(record.finite_upper_proof_authority);
}

for (const caseId of multiplicityCases) {
  const item = conformance.cases.find((candidate) => candidate.id === caseId);
  assert(item, `missing multiplicity case ${caseId}`);
  const actual = validateMultiplicityRecord(item.input)
    ? "VALID_MULTIPLICITY_RECORD"
    : "INVALID_MULTIPLICITY_RECORD";
  assert(actual === item.expected, `${caseId}: expected ${item.expected}, received ${actual}`);
}

const firewallCaseExpectations = new Map([
  ["p1_rejects_resolver_result", ["P1_T1_EVIDENCE_SEAL", "resolver_result", "V_STAGE_P1_REJECTS_CANONICAL_P2_FIELD"]],
  ["p1_rejects_capability_vector", ["P1_T1_EVIDENCE_SEAL", "capability_vector", "V_STAGE_P1_REJECTS_CANONICAL_P2_FIELD"]],
  ["adjudicator_view_rejects_resolver_result", ["AdjudicationEvidenceViewV1", "resolver_result", "V_ADJUDICATION_VIEW_REJECTS_CANONICAL_P2_FIELD"]],
  ["adjudicator_view_rejects_capability_vector", ["AdjudicationEvidenceViewV1", "capability_vector", "V_ADJUDICATION_VIEW_REJECTS_CANONICAL_P2_FIELD"]]
]);
for (const [caseId, [surface, field, expectedReason]] of firewallCaseExpectations) {
  const item = conformance.cases.find((candidate) => candidate.id === caseId);
  assert(item, `missing independent firewall case ${caseId}`);
  assert(deepEqual(item.input, { surface, field }), `${caseId}: input fixture differs`);
  assert(item.expected === expectedReason, `${caseId}: intended firewall reason differs`);
  const canonical = canonicalFirewallField(item.input.field);
  assert(canonical === field, `${caseId}: canonical field normalization differs`);
  if (surface === "P1_T1_EVIDENCE_SEAL") {
    assert(p1.forbidden_fields.includes(canonical), `${caseId}: P1 accepted forbidden canonical P2 field`);
    assert(item.blocked_transition === "P1_T1_EVIDENCE_SEAL", `${caseId}: wrong blocked transition`);
  } else {
    assert(adjudicationViewDeny.includes(canonical), `${caseId}: adjudication view accepted forbidden canonical P2 field`);
    assert(adjudicatorDeny.includes(canonical), `${caseId}: RoleAccess accepted forbidden canonical P2 field`);
    assert(item.blocked_transition === "P3_T2_BLINDED_ADJUDICATION_REGISTRY_SEAL", `${caseId}: wrong blocked transition`);
  }
}

const requiredEvidenceSemantics = ["acceptance_and_rejection", "ordering", "filtering", "duplicate_handling", "authorship", "chronology_and_timezone", "reply_or_parent_structure", "validity_metadata", "unknown_and_extension_fields", "attachments_and_blobs", "referenced_and_tool_material", "omissions_and_completeness_declaration"];
assert(deepEqual(contract.source_evidence_contract.required_semantics, requiredEvidenceSemantics), "evidence-complete semantics differ");
assert(contract.provenance_roots.some((root) => root.id === "github_issue_263"), "Issue #263 provenance root missing");
assert(contract.source_resolution_contract.provenance_root === "github_issue_263", "source resolution is not rooted in Issue #263");
assert(contract.source_evidence_contract.unstable_transport_hash_is_raw_authority === false, "transport serialization cannot be raw authority");
assert(contract.identity_model.physical_identity_rules.clone.startsWith("always_new_physical_instance"), "clone identity rule missing");
assert(contract.identity_model.physical_identity_rules.restore.startsWith("always_new_physical_instance"), "restore identity rule missing");

const targetAxes = ["existence_status", "multiplicity_status", "resolvability", "evaluability", "integrity"];
assert(deepEqual(Object.keys(contract.denominator_model.orthogonal_target_state), targetAxes), "target state axes differ");
assert(contract.denominator_model.target_count_bounds.unbounded_upper_representation === null, "unbounded upper must be null");
const useClasses = ["DISCOVERY_ELIGIBILITY", "ADJUDICATION", "PRIMARY_SCORING", "SECONDARY_DIAGNOSTIC", "REPLAY_AUDIT"];
assert(deepEqual(Object.keys(contract.capability_model.per_use_acceptance), useClasses), "capability per-use table differs");
assert(contract.adjudication_view.built_before === "P2_OPAQUE_RESOLUTION", "adjudication view must precede resolver output");
assert(contract.adjudication_view.forbidden_fields.includes("resolver_failure_reason") && contract.adjudication_view.forbidden_fields.includes("retry_timing"), "blind view side-channel exclusions incomplete");
assert(canonicalP2FirewallFields.every((field) => contract.adjudication_view.forbidden_fields.includes(field)), "blind view canonical P2 field exclusions incomplete");
assert(contract.snapshot_authority.snapshot_is_occurrence_authority === false, "snapshot cannot become occurrence authority");
assert(contract.legacy_summary_firewall.unknown_lineage === "NON_NORMATIVE", "unknown provenance must be non-normative");
assert(contract.legacy_summary_firewall.stripping_original_content_cleans_descendant === false, "stripping legacy prose cannot clean descendants");

const expectedMultiplicityRules = [
  "known_count_equals_number_evidenced_not_total_when_upper_unknown",
  "valid_counts_require_zero_le_known_count_le_lower_bound",
  "lower_bound_above_known_count_requires_separate_lower_bound_proof_authority",
  "finite_upper_requires_lower_bound_le_upper_bound_and_bound_proof_authority",
  "exact_requires_known_count_equals_lower_bound_equals_upper_bound_and_exact_completeness_proof",
  "unbounded_unknown_requires_upper_bound_null"
];
assert(deepEqual(contract.denominator_model.target_count_bounds.rules, expectedMultiplicityRules), "multiplicity bound rules differ");
const multiplicityDecision = contract.decision_registry.find((decision) => decision.id === "D_MULTIPLICITY_001");
assert(multiplicityDecision, "D_MULTIPLICITY_001 is missing");
assert(multiplicityDecision.validator === "bounds_prefrozen_nonnegative_known_le_lower_and_upper_ge_lower_or_null_with_required_proof_authority", "D_MULTIPLICITY_001 validator differs");
assert(deepEqual(multiplicityDecision.allowed_domain.required, ["bound_sources", "bound_validator", "unbounded_disposition"]), "D_MULTIPLICITY_001 allowed domain changed");

const implementationComponents = ["adapter", "parser_extractor", "canonicalizer", "resolver", "adjudication_view_builder", "snapshot_packager", "registry_builder", "sampler", "probe_builder", "key_instantiator", "scorer", "controller", "replay_order", "aggregator_information_gate"];
assert(deepEqual(contract.implementation_binding.required_component_ids, implementationComponents), "initial implementation manifest is not exhaustive");
assert(contract.implementation_binding.unchanged_contract_or_profile_digest_is_sufficient === false, "unchanged semantic digest cannot authorize implementation replacement");
assert(contract.scorer_key_policy.target_key_instantiator.prohibited_additions.includes("new_partial_credit_rule"), "semantic scorer mutation guard missing");
assert(contract.c0_c1_equality.only_permitted_difference.path === "treatment.conv_mem_availability", "C0/C1 treatment difference path differs");
assert(contract.c0_c1_equality.required_equal_paths.includes("environment.runtime_versions"), "nested environment equality missing");
assert(contract.coordination.g6_lane === "separate_and_closed", "G6 lane must remain separate and closed");

assert(contract.contract_version === "naturalistic-pre-g6-contract-v3", "successor version differs");
assert(contract.status === "PROPOSED_NOT_LOCKED", "successor must remain proposed pending independent review and Ryan authorization");
assert(contract.supersedes.version === priorContract.contract_version, "successor does not name V2 as its parent authority");
assert(contract.supersedes.reviewed_commit === "9f4791c2744c02d742fdb9c0fa1e9dd150591ac1", "successor reviewed parent commit differs");
assert(contract.supersedes.canonical_digest === priorCanonicalDigest, "successor parent digest differs");
assert(contract.normative_authority.changed_field_manifest === "docs/plans/artifacts/naturalistic-pre-g6-contract-v3.amendment.json", "successor changed-field manifest path differs");
assert(conformance.contract_version === contract.contract_version, "conformance contract version differs");
assert(conformance.artifact_type === "naturalistic_pre_g6_contract_v3_conformance", "conformance artifact type differs");

const regressionProjection = structuredClone(contract);
regressionProjection.contract_version = priorContract.contract_version;
regressionProjection.supersedes.version = priorContract.supersedes.version;
regressionProjection.supersedes.reviewed_commit = priorContract.supersedes.reviewed_commit;
regressionProjection.supersedes.reason = priorContract.supersedes.reason;
delete regressionProjection.supersedes.canonical_digest;
regressionProjection.canonicalization.sidecar = priorContract.canonicalization.sidecar;
regressionProjection.canonicalization.validator = priorContract.canonicalization.validator;
regressionProjection.normative_authority.canonical_contract = priorContract.normative_authority.canonical_contract;
regressionProjection.normative_authority.schema = priorContract.normative_authority.schema;
regressionProjection.normative_authority.conformance_cases = priorContract.normative_authority.conformance_cases;
delete regressionProjection.normative_authority.changed_field_manifest;
regressionProjection.denominator_model.target_count_bounds.rules = structuredClone(
  priorContract.denominator_model.target_count_bounds.rules
);
regressionProjection.decision_registry.find(
  (decision) => decision.id === "D_MULTIPLICITY_001"
).validator = priorContract.decision_registry.find(
  (decision) => decision.id === "D_MULTIPLICITY_001"
).validator;
assert(deepEqual(
  contract.verification_controls,
  [...priorContract.verification_controls, ...multiplicityCases]
), "V3 verification controls are not the exact V2 controls plus the multiplicity cases");
regressionProjection.verification_controls = structuredClone(priorContract.verification_controls);
regressionProjection.coordination.dependency_chain[1] = priorContract.coordination.dependency_chain[1];
assert(deepEqual(regressionProjection, priorContract), "V3 contains a non-allowlisted semantic change from V2");

assert(amendmentManifest.historical_authority.canonical_digest === priorCanonicalDigest, "amendment manifest historical digest differs");
assert(amendmentManifest.historical_authority.preserved_immutable === true, "amendment manifest does not preserve V2 immutably");
assert(amendmentManifest.successor_authority.contract_version === contract.contract_version, "amendment manifest successor version differs");
assert(amendmentManifest.successor_authority.canonical_digest === digest, "amendment manifest successor digest differs");
assert(amendmentManifest.successor_authority.canonical_byte_count === canonicalBytes.length, "amendment manifest byte count differs");
assert(amendmentManifest.semantic_scope === "multiplicity_inequality_consistency_only", "amendment semantic scope differs");
assert(deepEqual(
  amendmentManifest.semantic_changes.map((change) => change.json_pointer),
  [
    "/denominator_model/target_count_bounds/rules",
    "/decision_registry/18/validator"
  ]
), "amendment manifest semantic field allowlist differs");
assert(amendmentManifest.bound_source_selection.selected === false, "amendment selected a Ryan-owned bound source");

process.stdout.write(`${JSON.stringify({
  status: "PASS",
  contract_version: contract.contract_version,
  canonical_digest: digest,
  sidecar_digest: sidecarDigest,
  canonical_byte_count: canonicalBytes.length,
  trailing_byte_negative_control: "PASS",
  historical_v2_digest: priorCanonicalDigest,
  unrelated_semantics_regression: "PASS",
  amendment_manifest_validation: "PASS",
  stage_count: contract.stage_graph.length,
  decision_count: contract.decision_registry.length,
  invariant_count: contract.invariants.length,
  control_count: contract.verification_controls.length,
  conformance_case_count: conformance.cases.length,
  multiplicity_conformance_case_count: multiplicityCases.length,
  firewall_negative_case_count: firewallCaseExpectations.size,
  implementation_component_count: contract.implementation_binding.required_component_ids.length,
  issue_263_provenance_root: true,
  g6_lane: contract.coordination.g6_lane
}, null, 2)}\n`);
