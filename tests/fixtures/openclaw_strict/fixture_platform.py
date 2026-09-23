"""Parent §6.5.8 FixturePlatform — test-only injected ports (M6/T5).

Production controller/supervisor cores receive this object by construction.
They must never import this module. Harness alone advances clocks, schedules
events, and clears manager membership.
"""

from __future__ import annotations

import base64
import json
import struct
from dataclasses import dataclass, field
from typing import Any

# Logical peer policy (Architecture §6.5.8) — simulation identities only.
LOGICAL_PEERS: dict[str, tuple[int, int]] = {
    "operator": (1000, 1000),
    "controller": (0, 0),
    "supervisor": (0, 0),
    "runtime": (1001, 1001),
}

SPAWN_ROLES = frozenset(
    {"supervisor", "gateway", "agent", "strict_server", "model_worker"}
)
ACCESS_OPS = frozenset({"read", "create", "replace", "lock"})
EVENT_KINDS = frozenset({"ready", "stdout", "stderr", "exit", "hang"})

AGENT_SUCCESS_OBJECT = {"fixture": "protocol-only", "text": "synthetic answer"}
AGENT_SUCCESS_BYTES = json.dumps(
    AGENT_SUCCESS_OBJECT, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
).encode("utf-8")

MODEL_WORKER_ARGV = ["/fixture/bin/model-worker"]

MAX_REQUEST_FRAME = 131072
MAX_RESPONSE_FRAME = 2097152


def _b64(data: bytes | None) -> str | None:
    if data is None:
        return None
    return base64.b64encode(data).decode("ascii")


def encode_control_frame(obj: dict[str, Any]) -> bytes:
    """Length-prefixed UTF-8 canonical JSON (4-byte unsigned big-endian)."""

    body = json.dumps(
        obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(body) > MAX_REQUEST_FRAME:
        raise ValueError("request_frame_too_large")
    return struct.pack(">I", len(body)) + body


def try_decode_control_frame(buf: bytes) -> tuple[dict[str, Any] | None, bytes, str | None]:
    """Return (object|None, remainder, error_reason|None). Partial → (None, buf, None)."""

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
        # No trailing frames — discard remainder as protocol desync.
        return None, b"", "bad_frame"
    try:
        text = raw.decode("utf-8")
        obj = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, b"", "bad_frame"
    if not isinstance(obj, dict):
        return None, b"", "bad_frame"
    if len(obj) != len(set(obj)):
        return None, b"", "bad_frame"
    return obj, b"", None


@dataclass
class _HandleState:
    role: str
    argv: list[str]
    env: dict[str, str]
    cwd: str
    fd_roles: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    ready_seen: bool = False
    exited: bool = False
    hanging: bool = False


@dataclass
class _InvocationState:
    slot_id: str
    activation_id: str
    manager_boot_id: str
    unit_invocation_id: str
    containment_id: str
    members: set[str] = field(default_factory=set)
    model_work: set[str] = field(default_factory=set)
    stop_requested: bool = False
    # Harness-controlled observation overrides (None → derive from membership).
    force_terminal: bool | None = None
    force_populated: bool | None = None
    observe_boot_id: str | None = None
    observe_invocation_id: str | None = None
    observe_containment_id: str | None = None


class ByteQueue:
    """Bounded in-memory control/stdio queue with partial-frame support."""

    def __init__(self, name: str, *, max_bytes: int = MAX_RESPONSE_FRAME) -> None:
        self.name = name
        self.max_bytes = max_bytes
        self._buf = bytearray()
        self.blocked = False
        self.closed = False
        self.write_trace: list[int] = []

    def write(self, data: bytes) -> None:
        if self.closed:
            raise ValueError("queue_closed")
        if self.blocked:
            # Bytes are accepted into the queue (backpressure) but consumer waits.
            pass
        if len(self._buf) + len(data) > self.max_bytes:
            raise ValueError("queue_overflow")
        self._buf.extend(data)
        self.write_trace.append(len(data))

    def read(self, n: int | None = None) -> bytes:
        if self.blocked:
            return b""
        if n is None:
            out = bytes(self._buf)
            self._buf.clear()
            return out
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def peek(self) -> bytes:
        return bytes(self._buf)

    def __len__(self) -> int:
        return len(self._buf)


class FixturePlatform:
    """Exact §6.5.8 injected port. All clock/peer/access/spawn/manager ops trace here."""

    def __init__(
        self,
        *,
        boot_id: str = "boot-fixture-0001",
        auto_ready_on_supervisor_spawn: bool = True,
    ) -> None:
        self.trace: list[dict[str, Any]] = []
        self._boot_id = boot_id
        self._wall_time = "2026-09-21T00:00:00Z"
        self._boottime_ns = 1_000_000_000
        self._id_counter = 0
        self._peers: dict[str, dict[str, int]] = {}
        self._handles: dict[str, _HandleState] = {}
        self._invocations: dict[str, _InvocationState] = {}
        # Virtual access grants: (role, path_prefix, operation) → allow
        self._access_grants: set[tuple[str, str, str]] = set()
        self._install_default_access()
        # Control connections (connection_id → peer role name)
        self._connections: dict[str, str] = {}
        self.control_queues: dict[str, ByteQueue] = {}
        # Harness default: supervisor spawn gets one ready event so activate can
        # wait under the transition lock without real process notify.
        self.auto_ready_on_supervisor_spawn = auto_ready_on_supervisor_spawn

    def _install_default_access(self) -> None:
        private = (
            "/fixture/private/authority",
            "/fixture/private/grounding",
            "/fixture/private/citation",
            "/fixture/private/issuer",
            "/fixture/private/governance",
            "/fixture/private/control",
            "/fixture/private/qualification",
        )
        public = (
            "/fixture/public/manifest",
            "/fixture/public/projection",
            "/fixture/public/scope",
            "/fixture/public/registry",
            "/fixture/public/strict-config",
        )
        state = ("/fixture/state", "/fixture/tmp")
        control = ("/fixture/control", "/fixture/slot", "/fixture/receipt")
        for role in ("publisher", "qualifier", "operator"):
            for p in private:
                for op in ("read", "create", "replace", "lock"):
                    self._access_grants.add((role, p, op))
            for p in public:
                self._access_grants.add((role, p, "read"))
        for p in private:
            self._access_grants.add(("controller", p, "read"))
        for p in control:
            for op in ("read", "create", "replace", "lock"):
                self._access_grants.add(("controller", p, op))
        for p in public:
            self._access_grants.add(("supervisor", p, "read"))
        for p in ("/fixture/lease", "/fixture/control/supervisor"):
            for op in ("read", "create", "replace", "lock"):
                self._access_grants.add(("supervisor", p, op))
        for p in public:
            self._access_grants.add(("runtime", p, "read"))
        for p in state:
            for op in ("read", "create", "replace"):
                self._access_grants.add(("runtime", p, op))

    def _alloc_hex32(self) -> str:
        self._id_counter += 1
        return f"{self._id_counter:032x}"

    def _log(self, op: str, **fields: Any) -> None:
        rec = {"op": op, **fields}
        self.trace.append(rec)

    # --- harness clock / peer / membership controls ---

    def advance_wall(self, new_wall: str) -> None:
        self._wall_time = new_wall
        self._log("harness_advance_wall", wall_time=new_wall)

    def advance_boottime(self, delta_ns: int) -> None:
        self._boottime_ns += int(delta_ns)
        self._log("harness_advance_boottime", boottime_ns=self._boottime_ns)

    def suspend_resume(self, suspend_ns: int) -> None:
        # BOOTTIME includes suspended time.
        self._boottime_ns += int(suspend_ns)
        self._log("harness_suspend_resume", boottime_ns=self._boottime_ns)

    def new_boot(self, boot_id: str, *, wall_time: str | None = None) -> None:
        self._boot_id = boot_id
        self._boottime_ns = 0
        if wall_time is not None:
            self._wall_time = wall_time
        self._log("harness_new_boot", boot_id=boot_id, wall_time=self._wall_time)

    def set_peer(self, connection_id: str, role: str) -> None:
        if role not in LOGICAL_PEERS:
            raise ValueError(f"unknown_peer_role:{role}")
        uid, gid = LOGICAL_PEERS[role]
        self._peers[connection_id] = {"uid": uid, "gid": gid}
        self._connections[connection_id] = role
        self._log("harness_set_peer", connection_id=connection_id, role=role, uid=uid, gid=gid)

    def forge_peer(self, connection_id: str, uid: int, gid: int) -> None:
        """Negative-control: install a forged credential not in the logical table."""

        self._peers[connection_id] = {"uid": uid, "gid": gid}
        self._log("harness_forge_peer", connection_id=connection_id, uid=uid, gid=gid)

    def open_control_connection(self, connection_id: str, role: str = "operator") -> ByteQueue:
        self.set_peer(connection_id, role)
        q = ByteQueue(f"control:{connection_id}", max_bytes=MAX_RESPONSE_FRAME)
        self.control_queues[connection_id] = q
        self._log("harness_open_control", connection_id=connection_id, role=role)
        return q

    def schedule_event(self, handle: str, kind: str, *, bytes_b64: str | None = None, exit_code: int | None = None) -> None:
        if kind not in EVENT_KINDS:
            raise ValueError(f"bad_event_kind:{kind}")
        st = self._handles[handle]
        if kind == "hang":
            st.hanging = True
            self._log("harness_schedule_event", handle=handle, kind=kind)
            return
        ev = {
            "kind": kind,
            "bytes_b64": bytes_b64 if kind in ("stdout", "stderr") else None,
            "exit_code": exit_code if kind == "exit" else None,
        }
        st.events.append(ev)
        self._log("harness_schedule_event", handle=handle, kind=kind)

    def schedule_agent_success(self, handle: str) -> None:
        self.schedule_event(handle, "stdout", bytes_b64=_b64(AGENT_SUCCESS_BYTES))
        self.schedule_event(handle, "exit", exit_code=0)

    def remove_manager_member(self, invocation_id: str, member: str) -> None:
        inv = self._invocations[invocation_id]
        inv.members.discard(member)
        inv.model_work.discard(member)
        self._log("harness_remove_member", invocation_id=invocation_id, member=member)

    def add_detached_descendant(self, invocation_id: str, member: str) -> None:
        inv = self._invocations[invocation_id]
        inv.members.add(member)
        self._log("harness_add_detached", invocation_id=invocation_id, member=member)

    def add_outstanding_model_work(self, invocation_id: str, work_id: str) -> None:
        inv = self._invocations[invocation_id]
        inv.model_work.add(work_id)
        inv.members.add(work_id)
        self._log("harness_add_model_work", invocation_id=invocation_id, work_id=work_id)

    def force_observe(
        self,
        invocation_id: str,
        *,
        terminal: bool | None = None,
        populated: bool | None = None,
        manager_boot_id: str | None = None,
        unit_invocation_id: str | None = None,
        containment_id: str | None = None,
    ) -> None:
        inv = self._invocations[invocation_id]
        inv.force_terminal = terminal
        inv.force_populated = populated
        if manager_boot_id is not None:
            inv.observe_boot_id = manager_boot_id
        if unit_invocation_id is not None:
            inv.observe_invocation_id = unit_invocation_id
        if containment_id is not None:
            inv.observe_containment_id = containment_id
        self._log(
            "harness_force_observe",
            invocation_id=invocation_id,
            terminal=terminal,
            populated=populated,
        )

    def clear_all_members(self, invocation_id: str) -> None:
        inv = self._invocations[invocation_id]
        inv.members.clear()
        inv.model_work.clear()
        self._log("harness_clear_members", invocation_id=invocation_id)

    # --- fixed ports ---

    def sample_clock(self) -> dict[str, Any]:
        before = self._boottime_ns
        # Paired sample: before / wall / after with no real wait; harness may
        # have identical before/after unless it advances mid-sample.
        after = self._boottime_ns
        out = {
            "boot_id": self._boot_id,
            "wall_time": self._wall_time,
            "boottime_before_ns": before,
            "boottime_after_ns": after,
        }
        self._log("sample_clock", **out)
        return dict(out)

    def peer(self, connection_id: str) -> dict[str, int]:
        if connection_id not in self._peers:
            raise ValueError(f"unknown_connection:{connection_id}")
        out = dict(self._peers[connection_id])
        self._log("peer", connection_id=connection_id, **out)
        return out

    def access(self, role: str, path: str, operation: str) -> bool:
        if operation not in ACCESS_OPS:
            raise ValueError(f"bad_access_op:{operation}")
        if ".." in path or path != path.replace("//", "/"):
            allowed = False
        elif not path.startswith("/fixture/"):
            allowed = False
        else:
            allowed = False
            for r, prefix, op in self._access_grants:
                if r == role and operation == op and (
                    path == prefix or path.startswith(prefix.rstrip("/") + "/") or path.startswith(prefix)
                ):
                    allowed = True
                    break
            # Runtime must never read private qualification/issuer/governance/control.
            if role == "runtime" and any(
                path.startswith(p)
                for p in (
                    "/fixture/private/",
                    "/fixture/control/",
                    "/fixture/slot/",
                    "/fixture/receipt/",
                )
            ):
                allowed = False
        self._log("access", role=role, path=path, operation=operation, allowed=allowed)
        return allowed

    def spawn(
        self,
        role: str,
        argv: list[str],
        env: dict[str, str],
        cwd: str,
        fd_roles: dict[str, Any],
    ) -> str:
        if role not in SPAWN_ROLES:
            raise ValueError(f"bad_spawn_role:{role}")
        if role == "model_worker" and list(argv) != MODEL_WORKER_ARGV:
            raise ValueError("bad_model_worker_argv")
        # Runtime roles never receive control/notify/lease capabilities.
        if role in ("gateway", "agent", "strict_server", "model_worker"):
            forbidden = {"control", "notify", "lease", "operator_control", "supervisor_control"}
            if forbidden.intersection(fd_roles.keys()):
                raise ValueError("runtime_fd_role_forbidden")
        handle = self._alloc_hex32()
        st = _HandleState(
            role=role,
            argv=list(argv),
            env=dict(env),
            cwd=cwd,
            fd_roles=dict(fd_roles),
        )
        if role == "supervisor" and self.auto_ready_on_supervisor_spawn:
            st.events.append({"kind": "ready", "bytes_b64": None, "exit_code": None})
        self._handles[handle] = st
        self._log(
            "spawn",
            handle=handle,
            role=role,
            argv=list(argv),
            env=dict(env),
            cwd=cwd,
            fd_role_keys=sorted(fd_roles.keys()),
        )
        return handle

    def next_event(self, handle: str) -> dict[str, Any]:
        st = self._handles[handle]
        if st.hanging and not st.events:
            out = {"kind": "hang", "bytes_b64": None, "exit_code": None}
            self._log("next_event", handle=handle, **out)
            return out
        if not st.events:
            out = {"kind": "hang", "bytes_b64": None, "exit_code": None}
            self._log("next_event", handle=handle, **out)
            return out
        ev = st.events.pop(0)
        if ev["kind"] == "ready":
            if st.ready_seen:
                raise ValueError("ready_already_seen")
            st.ready_seen = True
        if ev["kind"] == "exit":
            st.exited = True
        self._log("next_event", handle=handle, **ev)
        return dict(ev)

    def manager_start(self, slot_id: str, activation_id: str) -> dict[str, str]:
        unit_invocation_id = self._alloc_hex32()
        containment_id = self._alloc_hex32()
        # Default logical descendants for a unit start.
        members = {
            f"proc:supervisor:{unit_invocation_id}",
            f"proc:gateway:{unit_invocation_id}",
            f"proc:agent:{unit_invocation_id}",
            f"proc:strict_server:{unit_invocation_id}",
            f"proc:model_worker:{unit_invocation_id}",
        }
        inv = _InvocationState(
            slot_id=slot_id,
            activation_id=activation_id,
            manager_boot_id=self._boot_id,
            unit_invocation_id=unit_invocation_id,
            containment_id=containment_id,
            members=set(members),
            model_work={f"proc:model_worker:{unit_invocation_id}"},
        )
        self._invocations[unit_invocation_id] = inv
        out = {
            "manager_boot_id": inv.manager_boot_id,
            "unit_invocation_id": unit_invocation_id,
            "containment_id": containment_id,
        }
        self._log("manager_start", slot_id=slot_id, activation_id=activation_id, **out)
        return dict(out)

    def manager_stop(self, invocation_id: str) -> dict[str, Any]:
        inv = self._invocations[invocation_id]
        inv.stop_requested = True
        # Acknowledgement never asserts emptiness.
        out = {"acknowledged": True, "unit_invocation_id": invocation_id}
        self._log("manager_stop", **out)
        return dict(out)

    def manager_observe(self, invocation_id: str) -> dict[str, Any]:
        inv = self._invocations[invocation_id]
        populated: bool | None
        if inv.force_populated is not None:
            populated = inv.force_populated
        elif inv.members or inv.model_work:
            populated = True
        else:
            populated = False
        if inv.force_terminal is not None:
            terminal = inv.force_terminal
        else:
            terminal = inv.stop_requested and populated is False
        out = {
            "manager_boot_id": inv.observe_boot_id or inv.manager_boot_id,
            "unit_invocation_id": inv.observe_invocation_id or inv.unit_invocation_id,
            "containment_id": inv.observe_containment_id or inv.containment_id,
            "terminal": terminal,
            "populated": populated,
        }
        self._log("manager_observe", requested_invocation_id=invocation_id, **out)
        return dict(out)

    def get_invocation(self, invocation_id: str) -> _InvocationState:
        return self._invocations[invocation_id]

    def port_ops(self) -> list[str]:
        return [t["op"] for t in self.trace if not str(t["op"]).startswith("harness_")]
