# pylint: disable=too-many-instance-attributes,too-many-arguments
"""Opaque process-local R2b v2 quiescence lease (I2)."""

from __future__ import annotations

import copy
import fcntl
import multiprocessing as mp
import os
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chroma_write_store import _proc_start_time, current_code_revision

from eval_corpus.r2b_v2.gate_policy import GatePolicy, production_gate_policy, test_gate_policy
from eval_corpus.r2b_v2.trusted import (
    authority_key,
    consume_authority,
    is_authority_consumed,
    lease_token,
    register_active_authority,
)


class R2bQuiescenceLeaseError(RuntimeError):
    """Lease acquisition, verification, or release failure."""


def _flock_probe_worker(lock_path: str, result_queue: mp.Queue) -> None:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result_queue.put("available")
    except BlockingIOError:
        result_queue.put("held")
    finally:
        os.close(fd)


def _probe_exclusive_available(lock_path: str) -> bool:
    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_flock_probe_worker, args=(lock_path, queue))
    proc.start()
    proc.join(timeout=5)
    if proc.exitcode != 0 or queue.empty():
        raise R2bQuiescenceLeaseError("lock ownership probe failed")
    return queue.get() == "available"


@dataclass(frozen=True)
class _LeaseBindings:
    run_id: str
    grant_digest: str
    authority_digest: str
    gate_path: str
    gate_inode: int
    gate_identity: str
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
    __slots__ = ("bindings", "lock_fd", "ownership_active", "token")

    def __init__(self, *, bindings: _LeaseBindings, lock_fd: int, token: bytes) -> None:
        self.bindings = bindings
        self.lock_fd = lock_fd
        self.token = token
        self.ownership_active = True

    def verify_live_ownership(self) -> None:
        if self.token != lease_token():
            raise R2bQuiescenceLeaseError("lease token invalid after fork or forgery attempt")
        if not self.ownership_active:
            raise R2bQuiescenceLeaseError("lease ownership was released or consumed")
        if self.lock_fd < 0:
            raise R2bQuiescenceLeaseError("lease lock descriptor is closed")
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
        if _probe_exclusive_available(self.bindings.gate_path):
            raise R2bQuiescenceLeaseError(
                "exclusive kernel lock is not held — live ownership lost"
            )

    def release(self) -> None:
        key = authority_key(
            self.bindings.run_id, self.bindings.grant_digest, self.bindings.authority_digest
        )
        self.ownership_active = False
        if self.lock_fd >= 0:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self.lock_fd)
            self.lock_fd = -1
        consume_authority(key)


class R2bQuiescenceLease:
    __slots__ = ("_holder", "_token")

    def __init__(self, holder: _LeaseHolder, token: bytes) -> None:
        if token != lease_token():
            raise R2bQuiescenceLeaseError("R2bQuiescenceLease cannot be constructed by callers")
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
        if self._token != lease_token():
            raise R2bQuiescenceLeaseError("lease token invalid after fork or forgery attempt")
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
    return fd, os.fstat(fd).st_ino


def acquire_r2b_quiescence_lease(
    *,
    run_id: str,
    grant_digest: str,
    authority_digest: str,
    writer_coverage_digest: str,
    open_evidence_digest: str,
    monotonic_deadline: float,
    bound_source_paths: tuple[str, ...],
    timeout_ms: int,
    gate_policy: GatePolicy | None = None,
    test_lock_path: Path | None = None,
    phase_bounds: tuple[str, ...] = (),
) -> R2bQuiescenceLease:
    if monotonic_deadline <= time.monotonic():
        raise R2bQuiescenceLeaseError("monotonic_deadline is already expired")
    if timeout_ms <= 0:
        raise R2bQuiescenceLeaseError("timeout_ms must be explicitly positive")
    key = authority_key(run_id, grant_digest, authority_digest)
    if is_authority_consumed(key):
        raise R2bQuiescenceLeaseError(
            "authority chain already consumed — same-run reacquisition refused"
        )
    if gate_policy is not None and test_lock_path is not None:
        raise R2bQuiescenceLeaseError("gate_policy and test_lock_path are mutually exclusive")
    if gate_policy is None:
        policy = test_gate_policy(test_lock_path) if test_lock_path is not None else production_gate_policy()
    else:
        policy = gate_policy
    path = policy.resolve_path()
    revision = current_code_revision()
    if revision == "unknown":
        raise R2bQuiescenceLeaseError("trusted implementation revision is unavailable")
    fd, inode = _open_exclusive_lock(path, timeout_ms=timeout_ms)
    bindings = _LeaseBindings(
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        gate_path=str(path),
        gate_inode=inode,
        gate_identity=policy.canonical_identity,
        gate_protocol=policy.protocol,
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
    register_active_authority(key)
    holder = _LeaseHolder(bindings=bindings, lock_fd=fd, token=lease_token())
    return R2bQuiescenceLease(holder, lease_token())


def verify_r2b_quiescence_lease(
    lease: R2bQuiescenceLease,
    *,
    expected_run_id: str | None = None,
    expected_grant_digest: str | None = None,
    expected_authority_digest: str | None = None,
    expected_coverage_digest: str | None = None,
    expected_implementation_revision: str | None = None,
    expected_gate_identity: str | None = None,
) -> None:
    if not isinstance(lease, R2bQuiescenceLease):
        raise R2bQuiescenceLeaseError("forged capability type")
    lease.verify()
    bindings = lease.bindings
    if expected_run_id is not None and bindings.run_id != expected_run_id:
        raise R2bQuiescenceLeaseError("run_id mismatch")
    if expected_grant_digest is not None and bindings.grant_digest != expected_grant_digest:
        raise R2bQuiescenceLeaseError("grant_digest mismatch")
    if expected_authority_digest is not None and bindings.authority_digest != expected_authority_digest:
        raise R2bQuiescenceLeaseError("authority_digest mismatch")
    if expected_coverage_digest is not None and bindings.writer_coverage_digest != expected_coverage_digest:
        raise R2bQuiescenceLeaseError("writer_coverage_digest mismatch")
    if (
        expected_implementation_revision is not None
        and bindings.implementation_revision != expected_implementation_revision
    ):
        raise R2bQuiescenceLeaseError("implementation revision mismatch")
    if expected_gate_identity is not None and bindings.gate_identity != expected_gate_identity:
        raise R2bQuiescenceLeaseError("gate identity mismatch")


def extend_lease_deadline(*_args: Any, **_kwargs: Any) -> None:
    raise R2bQuiescenceLeaseError("lease deadline cannot be extended in place")


def lease_from_serialized_payload(_payload: dict[str, Any]) -> R2bQuiescenceLease:
    raise R2bQuiescenceLeaseError(
        "deserialized metadata cannot reconstruct R2bQuiescenceLease authority"
    )


def attempt_pickle_roundtrip(lease: R2bQuiescenceLease) -> None:
    pickle.dumps(lease)


def duplicate_lease_via_copy(lease: R2bQuiescenceLease) -> None:
    copy.copy(lease)
