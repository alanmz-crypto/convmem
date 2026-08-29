"""Process-local trusted authority registry for R2b v2 lease and coverage proofs."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity


class AuthorityRegistryError(RuntimeError):
    """Registry lookup, minting, or cross-slice binding failure."""


@dataclass(frozen=True)
class AuthorityHandle:
    """Opaque capability identity — not forgeable from bytes or constructors."""

    kind: str
    handle_id: str


@dataclass(frozen=True)
class LeaseAuthorityRecord:  # pylint: disable=too-many-instance-attributes
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
    monotonic_deadline: float
    bound_source_paths: tuple[str, ...]
    phase_bounds: tuple[str, ...]
    custodian_id: str


@dataclass(frozen=True)
class CoverageAuthorityRecord(CoverageEvidenceIdentity):
    """Registry-backed trusted coverage evidence."""


@dataclass(frozen=True)
class DiagnosticMintTicket:
    ticket_id: str
    evidence: CoverageEvidenceIdentity


_LEASE_RECORDS: dict[str, LeaseAuthorityRecord] = {}
_COVERAGE_RECORDS: dict[str, CoverageAuthorityRecord] = {}
_DIAGNOSTIC_TICKETS: dict[str, DiagnosticMintTicket] = {}
_INVALIDATED: set[str] = set()
_CUSTODIAN_REF: dict[str, Any] = {}


def _new_handle_id() -> str:
    return secrets.token_hex(16)


def register_custodian(custodian_id: str, custodian: Any) -> None:
    _CUSTODIAN_REF[custodian_id] = custodian


def lookup_custodian(custodian_id: str) -> Any:
    custodian = _CUSTODIAN_REF.get(custodian_id)
    if custodian is None:
        raise AuthorityRegistryError("lock custodian record missing")
    return custodian


def mint_lease_handle(record: LeaseAuthorityRecord) -> AuthorityHandle:
    handle_id = _new_handle_id()
    _LEASE_RECORDS[handle_id] = record
    return AuthorityHandle("lease", handle_id)


def lookup_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    if not isinstance(handle, AuthorityHandle) or handle.kind != "lease":
        raise AuthorityRegistryError("invalid lease authority handle")
    if handle.handle_id in _INVALIDATED:
        raise AuthorityRegistryError("lease authority handle invalidated")
    record = _LEASE_RECORDS.get(handle.handle_id)
    if record is None:
        raise AuthorityRegistryError("lease authority handle not registered")
    return record


def invalidate_lease_handle(handle: AuthorityHandle) -> None:
    record = _LEASE_RECORDS.pop(handle.handle_id, None)
    _INVALIDATED.add(handle.handle_id)
    if record is not None:
        _CUSTODIAN_REF.pop(record.custodian_id, None)


def release_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    record = lookup_lease_handle(handle)
    invalidate_lease_handle(handle)
    return record


def register_diagnostic_ticket(ticket: DiagnosticMintTicket) -> None:
    _DIAGNOSTIC_TICKETS[ticket.ticket_id] = ticket


def consume_diagnostic_ticket(ticket_id: str | None, *, coverage_digest: str) -> DiagnosticMintTicket:
    if not ticket_id:
        raise AuthorityRegistryError("diagnostic mint ticket missing — caller cannot mint authority")
    ticket = _DIAGNOSTIC_TICKETS.pop(ticket_id, None)
    if ticket is None:
        raise AuthorityRegistryError("diagnostic mint ticket invalid or already consumed")
    if ticket.evidence.coverage_digest != coverage_digest:
        raise AuthorityRegistryError("diagnostic mint ticket digest mismatch")
    return ticket


def mint_coverage_handle(record: CoverageAuthorityRecord) -> AuthorityHandle:
    handle_id = _new_handle_id()
    _COVERAGE_RECORDS[handle_id] = record
    return AuthorityHandle("coverage", handle_id)


def lookup_coverage_handle(handle: AuthorityHandle) -> CoverageAuthorityRecord:
    if not isinstance(handle, AuthorityHandle) or handle.kind != "coverage":
        raise AuthorityRegistryError("invalid coverage authority handle")
    if handle.handle_id in _INVALIDATED:
        raise AuthorityRegistryError("coverage authority handle invalidated")
    record = _COVERAGE_RECORDS.get(handle.handle_id)
    if record is None:
        raise AuthorityRegistryError("coverage authority handle not registered")
    return record


def invalidate_coverage_handle(handle: AuthorityHandle) -> None:
    _INVALIDATED.add(handle.handle_id)
    _COVERAGE_RECORDS.pop(handle.handle_id, None)


def invalidate_all_authority() -> None:
    _LEASE_RECORDS.clear()
    _COVERAGE_RECORDS.clear()
    _DIAGNOSTIC_TICKETS.clear()
    _INVALIDATED.clear()
    for custodian in list(_CUSTODIAN_REF.values()):
        try:
            custodian.release()
        except Exception:  # pylint: disable=broad-except
            pass
    _CUSTODIAN_REF.clear()
