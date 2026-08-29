"""Private registry minting — not part of the public R2b v2 import surface."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity

_PROCESS_MINT_SEAL = secrets.token_hex(32)
_AUTHORITY_EPOCH = 0

_LEASE_RECORDS: dict[str, Any] = {}
_COVERAGE_RECORDS: dict[str, Any] = {}
_SOURCE_RECORDS: dict[str, Any] = {}
_DIAGNOSTIC_TICKETS: dict[str, Any] = {}
_TICKET_PROVENANCE: dict[str, str] = {}
_RECENTLY_CONSUMED_TICKETS: dict[str, DiagnosticMintTicket] = {}
_INVALIDATED: set[str] = set()
_CUSTODIAN_REF: dict[str, Any] = {}
_COVERAGE_LEASE_BINDING: dict[str, str] = {}


@dataclass(frozen=True)
class AuthorityHandle:
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
    mint_epoch: int


@dataclass(frozen=True)
class CoverageAuthorityRecord(CoverageEvidenceIdentity):
    mint_seal: str
    consumed_ticket_id: str
    mint_epoch: int


@dataclass(frozen=True)
class DiagnosticMintTicket:
    ticket_id: str
    evidence: CoverageEvidenceIdentity


@dataclass(frozen=True)
class SourceAuthorityRecord:  # pylint: disable=too-many-instance-attributes
    lease_handle_id: str
    coverage_handle_id: str
    authority_epoch: int
    run_id: str
    coverage_digest: str
    gate_identity: str
    gate_path: str
    open_evidence_digest: str


class AuthorityRegistryError(RuntimeError):
    """Registry lookup, minting, or cross-slice binding failure."""


def current_authority_epoch() -> int:
    return _AUTHORITY_EPOCH


def _new_handle_id() -> str:
    return secrets.token_hex(16)


def _register_lease_custodian(custodian_id: str, custodian: Any) -> None:
    if custodian_id in _CUSTODIAN_REF:
        raise AuthorityRegistryError("custodian id already registered")
    _CUSTODIAN_REF[custodian_id] = custodian


def lookup_custodian(custodian_id: str) -> Any:
    custodian = _CUSTODIAN_REF.get(custodian_id)
    if custodian is None:
        raise AuthorityRegistryError("lock custodian record missing")
    return custodian


def register_diagnostic_ticket(ticket: DiagnosticMintTicket, *, provenance_seal: str) -> None:
    _DIAGNOSTIC_TICKETS[ticket.ticket_id] = ticket
    _TICKET_PROVENANCE[ticket.ticket_id] = provenance_seal


def consume_diagnostic_ticket(
    ticket_id: str | None,
    *,
    coverage_digest: str,
    provenance_seal: str,
) -> DiagnosticMintTicket:
    if not ticket_id:
        raise AuthorityRegistryError("diagnostic mint ticket missing — caller cannot mint authority")
    ticket = _DIAGNOSTIC_TICKETS.pop(ticket_id, None)
    if ticket is None:
        raise AuthorityRegistryError("diagnostic mint ticket invalid or already consumed")
    if _TICKET_PROVENANCE.pop(ticket_id, None) != provenance_seal:
        raise AuthorityRegistryError("diagnostic census provenance seal invalid")
    if ticket.evidence.coverage_digest != coverage_digest:
        raise AuthorityRegistryError("diagnostic mint ticket digest mismatch")
    _RECENTLY_CONSUMED_TICKETS[ticket_id] = ticket
    return ticket


def mint_coverage_from_consumed_ticket(ticket: DiagnosticMintTicket) -> AuthorityHandle:
    expected = _RECENTLY_CONSUMED_TICKETS.pop(ticket.ticket_id, None)
    if expected is None or expected != ticket:
        raise AuthorityRegistryError("coverage mint requires consumed diagnostic ticket")
    record = CoverageAuthorityRecord(
        code_revision=ticket.evidence.code_revision,
        inventory_digest=ticket.evidence.inventory_digest,
        runtime_census_digest=ticket.evidence.runtime_census_digest,
        coverage_digest=ticket.evidence.coverage_digest,
        gate_identity=ticket.evidence.gate_identity,
        gate_path=ticket.evidence.gate_path,
        gate_protocol=ticket.evidence.gate_protocol,
        mint_seal=_PROCESS_MINT_SEAL,
        consumed_ticket_id=ticket.ticket_id,
        mint_epoch=_AUTHORITY_EPOCH,
    )
    handle_id = _new_handle_id()
    _COVERAGE_RECORDS[handle_id] = record
    return AuthorityHandle("coverage", handle_id)


def mint_lease_handle(record: LeaseAuthorityRecord) -> AuthorityHandle:
    handle_id = _new_handle_id()
    _LEASE_RECORDS[handle_id] = record
    return AuthorityHandle("lease", handle_id)


def _bind_coverage_to_lease(*, coverage_handle_id: str, lease_handle_id: str) -> None:
    existing = _COVERAGE_LEASE_BINDING.get(coverage_handle_id)
    if existing is not None and existing != lease_handle_id:
        raise AuthorityRegistryError("coverage already bound to a different lease")
    _COVERAGE_LEASE_BINDING[coverage_handle_id] = lease_handle_id


def compose_and_mint_source_authority(
    *,
    lease_handle: AuthorityHandle,
    coverage_handle: AuthorityHandle,
    open_evidence_digest: str,
) -> AuthorityHandle:
    """Mint source authority only from validated lease+coverage composition."""
    lease_record = lookup_lease_handle(lease_handle)
    coverage_record = lookup_coverage_handle(coverage_handle)
    if lease_record.open_evidence_digest != open_evidence_digest:
        raise AuthorityRegistryError("open_evidence_digest mismatch")
    if lease_record.gate_path != coverage_record.gate_path:
        raise AuthorityRegistryError("gate_path mismatch between lease and trusted coverage")
    if lease_record.gate_protocol != coverage_record.gate_protocol:
        raise AuthorityRegistryError("gate_protocol mismatch between lease and trusted coverage")
    if lease_record.writer_coverage_digest != coverage_record.coverage_digest:
        raise AuthorityRegistryError("writer_coverage_digest mismatch — cross-slice binding failed")
    if lease_record.implementation_revision != coverage_record.code_revision:
        raise AuthorityRegistryError("implementation revision mismatch between lease and coverage")
    _bind_coverage_to_lease(
        coverage_handle_id=coverage_handle.handle_id,
        lease_handle_id=lease_handle.handle_id,
    )
    record = SourceAuthorityRecord(
        lease_handle_id=lease_handle.handle_id,
        coverage_handle_id=coverage_handle.handle_id,
        authority_epoch=_AUTHORITY_EPOCH,
        run_id=lease_record.run_id,
        coverage_digest=coverage_record.coverage_digest,
        gate_identity=coverage_record.gate_identity,
        gate_path=coverage_record.gate_path,
        open_evidence_digest=open_evidence_digest,
    )
    handle_id = _new_handle_id()
    _SOURCE_RECORDS[handle_id] = record
    return AuthorityHandle("source", handle_id)


def lookup_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    if not isinstance(handle, AuthorityHandle) or handle.kind != "lease":
        raise AuthorityRegistryError("invalid lease authority handle")
    if handle.handle_id in _INVALIDATED:
        raise AuthorityRegistryError("lease authority handle invalidated")
    record = _LEASE_RECORDS.get(handle.handle_id)
    if record is None:
        raise AuthorityRegistryError("lease authority handle not registered")
    if record.mint_epoch != _AUTHORITY_EPOCH:
        raise AuthorityRegistryError("lease authority handle epoch invalidated")
    return record


def lookup_coverage_handle(handle: AuthorityHandle) -> CoverageAuthorityRecord:
    if not isinstance(handle, AuthorityHandle) or handle.kind != "coverage":
        raise AuthorityRegistryError("invalid coverage authority handle")
    if handle.handle_id in _INVALIDATED:
        raise AuthorityRegistryError("coverage authority handle invalidated")
    record = _COVERAGE_RECORDS.get(handle.handle_id)
    if record is None:
        raise AuthorityRegistryError("coverage authority handle not registered")
    if record.mint_epoch != _AUTHORITY_EPOCH:
        raise AuthorityRegistryError("coverage authority handle epoch invalidated")
    if record.mint_seal != _PROCESS_MINT_SEAL:
        raise AuthorityRegistryError("coverage authority mint seal invalid")
    return record


def lookup_source_handle(handle: AuthorityHandle) -> SourceAuthorityRecord:
    if not isinstance(handle, AuthorityHandle) or handle.kind != "source":
        raise AuthorityRegistryError("invalid source authority handle")
    if handle.handle_id in _INVALIDATED:
        raise AuthorityRegistryError("source authority handle invalidated")
    record = _SOURCE_RECORDS.get(handle.handle_id)
    if record is None:
        raise AuthorityRegistryError("source authority handle not registered")
    if record.authority_epoch != _AUTHORITY_EPOCH:
        raise AuthorityRegistryError("source authority handle epoch invalidated")
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


def invalidate_coverage_handle(handle: AuthorityHandle) -> None:
    _INVALIDATED.add(handle.handle_id)
    _COVERAGE_RECORDS.pop(handle.handle_id, None)
    _COVERAGE_LEASE_BINDING.pop(handle.handle_id, None)


def invalidate_all_authority() -> None:
    global _PROCESS_MINT_SEAL, _AUTHORITY_EPOCH  # pylint: disable=global-statement
    _LEASE_RECORDS.clear()
    _COVERAGE_RECORDS.clear()
    _SOURCE_RECORDS.clear()
    _DIAGNOSTIC_TICKETS.clear()
    _TICKET_PROVENANCE.clear()
    _RECENTLY_CONSUMED_TICKETS.clear()
    _INVALIDATED.clear()
    _COVERAGE_LEASE_BINDING.clear()
    _PROCESS_MINT_SEAL = secrets.token_hex(32)
    _AUTHORITY_EPOCH += 1
    for custodian in list(_CUSTODIAN_REF.values()):
        try:
            custodian.release()
        except Exception:  # pylint: disable=broad-except
            pass
    _CUSTODIAN_REF.clear()
