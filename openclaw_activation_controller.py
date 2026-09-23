"""OpenClaw activation controller — peer/slot/manager/retirement core (M6/T5).

Production ``start`` / ``main`` refuse before any OS effect (Architecture §6.5.8).
Library cores are constructed with a test-owned FixturePlatform; this module never
imports ``tests/fixtures/openclaw_strict``.
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
RETIREMENT_SCHEMA = "convmem.activation-retirement.v1"
CLOCK_REVIEW_SCHEMA = "convmem.clock-review.v1"

LOGICAL_UID = {
    "operator": 1000,
    "controller": 0,
    "supervisor": 0,
    "runtime": 1001,
}
LOGICAL_GID = dict(LOGICAL_UID)

STATES = (
    "NEW",
    "QUALIFYING",
    "ACTIVE_IDLE",
    "TURN_RUNNING",
    "REVOKING",
    "SEALED",
    "QUARANTINED",
)

# Closed lifecycle config claims (Architecture §6.5.6) — validated as data.
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


def _parse_wall(wall: str) -> int:
    """Parse ``YYYY-MM-DDTHH:MM:SSZ`` to epoch seconds (integer, no float)."""

    if len(wall) != 20 or wall[10] != "T" or wall[-1] != "Z":
        raise ValueError("bad_wall_time")
    year = int(wall[0:4])
    month = int(wall[5:7])
    day = int(wall[8:10])
    hour = int(wall[11:13])
    minute = int(wall[14:16])
    second = int(wall[17:19])
    # Civil-to-epoch (proleptic Gregorian) — deterministic, no host tz.
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
    """Validate closed lifecycle disables; return normalized core claims.

    OpenClaw effective inventory is Gate D; this core only accepts synthetic
    config objects that assert every required disable is false/absent-as-false.
    """

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
class SlotState:
    slot_id: str
    lineage_id: str
    state: str = "NEW"
    activation_id: str | None = None
    activation_manifest: dict[str, Any] | None = None
    publication_sha256: str | None = None
    manager_boot_id: str | None = None
    unit_invocation_id: str | None = None
    containment_id: str | None = None
    freshness_anchor: FreshnessAnchor | None = None
    authority_head: str | None = None
    expires_at: str | None = None
    lease_deadline_boottime_ns: int | None = None
    terminal_reason: str | None = None
    retirement_receipt: dict[str, Any] | None = None
    quarantine_reason: str | None = None
    wall_offset_lower_bound: int | None = None
    max_accepted_turns_sealed: bool = False
    persisted: dict[str, Any] = field(default_factory=dict)


@dataclass
class ControllerCore:
    """Stable-slot lifecycle, peer policy, lock order, retirement/quarantine."""

    platform: FixturePlatformPort
    supervisor: Any  # SupervisorCore — duck-typed; avoids fixture/production import cycle
    slots: MutableMapping[str, SlotState] = field(default_factory=dict)
    # Fixture lock order: slot transition → lineage exclusive (no prod/governed layers).
    _slot_transition_held: bool = False
    _lineage_exclusive_held: bool = False
    _active_control_connections: int = 0
    MAX_CONTROL_CONNECTIONS: int = 8

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
        if len(slot_id) != 32 or any(c not in "0123456789abcdef" for c in slot_id):
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
        # Must not hold slot transition while waiting for lineage in reverse order.
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
        before = int(sample["boottime_before_ns"])
        after = int(sample["boottime_after_ns"])
        wall = str(sample["wall_time"])
        wall_s = _parse_wall(wall)
        # Midpoint BOOTTIME for offset lower-bound maintenance.
        mid = (before + after) // 2
        offset = wall_s * 1_000_000_000 - mid
        if st.wall_offset_lower_bound is None:
            st.wall_offset_lower_bound = offset
        elif offset < st.wall_offset_lower_bound:
            # New interval entirely below retained lower bound → seal.
            self._enter_revoking(st, "clock_anomaly")
            return
        # Wall decrease vs last sampled wall in anchor.
        if st.freshness_anchor is not None:
            prev = _parse_wall(st.freshness_anchor.sampled_wall_time)
            if wall_s < prev:
                self._enter_revoking(st, "clock_anomaly")

    def establish_freshness_anchor(
        self,
        st: SlotState,
        *,
        authority_snapshot_id: str,
        remaining_snapshot_lifetime_ns: int,
        clock_review: Mapping[str, Any] | None = None,
    ) -> FreshnessAnchor:
        sample = self._sample_paired()
        boot_id = str(sample["boot_id"])
        if remaining_snapshot_lifetime_ns < 0:
            raise ValueError("negative_snapshot_lifetime")
        if st.freshness_anchor is not None and st.freshness_anchor.boot_id == boot_id:
            # Same boot: reuse deadline or a smaller one.
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
        # New boot requires operator clock-review receipt.
        if clock_review is None:
            raise ValueError("clock_review_required")
        if clock_review.get("schema") != CLOCK_REVIEW_SCHEMA:
            raise ValueError("bad_clock_review_schema")
        if clock_review.get("boot_id") != boot_id:
            raise ValueError("clock_review_boot_mismatch")
        if clock_review.get("expires_at") != st.expires_at:
            raise ValueError("clock_review_expiry_renewal_forbidden")
        if int(clock_review.get("reviewer_uid", -1)) != LOGICAL_UID["operator"]:
            raise ValueError("clock_review_reviewer_uid")
        # May only establish remaining absolute lifetime, never renew cutoff.
        deadline = int(sample["boottime_after_ns"]) + remaining_snapshot_lifetime_ns
        ref = _sha256_labeled(_canonical(dict(clock_review)))
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

    def qualify_and_activate(
        self,
        slot_id: str,
        activation_manifest: Mapping[str, Any],
        launch_policy: Mapping[str, Any],
        *,
        lifecycle_config: Mapping[str, Any] | None = None,
        remaining_snapshot_lifetime_ns: int = 3_600_000_000_000,
        clock_review: Mapping[str, Any] | None = None,
        max_activation_lifetime_s: int | None = None,
    ) -> SlotState:
        st = self.slots[slot_id]
        self._acquire_slot_transition()
        try:
            if st.state in ("QUARANTINED", "ACTIVE_IDLE", "TURN_RUNNING", "REVOKING"):
                raise ValueError(f"slot_not_activatable:{st.state}")
            if st.state == "SEALED" and st.retirement_receipt is None:
                raise ValueError("sealed_without_receipt")
            # After successful retirement, slot may be reused from SEALED → NEW externally.
            if st.state == "SEALED":
                st.state = "NEW"
                st.activation_id = None
                st.unit_invocation_id = None
                st.containment_id = None
                st.retirement_receipt = None
                st.terminal_reason = None
            st.state = "QUALIFYING"
            lifecycle_config_core(lifecycle_config)
            # Private cold qualification paths — controller may read.
            for path in (
                "/fixture/private/qualification/manifest.json",
                "/fixture/private/authority/head.json",
                "/fixture/private/issuer/inventory.json",
                "/fixture/private/governance/fence.json",
            ):
                self.check_access("controller", path, "read")
            # Runtime must be denied these same paths.
            for path in (
                "/fixture/private/qualification/manifest.json",
                "/fixture/private/issuer/inventory.json",
                "/fixture/private/governance/fence.json",
                "/fixture/private/control/socket",
            ):
                if self.platform.access("runtime", path, "read"):
                    raise ValueError("runtime_private_access_allowed")
            pub = str(activation_manifest["publication_sha256"])
            act_id = str(activation_manifest["activation_id"])
            if str(activation_manifest["slot_id"]) != slot_id:
                raise ValueError("activation_slot_mismatch")
            if launch_policy.get("operator_uid") != LOGICAL_UID["operator"]:
                raise ValueError("bad_operator_uid")
            if launch_policy.get("controller_uid") != LOGICAL_UID["controller"]:
                raise ValueError("bad_controller_uid")
            if launch_policy.get("supervisor_uid") != LOGICAL_UID["supervisor"]:
                raise ValueError("bad_supervisor_uid")
            if launch_policy.get("runtime_uid") != LOGICAL_UID["runtime"]:
                raise ValueError("bad_runtime_uid")
            snap_id = str(activation_manifest["snapshot_id"])
            if st.freshness_anchor is None or st.freshness_anchor.boot_id != self._sample_paired()["boot_id"]:
                # Re-sample inside establish after boot check.
                pass
            sample = self._sample_paired()
            if st.freshness_anchor is not None and st.freshness_anchor.boot_id != sample["boot_id"]:
                self.establish_freshness_anchor(
                    st,
                    authority_snapshot_id=snap_id,
                    remaining_snapshot_lifetime_ns=remaining_snapshot_lifetime_ns,
                    clock_review=clock_review,
                )
            elif st.freshness_anchor is None:
                # First qualification on this boot — no review required.
                deadline = int(sample["boottime_after_ns"]) + remaining_snapshot_lifetime_ns
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
            # Lease: min(snapshot deadline, now + max_lifetime).
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
            # Manager start — only after qualification.
            ids = self.platform.manager_start(slot_id, act_id)
            # Spawn supervisor (virtual) with control/lease/notify fd roles.
            fd_roles = {
                "supervisor_control": object(),
                "lease": object(),
                "notify": object(),
            }
            sup_proc = launch_policy["processes"]["supervisor"]
            handle = self.platform.spawn(
                "supervisor",
                list(sup_proc["argv_template"]),
                dict(sup_proc["environment"]),
                str(sup_proc["cwd"]),
                fd_roles,
            )
            # Wait for READY while still holding the slot transition lock.
            ready = self.platform.next_event(handle)
            if ready.get("kind") != "ready":
                st.state = "REVOKING"
                st.terminal_reason = "integrity_failure"
                raise ValueError("supervisor_not_ready")
            st.activation_id = act_id
            st.activation_manifest = dict(activation_manifest)
            st.publication_sha256 = pub
            st.manager_boot_id = ids["manager_boot_id"]
            st.unit_invocation_id = ids["unit_invocation_id"]
            st.containment_id = ids["containment_id"]
            st.lease_deadline_boottime_ns = lease
            st.expires_at = expires_at
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
                }
            )
            return st
        except Exception:
            if st.state == "QUALIFYING":
                st.state = "REVOKING"
                st.terminal_reason = "integrity_failure"
            raise
        finally:
            self._release_slot_transition()

    def await_supervisor_ready(self, slot_id: str) -> None:
        st = self.slots[slot_id]
        handle = self.supervisor.supervisor_handle
        if handle is None:
            raise ValueError("no_supervisor_handle")
        ev = self.platform.next_event(handle)
        if ev.get("kind") != "ready":
            self._enter_revoking(st, "integrity_failure")
            raise ValueError("supervisor_not_ready")

    def open_control_session(self, connection_id: str) -> None:
        if self._active_control_connections >= self.MAX_CONTROL_CONNECTIONS:
            raise ValueError("control_connection_capacity")
        self.validate_peer(connection_id, expected_role="operator")
        self._active_control_connections += 1

    def close_control_session(self) -> None:
        if self._active_control_connections > 0:
            self._active_control_connections -= 1

    def handle_control(
        self,
        connection_id: str,
        request: Mapping[str, Any],
        *,
        consumer_blocked: bool = False,
    ) -> dict[str, Any]:
        """Authenticate peer and dispatch framed control op to supervisor core."""

        try:
            self.validate_peer(connection_id, expected_role="operator")
        except ValueError:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        slot_id = str(request.get("slot_id", ""))
        if slot_id not in self.slots:
            return self._response(request, "unavailable", {"reason": "not_active"})
        st = self.slots[slot_id]
        if st.state == "QUARANTINED":
            return self._response(request, "unavailable", {"reason": "not_active"})
        if st.state == "SEALED":
            return self._response(
                request,
                "sealed",
                {"reason": st.terminal_reason or "shutdown", "retirement_ref": None},
            )
        sample = self._sample_paired()
        self._update_clock_anomaly(st, sample)
        if st.state in ("REVOKING",):
            return self._response(request, "revoking", {"reason": st.terminal_reason or "operator"})
        if st.activation_id and request.get("activation_id") != st.activation_id:
            return self._response(request, "invalid_request", {"reason": "bad_arguments"})
        # Lease check
        if st.lease_deadline_boottime_ns is not None:
            now_bt = int(sample["boottime_after_ns"])
            if now_bt > st.lease_deadline_boottime_ns:
                self._enter_revoking(st, "expiry")
                return self._response(request, "revoking", {"reason": "expiry"})
        op = request.get("op")
        if op == "status":
            return self._status_response(request, st)
        if op == "revoke":
            # Revoke must not wait for a blocked consumer.
            _ = consumer_blocked
            reason = str(request.get("reason", "operator"))
            self._enter_revoking(st, reason)
            # Supervisor revoke wins against uncommitted release.
            self.supervisor.revoke(reason)
            return self._response(request, "revoking", {"reason": reason})
        if op in ("turn", "cancel"):
            if st.state not in ("ACTIVE_IDLE", "TURN_RUNNING"):
                return self._response(request, "unavailable", {"reason": "not_active"})
            resp = self.supervisor.handle_request(dict(request), clock_sample=sample)
            # Mirror turn state onto slot.
            if resp["outcome"] == "running":
                st.state = "TURN_RUNNING"
            elif resp["outcome"] in ("committed", "busy", "already_committed", "status"):
                if resp["outcome"] == "committed":
                    st.state = "ACTIVE_IDLE"
            elif resp["outcome"] in ("cancelled", "sealed"):
                self._enter_revoking(
                    st, "disconnect" if resp["outcome"] == "cancelled" else str(resp.get("payload", {}).get("reason", "shutdown"))
                )
                if resp["outcome"] == "cancelled":
                    # Canceling a live turn seals the activation.
                    st.state = "SEALED"
                    st.terminal_reason = "disconnect"
                    resp = self._response(
                        request,
                        "sealed",
                        {"reason": "disconnect", "retirement_ref": None},
                    )
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
        st.state = "REVOKING"
        st.terminal_reason = reason
        st.persisted["state"] = st.state
        st.persisted["terminal_reason"] = reason

    def request_manager_stop(self, slot_id: str) -> dict[str, Any]:
        st = self.slots[slot_id]
        if not st.unit_invocation_id:
            raise ValueError("no_invocation")
        # Stop ack is never empty proof.
        return self.platform.manager_stop(st.unit_invocation_id)

    def attempt_retirement(self, slot_id: str, *, terminal_reason: str | None = None) -> dict[str, Any]:
        """Issue retirement receipt only for exact terminal=true,populated=false."""

        st = self.slots[slot_id]
        if not st.unit_invocation_id:
            self._quarantine(st, "missing_invocation")
            raise ValueError("quarantined:missing_invocation")
        obs = self.platform.manager_observe(st.unit_invocation_id)
        reason = terminal_reason or st.terminal_reason or "operator"
        # Matching identities required.
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
            # terminal false, populated true/null, or unknown → quarantine
            self._quarantine(
                st,
                f"uncertain_emptiness:terminal={obs.get('terminal')}:populated={obs.get('populated')}",
            )
            raise ValueError("quarantined:uncertain_emptiness")
        sample = self._sample_paired()
        body = {
            "schema": RETIREMENT_SCHEMA,
            "slot_id": st.slot_id,
            "activation_id": st.activation_id,
            "activation_manifest_sha256": _sha256_labeled(
                _canonical(st.activation_manifest or {})
            ),
            "pinned_publication_sha256": st.publication_sha256,
            "manager_boot_id": st.manager_boot_id,
            "unit_invocation_id": st.unit_invocation_id,
            "containment_id": st.containment_id,
            "terminal_reason": reason,
            "observed_empty_boottime_ns": int(sample["boottime_after_ns"]),
        }
        receipt = dict(body)
        receipt["receipt_payload_sha256"] = _sha256_labeled(_canonical(body))
        # Write receipt path via access check.
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
        """Preserve manager membership and on-disk slot; do not start a second unit."""

        st = self.slots[slot_id]
        persisted = dict(st.persisted)
        # Membership survives — observe without clearing.
        if st.unit_invocation_id:
            obs = self.platform.manager_observe(st.unit_invocation_id)
            if obs.get("populated") is not False:
                self._quarantine(st, "restart_nonempty")
        st.persisted = persisted
        return st

    def serving_rollback_view(self, slot_id: str) -> dict[str, Any]:
        """Serving-only rollback: retain exact authority head and expiry; no session resume."""

        st = self.slots[slot_id]
        return {
            "authority_head": st.authority_head,
            "expires_at": st.expires_at,
            "freshness_anchor": None if st.freshness_anchor is None else st.freshness_anchor.as_dict(),
            "session_resumable": False,
            "teardown_is_recovery": False,
            "serving_only": True,
        }

    def retire_before_lineage_exclusive(self, slot_id: str) -> None:
        """Lock-order helper: retire under slot transition, then lineage exclusive."""

        self._acquire_slot_transition()
        try:
            if self.slots[slot_id].state != "SEALED":
                raise ValueError("not_sealed")
        finally:
            self._release_slot_transition()
        self._acquire_lineage_exclusive()
        try:
            # Publisher path placeholder — fixture omits prod/governed layers.
            pass
        finally:
            self._release_lineage_exclusive()


# Module-level enroll_slot for capability detection / thin wrapper.
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
