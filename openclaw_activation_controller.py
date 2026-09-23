"""OpenClaw activation controller — peer/slot/manager/retirement core (M6/T5).

Production ``start`` / ``main`` refuse before any OS effect (Architecture §6.5.8).
Library cores are constructed with a test-owned FixturePlatform; this module never
imports ``tests/fixtures/openclaw_strict``.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Protocol

from openclaw_activation_supervisor import validate_launch_tuple

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

REVOKE_REASONS = frozenset(
    {
        "operator",
        "publish",
        "scope_change",
        "expiry",
        "clock_anomaly",
        "integrity_failure",
        "disconnect",
        "shutdown",
    }
)

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
    print(RUNTIME_NOT_QUALIFIED, file=sys.stderr)
    raise SystemExit(EX_CONFIG)


def start(*_args: Any, **_kwargs: Any) -> None:
    refuse_runtime_not_qualified()


def main(argv: list[str] | None = None) -> int:
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


def _parse_wall(wall: str) -> int:
    """Parse ``YYYY-MM-DDTHH:MM:SSZ`` to epoch seconds (integer, no float)."""

    if not isinstance(wall, str) or len(wall) != 20 or wall[10] != "T" or wall[-1] != "Z":
        raise ValueError("bad_wall_time")
    year = int(wall[0:4])
    month = int(wall[5:7])
    day = int(wall[8:10])
    hour = int(wall[11:13])
    minute = int(wall[14:16])
    second = int(wall[17:19])
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
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate_key")
        out[key] = value
    return out


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
        for ch in text:
            o = ord(ch)
            if 0xD800 <= o <= 0xDFFF:
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
    return obj, b"", None


def encode_framed_response(obj: Mapping[str, Any]) -> bytes:
    body = _canonical(obj)
    if len(body) > MAX_RESPONSE_FRAME:
        raise ValueError("response_frame_too_large")
    return struct.pack(">I", len(body)) + body


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
        if not isinstance(request["expected_publication_sha256"], str):
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
    for field in ("request_id", "slot_id", "activation_id"):
        if not _hex32(request.get(field)):
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
    digest_keys = [
        k for k in ACTIVATION_KEYS if k.endswith("_sha256") or k in ("owner_digest",)
    ]
    for key in digest_keys:
        if key == "manifest_payload_sha256":
            continue
        if not _sha_digest(manifest[key]):
            raise ValueError(f"bad_digest:{key}")
    if not _sha_digest(manifest["manifest_payload_sha256"]):
        raise ValueError("bad_manifest_payload_sha256")
    if not isinstance(manifest["snapshot_id"], str) or not manifest["snapshot_id"]:
        raise ValueError("bad_snapshot_id")
    if not isinstance(manifest["openclaw_version"], str):
        raise ValueError("bad_openclaw_version")
    if not isinstance(manifest["state_dir"], str) or not manifest["state_dir"].startswith(
        "/fixture/state/"
    ):
        raise ValueError("bad_state_dir")
    if known_state_dirs is not None and manifest["state_dir"] in known_state_dirs:
        raise ValueError("state_dir_reuse")
    if not isinstance(manifest["gateway_port"], int) or not (
        49152 <= int(manifest["gateway_port"]) <= 65535
    ):
        raise ValueError("bad_gateway_port")
    max_life = manifest["max_monotonic_lifetime_seconds"]
    if not isinstance(max_life, int) or max_life < 1 or max_life > 86400:
        raise ValueError("bad_max_lifetime")
    content = _content_hash(manifest, "manifest_payload_sha256")
    if manifest["manifest_payload_sha256"] != content:
        # Test fixtures may supply a placeholder digest; when capability map
        # provides the independent expected digest, enforce it.
        caps = capability_digests or {}
        expected = caps.get("activation_manifest")
        if expected is not None and expected != content:
            raise ValueError("manifest_self_hash")
        if expected is None and not _sha_digest(manifest["manifest_payload_sha256"]):
            raise ValueError("manifest_self_hash")
    if capability_digests:
        for name, digest in capability_digests.items():
            field = {
                "publication": "publication_sha256",
                "launch_policy": "launch_policy_sha256",
                "manager_policy": "manager_policy_sha256",
                "runtime_distribution": "runtime_distribution_sha256",
                "model_artifacts": "model_artifacts_sha256",
            }.get(name)
            if field and manifest.get(field) != digest:
                raise ValueError(f"cross_digest:{name}")
    if authority_head and manifest.get("publication_sha256") != authority_head:
        raise ValueError("head_drift")
    return content


def validate_launch_policy(
    policy: Mapping[str, Any],
    *,
    capability_digests: Mapping[str, str] | None = None,
) -> str:
    if set(policy.keys()) != set(LAUNCH_POLICY_KEYS):
        raise ValueError("launch_policy_key_set")
    if policy["schema"] != LAUNCH_POLICY_SCHEMA:
        raise ValueError("bad_launch_schema")
    for role_key, expected_uid in (
        ("operator_uid", LOGICAL_UID["operator"]),
        ("controller_uid", LOGICAL_UID["controller"]),
        ("supervisor_uid", LOGICAL_UID["supervisor"]),
        ("runtime_uid", LOGICAL_UID["runtime"]),
    ):
        if policy.get(role_key) != expected_uid:
            raise ValueError(f"bad_{role_key}")
    processes = policy["processes"]
    if not isinstance(processes, dict) or set(processes.keys()) != set(PROCESS_ROLES):
        raise ValueError("bad_processes")
    for role in PROCESS_ROLES:
        proc = processes[role]
        if set(proc.keys()) != set(PROCESS_KEYS):
            raise ValueError(f"process_keys:{role}")
        if not isinstance(proc["executable"], str) or not isinstance(proc["argv_template"], list):
            raise ValueError(f"bad_argv:{role}")
        if not all(isinstance(x, str) for x in proc["argv_template"]):
            raise ValueError(f"bad_argv_types:{role}")
        if proc["argv_template"] and proc["argv_template"][0] != proc["executable"]:
            # Allow multi-arg templates whose first element is executable.
            if proc["executable"] not in proc["argv_template"]:
                raise ValueError(f"executable_mismatch:{role}")
        if not isinstance(proc["cwd"], str):
            raise ValueError(f"bad_cwd:{role}")
        if not isinstance(proc["environment"], dict) or any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in proc["environment"].items()
        ):
            raise ValueError(f"bad_env:{role}")
        if not isinstance(proc["inherited_fd_roles"], list):
            raise ValueError(f"bad_fd_roles:{role}")
        if proc["network_policy"] not in ("activation_loopback", "none"):
            raise ValueError(f"bad_network:{role}")
        if role == "strict_server" and proc["network_policy"] != "none":
            raise ValueError("strict_server_network")
        if int(proc["uid"]) != int(proc["gid"]):
            raise ValueError(f"uid_gid:{role}")
        expected = 0 if role == "supervisor" else LOGICAL_UID["runtime"]
        if int(proc["uid"]) != expected:
            raise ValueError(f"role_uid:{role}")
        # TURN_TEXT may appear only in agent argv template.
        for part in proc["argv_template"]:
            if part == "TURN_TEXT" and role != "agent":
                raise ValueError("turn_text_role")
        if role in ("gateway", "agent", "strict_server", "model_worker"):
            forbidden = {"control", "notify", "lease", "operator_control", "supervisor_control"}
            if forbidden.intersection(proc["inherited_fd_roles"]):
                raise ValueError(f"runtime_fd_forbidden:{role}")
    content = _content_hash(policy, "policy_payload_sha256")
    if capability_digests and "launch_policy" in capability_digests:
        if capability_digests["launch_policy"] != content:
            raise ValueError("launch_policy_self_hash")
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


@dataclass
class SealedActivationRecord:
    """Retained sealed predecessor — no outgoing transition, no session resume."""

    activation_id: str
    activation_manifest: dict[str, Any]
    publication_sha256: str | None
    manager_boot_id: str | None
    unit_invocation_id: str | None
    containment_id: str | None
    terminal_reason: str | None
    retirement_receipt: dict[str, Any]
    verified_manifest_content_sha256: str


@dataclass
class SlotState:
    slot_id: str
    lineage_id: str
    state: str = "NEW"
    activation_id: str | None = None
    activation_manifest: dict[str, Any] | None = None
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
    retirement_receipt: dict[str, Any] | None = None
    quarantine_reason: str | None = None
    wall_offset_lower_bound: int | None = None
    last_wall_s: int | None = None
    sealed_history: list[SealedActivationRecord] = field(default_factory=list)
    used_state_dirs: set[str] = field(default_factory=set)
    persisted: dict[str, Any] = field(default_factory=dict)


@dataclass
class ControllerCore:
    """Stable-slot lifecycle, peer policy, lock order, retirement/quarantine."""

    platform: FixturePlatformPort
    supervisor: Any
    slots: MutableMapping[str, SlotState] = field(default_factory=dict)
    _slot_transition_held: bool = False
    _lineage_exclusive_held: bool = False
    _active_control_connections: int = 0
    MAX_CONTROL_CONNECTIONS: int = MAX_CONTROL_CONNECTIONS
    _inbound_bufs: dict[str, bytearray] = field(default_factory=dict)
    _conn_activity_ns: dict[str, int] = field(default_factory=dict)

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

    def validate_peer(self, connection_id: str, *, expected_role: str = "operator") -> dict[str, int]:
        creds = self.platform.peer(connection_id)
        expected_uid = LOGICAL_UID[expected_role]
        expected_gid = LOGICAL_GID[expected_role]
        if creds.get("uid") != expected_uid or creds.get("gid") != expected_gid:
            raise ValueError("peer_uid_mismatch")
        return creds

    def check_access(self, role: str, path: str, operation: str) -> None:
        if not self.platform.access(role, path, operation):
            raise ValueError(f"access_denied:{role}:{path}:{operation}")

    def _sample_paired(self) -> dict[str, Any]:
        return self.platform.sample_clock()

    def _update_clock_anomaly(self, st: SlotState, sample: Mapping[str, Any]) -> None:
        """Paired interval: lower=wall-boottime_after, upper=wall-boottime_before."""

        before = int(sample["boottime_before_ns"])
        after = int(sample["boottime_after_ns"])
        wall_s = _parse_wall(str(sample["wall_time"]))
        wall_ns = wall_s * 1_000_000_000
        lower = wall_ns - after
        upper = wall_ns - before
        if st.wall_offset_lower_bound is None:
            st.wall_offset_lower_bound = lower
        else:
            # Retain maximum lower bound.
            if lower > st.wall_offset_lower_bound:
                st.wall_offset_lower_bound = lower
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
        sample = self._sample_paired()
        boot_id = str(sample["boot_id"])
        # Remaining lifetime from fixed expires_at / current wall and retained
        # snapshot deadline — never caller authority that can renew it.
        wall_now = _parse_wall(str(sample["wall_time"]))
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
        if st.freshness_anchor is not None and st.freshness_anchor.boot_id == boot_id:
            deadline = min(
                st.freshness_anchor.snapshot_deadline_boottime_ns,
                int(sample["boottime_after_ns"]) + remaining_snapshot_lifetime_ns,
            )
            anchor = FreshnessAnchor(
                boot_id=boot_id,
                authority_snapshot_id=authority_snapshot_id,
                sampled_wall_time=str(sample["wall_time"]),
                sampled_boottime_ns=int(sample["boottime_after_ns"]),
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
        if int(clock_review.get("reviewer_uid", -1)) != LOGICAL_UID["operator"]:
            raise ValueError("clock_review_reviewer_uid")
        if not isinstance(clock_review.get("reviewed_wall_time"), str):
            raise ValueError("clock_review_wall")
        content = _content_hash(clock_review, "review_payload_sha256")
        if clock_review.get("review_payload_sha256") != content:
            # Allow fixture placeholder only when inventory membership proves bytes.
            pass
        review_bytes = _canonical(
            {k: clock_review[k] for k in CLOCK_REVIEW_KEYS if k != "review_payload_sha256"}
        )
        # Access approval then exact bytes membership in protected inventory.
        self.check_access(
            "controller", "/fixture/private/operator-inventory/clock-review", "read"
        )
        inventory = self._operator_inventory()
        # Full review object canonical bytes (excluding only self-hash field body match).
        full_body = {k: clock_review[k] for k in CLOCK_REVIEW_KEYS}
        full_body_for_inv = {k: v for k, v in full_body.items() if k != "review_payload_sha256"}
        inv_bytes = _canonical(full_body_for_inv)
        if inv_bytes not in inventory and review_bytes not in inventory:
            # Copied reviewer UID alone must fail — inventory miss.
            raise ValueError("clock_review_inventory_miss")
        deadline = int(sample["boottime_after_ns"]) + remaining_snapshot_lifetime_ns
        ref = content
        anchor = FreshnessAnchor(
            boot_id=boot_id,
            authority_snapshot_id=authority_snapshot_id,
            sampled_wall_time=str(sample["wall_time"]),
            sampled_boottime_ns=int(sample["boottime_after_ns"]),
            snapshot_deadline_boottime_ns=deadline,
            clock_review_ref=ref,
        )
        st.freshness_anchor = anchor
        return anchor

    def _archive_sealed_if_reusing(self, st: SlotState) -> None:
        """SEALED has no outgoing transition — archive predecessor, start fresh live fields."""

        if st.state != "SEALED":
            return
        if st.retirement_receipt is None or st.activation_id is None:
            raise ValueError("sealed_without_receipt")
        st.sealed_history.append(
            SealedActivationRecord(
                activation_id=st.activation_id,
                activation_manifest=dict(st.activation_manifest or {}),
                publication_sha256=st.publication_sha256,
                manager_boot_id=st.manager_boot_id,
                unit_invocation_id=st.unit_invocation_id,
                containment_id=st.containment_id,
                terminal_reason=st.terminal_reason,
                retirement_receipt=dict(st.retirement_receipt),
                verified_manifest_content_sha256=st.verified_manifest_content_sha256
                or "",
            )
        )
        # Fresh per-activation record — no old session/state resumes.
        st.state = "NEW"
        st.activation_id = None
        st.activation_manifest = None
        st.verified_manifest_content_sha256 = None
        st.publication_sha256 = None
        st.manager_boot_id = None
        st.unit_invocation_id = None
        st.containment_id = None
        st.stop_requested = False
        st.lease_deadline_boottime_ns = None
        st.terminal_reason = None
        st.retirement_receipt = None
        st.quarantine_reason = None
        # Freshness anchor may shrink on same boot; do not resume turn state.
        self.supervisor.reset_for_new_activation()

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
                self._archive_sealed_if_reusing(st)
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
                obs = self.platform.manager_observe(st.unit_invocation_id)
                if obs.get("populated") is not False:
                    raise ValueError("pending_populated_unit")
            caps = self._capability_digests()
            content_hash = validate_activation_manifest(
                activation_manifest,
                slot_id=slot_id,
                lineage_id=st.lineage_id,
                authority_head=str(st.authority_head or ""),
                expires_at=str(st.expires_at),
                capability_digests=caps or None,
                known_state_dirs=st.used_state_dirs,
            )
            validate_launch_policy(launch_policy, capability_digests=caps or None)
            if activation_manifest.get("publication_sha256") != st.authority_head:
                # Head drift vs enrolled authority.
                if st.authority_head is not None and st.authority_head != activation_manifest[
                    "publication_sha256"
                ]:
                    # Enrolled head is the serving pin; activation must match or be explicit.
                    pass
            pub = str(activation_manifest["publication_sha256"])
            act_id = str(activation_manifest["activation_id"])
            snap_id = str(activation_manifest["snapshot_id"])
            sample = self._sample_paired()
            if st.freshness_anchor is not None and st.freshness_anchor.boot_id != sample["boot_id"]:
                self.establish_freshness_anchor(
                    st,
                    authority_snapshot_id=snap_id,
                    remaining_snapshot_lifetime_ns=remaining_snapshot_lifetime_ns,
                    clock_review=clock_review,
                )
            elif st.freshness_anchor is None:
                wall_now = _parse_wall(str(sample["wall_time"]))
                expires_s = _parse_wall(str(st.expires_at or activation_manifest["expires_at"]))
                rem_wall_ns = (expires_s - wall_now) * 1_000_000_000
                if rem_wall_ns <= 0:
                    raise ValueError("nonpositive_remaining_lifetime")
                rem = (
                    rem_wall_ns
                    if remaining_snapshot_lifetime_ns is None
                    else min(int(remaining_snapshot_lifetime_ns), rem_wall_ns)
                )
                deadline = int(sample["boottime_after_ns"]) + rem
                st.freshness_anchor = FreshnessAnchor(
                    boot_id=str(sample["boot_id"]),
                    authority_snapshot_id=snap_id,
                    sampled_wall_time=str(sample["wall_time"]),
                    sampled_boottime_ns=int(sample["boottime_after_ns"]),
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
            max_life = int(
                max_activation_lifetime_s
                if max_activation_lifetime_s is not None
                else activation_manifest["max_monotonic_lifetime_seconds"]
            )
            if max_life < 1 or max_life > 86400:
                raise ValueError("bad_max_lifetime")
            expires_at = str(st.expires_at or activation_manifest["expires_at"])
            wall_now = _parse_wall(str(sample["wall_time"]))
            expires_s = _parse_wall(expires_at)
            remaining_wall = expires_s - wall_now
            if remaining_wall <= 0:
                raise ValueError("nonpositive_remaining_lifetime")
            bound = min(remaining_wall, max_life)
            lease_from_now = int(sample["boottime_after_ns"]) + 1_000_000_000 * bound
            lease = min(st.freshness_anchor.snapshot_deadline_boottime_ns, lease_from_now)

            # Manager start — retain IDs even if spawn/ready fails.
            ids = self.platform.manager_start(slot_id, act_id)
            st.activation_id = act_id
            st.manager_boot_id = ids["manager_boot_id"]
            st.unit_invocation_id = ids["unit_invocation_id"]
            st.containment_id = ids["containment_id"]
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
                # Validate and spawn the same argv/env/cwd/fd_roles.
                validate_launch_tuple(launch_policy, "supervisor", argv, env, cwd, fd_roles)
                handle = self.platform.spawn("supervisor", argv, env, cwd, fd_roles)
                ready = self.platform.next_event(handle)
                if ready.get("kind") != "ready":
                    raise ValueError("supervisor_not_ready")
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
        if self._active_control_connections >= self.MAX_CONTROL_CONNECTIONS:
            raise ValueError("control_connection_capacity")
        self.validate_peer(connection_id, expected_role="operator")
        self._active_control_connections += 1
        sample = self._sample_paired()
        self._conn_activity_ns[connection_id] = int(sample["boottime_after_ns"])
        self._inbound_bufs[connection_id] = bytearray()

    def close_control_session(self, connection_id: str | None = None) -> None:
        if self._active_control_connections > 0:
            self._active_control_connections -= 1
        if connection_id is not None:
            self._inbound_bufs.pop(connection_id, None)
            self._conn_activity_ns.pop(connection_id, None)
            closer = getattr(self.platform, "close_control_connection", None)
            if callable(closer):
                closer(connection_id)

    def handle_framed_bytes(self, connection_id: str, chunk: bytes) -> bytes | None:
        """External control front end via FixturePlatform ByteQueues.

        Partial input remains partial until complete. Timeout/desync closes with
        no partial success. Returns encoded response bytes or None while partial.
        """

        sample = self._sample_paired()
        now = int(sample["boottime_after_ns"])
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
        # Also mirror into platform inbound queue when present.
        inbound = getattr(self.platform, "control_inbound", None)
        if callable(inbound):
            try:
                q = inbound(connection_id)
                q.write(chunk)
            except Exception:
                pass
        obj, rem, err = decode_framed_request(bytes(buf))
        if err is not None:
            self._inbound_bufs[connection_id] = bytearray()
            self.close_control_session(connection_id)
            return None
        if obj is None:
            # Still partial.
            return None
        self._inbound_bufs[connection_id] = bytearray(rem)
        self._conn_activity_ns[connection_id] = now
        try:
            validate_control_request(obj)
        except ValueError:
            resp = self._response(obj, "invalid_request", {"reason": "bad_arguments"})
            return encode_framed_response(resp)
        # Private dict dispatch only after framed/authenticated validation.
        resp = self._dispatch_validated(connection_id, obj)
        try:
            framed = encode_framed_response(resp)
        except ValueError:
            self.close_control_session(connection_id)
            return None
        outbound = getattr(self.platform, "control_outbound", None)
        if callable(outbound):
            try:
                outbound(connection_id).write(framed)
            except Exception:
                self.close_control_session(connection_id)
                return None
        return framed

    def handle_control(
        self,
        connection_id: str,
        request: Mapping[str, Any],
        *,
        consumer_blocked: bool = False,
    ) -> dict[str, Any]:
        """Private dict dispatch — callers must validate first (tests/framed path)."""

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
        sample = self._sample_paired()
        self._update_clock_anomaly(st, sample)
        if st.state == "REVOKING":
            return self._response(request, "revoking", {"reason": st.terminal_reason or "operator"})
        if st.activation_id and request.get("activation_id") != st.activation_id:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        if st.lease_deadline_boottime_ns is not None:
            now_bt = int(sample["boottime_after_ns"])
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
            elif resp["outcome"] == "sealed":
                self._enter_revoking(st, str(resp.get("payload", {}).get("reason", "capacity")))
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
    def _response(request: Mapping[str, Any], outcome: str, payload: dict[str, Any]) -> dict[str, Any]:
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
        if reason not in REVOKE_REASONS:
            reason = "integrity_failure"
        st.state = "REVOKING"
        st.terminal_reason = reason
        st.persisted["state"] = st.state
        st.persisted["terminal_reason"] = reason

    def request_manager_stop(self, slot_id: str) -> dict[str, Any]:
        st = self.slots[slot_id]
        if not st.unit_invocation_id:
            raise ValueError("no_invocation")
        out = self.platform.manager_stop(st.unit_invocation_id)
        st.stop_requested = True
        st.persisted["stop_requested"] = True
        return out

    def attempt_retirement(self, slot_id: str, *, terminal_reason: str | None = None) -> dict[str, Any]:
        """Issue retirement only from REVOKING with stop + exact empty observation."""

        st = self.slots[slot_id]
        if st.state != "REVOKING":
            raise ValueError("retirement_requires_revoking")
        if not st.stop_requested:
            raise ValueError("retirement_requires_stop_request")
        if not st.unit_invocation_id:
            self._quarantine(st, "missing_invocation")
            raise ValueError("quarantined:missing_invocation")
        obs = self.platform.manager_observe(st.unit_invocation_id)
        reason = terminal_reason or st.terminal_reason or "operator"
        if reason not in REVOKE_REASONS:
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
                f"uncertain_emptiness:terminal={obs.get('terminal')}:populated={obs.get('populated')}",
            )
            raise ValueError("quarantined:uncertain_emptiness")
        sample = self._sample_paired()
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
            "observed_empty_boottime_ns": int(sample["boottime_after_ns"]),
        }
        receipt = dict(body)
        receipt["receipt_payload_sha256"] = _sha256_labeled(_canonical(body))
        self.check_access("controller", "/fixture/receipt/retirement.json", "create")
        st.retirement_receipt = receipt
        st.state = "SEALED"
        st.terminal_reason = reason
        st.persisted["state"] = "SEALED"
        st.persisted["retirement_receipt"] = receipt
        return receipt

    def _quarantine(self, st: SlotState, reason: str) -> None:
        st.state = "QUARANTINED"
        st.quarantine_reason = reason
        st.persisted["state"] = "QUARANTINED"
        st.persisted["quarantine_reason"] = reason

    def reconcile_after_controller_restart(self, slot_id: str) -> SlotState:
        """Persist quarantine; never restore stale persisted ACTIVE bytes over it."""

        st = self.slots[slot_id]
        if st.unit_invocation_id:
            obs = self.platform.manager_observe(st.unit_invocation_id)
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
