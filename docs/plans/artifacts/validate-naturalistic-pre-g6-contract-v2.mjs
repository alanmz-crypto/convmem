#!/usr/bin/env node

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const contractPath = join(here, "naturalistic-pre-g6-contract-v2.json");
const schemaPath = join(here, "naturalistic-pre-g6-contract-v2.schema.json");
const conformancePath = join(here, "naturalistic-pre-g6-contract-v2.conformance.json");
const sidecarPath = join(here, "naturalistic-pre-g6-contract-v2.json.sha256");

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
hasValidUnicode(contract);
validateSchema(contract, schema);

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
assert(/^[0-9a-f]{64}  naturalistic-pre-g6-contract-v2\.json\n$/.test(sidecar), "sidecar format must be sha256sum-compatible with exactly one terminal LF");
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
assert(p1.forbidden_fields.includes("resolver_output_digest") && p1.forbidden_fields.includes("target_census"), "P1 must forbid P2/P3 knowledge");
assert(contract.stage_graph[2].produces.includes("OpaqueResolverManifestV2"), "P2 must produce resolver authority");
assert(contract.stage_graph[3].produces.includes("TargetRegistryV2"), "P3/T2 must produce registry authority");
assert(contract.amendment_policy.same_authority_identity_with_changed_estimand === "PROHIBITED", "estimand amendment cannot retain authority identity");
assert(contract.amendment_policy.construct_amendment_requires.includes("new_contract_version") && contract.amendment_policy.construct_amendment_requires.includes("new_canonical_digest_and_sidecar") && contract.amendment_policy.construct_amendment_requires.includes("outcome_blind_independent_review"), "construct amendment controls incomplete");
assert(contract.role_access_policy.adjudication_interface.artifact === "AdjudicationEvidenceViewV1", "adjudication interface artifact differs");
assert(contract.role_access_policy.adjudication_interface.constant_shape === true && contract.role_access_policy.adjudication_interface.all_resolver_derived_fields_hidden === true, "role access does not enforce a constant blind interface");
assert(contract.role_access_policy.roles.adjudicator.may_not_read.includes("resolver_retry_count_and_timing") && contract.role_access_policy.roles.adjudicator.may_not_read.includes("resolver_missing_file_signals"), "adjudicator side-channel deny list incomplete");

const decisionFields = ["id", "name", "semantics", "allowed_domain", "units", "allowed_states", "preferred", "owner_authority", "freeze_stage", "evidence_required", "validator", "failure_transition", "accepted_downside", "overturning_evidence"];
const decisionIds = new Set();
for (const decision of contract.decision_registry) {
  for (const field of decisionFields) assert(Object.hasOwn(decision, field), `${decision.id ?? "decision"}: missing ${field}`);
  assert(!decisionIds.has(decision.id), `duplicate decision ID ${decision.id}`);
  decisionIds.add(decision.id);
  assert(decision.freeze_stage === "P0_T0_CONSTRUCT_FREEZE", `${decision.id}: wrong freeze stage`);
}

const requiredCases = [
  "jcs_without_trailing_newline",
  "p1_cannot_bind_p2_output",
  "clone_with_lineage_remains_distinct",
  "restore_preserved_native_ids_remains_distinct",
  "duplicate_content_distinct_occurrences",
  "known_present_additional_multiplicity_unknown",
  "unbounded_multiplicity_blocks",
  "incomplete_source_inventory_hidden_resolver",
  "source_deleted_after_intact_seal",
  "source_modified_after_seal",
  "stripped_origin_legacy_descendant",
  "summary_missing_consumed_dependency",
  "post_freeze_parser_canonicalizer_replacement",
  "target_specific_semantic_key_change",
  "unlisted_implementation_component",
  "nested_c0_c1_mismatch",
  "unknown_ryan_decision_value",
  "decision_missing_validator_or_authority"
];
assert(conformance.case_count === requiredCases.length, "conformance case_count mismatch");
assert(deepEqual(conformance.cases.map((item) => item.id), requiredCases), "conformance cases differ or are out of order");
for (const item of conformance.cases) {
  for (const field of ["id", "scenario", "input", "expected", "blocked_transition"]) assert(Object.hasOwn(item, field), `${item.id}: missing ${field}`);
  assert(contract.verification_controls.includes(item.id), `${item.id}: missing verification control`);
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
assert(contract.snapshot_authority.snapshot_is_occurrence_authority === false, "snapshot cannot become occurrence authority");
assert(contract.legacy_summary_firewall.unknown_lineage === "NON_NORMATIVE", "unknown provenance must be non-normative");
assert(contract.legacy_summary_firewall.stripping_original_content_cleans_descendant === false, "stripping legacy prose cannot clean descendants");

const implementationComponents = ["adapter", "parser_extractor", "canonicalizer", "resolver", "adjudication_view_builder", "snapshot_packager", "registry_builder", "sampler", "probe_builder", "key_instantiator", "scorer", "controller", "replay_order", "aggregator_information_gate"];
assert(deepEqual(contract.implementation_binding.required_component_ids, implementationComponents), "initial implementation manifest is not exhaustive");
assert(contract.implementation_binding.unchanged_contract_or_profile_digest_is_sufficient === false, "unchanged semantic digest cannot authorize implementation replacement");
assert(contract.scorer_key_policy.target_key_instantiator.prohibited_additions.includes("new_partial_credit_rule"), "semantic scorer mutation guard missing");
assert(contract.c0_c1_equality.only_permitted_difference.path === "treatment.conv_mem_availability", "C0/C1 treatment difference path differs");
assert(contract.c0_c1_equality.required_equal_paths.includes("environment.runtime_versions"), "nested environment equality missing");
assert(contract.coordination.g6_lane === "separate_and_closed", "G6 lane must remain separate and closed");

process.stdout.write(`${JSON.stringify({
  status: "PASS",
  contract_version: contract.contract_version,
  canonical_digest: digest,
  sidecar_digest: sidecarDigest,
  stage_count: contract.stage_graph.length,
  decision_count: contract.decision_registry.length,
  invariant_count: contract.invariants.length,
  control_count: contract.verification_controls.length,
  conformance_case_count: conformance.cases.length,
  implementation_component_count: contract.implementation_binding.required_component_ids.length,
  issue_263_provenance_root: true,
  g6_lane: contract.coordination.g6_lane
}, null, 2)}\n`);
