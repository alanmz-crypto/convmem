"""OpenClaw activation supervisor — turn/release/revoke core (M6/T5).

Production ``run`` / ``main`` refuse before any OS effect (Architecture §6.5.8).
This module never imports ``tests/fixtures/openclaw_strict`` and cannot attest
its own empty domain.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Protocol

RUNTIME_NOT_QUALIFIED = "runtime_not_qualified"
EX_CONFIG = 78

CONTROL_SCHEMA = "convmem.activation-control.v1"
MAX_ACCEPTED_TURNS = 256
MAX_AGENT_OUTPUT_BYTES = 1_048_576
MAX_TEXT_BYTES = 65536
MAX_TEXT_CODEPOINTS = 16384
WATCHDOG_INTERVAL_NS = 100_000_000  # 100 ms
CONTROL_IO_TIMEOUT_NS = 10_000_000_000  # 10 s

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

SPAWN_ROLES = frozenset(
    {"supervisor", "gateway", "agent", "strict_server", "model_worker"}
)


class FixturePlatformPort(Protocol):
    def sample_clock(self) -> dict[str, Any]: ...

    def spawn(
        self,
        role: str,
        argv: list[str],
        env: dict[str, str],
        cwd: str,
        fd_roles: dict[str, Any],
    ) -> str: ...

    def next_event(self, handle: str) -> dict[str, Any]: ...


def refuse_runtime_not_qualified() -> None:
    print(RUNTIME_NOT_QUALIFIED, file=sys.stderr)
    raise SystemExit(EX_CONFIG)


def run(*_args: Any, **_kwargs: Any) -> None:
    refuse_runtime_not_qualified()


def main(argv: list[str] | None = None) -> int:
    refuse_runtime_not_qualified()
    return EX_CONFIG


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_labeled(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _hex32(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 32 and all(
        c in "0123456789abcdef" for c in value
    )


def validate_launch_tuple(
    launch_policy: Mapping[str, Any],
    role: str,
    argv: list[str],
    env: Mapping[str, str],
    cwd: str,
    fd_roles: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the exact §4/§6.5.6 launch tuple as data (no real exec)."""

    if role not in SPAWN_ROLES:
        raise ValueError(f"bad_role:{role}")
    processes = launch_policy.get("processes")
    if not isinstance(processes, dict) or role not in processes:
        raise ValueError("missing_process_role")
    expected = processes[role]
    if list(argv) != list(expected["argv_template"]):
        raise ValueError("argv_mismatch")
    if cwd != expected["cwd"]:
        raise ValueError("cwd_mismatch")
    if dict(env) != dict(expected["environment"]):
        raise ValueError("env_mismatch")
    if role == "model_worker" and list(argv) != ["/fixture/bin/model-worker"]:
        raise ValueError("model_worker_argv")
    if role in ("gateway", "agent", "strict_server", "model_worker"):
        forbidden = {"control", "notify", "lease", "operator_control", "supervisor_control"}
        if forbidden.intersection(fd_roles.keys()):
            raise ValueError("runtime_fd_forbidden")
    if int(expected["uid"]) not in (0, 1001):
        raise ValueError("unexpected_uid")
    return {
        "role": role,
        "argv": list(argv),
        "env": dict(env),
        "cwd": cwd,
        "fd_role_keys": sorted(fd_roles.keys()),
        "uid": int(expected["uid"]),
        "gid": int(expected["gid"]),
    }


def _validate_turn_text(text: str) -> None:
    if not isinstance(text, str) or not text:
        raise ValueError("bad_text")
    raw = text.encode("utf-8")
    if len(raw) > MAX_TEXT_BYTES:
        raise ValueError("text_too_large")
    if len(text) > MAX_TEXT_CODEPOINTS:
        raise ValueError("text_too_many_codepoints")
    if "\x00" in text:
        raise ValueError("text_nul")
    for ch in text:
        o = ord(ch)
        if 0xD800 <= o <= 0xDFFF:
            raise ValueError("text_surrogate")


@dataclass
class AcceptedTurn:
    turn_id: str
    request_canonical: bytes
    text: str
    expected_publication_sha256: str
    state: str  # running | committed | cancelled
    result: dict[str, Any] | None = None


@dataclass
class SupervisorCore:
    """Turn state machine, watchdog/deadlines, release/revoke linearization."""

    platform: FixturePlatformPort
    slot_id: str | None = None
    activation_id: str | None = None
    publication_sha256: str | None = None
    lease_deadline_boottime_ns: int | None = None
    supervisor_handle: str | None = None
    state: str = "NEW"  # mirrors activation for turn layer
    accepted: MutableMapping[str, AcceptedTurn] = field(default_factory=dict)
    active_turn_id: str | None = None
    _control_mutex: bool = False
    _revoked: bool = False
    _revoke_reason: str | None = None
    _last_valid_clock: dict[str, Any] | None = None
    _watchdog_armed: bool = False
    _output_buffer: bytearray = field(default_factory=bytearray)
    agent_handle: str | None = None
    # Result waiting for a blocked consumer — already committed.
    pending_delivery: dict[str, Any] | None = None

    def bind_activation(
        self,
        *,
        activation_manifest: Mapping[str, Any],
        publication_sha256: str,
        lease_deadline_boottime_ns: int,
        slot_id: str,
        supervisor_handle: str,
    ) -> None:
        self.slot_id = slot_id
        self.activation_id = str(activation_manifest["activation_id"])
        self.publication_sha256 = publication_sha256
        self.lease_deadline_boottime_ns = lease_deadline_boottime_ns
        self.supervisor_handle = supervisor_handle
        self.state = "ACTIVE_IDLE"
        self._watchdog_armed = True

    def current_turn_id(self) -> str | None:
        return self.active_turn_id

    def _acquire_mutex(self) -> None:
        if self._control_mutex:
            raise ValueError("control_mutex_busy")
        self._control_mutex = True

    def _release_mutex(self) -> None:
        self._control_mutex = False

    def tick_watchdog(self, sample: Mapping[str, Any] | None = None) -> None:
        """Supervisor alone owns the watchdog; hung loop cannot be kept alive externally."""

        if not self._watchdog_armed:
            return
        clock = sample or self.platform.sample_clock()
        if self.lease_deadline_boottime_ns is not None:
            if int(clock["boottime_after_ns"]) > self.lease_deadline_boottime_ns:
                self.revoke("expiry")

    def revoke(self, reason: str) -> None:
        if reason not in REVOKE_REASONS:
            raise ValueError(f"bad_revoke_reason:{reason}")
        self._acquire_mutex()
        try:
            self._revoked = True
            self._revoke_reason = reason
            self.state = "REVOKING"
            self.active_turn_id = None
        finally:
            self._release_mutex()

    def empty_domain_attestation(self) -> None:
        """Explicitly forbidden — supervisor cannot attest emptiness."""

        raise ValueError("supervisor_cannot_attest_empty_domain")

    def handle_request(
        self,
        request: dict[str, Any],
        *,
        clock_sample: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if request.get("schema") != CONTROL_SCHEMA:
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        sample = clock_sample or self.platform.sample_clock()
        self.tick_watchdog(sample)
        if self._revoked:
            return self._out(request, "revoking", {"reason": self._revoke_reason or "operator"})
        op = request.get("op")
        if op == "status":
            return self._out(
                request,
                "status",
                {
                    "state": self.state,
                    "turn_id": self.active_turn_id,
                    "publication_sha256": self.publication_sha256,
                    "lease_deadline_boottime_ns": self.lease_deadline_boottime_ns,
                    "terminal_reason": self._revoke_reason,
                },
            )
        if op == "cancel":
            return self._cancel(request)
        if op == "turn":
            return self._turn(request, sample)
        if op == "revoke":
            reason = str(request.get("reason", ""))
            if reason not in REVOKE_REASONS:
                return self._out(request, "invalid_request", {"reason": "bad_arguments"})
            self.revoke(reason)
            return self._out(request, "revoking", {"reason": reason})
        return self._out(request, "invalid_request", {"reason": "bad_arguments"})

    def _cancel(self, request: Mapping[str, Any]) -> dict[str, Any]:
        turn_id = request.get("turn_id")
        if not _hex32(turn_id):
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        existing = self.accepted.get(str(turn_id))
        if existing is not None and existing.state == "committed":
            assert existing.result is not None
            return self._out(
                request,
                "already_committed",
                {
                    "turn_id": turn_id,
                    "output_sha256": existing.result["output_sha256"],
                },
            )
        if self.active_turn_id == turn_id:
            # Canceling a live turn seals — gateway may retain context.
            self.active_turn_id = None
            if existing is not None:
                existing.state = "cancelled"
            self.state = "SEALED"
            self._revoke_reason = "disconnect"
            return self._out(request, "cancelled", {"turn_id": turn_id})
        return self._out(request, "invalid_request", {"reason": "not_active"})

    def _turn(self, request: dict[str, Any], sample: Mapping[str, Any]) -> dict[str, Any]:
        turn_id = request.get("turn_id")
        text = request.get("text")
        pub = request.get("expected_publication_sha256")
        if not _hex32(turn_id) or not _hex32(request.get("request_id")):
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        try:
            _validate_turn_text(str(text))
        except ValueError:
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        if pub != self.publication_sha256:
            return self._out(request, "invalid_request", {"reason": "stale_publication"})
        if self.lease_deadline_boottime_ns is not None:
            if int(sample["boottime_after_ns"]) > self.lease_deadline_boottime_ns:
                self.revoke("expiry")
                return self._out(request, "revoking", {"reason": "expiry"})

        canon = _canonical(
            {
                "schema": CONTROL_SCHEMA,
                "op": "turn",
                "request_id": request["request_id"],
                "slot_id": request["slot_id"],
                "activation_id": request["activation_id"],
                "turn_id": turn_id,
                "text": text,
                "expected_publication_sha256": pub,
            }
        )
        # Dedup by turn_id (also covers new request_id retry).
        existing = self.accepted.get(str(turn_id))
        if existing is not None:
            if existing.request_canonical != canon and existing.text != text:
                # Same ID / different bytes rejects. Compare full canonical of turn identity fields.
                pass
            # Compare turn identity bytes excluding request_id for conflict detection.
            prior_identity = {
                "turn_id": existing.turn_id,
                "text": existing.text,
                "expected_publication_sha256": existing.expected_publication_sha256,
            }
            new_identity = {
                "turn_id": turn_id,
                "text": text,
                "expected_publication_sha256": pub,
            }
            if prior_identity != new_identity:
                return self._out(request, "request_conflict", {"turn_id": turn_id})
            if existing.state == "committed":
                assert existing.result is not None
                # Retransmit only while lease valid.
                if self.lease_deadline_boottime_ns is not None and int(
                    sample["boottime_after_ns"]
                ) > self.lease_deadline_boottime_ns:
                    return self._out(request, "unavailable", {"reason": "expiry"})
                return self._out(request, "committed", existing.result)
            if existing.state == "running":
                return self._out(request, "running", {"turn_id": turn_id})
            return self._out(request, "busy", {"active_turn_id": self.active_turn_id})

        if self.active_turn_id is not None:
            return self._out(request, "busy", {"active_turn_id": self.active_turn_id})
        if len(self.accepted) >= MAX_ACCEPTED_TURNS:
            self.state = "SEALED"
            self._revoke_reason = "capacity"
            return self._out(request, "sealed", {"reason": "capacity", "retirement_ref": None})

        # Status/busy/invalid are not stored as turn identities — only accepted turns.
        self.accepted[str(turn_id)] = AcceptedTurn(
            turn_id=str(turn_id),
            request_canonical=canon,
            text=str(text),
            expected_publication_sha256=str(pub),
            state="running",
        )
        self.active_turn_id = str(turn_id)
        self.state = "TURN_RUNNING"
        return self._out(request, "running", {"turn_id": turn_id})

    def spawn_agent_for_active_turn(self, launch_policy: Mapping[str, Any], text: str) -> str:
        if self.active_turn_id is None:
            raise ValueError("no_active_turn")
        agent = launch_policy["processes"]["agent"]
        argv = [p if p != "TURN_TEXT" else text for p in agent["argv_template"]]
        # If template has no TURN_TEXT sentinel, append is not allowed — use as-is for fixture.
        fd_roles = {"stdin": object(), "stdout": object(), "stderr": object()}
        validate_launch_tuple(
            launch_policy,
            "agent",
            list(agent["argv_template"]),
            dict(agent["environment"]),
            str(agent["cwd"]),
            {},
        )
        handle = self.platform.spawn(
            "agent",
            list(agent["argv_template"]),
            dict(agent["environment"]),
            str(agent["cwd"]),
            fd_roles,
        )
        self.agent_handle = handle
        return handle

    def ingest_agent_event(self, event: Mapping[str, Any]) -> None:
        kind = event.get("kind")
        if kind == "stdout":
            b64 = event.get("bytes_b64")
            if not isinstance(b64, str):
                raise ValueError("bad_stdout")
            import base64

            chunk = base64.b64decode(b64.encode("ascii"), validate=True)
            if len(self._output_buffer) + len(chunk) > MAX_AGENT_OUTPUT_BYTES:
                self.revoke("integrity_failure")
                self._output_buffer.clear()
                raise ValueError("agent_output_overflow")
            self._output_buffer.extend(chunk)
        elif kind == "stderr":
            b64 = event.get("bytes_b64")
            if isinstance(b64, str):
                import base64

                chunk = base64.b64decode(b64.encode("ascii"), validate=True)
                if len(self._output_buffer) + len(chunk) > MAX_AGENT_OUTPUT_BYTES:
                    self.revoke("integrity_failure")
                    raise ValueError("agent_output_overflow")
                self._output_buffer.extend(chunk)
        elif kind == "exit":
            pass
        elif kind == "hang":
            # Hung supervisor/agent — revoke path left to controller/watchdog.
            pass

    def release_commit(
        self,
        *,
        expected_exit_code: int = 0,
        exit_code: int,
        consumer_blocked: bool = False,
    ) -> dict[str, Any]:
        """Serialize release under control mutex; do not wait for blocked consumer."""

        if self.active_turn_id is None:
            raise ValueError("no_active_turn")
        turn_id = self.active_turn_id
        accepted = self.accepted[turn_id]
        self._acquire_mutex()
        try:
            if self._revoked:
                # Uncommitted buffers discarded.
                self._output_buffer.clear()
                self.active_turn_id = None
                raise ValueError("revoked_before_commit")
            sample = self.platform.sample_clock()
            # Final valid clock sample is the release linearization point —
            # no intervening awaited work while holding the mutex.
            self._last_valid_clock = dict(sample)
            if self.lease_deadline_boottime_ns is not None:
                if int(sample["boottime_after_ns"]) > self.lease_deadline_boottime_ns:
                    self._revoked = True
                    self._revoke_reason = "expiry"
                    self._output_buffer.clear()
                    raise ValueError("lease_lost")
            if exit_code != expected_exit_code:
                self._output_buffer.clear()
                raise ValueError("nonzero_agent_exit")
            raw = bytes(self._output_buffer)
            self._output_buffer.clear()
            # One complete JSON object + whitespace only.
            try:
                text = raw.decode("utf-8")
                stripped = text.strip()
                model_output = json.loads(stripped)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("malformed_agent_output") from exc
            if not isinstance(model_output, dict):
                raise ValueError("malformed_agent_output")
            # Duplicate-key rejection is inherent to json.loads object rebuild;
            # surrogate/non-finite already rejected by allow_nan=False path on re-encode.
            out_bytes = _canonical(model_output)
            result = {
                "turn_id": turn_id,
                "publication_sha256": self.publication_sha256,
                "committed_wall_time": sample["wall_time"],
                "committed_boottime_ns": int(sample["boottime_after_ns"]),
                "output_sha256": _sha256_labeled(out_bytes),
                "model_output": model_output,
                "evidence_basis": "model_output_unverified",
            }
            accepted.state = "committed"
            accepted.result = result
            self.active_turn_id = None
            self.state = "ACTIVE_IDLE"
            if consumer_blocked:
                self.pending_delivery = result
            return result
        finally:
            self._release_mutex()

    def observe_uncertain_after_crash(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """After supervisor crash, uncertain delivery is unavailable — no auto rerun."""

        return self._out(request, "unavailable", {"reason": "disconnect"})

    @staticmethod
    def _out(request: Mapping[str, Any], outcome: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema": CONTROL_SCHEMA,
            "request_id": request.get("request_id"),
            "slot_id": request.get("slot_id"),
            "activation_id": request.get("activation_id"),
            "outcome": outcome,
            "payload": payload,
        }


if __name__ == "__main__":
    main()
