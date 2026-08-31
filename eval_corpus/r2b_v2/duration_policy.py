"""R2b v2 named duration policy fields and phase deadline tracking (I5).

Values are supplied explicitly by the caller. This module defines no accepted
production defaults.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


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
        return (
            "acquisition_bound",
            "hitl_reservation_bound",
            "capture_bound",
            "release_close_bound",
            "transaction_deadline",
        )

    def as_reference_dict(self) -> dict[str, str]:
        """Named fields only — concrete seconds are not embedded in manifests."""
        return {name: "policy_pending" for name in self.policy_field_names()}


def minimum_grant_remaining_budget(policy: DurationPolicy) -> float:
    """Lower bound for remaining budget proof before ACCEPT AND GRANT."""
    return policy.capture_bound + policy.release_close_bound


@dataclass
class PhaseDeadlineTracker:
    """Monotonic phase timing for one scratch transaction."""

    policy: DurationPolicy
    transaction_start: float
    phase_starts: dict[str, float]
    consumed: bool = False

    @classmethod
    def begin(cls, policy: DurationPolicy) -> PhaseDeadlineTracker:
        policy.validate_positive()
        return cls(
            policy=policy,
            transaction_start=time.monotonic(),
            phase_starts={},
        )

    def absolute_deadline(self) -> float:
        return self.transaction_start + self.policy.transaction_deadline

    def check_transaction_deadline(self) -> None:
        if self.consumed:
            raise TransactionDeadlineExpired("transaction already consumed")
        if time.monotonic() > self.absolute_deadline():
            self.consumed = True
            raise TransactionDeadlineExpired("transaction deadline expired")

    def start_phase(self, phase: str) -> None:
        self.check_transaction_deadline()
        self.phase_starts[phase] = time.monotonic()

    def check_phase_bound(self, phase: str, bound: float) -> None:
        self.check_transaction_deadline()
        start = self.phase_starts.get(phase)
        if start is None:
            raise DurationPolicyError(f"phase {phase!r} was never started")
        if time.monotonic() - start > bound:
            self.consumed = True
            raise PhaseDeadlineExpired(
                phase,
                f"{phase} bound {bound}s exceeded",
            )

    def remaining_seconds(self) -> float:
        return max(0.0, self.absolute_deadline() - time.monotonic())

    def prove_remaining_budget_for_grant(self) -> None:
        """Fail closed when capture + close/release cannot fit in remaining time."""
        required = minimum_grant_remaining_budget(self.policy)
        self.check_transaction_deadline()
        if self.remaining_seconds() < required:
            self.consumed = True
            raise InsufficientRemainingBudget(
                f"remaining budget {self.remaining_seconds():.3f}s "
                f"< required {required:.3f}s for grant"
            )

    def mark_consumed(self, *, reason: str) -> None:
        del reason
        self.consumed = True
