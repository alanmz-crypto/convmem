# pylint: disable=too-many-instance-attributes,too-many-arguments
"""Opaque process-local R2b v2 quiescence lease (I2)."""

from __future__ import annotations

import copy
import fcntl
import os
import pickle
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chroma_write_store import (
    WRITER_GATE_PROTOCOL_VERSION,
    _proc_start_time,
    current_code_revision,
)

_LEASE_SECRET = secrets.token_bytes(32)


class R2bQuiescenceLeaseError(RuntimeError):
    """Lease acquisition, verification, or release failure."""


@dataclass(frozen=True)
class _LeaseBindings:
    run_id: str
    grant_digest: str
    authority_digest: str
    gate_path: str
    gate_inode: int
    gate_protocol: int
    coordinator_pid: int
    coordinator_start_time: str
    implementation_revision: str
    writer_coverage_digest: str
    open_evidence_digest: str
    monotonic_start: float
    monotonic_deadline: float
    bound_source_paths: tuple[str, ...]
    phase_bounds: tuple[str, ...]


class _LeaseHolder:
    """Internal holder — never exposed; owns the live kernel lock descriptor."""

    __slots__ = ("bindings", "lock_fd", "token")

    def __init__(
        self,
        *,
        bindings: _LeaseBindings,
        lock_fd: int,
        token: bytes,
    ) -> None:
        self.bindings = bindings
        self.lock_fd = lock_fd
        self.token = token

    def verify_live_ownership(self) -> None:
        if self.lock_fd < 0:
            raise R2bQuiescenceLeaseError("lease lock descriptor is closed")
        try:
            flags = fcntl.fcntl(self.lock_fd, fcntl.F_GETFL)
        except OSError as exc:
            raise R2bQuiescenceLeaseError(
                "lease lock descriptor is not live"
            ) from exc
        if flags < 0:
            raise R2bQuiescenceLeaseError("lease lock descriptor is not live")
        try:
            st = os.fstat(self.lock_fd)
        except OSError as exc:
            raise R2bQuiescenceLeaseError("cannot stat live lock descriptor") from exc
        if st.st_ino != self.bindings.gate_inode:
            raise R2bQuiescenceLeaseError("gate inode identity mismatch")
        if time.monotonic() > self.bindings.monotonic_deadline:
            raise R2bQuiescenceLeaseError("lease deadline expired")
        if os.getpid() != self.bindings.coordinator_pid:
            raise R2bQuiescenceLeaseError("coordinator PID mismatch")
        if _proc_start_time(self.bindings.coordinator_pid) != self.bindings.coordinator_start_time:
            raise R2bQuiescenceLeaseError("coordinator process start identity mismatch")

    def release(self) -> None:
        if self.lock_fd >= 0:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self.lock_fd)
            self.lock_fd = -1


class R2bQuiescenceLease:
    """Opaque authority — not reconstructible from metadata or booleans."""

    __slots__ = ("_holder", "_token")

    def __init__(self, holder: _LeaseHolder, token: bytes) -> None:
        if token != _LEASE_SECRET:
            raise R2bQuiescenceLeaseError(
                "R2bQuiescenceLease cannot be constructed by callers"
            )
        self._holder = holder
        self._token = token

    def __bool__(self) -> bool:
        raise R2bQuiescenceLeaseError(
            "R2bQuiescenceLease is not reducible to a boolean authority claim"
        )

    def __reduce__(self) -> Any:
        raise R2bQuiescenceLeaseError("R2bQuiescenceLease is not serializable")

    def __copy__(self) -> R2bQuiescenceLease:
        raise R2bQuiescenceLeaseError("R2bQuiescenceLease cannot be copied")

    def __deepcopy__(self, memo: dict[int, Any]) -> R2bQuiescenceLease:
        raise R2bQuiescenceLeaseError("R2bQuiescenceLease cannot be deep-copied")

    def __getstate__(self) -> Any:
        raise R2bQuiescenceLeaseError("R2bQuiescenceLease is not serializable")

    def __setstate__(self, state: Any) -> None:
        raise R2bQuiescenceLeaseError("R2bQuiescenceLease is not deserializable")

    @property
    def bindings(self) -> _LeaseBindings:
        return self._holder.bindings

    def verify(self) -> None:
        """Fail closed unless live kernel ownership and bindings remain valid."""
        self._holder.verify_live_ownership()

    def release(self) -> None:
        self._holder.release()


def _open_exclusive_lock(path: Path, *, timeout_ms: int) -> tuple[int, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError as exc:
            if time.monotonic() >= deadline:
                os.close(fd)
                raise TimeoutError(
                    f"writer_quiesce_timeout: exclusive lease after {timeout_ms}ms"
                ) from exc
            time.sleep(0.01)
    inode = os.fstat(fd).st_ino
    return fd, inode


def acquire_r2b_quiescence_lease(
    *,
    run_id: str,
    grant_digest: str,
    authority_digest: str,
    lock_path: Path,
    writer_coverage_digest: str,
    open_evidence_digest: str,
    monotonic_deadline: float,
    bound_source_paths: tuple[str, ...],
    phase_bounds: tuple[str, ...] = (),
    implementation_revision: str | None = None,
    timeout_ms: int = 30_000,
) -> R2bQuiescenceLease:
    """Acquire exclusive writer-gate authority bound to live kernel ownership."""
    if monotonic_deadline <= time.monotonic():
        raise R2bQuiescenceLeaseError("monotonic_deadline is already expired")
    path = lock_path.expanduser()
    fd, inode = _open_exclusive_lock(path, timeout_ms=timeout_ms)
    revision = implementation_revision or current_code_revision()
    bindings = _LeaseBindings(
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        gate_path=str(path.resolve(strict=False)),
        gate_inode=inode,
        gate_protocol=WRITER_GATE_PROTOCOL_VERSION,
        coordinator_pid=os.getpid(),
        coordinator_start_time=_proc_start_time(os.getpid()),
        implementation_revision=revision,
        writer_coverage_digest=writer_coverage_digest,
        open_evidence_digest=open_evidence_digest,
        monotonic_start=time.monotonic(),
        monotonic_deadline=monotonic_deadline,
        bound_source_paths=bound_source_paths,
        phase_bounds=phase_bounds,
    )
    holder = _LeaseHolder(bindings=bindings, lock_fd=fd, token=_LEASE_SECRET)
    return R2bQuiescenceLease(holder, _LEASE_SECRET)


def verify_r2b_quiescence_lease(
    lease: R2bQuiescenceLease,
    *,
    expected_run_id: str | None = None,
    expected_grant_digest: str | None = None,
    expected_coverage_digest: str | None = None,
    expected_implementation_revision: str | None = None,
) -> None:
    """Trusted verifier — metadata alone cannot satisfy this check."""
    if not isinstance(lease, R2bQuiescenceLease):
        raise R2bQuiescenceLeaseError("forged capability type")
    lease.verify()
    bindings = lease.bindings
    if expected_run_id is not None and bindings.run_id != expected_run_id:
        raise R2bQuiescenceLeaseError("run_id mismatch")
    if expected_grant_digest is not None and bindings.grant_digest != expected_grant_digest:
        raise R2bQuiescenceLeaseError("grant_digest mismatch")
    if (
        expected_coverage_digest is not None
        and bindings.writer_coverage_digest != expected_coverage_digest
    ):
        raise R2bQuiescenceLeaseError("writer_coverage_digest mismatch")
    if (
        expected_implementation_revision is not None
        and bindings.implementation_revision != expected_implementation_revision
    ):
        raise R2bQuiescenceLeaseError("implementation revision mismatch")


def extend_lease_deadline(*_args: Any, **_kwargs: Any) -> None:
    """Deadline extension is explicitly forbidden."""
    raise R2bQuiescenceLeaseError("lease deadline cannot be extended in place")


def lease_from_serialized_payload(_payload: dict[str, Any]) -> R2bQuiescenceLease:
    """Refuse JSON/dict reconstruction as authority."""
    raise R2bQuiescenceLeaseError(
        "deserialized metadata cannot reconstruct R2bQuiescenceLease authority"
    )


def attempt_pickle_roundtrip(lease: R2bQuiescenceLease) -> None:
    """Adversarial helper for tests — re-raises serialization refusal."""
    pickle.dumps(lease)


def duplicate_lease_via_copy(lease: R2bQuiescenceLease) -> None:
    """Adversarial helper for tests."""
    copy.copy(lease)
