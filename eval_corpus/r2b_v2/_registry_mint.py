"""Private trusted authority registry — lifecycle-gated minting only."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.lock_custodian import LockCustodianError

_PROCESS_MINT_SEAL = secrets.token_hex(32)
_AUTHORITY_EPOCH = 0
_REGISTRY_LOCK = threading.RLock()


class AuthorityRegistryError(RuntimeError):
    """Registry lookup, minting, or cross-slice binding failure."""


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
    composition_seal: str


@dataclass(frozen=True)
class _CustodianBinding:
    custodian: Any
    object_id: int


class _SealedStore(MutableMapping[str, Any]):
    """Registry backing store that rejects ordinary caller mutation."""

    __slots__ = ("_data", "_owner")

    def __init__(self, owner: _TrustedRegistry) -> None:
        self._data: dict[str, Any] = {}
        self._owner = owner

    def _allow(self) -> bool:
        return self._owner._internal_mutation_active

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if not self._allow():
            raise AuthorityRegistryError("direct registry mutation forbidden")
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        if not self._allow():
            raise AuthorityRegistryError("direct registry mutation forbidden")
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        if not self._allow():
            raise AuthorityRegistryError("direct registry mutation forbidden")
        return self._data.pop(key, default)

    def clear(self) -> None:
        if not self._allow():
            raise AuthorityRegistryError("direct registry mutation forbidden")
        self._data.clear()

    def setdefault(self, key: str, default: Any = None) -> Any:
        if not self._allow():
            raise AuthorityRegistryError("direct registry mutation forbidden")
        return self._data.setdefault(key, default)


class _TrustedRegistry:
    """Process-local trusted authority state with lifecycle-gated mutation."""

    __slots__ = (
        "_internal_mutation_active",
        "_lease_records",
        "_coverage_records",
        "_source_records",
        "_diagnostic_tickets",
        "_ticket_provenance",
        "_recently_consumed_tickets",
        "_invalidated",
        "_custodian_refs",
        "_coverage_lease_binding",
        "_lease_dependent_sources",
        "_coverage_dependent_sources",
        "_census_mint_active",
        "_census_expected_digest",
        "_lease_mint_active",
        "_source_compose_active",
    )

    def __init__(self) -> None:
        self._internal_mutation_active = False
        self._lease_records = _SealedStore(self)
        self._coverage_records = _SealedStore(self)
        self._source_records = _SealedStore(self)
        self._diagnostic_tickets = _SealedStore(self)
        self._ticket_provenance = _SealedStore(self)
        self._recently_consumed_tickets = _SealedStore(self)
        self._invalidated: set[str] = set()
        self._custodian_refs = _SealedStore(self)
        self._coverage_lease_binding = _SealedStore(self)
        self._lease_dependent_sources: dict[str, set[str]] = {}
        self._coverage_dependent_sources: dict[str, set[str]] = {}
        self._census_mint_active = False
        self._census_expected_digest: str | None = None
        self._lease_mint_active = False
        self._source_compose_active = False

    @contextmanager
    def _mutation(self) -> Iterator[None]:
        prior = self._internal_mutation_active
        self._internal_mutation_active = True
        try:
            yield
        finally:
            self._internal_mutation_active = prior

    @contextmanager
    def census_mint_window(self, *, coverage_digest: str) -> Iterator[None]:
        if self._census_mint_active:
            raise AuthorityRegistryError("nested census mint window")
        self._census_mint_active = True
        self._census_expected_digest = coverage_digest
        try:
            yield
        finally:
            self._census_mint_active = False
            self._census_expected_digest = None

    @contextmanager
    def lease_acquisition_window(self) -> Iterator[None]:
        if self._lease_mint_active:
            raise AuthorityRegistryError("nested lease acquisition window")
        self._lease_mint_active = True
        try:
            yield
        finally:
            self._lease_mint_active = False

    @contextmanager
    def source_composition_window(self) -> Iterator[None]:
        if self._source_compose_active:
            raise AuthorityRegistryError("nested source composition window")
        self._source_compose_active = True
        try:
            yield
        finally:
            self._source_compose_active = False

    def _new_handle_id(self) -> str:
        return secrets.token_hex(16)

    def _validate_custodian_binding(self, custodian_id: str) -> Any:
        binding = self._custodian_refs.get(custodian_id)
        if binding is None:
            raise AuthorityRegistryError("lock custodian record missing")
        if not isinstance(binding, _CustodianBinding):
            raise AuthorityRegistryError("custodian binding tampered")
        if id(binding.custodian) != binding.object_id:
            raise AuthorityRegistryError("custodian binding identity mismatch")
        return binding.custodian

    def register_lease_custodian(self, custodian_id: str, custodian: Any) -> None:
        if not self._lease_mint_active:
            raise AuthorityRegistryError("custodian registration outside lease lifecycle")
        if custodian_id in self._custodian_refs:
            raise AuthorityRegistryError("custodian id already registered")
        with self._mutation():
            self._custodian_refs[custodian_id] = _CustodianBinding(
                custodian=custodian,
                object_id=id(custodian),
            )

    def lookup_custodian(self, custodian_id: str) -> Any:
        return self._validate_custodian_binding(custodian_id)

    def register_diagnostic_ticket(
        self,
        ticket: DiagnosticMintTicket,
        *,
        provenance_seal: str,
    ) -> None:
        if not self._census_mint_active:
            raise AuthorityRegistryError(
                "diagnostic registration outside canonical census lifecycle"
            )
        expected_digest = self._census_expected_digest
        if expected_digest is None:
            raise AuthorityRegistryError("diagnostic census provenance seal invalid")
        if ticket.evidence.coverage_digest != expected_digest:
            raise AuthorityRegistryError("diagnostic mint ticket digest mismatch")
        with self._mutation():
            self._diagnostic_tickets[ticket.ticket_id] = ticket
            self._ticket_provenance[ticket.ticket_id] = provenance_seal

    def consume_diagnostic_ticket(
        self,
        ticket_id: str | None,
        *,
        coverage_digest: str,
        provenance_seal: str,
    ) -> DiagnosticMintTicket:
        if not ticket_id:
            raise AuthorityRegistryError(
                "diagnostic mint ticket missing — caller cannot mint authority"
            )
        with self._mutation():
            ticket = self._diagnostic_tickets.pop(ticket_id, None)
            if ticket is None:
                raise AuthorityRegistryError(
                    "diagnostic mint ticket invalid or already consumed"
                )
            if self._ticket_provenance.pop(ticket_id, None) != provenance_seal:
                raise AuthorityRegistryError("diagnostic census provenance seal invalid")
            if ticket.evidence.coverage_digest != coverage_digest:
                raise AuthorityRegistryError("diagnostic mint ticket digest mismatch")
            self._recently_consumed_tickets[ticket_id] = ticket
        return ticket

    def mint_coverage_from_consumed_ticket(self, ticket: DiagnosticMintTicket) -> AuthorityHandle:
        with self._mutation():
            expected = self._recently_consumed_tickets.pop(ticket.ticket_id, None)
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
            handle_id = self._new_handle_id()
            self._coverage_records[handle_id] = record
        return AuthorityHandle("coverage", handle_id)

    def mint_lease_handle(self, record: LeaseAuthorityRecord) -> AuthorityHandle:
        if not self._lease_mint_active:
            raise AuthorityRegistryError("lease mint outside canonical acquisition lifecycle")
        with self._mutation():
            handle_id = self._new_handle_id()
            self._lease_records[handle_id] = record
        return AuthorityHandle("lease", handle_id)

    def _bind_coverage_to_lease(
        self,
        *,
        coverage_handle_id: str,
        lease_handle_id: str,
    ) -> None:
        existing = self._coverage_lease_binding.get(coverage_handle_id)
        if existing is not None and existing != lease_handle_id:
            raise AuthorityRegistryError("coverage already bound to a different lease")
        self._coverage_lease_binding[coverage_handle_id] = lease_handle_id

    def _revalidate_live_lease(self, handle: AuthorityHandle) -> LeaseAuthorityRecord:
        record = self.lookup_lease_handle(handle)
        custodian = self._validate_custodian_binding(record.custodian_id)
        try:
            custodian.verify()
        except LockCustodianError as exc:
            raise AuthorityRegistryError("lease prerequisite invalid during issuance") from exc
        return record

    def compose_and_mint_source_authority(
        self,
        *,
        lease_handle: AuthorityHandle,
        coverage_handle: AuthorityHandle,
        open_evidence_digest: str,
    ) -> AuthorityHandle:
        if not self._source_compose_active:
            raise AuthorityRegistryError(
                "source authority mint outside canonical composition lifecycle"
            )
        with self._mutation():
            lease_record = self._revalidate_live_lease(lease_handle)
            coverage_record = self.lookup_coverage_handle(coverage_handle)
            if lease_record.open_evidence_digest != open_evidence_digest:
                raise AuthorityRegistryError("open_evidence_digest mismatch")
            if lease_record.gate_path != coverage_record.gate_path:
                raise AuthorityRegistryError(
                    "gate_path mismatch between lease and trusted coverage"
                )
            if lease_record.gate_protocol != coverage_record.gate_protocol:
                raise AuthorityRegistryError(
                    "gate_protocol mismatch between lease and trusted coverage"
                )
            if lease_record.writer_coverage_digest != coverage_record.coverage_digest:
                raise AuthorityRegistryError(
                    "writer_coverage_digest mismatch — cross-slice binding failed"
                )
            if lease_record.implementation_revision != coverage_record.code_revision:
                raise AuthorityRegistryError(
                    "implementation revision mismatch between lease and coverage"
                )
            self._revalidate_live_lease(lease_handle)
            self._bind_coverage_to_lease(
                coverage_handle_id=coverage_handle.handle_id,
                lease_handle_id=lease_handle.handle_id,
            )
            composition_seal = secrets.token_hex(16)
            record = SourceAuthorityRecord(
                lease_handle_id=lease_handle.handle_id,
                coverage_handle_id=coverage_handle.handle_id,
                authority_epoch=_AUTHORITY_EPOCH,
                run_id=lease_record.run_id,
                coverage_digest=coverage_record.coverage_digest,
                gate_identity=coverage_record.gate_identity,
                gate_path=coverage_record.gate_path,
                open_evidence_digest=open_evidence_digest,
                composition_seal=composition_seal,
            )
            handle_id = self._new_handle_id()
            self._source_records[handle_id] = record
            self._lease_dependent_sources.setdefault(lease_handle.handle_id, set()).add(
                handle_id
            )
            self._coverage_dependent_sources.setdefault(
                coverage_handle.handle_id, set()
            ).add(handle_id)
        return AuthorityHandle("source", handle_id)

    def lookup_lease_handle(self, handle: AuthorityHandle) -> LeaseAuthorityRecord:
        if not isinstance(handle, AuthorityHandle) or handle.kind != "lease":
            raise AuthorityRegistryError("invalid lease authority handle")
        if handle.handle_id in self._invalidated:
            raise AuthorityRegistryError("lease authority handle invalidated")
        record = self._lease_records.get(handle.handle_id)
        if record is None:
            raise AuthorityRegistryError("lease authority handle not registered")
        if record.mint_epoch != _AUTHORITY_EPOCH:
            raise AuthorityRegistryError("lease authority handle epoch invalidated")
        return record

    def lookup_coverage_handle(self, handle: AuthorityHandle) -> CoverageAuthorityRecord:
        if not isinstance(handle, AuthorityHandle) or handle.kind != "coverage":
            raise AuthorityRegistryError("invalid coverage authority handle")
        if handle.handle_id in self._invalidated:
            raise AuthorityRegistryError("coverage authority handle invalidated")
        record = self._coverage_records.get(handle.handle_id)
        if record is None:
            raise AuthorityRegistryError("coverage authority handle not registered")
        if record.mint_epoch != _AUTHORITY_EPOCH:
            raise AuthorityRegistryError("coverage authority handle epoch invalidated")
        if record.mint_seal != _PROCESS_MINT_SEAL:
            raise AuthorityRegistryError("coverage authority mint seal invalid")
        return record

    def lookup_source_handle(self, handle: AuthorityHandle) -> SourceAuthorityRecord:
        if not isinstance(handle, AuthorityHandle) or handle.kind != "source":
            raise AuthorityRegistryError("invalid source authority handle")
        if handle.handle_id in self._invalidated:
            raise AuthorityRegistryError("source authority handle invalidated")
        record = self._source_records.get(handle.handle_id)
        if record is None:
            raise AuthorityRegistryError("source authority handle not registered")
        if record.authority_epoch != _AUTHORITY_EPOCH:
            raise AuthorityRegistryError("source authority handle epoch invalidated")
        lease = AuthorityHandle("lease", record.lease_handle_id)
        coverage = AuthorityHandle("coverage", record.coverage_handle_id)
        self.lookup_lease_handle(lease)
        self.lookup_coverage_handle(coverage)
        bound_lease = self._coverage_lease_binding.get(record.coverage_handle_id)
        if bound_lease != record.lease_handle_id:
            raise AuthorityRegistryError("source authority coverage binding invalid")
        return record

    def _invalidate_source_ids(self, source_ids: set[str]) -> None:
        for source_id in source_ids:
            self._invalidated.add(source_id)
            self._source_records.pop(source_id, None)

    def invalidate_lease_handle(self, handle: AuthorityHandle) -> None:
        with self._mutation():
            record = self._lease_records.pop(handle.handle_id, None)
            self._invalidated.add(handle.handle_id)
            dependent_sources = self._lease_dependent_sources.pop(handle.handle_id, set())
            self._invalidate_source_ids(dependent_sources)
            if record is not None:
                self._custodian_refs.pop(record.custodian_id, None)
                for cov_id, lease_id in list(self._coverage_lease_binding.items()):
                    if lease_id == handle.handle_id:
                        self._coverage_lease_binding.pop(cov_id, None)
                        cov_sources = self._coverage_dependent_sources.pop(cov_id, set())
                        self._invalidate_source_ids(cov_sources)
                        self._invalidated.add(cov_id)
                        self._coverage_records.pop(cov_id, None)

    def release_lease_handle(self, handle: AuthorityHandle) -> LeaseAuthorityRecord:
        record = self.lookup_lease_handle(handle)
        self.invalidate_lease_handle(handle)
        return record

    def invalidate_coverage_handle(self, handle: AuthorityHandle) -> None:
        with self._mutation():
            self._invalidated.add(handle.handle_id)
            self._coverage_records.pop(handle.handle_id, None)
            self._coverage_lease_binding.pop(handle.handle_id, None)
            dependent_sources = self._coverage_dependent_sources.pop(handle.handle_id, set())
            self._invalidate_source_ids(dependent_sources)

    def invalidate_all_authority(self) -> None:
        global _PROCESS_MINT_SEAL, _AUTHORITY_EPOCH  # pylint: disable=global-statement
        with self._mutation():
            for custodian_binding in list(self._custodian_refs.values()):
                if isinstance(custodian_binding, _CustodianBinding):
                    try:
                        custodian_binding.custodian.release()
                    except Exception:  # pylint: disable=broad-except
                        pass
            self._lease_records.clear()
            self._coverage_records.clear()
            self._source_records.clear()
            self._diagnostic_tickets.clear()
            self._ticket_provenance.clear()
            self._recently_consumed_tickets.clear()
            self._invalidated.clear()
            self._coverage_lease_binding.clear()
            self._custodian_refs.clear()
            self._lease_dependent_sources.clear()
            self._coverage_dependent_sources.clear()
        _PROCESS_MINT_SEAL = secrets.token_hex(32)
        _AUTHORITY_EPOCH += 1


_REGISTRY = _TrustedRegistry()

_FORBIDDEN_MODULE_ATTRS = frozenset(
    {
        "_LEASE_RECORDS",
        "_COVERAGE_RECORDS",
        "_SOURCE_RECORDS",
        "_DIAGNOSTIC_TICKETS",
        "_TICKET_PROVENANCE",
        "_RECENTLY_CONSUMED_TICKETS",
        "_INVALIDATED",
        "_CUSTODIAN_REF",
        "_COVERAGE_LEASE_BINDING",
        "_TrustedRegistry",
        "_SealedStore",
        "_REGISTRY",
    }
)


def __getattr__(name: str) -> Any:
    if name in _FORBIDDEN_MODULE_ATTRS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def current_authority_epoch() -> int:
    return _AUTHORITY_EPOCH


def census_mint_window(*, coverage_digest: str) -> Iterator[None]:
    return _REGISTRY.census_mint_window(coverage_digest=coverage_digest)


def lease_acquisition_window() -> Iterator[None]:
    return _REGISTRY.lease_acquisition_window()


def source_composition_window() -> Iterator[None]:
    return _REGISTRY.source_composition_window()


def _register_lease_custodian(custodian_id: str, custodian: Any) -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.register_lease_custodian(custodian_id, custodian)


def lookup_custodian(custodian_id: str) -> Any:
    with _REGISTRY_LOCK:
        return _REGISTRY.lookup_custodian(custodian_id)


def register_diagnostic_ticket(ticket: DiagnosticMintTicket, *, provenance_seal: str) -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.register_diagnostic_ticket(ticket, provenance_seal=provenance_seal)


def consume_diagnostic_ticket(
    ticket_id: str | None,
    *,
    coverage_digest: str,
    provenance_seal: str,
) -> DiagnosticMintTicket:
    with _REGISTRY_LOCK:
        return _REGISTRY.consume_diagnostic_ticket(
            ticket_id,
            coverage_digest=coverage_digest,
            provenance_seal=provenance_seal,
        )


def mint_coverage_from_consumed_ticket(ticket: DiagnosticMintTicket) -> AuthorityHandle:
    with _REGISTRY_LOCK:
        return _REGISTRY.mint_coverage_from_consumed_ticket(ticket)


def mint_lease_handle(record: LeaseAuthorityRecord) -> AuthorityHandle:
    with _REGISTRY_LOCK:
        return _REGISTRY.mint_lease_handle(record)


def compose_and_mint_source_authority(
    *,
    lease_handle: AuthorityHandle,
    coverage_handle: AuthorityHandle,
    open_evidence_digest: str,
) -> AuthorityHandle:
    with _REGISTRY_LOCK:
        return _REGISTRY.compose_and_mint_source_authority(
            lease_handle=lease_handle,
            coverage_handle=coverage_handle,
            open_evidence_digest=open_evidence_digest,
        )


def lookup_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    with _REGISTRY_LOCK:
        return _REGISTRY.lookup_lease_handle(handle)


def lookup_coverage_handle(handle: AuthorityHandle) -> CoverageAuthorityRecord:
    with _REGISTRY_LOCK:
        return _REGISTRY.lookup_coverage_handle(handle)


def lookup_source_handle(handle: AuthorityHandle) -> SourceAuthorityRecord:
    with _REGISTRY_LOCK:
        return _REGISTRY.lookup_source_handle(handle)


def invalidate_lease_handle(handle: AuthorityHandle) -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.invalidate_lease_handle(handle)


def release_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    with _REGISTRY_LOCK:
        return _REGISTRY.release_lease_handle(handle)


def invalidate_coverage_handle(handle: AuthorityHandle) -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.invalidate_coverage_handle(handle)


def invalidate_all_authority() -> None:
    with _REGISTRY_LOCK:
        _REGISTRY.invalidate_all_authority()
