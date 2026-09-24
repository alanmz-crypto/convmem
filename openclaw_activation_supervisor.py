"""OpenClaw activation supervisor — turn/release/revoke core (M6/T5).

Production ``run`` / ``main`` refuse before any OS effect (Architecture §6.5.8).
This module never imports ``tests/fixtures/openclaw_strict`` and cannot attest
its own empty domain.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Protocol, cast

RUNTIME_NOT_QUALIFIED = "runtime_not_qualified"
EX_CONFIG = 78

CONTROL_SCHEMA = "convmem.activation-control.v1"
MAX_ACCEPTED_TURNS = 256
MAX_AGENT_OUTPUT_BYTES = 1_048_576
MAX_TEXT_BYTES = 65536
MAX_TEXT_CODEPOINTS = 16384
WATCHDOG_INTERVAL_NS = 100_000_000  # 100 ms


def _supervisor_revoke_reasons() -> frozenset[str]:
    """External revoke reasons (inventory blob — distinct from controller helper)."""

    return frozenset(line for line in """operator
publish
scope_change
expiry
clock_anomaly
integrity_failure
disconnect
shutdown""".splitlines() if line)


REVOKE_REASONS = _supervisor_revoke_reasons()

SPAWN_ROLES = frozenset({"supervisor", "gateway", "agent", "strict_server", "model_worker"})


def _port_map_get(mapping: object, key: str) -> Any:
    """Read injected-port mapping field; Protocol ellipsis makes value look unsubscriptable."""
    # pylint: disable=E1136  # runtime mapping from FixturePlatformPort; stub body is ellipsis
    return cast(Mapping[str, Any], mapping)[key]


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

    def advance_boottime(self, delta_ns: int) -> None: ...


def refuse_runtime_not_qualified() -> None:
    """Supervisor production refusal before any OS effect."""

    sys.stderr.write(f"{RUNTIME_NOT_QUALIFIED}\n")
    raise SystemExit(EX_CONFIG)


def run(*_args: Any, **_kwargs: Any) -> None:
    refuse_runtime_not_qualified()


def main(argv: list[str] | None = None) -> int:
    # pylint: disable=W0613  # public CLI argv retained for interface parity
    del argv
    refuse_runtime_not_qualified()
    return EX_CONFIG


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_labeled(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _hex32(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 32 and all(c in "0123456789abcdef" for c in value)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate_key")
        out[key] = value
    return out


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"nonfinite:{value}")


# pylint: disable=R0917  # frozen public launch-tuple arity (positional callers in tests)
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
    expected_argv = list(expected["argv_template"])
    if role == "agent" and "TURN_TEXT" in expected_argv:
        if len(argv) != len(expected_argv):
            raise ValueError("argv_mismatch")
        for actual, templ in zip(argv, expected_argv):
            if templ == "TURN_TEXT":
                continue
            if actual != templ:
                raise ValueError("argv_mismatch")
        if sum(1 for p in expected_argv if p == "TURN_TEXT") != 1:
            raise ValueError("turn_text_count")
    elif list(argv) != expected_argv:
        raise ValueError("argv_mismatch")
    if cwd != expected["cwd"]:
        raise ValueError("cwd_mismatch")
    if dict(env) != dict(expected["environment"]):
        raise ValueError("env_mismatch")
    if role == "model_worker" and list(argv) != ["/fixture/bin/model-worker"]:
        raise ValueError("model_worker_argv")
    # Always compare fd roles exactly — empty policy list is not unconstrained.
    policy_fds = list(expected["inherited_fd_roles"])
    if sorted(fd_roles.keys()) != sorted(policy_fds):
        raise ValueError("fd_roles_mismatch")
    if role in ("gateway", "agent", "strict_server", "model_worker"):
        forbidden = {"control", "notify", "lease", "operator_control", "supervisor_control"}
        if forbidden.intersection(fd_roles.keys()):
            raise ValueError("runtime_fd_forbidden")
        if forbidden.intersection(policy_fds):
            raise ValueError("runtime_fd_forbidden")
    if int(expected["uid"]) not in (0, 1001):
        raise ValueError("unexpected_uid")
    if int(expected["gid"]) != int(expected["uid"]):
        raise ValueError("uid_gid_mismatch")
    return {
        "role": role,
        "argv": list(argv),
        "env": dict(env),
        "cwd": cwd,
        "fd_role_keys": sorted(fd_roles.keys()),
        "uid": int(expected["uid"]),
        "gid": int(expected["gid"]),
    }


def _validate_turn_text(text: Any) -> None:
    # Do not coerce non-string text.
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


def _parse_complete_stdout_object(raw: bytes) -> dict[str, Any]:
    """One complete JSON object + whitespace only; reject duplicates/nonfinite/surrogates."""

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("malformed_agent_output") from exc
    for ch in text:
        o = ord(ch)
        if 0xD800 <= o <= 0xDFFF:
            raise ValueError("surrogate")
    stripped = text.lstrip()
    if not stripped:
        raise ValueError("malformed_agent_output")
    try:
        decoder = json.JSONDecoder(
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
        model_output, idx = decoder.raw_decode(stripped)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError("malformed_agent_output") from exc
    trailing = stripped[idx:]
    if trailing.strip():
        raise ValueError("trailing_objects")
    if not isinstance(model_output, dict):
        raise ValueError("malformed_agent_output")
    return model_output


@dataclass
# pylint: disable=R0902  # attributes mirror accepted-turn receipt fields
class AcceptedTurn:
    turn_id: str
    request_id: str
    request_canonical: bytes
    text: str
    expected_publication_sha256: str
    slot_id: str
    activation_id: str
    state: str  # running | committed | cancelled
    result: dict[str, Any] | None = None


@dataclass
# pylint: disable=R0902  # attributes mirror supervisor activation/turn bookkeeping fields
class SupervisorCore:
    """Turn state machine, watchdog/deadlines, release/revoke linearization."""

    platform: FixturePlatformPort
    slot_id: str | None = None
    activation_id: str | None = None
    publication_sha256: str | None = None
    lease_deadline_boottime_ns: int | None = None
    supervisor_handle: str | None = None
    state: str = "NEW"
    accepted: MutableMapping[str, AcceptedTurn] = field(default_factory=dict)
    # Accepted request_id → canonical request bytes (conflict if bytes change).
    accepted_request_ids: MutableMapping[str, bytes] = field(default_factory=dict)
    # Turn identity key → turn_id for new-request_id same-identity replay.
    turn_identity_index: MutableMapping[str, str] = field(default_factory=dict)
    active_turn_id: str | None = None
    _control_mutex: bool = False
    _revoked: bool = False
    _revoke_reason: str | None = None
    _internal_terminal: str | None = None
    _last_valid_clock: dict[str, Any] | None = None
    _watchdog_armed: bool = False
    _watchdog_samples: list[dict[str, Any]] = field(default_factory=list)
    _stdout_buffer: bytearray = field(default_factory=bytearray)
    _stderr_buffer: bytearray = field(default_factory=bytearray)
    agent_handle: str | None = None
    _observed_exit_code: int | None = None
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
        self._internal_terminal = None
        sample: dict[str, Any] = cast(dict[str, Any], self.platform.sample_clock())
        self._watchdog_samples.append(dict(sample))

    def reset_for_new_activation(self) -> None:
        """Fresh activation — no old-session retransmission or turn resume."""

        self.accepted.clear()
        self.accepted_request_ids.clear()
        self.turn_identity_index.clear()
        self.active_turn_id = None
        self._revoked = False
        self._revoke_reason = None
        self._internal_terminal = None
        self._stdout_buffer.clear()
        self._stderr_buffer.clear()
        self.agent_handle = None
        self._observed_exit_code = None
        self.pending_delivery = None
        self.state = "NEW"
        self._watchdog_armed = False
        self._watchdog_samples.clear()
        self.supervisor_handle = None
        self.activation_id = None
        self.publication_sha256 = None
        self.lease_deadline_boottime_ns = None
        self.slot_id = None

    def preload_completed_history(self, records: list[Mapping[str, Any]]) -> None:
        """Independent fixture preload consistent with parent accepted-turn semantics."""

        for rec in records:
            tid = str(rec["turn_id"])
            rid = str(rec["request_id"])
            text = str(rec["text"])
            pub = str(rec["expected_publication_sha256"])
            slot_id = str(rec.get("slot_id", self.slot_id))
            activation_id = str(rec.get("activation_id", self.activation_id))
            canon = _canonical(
                {
                    "schema": CONTROL_SCHEMA,
                    "op": "turn",
                    "request_id": rid,
                    "slot_id": slot_id,
                    "activation_id": activation_id,
                    "turn_id": tid,
                    "text": text,
                    "expected_publication_sha256": pub,
                }
            )
            self.accepted[tid] = AcceptedTurn(
                turn_id=tid,
                request_id=rid,
                request_canonical=canon,
                text=text,
                expected_publication_sha256=pub,
                slot_id=slot_id,
                activation_id=activation_id,
                state=str(rec.get("state", "committed")),
                result=None,
            )
            self.accepted_request_ids[rid] = canon
            self.turn_identity_index[self._identity_key(tid, text, pub)] = tid

    @staticmethod
    def _identity_key(turn_id: str, text: str, pub: str) -> str:
        return f"{turn_id}|{pub}|{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

    def current_turn_id(self) -> str | None:
        return self.active_turn_id

    def _acquire_mutex(self) -> None:
        if self._control_mutex:
            raise ValueError("control_mutex_busy")
        self._control_mutex = True

    def _release_mutex(self) -> None:
        self._control_mutex = False

    def _enter_revoking_internal(self, reason: str, *, internal: str | None = None) -> None:
        self._revoked = True
        if reason in REVOKE_REASONS:
            self._revoke_reason = reason
        else:
            self._revoke_reason = "integrity_failure"
        self._internal_terminal = internal or reason
        self.state = "REVOKING"
        self.active_turn_id = None
        self._stdout_buffer.clear()
        self._stderr_buffer.clear()

    def tick_watchdog(self, sample: Mapping[str, Any] | None = None) -> None:
        if not self._watchdog_armed:
            return
        clock = sample or cast(dict[str, Any], self.platform.sample_clock())
        now = int(clock["boottime_after_ns"])
        if self.state == "TURN_RUNNING" and self._watchdog_samples:
            prev = int(self._watchdog_samples[-1]["boottime_after_ns"])
            if now - prev > WATCHDOG_INTERVAL_NS:
                self.revoke("integrity_failure")
                self._internal_terminal = "watchdog_interval_skipped"
                return
        self._watchdog_samples.append(dict(clock))
        if self.lease_deadline_boottime_ns is not None:
            if now > self.lease_deadline_boottime_ns:
                self.revoke("expiry")

    def _assert_watchdog_coverage(self) -> None:
        """Enforce <=100ms scripted-work sampling during a live turn."""

        if not self._watchdog_armed:
            raise ValueError("watchdog_not_armed")
        if not self._watchdog_samples:
            raise ValueError("watchdog_interval_skipped")
        samples = [int(s["boottime_after_ns"]) for s in self._watchdog_samples]
        for earlier, later in zip(samples, samples[1:]):
            if later - earlier > WATCHDOG_INTERVAL_NS:
                self._enter_revoking_internal("integrity_failure", internal="watchdog_interval_skipped")
                raise ValueError("watchdog_interval_skipped")
        now = int(_port_map_get(cast(dict[str, Any], self.platform.sample_clock()), "boottime_after_ns"))
        if now - samples[-1] > WATCHDOG_INTERVAL_NS:
            self._enter_revoking_internal("integrity_failure", internal="watchdog_interval_skipped")
            raise ValueError("watchdog_interval_skipped")

    def script_work_intervals(self, count: int = 1) -> None:
        """Advance scripted clock by <=100ms intervals and sample — no real wait."""

        for _ in range(count):
            adv = getattr(self.platform, "advance_boottime", None)
            if callable(adv):
                adv(WATCHDOG_INTERVAL_NS)
            self.tick_watchdog()

    def revoke(self, reason: str) -> None:
        if reason not in REVOKE_REASONS:
            raise ValueError(f"bad_revoke_reason:{reason}")
        self._acquire_mutex()
        try:
            self._enter_revoking_internal(reason)
        finally:
            self._release_mutex()

    def empty_domain_attestation(self) -> None:
        raise ValueError("supervisor_cannot_attest_empty_domain")

    def handle_request(
        self,
        request: dict[str, Any],
        *,
        clock_sample: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if request.get("schema") != CONTROL_SCHEMA:
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        sample = clock_sample or cast(dict[str, Any], self.platform.sample_clock())
        self.tick_watchdog(sample)
        op = request.get("op")
        if self._revoked:
            # Identity retries for cancelled/committed turns must not become busy/revoking.
            if op == "turn":
                replay = self._replay_accepted_turn(request, sample)
                if replay is not None:
                    return replay
            return self._out(request, "revoking", {"reason": self._revoke_reason or "operator"})
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

    def _replay_accepted_turn(self, request: Mapping[str, Any], sample: Mapping[str, Any]) -> dict[str, Any] | None:
        turn_id = request.get("turn_id")
        text = request.get("text")
        pub = request.get("expected_publication_sha256")
        request_id = request.get("request_id")
        if not _hex32(turn_id) or not isinstance(text, str) or not _hex32(request_id):
            return None
        identity_key = self._identity_key(str(turn_id), str(text), str(pub))
        existing_tid = self.turn_identity_index.get(identity_key)
        existing = self.accepted.get(str(turn_id))
        if existing_tid is not None and existing_tid == turn_id:
            existing = self.accepted[existing_tid]
        if existing is None:
            return None
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
            if (
                self.lease_deadline_boottime_ns is not None
                and int(_port_map_get(sample, "boottime_after_ns")) > self.lease_deadline_boottime_ns
            ):
                return self._out(request, "unavailable", {"reason": "expiry"})
            return self._out(request, "committed", existing.result)
        if existing.state == "cancelled":
            return self._out(request, "cancelled", {"turn_id": turn_id})
        if existing.state == "running":
            return self._out(request, "running", {"turn_id": turn_id})
        return None

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
            # Cancel live turn → REVOKING (outer SEALED only after manager proof).
            self.active_turn_id = None
            if existing is not None:
                existing.state = "cancelled"
            self.state = "REVOKING"
            self._revoke_reason = "disconnect"
            self._revoked = True
            self._stdout_buffer.clear()
            self._stderr_buffer.clear()
            return self._out(request, "cancelled", {"turn_id": turn_id})
        return self._out(request, "invalid_request", {"reason": "not_active"})

    def _turn(self, request: dict[str, Any], sample: Mapping[str, Any]) -> dict[str, Any]:
        # pylint: disable=R0911  # closed control-protocol outcome surface
        turn_id = request.get("turn_id")
        text = request.get("text")
        pub = request.get("expected_publication_sha256")
        request_id = request.get("request_id")
        if not _hex32(turn_id) or not _hex32(request_id):
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        try:
            _validate_turn_text(text)
        except ValueError:
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})
        if pub != self.publication_sha256:
            return self._out(request, "invalid_request", {"reason": "stale_publication"})
        if self.lease_deadline_boottime_ns is not None:
            if int(_port_map_get(sample, "boottime_after_ns")) > self.lease_deadline_boottime_ns:
                self.revoke("expiry")
                return self._out(request, "revoking", {"reason": "expiry"})

        canon = _canonical(
            {
                "schema": CONTROL_SCHEMA,
                "op": "turn",
                "request_id": request_id,
                "slot_id": request["slot_id"],
                "activation_id": request["activation_id"],
                "turn_id": turn_id,
                "text": text,
                "expected_publication_sha256": pub,
            }
        )
        # Repeated accepted request_id with changed bytes rejects.
        prior_req = self.accepted_request_ids.get(str(request_id))
        if prior_req is not None and prior_req != canon:
            return self._out(request, "request_conflict", {"turn_id": turn_id})

        identity_key = self._identity_key(str(turn_id), str(text), str(pub))
        # New request_id same turn identity → return existing state.
        existing_tid = self.turn_identity_index.get(identity_key)
        if existing_tid is not None and existing_tid == turn_id:
            existing = self.accepted[existing_tid]
            if str(request_id) != existing.request_id:
                if existing.state == "committed":
                    assert existing.result is not None
                    if (
                        self.lease_deadline_boottime_ns is not None
                        and int(_port_map_get(sample, "boottime_after_ns")) > self.lease_deadline_boottime_ns
                    ):
                        return self._out(request, "unavailable", {"reason": "expiry"})
                    return self._out(request, "committed", existing.result)
                if existing.state == "running":
                    return self._out(request, "running", {"turn_id": turn_id})
                if existing.state == "cancelled":
                    return self._out(request, "cancelled", {"turn_id": turn_id})

        existing = self.accepted.get(str(turn_id))
        if existing is not None:
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
                if (
                    self.lease_deadline_boottime_ns is not None
                    and int(_port_map_get(sample, "boottime_after_ns")) > self.lease_deadline_boottime_ns
                ):
                    return self._out(request, "unavailable", {"reason": "expiry"})
                return self._out(request, "committed", existing.result)
            if existing.state == "running":
                return self._out(request, "running", {"turn_id": turn_id})
            if existing.state == "cancelled":
                return self._out(request, "cancelled", {"turn_id": turn_id})
            return self._out(request, "busy", {"active_turn_id": self.active_turn_id})

        if self.active_turn_id is not None:
            return self._out(request, "busy", {"active_turn_id": self.active_turn_id})
        if len(self.accepted) >= MAX_ACCEPTED_TURNS:
            # Capacity is internal terminal reasoning — REVOKING, never SEALED+null.
            self._enter_revoking_internal("integrity_failure", internal="capacity")
            return self._out(request, "unavailable", {"reason": "capacity"})

        if self.slot_id is None or self.activation_id is None:
            return self._out(request, "unavailable", {"reason": "not_active"})
        if request.get("slot_id") != self.slot_id or request.get("activation_id") != self.activation_id:
            return self._out(request, "invalid_request", {"reason": "bad_arguments"})

        self.accepted[str(turn_id)] = AcceptedTurn(
            turn_id=str(turn_id),
            request_id=str(request_id),
            request_canonical=canon,
            text=str(text),
            expected_publication_sha256=str(pub),
            slot_id=str(self.slot_id),
            activation_id=str(self.activation_id),
            state="running",
        )
        self.accepted_request_ids[str(request_id)] = canon
        self.turn_identity_index[identity_key] = str(turn_id)
        self.active_turn_id = str(turn_id)
        self.state = "TURN_RUNNING"
        return self._out(request, "running", {"turn_id": turn_id})

    def spawn_agent_for_active_turn(self, launch_policy: Mapping[str, Any], text: str) -> str:
        if self.active_turn_id is None:
            raise ValueError("no_active_turn")
        self._assert_watchdog_coverage()
        agent = launch_policy["processes"]["agent"]
        template = list(agent["argv_template"])
        # Literal TURN_TEXT substitution only — never mutate the launch policy.
        argv = [text if p == "TURN_TEXT" else p for p in template]
        env = dict(agent["environment"])
        cwd = str(agent["cwd"])
        fd_roles: dict[str, Any] = {role: object() for role in agent["inherited_fd_roles"]}
        validate_launch_tuple(launch_policy, "agent", argv, env, cwd, fd_roles)
        handle = cast(str, self.platform.spawn("agent", argv, env, cwd, fd_roles))
        self.agent_handle = handle
        self._observed_exit_code = None
        self._stdout_buffer.clear()
        self._stderr_buffer.clear()
        return handle

    def ingest_agent_event(self, event: Mapping[str, Any]) -> None:
        try:
            self._ingest_agent_event_body(event)
        except ValueError:
            # Malformed/partial child output must not leave the activation live.
            if not self._revoked and (self.state == "TURN_RUNNING" or self.active_turn_id is not None):
                self._enter_revoking_internal("integrity_failure")
            raise

    def _ingest_agent_event_body(self, event: Mapping[str, Any]) -> None:
        kind = event.get("kind")
        if kind not in ("ready", "stdout", "stderr", "exit", "hang"):
            raise ValueError("bad_event_kind")
        if self.state == "TURN_RUNNING":
            self.tick_watchdog()
        if kind == "stdout":
            b64 = event.get("bytes_b64")
            if not isinstance(b64, str) or event.get("exit_code") is not None:
                raise ValueError("bad_stdout")
            try:
                chunk = base64.b64decode(b64.encode("ascii"), validate=True)
            except Exception as exc:
                raise ValueError("bad_base64") from exc
            if len(self._stdout_buffer) + len(self._stderr_buffer) + len(chunk) > MAX_AGENT_OUTPUT_BYTES:
                self.revoke("integrity_failure")
                self._stdout_buffer.clear()
                raise ValueError("agent_output_overflow")
            self._stdout_buffer.extend(chunk)
        elif kind == "stderr":
            b64 = event.get("bytes_b64")
            if not isinstance(b64, str) or event.get("exit_code") is not None:
                raise ValueError("bad_stderr")
            try:
                chunk = base64.b64decode(b64.encode("ascii"), validate=True)
            except Exception as exc:
                raise ValueError("bad_base64") from exc
            if len(self._stdout_buffer) + len(self._stderr_buffer) + len(chunk) > MAX_AGENT_OUTPUT_BYTES:
                self.revoke("integrity_failure")
                raise ValueError("agent_output_overflow")
            self._stderr_buffer.extend(chunk)
        elif kind == "exit":
            # pylint: disable=C0123  # exact type identity; not isinstance/__class__
            if event.get("bytes_b64") is not None or type(event.get("exit_code")) is not int:
                raise ValueError("bad_exit")
            code = int(event["exit_code"])
            self._observed_exit_code = code
            if code != 0:
                self._enter_revoking_internal("integrity_failure")
                self._stdout_buffer.clear()
                self._stderr_buffer.clear()
        elif kind == "hang":
            if event.get("bytes_b64") is not None or event.get("exit_code") is not None:
                raise ValueError("bad_hang")
            self._enter_revoking_internal("disconnect")

    def release_commit(self, *, consumer_blocked: bool = False) -> dict[str, Any]:
        """Serialize release under control mutex; use observed exit — no forged code."""

        if self.active_turn_id is None:
            raise ValueError("no_active_turn")
        turn_id = self.active_turn_id
        accepted = self.accepted[turn_id]
        self._acquire_mutex()
        try:
            if self._revoked:
                self._stdout_buffer.clear()
                self._stderr_buffer.clear()
                self.active_turn_id = None
                raise ValueError("revoked_before_commit")
            self._assert_watchdog_coverage()
            # Final paired sample under mutex — no await.
            sample: dict[str, Any] = cast(dict[str, Any], self.platform.sample_clock())
            self._last_valid_clock = dict(sample)
            self._watchdog_samples.append(dict(sample))
            # Revalidate accepted slot/activation/publication against bound activation.
            if self.activation_id is None or self.publication_sha256 is None or self.slot_id is None:
                self._enter_revoking_internal("integrity_failure")
                raise ValueError("activation_drift")
            if accepted.slot_id != self.slot_id or accepted.activation_id != self.activation_id:
                self._enter_revoking_internal("integrity_failure")
                self._stdout_buffer.clear()
                self._stderr_buffer.clear()
                raise ValueError("activation_drift")
            if accepted.expected_publication_sha256 != self.publication_sha256:
                self._enter_revoking_internal("integrity_failure")
                self._stdout_buffer.clear()
                self._stderr_buffer.clear()
                raise ValueError("publication_drift")
            if self.lease_deadline_boottime_ns is not None:
                if int(_port_map_get(sample, "boottime_after_ns")) > self.lease_deadline_boottime_ns:
                    self._enter_revoking_internal("expiry")
                    self._stdout_buffer.clear()
                    self._stderr_buffer.clear()
                    raise ValueError("lease_lost")
            if self._observed_exit_code is None:
                self._enter_revoking_internal("integrity_failure")
                self._stdout_buffer.clear()
                self._stderr_buffer.clear()
                raise ValueError("no_observed_exit")
            if self._observed_exit_code != 0:
                self._enter_revoking_internal("integrity_failure")
                self._stdout_buffer.clear()
                self._stderr_buffer.clear()
                raise ValueError("nonzero_agent_exit")
            # Only complete stdout JSON becomes model_output; stderr separate.
            raw = bytes(self._stdout_buffer)
            self._stdout_buffer.clear()
            _ = len(self._stderr_buffer)
            self._stderr_buffer.clear()
            try:
                model_output = _parse_complete_stdout_object(raw)
            except ValueError:
                self._enter_revoking_internal("integrity_failure")
                raise
            out_bytes = _canonical(model_output)
            result = {
                "turn_id": turn_id,
                "publication_sha256": self.publication_sha256,
                "committed_wall_time": _port_map_get(sample, "wall_time"),
                "committed_boottime_ns": int(_port_map_get(sample, "boottime_after_ns")),
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
        return self._out(request, "unavailable", {"reason": "disconnect"})

    @staticmethod
    def _out(request: Mapping[str, Any], outcome: str, payload: dict[str, Any]) -> dict[str, Any]:
        return dict(
            (
                ("schema", CONTROL_SCHEMA),
                ("request_id", request.get("request_id")),
                ("slot_id", request.get("slot_id")),
                ("activation_id", request.get("activation_id")),
                ("outcome", outcome),
                ("payload", payload),
            )
        )


if __name__ == "__main__":
    main()
