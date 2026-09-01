"""R2b v2 named duration policy fields and phase deadline tracking (I5).

Values are supplied explicitly by the caller. This module defines no accepted
production defaults.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from eval_corpus.r2b_v2.contract import DURATION_POLICY_FIELD_NAMES

ClockFn = Callable[[], float]


class ManualClock:
    """Injectable monotonic clock for deterministic adversarial tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, delta: float) -> None:
        self._t += delta

    def set(self, value: float) -> None:
        self._t = value


class DurationPolicyError(RuntimeError):
    """Invalid or expired duration policy."""


class TransactionDeadlineExpired(DurationPolicyError):
    """Absolute monotonic transaction deadline exceeded."""


class PhaseDeadlineExpired(DurationPolicyError):
    """Named phase bound exceeded."""

    def __init__(self, phase: str, message: str) -> None:
        super().__init__(message)
        self.phase = phase


class InsufficientRemainingBudget(DurationPolicyError):
    """Remaining transaction budget too small for the requested operation."""


@dataclass(frozen=True)
class DurationPolicy:
    """Immutable phase bounds — caller-supplied; not production ratification."""

    acquisition_bound: float
    hitl_reservation_bound: float
    capture_bound: float
    release_close_bound: float
    transaction_deadline: float

    def validate_positive(self) -> None:
        for name, value in (
            ("acquisition_bound", self.acquisition_bound),
            ("hitl_reservation_bound", self.hitl_reservation_bound),
            ("capture_bound", self.capture_bound),
            ("release_close_bound", self.release_close_bound),
            ("transaction_deadline", self.transaction_deadline),
        ):
            if value <= 0:
                raise DurationPolicyError(f"{name} must be positive, got {value}")

    def policy_field_names(self) -> tuple[str, ...]:
        return DURATION_POLICY_FIELD_NAMES

    def as_reference_dict(self) -> dict[str, str]:
        """Named fields only — concrete seconds are not embedded in manifests."""
        return {name: "policy_pending" for name in self.policy_field_names()}

    def phase_bound(self, phase: str) -> float:
        mapping = {
            "acquisition": self.acquisition_bound,
            "hitl": self.hitl_reservation_bound,
            "capture": self.capture_bound,
            "release_close": self.release_close_bound,
        }
        if phase not in mapping:
            raise DurationPolicyError(f"unknown phase {phase!r}")
        return mapping[phase]


def minimum_grant_remaining_budget(policy: DurationPolicy) -> float:
    """Lower bound for remaining budget proof before ACCEPT AND GRANT."""
    return policy.capture_bound + policy.release_close_bound


@dataclass(frozen=True)
class DeadlineObservation:
    """Immutable deadline sample authorizing one authority commit."""

    phase: str
    observed_at: float
    phase_started_at: float
    phase_deadline: float
    transaction_deadline: float
    effective_deadline: float
    outcome: str
    commit_scope: str
    required_remaining: float

    def as_evidence_dict(self) -> dict[str, float | str]:
        return {
            "phase": self.phase,
            "observed_at": self.observed_at,
            "phase_started_at": self.phase_started_at,
            "phase_deadline": self.phase_deadline,
            "transaction_deadline": self.transaction_deadline,
            "effective_deadline": self.effective_deadline,
            "outcome": self.outcome,
            "commit_scope": self.commit_scope,
            "required_remaining": self.required_remaining,
        }


@dataclass
class PhaseDeadlineTracker:
    """Monotonic phase timing for one scratch transaction."""

    policy: DurationPolicy
    transaction_start: float
    absolute_transaction_deadline: float
    phase_starts: dict[str, float]
    _clock: ClockFn
    consumed: bool = False

    @classmethod
    def begin(
        cls,
        policy: DurationPolicy,
        *,
        clock: ClockFn | None = None,
    ) -> PhaseDeadlineTracker:
        policy.validate_positive()
        clock_fn = clock or time.monotonic
        start = clock_fn()
        return cls(
            policy=policy,
            transaction_start=start,
            absolute_transaction_deadline=start + policy.transaction_deadline,
            phase_starts={},
            _clock=clock_fn,
        )

    def absolute_deadline(self) -> float:
        return self.absolute_transaction_deadline

    def start_phase_once(self, phase: str) -> None:
        if phase in self.phase_starts:
            raise DurationPolicyError(f"phase {phase!r} already started")
        if self.consumed:
            raise TransactionDeadlineExpired("transaction already consumed")
        observed = self._clock()
        if observed >= self.absolute_transaction_deadline:
            self.consumed = True
            raise TransactionDeadlineExpired("transaction deadline expired")
        self.phase_starts[phase] = observed

    def observe_for_commit(
        self,
        phase: str,
        *,
        observed_at: float,
        required_remaining: float = 0.0,
        commit_scope: str = "",
    ) -> DeadlineObservation:
        """Evaluate deadlines at a single pre-sampled monotonic time."""
        if self.consumed:
            raise TransactionDeadlineExpired("transaction already consumed")
        phase_start = self.phase_starts.get(phase)
        if phase_start is None:
            raise DurationPolicyError(f"phase {phase!r} was never started")
        bound = self.policy.phase_bound(phase)
        phase_deadline = phase_start + bound
        tx_deadline = self.absolute_transaction_deadline
        effective = min(phase_deadline, tx_deadline)
        remaining = tx_deadline - observed_at
        expired = (
            observed_at >= phase_deadline
            or observed_at >= tx_deadline
            or remaining < required_remaining
        )
        outcome = "expired" if expired else "within_budget"
        observation = DeadlineObservation(
            phase=phase,
            observed_at=observed_at,
            phase_started_at=phase_start,
            phase_deadline=phase_deadline,
            transaction_deadline=tx_deadline,
            effective_deadline=effective,
            outcome=outcome,
            commit_scope=commit_scope,
            required_remaining=required_remaining,
        )
        if expired:
            self.consumed = True
            if observed_at >= tx_deadline or remaining < required_remaining:
                if remaining < required_remaining:
                    raise InsufficientRemainingBudget(
                        f"remaining budget {remaining:.6f}s "
                        f"< required {required_remaining:.6f}s"
                    )
                raise TransactionDeadlineExpired("transaction deadline expired")
            raise PhaseDeadlineExpired(
                phase,
                f"{phase} bound {bound}s exceeded at commit observation",
            )
        return observation

    def consume(self, *, reason: str) -> None:
        del reason
        self.consumed = True

    # Back-compat aliases for gradual migration
    def start_phase(self, phase: str) -> None:
        self.start_phase_once(phase)

    def check_transaction_deadline(self) -> None:
        if self.consumed:
            raise TransactionDeadlineExpired("transaction already consumed")
        if self._clock() >= self.absolute_transaction_deadline:
            self.consumed = True
            raise TransactionDeadlineExpired("transaction deadline expired")

    def check_phase_bound(self, phase: str, bound: float) -> None:
        self.observe_for_commit(
            phase,
            observed_at=self._clock(),
            commit_scope="legacy_check_phase_bound",
        )

    def remaining_seconds(self) -> float:
        return max(0.0, self.absolute_transaction_deadline - self._clock())

    def prove_remaining_budget_for_grant(self) -> None:
        if "hitl" not in self.phase_starts:
            self.start_phase_once("hitl")
        required = minimum_grant_remaining_budget(self.policy)
        self.observe_for_commit(
            "hitl",
            observed_at=self._clock(),
            required_remaining=required,
            commit_scope="grant_budget_proof",
        )

    def mark_consumed(self, *, reason: str) -> None:
        self.consume(reason=reason)
