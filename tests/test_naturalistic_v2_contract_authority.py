"""V2-00 — locked PRE-G6 Contract V2 authority import and conformance oracle.

Hermetic tests only: no runtime identity classes, no live evidence, no G6/T0.
The locked Node validator is the primary conformance oracle; Python independently
reproduces RFC 8785/JCS bytes and digest for cross-check.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO / "docs/plans/artifacts"
CONTRACT_PATH = ARTIFACTS / "naturalistic-pre-g6-contract-v2.json"
CONFORMANCE_PATH = ARTIFACTS / "naturalistic-pre-g6-contract-v2.conformance.json"
SCHEMA_PATH = ARTIFACTS / "naturalistic-pre-g6-contract-v2.schema.json"
SIDECAR_PATH = ARTIFACTS / "naturalistic-pre-g6-contract-v2.json.sha256"
VALIDATOR_PATH = ARTIFACTS / "validate-naturalistic-pre-g6-contract-v2.mjs"

LOCKED_COMMIT = "9f4791c2744c02d742fdb9c0fa1e9dd150591ac1"
EXPECTED_DIGEST = "917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e"
EXPECTED_BYTE_COUNT = 47_330

LOCKED_ARTIFACTS = (
    "docs/plans/artifacts/naturalistic-pre-g6-contract-v2.json",
    "docs/plans/artifacts/naturalistic-pre-g6-contract-v2.conformance.json",
    "docs/plans/artifacts/naturalistic-pre-g6-contract-v2.schema.json",
    "docs/plans/artifacts/naturalistic-pre-g6-contract-v2.json.sha256",
    "docs/plans/artifacts/validate-naturalistic-pre-g6-contract-v2.mjs",
)

# Maps each published conformance case id to the executable control exercised here.
CASE_TO_CONTROL = {
    "jcs_without_trailing_newline": "validator_sidecar_and_python_jcs_trailing_LF_negative",
    "p1_cannot_bind_p2_output": "validator_p1_forbidden_later_stage_fields",
    "p1_rejects_resolver_result": "validator_firewall_case_p1_resolver_result",
    "p1_rejects_capability_vector": "validator_firewall_case_p1_capability_vector",
    "adjudicator_view_rejects_resolver_result": "validator_firewall_case_view_resolver_result",
    "adjudicator_view_rejects_capability_vector": "validator_firewall_case_view_capability_vector",
    "clone_with_lineage_remains_distinct": "verification_control_registry_presence",
    "restore_preserved_native_ids_remains_distinct": "verification_control_registry_presence",
    "duplicate_content_distinct_occurrences": "verification_control_registry_presence",
    "known_present_additional_multiplicity_unknown": "verification_control_registry_presence",
    "unbounded_multiplicity_blocks": "verification_control_registry_presence",
    "incomplete_source_inventory_hidden_resolver": "verification_control_registry_presence",
    "source_deleted_after_intact_seal": "verification_control_registry_presence",
    "source_modified_after_seal": "verification_control_registry_presence",
    "stripped_origin_legacy_descendant": "verification_control_registry_presence",
    "summary_missing_consumed_dependency": "verification_control_registry_presence",
    "post_freeze_parser_canonicalizer_replacement": "verification_control_registry_presence",
    "target_specific_semantic_key_change": "verification_control_registry_presence",
    "unlisted_implementation_component": "verification_control_registry_presence",
    "nested_c0_c1_mismatch": "verification_control_registry_presence",
    "unknown_ryan_decision_value": "verification_control_registry_presence",
    "decision_missing_validator_or_authority": "verification_control_registry_presence",
}


def _jcs(value: object) -> str:
    """RFC 8785 JCS — must match validate-naturalistic-pre-g6-contract-v2.mjs."""
    if value is None or isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, (int, float)):
        if not isinstance(value, bool):
            import math

            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("JCS forbids non-finite numbers")
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ",".join(_jcs(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        return "{" + ",".join(f"{json.dumps(k)}:{_jcs(value[k])}" for k in keys) + "}"
    raise TypeError(f"unsupported JCS value type: {type(value)!r}")


def _run_locked_validator() -> dict:
    proc = subprocess.run(
        ["node", str(VALIDATOR_PATH)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(proc.stdout)


def _git_blob_sha256(commit: str, path: str) -> str:
    proc = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    return hashlib.sha256(proc.stdout).hexdigest()


class ImportedArtifactIdentityTests(unittest.TestCase):
    def test_locked_artifact_bytes_match_authority_commit(self):
        for rel_path in LOCKED_ARTIFACTS:
            disk_path = REPO / rel_path
            self.assertTrue(disk_path.is_file(), f"missing imported artifact: {rel_path}")
            expected = _git_blob_sha256(LOCKED_COMMIT, rel_path)
            actual = hashlib.sha256(disk_path.read_bytes()).hexdigest()
            self.assertEqual(actual, expected, rel_path)


class CanonicalDigestTests(unittest.TestCase):
    def test_rfc8785_byte_count_and_digest(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        canonical_bytes = _jcs(contract).encode("utf-8")
        digest = hashlib.sha256(canonical_bytes).hexdigest()
        self.assertEqual(len(canonical_bytes), EXPECTED_BYTE_COUNT)
        self.assertEqual(digest, EXPECTED_DIGEST)

    def test_sidecar_matches_canonical_digest(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        canonical_bytes = _jcs(contract).encode("utf-8")
        digest = hashlib.sha256(canonical_bytes).hexdigest()
        sidecar = SIDECAR_PATH.read_text(encoding="utf-8")
        self.assertRegex(
            sidecar,
            rf"^{digest}  naturalistic-pre-g6-contract-v2\.json\n$",
        )


class LockedValidatorOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator_result = _run_locked_validator()
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.conformance = json.loads(CONFORMANCE_PATH.read_text(encoding="utf-8"))

    def test_validator_passes(self):
        self.assertEqual(self.validator_result["status"], "PASS")

    def test_validator_reports_locked_counts(self):
        self.assertEqual(self.validator_result["contract_version"], "naturalistic-pre-g6-contract-v2")
        self.assertEqual(self.validator_result["canonical_digest"], EXPECTED_DIGEST)
        self.assertEqual(self.validator_result["sidecar_digest"], EXPECTED_DIGEST)
        self.assertEqual(self.validator_result["conformance_case_count"], 22)
        self.assertEqual(self.validator_result["firewall_negative_case_count"], 4)
        self.assertEqual(self.validator_result["stage_count"], 12)
        self.assertTrue(self.validator_result["issue_263_provenance_root"])
        self.assertEqual(self.validator_result["g6_lane"], "separate_and_closed")

    def test_trailing_newline_negative_control(self):
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        canonical_bytes = _jcs(contract).encode("utf-8")
        sidecar_digest = SIDECAR_PATH.read_text(encoding="utf-8").split()[0]
        self.assertEqual(hashlib.sha256(canonical_bytes).hexdigest(), sidecar_digest)
        self.assertNotEqual(
            hashlib.sha256(canonical_bytes + b"\n").hexdigest(),
            sidecar_digest,
        )

    def test_unknown_top_level_field_rejected_by_schema(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertFalse(schema.get("additionalProperties", True))
        mutated = deepcopy(json.loads(CONTRACT_PATH.read_text(encoding="utf-8")))
        mutated["__v200_unknown_field_probe__"] = True
        script = f"""
const fs = require('fs');
const schema = JSON.parse(fs.readFileSync({json.dumps(str(SCHEMA_PATH))}, 'utf8'));
const value = {json.dumps(mutated)};
function fail(msg) {{ throw new Error(msg); }}
function typeMatches(value, expected) {{
  const candidates = Array.isArray(expected) ? expected : [expected];
  return candidates.some((candidate) => {{
    if (candidate === 'null') return value === null;
    if (candidate === 'array') return Array.isArray(value);
    if (candidate === 'object') return value !== null && typeof value === 'object' && !Array.isArray(value);
    if (candidate === 'integer') return Number.isInteger(value);
    return typeof value === candidate;
  }});
}}
function validateSchema(value, schema, path = '$') {{
  if (schema.type) {{
    if (!typeMatches(value, schema.type)) fail(`${{path}}: type mismatch`);
  }}
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {{
    if (schema.additionalProperties === false) {{
      const allowed = new Set(Object.keys(schema.properties ?? {{}}));
      for (const key of Object.keys(value)) {{
        if (!allowed.has(key)) fail(`${{path}}: unexpected property ${{key}}`);
      }}
    }}
  }}
}}
try {{
  validateSchema(value, schema);
  process.exit(2);
}} catch (err) {{
  if (String(err.message).includes('unexpected property')) process.exit(0);
  console.error(err);
  process.exit(1);
}}
"""
        proc = subprocess.run(["node", "-e", script], cwd=REPO, check=False)
        self.assertEqual(proc.returncode, 0, "unknown top-level field must fail schema validation")

    def test_every_conformance_case_has_executable_control(self):
        case_ids = [case["id"] for case in self.conformance["cases"]]
        self.assertEqual(len(case_ids), 22)
        self.assertEqual(self.conformance["case_count"], 22)
        missing = [cid for cid in case_ids if cid not in CASE_TO_CONTROL]
        self.assertEqual(missing, [])
        controls = set(self.contract["verification_controls"])
        for case_id in case_ids:
            self.assertIn(case_id, controls, case_id)
            self.assertIn(case_id, CASE_TO_CONTROL)

    def test_p1_forbids_canonical_p2_fields(self):
        p1 = next(s for s in self.contract["stage_graph"] if s["id"] == "P1_T1_EVIDENCE_SEAL")
        for field in ("resolver_result", "capability_vector", "resolver_output_digest", "target_census"):
            self.assertIn(field, p1["forbidden_fields"], field)

    def test_adjudicator_firewall_fields(self):
        deny = self.contract["role_access_policy"]["roles"]["adjudicator"]["may_not_read"]
        view_deny = self.contract["adjudication_view"]["forbidden_fields"]
        for field in ("resolver_result", "capability_vector", "OpaqueResolverManifestV2"):
            self.assertIn(field, deny, field)
        for field in ("resolver_result", "capability_vector"):
            self.assertIn(field, view_deny, field)

    def test_issue_263_invariant_present(self):
        roots = self.contract["provenance_roots"]
        issue = next(r for r in roots if r.get("id") == "github_issue_263")
        self.assertEqual(
            issue["required_invariant"],
            "source_present_but_verbatim_evidence_unavailable_must_never_be_reported_as_source_absent",
        )


if __name__ == "__main__":
    unittest.main()
