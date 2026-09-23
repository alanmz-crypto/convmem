"""Deterministic lifecycle event scripts for Gate C T5 cases (M6)."""

from __future__ import annotations

import json
from typing import Any

from fixture_platform import (
    AGENT_SUCCESS_BYTES,
    FixturePlatform,
    LOGICAL_PEERS,
    encode_control_frame,
    try_decode_control_frame,
)

HEX_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
HEX_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
HEX_C = "cccccccccccccccccccccccccccccccc"
HEX_D = "dddddddddddddddddddddddddddddddd"
HEX_E = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
PUB = "sha256:" + ("a" * 64)
PUB_B = "sha256:" + ("b" * 64)


def base_activation_manifest(**overrides: Any) -> dict[str, Any]:
    m = {
        "schema": "convmem.openclaw-activation.v2",
        "activation_id": HEX_C,
        "slot_id": HEX_B,
        "lineage_id": HEX_A,
        "owner_digest": PUB,
        "publication_sha256": PUB,
        "scope_sha256": PUB,
        "registry_sha256": PUB,
        "strict_config_sha256": PUB,
        "authority_manifest_sha256": PUB,
        "projection_manifest_sha256": PUB,
        "snapshot_id": "snap-fixture-1",
        "as_of": "2026-09-21T00:00:00Z",
        "expires_at": "2026-09-22T00:00:00Z",
        "openclaw_version": "fixture",
        "openclaw_config_sha256": PUB,
        "plugin_tree_sha256": PUB,
        "connector_launch_sha256": PUB,
        "strict_server_tree_sha256": PUB,
        "supervisor_tree_sha256": PUB,
        "controller_tree_sha256": PUB,
        "runtime_distribution_sha256": PUB,
        "model_artifacts_sha256": PUB,
        "launch_policy_sha256": PUB,
        "manager_policy_sha256": PUB,
        "control_protocol_version": "convmem.activation-control.v1",
        "release_protocol_version": "convmem.buffered-release.v1",
        "state_dir": "/fixture/state/act-1",
        "gateway_port": 51000,
        "gateway_argv_sha256": PUB,
        "agent_argv_sha256": PUB,
        "created_at": "2026-09-21T00:00:00Z",
        "max_monotonic_lifetime_seconds": 3600,
        "manifest_payload_sha256": PUB,
    }
    m.update(overrides)
    return m


def base_launch_policy(**overrides: Any) -> dict[str, Any]:
    def proc(uid: int, exe: str, net: str = "none", argv: list[str] | None = None) -> dict[str, Any]:
        return {
            "executable": exe,
            "argv_template": list(argv) if argv is not None else [exe],
            "cwd": "/fixture/empty",
            "environment": {"HOME": "/fixture/home", "PATH": "/runtime/bin"},
            "inherited_fd_roles": [],
            "network_policy": net,
            "uid": uid,
            "gid": uid,
            "seccomp_filter_sha256": None,
        }

    p = {
        "schema": "convmem.activation-launch-policy.v1",
        "runtime_distribution_sha256": PUB,
        "model_artifacts_sha256": PUB,
        "processes": {
            "supervisor": proc(0, "/fixture/bin/supervisor"),
            "gateway": proc(1001, "/fixture/bin/gateway", "activation_loopback"),
            "agent": proc(
                1001,
                "/fixture/bin/agent",
                "activation_loopback",
                argv=["/fixture/bin/agent", "--message", "TURN_TEXT"],
            ),
            "strict_server": proc(1001, "/fixture/bin/strict_server"),
            "model_worker": {
                "executable": "/fixture/bin/model-worker",
                "argv_template": ["/fixture/bin/model-worker"],
                "cwd": "/fixture/empty",
                "environment": {"HOME": "/fixture/home", "PATH": "/runtime/bin"},
                "inherited_fd_roles": [],
                "network_policy": "activation_loopback",
                "uid": 1001,
                "gid": 1001,
                "seccomp_filter_sha256": None,
            },
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
        "manager_policy_sha256": PUB,
        "policy_payload_sha256": PUB,
    }
    p.update(overrides)
    return p


def base_clock_review(**overrides: Any) -> dict[str, Any]:
    r = {
        "schema": "convmem.clock-review.v1",
        "lineage_id": HEX_A,
        "authority_snapshot_id": "snap-fixture-1",
        "boot_id": "boot-fixture-0002",
        "expires_at": "2026-09-22T00:00:00Z",
        "reviewed_wall_time": "2026-09-21T12:00:00Z",
        "reviewer_uid": 1000,
        "review_payload_sha256": PUB,
    }
    r.update(overrides)
    return r


def clock_review_inventory_bytes(review: dict[str, Any] | None = None) -> bytes:
    """Canonical body excluding only review_payload_sha256 (parent self-hash rule)."""

    r = dict(review or base_clock_review())
    body = {k: r[k] for k in sorted(r) if k != "review_payload_sha256"}
    return json.dumps(
        body, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def install_clock_review_inventory(platform: FixturePlatform, review: dict[str, Any] | None = None) -> bytes:
    raw = clock_review_inventory_bytes(review)
    platform.install_operator_inventory_bytes(raw)
    return raw


def turn_request(
    *,
    request_id: str = HEX_A,
    slot_id: str = HEX_B,
    activation_id: str = HEX_C,
    turn_id: str = HEX_D,
    text: str = "fixture turn",
    publication: str = PUB,
) -> dict[str, Any]:
    return {
        "schema": "convmem.activation-control.v1",
        "op": "turn",
        "request_id": request_id,
        "slot_id": slot_id,
        "activation_id": activation_id,
        "turn_id": turn_id,
        "text": text,
        "expected_publication_sha256": publication,
    }


def status_request(**kw: Any) -> dict[str, Any]:
    return {
        "schema": "convmem.activation-control.v1",
        "op": "status",
        "request_id": kw.get("request_id", HEX_A),
        "slot_id": kw.get("slot_id", HEX_B),
        "activation_id": kw.get("activation_id", HEX_C),
    }


def cancel_request(**kw: Any) -> dict[str, Any]:
    return {
        "schema": "convmem.activation-control.v1",
        "op": "cancel",
        "request_id": kw.get("request_id", HEX_A),
        "slot_id": kw.get("slot_id", HEX_B),
        "activation_id": kw.get("activation_id", HEX_C),
        "turn_id": kw.get("turn_id", HEX_D),
    }


def revoke_request(*, reason: str = "operator", **kw: Any) -> dict[str, Any]:
    return {
        "schema": "convmem.activation-control.v1",
        "op": "revoke",
        "request_id": kw.get("request_id", HEX_A),
        "slot_id": kw.get("slot_id", HEX_B),
        "activation_id": kw.get("activation_id", HEX_C),
        "reason": reason,
    }


def script_peer_policy_ok(platform: FixturePlatform) -> None:
    for role, (uid, gid) in LOGICAL_PEERS.items():
        cid = f"conn-{role}"
        platform.set_peer(cid, role)
        got = platform.peer(cid)
        assert got == {"uid": uid, "gid": gid}


def script_partial_frame_discard(platform: FixturePlatform) -> tuple[bytes, str | None]:
    """Partial then complete frame; trailing bytes fail closed."""

    full = encode_control_frame(status_request())
    partial = full[:6]
    obj, rem, err = try_decode_control_frame(partial)
    assert obj is None and err is None and rem == partial
    obj2, rem2, err2 = try_decode_control_frame(full)
    assert obj2 is not None and err2 is None and rem2 == b""
    desync = full + b"\x00trailer"
    obj3, _rem3, err3 = try_decode_control_frame(desync)
    assert obj3 is None and err3 == "bad_frame"
    platform.trace.append({"op": "script_partial_frame_discard", "ok": True})
    return full, err3


def agent_success_b64() -> str:
    import base64

    return base64.b64encode(AGENT_SUCCESS_BYTES).decode("ascii")


def assert_agent_success_bytes(raw: bytes) -> None:
    assert raw == AGENT_SUCCESS_BYTES
    assert json.loads(raw.decode("utf-8"))["fixture"] == "protocol-only"


def _enter_revoking_for_retirement(controller: Any, slot_id: str = HEX_B) -> None:
    """Legitimate path to REVOKING + stop before attempt_retirement."""

    platform = controller.platform
    platform.set_peer("retire-op", "operator")
    controller.handle_control(
        "retire-op",
        revoke_request(request_id="f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0"),
    )
    assert controller.slots[slot_id].state == "REVOKING"
    controller.request_manager_stop(slot_id)
