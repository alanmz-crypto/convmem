"""Deterministic protocol_fixture specimens (Architecture §6.5.8).

Roles: activation, launch, manager, socket, connector, filter, runtime_image, model.
Filter/image/model payloads are inert; others carry closed schema-shaped payloads.
Not executable and not source-component digests.
"""

from __future__ import annotations

from typing import Any

ARTIFACT_KIND = "protocol_fixture"
ROLES = (
    "activation",
    "launch",
    "manager",
    "socket",
    "connector",
    "filter",
    "runtime_image",
    "model",
)


def wrap_specimen(role: str, payload: dict[str, Any]) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError(f"unknown_role:{role}")
    return {"artifact_kind": ARTIFACT_KIND, "role": role, "payload": payload}


def inert_payload(role: str) -> dict[str, Any]:
    if role not in {"filter", "runtime_image", "model"}:
        raise ValueError(f"inert_role_required:{role}")
    return {"schema": "convmem.inert-fixture.v1", "role": role}


def specimen_catalog() -> dict[str, dict[str, Any]]:
    """Fixed catalog of inert + minimal closed-shape specimens for validators."""
    sha = "sha256:" + ("a" * 64)
    hex32 = "b" * 32
    catalog: dict[str, dict[str, Any]] = {}
    for role in ("filter", "runtime_image", "model"):
        catalog[role] = wrap_specimen(role, inert_payload(role))
    catalog["socket"] = wrap_specimen(
        "socket",
        {
            "schema": "convmem.controller-socket-policy.v1",
            "socket_path": "/fixture/control.sock",
            "socket_mode": "0600",
            "owner_uid": 0,
            "permitted_peer_uid": 1000,
            "max_request_bytes": 131072,
            "max_response_bytes": 2097152,
            "policy_payload_sha256": sha,
        },
    )
    catalog["connector"] = wrap_specimen(
        "connector",
        {
            "schema": "convmem.openclaw-connector-launch.v2",
            "python_executable": "/runtime/bin/python",
            "python_executable_sha256": sha,
            "strict_server_path": "/src/openclaw_strict_server.py",
            "strict_server_tree_sha256": sha,
            "working_directory": "/fixture/empty",
            "scope_file": "/fixture/scope.json",
            "registry_file": "/fixture/registry.json",
            "strict_config_file": "/fixture/strict-config.json",
            "scope_sha256": sha,
            "registry_sha256": sha,
            "strict_config_sha256": sha,
            "service_home": "/fixture/home",
            "path_value": "/runtime/bin",
            "lang": "C.UTF-8",
            "lc_all": "C.UTF-8",
            "temp_directory": "/fixture/tmp",
            "setpriv_executable": "/runtime/bin/setpriv",
            "setpriv_sha256": sha,
            "seccomp_filter_file": "/runtime/filter.bpf",
            "seccomp_filter_sha256": sha,
            "runtime_distribution_sha256": sha,
            "launch_policy_sha256": sha,
            "manager_policy_sha256": sha,
            "launch_payload_sha256": sha,
        },
    )
    catalog["manager"] = wrap_specimen(
        "manager",
        {
            "schema": "convmem.activation-manager-policy.v1",
            "unit_bytes_b64": "W1VuaXRdCg==",
            "unit_sha256": sha,
            "controller_socket_policy_sha256": sha,
            "runtime_distribution_sha256": sha,
            "operator_uid": 1000,
            "controller_uid": 0,
            "supervisor_uid": 0,
            "runtime_uid": 1001,
            "kernel_release": "fixture",
            "systemd_version": "fixture",
            "capability_evidence_sha256": sha,
            "policy_payload_sha256": sha,
        },
    )
    catalog["launch"] = wrap_specimen(
        "launch",
        {
            "schema": "convmem.activation-launch-policy.v1",
            "runtime_distribution_sha256": sha,
            "model_artifacts_sha256": sha,
            "processes": {
                role: {
                    "executable": f"/runtime/bin/{role}",
                    "argv_template": [f"/runtime/bin/{role}"],
                    "cwd": "/fixture/empty",
                    "environment": {"HOME": "/fixture/home", "PATH": "/runtime/bin"},
                    "inherited_fd_roles": [],
                    "network_policy": "none" if role == "strict_server" else "activation_loopback",
                    "uid": 1001 if role != "supervisor" else 0,
                    "gid": 1001 if role != "supervisor" else 0,
                    "seccomp_filter_sha256": sha if role == "strict_server" else None,
                }
                for role in (
                    "supervisor",
                    "gateway",
                    "agent",
                    "strict_server",
                    "model_worker",
                )
            },
            "read_only_mounts": [
                {
                    "source_role": "runtime",
                    "destination": "/runtime",
                    "mode": "ro",
                    "max_bytes": None,
                }
            ],
            "writable_mounts": [
                {
                    "source_role": "state",
                    "destination": "/fixture/state",
                    "mode": "rw",
                    "max_bytes": 1048576,
                }
            ],
            "endpoints": {
                "gateway_port": 51000,
                "model_port": 51001,
                "model_api": "openai-completions",
                "model_id": "fixture-model",
            },
            "operator_uid": 1000,
            "controller_uid": 0,
            "supervisor_uid": 0,
            "runtime_uid": 1001,
            "manager_policy_sha256": sha,
            "policy_payload_sha256": sha,
        },
    )
    catalog["activation"] = wrap_specimen(
        "activation",
        {
            "schema": "convmem.openclaw-activation.v2",
            "activation_id": hex32,
            "slot_id": hex32,
            "lineage_id": hex32,
            "owner_digest": sha,
            "publication_sha256": sha,
            "scope_sha256": sha,
            "registry_sha256": sha,
            "strict_config_sha256": sha,
            "authority_manifest_sha256": sha,
            "projection_manifest_sha256": sha,
            "snapshot_id": "snap2_fixture",
            "as_of": "2026-09-21T00:00:00Z",
            "expires_at": "2026-09-22T00:00:00Z",
            "openclaw_version": "fixture",
            "openclaw_config_sha256": sha,
            "plugin_tree_sha256": sha,
            "connector_launch_sha256": sha,
            "strict_server_tree_sha256": sha,
            "supervisor_tree_sha256": sha,
            "controller_tree_sha256": sha,
            "runtime_distribution_sha256": sha,
            "model_artifacts_sha256": sha,
            "launch_policy_sha256": sha,
            "manager_policy_sha256": sha,
            "control_protocol_version": "convmem.activation-control.v1",
            "release_protocol_version": "convmem.buffered-release.v1",
            "state_dir": "/fixture/state",
            "gateway_port": 51000,
            "gateway_argv_sha256": sha,
            "agent_argv_sha256": sha,
            "created_at": "2026-09-21T00:00:00Z",
            "max_monotonic_lifetime_seconds": 3600,
            "manifest_payload_sha256": sha,
        },
    )
    return catalog
