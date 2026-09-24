"""Independent parent-derived field-set table for Gate B/C schemas (M2/T0b).

Source: Architecture-openclaw-convmem-integration.md at plan parent d5f986f0…
(section 6.x closed field freezes). This table is authored from that parent text;
it must not be generated from on-disk schemas or positive instances.
"""

from __future__ import annotations

from typing import Any

# Top-level: frozenset of property names (== required for these closed objects).
TOP_LEVEL: dict[str, frozenset[str]] = {
    "convmem-bound-read-scope-v2.schema.json": frozenset(
        {
            "schema",
            "project",
            "allowed_project_bindings",
            "domain",
            "site_mode",
            "site",
            "authority_snapshot",
            "serving_projection",
            "max_snapshot_age_seconds",
        }
    ),
    "convmem-project-binding-registry-v3.schema.json": frozenset(
        {"schema", "revision", "bindings"}
    ),
    "convmem-bound-authority-record-v3.schema.json": frozenset(
        {
            "schema",
            "project_binding_id",
            "source_registration_id",
            "authority_site",
            "authority_domain",
            "record_kind",
            "logical_id",
            "assertion_id",
            "source_event_id",
            "producer",
            "logical_key",
            "semantic_sha256",
            "payload_sha256",
            "title",
            "document",
            "observed_at",
            "recorded_at",
            "confidence_bps",
            "relates_to_assertion_id",
            "target_assertion_id",
            "verification_result",
            "supersedes_assertion_ids",
            "decision_disposition_ref",
            "supersession_disposition_ref",
            "provenance_envelope",
            "provenance_commitment",
            "origin_assurance",
            "provenance_qualification",
            "check_eligibility",
        }
    ),
    "convmem-authority-disposition-v1.schema.json": frozenset(
        {
            "schema",
            "action",
            "project_binding_id",
            "subject_assertion_id",
            "subject_semantic_sha256",
            "target_assertion_ids",
            "basis_snapshot_id",
            "expected_head_assertion_ids",
            "replaces_disposition_ref",
            "review_actor",
            "review_role",
            "review_outcome",
            "reviewed_at",
            "ratifier_actor",
            "ratifier_role",
            "ratified_at",
            "rationale_sha256",
        }
    ),
    "convmem-strict-provenance-context-v2.schema.json": frozenset(
        {
            "schema",
            "schema_semantics",
            "policies",
            "recipes",
            "verified_channels",
            "registered_assertions",
            "grounding_sha256",
            "context_payload_sha256",
        }
    ),
    "convmem-strict-grounding-v1.schema.json": frozenset(
        {
            "schema",
            "blobs",
            "roots",
            "edges",
            "outputs",
            "receipts",
            "grounding_payload_sha256",
        }
    ),
    "convmem-capture-receipt-v1.schema.json": frozenset(
        {
            "schema",
            "capture_id",
            "capture_class",
            "capture_issuer_id",
            "source_registration_id",
            "source_event_id",
            "provenance_assertion_id",
            "provenance_commitment",
            "input_bindings_sha256",
            "transformer_artifact_sha256",
            "recipe_sha256",
            "submitted_views_sha256",
            "returned_output_sha256",
            "captured_at",
            "receipt_payload_sha256",
        }
    ),
    "convmem-strict-fixture-bundle-v2.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "operation_id",
            "expected_parent_manifest_sha256",
            "batches",
            "dispositions",
            "provenance_context",
            "grounding",
            "built_at",
            "as_of",
            "expires_at",
            "fixture_payload_sha256",
        }
    ),
    "convmem-strict-citation-map-v1.schema.json": frozenset(
        {"schema", "citations", "citation_map_payload_sha256"}
    ),
    "convmem-bound-authority-manifest-v3.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "authority_seq",
            "owner_digest",
            "snapshot_id",
            "parent_snapshot_id",
            "parent_manifest_sha256",
            "scope_sha256",
            "registry_sha256",
            "input_sha256",
            "source_cutoff_sha256",
            "operation_id",
            "authority_records_sha256",
            "record_count",
            "dispositions_sha256",
            "disposition_count",
            "citation_map_sha256",
            "provenance_context_sha256",
            "grounding_sha256",
            "added_assertion_ids",
            "added_disposition_ids",
            "added_provenance_ids",
            "added_grounding_refs",
            "semantic_contract_sha256",
            "reducer_version",
            "canonicalization_version",
            "builder_version",
            "builder_tree_sha256",
            "built_at",
            "as_of",
            "expires_at",
            "manifest_payload_sha256",
        }
    ),
    "convmem-bound-projection-row-v2.schema.json": frozenset(
        {
            "schema",
            "project_binding_id",
            "public_binding_ref",
            "source_registration_id",
            "authority_site",
            "authority_domain",
            "record_kind",
            "logical_id",
            "assertion_id",
            "public_ledger_id",
            "citation_ref",
            "title",
            "document",
            "observed_at",
            "recorded_at",
            "confidence_bps",
            "relates_to_assertion_id",
            "target_assertion_id",
            "verification_result",
            "supersedes_assertion_ids",
            "decision_disposition_ref",
            "supersession_disposition_ref",
            "origin_assurance",
            "provenance_qualification",
            "check_eligibility",
            "authority_state",
            "verification_state",
            "state_disposition_refs",
            "payload_sha256",
            "state_sha256",
        }
    ),
    "convmem-strict-graph-v1.schema.json": frozenset(
        {"schema", "nodes", "edges", "graph_payload_sha256"}
    ),
    "convmem-bound-projection-manifest-v3.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "authority_seq",
            "owner_digest",
            "generation_id",
            "previous_generation_id",
            "snapshot_id",
            "authority_manifest_sha256",
            "scope_sha256",
            "registry_sha256",
            "semantic_contract_sha256",
            "rows_sha256",
            "row_count",
            "graph_sha256",
            "graph_node_count",
            "search_kernel",
            "search_kernel_version",
            "tokenizer_unicode_version",
            "builder_version",
            "builder_tree_sha256",
            "built_at",
            "as_of",
            "expires_at",
            "manifest_payload_sha256",
        }
    ),
    "convmem-strict-generation-layout-v2.schema.json": frozenset(
        {
            "schema",
            "authority_dir",
            "projection_dir",
            "active_dir",
            "locks_dir",
            "control_dir",
            "layout_payload_sha256",
        }
    ),
    "convmem-strict-publication-v2.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "owner_digest",
            "epoch",
            "authority_seq",
            "authority_snapshot_id",
            "authority_manifest_sha256",
            "authority_source_cutoff_sha256",
            "serving_generation_id",
            "projection_manifest_sha256",
            "semantic_contract_sha256",
            "pending_operation_id",
            "mode",
            "previous_publication_sha256",
            "freshness_anchor",
            "published_at",
            "publication_payload_sha256",
        }
    ),
    "convmem-strict-enrollment-v1.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "slot_id",
            "mode",
            "owner_digest",
            "operator_uid",
            "controller_uid",
            "supervisor_uid",
            "runtime_uid",
            "scope_sha256",
            "registry_sha256",
            "semantic_contract_sha256",
            "initial_source_cutoff_sha256",
            "enrollment_payload_sha256",
        }
    ),
    "convmem-strict-slot-v1.schema.json": frozenset(
        {
            "schema",
            "slot_id",
            "lineage_id",
            "activation_id",
            "activation_manifest_sha256",
            "unit_invocation_id",
            "state",
            "retirement_ref",
            "slot_payload_sha256",
        }
    ),
    "convmem-strict-source-cutoff-v1.schema.json": frozenset(
        {"schema", "lineage_id", "mode", "operations", "cutoff_payload_sha256"}
    ),
    "convmem-strict-semantic-contract-v1.schema.json": frozenset(
        {
            "schema",
            "reducer_version",
            "grounding_version",
            "canonicalization_version",
            "identity_version",
            "search_kernel",
            "search_kernel_version",
            "tokenizer_unicode_version",
            "schema_digests",
            "contract_payload_sha256",
        }
    ),
    "convmem-strict-state-v2.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "authority_seq",
            "authority_manifest_sha256",
            "semantic_contract_sha256",
            "assertion_id",
            "authority_state",
            "verification_state",
            "subject_head_assertion_ids",
            "verification_inputs",
            "state_disposition_refs",
        }
    ),
    "convmem-clock-review-v1.schema.json": frozenset(
        {
            "schema",
            "lineage_id",
            "authority_snapshot_id",
            "boot_id",
            "expires_at",
            "reviewed_wall_time",
            "reviewer_uid",
            "review_payload_sha256",
        }
    ),
    "convmem-raw-evidence-v3.schema.json": frozenset(
        {
            "schema",
            "instruction_authority",
            "snapshot",
            "selection_complete",
            "display_basis",
            "results",
        }
    ),
    "convmem-error-v1.schema.json": frozenset({"schema", "error", "correlation_id"}),
    "convmem-strict-config-v2.schema.json": frozenset(
        {
            "schema",
            "projection_root",
            "max_projection_rows",
            "max_projection_bytes",
            "telemetry",
        }
    ),
    "convmem-openclaw-connector-launch-v2.schema.json": frozenset(
        {
            "schema",
            "python_executable",
            "python_executable_sha256",
            "strict_server_path",
            "strict_server_tree_sha256",
            "working_directory",
            "scope_file",
            "registry_file",
            "strict_config_file",
            "scope_sha256",
            "registry_sha256",
            "strict_config_sha256",
            "service_home",
            "path_value",
            "lang",
            "lc_all",
            "temp_directory",
            "setpriv_executable",
            "setpriv_sha256",
            "seccomp_filter_file",
            "seccomp_filter_sha256",
            "runtime_distribution_sha256",
            "launch_policy_sha256",
            "manager_policy_sha256",
            "launch_payload_sha256",
        }
    ),
    "convmem-openclaw-activation-v2.schema.json": frozenset(
        {
            "schema",
            "activation_id",
            "slot_id",
            "lineage_id",
            "owner_digest",
            "publication_sha256",
            "scope_sha256",
            "registry_sha256",
            "strict_config_sha256",
            "authority_manifest_sha256",
            "projection_manifest_sha256",
            "snapshot_id",
            "as_of",
            "expires_at",
            "openclaw_version",
            "openclaw_config_sha256",
            "plugin_tree_sha256",
            "connector_launch_sha256",
            "strict_server_tree_sha256",
            "supervisor_tree_sha256",
            "controller_tree_sha256",
            "runtime_distribution_sha256",
            "model_artifacts_sha256",
            "launch_policy_sha256",
            "manager_policy_sha256",
            "control_protocol_version",
            "release_protocol_version",
            "state_dir",
            "gateway_port",
            "gateway_argv_sha256",
            "agent_argv_sha256",
            "created_at",
            "max_monotonic_lifetime_seconds",
            "manifest_payload_sha256",
        }
    ),
    "convmem-activation-retirement-v1.schema.json": frozenset(
        {
            "schema",
            "slot_id",
            "activation_id",
            "activation_manifest_sha256",
            "pinned_publication_sha256",
            "manager_boot_id",
            "unit_invocation_id",
            "containment_id",
            "terminal_reason",
            "observed_empty_boottime_ns",
            "receipt_payload_sha256",
        }
    ),
    "convmem-activation-launch-policy-v1.schema.json": frozenset(
        {
            "schema",
            "runtime_distribution_sha256",
            "model_artifacts_sha256",
            "processes",
            "read_only_mounts",
            "writable_mounts",
            "endpoints",
            "operator_uid",
            "controller_uid",
            "supervisor_uid",
            "runtime_uid",
            "manager_policy_sha256",
            "policy_payload_sha256",
        }
    ),
    "convmem-activation-manager-policy-v1.schema.json": frozenset(
        {
            "schema",
            "unit_bytes_b64",
            "unit_sha256",
            "controller_socket_policy_sha256",
            "runtime_distribution_sha256",
            "operator_uid",
            "controller_uid",
            "supervisor_uid",
            "runtime_uid",
            "kernel_release",
            "systemd_version",
            "capability_evidence_sha256",
            "policy_payload_sha256",
        }
    ),
    "convmem-controller-socket-policy-v1.schema.json": frozenset(
        {
            "schema",
            "socket_path",
            "socket_mode",
            "owner_uid",
            "permitted_peer_uid",
            "max_request_bytes",
            "max_response_bytes",
            "policy_payload_sha256",
        }
    ),
}

# Activation-control is oneOf — per-variant top-level sets.
ACTIVATION_CONTROL_VARIANTS_FIELDS: dict[str, frozenset[str]] = {
    "turn": frozenset(
        {
            "schema",
            "op",
            "request_id",
            "slot_id",
            "activation_id",
            "turn_id",
            "text",
            "expected_publication_sha256",
        }
    ),
    "cancel": frozenset(
        {"schema", "op", "request_id", "slot_id", "activation_id", "turn_id"}
    ),
    "status": frozenset({"schema", "op", "request_id", "slot_id", "activation_id"}),
    "revoke": frozenset(
        {"schema", "op", "request_id", "slot_id", "activation_id", "reason"}
    ),
}

# Nested object families the parent explicitly freezes.
NESTED: dict[str, frozenset[str]] = {
    "registry_binding": frozenset(
        {
            "id",
            "public_ref",
            "project",
            "domain_root",
            "site_mode",
            "site",
            "non_expanding_roots",
            "source_registrations",
            "lineage_id",
            "capture_issuers",
            "verification_producers",
        }
    ),
    "registry_source": frozenset(
        {
            "id",
            "source_class",
            "source_identity",
            "identity_match",
            "authorization_domain",
            "site",
            "event_id_resolver",
        }
    ),
    "registry_capture_issuer": frozenset(
        {
            "issuer_id",
            "capture_class",
            "enrollment_sha256",
            "receipt_root",
            "source_registration_ids",
        }
    ),
    "registry_verification_producer": frozenset(
        {
            "source_registration_id",
            "producer",
            "transformer_identity",
            "transformer_version",
            "transformer_artifact_sha256",
            "recipe_sha256",
            "capture_class",
        }
    ),
    "provenance_schema_semantics": frozenset(
        {"schema_version", "binding_version", "semantic_bytes_b64", "semantic_sha256"}
    ),
    "provenance_policy": frozenset(
        {"policy_version", "semantic_bytes_b64", "semantic_sha256", "rules"}
    ),
    "provenance_policy_rule": frozenset(
        {
            "transformer_class",
            "transformer_identity",
            "transformer_version",
            "recipe_id",
            "cap",
            "preservation_contract",
            "artifact_sha256",
        }
    ),
    "provenance_recipe": frozenset(
        {"recipe_id", "recipe_bytes_b64", "recipe_sha256"}
    ),
    "provenance_verified_channel": frozenset(
        {
            "origin_class",
            "channel_class",
            "channel_locator",
            "channel_evidence_sha256",
        }
    ),
    "provenance_registered_assertion": frozenset(
        {"assertion_id", "provenance_commitment", "envelope"}
    ),
    "grounding_blob": frozenset({"sha256", "length", "bytes_b64"}),
    "grounding_root": frozenset(
        {
            "provenance_assertion_id",
            "provenance_commitment",
            "source_registration_id",
            "source_event_id",
            "source_identity",
            "record_locator",
            "raw_blob_sha256",
            "view_blob_sha256",
            "selector",
            "receipt_ref",
        }
    ),
    "grounding_edge": frozenset(
        {
            "child_provenance_assertion_id",
            "child_provenance_commitment",
            "parent_provenance_assertion_id",
            "parent_provenance_commitment",
            "parent_output_blob_sha256",
            "view_blob_sha256",
            "selector",
            "receipt_ref",
        }
    ),
    "grounding_output": frozenset(
        {"provenance_assertion_id", "provenance_commitment", "output_blob_sha256"}
    ),
    "grounding_selector_identity": frozenset({"kind"}),
    "grounding_selector_byte_range": frozenset({"kind", "start", "end"}),
    "capture_receipt": frozenset(
        {
            "schema",
            "capture_id",
            "capture_class",
            "capture_issuer_id",
            "source_registration_id",
            "source_event_id",
            "provenance_assertion_id",
            "provenance_commitment",
            "input_bindings_sha256",
            "transformer_artifact_sha256",
            "recipe_sha256",
            "submitted_views_sha256",
            "returned_output_sha256",
            "captured_at",
            "receipt_payload_sha256",
        }
    ),
    "fixture_batch": frozenset({"source_registration_id", "source"}),
    "fixture_scan_source": frozenset(
        {"schema", "event_key", "captured_at", "records"}
    ),
    "fixture_source_record": frozenset(
        {
            "record_kind",
            "producer",
            "logical_key",
            "title",
            "document",
            "observed_at",
            "confidence_bps",
            "relates_to_assertion_id",
            "target_assertion_id",
            "verification_result",
            "provenance_assertion_id",
        }
    ),
    "citation_entry": frozenset(
        {
            "citation_ref",
            "assertion_id",
            "provenance_assertion_id",
            "provenance_commitment",
            "root_bindings",
            "input_bindings",
        }
    ),
    "citation_ref_object": frozenset(
        {"schema", "project_binding_id", "assertion_id", "provenance_commitment"}
    ),
    "source_cutoff_operation": frozenset(
        {"operation_id", "input_sha256", "source_prefix_sha256"}
    ),
    "semantic_schema_digest": frozenset({"path", "sha256"}),
    "strict_state_verification_input": frozenset(
        {
            "assertion_id",
            "logical_id",
            "authority_state",
            "reported_result",
            "effective_result",
            "check_eligibility",
        }
    ),
    "graph_edge": frozenset({"kind", "from_assertion_id", "to_assertion_id"}),
    "publication_freshness_anchor": frozenset(
        {
            "boot_id",
            "authority_snapshot_id",
            "sampled_wall_time",
            "sampled_boottime_ns",
            "snapshot_deadline_boottime_ns",
            "clock_review_ref",
        }
    ),
    "raw_evidence_snapshot": frozenset(
        {
            "snapshot_id",
            "lineage_id",
            "authority_seq",
            "authority_manifest_sha256",
            "semantic_contract_sha256",
            "state_basis",
            "verification_basis",
            "as_of",
            "expires_at",
        }
    ),
    "raw_evidence_result": frozenset(
        {
            "title",
            "document",
            "ledger_id",
            "citation_ref",
            "record_kind",
            "logical_id",
            "authority_state",
            "verification_state",
            "verification_result",
            "target_ledger_id",
            "supersedes_ledger_ids",
            "origin_assurance",
            "provenance_qualification",
            "provenance_basis",
            "check_eligibility",
            "state_sha256",
            "confidence_bps",
            "observed_at",
            "recorded_at",
            "decision_disposition_ref",
            "supersession_disposition_ref",
            "state_disposition_refs",
            "truncated",
            "domain",
            "site",
        }
    ),
    "error_object": frozenset({"code", "message"}),
    "launch_process_entry": frozenset(
        {
            "executable",
            "argv_template",
            "cwd",
            "environment",
            "inherited_fd_roles",
            "network_policy",
            "uid",
            "gid",
            "seccomp_filter_sha256",
        }
    ),
    "launch_mount": frozenset({"source_role", "destination", "mode", "max_bytes"}),
    "launch_endpoints": frozenset(
        {"gateway_port", "model_port", "model_api", "model_id"}
    ),
    "launch_processes_roles": frozenset(
        {"supervisor", "gateway", "agent", "strict_server", "model_worker"}
    ),
}


def schema_shape(schema: dict[str, Any]) -> tuple[frozenset[str], frozenset[str]]:
    """Return (properties, required) for a plain object schema (not oneOf)."""
    props = frozenset((schema.get("properties") or {}).keys())
    req = frozenset(schema.get("required") or [])
    return props, req
