"""Durable R2b v2 authority state machine substrate (I1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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

# Transitions implemented for I1–I3 substrate only.
_ALLOWED: dict[AuthorityState, frozenset[AuthorityState]] = {
    AuthorityState.NEW: frozenset({AuthorityState.PREPARED, *_TERMINAL}),
    AuthorityState.PREPARED: frozenset({AuthorityState.Q_AUTHORIZED, *_TERMINAL}),
    AuthorityState.Q_AUTHORIZED: frozenset({AuthorityState.Q_ACQUIRING, *_TERMINAL}),
    AuthorityState.Q_ACQUIRING: frozenset({AuthorityState.Q_HELD, *_TERMINAL}),
    AuthorityState.Q_HELD: frozenset({AuthorityState.COVERAGE_PROVEN, *_TERMINAL}),
    # Later live states exist for schema completeness; I4+ drives them.
    AuthorityState.COVERAGE_PROVEN: frozenset({AuthorityState.SNAPSHOT_BOUND, *_TERMINAL}),
    AuthorityState.SNAPSHOT_BOUND: frozenset({AuthorityState.PACKET_DRAFTED, *_TERMINAL}),
    AuthorityState.PACKET_DRAFTED: frozenset({AuthorityState.PACKET_ACCEPTED, *_TERMINAL}),
    AuthorityState.PACKET_ACCEPTED: frozenset({AuthorityState.MATERIALIZED, *_TERMINAL}),
    AuthorityState.MATERIALIZED: frozenset({AuthorityState.CAPTURE_GRANTED, *_TERMINAL}),
    AuthorityState.CAPTURE_GRANTED: frozenset({AuthorityState.CAPTURING, *_TERMINAL}),
    AuthorityState.CAPTURING: frozenset({AuthorityState.FINAL_SOURCE_CHECKED, *_TERMINAL}),
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
    resumed: bool = False

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

    def transition(self, nxt: AuthorityState, *, reason: str) -> None:
        if self.resumed:
            raise AuthorityStateError(
                "run cannot be resumed or reacquired by reconstructing state"
            )
        if self.terminal:
            raise AuthorityStateError(
                f"terminal state {self.state.value} cannot transition to {nxt.value}"
            )
        allowed = _ALLOWED.get(self.state, frozenset())
        if nxt not in allowed:
            raise AuthorityStateError(
                f"invalid transition {self.state.value} -> {nxt.value}"
            )
        prior = self.state
        self.state = nxt
        self._record(prior, nxt, reason=reason)

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


def reconstruct_state_machine(
    *,
    run_id: str,
    state: AuthorityState,
) -> AuthorityStateMachine:
    """Rehydrate persisted state for inspection only — not resumption authority."""
    machine = AuthorityStateMachine(run_id=run_id, state=state, resumed=True)
    return machine
