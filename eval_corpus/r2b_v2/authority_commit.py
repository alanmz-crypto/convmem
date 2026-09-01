"""Centralized expiry-safe authority commitment for R2b v2 (I5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from eval_corpus.r2b_v2.materialization import V2MaterializationResult

from eval_corpus.r2b_v2.authority_state import (
    AuthorityState,
    AuthorityStateError,
    AuthorityStateMachine,
    _guarded_transition,
    new_authority_state_machine,
)
from eval_corpus.r2b_v2.duration_policy import (
    DeadlineObservation,
    DurationPolicy,
    DurationPolicyError,
    InsufficientRemainingBudget,
    PhaseDeadlineExpired,
    PhaseDeadlineTracker,
    TransactionDeadlineExpired,
    minimum_grant_remaining_budget,
)
from eval_corpus.r2b_v2.lease import (
    R2bQuiescenceLease,
    R2bQuiescenceLeaseError,
    _LeaseHolder,
    acquire_r2b_quiescence_lease_physical,
    invalidate_pending_lease,
    release_pending_lease_kernel,
    verify_r2b_quiescence_lease,
)
from eval_corpus.r2b_v2.quiescence_evidence import (
    write_quiescence_close,
    write_quiescence_release,
)

ClockFn = Callable[[], float]

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


class AuthorityCommitError(RuntimeError):
    """Authority commitment failure."""


@dataclass(frozen=True)
class CommitSpec:
    phase: str
    target_state: AuthorityState
    required_remaining: float = 0.0
    commit_scope: str = ""
    reason: str = ""


@dataclass
class PreparedActivation:
    """Non-authoritative staged artifact pending guarded commit."""

    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PendingLease:
    """Physical kernel lease not yet authority-committed."""

    holder: _LeaseHolder
    run_id: str


@dataclass(frozen=True)
class AcquisitionFailureArtifact:
    expired_observation: DeadlineObservation | None
    physical_acquired: bool
    authority_revoked: bool
    kernel_release_outcome: str
    final_disposition: AuthorityState


@dataclass
class AuthorityCommitter:
    """Owns state machine, deadline tracker, and guarded authority transitions."""

    run_id: str
    policy: DurationPolicy
    machine: AuthorityStateMachine
    tracker: PhaseDeadlineTracker
    _clock: ClockFn

    @classmethod
    def begin(
        cls,
        run_id: str,
        policy: DurationPolicy,
        *,
        clock: ClockFn | None = None,
        machine: AuthorityStateMachine | None = None,
        tracker: PhaseDeadlineTracker | None = None,
    ) -> AuthorityCommitter:
        clock_fn = clock or __import__("time").monotonic
        resolved_tracker = tracker or PhaseDeadlineTracker.begin(policy, clock=clock_fn)
        resolved_machine = machine or new_authority_state_machine(run_id)
        return cls(
            run_id=run_id,
            policy=policy,
            machine=resolved_machine,
            tracker=resolved_tracker,
            _clock=clock_fn,
        )

    def _commit_guarded(
        self,
        spec: CommitSpec,
        prepared: PreparedActivation,
        *,
        activate: Callable[[DeadlineObservation], Any],
    ) -> tuple[DeadlineObservation, Any]:
        if spec.target_state not in GUARDED_SUCCESS_STATES:
            raise AuthorityCommitError(
                f"{spec.target_state.value} is not a guarded success state"
            )
        allowed = _allowed_from_current(self.machine.state)
        if spec.target_state not in allowed:
            raise AuthorityStateError(
                f"invalid guarded transition {self.machine.state.value} -> "
                f"{spec.target_state.value}"
            )
        observed_at = self._clock()
        try:
            observation = self.tracker.observe_for_commit(
                spec.phase,
                observed_at=observed_at,
                required_remaining=spec.required_remaining,
                commit_scope=spec.commit_scope or spec.target_state.value,
            )
        except (
            PhaseDeadlineExpired,
            TransactionDeadlineExpired,
            InsufficientRemainingBudget,
        ):
            self.tracker.consume(reason=f"commit failed: {spec.commit_scope}")
            raise
        result = activate(observation)
        _guarded_transition(
            self.machine,
            spec.target_state,
            reason=spec.reason or spec.commit_scope,
        )
        return observation, result

    def commit_q_held(
        self,
        lease: R2bQuiescenceLease,
        *,
        reason: str = "lease held",
    ) -> DeadlineObservation:
        verify_r2b_quiescence_lease(lease, expected_run_id=self.run_id)
        if self.machine.state == AuthorityState.Q_AUTHORIZED:
            self.machine.transition(AuthorityState.Q_ACQUIRING, reason="auto acquire start")
        if self.machine.state != AuthorityState.Q_ACQUIRING:
            raise AuthorityStateError(
                f"Q_HELD requires Q_ACQUIRING, got {self.machine.state.value}"
            )
        if "acquisition" not in self.tracker.phase_starts:
            self.tracker.start_phase_once("acquisition")
        observation, _ = self._commit_guarded(
            CommitSpec(
                phase="acquisition",
                target_state=AuthorityState.Q_HELD,
                commit_scope="q_held",
                reason=reason,
            ),
            PreparedActivation(kind="lease", payload={"run_id": self.run_id}),
            activate=lambda _obs: None,
        )
        return observation

    def commit_packet_accepted(
        self,
        *,
        manifest_path: Path,
        approval_digest: str,
        reason: str = "Ryan packet ACCEPT",
    ) -> DeadlineObservation:
        if self.machine.state != AuthorityState.PACKET_DRAFTED:
            raise AuthorityStateError(
                f"PACKET_ACCEPTED requires PACKET_DRAFTED, got {self.machine.state.value}"
            )
        prepared = PreparedActivation(
            kind="approval_sidecar",
            payload={
                "manifest_path": str(manifest_path),
                "approval_digest": approval_digest,
            },
        )

        def activate(_obs: DeadlineObservation) -> str:
            from eval_corpus.run_manifest import write_approval_sidecar

            write_approval_sidecar(manifest_path, approval_digest)
            return approval_digest

        observation, _ = self._commit_guarded(
            CommitSpec(
                phase="hitl",
                target_state=AuthorityState.PACKET_ACCEPTED,
                commit_scope="packet_accepted",
                reason=reason,
            ),
            prepared,
            activate=activate,
        )
        return observation

    def commit_materialized(
        self,
        materialized: V2MaterializationResult,
        *,
        reason: str = "binder validated packet",
    ) -> DeadlineObservation:
        if self.machine.state != AuthorityState.PACKET_ACCEPTED:
            raise AuthorityStateError(
                f"MATERIALIZED requires PACKET_ACCEPTED, got {self.machine.state.value}"
            )
        prepared = PreparedActivation(
            kind="materialization",
            payload={"manifest_path": str(materialized.manifest_path)},
        )
        observation, _ = self._commit_guarded(
            CommitSpec(
                phase="hitl",
                target_state=AuthorityState.MATERIALIZED,
                commit_scope="materialized",
                reason=reason,
            ),
            prepared,
            activate=lambda _obs: materialized,
        )
        return observation

    def commit_capture_granted(
        self,
        materialized: V2MaterializationResult,
        *,
        reason: str = "Ryan ACCEPT AND GRANT",
    ) -> DeadlineObservation:
        if self.machine.state != AuthorityState.MATERIALIZED:
            raise AuthorityStateError(
                f"CAPTURE_GRANTED requires MATERIALIZED, got {self.machine.state.value}"
            )
        if materialized.bindings.capture_dir.exists():
            raise AuthorityCommitError("capture_dir must be absent before grant")
        required = minimum_grant_remaining_budget(self.policy)
        prepared = PreparedActivation(kind="capture_grant", payload={})
        observation, _ = self._commit_guarded(
            CommitSpec(
                phase="hitl",
                target_state=AuthorityState.CAPTURE_GRANTED,
                required_remaining=required,
                commit_scope="capture_granted",
                reason=reason,
            ),
            prepared,
            activate=lambda _obs: materialized,
        )
        return observation

    def commit_capture_seal(
        self,
        *,
        promote_marker: Callable[[], dict[str, Any]],
        reason: str = "marker last",
    ) -> tuple[DeadlineObservation, dict[str, Any]]:
        if self.machine.state != AuthorityState.FINAL_SOURCE_CHECKED:
            raise AuthorityStateError(
                f"SEALED requires FINAL_SOURCE_CHECKED, got {self.machine.state.value}"
            )
        prepared = PreparedActivation(kind="capture_marker", payload={})

        def activate(_obs: DeadlineObservation) -> dict[str, Any]:
            return promote_marker()

        observation, marker_result = self._commit_guarded(
            CommitSpec(
                phase="capture",
                target_state=AuthorityState.SEALED,
                commit_scope="capture_seal",
                reason=reason,
            ),
            prepared,
            activate=activate,
        )
        return observation, marker_result

    def commit_closing(
        self,
        *,
        close_path: Path,
        close_body: dict[str, Any],
        reason: str = "close evidence fsynced",
    ) -> tuple[DeadlineObservation, str]:
        if self.machine.state != AuthorityState.SEALED:
            raise AuthorityStateError(
                f"CLOSING requires SEALED, got {self.machine.state.value}"
            )
        prepared = PreparedActivation(kind="quiescence_close", payload={"path": str(close_path)})

        def activate(obs: DeadlineObservation) -> str:
            return write_quiescence_close(
                close_path,
                deadline_observation=obs,
                run_id=close_body["run_id"],
                terminal_disposition=close_body["terminal_disposition"],
                marker_result=close_body["marker_result"],
                final_source_result=close_body["final_source_result"],
                gate_identity=close_body["gate_identity"],
                release_intent=close_body["release_intent"],
                preceding_digests=close_body["preceding_digests"],
            )

        observation, digest = self._commit_guarded(
            CommitSpec(
                phase="release_close",
                target_state=AuthorityState.CLOSING,
                commit_scope="closing",
                reason=reason,
            ),
            prepared,
            activate=activate,
        )
        return observation, digest

    def commit_closed(
        self,
        *,
        release_path: Path,
        release_body: dict[str, Any],
        reason: str = "release evidence written",
    ) -> tuple[DeadlineObservation, str]:
        if self.machine.state != AuthorityState.CLOSING:
            raise AuthorityStateError(
                f"CLOSED requires CLOSING, got {self.machine.state.value}"
            )
        prepared = PreparedActivation(
            kind="quiescence_release",
            payload={"path": str(release_path)},
        )

        def activate(obs: DeadlineObservation) -> str:
            return write_quiescence_release(
                release_path,
                deadline_observation=obs,
                run_id=release_body["run_id"],
                close_digest=release_body["close_digest"],
                release_result=release_body["release_result"],
                post_release_observation=release_body["post_release_observation"],
                kernel_released=release_body.get("kernel_released"),
            )

        observation, digest = self._commit_guarded(
            CommitSpec(
                phase="release_close",
                target_state=AuthorityState.CLOSED,
                commit_scope="closed",
                reason=reason,
            ),
            prepared,
            activate=activate,
        )
        return observation, digest

    def commit_acquisition(self, pending: PendingLease) -> R2bQuiescenceLease:
        if pending.run_id != self.run_id:
            raise AuthorityCommitError("pending lease run_id mismatch")
        if self.machine.state not in (
            AuthorityState.Q_AUTHORIZED,
            AuthorityState.Q_ACQUIRING,
            AuthorityState.NEW,
        ):
            raise AuthorityStateError(
                f"acquisition commit requires NEW/Q_AUTHORIZED/Q_ACQUIRING, "
                f"got {self.machine.state.value}"
            )
        if self.machine.state == AuthorityState.NEW:
            self.machine.transition(AuthorityState.PREPARED, reason="acquisition prepare")
            self.machine.transition(AuthorityState.Q_AUTHORIZED, reason="acquisition authorize")
        if self.machine.state == AuthorityState.Q_AUTHORIZED:
            self.machine.transition(AuthorityState.Q_ACQUIRING, reason="auto acquire start")

        def activate(_obs: DeadlineObservation) -> R2bQuiescenceLease:
            return R2bQuiescenceLease(pending.holder)

        try:
            self._commit_guarded(
                CommitSpec(
                    phase="acquisition",
                    target_state=AuthorityState.Q_HELD,
                    commit_scope="acquisition",
                    reason="physical acquisition committed",
                ),
                PreparedActivation(kind="pending_lease", payload={"run_id": self.run_id}),
                activate=activate,
            )
        except (
            PhaseDeadlineExpired,
            TransactionDeadlineExpired,
            InsufficientRemainingBudget,
        ) as exc:
            artifact = self.neutralize_pending_lease(
                pending,
                expired_observation=getattr(exc, "observation", None),
            )
            raise AuthorityCommitError(
                f"acquisition authority commit failed: {artifact.final_disposition.value}"
            ) from exc
        return R2bQuiescenceLease(pending.holder)

    def neutralize_pending_lease(
        self,
        pending: PendingLease,
        *,
        expired_observation: DeadlineObservation | None = None,
    ) -> AcquisitionFailureArtifact:
        self.tracker.consume(reason="pending lease neutralization")
        authority_revoked = False
        kernel_outcome = "not_attempted"
        try:
            invalidate_pending_lease(pending.holder)
            authority_revoked = True
        except R2bQuiescenceLeaseError:
            authority_revoked = False
        try:
            release_pending_lease_kernel(pending.holder)
            kernel_outcome = "released"
            disposition = AuthorityState.ABORTED
            self.machine.abort(reason="acquisition commit expired after physical acquire")
        except Exception:
            kernel_outcome = "failed_or_uncertain"
            disposition = AuthorityState.QUARANTINED
            self.machine.quarantine(
                reason="acquisition neutralization release failed or uncertain"
            )
        return AcquisitionFailureArtifact(
            expired_observation=expired_observation,
            physical_acquired=True,
            authority_revoked=authority_revoked,
            kernel_release_outcome=kernel_outcome,
            final_disposition=disposition,
        )


def _allowed_from_current(state: AuthorityState) -> frozenset[AuthorityState]:
    from eval_corpus.r2b_v2.authority_state import _ALLOWED  # pylint: disable=import-outside-toplevel

    return _ALLOWED.get(state, frozenset())
