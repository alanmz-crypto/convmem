# pylint: disable=too-many-instance-attributes,too-many-arguments
"""Opaque process-local R2b v2 quiescence lease (I2)."""

from __future__ import annotations

import copy
import hashlib
import os
import pickle
import re
import time
from pathlib import Path
from typing import Any

from chroma_write_store import _proc_start_time

from eval_corpus.r2b_v2._authority_capability import (
    issue_lease_capability,
    trust_class_for_gate_policy,
)
from eval_corpus.r2b_v2._registry_mint import (
    mint_lease_handle,
)
from eval_corpus.r2b_v2.coverage.inventory import resolve_r2b_implementation_revision
from eval_corpus.r2b_v2.authority_registry import (
    AuthorityHandle,
    AuthorityRegistryError,
    LeaseAuthorityRecord,
    current_authority_epoch,
    invalidate_lease_handle,
    lookup_custodian,
    lookup_lease_handle,
    release_lease_handle,
)
from eval_corpus.r2b_v2.gate_policy import GatePolicy, resolve_trusted_gate_policy
from eval_corpus.r2b_v2.lock_custodian import LockCustodian, LockCustodianError, spawn_lock_custodian
from eval_corpus.r2b_v2.trusted import (
    authority_key,
    consume_authority,
    is_authority_consumed,
    register_active_authority,
)


class R2bQuiescenceLeaseError(RuntimeError):
    """Lease acquisition, verification, or release failure."""


class _LeaseBindingsView:
    """Read-only lease field view backed by the registry record."""

    __slots__ = ("_monotonic_start", "_record")

    def __init__(self, record: LeaseAuthorityRecord, monotonic_start: float) -> None:
        self._record = record
        self._monotonic_start = monotonic_start

    @property
    def monotonic_start(self) -> float:
        return self._monotonic_start

    def __getattr__(self, name: str) -> Any:
        return getattr(self._record, name)


class _LeaseHolder:
    __slots__ = ("bindings", "custodian_id", "handle", "ownership_active", "_custodian")

    def __init__(
        self,
        *,
        bindings: _LeaseBindingsView,
        custodian_id: str,
        handle: AuthorityHandle,
        custodian: LockCustodian,
    ) -> None:
        self.bindings = bindings
        self.custodian_id = custodian_id
        self.handle = handle
        self.ownership_active = True
        self._custodian = custodian

    @property
    def custodian(self) -> LockCustodian:
        return self._custodian

    def verify_live_ownership(self) -> None:
        if not self.ownership_active:
            raise R2bQuiescenceLeaseError("lease ownership was released or consumed")
        try:
            lookup_lease_handle(self.handle)
        except AuthorityRegistryError as exc:
            raise R2bQuiescenceLeaseError("lease authority handle invalid") from exc
        if time.monotonic() > self.bindings.monotonic_deadline:
            raise R2bQuiescenceLeaseError("lease deadline expired")
        if os.getpid() != self.bindings.coordinator_pid:
            raise R2bQuiescenceLeaseError("coordinator PID mismatch")
        if _proc_start_time(self.bindings.coordinator_pid) != self.bindings.coordinator_start_time:
            raise R2bQuiescenceLeaseError("coordinator process start identity mismatch")
        try:
            st = os.stat(self.bindings.gate_path)
        except OSError as exc:
            raise R2bQuiescenceLeaseError("cannot stat gate path") from exc
        if st.st_ino != self.bindings.gate_inode:
            raise R2bQuiescenceLeaseError("gate inode identity mismatch")
        try:
            lookup_custodian(self.custodian_id).verify()
        except (LockCustodianError, AuthorityRegistryError) as exc:
            raise R2bQuiescenceLeaseError(
                "original authorized holder no longer owns exclusive kernel lock"
            ) from exc

    def release(self) -> None:
        key = authority_key(
            self.bindings.run_id, self.bindings.grant_digest, self.bindings.authority_digest
        )
        self.ownership_active = False
        try:
            lookup_custodian(self.custodian_id).release()
        except AuthorityRegistryError:
            pass
        finally:
            release_lease_handle(self.handle)
        consume_authority(key)


class R2bQuiescenceLease:
    __slots__ = ("_handle", "_holder")

    def __init__(self, holder: _LeaseHolder) -> None:
        if not isinstance(holder, _LeaseHolder):
            raise R2bQuiescenceLeaseError(
                "R2bQuiescenceLease cannot be constructed by callers"
            )
        try:
            lookup_lease_handle(holder.handle)
        except AuthorityRegistryError as exc:
            raise R2bQuiescenceLeaseError(
                "R2bQuiescenceLease cannot be constructed by callers"
            ) from exc
        self._holder = holder
        self._handle = holder.handle

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
    def bindings(self) -> _LeaseBindingsView:
        return self._holder.bindings

    @property
    def authority_handle(self) -> AuthorityHandle:
        return self._handle

    def verify(self) -> None:
        self._holder.verify_live_ownership()

    def release(self) -> None:
        self._holder.release()


def acquire_r2b_quiescence_lease_physical(
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
    implementation_revision: str | None = None,
) -> _LeaseHolder:
    """Physical kernel acquisition — not authority commitment."""
    if monotonic_deadline <= time.monotonic():
        raise R2bQuiescenceLeaseError("monotonic_deadline is already expired")
    if timeout_ms <= 0:
        raise R2bQuiescenceLeaseError("timeout_ms must be explicitly positive")
    key = authority_key(run_id, grant_digest, authority_digest)
    if is_authority_consumed(key):
        raise R2bQuiescenceLeaseError(
            "authority chain already consumed — same-run reacquisition refused"
        )
    policy = resolve_trusted_gate_policy(
        gate_policy,
        test_lock_path,
        error_cls=R2bQuiescenceLeaseError,
        mutual_exclusion_message="gate_policy and test_lock_path are mutually exclusive",
        untrusted_policy_message="caller-supplied gate policy cannot mint trusted authority",
    )
    path = policy.resolve_path()
    if test_lock_path is not None:
        revision = implementation_revision or hashlib.sha256(
            b"r2b-v2-test:default-lease"
        ).hexdigest()[:40]
        if revision == "unknown" or not re.match(r"^[0-9a-f]{40}$", revision):
            raise R2bQuiescenceLeaseError("trusted implementation revision is unavailable")
    else:
        revision = resolve_r2b_implementation_revision()
        if revision == "unknown" or not re.match(r"^[0-9a-f]{40}$", revision):
            raise R2bQuiescenceLeaseError("trusted implementation revision is unavailable")
        if implementation_revision is not None and implementation_revision != revision:
            raise R2bQuiescenceLeaseError(
                "caller-supplied implementation revision cannot mint trusted authority"
            )
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    custodian: LockCustodian | None = None
    while True:
        try:
            custodian = spawn_lock_custodian(str(path))
            break
        except LockCustodianError as exc:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"writer_quiesce_timeout: exclusive lease after {timeout_ms}ms"
                ) from exc
            time.sleep(0.01)
    assert custodian is not None
    custodian_id = f"lease-{run_id}-{time.monotonic_ns()}"
    monotonic_start = time.monotonic()
    trust_class = trust_class_for_gate_policy(policy.policy_class)
    lease_capability = issue_lease_capability(
        custodian_id=custodian_id,
        gate_path=str(path),
        gate_inode=custodian.inode,
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        trust_class=trust_class,
    )
    record = LeaseAuthorityRecord(
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        gate_path=str(path),
        gate_inode=custodian.inode,
        gate_identity=policy.canonical_identity,
        gate_protocol=policy.protocol,
        coordinator_pid=os.getpid(),
        coordinator_start_time=_proc_start_time(os.getpid()),
        implementation_revision=revision,
        writer_coverage_digest=writer_coverage_digest,
        open_evidence_digest=open_evidence_digest,
        monotonic_deadline=monotonic_deadline,
        bound_source_paths=bound_source_paths,
        phase_bounds=phase_bounds,
        custodian_id=custodian_id,
        mint_epoch=current_authority_epoch(),
        trust_class=trust_class,
    )
    register_active_authority(key)
    handle = mint_lease_handle(lease_capability, record, custodian=custodian)
    bindings = _LeaseBindingsView(record, monotonic_start)
    return _LeaseHolder(
        bindings=bindings,
        custodian_id=custodian_id,
        handle=handle,
        custodian=custodian,
    )


def invalidate_pending_lease(holder: _LeaseHolder) -> None:
    holder.ownership_active = False
    invalidate_lease_handle(holder.handle)


def release_pending_lease_kernel(holder: _LeaseHolder) -> None:
    if holder.ownership_active:
        holder.ownership_active = False
    lookup_custodian(holder.custodian_id).release()
    release_lease_handle(holder.handle)
    key = authority_key(
        holder.bindings.run_id,
        holder.bindings.grant_digest,
        holder.bindings.authority_digest,
    )
    consume_authority(key)


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
    implementation_revision: str | None = None,
) -> R2bQuiescenceLease:
    holder = acquire_r2b_quiescence_lease_physical(
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        writer_coverage_digest=writer_coverage_digest,
        open_evidence_digest=open_evidence_digest,
        monotonic_deadline=monotonic_deadline,
        bound_source_paths=bound_source_paths,
        timeout_ms=timeout_ms,
        gate_policy=gate_policy,
        test_lock_path=test_lock_path,
        phase_bounds=phase_bounds,
        implementation_revision=implementation_revision,
    )
    return R2bQuiescenceLease(holder)


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
