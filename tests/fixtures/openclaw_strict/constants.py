"""Frozen T0a constants from Architecture §6.5.8 / Execution §5.1."""

from __future__ import annotations

CODE_BASELINE_SHA = "5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d"
SEMANTIC_PARENT_SHA = "9faac8ea87532bc73f74b788b38234de0c614a4e"
M11_REVIEWED_OVERLAY_SHA = "95011db461d51dcd3960a375757418401c5e505b"
M11_CONTROL_PLANE_INPUTS = frozenset(
    {
        "docs/plans/ARCHITECTURE-openclaw-convmem-integration.md",
        "docs/plans/EXECUTION-openclaw-convmem-integration.md",
        "docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md",
        "docs/plans/STATUS-openclaw-convmem-integration.md",
    }
)
EXPECTED_TEST_RUNTIME_TREE_SHA256 = (
    "sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b"
)

RUNTIME_NOT_QUALIFIED = "runtime_not_qualified"
EX_CONFIG = 78
HEX40_RE = r"^[0-9a-f]{40}$"

TMPFS_SIZE_BYTES = 268435456
SUITE_WALL_DEADLINE_SEC = 600
SUITE_OUTPUT_LIMIT_BYTES = 16777216
TMP_SAMPLE_INTERVAL_SEC = 1.0

CHILD_ENV = {
    "HOME": "/fixture/home",
    "TMPDIR": "/fixture/tmp",
    "XDG_CONFIG_HOME": "/fixture/config",
    "XDG_CACHE_HOME": "/fixture/cache",
    "XDG_DATA_HOME": "/fixture/data",
    "PATH": "/runtime/bin:/usr/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
}

HOST_SENTINEL_ENV = {
    "CONVMEM_OPENCLAW_SENTINEL_CRED": "synthetic-canary-credential",
    "CONVMEM_OPENCLAW_SENTINEL_CONFIG": "synthetic-canary-config",
}

FORBIDDEN_CHILD_ENV_PREFIXES = (
    "OPENCLAW_FIXTURE_SELECT_FAKE",
    "CONVMEM_SELECT_PRODUCTION_FAKE",
    "OPENCLAW_USE_FAKE",
)

BWRAP_MANDATORY_FLAGS = (
    "--unshare-user",
    "--unshare-pid",
    "--unshare-ipc",
    "--unshare-net",
    "--unshare-uts",
    "--disable-userns",
    "--assert-userns-disabled",
    "--cap-drop",
    "ALL",
    "--new-session",
    "--die-with-parent",
)

FORBIDDEN_BWRAP_FLAGS = (
    "--unshare-user-try",
    "--unshare-ipc-try",
    "--unshare-pid-try",
    "--unshare-net-try",
    "--unshare-uts-try",
    "--unshare-cgroup-try",
    "--share-net",
    "--not-a-security-boundary",
    "--as-pid-1",
)

EDIT_ALLOWLIST_EXACT = frozenset(
    {
        "openclaw_activation_controller.py",
        "openclaw_activation_supervisor.py",
        "openclaw_strict_server.py",
        "bound_read_scope.py",
        "strict_grounding.py",
        "strict_evidence_state.py",
        "strict_projection_publisher.py",
        "strict_projection.py",
        "mcp_server.py",
        "requirements.txt",
        "integrations/openclaw-convmem-reader/package.json",
        "integrations/openclaw-convmem-reader/openclaw.plugin.json",
        "integrations/openclaw-convmem-reader/index.js",
        "integrations/openclaw-convmem-reader/test/connector.test.mjs",
        "tests/test_bound_read_scope.py",
        "tests/test_strict_grounding.py",
        "tests/test_strict_evidence_state.py",
        "tests/test_strict_projection_publisher.py",
        "tests/test_strict_projection.py",
        "tests/test_strict_projection_recovery.py",
        "tests/test_mcp_openclaw_strict.py",
        "tests/test_strict_snapshot_revocation.py",
        "tests/test_openclaw_lifecycle_config.py",
        "tests/test_openclaw_connector_contract.py",
        "tests/test_openclaw_activation_controller.py",
        "tests/test_openclaw_activation_supervisor.py",
        "tests/test_openclaw_strict_packet_contract.py",
    }
)
EDIT_ALLOWLIST_PREFIXES = ("tests/fixtures/openclaw_strict/",)
_SCHEMA_ALLOWLIST_MEMBERS = (
    "schemas/convmem-bound-read-scope-v2.schema.json",
    "schemas/convmem-project-binding-registry-v3.schema.json",
    "schemas/convmem-bound-authority-record-v3.schema.json",
    "schemas/convmem-authority-disposition-v1.schema.json",
    "schemas/convmem-strict-provenance-context-v2.schema.json",
    "schemas/convmem-strict-grounding-v1.schema.json",
    "schemas/convmem-capture-receipt-v1.schema.json",
    "schemas/convmem-strict-fixture-bundle-v2.schema.json",
    "schemas/convmem-strict-citation-map-v1.schema.json",
    "schemas/convmem-bound-authority-manifest-v3.schema.json",
    "schemas/convmem-bound-projection-row-v2.schema.json",
    "schemas/convmem-strict-graph-v1.schema.json",
    "schemas/convmem-bound-projection-manifest-v3.schema.json",
    "schemas/convmem-strict-generation-layout-v2.schema.json",
    "schemas/convmem-strict-publication-v2.schema.json",
    "schemas/convmem-strict-enrollment-v1.schema.json",
    "schemas/convmem-strict-slot-v1.schema.json",
    "schemas/convmem-strict-source-cutoff-v1.schema.json",
    "schemas/convmem-strict-semantic-contract-v1.schema.json",
    "schemas/convmem-strict-state-v2.schema.json",
    "schemas/convmem-clock-review-v1.schema.json",
    "schemas/convmem-raw-evidence-v3.schema.json",
    "schemas/convmem-error-v1.schema.json",
    "schemas/convmem-strict-config-v2.schema.json",
    "schemas/convmem-openclaw-connector-launch-v2.schema.json",
    "schemas/convmem-openclaw-activation-v2.schema.json",
    "schemas/convmem-activation-control-v1.schema.json",
    "schemas/convmem-activation-retirement-v1.schema.json",
    "schemas/convmem-activation-launch-policy-v1.schema.json",
    "schemas/convmem-activation-manager-policy-v1.schema.json",
    "schemas/convmem-controller-socket-policy-v1.schema.json",
)
SCHEMA_ALLOWLIST = frozenset(_SCHEMA_ALLOWLIST_MEMBERS)


STRICT_PYTEST_FILES = (
    "tests/test_bound_read_scope.py",
    "tests/test_strict_grounding.py",
    "tests/test_strict_evidence_state.py",
    "tests/test_strict_projection_publisher.py",
    "tests/test_strict_projection.py",
    "tests/test_strict_projection_recovery.py",
    "tests/test_mcp_openclaw_strict.py",
    "tests/test_strict_snapshot_revocation.py",
    "tests/test_openclaw_lifecycle_config.py",
    "tests/test_openclaw_connector_contract.py",
    "tests/test_openclaw_activation_controller.py",
    "tests/test_openclaw_activation_supervisor.py",
    "tests/test_openclaw_strict_packet_contract.py",
)
CONNECTOR_NODE_TEST = "integrations/openclaw-convmem-reader/test/connector.test.mjs"
LEGACY_PYTEST_FILES = (
    "tests/test_site_filter.py",
    "tests/test_milestone_c.py",
    "tests/test_agent_run_ledger.py",
    "tests/test_query_ledger_lookup.py",
    "tests/test_query_search_harden.py",
    "tests/test_ledger_related.py",
    "tests/test_unresolved_payload.py",
    "tests/test_file_generation_store.py",
    "tests/test_file_generation_validate.py",
    "tests/test_governed_recovery_and_writers.py",
    "tests/test_governed_writer_gate.py",
    "tests/test_shadow_writer_coverage_scan.py",
    "tests/test_provenance.py",
    "tests/test_provenance_continuity.py",
)
LEGACY_DESELECTS = (
    "tests/test_agent_run_ledger.py::test_v8_kiro_hook_adapter_fail_open",
    "tests/test_agent_run_ledger.py::test_v6_git_facts_non_git_cwd",
    "tests/test_agent_run_ledger.py::test_q7_hook_failure_writes_stderr",
    "tests/test_agent_run_ledger.py::test_q4_hook_two_missing_id_starts_same_cwd",
)

# Exact closed MCP tool inventory (Architecture §8 / Execution §9).
STRICT_TOOL_NAMES = ("search", "unresolved", "related")

# M7 evidence-class labels — never upgrade FAKE/STATIC/DISPOSABLE to REAL success.
EVIDENCE_LABELS = ("STATIC", "FAKE", "DISPOSABLE_KERNEL", "REAL")

# Disposable fixture evidence paths (host fixture_root/evidence ↔ /fixture/evidence).
EVIDENCE_MANIFEST_REL = "evidence/fixture-manifest.json"
EVIDENCE_AUDIT_REL = "evidence/bounded-audit-evidence.json"
EVIDENCE_SUITE_RESULTS_REL = "evidence/suite_results.json"
EVIDENCE_JUNIT_STRICT_REL = "evidence/pytest-strict-junit.xml"
EVIDENCE_JUNIT_LEGACY_REL = "evidence/pytest-legacy-junit.xml"
EVIDENCE_NODE_OUTCOMES_REL = "evidence/pytest-node-outcomes.json"
JUNIT_STRICT_PATH = "/fixture/evidence/pytest-strict-junit.xml"
JUNIT_LEGACY_PATH = "/fixture/evidence/pytest-legacy-junit.xml"
NODE_OUTCOMES_PATH = "/fixture/evidence/pytest-node-outcomes.json"
NODE_OUTCOMES_SCHEMA = "convmem.pytest-node-outcomes.v1"
SELECTED_NODES_STRICT_PATH = "/fixture/selected_nodes_strict.json"
PROMPT_INJECTION_SPECIMEN_REL = (
    "tests/fixtures/openclaw_strict/protocol_fixture/"
    "prompt_injection_tool_result.specimen.json"
)

# Fixed M8 behavioral baseline (Execution §5.1) — correction must preserve these.
EXPECTED_STRICT_JUNIT_COUNTS = {
    "collected": 238,
    "passed": 238,
    "failed": 0,
    "error": 0,
    "skipped": 0,
}
EXPECTED_LEGACY_JUNIT_COUNTS = {
    "collected": 116,
    "passed": 115,
    "failed": 0,
    "error": 0,
    "skipped": 1,
}
EXPECTED_LEGACY_DESELECTION_COUNT = 4

# Exact generated relative paths excluded from fixture/source inventories.
GENERATED_EVIDENCE_FIXTURE_RELS = frozenset(
    {
        "fixture-manifest.json",
        "suite_results.json",
        "evidence/fixture-manifest.json",
        "evidence/bounded-audit-evidence.json",
        "evidence/suite_results.json",
        "evidence/pytest-strict-junit.xml",
        "evidence/pytest-legacy-junit.xml",
        "evidence/pytest-node-outcomes.json",
    }
)
GENERATED_EVIDENCE_SOURCE_RELS = frozenset(
    {
        "tests/fixtures/openclaw_strict/fixture-manifest.json",
        "tests/fixtures/openclaw_strict/suite_results.json",
        "tests/fixtures/openclaw_strict/evidence/fixture-manifest.json",
        "tests/fixtures/openclaw_strict/evidence/bounded-audit-evidence.json",
        "tests/fixtures/openclaw_strict/evidence/suite_results.json",
        "tests/fixtures/openclaw_strict/evidence/pytest-strict-junit.xml",
        "tests/fixtures/openclaw_strict/evidence/pytest-legacy-junit.xml",
        "tests/fixtures/openclaw_strict/evidence/pytest-node-outcomes.json",
    }
)

# Protected CORE helpers for M7 protected-byte proof (Architecture §6.5.9 CORE).
PROTECTED_BYTE_PROOF_PATHS = (
    "canonical_json.py",
    "provenance.py",
    "provenance_binding.py",
    "domains.py",
    "requirements.txt",
)

INTEGRATION_IMPORT_SENTINELS = (
    "openclaw_activation_controller",
    "openclaw_activation_supervisor",
    "openclaw_strict_server",
    "bound_read_scope",
    "strict_grounding",
    "strict_evidence_state",
    "strict_projection_publisher",
    "strict_projection",
)

PREFLIGHT_OK_PATH = "/fixture/preflight_ok"
PREFLIGHT_REPORT_PATH = "/fixture/preflight_report.json"
IMPORT_TRACE_PATH = "/fixture/import_trace.json"
FROZEN_INVENTORY_PATH = "/fixture/frozen_runtime_inventory.json"
CANARY_PATHS_FILE = "/fixture/canary_paths.json"
HOST_NETNS_FILE = "/fixture/host_net_ns"
FD_OBSERVATION_FILE = "/fixture/fd_observation.json"
NS_OBSERVATION_FILE = "/fixture/ns_observation.json"
SYNTHETIC_DEP_ROOT = "/fixture/synthetic_dep"
SYNTHETIC_DEP_INVENTORY = "/fixture/synthetic_dep/inventory.json"
SYNTHETIC_DEP_TREE = "/fixture/synthetic_dep/tree"
SYNTHETIC_HOST_USR_INVENTORY = "/fixture/synthetic_host_usr/inventory.json"
SYNTHETIC_HOST_USR_TREE = "/fixture/synthetic_host_usr/tree"
RESOLUTION_REPORT_PATH = "/fixture/resolution_report.json"
NODE_RESOLUTION_REPORT_PATH = "/fixture/node_resolution_report.json"
PLUGIN_INVENTORY_PATH = "/fixture/pytest_plugin_inventory.json"
LEGACY_IDENTITY_CONFIG = "/fixture/home/.config/convmem/config.toml"
LEGACY_IDENTITY_CHROMA = "/fixture/legacy-live-identity/chroma"

INNER_ROLE_ENV = "CONVMEM_OPENCLAW_INNER_ROLE"
INNER_ROLE_VALUE = "inner"

FROZEN_PYTHON = "3.13.12"
FROZEN_UNICODE = "15.1.0"
FROZEN_NODE = "v26.9.0"
FROZEN_MCP = "1.28.1"
FROZEN_IDNA = "3.18"

CONTROL_EXPOSED_CANARY = "exposed_canary"
CONTROL_HOST_USR = "host_usr"
CONTROL_MISSING_DEP = "missing_dep"
CONTROL_CHANGED_DEP = "changed_dep"
CONTROL_UNLISTED_FILE = "unlisted_file"
CONTROL_WRONG_NAMESPACE = "wrong_namespace"
CONTROL_WRONG_ENV = "wrong_env"
CONTROL_EXTRA_FD = "extra_fd"
CONTROL_ARBITRARY_SUITE = "arbitrary_suite"
CONTROL_PRODUCTION_FAKE = "production_fake"

ALL_NEGATIVE_CONTROLS = (
    CONTROL_EXPOSED_CANARY,
    CONTROL_HOST_USR,
    CONTROL_MISSING_DEP,
    CONTROL_CHANGED_DEP,
    CONTROL_UNLISTED_FILE,
    CONTROL_WRONG_NAMESPACE,
    CONTROL_WRONG_ENV,
    CONTROL_EXTRA_FD,
    CONTROL_ARBITRARY_SUITE,
    CONTROL_PRODUCTION_FAKE,
)

# Exact expected independent failure reason prefixes (correction 4/5).
CONTROL_EXPECTED_REASON_PREFIX = {
    CONTROL_EXPOSED_CANARY: "canary_exposed:",
    CONTROL_HOST_USR: "unlisted_or_host_usr:",
    CONTROL_MISSING_DEP: "missing_dependency:",
    CONTROL_CHANGED_DEP: "changed_dependency:",
    CONTROL_UNLISTED_FILE: "unlisted_dependency:",
    CONTROL_WRONG_NAMESPACE: "netns_not_isolated",
    CONTROL_WRONG_ENV: "sentinel_env_present:",
    CONTROL_EXTRA_FD: "unexpected_inherited_fds:",
    CONTROL_ARBITRARY_SUITE: "arbitrary_suite_or_selector_drift:",
    CONTROL_PRODUCTION_FAKE: "production_fake_selector:",
}
