"""Deterministic lifecycle event scripts for Gate C T5 cases (M6)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fixture_platform import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
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
STRICT_SECCOMP = "sha256:" + ("c" * 64)

# Closed role environment key sets (Architecture §6.5.6 / §4).
_FIXTURE_COMMON_ENV_TAIL = ("HOME", "PATH") + ("LANG", "LC_ALL", "TMPDIR")
GATEWAY_AGENT_ENV_KEYS = (
    "OPENCLAW_GATEWAY_TOKEN",
    "OPENCLAW_STATE_DIR",
    "OPENCLAW_CONFIG_PATH",
) + _FIXTURE_COMMON_ENV_TAIL + (
    "XDG_CACHE_HOME",
)
STRICT_SERVER_ENV_KEYS = (
    "CONVMEM_MCP_PROFILE",
    "CONVMEM_BOUND_READ_SCOPE_FILE",
    "CONVMEM_PROJECT_BINDING_REGISTRY_FILE",
    "CONVMEM_STRICT_CONFIG_FILE",
) + _FIXTURE_COMMON_ENV_TAIL
SUPERVISOR_ENV_KEYS = ("NOTIFY_SOCKET", "WATCHDOG_USEC")
MODEL_WORKER_ENV_KEYS = ("HOME", "PATH", "TMPDIR", "XDG_CACHE_HOME", "OMP_NUM_THREADS")


def independent_content_hash(obj: dict[str, Any], exclude: str) -> str:
    """Test-side self-hash — must not call production helpers."""

    body = {k: obj[k] for k in sorted(obj) if k != exclude}
    raw = json.dumps(
        body, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def independent_canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(
        obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _gateway_agent_env(*, state_dir: str = "/fixture/state/act-1") -> dict[str, str]:
    return {
        "OPENCLAW_GATEWAY_TOKEN": "0" * 64,
        "OPENCLAW_STATE_DIR": state_dir,
        "OPENCLAW_CONFIG_PATH": "/fixture/config/openclaw.json",
        "HOME": "/fixture/home",
        "PATH": "/runtime/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": "/fixture/tmp",
        "XDG_CACHE_HOME": "/fixture/cache",
    }


def _strict_server_env() -> dict[str, str]:
    return {
        "CONVMEM_MCP_PROFILE": "openclaw-strict",
        "CONVMEM_BOUND_READ_SCOPE_FILE": "/fixture/public/scope/bound.json",
        "CONVMEM_PROJECT_BINDING_REGISTRY_FILE": "/fixture/public/registry/bindings.json",
        "CONVMEM_STRICT_CONFIG_FILE": "/fixture/public/strict-config/config.json",
        "HOME": "/fixture/home",
        "PATH": "/runtime/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": "/fixture/tmp",
    }


def gateway_argv_template(*, port: int = 51000) -> list[str]:
    return [
        "/fixture/bin/node",
        "/fixture/bin/openclaw",
        "gateway",
        "run",
        "--bind",
        "loopback",
        "--port",
        str(port),
        *(
            "--auth|token|--tailscale|off|--ws-log|compact".split("|")
        ),
    ]


def agent_argv_template(*, activation_id: str = HEX_C) -> list[str]:
    return [
        "/fixture/bin/node",
        "/fixture/bin/openclaw",
        "agent",
        "--json",
        "--session-id",
        activation_id,
        "--timeout",
        "120",
        "--message",
        "TURN_TEXT",
    ]


def argv_digest(argv: list[str]) -> str:
    raw = json.dumps(
        argv, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def base_launch_policy(**overrides: Any) -> dict[str, Any]:
    activation_id = str(overrides.pop("_activation_id", HEX_C))
    port = 51000
    if "endpoints" in overrides and isinstance(overrides["endpoints"], dict):
        port = int(overrides["endpoints"].get("gateway_port", port))
    state_dir = "/fixture/state/act-1"
    ga_env = _gateway_agent_env(state_dir=state_dir)

    def proc(
        uid: int,
        exe: str,
        *,
        net: str = "none",
        argv: list[str] | None = None,
        environment: dict[str, str] | None = None,
        inherited_fd_roles: list[str] | None = None,
        seccomp: str | None = None,
        cwd: str = "/fixture/empty",
    ) -> dict[str, Any]:
        return {
            "executable": exe,
            "argv_template": list(argv) if argv is not None else [exe],
            "cwd": cwd,
            "environment": dict(environment or {}),
            "inherited_fd_roles": list(inherited_fd_roles or []),
            "network_policy": net,
            "uid": uid,
            "gid": uid,
            "seccomp_filter_sha256": seccomp,
        }

    p: dict[str, Any] = {
        "schema": "convmem.activation-launch-policy.v1",
        "runtime_distribution_sha256": PUB,
        "model_artifacts_sha256": PUB,
        "processes": {
            "supervisor": proc(
                0,
                "/fixture/bin/supervisor",
                net="none",
                argv=["/fixture/bin/supervisor"],
                environment={
                    "NOTIFY_SOCKET": "/fixture/notify",
                    "WATCHDOG_USEC": "1000000",
                },
                inherited_fd_roles=["supervisor_control", "lease", "notify"],
            ),
            "gateway": proc(
                1001,
                "/fixture/bin/node",
                net="activation_loopback",
                argv=gateway_argv_template(port=port),
                environment=ga_env,
                inherited_fd_roles=["stdout", "stderr"],
            ),
            "agent": proc(
                1001,
                "/fixture/bin/node",
                net="activation_loopback",
                argv=agent_argv_template(activation_id=activation_id),
                environment=ga_env,
                inherited_fd_roles=["stdin", "stdout", "stderr"],
            ),
            "strict_server": proc(
                1001,
                "/fixture/bin/strict_server",
                net="none",
                argv=[
                    *("/fixture/bin/setpriv", "--no-new-privs"),
                    *("--seccomp-filter", "/fixture/filter/strict.bpf"),
                    *("/fixture/bin/python", "-B", "-s"),
                    "/fixture/bin/strict_server",
                ],
                environment=_strict_server_env(),
                inherited_fd_roles=["stdin", "stdout", "stderr"],
                seccomp=STRICT_SECCOMP,
            ),
            "model_worker": proc(
                1001,
                "/fixture/bin/model-worker",
                net="activation_loopback",
                argv=["/fixture/bin/model-worker"],
                environment={
                    "HOME": "/fixture/home",
                    "PATH": "/runtime/bin",
                    "TMPDIR": "/fixture/tmp",
                    "XDG_CACHE_HOME": "/fixture/cache",
                    "OMP_NUM_THREADS": "1",
                },
                inherited_fd_roles=["stdout", "stderr"],
            ),
        },
        "read_only_mounts": [
            {
                "source_role": "runtime",
                "destination": "/runtime",
                "mode": "ro",
                "max_bytes": None,
            },
            {
                "source_role": "config",
                "destination": "/fixture/config",
                "mode": "ro",
                "max_bytes": None,
            },
            {
                "source_role": "model",
                "destination": "/fixture/model",
                "mode": "ro",
                "max_bytes": None,
            },
        ],
        "writable_mounts": [
            {
                "source_role": "state",
                "destination": "/fixture/state",
                "mode": "rw",
                "max_bytes": 536870912,
            },
            {
                "source_role": "temp",
                "destination": "/fixture/tmp",
                "mode": "rw",
                "max_bytes": 536870912,
            },
        ],
        "endpoints": {
            "gateway_port": port,
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
    if "policy_payload_sha256" not in overrides:
        p["policy_payload_sha256"] = independent_content_hash(p, "policy_payload_sha256")
    return p


def base_activation_manifest(**overrides: Any) -> dict[str, Any]:
    activation_id = str(overrides.get("activation_id", HEX_C))
    policy = base_launch_policy(_activation_id=activation_id)
    policy_hash = independent_content_hash(policy, "policy_payload_sha256")
    gw_argv = gateway_argv_template()
    ag_argv = agent_argv_template(activation_id=activation_id)
    m: dict[str, Any] = {
        "schema": "convmem.openclaw-activation.v2",
        "activation_id": activation_id,
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
        "launch_policy_sha256": policy_hash,
        "manager_policy_sha256": PUB,
        "control_protocol_version": "convmem.activation-control.v1",
        "release_protocol_version": "convmem.buffered-release.v1",
        "state_dir": "/fixture/state/act-1",
        "gateway_port": 51000,
        "gateway_argv_sha256": argv_digest(gw_argv),
        "agent_argv_sha256": argv_digest(ag_argv),
        "created_at": "2026-09-21T00:00:00Z",
        "max_monotonic_lifetime_seconds": 3600,
        "manifest_payload_sha256": PUB,
    }
    m.update(overrides)
    if "manifest_payload_sha256" not in overrides:
        m["manifest_payload_sha256"] = independent_content_hash(m, "manifest_payload_sha256")
    return m


def base_clock_review(**overrides: Any) -> dict[str, Any]:
    r: dict[str, Any] = {
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
    if "review_payload_sha256" not in overrides:
        r["review_payload_sha256"] = independent_content_hash(r, "review_payload_sha256")
    return r


def clock_review_inventory_bytes(review: dict[str, Any] | None = None) -> bytes:
    """Full canonical receipt bytes including self-hash (Architecture §6.5.6)."""

    r = dict(review or base_clock_review())
    if r.get("review_payload_sha256") == PUB or not str(r.get("review_payload_sha256", "")).startswith(
        "sha256:"
    ):
        r["review_payload_sha256"] = independent_content_hash(r, "review_payload_sha256")
    return independent_canonical(r)


def install_clock_review_inventory(
    platform: FixturePlatform, review: dict[str, Any] | None = None
) -> bytes:
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


def open_operator_session(
    controller: Any, platform: FixturePlatform, connection_id: str = "op1"
) -> str:
    """Authenticate a control connection through the same accounting path as framing."""

    platform.set_peer(connection_id, "operator")
    if connection_id not in platform._control_conns:  # pylint: disable=W0212  # fixture white-box: same accounting path as framing
        platform.open_control_connection(connection_id, "operator")
    if connection_id not in controller._open_sessions:  # pylint: disable=W0212  # fixture white-box: session accounting path
        controller.open_control_session(connection_id)
    return connection_id


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
    cid = open_operator_session(controller, platform, "retire-op")
    controller.handle_control(
        cid,
        revoke_request(request_id="f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0"),
    )
    assert controller.slots[slot_id].state == "REVOKING"
    controller.request_manager_stop(slot_id)
