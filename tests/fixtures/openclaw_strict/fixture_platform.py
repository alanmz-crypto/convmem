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
CONTROL_IO_TIMEOUT_NS = 10_000_000_000  # scripted 10s receive/send deadline
MAX_CONTROL_CONNECTIONS = 8

# Sentinel: force_observe with no override vs explicit populated=null.
_OBSERVE_UNSET = object()


def _b64(data: bytes | None) -> str | None:
    if data is None:
        return None
    return base64.b64encode(data).decode("ascii")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate_key")
        out[key] = value
    return out


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite:{value}")


def decode_json_object(raw: bytes | str) -> dict[str, Any]:
    """Decode one UTF-8 JSON object; reject duplicate keys / nonfinite / surrogates."""

    text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else raw
    for ch in text:
        o = ord(ch)
        if 0xD800 <= o <= 0xDFFF:
            raise ValueError("surrogate")
    obj = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite,
    )
    if not isinstance(obj, dict):
        raise ValueError("not_object")
    return obj


def encode_control_frame(obj: dict[str, Any], *, max_body: int = MAX_REQUEST_FRAME) -> bytes:
    """Length-prefixed UTF-8 canonical JSON (4-byte unsigned big-endian)."""

    body = json.dumps(
        obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(body) > max_body:
        raise ValueError("frame_too_large")
    return struct.pack(">I", len(body)) + body


def encode_response_frame(obj: dict[str, Any]) -> bytes:
    return encode_control_frame(obj, max_body=MAX_RESPONSE_FRAME)


def try_decode_control_frame(buf: bytes) -> tuple[dict[str, Any] | None, bytes, str | None]:
    """Return (object|None, remainder, error_reason|None). Partial → (None, buf, None)."""

    header_size = 4
    if len(buf) < header_size:
        return None, buf, None
    frame_len = struct.unpack(">I", buf[:header_size])[0]
    if frame_len > MAX_REQUEST_FRAME:
        return None, b"", "bad_frame"
    if len(buf) < header_size + frame_len:
        return None, buf, None
    raw = buf[header_size : header_size + frame_len]
    rest = buf[header_size + frame_len :]
    if rest:
        # No trailing frames — discard remainder as protocol desync.
        return None, b"", "bad_frame"
    try:
        obj = decode_json_object(raw)
        # Canonical-bytes gate (same contract as production framed decode).
        canonical = json.dumps(
            obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        if canonical != raw:
            return None, b"", "bad_frame"
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None, b"", "bad_frame"
    return obj, b"", None


def _path_under_prefix(path: str, prefix: str) -> bool:
    """True when path equals prefix or is a path-component child of prefix."""

    if path == prefix:
        return True
    base = prefix.rstrip("/")
    return path.startswith(base + "/")


@dataclass
class _HandleState:  # pylint: disable=R0902  # attributes mirror handle observation fields
    role: str
    argv: list[str]
    env: dict[str, str]
    cwd: str
    fd_roles: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    ready_seen: bool = False
    exited: bool = False
    hanging: bool = False
    observed_exit_code: int | None = None


@dataclass
class _InvocationState:  # pylint: disable=R0902  # attributes mirror invocation observation fields
    slot_id: str
    activation_id: str
    manager_boot_id: str
    unit_invocation_id: str
    containment_id: str
    members: set[str] = field(default_factory=set)
    model_work: set[str] = field(default_factory=set)
    stop_requested: bool = False
    # Harness-controlled observation overrides (_OBSERVE_UNSET → derive).
    force_terminal: Any = _OBSERVE_UNSET
    force_populated: Any = _OBSERVE_UNSET
    observe_boot_id: str | None = None
    observe_invocation_id: str | None = None
    observe_containment_id: str | None = None


@dataclass
class _ControlConn:  # pylint: disable=R0902  # attributes mirror control-connection fields
    connection_id: str
    role: str
    inbound: "ByteQueue"
    outbound: "ByteQueue"
    opened_boottime_ns: int
    last_activity_boottime_ns: int
    closed: bool = False
    authenticated: bool = True


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
            # Bytes accepted into the queue (backpressure); consumer waits.
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

    def close(self) -> None:
        self.closed = True

    def __len__(self) -> int:
        return len(self._buf)


class FixturePlatform:  # pylint: disable=R0902,R0904  # attributes/methods mirror injected FixturePlatformPort surface
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
        self._connections: dict[str, str] = {}
        self.control_queues: dict[str, ByteQueue] = {}
        self._control_conns: dict[str, _ControlConn] = {}
        # Test-owned protected operator inventory (exact clock-review bytes).
        self.operator_inventory: set[bytes] = set()
        # Test-owned capability digests for cross-check (internal shapes).
        self.capability_digests: dict[str, str] = {}
        self.known_state_dirs: set[str] = set()
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
            "/fixture/private/operator-inventory",
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
        self._boottime_ns += int(suspend_ns)
        self._log("harness_suspend_resume", boottime_ns=self._boottime_ns)

    def new_boot(self, boot_id: str, *, wall_time: str | None = None) -> None:
        self._boot_id = boot_id
        self._boottime_ns = 0
        if wall_time is not None:
            self._wall_time = wall_time
        self._log("harness_new_boot", boot_id=boot_id, wall_time=self._wall_time)

    def install_operator_inventory_bytes(self, payload: bytes) -> None:
        self.operator_inventory.add(payload)
        self._log("harness_inventory_add", nbytes=len(payload))

    def set_capability_digest(self, name: str, digest: str) -> None:
        self.capability_digests[name] = digest

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
        if connection_id in self._control_conns and not self._control_conns[connection_id].closed:
            raise ValueError("duplicate_control_open")
        if self.active_control_connection_count() >= MAX_CONTROL_CONNECTIONS:
            raise ValueError("control_connection_capacity")
        self.set_peer(connection_id, role)
        inbound = ByteQueue(f"control-in:{connection_id}", max_bytes=MAX_REQUEST_FRAME)
        outbound = ByteQueue(f"control-out:{connection_id}", max_bytes=MAX_RESPONSE_FRAME)
        now = self._boottime_ns
        self._control_conns[connection_id] = _ControlConn(
            connection_id=connection_id,
            role=role,
            inbound=inbound,
            outbound=outbound,
            opened_boottime_ns=now,
            last_activity_boottime_ns=now,
        )
        # Legacy alias: single queue name maps to outbound (responses).
        self.control_queues[connection_id] = outbound
        self._log("harness_open_control", connection_id=connection_id, role=role)
        return outbound

    def control_inbound(self, connection_id: str) -> ByteQueue:
        return self._control_conns[connection_id].inbound

    def control_outbound(self, connection_id: str) -> ByteQueue:
        return self._control_conns[connection_id].outbound

    def close_control_connection(self, connection_id: str) -> None:
        conn = self._control_conns.pop(connection_id, None)
        if conn is None:
            return
        conn.closed = True
        conn.inbound.close()
        conn.outbound.close()
        self.control_queues.pop(connection_id, None)
        self._log("harness_close_control", connection_id=connection_id)

    def active_control_connection_count(self) -> int:
        return sum(1 for c in self._control_conns.values() if not c.closed)

    def schedule_event(
        self,
        handle: str,
        kind: str,
        *,
        bytes_b64: str | None = None,
        exit_code: int | None = None,
    ) -> None:
        if kind not in EVENT_KINDS:
            raise ValueError(f"bad_event_kind:{kind}")
        st = self._handles[handle]
        if kind == "hang":
            st.hanging = True
            self._log("harness_schedule_event", handle=handle, kind=kind)
            return
        if kind in ("stdout", "stderr"):
            if bytes_b64 is None or not isinstance(bytes_b64, str):
                raise ValueError("bytes_b64_required")
            # Canonical base64 only.
            try:
                base64.b64decode(bytes_b64.encode("ascii"), validate=True)
            except Exception as exc:
                raise ValueError("bad_base64") from exc
        if kind == "exit" and not isinstance(exit_code, int):
            raise ValueError("exit_code_required")
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
        terminal: Any = _OBSERVE_UNSET,
        populated: Any = _OBSERVE_UNSET,
        manager_boot_id: str | None = None,
        unit_invocation_id: str | None = None,
        containment_id: str | None = None,
    ) -> None:
        """Override observe fields. Omit args to leave unset; pass populated=None for unknown."""

        inv = self._invocations[invocation_id]
        if terminal is not _OBSERVE_UNSET:
            inv.force_terminal = terminal
        if populated is not _OBSERVE_UNSET:
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
            terminal=("unset" if terminal is _OBSERVE_UNSET else terminal),
            populated=("unset" if populated is _OBSERVE_UNSET else populated),
        )

    def clear_all_members(self, invocation_id: str) -> None:
        inv = self._invocations[invocation_id]
        inv.members.clear()
        inv.model_work.clear()
        self._log("harness_clear_members", invocation_id=invocation_id)

    def preload_accepted_turn_history(
        self,
        *,
        count: int,
        turn_state: str = "committed",
    ) -> list[dict[str, Any]]:
        """Independent fixture preload of completed/cancelled turn identities (capacity tests)."""

        records: list[dict[str, Any]] = []
        for i in range(count):
            tid = f"{(i + 1):032x}"
            records.append(
                {
                    "turn_id": tid,
                    "request_id": f"{(i + 1000):032x}",
                    "text": f"preload-{i}",
                    "state": turn_state,
                    "expected_publication_sha256": "sha256:" + ("a" * 64),
                }
            )
        self._log("harness_preload_turns", count=count, turn_state=turn_state)
        return records

    # --- fixed ports ---

    def sample_clock(self) -> dict[str, Any]:
        before = self._boottime_ns
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
        if ".." in path.split("/") or "//" in path:
            allowed = False
        elif not path.startswith("/fixture/"):
            allowed = False
        else:
            allowed = False
            for r, prefix, op in self._access_grants:
                if r == role and operation == op and _path_under_prefix(path, prefix):
                    allowed = True
                    break
            if role == "runtime" and any(
                _path_under_prefix(path, p)
                for p in (
                    "/fixture/private",
                    "/fixture/control",
                    "/fixture/slot",
                    "/fixture/receipt",
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
        if st.exited:
            raise ValueError("exit_already_terminal")
        if st.hanging and not st.events:
            out = {"kind": "hang", "bytes_b64": None, "exit_code": None}
            self._log("next_event", handle=handle, **out)
            return out
        if not st.events:
            out = {"kind": "hang", "bytes_b64": None, "exit_code": None}
            self._log("next_event", handle=handle, **out)
            return out
        ev = st.events.pop(0)
        kind = ev["kind"]
        if kind not in EVENT_KINDS:
            raise ValueError("bad_event_kind")
        if kind == "ready":
            if st.ready_seen:
                raise ValueError("ready_already_seen")
            if ev.get("bytes_b64") is not None or ev.get("exit_code") is not None:
                raise ValueError("ready_shape")
            st.ready_seen = True
        elif kind in ("stdout", "stderr"):
            if not isinstance(ev.get("bytes_b64"), str) or ev.get("exit_code") is not None:
                raise ValueError("stdio_shape")
            try:
                base64.b64decode(ev["bytes_b64"].encode("ascii"), validate=True)
            except Exception as exc:
                raise ValueError("bad_base64") from exc
        elif kind == "exit":
            if ev.get("bytes_b64") is not None or not isinstance(ev.get("exit_code"), int):
                raise ValueError("exit_shape")
            st.exited = True
            st.observed_exit_code = int(ev["exit_code"])
        elif kind == "hang":
            if ev.get("bytes_b64") is not None or ev.get("exit_code") is not None:
                raise ValueError("hang_shape")
        self._log("next_event", handle=handle, **ev)
        return dict(ev)

    def observed_exit_code(self, handle: str) -> int | None:
        return self._handles[handle].observed_exit_code

    def manager_start(self, slot_id: str, activation_id: str) -> dict[str, str]:
        unit_invocation_id = self._alloc_hex32()
        containment_id = self._alloc_hex32()
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
        out = {"acknowledged": True, "unit_invocation_id": invocation_id}
        self._log("manager_stop", **out)
        return dict(out)

    def manager_observe(self, invocation_id: str) -> dict[str, Any]:
        inv = self._invocations[invocation_id]
        if inv.force_populated is not _OBSERVE_UNSET:
            populated = inv.force_populated
        elif inv.members or inv.model_work:
            populated = True
        else:
            populated = False
        if inv.force_terminal is not _OBSERVE_UNSET:
            terminal = inv.force_terminal
        else:
            terminal = bool(inv.stop_requested and populated is False)
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

    def control_conn(self, connection_id: str) -> _ControlConn:
        return self._control_conns[connection_id]

    def port_ops(self) -> list[str]:
        return [t["op"] for t in self.trace if not str(t["op"]).startswith("harness_")]
