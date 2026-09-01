"""Durable R2b v2 authority state machine substrate (I1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from eval_corpus.r2b_v2.coverage.proof import TrustedCoverageProof
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease


class AuthorityState(str, Enum):
    NEW = "NEW"
    PREPARED = "PREPARED"
    Q_AUTHORIZED = "Q_AUTHORIZED"
    Q_ACQUIRING = "Q_ACQUIRING"
    Q_HELD = "Q_HELD"
    COVERAGE_PROVEN = "COVERAGE_PROVEN"
    SNAPSHOT_BOUND = "SNAPSHOT_BOUND"
    PACKET_DRAFTED = "PACKET_DRAFTED"
    PACKET_ACCEPTED = "PACKET_ACCEPTED"
    MATERIALIZED = "MATERIALIZED"
    CAPTURE_GRANTED = "CAPTURE_GRANTED"
    CAPTURING = "CAPTURING"
    FINAL_SOURCE_CHECKED = "FINAL_SOURCE_CHECKED"
    SEALED = "SEALED"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    ABORTED = "ABORTED"
    QUARANTINED = "QUARANTINED"


_TERMINAL = frozenset({AuthorityState.ABORTED, AuthorityState.QUARANTINED})

GUARDED_SUCCESS_STATES = frozenset(
    {
        AuthorityState.Q_HELD,
        AuthorityState.PACKET_ACCEPTED,
        AuthorityState.MATERIALIZED,
        AuthorityState.CAPTURE_GRANTED,
        AuthorityState.SEALED,
        AuthorityState.CLOSING,
        AuthorityState.CLOSED,
    }
)

# Full v2 state machine including I4–I6 scratch-reachable transitions.
_ALLOWED: dict[AuthorityState, frozenset[AuthorityState]] = {
    AuthorityState.NEW: frozenset({AuthorityState.PREPARED, *_TERMINAL}),
    AuthorityState.PREPARED: frozenset({AuthorityState.Q_AUTHORIZED, *_TERMINAL}),
    AuthorityState.Q_AUTHORIZED: frozenset({AuthorityState.Q_ACQUIRING, *_TERMINAL}),
    AuthorityState.Q_ACQUIRING: frozenset({AuthorityState.Q_HELD, *_TERMINAL}),
    AuthorityState.Q_HELD: frozenset({AuthorityState.COVERAGE_PROVEN, *_TERMINAL}),
    AuthorityState.COVERAGE_PROVEN: frozenset({AuthorityState.SNAPSHOT_BOUND, *_TERMINAL}),
    AuthorityState.SNAPSHOT_BOUND: frozenset({AuthorityState.PACKET_DRAFTED, *_TERMINAL}),
    AuthorityState.PACKET_DRAFTED: frozenset({AuthorityState.PACKET_ACCEPTED, *_TERMINAL}),
    AuthorityState.PACKET_ACCEPTED: frozenset({AuthorityState.MATERIALIZED, *_TERMINAL}),
    AuthorityState.MATERIALIZED: frozenset({AuthorityState.CAPTURE_GRANTED, *_TERMINAL}),
    AuthorityState.CAPTURE_GRANTED: frozenset({AuthorityState.CAPTURING, *_TERMINAL}),
    AuthorityState.CAPTURING: frozenset(
        {AuthorityState.FINAL_SOURCE_CHECKED, *_TERMINAL}
    ),
    AuthorityState.FINAL_SOURCE_CHECKED: frozenset({AuthorityState.SEALED, *_TERMINAL}),
    AuthorityState.SEALED: frozenset({AuthorityState.CLOSING, *_TERMINAL}),
    AuthorityState.CLOSING: frozenset({AuthorityState.CLOSED, *_TERMINAL}),
    AuthorityState.CLOSED: frozenset(),
    AuthorityState.ABORTED: frozenset(),
    AuthorityState.QUARANTINED: frozenset(),
}


class AuthorityStateError(RuntimeError):
    """Invalid or unauthorized authority state transition."""


@dataclass
class AuthorityStateMachine:
    """Explicit durable authority state for one R2b v2 run."""

    run_id: str
    state: AuthorityState = AuthorityState.NEW
    history: list[dict[str, Any]] = field(default_factory=list)
    _resumed: bool = field(default=False, repr=False)

    def _record(self, prior: AuthorityState, nxt: AuthorityState, *, reason: str) -> None:
        self.history.append(
            {
                "from": prior.value,
                "to": nxt.value,
                "reason": reason,
            }
        )

    @property
    def terminal(self) -> bool:
        return self.state in _TERMINAL or self.state == AuthorityState.CLOSED

    @property
    def resumed(self) -> bool:
        return self._resumed

    def transition(self, nxt: AuthorityState, *, reason: str) -> None:
        if nxt in GUARDED_SUCCESS_STATES:
            raise AuthorityStateError(
                f"{nxt.value} requires AuthorityCommitter guarded commit"
            )
        _transition_unchecked(self, nxt, reason=reason)

    def abort(self, *, reason: str) -> None:
        if self.state == AuthorityState.ABORTED:
            return
        if self.state == AuthorityState.QUARANTINED:
            raise AuthorityStateError("QUARANTINED cannot become ABORTED")
        if self.state == AuthorityState.CLOSED:
            raise AuthorityStateError("CLOSED cannot become ABORTED")
        prior = self.state
        self.state = AuthorityState.ABORTED
        self._record(prior, AuthorityState.ABORTED, reason=reason)

    def quarantine(self, *, reason: str) -> None:
        if self.state == AuthorityState.QUARANTINED:
            return
        if self.state == AuthorityState.ABORTED:
            raise AuthorityStateError("ABORTED cannot become QUARANTINED")
        if self.state == AuthorityState.CLOSED:
            raise AuthorityStateError("CLOSED cannot become QUARANTINED")
        prior = self.state
        self.state = AuthorityState.QUARANTINED
        self._record(prior, AuthorityState.QUARANTINED, reason=reason)


def _transition_unchecked(
    machine: AuthorityStateMachine,
    nxt: AuthorityState,
    *,
    reason: str,
) -> None:
    if machine._resumed:
        raise AuthorityStateError(
            "run cannot be resumed or reacquired by reconstructing state"
        )
    if machine.terminal:
        raise AuthorityStateError(
            f"terminal state {machine.state.value} cannot transition to {nxt.value}"
        )
    allowed = _ALLOWED.get(machine.state, frozenset())
    if nxt not in allowed:
        raise AuthorityStateError(
            f"invalid transition {machine.state.value} -> {nxt.value}"
        )
    prior = machine.state
    machine.state = nxt
    machine._record(prior, nxt, reason=reason)


def _guarded_transition(
    machine: AuthorityStateMachine,
    nxt: AuthorityState,
    *,
    reason: str,
) -> None:
    if nxt not in GUARDED_SUCCESS_STATES:
        raise AuthorityStateError(f"{nxt.value} is not a guarded success state")
    _transition_unchecked(machine, nxt, reason=reason)


def new_authority_state_machine(run_id: str) -> AuthorityStateMachine:
    """Mint a fresh authority state machine for a new run."""
    return AuthorityStateMachine(run_id=run_id, _resumed=False)


def observe_authority_state(machine: AuthorityStateMachine) -> dict[str, Any]:
    """Read-only snapshot of durable authority state — not resumption authority."""
    return {
        "run_id": machine.run_id,
        "state": machine.state.value,
        "terminal": machine.terminal,
        "history_len": len(machine.history),
        "resumed": machine.resumed,
    }


def transition_to_q_held(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    committer: Any,
    *,
    reason: str,
) -> None:
    """Evidence-coupled Q_ACQUIRING → Q_HELD via AuthorityCommitter."""
    verify_r2b_quiescence_lease(lease, expected_run_id=machine.run_id)
    committer.commit_q_held(lease, reason=reason)


def transition_to_coverage_proven(
    machine: AuthorityStateMachine,
    lease: R2bQuiescenceLease,
    trusted_coverage: TrustedCoverageProof,
    *,
    reason: str,
) -> None:
    """Evidence-coupled Q_HELD → COVERAGE_PROVEN with cross-slice binding."""
    verify_r2b_quiescence_lease(
        lease,
        expected_run_id=machine.run_id,
        expected_coverage_digest=trusted_coverage.coverage_digest,
        expected_gate_identity=trusted_coverage.gate_identity,
    )
    bindings = lease.bindings
    if bindings.gate_path != trusted_coverage.gate_path:
        raise AuthorityStateError("gate_path mismatch between lease and trusted coverage")
    if machine.state != AuthorityState.Q_HELD:
        raise AuthorityStateError(
            f"COVERAGE_PROVEN requires Q_HELD, got {machine.state.value}"
        )
    machine.transition(AuthorityState.COVERAGE_PROVEN, reason=reason)


def reconstruct_state_machine(
    *,
    run_id: str,
    state: AuthorityState,
) -> AuthorityStateMachine:
    """Rehydrate persisted state for inspection only — not resumption authority."""
    return AuthorityStateMachine(run_id=run_id, state=state, _resumed=True)
