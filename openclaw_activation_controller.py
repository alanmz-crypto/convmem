"""OpenClaw activation controller — peer/slot/manager/retirement core (M6/T5).

Production ``start`` / ``main`` refuse before any OS effect (Architecture §6.5.8).
Library cores are constructed with a test-owned FixturePlatform; this module never
imports ``tests/fixtures/openclaw_strict``.
"""
# pylint: disable=C0302  # preserved activation-controller component boundary


from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping, MutableMapping, Protocol, cast

RUNTIME_NOT_QUALIFIED = "runtime_not_qualified"
EX_CONFIG = 78

CONTROL_SCHEMA = "convmem.activation-control.v1"
RETIREMENT_SCHEMA = "convmem.activation-retirement.v1"
CLOCK_REVIEW_SCHEMA = "convmem.clock-review.v1"
ACTIVATION_SCHEMA = "convmem.openclaw-activation.v2"
LAUNCH_POLICY_SCHEMA = "convmem.activation-launch-policy.v1"

LOGICAL_UID = {
    "operator": 1000,
    "controller": 0,
    "supervisor": 0,
    "runtime": 1001,
}
LOGICAL_GID = dict(LOGICAL_UID)

MAX_REQUEST_FRAME = 131072
MAX_RESPONSE_FRAME = 2097152
CONTROL_IO_TIMEOUT_NS = 10_000_000_000
MAX_CONTROL_CONNECTIONS = 8

def _controller_revoke_reasons() -> frozenset[str]:
    """Build external revoke-reason set (tuple source — distinct from supervisor)."""

    return frozenset(
        (
            "operator",
            "publish",
            "scope_change",
            "expiry",
            "clock_anomaly",
            "integrity_failure",
            "disconnect",
            "shutdown",
        )
    )


REVOKE_REASONS = _controller_revoke_reasons()

# Internal terminal reasons only — never accepted on external revoke requests.
INTERNAL_TERMINAL_REASONS = frozenset({"capacity"})

TERMINAL_RECEIPT_REASONS = REVOKE_REASONS | INTERNAL_TERMINAL_REASONS

INVALID_REASONS = frozenset(
    {
        "not_active",
        "stale_publication",
        "bad_frame",
        "bad_arguments",
        "capacity",
        *REVOKE_REASONS,
    }
)

# Parent-fixed descriptor-role sets — policy cannot invent alternatives.
FIXED_FD_ROLES: dict[str, frozenset[str]] = {
    "supervisor": frozenset({"supervisor_control", "lease", "notify"}),
    "gateway": frozenset({"stdout", "stderr"}),
    "agent": frozenset({"stdin", "stdout", "stderr"}),
    "strict_server": frozenset({"stdin", "stdout", "stderr"}),
    "model_worker": frozenset({"stdout", "stderr"}),
}

STRICT_SERVER_ARGV_PREFIX = (
    "/fixture/bin/setpriv",
    "--no-new-privs",
    "--seccomp-filter",
    "/fixture/filter/strict.bpf",
    "/fixture/bin/python",
    "-B",
    "-s",
)

ACTIVATION_KEYS = (
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
)

LAUNCH_POLICY_KEYS = (
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
)

PROCESS_ROLES = ("supervisor", "gateway", "agent", "strict_server", "model_worker")
PROCESS_KEYS = (
    "executable",
    "argv_template",
    "cwd",
    "environment",
    "inherited_fd_roles",
    "network_policy",
    "uid",
    "gid",
    "seccomp_filter_sha256",
)
CLOCK_REVIEW_KEYS = (
    "schema",
    "lineage_id",
    "authority_snapshot_id",
    "boot_id",
    "expires_at",
    "reviewed_wall_time",
    "reviewer_uid",
    "review_payload_sha256",
)

def _frozen_env_keys(*names: str) -> frozenset[str]:
    """Build closed env-key sets from an explicit name tuple (R0801-safe shape)."""

    return frozenset(names)


GATEWAY_AGENT_ENV_KEYS = _frozen_env_keys(
    "OPENCLAW_GATEWAY_TOKEN",
    "OPENCLAW_STATE_DIR",
    "OPENCLAW_CONFIG_PATH",
    "HOME",
    "PATH",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "XDG_CACHE_HOME",
)
STRICT_SERVER_ENV_KEYS = _frozen_env_keys(
    "CONVMEM_MCP_PROFILE",
    "CONVMEM_BOUND_READ_SCOPE_FILE",
    "CONVMEM_PROJECT_BINDING_REGISTRY_FILE",
    "CONVMEM_STRICT_CONFIG_FILE",
    "HOME",
    "PATH",
    "LANG",
    "LC_ALL",
    "TMPDIR",
)
SUPERVISOR_ENV_KEYS = _frozen_env_keys("NOTIFY_SOCKET", "WATCHDOG_USEC")
MODEL_WORKER_ENV_KEYS = _frozen_env_keys(
    "HOME", "PATH", "TMPDIR", "XDG_CACHE_HOME", "OMP_NUM_THREADS"
)
MOUNT_SOURCE_ROLES = frozenset(
    {"runtime", "public_evidence", "config", "model", "control", "state", "temp"}
)
RO_SOURCE_ROLES = frozenset(
    {"runtime", "public_evidence", "config", "model", "control"}
)
RW_SOURCE_ROLES = frozenset({"state", "temp"})
MOUNT_KEYS = frozenset({"source_role", "destination", "mode", "max_bytes"})
ENDPOINT_KEYS = frozenset({"gateway_port", "model_port", "model_api", "model_id"})
MAX_WRITABLE_BYTES = 1_073_741_824
EMPTY_CWD = "/fixture/empty"
GATEWAY_ARGV_FIXED = (
    "gateway",
    "run",
    "--bind",
    "loopback",
    "--auth",
    "token",
    "--tailscale",
    "off",
    "--ws-log",
    "compact",
)
AGENT_ARGV_FIXED_PREFIX = ("agent", "--json", "--session-id")
AGENT_ARGV_FIXED_MID = ("--timeout", "120", "--message", "TURN_TEXT")

_LIFECYCLE_REQUIRED_FALSE = (
    "native_memory",
    "automatic_memory_flush",
    "heartbeat",
    "acp",
    "subagents",
    "skills",
    "hooks",
    "discovery",
    "channels",
    "runtime_tools",
    "filesystem_tools",
    "browser_tools",
    "write_tools",
    "automatic_transcript_capture",
)

TURN_KEYS = frozenset(
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
)
CANCEL_KEYS = frozenset({"schema", "op", "request_id", "slot_id", "activation_id", "turn_id"})
STATUS_KEYS = frozenset({"schema", "op", "request_id", "slot_id", "activation_id"})
REVOKE_KEYS = frozenset({"schema", "op", "request_id", "slot_id", "activation_id", "reason"})



def _port_map_get(mapping: object, key: str) -> Any:
    """Read injected-port mapping field; Protocol ellipsis makes value look unsubscriptable."""
    # pylint: disable=E1136  # runtime mapping from FixturePlatformPort; stub body is ellipsis
    return cast(Mapping[str, Any], mapping)[key]

class FixturePlatformPort(Protocol):
    """Duck-typed §6.5.8 port — supplied by the test caller."""

    def sample_clock(self) -> dict[str, Any]: ...

    def peer(self, connection_id: str) -> dict[str, int]: ...

    def access(self, role: str, path: str, operation: str) -> bool: ...

    def spawn(
        self,
        role: str,
        argv: list[str],
        env: dict[str, str],
        cwd: str,
        fd_roles: dict[str, Any],
    ) -> str: ...

    def next_event(self, handle: str) -> dict[str, Any]: ...

    def manager_start(self, slot_id: str, activation_id: str) -> dict[str, str]: ...

    def manager_stop(self, invocation_id: str) -> dict[str, Any]: ...

    def manager_observe(self, invocation_id: str) -> dict[str, Any]: ...


def refuse_runtime_not_qualified() -> None:
    """Refuse production entry before any OS effect (Architecture §6.5.8)."""

    print(RUNTIME_NOT_QUALIFIED, file=sys.stderr)
    raise SystemExit(EX_CONFIG)


def start(*_args: Any, **_kwargs: Any) -> None:
    """Production start entry — always refuses."""

    refuse_runtime_not_qualified()


def main(argv: list[str] | None = None) -> int:
    # pylint: disable=W0613  # public CLI argv retained for interface parity
    """Production main entry — always refuses; argv unused by design."""

    refuse_runtime_not_qualified()
    return EX_CONFIG


def _canonical(obj: Mapping[str, Any]) -> bytes:
    return json.dumps(
        obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_labeled(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _content_hash(obj: Mapping[str, Any], exclude: str) -> str:
    body = {k: obj[k] for k in sorted(obj) if k != exclude}
    return _sha256_labeled(_canonical(body))


def _hex32(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 32 and all(
        c in "0123456789abcdef" for c in value
    )


def _sha_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(c in "0123456789abcdef" for c in value[7:])
    )


def _require_int(value: Any, err: str) -> int:
    """Exact integer type identity — reject bool and all int subclasses."""

    # pylint: disable=C0123  # exact type identity; not isinstance/__class__
    if type(value) is not int:
        raise ValueError(err)
    return value


def _days_in_month(year: int, month: int) -> int:
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    if month in (4, 6, 9, 11):
        return 30
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    return 29 if leap else 28



def _wall_separators_ok(wall: str) -> bool:
    """Canonical wall-time separators at fixed offsets."""

    expected = ((4, "-"), (7, "-"), (10, "T"), (13, ":"), (16, ":"), (19, "Z"))
    return all(wall[idx] == ch for idx, ch in expected)


def _parse_wall(wall: str) -> int:
    """Parse canonical ``YYYY-MM-DDTHH:MM:SSZ`` to epoch seconds (integer, no float)."""

    if not isinstance(wall, str) or len(wall) != 20:
        raise ValueError("bad_wall_time")
    if not _wall_separators_ok(wall):
        raise ValueError("bad_wall_time")
    for idx, ch in enumerate(wall):
        if idx in (4, 7, 10, 13, 16, 19):
            continue
        if ch not in "0123456789":
            raise ValueError("bad_wall_time")
    year = int(wall[0:4])
    month = int(wall[5:7])
    day = int(wall[8:10])
    hour = int(wall[11:13])
    minute = int(wall[14:16])
    second = int(wall[17:19])
    if not 1 <= month <= 12:
        raise ValueError("bad_wall_time")
    if not 1 <= day <= _days_in_month(year, month):
        raise ValueError("bad_wall_time")
    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
        raise ValueError("bad_wall_time")
    y = year
    m = month
    if m <= 2:
        y -= 1
        m += 12
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m - 3) + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    return days * 86400 + hour * 3600 + minute * 60 + second


def _validate_state_dir(path: Any) -> str:
    """Require a proper path-component child of ``/fixture/state`` (no escapes)."""

    if not isinstance(path, str):
        raise ValueError("bad_state_dir")
    prefix = "/fixture/state/"
    if not path.startswith(prefix):
        raise ValueError("bad_state_dir")
    if "//" in path or "/./" in path or "/../" in path:
        raise ValueError("bad_state_dir")
    if path.endswith("/.") or path.endswith("/.."):
        raise ValueError("bad_state_dir")
    rest = path[len(prefix) :]
    if not rest or rest.startswith("/") or rest.endswith("/"):
        raise ValueError("bad_state_dir")
    for part in rest.split("/"):
        if part in ("", ".", ".."):
            raise ValueError("bad_state_dir")
        if any(c in part for c in ("\\", "\x00")):
            raise ValueError("bad_state_dir")
    return path


def _frozen_map(obj: Mapping[str, Any]) -> MappingProxyType[str, Any]:
    return MappingProxyType(dict(obj))


def lifecycle_config_core(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate closed lifecycle disables; return normalized core claims."""

    cfg = dict(config or {})
    out: dict[str, Any] = {}
    for key in _LIFECYCLE_REQUIRED_FALSE:
        val = cfg.get(key, False)
        if val is not False:
            raise ValueError(f"lifecycle_not_disabled:{key}")
        out[key] = False
    out["provider_fallback"] = False
    if cfg.get("provider_fallback", False) is not False:
        raise ValueError("lifecycle_not_disabled:provider_fallback")
    return out


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Assemble object map while rejecting duplicate JSON keys."""

    built: dict[str, Any] = {}
    for name, item in pairs:
        if name in built:
            raise ValueError("duplicate_key")
        built[name] = item
    return built


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite:{value}")


def decode_framed_request(buf: bytes) -> tuple[dict[str, Any] | None, bytes, str | None]:
    """Four-byte BE length + canonical UTF-8 JSON; partial stays partial."""

    if len(buf) < 4:
        return None, buf, None
    (length,) = struct.unpack(">I", buf[:4])
    if length > MAX_REQUEST_FRAME:
        return None, b"", "bad_frame"
    if len(buf) < 4 + length:
        return None, buf, None
    raw = buf[4 : 4 + length]
    rest = buf[4 + length :]
    if rest:
        return None, b"", "bad_frame"
    try:
        text = raw.decode("utf-8")
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in text):
            raise ValueError("surrogate")
        obj = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None, b"", "bad_frame"
    if not isinstance(obj, dict):
        return None, b"", "bad_frame"
    # Reject whitespace / key-order / escape alternatives — exact canonical bytes.
    if _canonical(obj) != raw:
        return None, b"", "bad_frame"
    return obj, b"", None


def encode_framed_response(obj: Mapping[str, Any]) -> bytes:
    body = _canonical(obj)
    if len(body) > MAX_RESPONSE_FRAME:
        raise ValueError("response_frame_too_large")
    return struct.pack(">I", len(body)) + body


def _argv_digest(argv: list[str]) -> str:
    return _sha256_labeled(
        json.dumps(
            argv, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    )


def validate_control_request(request: Mapping[str, Any]) -> None:
    """Closed op variants/keys/types; no coercion of non-string text."""

    if request.get("schema") != CONTROL_SCHEMA:
        raise ValueError("bad_arguments")
    op = request.get("op")
    if op not in ("turn", "cancel", "status", "revoke"):
        raise ValueError("bad_arguments")
    keys = set(request.keys())
    if op == "turn":
        if keys != TURN_KEYS:
            raise ValueError("bad_arguments")
        if not isinstance(request["text"], str):
            raise ValueError("bad_arguments")
        if not _hex32(request["turn_id"]):
            raise ValueError("bad_arguments")
        if not _sha_digest(request["expected_publication_sha256"]):
            raise ValueError("bad_arguments")
    elif op == "cancel":
        if keys != CANCEL_KEYS:
            raise ValueError("bad_arguments")
        if not _hex32(request["turn_id"]):
            raise ValueError("bad_arguments")
    elif op == "status":
        if keys != STATUS_KEYS:
            raise ValueError("bad_arguments")
    elif op == "revoke":
        if keys != REVOKE_KEYS:
            raise ValueError("bad_arguments")
        if request["reason"] not in REVOKE_REASONS:
            raise ValueError("bad_arguments")
    for req_key in ("request_id", "slot_id", "activation_id"):
        if not _hex32(request.get(req_key)):
            raise ValueError("bad_arguments")


def validate_activation_manifest(
    manifest: Mapping[str, Any],
    *,
    slot_id: str,
    lineage_id: str,
    authority_head: str,
    expires_at: str,
    capability_digests: Mapping[str, str] | None = None,
    known_state_dirs: set[str] | None = None,
    launch_policy: Mapping[str, Any] | None = None,
) -> str:
    """Closed key set/types/versions/self-hash; return verified content hash."""

    if set(manifest.keys()) != set(ACTIVATION_KEYS):
        raise ValueError("activation_key_set")
    if manifest["schema"] != ACTIVATION_SCHEMA:
        raise ValueError("bad_activation_schema")
    if manifest["control_protocol_version"] != CONTROL_SCHEMA:
        raise ValueError("bad_control_protocol_version")
    if manifest["release_protocol_version"] != "convmem.buffered-release.v1":
        raise ValueError("bad_release_protocol_version")
    for key in ("activation_id", "slot_id", "lineage_id"):
        if not _hex32(manifest[key]):
            raise ValueError(f"bad_{key}")
    if manifest["slot_id"] != slot_id or manifest["lineage_id"] != lineage_id:
        raise ValueError("slot_lineage_drift")
    if manifest["expires_at"] != expires_at:
        raise ValueError("expires_drift")
    for key in ACTIVATION_KEYS:
        if key.endswith("_sha256") or key == "owner_digest":
            if not _sha_digest(manifest[key]):
                raise ValueError(f"bad_digest:{key}")
    if not isinstance(manifest["snapshot_id"], str) or not manifest["snapshot_id"]:
        raise ValueError("bad_snapshot_id")
    if not isinstance(manifest["openclaw_version"], str):
        raise ValueError("bad_openclaw_version")
    for wall_key in ("as_of", "expires_at", "created_at"):
        if not isinstance(manifest[wall_key], str):
            raise ValueError(f"bad_{wall_key}")
        _parse_wall(str(manifest[wall_key]))
    _validate_state_dir(manifest["state_dir"])
    if known_state_dirs is not None and manifest["state_dir"] in known_state_dirs:
        raise ValueError("state_dir_reuse")
    gw_port = _require_int(manifest["gateway_port"], "bad_gateway_port")
    if not 49152 <= gw_port <= 65535:
        raise ValueError("bad_gateway_port")
    max_life = _require_int(manifest["max_monotonic_lifetime_seconds"], "bad_max_lifetime")
    if max_life < 1 or max_life > 86400:
        raise ValueError("bad_max_lifetime")
    # Self-hash is mandatory — capability digests cannot excuse a wrong hash.
    content = _content_hash(manifest, "manifest_payload_sha256")
    if manifest["manifest_payload_sha256"] != content:
        raise ValueError("manifest_self_hash")
    if capability_digests:
        for name, digest in capability_digests.items():
            digest_key = {
                "publication": "publication_sha256",
                "launch_policy": "launch_policy_sha256",
                "manager_policy": "manager_policy_sha256",
                "runtime_distribution": "runtime_distribution_sha256",
                "model_artifacts": "model_artifacts_sha256",
                "activation_manifest": "manifest_payload_sha256",
            }.get(name)
            if digest_key and manifest.get(digest_key) != digest:
                raise ValueError(f"cross_digest:{name}")
    if authority_head and manifest.get("publication_sha256") != authority_head:
        raise ValueError("head_drift")
    if launch_policy is not None:
        _cross_check_manifest_launch_policy(manifest, launch_policy)
    return content


def _cross_check_manifest_launch_policy(
    manifest: Mapping[str, Any], launch_policy: Mapping[str, Any]
) -> None:
    """Verify activation manifest digests/ports against a launch policy."""

    policy_hash = _content_hash(launch_policy, "policy_payload_sha256")
    if manifest["launch_policy_sha256"] != policy_hash:
        raise ValueError("launch_policy_digest_drift")
    if manifest["runtime_distribution_sha256"] != launch_policy["runtime_distribution_sha256"]:
        raise ValueError("runtime_distribution_drift")
    if manifest["model_artifacts_sha256"] != launch_policy["model_artifacts_sha256"]:
        raise ValueError("model_artifacts_drift")
    if manifest["manager_policy_sha256"] != launch_policy["manager_policy_sha256"]:
        raise ValueError("manager_policy_drift")
    endpoints = launch_policy["endpoints"]
    if int(manifest["gateway_port"]) != int(endpoints["gateway_port"]):
        raise ValueError("gateway_port_drift")
    gw = launch_policy["processes"]["gateway"]["argv_template"]
    ag = launch_policy["processes"]["agent"]["argv_template"]
    if manifest["gateway_argv_sha256"] != _argv_digest(list(gw)):
        raise ValueError("gateway_argv_digest_drift")
    if manifest["agent_argv_sha256"] != _argv_digest(list(ag)):
        raise ValueError("agent_argv_digest_drift")


def _validate_mount_list(entries: Any, *, writable: bool) -> int:
    if not isinstance(entries, list):
        raise ValueError("bad_mounts")
    total = 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry.keys()) != MOUNT_KEYS:
            raise ValueError("mount_keys")
        role = entry["source_role"]
        if role not in MOUNT_SOURCE_ROLES:
            raise ValueError("mount_source_role")
        if writable:
            if entry["mode"] != "rw" or role not in RW_SOURCE_ROLES:
                raise ValueError("writable_mount_mode")
            mb = entry["max_bytes"]
            mb_i = _require_int(mb, "writable_max_bytes")
            if mb_i < 1:
                raise ValueError("writable_max_bytes")
            total += mb_i
        else:
            if entry["mode"] != "ro" or role not in RO_SOURCE_ROLES:
                raise ValueError("readonly_mount_mode")
            if entry["max_bytes"] is not None:
                raise ValueError("readonly_max_bytes")
        if not isinstance(entry["destination"], str) or not entry["destination"].startswith("/"):
            raise ValueError("mount_destination")
    return total


def _validate_gateway_argv(argv: list[str], *, gateway_port: int) -> None:
    if len(argv) != 14:
        raise ValueError("gateway_argv_structure")
    if not argv[0].startswith("/") or not argv[1].startswith("/"):
        raise ValueError("gateway_argv_paths")
    if argv[2:6] != ["gateway", "run", "--bind", "loopback"]:
        raise ValueError("gateway_argv_structure")
    if argv[6] != "--port" or argv[7] != str(gateway_port):
        raise ValueError("gateway_argv_port")
    if argv[8:] != ["--auth", "token", "--tailscale", "off", "--ws-log", "compact"]:
        raise ValueError("gateway_argv_structure")


def _validate_agent_argv(argv: list[str]) -> None:
    if len(argv) != 10:
        raise ValueError("agent_argv_structure")
    if not argv[0].startswith("/") or not argv[1].startswith("/"):
        raise ValueError("agent_argv_paths")
    if argv[2:5] != ["agent", "--json", "--session-id"]:
        raise ValueError("agent_argv_structure")
    if not _hex32(argv[5]):
        raise ValueError("agent_argv_activation_id")
    if argv[6:] != ["--timeout", "120", "--message", "TURN_TEXT"]:
        raise ValueError("agent_argv_structure")
    if sum(1 for p in argv if p == "TURN_TEXT") != 1:
        raise ValueError("turn_text_count")


def _validate_strict_server_argv(argv: list[str], *, executable: str) -> None:
    if len(argv) != 8:
        raise ValueError("strict_server_argv_structure")
    if tuple(argv[:7]) != STRICT_SERVER_ARGV_PREFIX:
        raise ValueError("strict_server_setpriv")
    if argv[7] != executable:
        raise ValueError("strict_server_executable_mismatch")



def _validate_launch_process_env(role: str, env: Mapping[str, Any]) -> None:
    """Closed environment key/value checks for one launch-policy process role."""

    if not isinstance(env, dict) or any(
        not isinstance(k, str) or not isinstance(v, str) for k, v in env.items()
    ):
        raise ValueError(f"bad_env:{role}")
    env_keys = frozenset(env.keys())
    if role in ("gateway", "agent"):
        if env_keys != GATEWAY_AGENT_ENV_KEYS:
            raise ValueError(f"env_keys:{role}")
    elif role == "strict_server":
        if env_keys != STRICT_SERVER_ENV_KEYS:
            raise ValueError(f"env_keys:{role}")
        if env.get("CONVMEM_MCP_PROFILE") != "openclaw-strict":
            raise ValueError("strict_profile")
    elif role == "supervisor":
        if env_keys != SUPERVISOR_ENV_KEYS:
            raise ValueError(f"env_keys:{role}")
    elif role == "model_worker":
        if env_keys != MODEL_WORKER_ENV_KEYS:
            raise ValueError(f"env_keys:{role}")


def _validate_launch_process(
    role: str, proc: Mapping[str, Any], *, gateway_port: int
) -> None:
    """Validate one process entry inside a launch policy."""

    if set(proc.keys()) != set(PROCESS_KEYS):
        raise ValueError(f"process_keys:{role}")
    if not isinstance(proc["executable"], str) or not proc["executable"].startswith("/"):
        raise ValueError(f"bad_executable:{role}")
    if not isinstance(proc["argv_template"], list) or not proc["argv_template"]:
        raise ValueError(f"bad_argv:{role}")
    if not all(isinstance(x, str) for x in proc["argv_template"]):
        raise ValueError(f"bad_argv_types:{role}")
    argv = list(proc["argv_template"])
    if role == "strict_server":
        _validate_strict_server_argv(argv, executable=str(proc["executable"]))
    elif argv[0] != proc["executable"]:
        raise ValueError(f"executable_mismatch:{role}")
    if role in ("gateway", "agent") and proc["cwd"] != EMPTY_CWD:
        raise ValueError(f"bad_cwd:{role}")
    if not isinstance(proc["cwd"], str) or not proc["cwd"].startswith("/"):
        raise ValueError(f"bad_cwd:{role}")
    _validate_launch_process_env(role, proc["environment"])
    if not isinstance(proc["inherited_fd_roles"], list) or not all(
        isinstance(x, str) for x in proc["inherited_fd_roles"]
    ):
        raise ValueError(f"bad_fd_roles:{role}")
    if frozenset(proc["inherited_fd_roles"]) != FIXED_FD_ROLES[role]:
        raise ValueError(f"fd_roles_fixed:{role}")
    if len(proc["inherited_fd_roles"]) != len(FIXED_FD_ROLES[role]):
        raise ValueError(f"fd_roles_fixed:{role}")
    if proc["network_policy"] not in ("activation_loopback", "none"):
        raise ValueError(f"bad_network:{role}")
    if role == "strict_server" and proc["network_policy"] != "none":
        raise ValueError("strict_server_network")
    uid = _require_int(proc["uid"], f"uid_gid_types:{role}")
    gid = _require_int(proc["gid"], f"uid_gid_types:{role}")
    if uid != gid:
        raise ValueError(f"uid_gid:{role}")
    expected = 0 if role == "supervisor" else LOGICAL_UID["runtime"]
    if uid != expected:
        raise ValueError(f"role_uid:{role}")
    seccomp = proc["seccomp_filter_sha256"]
    if role == "strict_server":
        if not _sha_digest(seccomp):
            raise ValueError("strict_server_seccomp")
    elif seccomp is not None:
        raise ValueError(f"seccomp_must_be_null:{role}")
    turn_count = sum(1 for part in argv if part == "TURN_TEXT")
    if role == "agent":
        if turn_count != 1:
            raise ValueError("turn_text_count")
        _validate_agent_argv(argv)
    else:
        if turn_count != 0:
            raise ValueError("turn_text_role")
    if role == "gateway":
        _validate_gateway_argv(argv, gateway_port=gateway_port)
    if role == "model_worker" and argv != ["/fixture/bin/model-worker"]:
        raise ValueError("model_worker_argv")
    if role in ("gateway", "agent", "strict_server", "model_worker"):
        forbidden = {"control", "notify", "lease", "operator_control", "supervisor_control"}
        if forbidden.intersection(proc["inherited_fd_roles"]):
            raise ValueError(f"runtime_fd_forbidden:{role}")


def validate_launch_policy(
    policy: Mapping[str, Any],
    *,
    capability_digests: Mapping[str, str] | None = None,
) -> str:
    if set(policy.keys()) != set(LAUNCH_POLICY_KEYS):
        raise ValueError("launch_policy_key_set")
    if policy["schema"] != LAUNCH_POLICY_SCHEMA:
        raise ValueError("bad_launch_schema")
    for digest_key in (
        "runtime_distribution_sha256",
        "model_artifacts_sha256",
        "manager_policy_sha256",
        "policy_payload_sha256",
    ):
        if not _sha_digest(policy[digest_key]):
            raise ValueError(f"bad_digest:{digest_key}")
    for role_key, expected_uid in (
        ("operator_uid", LOGICAL_UID["operator"]),
        ("controller_uid", LOGICAL_UID["controller"]),
        ("supervisor_uid", LOGICAL_UID["supervisor"]),
        ("runtime_uid", LOGICAL_UID["runtime"]),
    ):
        uid_val = _require_int(policy.get(role_key), f"bad_{role_key}")
        if uid_val != expected_uid:
            raise ValueError(f"bad_{role_key}")
    processes = policy["processes"]
    if not isinstance(processes, dict) or set(processes.keys()) != set(PROCESS_ROLES):
        raise ValueError("bad_processes")
    endpoints = policy["endpoints"]
    if not isinstance(endpoints, dict) or set(endpoints.keys()) != ENDPOINT_KEYS:
        raise ValueError("bad_endpoints")
    gw_port = _require_int(endpoints["gateway_port"], "bad_endpoint_ports")
    model_port = _require_int(endpoints["model_port"], "bad_endpoint_ports")
    if not (49152 <= gw_port <= 65535 and 49152 <= model_port <= 65535):
        raise ValueError("bad_endpoint_ports")
    if gw_port == model_port:
        raise ValueError("endpoint_ports_not_distinct")
    if endpoints["model_api"] != "openai-completions":
        raise ValueError("bad_model_api")
    if not isinstance(endpoints["model_id"], str) or not endpoints["model_id"]:
        raise ValueError("bad_model_id")

    for role in PROCESS_ROLES:
        _validate_launch_process(role, processes[role], gateway_port=gw_port)

    ro_total = _validate_mount_list(policy["read_only_mounts"], writable=False)
    _ = ro_total
    writable_total = _validate_mount_list(policy["writable_mounts"], writable=True)
    if writable_total > MAX_WRITABLE_BYTES:
        raise ValueError("writable_ceiling")

    content = _content_hash(policy, "policy_payload_sha256")
    if policy["policy_payload_sha256"] != content:
        raise ValueError("launch_policy_self_hash")
    if capability_digests and "launch_policy" in capability_digests:
        if capability_digests["launch_policy"] != content:
            raise ValueError("launch_policy_capability_digest")
    return content


@dataclass
class FreshnessAnchor:
    boot_id: str
    authority_snapshot_id: str
    sampled_wall_time: str
    sampled_boottime_ns: int
    snapshot_deadline_boottime_ns: int
    clock_review_ref: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "boot_id": self.boot_id,
            "authority_snapshot_id": self.authority_snapshot_id,
            "sampled_wall_time": self.sampled_wall_time,
            "sampled_boottime_ns": self.sampled_boottime_ns,
            "snapshot_deadline_boottime_ns": self.snapshot_deadline_boottime_ns,
            "clock_review_ref": self.clock_review_ref,
        }


@dataclass(frozen=True)
# pylint: disable=R0902  # attributes mirror sealed activation record fields
class SealedActivationRecord:
    """Immutable sealed predecessor — SEALED has no outgoing transition."""

    activation_id: str
    activation_manifest: Mapping[str, Any]
    publication_sha256: str | None
    manager_boot_id: str | None
    unit_invocation_id: str | None
    containment_id: str | None
    terminal_reason: str | None
    retirement_receipt: Mapping[str, Any]
    verified_manifest_content_sha256: str
    state: str = "SEALED"

    def __post_init__(self) -> None:
        if self.state != "SEALED":
            raise ValueError("sealed_record_state")
        if not isinstance(self.activation_manifest, MappingProxyType):
            object.__setattr__(
                self, "activation_manifest", _frozen_map(self.activation_manifest)
            )
        if not isinstance(self.retirement_receipt, MappingProxyType):
            object.__setattr__(
                self, "retirement_receipt", _frozen_map(self.retirement_receipt)
            )


@dataclass
# pylint: disable=R0902  # attributes mirror slot lifecycle state machine fields
class SlotState:
    slot_id: str
    lineage_id: str
    state: str = "NEW"
    activation_id: str | None = None
    activation_manifest: Mapping[str, Any] | None = None
    verified_manifest_content_sha256: str | None = None
    publication_sha256: str | None = None
    manager_boot_id: str | None = None
    unit_invocation_id: str | None = None
    containment_id: str | None = None
    stop_requested: bool = False
    freshness_anchor: FreshnessAnchor | None = None
    authority_head: str | None = None
    expires_at: str | None = None
    lease_deadline_boottime_ns: int | None = None
    terminal_reason: str | None = None
    retirement_receipt: Mapping[str, Any] | None = None
    quarantine_reason: str | None = None
    wall_offset_lower_bound: int | None = None
    last_wall_s: int | None = None
    sealed_record: SealedActivationRecord | None = None
    sealed_history: list[SealedActivationRecord] = field(default_factory=list)
    used_state_dirs: set[str] = field(default_factory=set)
    persisted: dict[str, Any] = field(default_factory=dict)


@dataclass
# pylint: disable=R0902  # attributes mirror controller session/slot bookkeeping fields
class ControllerCore:
    """Stable-slot lifecycle, peer policy, lock order, retirement/quarantine."""

    platform: FixturePlatformPort
    supervisor: Any
    slots: MutableMapping[str, SlotState] = field(default_factory=dict)
    _slot_transition_held: bool = False
    _lineage_exclusive_held: bool = False
    _open_sessions: set[str] = field(default_factory=set)
    # pylint: disable=C0103  # public capacity attribute name is part of controller interface
    MAX_CONTROL_CONNECTIONS: int = MAX_CONTROL_CONNECTIONS
    _inbound_bufs: dict[str, bytearray] = field(default_factory=dict)
    _conn_activity_ns: dict[str, int] = field(default_factory=dict)
    _conn_send_started_ns: dict[str, int] = field(default_factory=dict)
    _pending_outbound: dict[str, bytes] = field(default_factory=dict)

    @property
    def _active_control_connections(self) -> int:
        return len(self._open_sessions)

    def enroll_slot(
        self,
        slot_id: str,
        lineage_id: str,
        *,
        authority_head: str,
        expires_at: str,
    ) -> SlotState:
        if slot_id in self.slots:
            raise ValueError("slot_already_enrolled")
        if not _hex32(slot_id) or not _hex32(lineage_id):
            raise ValueError("bad_slot_id")
        st = SlotState(
            slot_id=slot_id,
            lineage_id=lineage_id,
            authority_head=authority_head,
            expires_at=expires_at,
            state="NEW",
        )
        self.slots[slot_id] = st
        st.persisted = {
            "slot_id": slot_id,
            "lineage_id": lineage_id,
            "authority_head": authority_head,
            "expires_at": expires_at,
            "state": "NEW",
        }
        return st

    def _acquire_slot_transition(self) -> None:
        if self._slot_transition_held:
            raise ValueError("slot_transition_reentry")
        self._slot_transition_held = True

    def _release_slot_transition(self) -> None:
        self._slot_transition_held = False

    def _acquire_lineage_exclusive(self) -> None:
        if self._slot_transition_held:
            raise ValueError("lock_order_violation:lineage_under_slot")
        if self._lineage_exclusive_held:
            raise ValueError("lineage_exclusive_reentry")
        self._lineage_exclusive_held = True

    def _release_lineage_exclusive(self) -> None:
        self._lineage_exclusive_held = False

    def validate_peer(
        self, connection_id: str, *, expected_role: str = "operator"
    ) -> dict[str, int]:
        # Protocol stub has ellipsis body; cast preserves injected-port return contract.
        creds = cast(dict[str, int], self.platform.peer(connection_id))
        expected_uid = LOGICAL_UID[expected_role]
        expected_gid = LOGICAL_GID[expected_role]
        if creds.get("uid") != expected_uid or creds.get("gid") != expected_gid:
            raise ValueError("peer_uid_mismatch")
        return creds

    def check_access(self, role: str, path: str, operation: str) -> None:
        if not self.platform.access(role, path, operation):
            raise ValueError(f"access_denied:{role}:{path}:{operation}")

    def _sample_paired(self) -> dict[str, Any]:
        # Injected FixturePlatformPort returns a real clock dict; Protocol stub is uninferable.
        # pylint: disable=E1111
        raw = self.platform.sample_clock()
        return cast(dict[str, Any], raw)

    def _update_clock_anomaly(self, st: SlotState, sample: Mapping[str, Any]) -> None:
        """Paired interval: lower=wall-boottime_after, upper=wall-boottime_before."""

        before = int(_port_map_get(sample, "boottime_before_ns"))
        after = int(_port_map_get(sample, "boottime_after_ns"))
        wall_s = _parse_wall(str(_port_map_get(sample, "wall_time")))
        wall_ns = wall_s * 1_000_000_000
        lower = wall_ns - after
        upper = wall_ns - before
        if st.wall_offset_lower_bound is None:
            st.wall_offset_lower_bound = lower
        else:
            # Retain maximum lower bound.
            st.wall_offset_lower_bound = max(st.wall_offset_lower_bound, lower)
            # Seal only when a new upper is below the retained lower bound.
            if upper < st.wall_offset_lower_bound:
                self._enter_revoking(st, "clock_anomaly")
                return
        # Observed wall-decrease rule.
        if st.last_wall_s is not None and wall_s < st.last_wall_s:
            self._enter_revoking(st, "clock_anomaly")
            return
        if st.freshness_anchor is not None:
            prev = _parse_wall(st.freshness_anchor.sampled_wall_time)
            if wall_s < prev and st.last_wall_s is None:
                self._enter_revoking(st, "clock_anomaly")
                return
        st.last_wall_s = wall_s

    def _operator_inventory(self) -> set[bytes]:
        inv = getattr(self.platform, "operator_inventory", None)
        return inv if isinstance(inv, set) else set()

    def _capability_digests(self) -> dict[str, str]:
        caps = getattr(self.platform, "capability_digests", None)
        return dict(caps) if isinstance(caps, dict) else {}

    def establish_freshness_anchor(
        self,
        st: SlotState,
        *,
        authority_snapshot_id: str,
        remaining_snapshot_lifetime_ns: int | None = None,
        clock_review: Mapping[str, Any] | None = None,
    ) -> FreshnessAnchor:
        sample: dict[str, Any] = self._sample_paired()
        boot_id = str(_port_map_get(sample, "boot_id"))
        # Remaining lifetime from fixed expires_at / current wall and retained
        # snapshot deadline — never caller authority that can renew it.
        wall_now = _parse_wall(str(_port_map_get(sample, "wall_time")))
        expires_s = _parse_wall(str(st.expires_at))
        remaining_wall_ns = (expires_s - wall_now) * 1_000_000_000
        if remaining_wall_ns <= 0:
            raise ValueError("nonpositive_remaining_lifetime")
        if remaining_snapshot_lifetime_ns is None:
            remaining_snapshot_lifetime_ns = remaining_wall_ns
        if remaining_snapshot_lifetime_ns < 0:
            raise ValueError("negative_snapshot_lifetime")
        # Caller cannot enlarge beyond absolute remaining wall lifetime.
        remaining_snapshot_lifetime_ns = min(
            int(remaining_snapshot_lifetime_ns), remaining_wall_ns
        )
        if remaining_snapshot_lifetime_ns <= 0:
            raise ValueError("nonpositive_remaining_lifetime")
        if st.freshness_anchor is not None and st.freshness_anchor.boot_id == boot_id:
            deadline = min(
                st.freshness_anchor.snapshot_deadline_boottime_ns,
                int(_port_map_get(sample, "boottime_after_ns")) + remaining_snapshot_lifetime_ns,
            )
            if deadline <= int(_port_map_get(sample, "boottime_after_ns")):
                raise ValueError("nonpositive_deadline")
            anchor = FreshnessAnchor(
                boot_id=boot_id,
                authority_snapshot_id=authority_snapshot_id,
                sampled_wall_time=str(_port_map_get(sample, "wall_time")),
                sampled_boottime_ns=int(_port_map_get(sample, "boottime_after_ns")),
                snapshot_deadline_boottime_ns=deadline,
                clock_review_ref=st.freshness_anchor.clock_review_ref,
            )
            st.freshness_anchor = anchor
            return anchor
        # New boot requires authenticated operator clock-review receipt.
        if clock_review is None:
            raise ValueError("clock_review_required")
        if set(clock_review.keys()) != set(CLOCK_REVIEW_KEYS):
            raise ValueError("clock_review_key_set")
        if clock_review.get("schema") != CLOCK_REVIEW_SCHEMA:
            raise ValueError("bad_clock_review_schema")
        if clock_review.get("boot_id") != boot_id:
            raise ValueError("clock_review_boot_mismatch")
        if clock_review.get("expires_at") != st.expires_at:
            raise ValueError("clock_review_expiry_renewal_forbidden")
        if clock_review.get("lineage_id") != st.lineage_id:
            raise ValueError("clock_review_lineage_mismatch")
        if clock_review.get("authority_snapshot_id") != authority_snapshot_id:
            raise ValueError("clock_review_snapshot_mismatch")
        # pylint: disable=C0123  # exact type identity; not isinstance/__class__
        if int(clock_review.get("reviewer_uid", -1)) != LOGICAL_UID["operator"] or type(
            clock_review.get("reviewer_uid")
        ) is not int:
            raise ValueError("clock_review_reviewer_uid")
        if not isinstance(clock_review.get("reviewed_wall_time"), str):
            raise ValueError("clock_review_wall")
        # Reviewed wall must bind the new-boot wall sample — not an unrelated value.
        if clock_review.get("reviewed_wall_time") != str(_port_map_get(sample, "wall_time")):
            raise ValueError("clock_review_wall_mismatch")
        _parse_wall(str(clock_review["reviewed_wall_time"]))
        content = _content_hash(clock_review, "review_payload_sha256")
        if clock_review.get("review_payload_sha256") != content:
            raise ValueError("clock_review_self_hash")
        # Access approval then exact full receipt bytes (including self-hash) in inventory.
        self.check_access(
            "controller", "/fixture/private/operator-inventory/clock-review", "read"
        )
        inventory = self._operator_inventory()
        full_body = {k: clock_review[k] for k in CLOCK_REVIEW_KEYS}
        inv_bytes = _canonical(full_body)
        if inv_bytes not in inventory:
            # Copied reviewer UID / body-without-hash / wrong hash must fail.
            raise ValueError("clock_review_inventory_miss")
        deadline = int(_port_map_get(sample, "boottime_after_ns")) + remaining_snapshot_lifetime_ns
        if deadline <= int(_port_map_get(sample, "boottime_after_ns")):
            raise ValueError("nonpositive_deadline")
        ref = content
        anchor = FreshnessAnchor(
            boot_id=boot_id,
            authority_snapshot_id=authority_snapshot_id,
            sampled_wall_time=str(_port_map_get(sample, "wall_time")),
            sampled_boottime_ns=int(_port_map_get(sample, "boottime_after_ns")),
            snapshot_deadline_boottime_ns=deadline,
            clock_review_ref=ref,
        )
        st.freshness_anchor = anchor
        return anchor

    def _make_sealed_record(self, st: SlotState) -> SealedActivationRecord:
        if st.retirement_receipt is None or st.activation_id is None:
            raise ValueError("sealed_without_receipt")
        return SealedActivationRecord(
            activation_id=st.activation_id,
            activation_manifest=_frozen_map(st.activation_manifest or {}),
            publication_sha256=st.publication_sha256,
            manager_boot_id=st.manager_boot_id,
            unit_invocation_id=st.unit_invocation_id,
            containment_id=st.containment_id,
            terminal_reason=st.terminal_reason,
            retirement_receipt=_frozen_map(st.retirement_receipt),
            verified_manifest_content_sha256=st.verified_manifest_content_sha256 or "",
            state="SEALED",
        )

    def _fresh_slot_after_sealed(self, sealed_st: SlotState) -> SlotState:
        """Replace a SEALED slot with a fresh live SlotState — never mutate SEALED."""

        if sealed_st.state != "SEALED":
            raise ValueError("not_sealed")
        predecessor = sealed_st.sealed_record
        if predecessor is None:
            predecessor = self._make_sealed_record(sealed_st)
        if predecessor.state != "SEALED":
            raise ValueError("sealed_predecessor_corrupt")
        history = list(sealed_st.sealed_history)
        history.append(predecessor)
        new_st = SlotState(
            slot_id=sealed_st.slot_id,
            lineage_id=sealed_st.lineage_id,
            state="NEW",
            authority_head=sealed_st.authority_head,
            expires_at=sealed_st.expires_at,
            wall_offset_lower_bound=sealed_st.wall_offset_lower_bound,
            last_wall_s=sealed_st.last_wall_s,
            freshness_anchor=sealed_st.freshness_anchor,
            sealed_history=history,
            used_state_dirs=set(sealed_st.used_state_dirs),
            sealed_record=None,
        )
        new_st.persisted = {
            "slot_id": new_st.slot_id,
            "lineage_id": new_st.lineage_id,
            "authority_head": new_st.authority_head,
            "expires_at": new_st.expires_at,
            "state": "NEW",
        }
        self.supervisor.reset_for_new_activation()
        return new_st


    def _prepare_activation_freshness_and_lease(
        self,
        st: SlotState,
        *,
        activation_manifest: Mapping[str, Any],
        sample: Mapping[str, Any],
        snap_id: str,
        remaining_snapshot_lifetime_ns: int | None,
        clock_review: Mapping[str, Any] | None,
        max_activation_lifetime_s: int | None,
    ) -> int:
        """Establish/refresh freshness and compute the activation lease deadline."""

        if st.freshness_anchor is not None and st.freshness_anchor.boot_id != _port_map_get(sample, "boot_id"):
            self.establish_freshness_anchor(
                st,
                authority_snapshot_id=snap_id,
                remaining_snapshot_lifetime_ns=remaining_snapshot_lifetime_ns,
                clock_review=clock_review,
            )
        elif st.freshness_anchor is None:
            wall_now = _parse_wall(str(_port_map_get(sample, "wall_time")))
            expires_s = _parse_wall(str(st.expires_at or activation_manifest["expires_at"]))
            rem_wall_ns = (expires_s - wall_now) * 1_000_000_000
            if rem_wall_ns <= 0:
                raise ValueError("nonpositive_remaining_lifetime")
            if remaining_snapshot_lifetime_ns is not None:
                # pylint: disable=C0123  # exact type identity; not isinstance/__class__
                if type(remaining_snapshot_lifetime_ns) is not int:
                    raise ValueError("bad_snapshot_lifetime")
                if remaining_snapshot_lifetime_ns < 0:
                    raise ValueError("negative_snapshot_lifetime")
            rem = (
                rem_wall_ns
                if remaining_snapshot_lifetime_ns is None
                else min(int(remaining_snapshot_lifetime_ns), rem_wall_ns)
            )
            if rem <= 0:
                raise ValueError("nonpositive_remaining_lifetime")
            deadline = int(_port_map_get(sample, "boottime_after_ns")) + rem
            if deadline <= int(_port_map_get(sample, "boottime_after_ns")):
                raise ValueError("nonpositive_deadline")
            st.freshness_anchor = FreshnessAnchor(
                boot_id=str(_port_map_get(sample, "boot_id")),
                authority_snapshot_id=snap_id,
                sampled_wall_time=str(_port_map_get(sample, "wall_time")),
                sampled_boottime_ns=int(_port_map_get(sample, "boottime_after_ns")),
                snapshot_deadline_boottime_ns=deadline,
                clock_review_ref=None,
            )
        else:
            self.establish_freshness_anchor(
                st,
                authority_snapshot_id=snap_id,
                remaining_snapshot_lifetime_ns=remaining_snapshot_lifetime_ns,
                clock_review=None,
            )
        assert st.freshness_anchor is not None
        manifest_max = _require_int(
            activation_manifest["max_monotonic_lifetime_seconds"], "bad_max_lifetime"
        )
        if max_activation_lifetime_s is not None:
            caller_max = _require_int(max_activation_lifetime_s, "bad_max_lifetime")
            if caller_max < 1 or caller_max > 86400:
                raise ValueError("bad_max_lifetime")
            # Caller shrink only — never enlarge the manifest bound.
            max_life = min(manifest_max, caller_max)
        else:
            max_life = manifest_max
        if max_life < 1 or max_life > 86400:
            raise ValueError("bad_max_lifetime")
        expires_at = str(st.expires_at or activation_manifest["expires_at"])
        wall_now = _parse_wall(str(_port_map_get(sample, "wall_time")))
        expires_s = _parse_wall(expires_at)
        remaining_wall = expires_s - wall_now
        if remaining_wall <= 0:
            raise ValueError("nonpositive_remaining_lifetime")
        bound = min(remaining_wall, max_life)
        lease_from_now = int(_port_map_get(sample, "boottime_after_ns")) + 1_000_000_000 * bound
        return min(st.freshness_anchor.snapshot_deadline_boottime_ns, lease_from_now)

    def qualify_and_activate(
        self,
        slot_id: str,
        activation_manifest: Mapping[str, Any],
        launch_policy: Mapping[str, Any],
        *,
        lifecycle_config: Mapping[str, Any] | None = None,
        remaining_snapshot_lifetime_ns: int | None = None,
        clock_review: Mapping[str, Any] | None = None,
        max_activation_lifetime_s: int | None = None,
    ) -> SlotState:
        st = self.slots[slot_id]
        self._acquire_slot_transition()
        try:
            if st.state in ("QUARANTINED", "ACTIVE_IDLE", "TURN_RUNNING", "REVOKING"):
                raise ValueError(f"slot_not_activatable:{st.state}")
            if st.state == "SEALED":
                # Genuine fresh live SlotState — retained SEALED object stays SEALED.
                st = self._fresh_slot_after_sealed(st)
                self.slots[slot_id] = st
            st.state = "QUALIFYING"
            lifecycle_config_core(lifecycle_config)
            for path in (
                "/fixture/private/qualification/manifest.json",
                "/fixture/private/authority/head.json",
                "/fixture/private/issuer/inventory.json",
                "/fixture/private/governance/fence.json",
            ):
                self.check_access("controller", path, "read")
            for path in (
                "/fixture/private/qualification/manifest.json",
                "/fixture/private/issuer/inventory.json",
                "/fixture/private/governance/fence.json",
                "/fixture/private/control/socket",
            ):
                if self.platform.access("runtime", path, "read"):
                    raise ValueError("runtime_private_access_allowed")
            # Pending old populated unit blocks launch.
            if st.unit_invocation_id:
                obs = cast(dict[str, Any], self.platform.manager_observe(st.unit_invocation_id))
                if obs.get("populated") is not False:
                    raise ValueError("pending_populated_unit")
            caps = self._capability_digests()
            policy_hash = validate_launch_policy(launch_policy, capability_digests=caps or None)
            content_hash = validate_activation_manifest(
                activation_manifest,
                slot_id=slot_id,
                lineage_id=st.lineage_id,
                authority_head=str(st.authority_head or ""),
                expires_at=str(st.expires_at),
                capability_digests=caps or None,
                known_state_dirs=st.used_state_dirs,
                launch_policy=launch_policy,
            )
            _ = policy_hash
            if activation_manifest.get("publication_sha256") != st.authority_head:
                if st.authority_head is not None and st.authority_head != activation_manifest[
                    "publication_sha256"
                ]:
                    raise ValueError("head_drift")
            pub = str(activation_manifest["publication_sha256"])
            act_id = str(activation_manifest["activation_id"])
            snap_id = str(activation_manifest["snapshot_id"])
            sample: dict[str, Any] = self._sample_paired()
            lease = self._prepare_activation_freshness_and_lease(
                st,
                activation_manifest=activation_manifest,
                sample=sample,
                snap_id=snap_id,
                remaining_snapshot_lifetime_ns=remaining_snapshot_lifetime_ns,
                clock_review=clock_review,
                max_activation_lifetime_s=max_activation_lifetime_s,
            )
            expires_at = str(st.expires_at or activation_manifest["expires_at"])

            # Manager start — retain IDs even if spawn/ready fails.
            ids = cast(dict[str, Any], self.platform.manager_start(slot_id, act_id))
            st.activation_id = act_id
            st.manager_boot_id = _port_map_get(ids, "manager_boot_id")
            st.unit_invocation_id = _port_map_get(ids, "unit_invocation_id")
            st.containment_id = _port_map_get(ids, "containment_id")
            st.activation_manifest = dict(activation_manifest)
            st.verified_manifest_content_sha256 = content_hash
            st.publication_sha256 = pub
            st.expires_at = expires_at
            st.used_state_dirs.add(str(activation_manifest["state_dir"]))

            try:
                fd_roles = {
                    "supervisor_control": object(),
                    "lease": object(),
                    "notify": object(),
                }
                sup_proc = launch_policy["processes"]["supervisor"]
                argv = list(sup_proc["argv_template"])
                env = dict(sup_proc["environment"])
                cwd = str(sup_proc["cwd"])
                # Validate and spawn the identical typed tuple — never mutate policy.
                # Lazy import: production ``python -I`` refusal must not load supervisor.
                from openclaw_activation_supervisor import validate_launch_tuple

                validate_launch_tuple(launch_policy, "supervisor", argv, env, cwd, fd_roles)
                handle = cast(str, self.platform.spawn("supervisor", argv, env, cwd, fd_roles))
                ready = cast(dict[str, Any], self.platform.next_event(handle))
                if ready.get("kind") != "ready":
                    raise ValueError("supervisor_not_ready")
            # pylint: disable=W0718  # spawn/ready path must revoke on any injected failure
            except Exception:
                # Request stop; remain retire/quarantine capable — domain retained.
                if st.unit_invocation_id:
                    self.platform.manager_stop(st.unit_invocation_id)
                    st.stop_requested = True
                st.state = "REVOKING"
                st.terminal_reason = "integrity_failure"
                raise

            st.lease_deadline_boottime_ns = lease
            self.supervisor.bind_activation(
                activation_manifest=dict(activation_manifest),
                publication_sha256=pub,
                lease_deadline_boottime_ns=lease,
                slot_id=slot_id,
                supervisor_handle=handle,
            )
            st.state = "ACTIVE_IDLE"
            st.sealed_record = None
            st.persisted.update(
                {
                    "state": st.state,
                    "activation_id": act_id,
                    "unit_invocation_id": st.unit_invocation_id,
                    "containment_id": st.containment_id,
                    "manager_boot_id": st.manager_boot_id,
                    "publication_sha256": pub,
                    "expires_at": expires_at,
                    "authority_head": st.authority_head,
                    "freshness_anchor": st.freshness_anchor.as_dict(),
                    "lease_deadline_boottime_ns": lease,
                    "verified_manifest_content_sha256": content_hash,
                    "stop_requested": st.stop_requested,
                }
            )
            return st
        except Exception:
            if st.state == "QUALIFYING":
                st.state = "REVOKING"
                st.terminal_reason = st.terminal_reason or "integrity_failure"
            raise
        finally:
            self._release_slot_transition()

    def open_control_session(self, connection_id: str) -> None:
        if connection_id in self._open_sessions:
            raise ValueError("duplicate_control_open")
        if len(self._open_sessions) >= self.MAX_CONTROL_CONNECTIONS:
            raise ValueError("control_connection_capacity")
        self.validate_peer(connection_id, expected_role="operator")
        self._open_sessions.add(connection_id)
        sample: dict[str, Any] = self._sample_paired()
        self._conn_activity_ns[connection_id] = int(_port_map_get(sample, "boottime_after_ns"))
        self._inbound_bufs[connection_id] = bytearray()

    def close_control_session(self, connection_id: str | None = None) -> None:
        if connection_id is None:
            return
        if connection_id not in self._open_sessions:
            # Unknown / already-closed — do not decrement accounting.
            return
        self._open_sessions.discard(connection_id)
        self._inbound_bufs.pop(connection_id, None)
        self._conn_activity_ns.pop(connection_id, None)
        self._conn_send_started_ns.pop(connection_id, None)
        self._pending_outbound.pop(connection_id, None)
        closer = getattr(self.platform, "close_control_connection", None)
        if callable(closer):
            # pylint: disable=E1102  # optional injected close_control_connection after callable()
            cast(Callable[..., Any], closer)(connection_id)

    def _flush_pending_outbound(self, connection_id: str) -> bytes | None:
        """Complete or SEND-timeout a previously blocked framed response."""

        framed = self._pending_outbound.get(connection_id)
        if framed is None:
            return None
        outbound = getattr(self.platform, "control_outbound", None)
        if not callable(outbound):
            self._pending_outbound.pop(connection_id, None)
            self._conn_send_started_ns.pop(connection_id, None)
            return framed
        try:
            # pylint: disable=E1102  # optional injected control_outbound after callable()
            q = cast(Callable[..., Any], outbound)(connection_id)
        # pylint: disable=W0718  # platform outbound may raise any injected failure
        except Exception:
            self.close_control_session(connection_id)
            return None
        sample: dict[str, Any] = self._sample_paired()
        now = int(_port_map_get(sample, "boottime_after_ns"))
        started = self._conn_send_started_ns.get(connection_id, now)
        if getattr(q, "blocked", False):
            if now - started > CONTROL_IO_TIMEOUT_NS:
                self.close_control_session(connection_id)
                return None
            return None
        try:
            q.write(framed)
        # pylint: disable=W0718  # platform outbound write may raise any injected failure
        except Exception:
            self.close_control_session(connection_id)
            return None
        self._pending_outbound.pop(connection_id, None)
        self._conn_send_started_ns.pop(connection_id, None)
        self._conn_activity_ns[connection_id] = now
        return framed

    def _write_framed_response(
        self, connection_id: str, resp: Mapping[str, Any]
    ) -> bytes | None:
        """Encode and write every framed response through the bounded outbound path."""

        try:
            framed = encode_framed_response(resp)
        except ValueError:
            self.close_control_session(connection_id)
            return None
        outbound = getattr(self.platform, "control_outbound", None)
        if callable(outbound):
            try:
                # pylint: disable=E1102  # optional injected control_outbound after callable()
                q = cast(Callable[..., Any], outbound)(connection_id)
            # pylint: disable=W0718  # platform outbound may raise any injected failure
            except Exception:
                self.close_control_session(connection_id)
                return None
            sample: dict[str, Any] = self._sample_paired()
            now = int(_port_map_get(sample, "boottime_after_ns"))
            if getattr(q, "blocked", False):
                self._pending_outbound[connection_id] = framed
                if connection_id not in self._conn_send_started_ns:
                    self._conn_send_started_ns[connection_id] = now
                started = self._conn_send_started_ns[connection_id]
                if now - started > CONTROL_IO_TIMEOUT_NS:
                    self.close_control_session(connection_id)
                    return None
                # Still within send window but blocked — no partial write.
                return None
            try:
                q.write(framed)
            # pylint: disable=W0718  # platform outbound write may raise any injected failure
            except Exception:
                self.close_control_session(connection_id)
                return None
            self._pending_outbound.pop(connection_id, None)
            self._conn_send_started_ns.pop(connection_id, None)
            self._conn_activity_ns[connection_id] = now
        return framed

    def handle_framed_bytes(self, connection_id: str, chunk: bytes) -> bytes | None:
        """External control front end via FixturePlatform ByteQueues.

        Partial input remains partial until complete. Timeout/desync closes with
        no partial success. Returns encoded response bytes or None while partial.
        Only currently opened/authenticated connections may be serviced.
        """

        if connection_id not in self._open_sessions:
            return None
        # Prefer completing a blocked SEND before receive-timeout accounting.
        if connection_id in self._pending_outbound:
            return self._flush_pending_outbound(connection_id)
        sample: dict[str, Any] = self._sample_paired()
        now = int(_port_map_get(sample, "boottime_after_ns"))
        last = self._conn_activity_ns.get(connection_id, now)
        if now - last > CONTROL_IO_TIMEOUT_NS:
            self.close_control_session(connection_id)
            return None
        try:
            self.validate_peer(connection_id, expected_role="operator")
        except ValueError:
            self.close_control_session(connection_id)
            return None
        buf = self._inbound_bufs.setdefault(connection_id, bytearray())
        buf.extend(chunk)
        # Mirror into platform inbound queue when present (bounded queue evidence).
        inbound = getattr(self.platform, "control_inbound", None)
        if callable(inbound):
            try:
                # pylint: disable=E1102  # optional injected control_inbound after callable()
                q = cast(Callable[..., Any], inbound)(connection_id)
                q.write(chunk)
            # pylint: disable=W0718  # platform inbound may raise any injected failure
            except Exception:
                self.close_control_session(connection_id)
                return None
        obj, rem, err = decode_framed_request(bytes(buf))
        if err is not None:
            self._inbound_bufs[connection_id] = bytearray()
            self.close_control_session(connection_id)
            return None
        if obj is None:
            # Still partial — receive window remains armed via activity stamp only on complete.
            return None
        self._inbound_bufs[connection_id] = bytearray(rem)
        self._conn_activity_ns[connection_id] = now
        try:
            validate_control_request(obj)
        except ValueError:
            resp = self._response(obj, "invalid_request", {"reason": "bad_arguments"})
            return self._write_framed_response(connection_id, resp)
        resp = self._dispatch_validated(connection_id, obj)
        return self._write_framed_response(connection_id, resp)

    def handle_control(
        self,
        connection_id: str,
        request: Mapping[str, Any],
        *,
        consumer_blocked: bool = False,
    ) -> dict[str, Any]:
        """Private dict dispatch helper — same open-session gate as framed path."""

        if connection_id not in self._open_sessions:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        try:
            validate_control_request(request)
        except ValueError:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        return self._dispatch_validated(
            connection_id, dict(request), consumer_blocked=consumer_blocked
        )

    def _dispatch_validated(
        self,
        connection_id: str,
        request: dict[str, Any],
        *,
        consumer_blocked: bool = False,
    ) -> dict[str, Any]:
        try:
            self.validate_peer(connection_id, expected_role="operator")
        except ValueError:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        slot_id = str(request["slot_id"])
        if slot_id not in self.slots:
            return self._response(request, "unavailable", {"reason": "not_active"})
        st = self.slots[slot_id]
        if st.state == "QUARANTINED":
            return self._response(request, "unavailable", {"reason": "not_active"})
        if st.state == "SEALED":
            return self._response(
                request,
                "sealed",
                {
                    "reason": st.terminal_reason or "shutdown",
                    "retirement_ref": None
                    if st.retirement_receipt is None
                    else st.retirement_receipt.get("receipt_payload_sha256"),
                },
            )
        sample: dict[str, Any] = self._sample_paired()
        self._update_clock_anomaly(st, sample)
        if st.state == "REVOKING":
            return self._response(request, "revoking", {"reason": st.terminal_reason or "operator"})
        if st.activation_id and request.get("activation_id") != st.activation_id:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        if st.lease_deadline_boottime_ns is not None:
            now_bt = int(_port_map_get(sample, "boottime_after_ns"))
            if now_bt > st.lease_deadline_boottime_ns:
                self._enter_revoking(st, "expiry")
                return self._response(request, "revoking", {"reason": "expiry"})
        op = request["op"]
        if op == "status":
            return self._status_response(request, st)
        if op == "revoke":
            _ = consumer_blocked
            reason = str(request["reason"])
            self._enter_revoking(st, reason)
            self.supervisor.revoke(reason)
            return self._response(request, "revoking", {"reason": reason})
        if op in ("turn", "cancel"):
            if st.state not in ("ACTIVE_IDLE", "TURN_RUNNING"):
                return self._response(request, "unavailable", {"reason": "not_active"})
            resp = self.supervisor.handle_request(dict(request), clock_sample=sample)
            if resp["outcome"] == "running":
                st.state = "TURN_RUNNING"
            elif resp["outcome"] == "committed":
                st.state = "ACTIVE_IDLE"
            elif resp["outcome"] == "cancelled":
                # Cancel live turn → REVOKING; SEALED only after independent retirement.
                self._enter_revoking(st, "disconnect")
            elif resp["outcome"] == "unavailable" and resp.get("payload", {}).get(
                "reason"
            ) == "capacity":
                # Capacity is an INTERNAL terminal reason; drive stop + REVOKING.
                if st.state not in ("SEALED", "QUARANTINED"):
                    st.state = "REVOKING"
                    st.terminal_reason = "capacity"
                    st.persisted["state"] = "REVOKING"
                    st.persisted["terminal_reason"] = "capacity"
                    st.persisted["internal_terminal"] = "capacity"
                    if st.unit_invocation_id and not st.stop_requested:
                        self.platform.manager_stop(st.unit_invocation_id)
                        st.stop_requested = True
                        st.persisted["stop_requested"] = True
            elif resp["outcome"] == "sealed":
                # Must not accept sealed-with-null; drive REVOKING instead.
                self._enter_revoking(st, "integrity_failure")
            elif resp["outcome"] == "revoking":
                st.state = "REVOKING"
                st.terminal_reason = str(resp.get("payload", {}).get("reason", "operator"))
            return resp
        return self._response(request, "invalid_request", {"reason": "bad_arguments"})

    def _status_response(self, request: Mapping[str, Any], st: SlotState) -> dict[str, Any]:
        turn_id = self.supervisor.current_turn_id()
        return self._response(
            request,
            "status",
            {
                "state": st.state,
                "turn_id": turn_id,
                "publication_sha256": st.publication_sha256,
                "lease_deadline_boottime_ns": st.lease_deadline_boottime_ns,
                "terminal_reason": st.terminal_reason,
            },
        )

    @staticmethod
    def _response(
        request: Mapping[str, Any], outcome: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "schema": CONTROL_SCHEMA,
            "request_id": request.get("request_id"),
            "slot_id": request.get("slot_id"),
            "activation_id": request.get("activation_id"),
            "outcome": outcome,
            "payload": payload,
        }

    def _enter_revoking(self, st: SlotState, reason: str) -> None:
        if st.state in ("SEALED", "QUARANTINED"):
            return
        if reason in INTERNAL_TERMINAL_REASONS:
            terminal = reason
        elif reason not in REVOKE_REASONS:
            terminal = "integrity_failure"
        else:
            terminal = reason
        st.state = "REVOKING"
        st.terminal_reason = terminal
        st.persisted["state"] = st.state
        st.persisted["terminal_reason"] = terminal

    def request_manager_stop(self, slot_id: str) -> dict[str, Any]:
        st = self.slots[slot_id]
        if not st.unit_invocation_id:
            raise ValueError("no_invocation")
        out = cast(dict[str, Any], self.platform.manager_stop(st.unit_invocation_id))
        st.stop_requested = True
        st.persisted["stop_requested"] = True
        return out

    def attempt_retirement(
        self, slot_id: str, *, terminal_reason: str | None = None
    ) -> dict[str, Any]:
        """Issue retirement only from REVOKING with stop + exact empty observation."""

        st = self.slots[slot_id]
        if st.state != "REVOKING":
            raise ValueError("retirement_requires_revoking")
        if not st.stop_requested:
            raise ValueError("retirement_requires_stop_request")
        if not st.unit_invocation_id:
            self._quarantine(st, "missing_invocation")
            raise ValueError("quarantined:missing_invocation")
        obs = cast(dict[str, Any], self.platform.manager_observe(st.unit_invocation_id))
        reason = terminal_reason or st.terminal_reason or "operator"
        if reason not in TERMINAL_RECEIPT_REASONS:
            raise ValueError("bad_terminal_reason")
        if obs.get("manager_boot_id") != st.manager_boot_id:
            self._quarantine(st, "stale_boot")
            raise ValueError("quarantined:stale_boot")
        if obs.get("unit_invocation_id") != st.unit_invocation_id:
            self._quarantine(st, "stale_invocation")
            raise ValueError("quarantined:stale_invocation")
        if obs.get("containment_id") != st.containment_id:
            self._quarantine(st, "stale_containment")
            raise ValueError("quarantined:stale_containment")
        if st.activation_id is None:
            self._quarantine(st, "stale_activation")
            raise ValueError("quarantined:stale_activation")
        if obs.get("terminal") is not True or obs.get("populated") is not False:
            self._quarantine(
                st,
                (
                    "uncertain_emptiness:"
                    f"terminal={obs.get('terminal')}:populated={obs.get('populated')}"
                ),
            )
            raise ValueError("quarantined:uncertain_emptiness")
        sample: dict[str, Any] = self._sample_paired()
        # Verified manifest content hash — not a new hash including self-hash.
        manifest_sha = st.verified_manifest_content_sha256
        if manifest_sha is None and st.activation_manifest is not None:
            manifest_sha = _content_hash(st.activation_manifest, "manifest_payload_sha256")
        body = {
            "schema": RETIREMENT_SCHEMA,
            "slot_id": st.slot_id,
            "activation_id": st.activation_id,
            "activation_manifest_sha256": manifest_sha,
            "pinned_publication_sha256": st.publication_sha256,
            "manager_boot_id": st.manager_boot_id,
            "unit_invocation_id": st.unit_invocation_id,
            "containment_id": st.containment_id,
            "terminal_reason": reason,
            "observed_empty_boottime_ns": int(_port_map_get(sample, "boottime_after_ns")),
        }
        receipt = dict(body)
        receipt["receipt_payload_sha256"] = _sha256_labeled(_canonical(body))
        self.check_access("controller", "/fixture/receipt/retirement.json", "create")
        frozen_receipt = _frozen_map(receipt)
        st.retirement_receipt = frozen_receipt
        st.state = "SEALED"
        st.terminal_reason = reason
        st.sealed_record = self._make_sealed_record(st)
        st.persisted["state"] = "SEALED"
        st.persisted["retirement_receipt"] = dict(receipt)
        return dict(receipt)

    def _quarantine(self, st: SlotState, reason: str) -> None:
        st.state = "QUARANTINED"
        st.quarantine_reason = reason
        st.persisted["state"] = "QUARANTINED"
        st.persisted["quarantine_reason"] = reason

    def reconcile_after_controller_restart(self, slot_id: str) -> SlotState:
        """Persist quarantine; never restore stale persisted ACTIVE bytes over it."""

        st = self.slots[slot_id]
        if st.unit_invocation_id:
            obs = cast(dict[str, Any], self.platform.manager_observe(st.unit_invocation_id))
            if obs.get("populated") is not False:
                self._quarantine(st, "restart_nonempty")
                # Quarantine wins — do not rehydrate ACTIVE from persisted snapshot.
                return st
        # Same-boot: retain persisted identity fields only when not quarantined.
        if st.state != "QUARANTINED":
            persisted_state = st.persisted.get("state")
            if persisted_state in ("ACTIVE_IDLE", "TURN_RUNNING") and st.state == "REVOKING":
                # Crash during revoke — stay REVOKING.
                st.persisted["state"] = "REVOKING"
        return st

    def serving_rollback_view(self, slot_id: str) -> dict[str, Any]:
        st = self.slots[slot_id]
        return {
            "authority_head": st.authority_head,
            "expires_at": st.expires_at,
            "freshness_anchor": None
            if st.freshness_anchor is None
            else st.freshness_anchor.as_dict(),
            "session_resumable": False,
            "teardown_is_recovery": False,
            "serving_only": True,
            "sealed_history_len": len(st.sealed_history),
        }

    def retire_before_lineage_exclusive(self, slot_id: str) -> None:
        self._acquire_slot_transition()
        try:
            if self.slots[slot_id].state != "SEALED":
                raise ValueError("not_sealed")
        finally:
            self._release_slot_transition()
        self._acquire_lineage_exclusive()
        try:
            pass
        finally:
            self._release_lineage_exclusive()


_default_cores: dict[str, ControllerCore] = {}


def enroll_slot(
    platform: FixturePlatformPort,
    supervisor: Any,
    slot_id: str,
    lineage_id: str,
    *,
    authority_head: str,
    expires_at: str,
) -> SlotState:
    core = ControllerCore(platform=platform, supervisor=supervisor)
    st = core.enroll_slot(
        slot_id, lineage_id, authority_head=authority_head, expires_at=expires_at
    )
    _default_cores[slot_id] = core
    return st


def get_controller(slot_id: str) -> ControllerCore:
    return _default_cores[slot_id]


if __name__ == "__main__":
    main()
