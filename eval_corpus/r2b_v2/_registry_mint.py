"""Private trusted authority registry — capability-gated minting only."""

from __future__ import annotations

import secrets
import threading
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from eval_corpus.r2b_v2._authority_capability import (
    AuthorityMintCapability,
    verify_live_custodian_lock,
)
from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.lock_custodian import LockCustodianError


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
    trust_class: str


@dataclass(frozen=True)
class CoverageAuthorityRecord(CoverageEvidenceIdentity):
    mint_seal: str
    consumed_ticket_id: str
    mint_epoch: int
    trust_class: str


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
    trust_class: str


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

    def _guard_mutation(self) -> None:
        if not self._owner._internal_mutation_active:  # pylint: disable=protected-access
            raise AuthorityRegistryError("direct registry mutation forbidden")

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._guard_mutation()
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        self._guard_mutation()
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def pop(self, key: str, default: Any = None) -> Any:
        self._guard_mutation()
        return self._data.pop(key, default)

    def clear(self) -> None:
        self._guard_mutation()
        self._data.clear()

    def setdefault(self, key: str, default: Any = None) -> Any:
        self._guard_mutation()
        return self._data.setdefault(key, default)


class _TrustedRegistry:
    """Process-local trusted authority state with capability-gated mutation."""

    # pylint: disable=too-many-instance-attributes

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
        "_process_mint_seal",
        "_authority_epoch",
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
        self._process_mint_seal = secrets.token_hex(32)
        self._authority_epoch = 0

    @contextmanager
    def _mutation(self) -> Iterator[None]:
        prior = self._internal_mutation_active
        self._internal_mutation_active = True
        try:
            yield
        finally:
            self._internal_mutation_active = prior

    def _new_handle_id(self) -> str:
        return secrets.token_hex(16)

    def _census_binding(self, evidence: CoverageEvidenceIdentity) -> dict[str, Any]:
        return {
            "coverage_digest": evidence.coverage_digest,
            "gate_identity": evidence.gate_identity,
            "code_revision": evidence.code_revision,
        }

    def _validate_custodian_binding(self, custodian_id: str) -> Any:
        binding = self._custodian_refs.get(custodian_id)
        if binding is None:
            raise AuthorityRegistryError("lock custodian record missing")
        if not isinstance(binding, _CustodianBinding):
            raise AuthorityRegistryError("custodian binding tampered")
        if id(binding.custodian) != binding.object_id:
            raise AuthorityRegistryError("custodian binding identity mismatch")
        try:
            verify_live_custodian_lock(binding.custodian)
        except LockCustodianError as exc:
            raise AuthorityRegistryError(
                "custodian no longer possesses exclusive kernel lock"
            ) from exc
        return binding.custodian

    def register_diagnostic_ticket(
        self,
        capability: AuthorityMintCapability,
        ticket: DiagnosticMintTicket,
        *,
        provenance_seal: str,
    ) -> None:
        binding = self._census_binding(ticket.evidence)
        trust_class = capability._consume_census_register(binding=binding)  # pylint: disable=protected-access
        with self._mutation():
            self._diagnostic_tickets[ticket.ticket_id] = (ticket, trust_class)
            self._ticket_provenance[ticket.ticket_id] = provenance_seal

    def finalize_diagnostic_and_mint_coverage(
        self,
        capability: AuthorityMintCapability,
        ticket_id: str | None,
        *,
        coverage_digest: str,
        provenance_seal: str,
        gate_identity: str,
        code_revision: str,
    ) -> AuthorityHandle:
        if not ticket_id:
            raise AuthorityRegistryError(
                "diagnostic mint ticket missing — caller cannot mint authority"
            )
        binding = {
            "coverage_digest": coverage_digest,
            "gate_identity": gate_identity,
            "code_revision": code_revision,
        }
        trust_class = capability._consume_census_mint(binding=binding)  # pylint: disable=protected-access
        with self._mutation():
            stored = self._diagnostic_tickets.pop(ticket_id, None)
            if stored is None:
                raise AuthorityRegistryError(
                    "diagnostic mint ticket invalid or already consumed"
                )
            ticket, registered_trust = stored
            if registered_trust != trust_class:
                raise AuthorityRegistryError("diagnostic ticket trust class mismatch")
            if self._ticket_provenance.pop(ticket_id, None) != provenance_seal:
                raise AuthorityRegistryError("diagnostic census provenance seal invalid")
            if ticket.evidence.coverage_digest != coverage_digest:
                raise AuthorityRegistryError("diagnostic mint ticket digest mismatch")
            record = CoverageAuthorityRecord(
                code_revision=ticket.evidence.code_revision,
                inventory_digest=ticket.evidence.inventory_digest,
                runtime_census_digest=ticket.evidence.runtime_census_digest,
                coverage_digest=ticket.evidence.coverage_digest,
                gate_identity=ticket.evidence.gate_identity,
                gate_path=ticket.evidence.gate_path,
                gate_protocol=ticket.evidence.gate_protocol,
                mint_seal=self._process_mint_seal,
                consumed_ticket_id=ticket.ticket_id,
                mint_epoch=self._authority_epoch,
                trust_class=trust_class,
            )
            handle_id = self._new_handle_id()
            self._coverage_records[handle_id] = record
        return AuthorityHandle("coverage", handle_id)

    def mint_lease_handle(
        self,
        capability: AuthorityMintCapability,
        record: LeaseAuthorityRecord,
        *,
        custodian: Any,
    ) -> AuthorityHandle:
        binding = {
            "custodian_id": record.custodian_id,
            "gate_path": record.gate_path,
            "gate_inode": record.gate_inode,
            "run_id": record.run_id,
            "grant_digest": record.grant_digest,
            "authority_digest": record.authority_digest,
        }
        trust_class = capability._consume_lease(binding=binding)  # pylint: disable=protected-access
        if record.trust_class != trust_class:
            raise AuthorityRegistryError("lease record trust class mismatch")
        verify_live_custodian_lock(custodian)
        if custodian.inode != record.gate_inode:
            raise AuthorityRegistryError("custodian gate inode mismatch")
        if custodian.lock_path != record.gate_path:
            raise AuthorityRegistryError("custodian gate path mismatch")
        with self._mutation():
            if record.custodian_id in self._custodian_refs:
                raise AuthorityRegistryError("custodian id already registered")
            self._custodian_refs[record.custodian_id] = _CustodianBinding(
                custodian=custodian,
                object_id=id(custodian),
            )
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
        record = self._lookup_lease_record(handle)
        self._validate_custodian_binding(record.custodian_id)
        return record

    def compose_and_mint_source_authority(
        self,
        capability: AuthorityMintCapability,
        *,
        lease_handle: AuthorityHandle,
        coverage_handle: AuthorityHandle,
        open_evidence_digest: str,
    ) -> AuthorityHandle:
        binding = {
            "lease_handle_id": lease_handle.handle_id,
            "coverage_handle_id": coverage_handle.handle_id,
            "open_evidence_digest": open_evidence_digest,
        }
        trust_class = capability._consume_source(binding=binding)  # pylint: disable=protected-access
        lease_record = self._revalidate_live_lease(lease_handle)
        coverage_record = self._lookup_coverage_record(coverage_handle)
        if lease_record.trust_class != trust_class:
            raise AuthorityRegistryError("source mint trust class mismatch")
        if coverage_record.trust_class != trust_class:
            raise AuthorityRegistryError("source mint trust class mismatch")
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
        with self._mutation():
            self._revalidate_live_lease(lease_handle)
            self._bind_coverage_to_lease(
                coverage_handle_id=coverage_handle.handle_id,
                lease_handle_id=lease_handle.handle_id,
            )
            composition_seal = secrets.token_hex(16)
            record = SourceAuthorityRecord(
                lease_handle_id=lease_handle.handle_id,
                coverage_handle_id=coverage_handle.handle_id,
                authority_epoch=self._authority_epoch,
                run_id=lease_record.run_id,
                coverage_digest=coverage_record.coverage_digest,
                gate_identity=coverage_record.gate_identity,
                gate_path=coverage_record.gate_path,
                open_evidence_digest=open_evidence_digest,
                composition_seal=composition_seal,
                trust_class=trust_class,
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

    def _lookup_lease_record(self, handle: AuthorityHandle) -> LeaseAuthorityRecord:
        if not isinstance(handle, AuthorityHandle) or handle.kind != "lease":
            raise AuthorityRegistryError("invalid lease authority handle")
        if handle.handle_id in self._invalidated:
            raise AuthorityRegistryError("lease authority handle invalidated")
        record = self._lease_records.get(handle.handle_id)
        if record is None:
            raise AuthorityRegistryError("lease authority handle not registered")
        if record.mint_epoch != self._authority_epoch:
            raise AuthorityRegistryError("lease authority handle epoch invalidated")
        return record

    def _lookup_coverage_record(self, handle: AuthorityHandle) -> CoverageAuthorityRecord:
        if not isinstance(handle, AuthorityHandle) or handle.kind != "coverage":
            raise AuthorityRegistryError("invalid coverage authority handle")
        if handle.handle_id in self._invalidated:
            raise AuthorityRegistryError("coverage authority handle invalidated")
        record = self._coverage_records.get(handle.handle_id)
        if record is None:
            raise AuthorityRegistryError("coverage authority handle not registered")
        if record.mint_epoch != self._authority_epoch:
            raise AuthorityRegistryError("coverage authority handle epoch invalidated")
        if record.mint_seal != self._process_mint_seal:
            raise AuthorityRegistryError("coverage authority mint seal invalid")
        return record

    def lookup_lease_handle(self, handle: AuthorityHandle) -> LeaseAuthorityRecord:
        record = self._lookup_lease_record(handle)
        self._validate_custodian_binding(record.custodian_id)
        return record

    def lookup_coverage_handle(self, handle: AuthorityHandle) -> CoverageAuthorityRecord:
        return self._lookup_coverage_record(handle)

    def lookup_source_handle(self, handle: AuthorityHandle) -> SourceAuthorityRecord:
        if not isinstance(handle, AuthorityHandle) or handle.kind != "source":
            raise AuthorityRegistryError("invalid source authority handle")
        if handle.handle_id in self._invalidated:
            raise AuthorityRegistryError("source authority handle invalidated")
        record = self._source_records.get(handle.handle_id)
        if record is None:
            raise AuthorityRegistryError("source authority handle not registered")
        if record.authority_epoch != self._authority_epoch:
            raise AuthorityRegistryError("source authority handle epoch invalidated")
        lease = AuthorityHandle("lease", record.lease_handle_id)
        coverage = AuthorityHandle("coverage", record.coverage_handle_id)
        self.lookup_lease_handle(lease)
        self._lookup_coverage_record(coverage)
        bound_lease = self._coverage_lease_binding.get(record.coverage_handle_id)
        if bound_lease != record.lease_handle_id:
            raise AuthorityRegistryError("source authority coverage binding invalid")
        return record

    def lookup_custodian(self, custodian_id: str) -> Any:
        return self._validate_custodian_binding(custodian_id)

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
        record = self._lookup_lease_record(handle)
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
        self._process_mint_seal = secrets.token_hex(32)
        self._authority_epoch += 1


def _build_registry_facade() -> dict[str, Any]:
    """Hold trusted registry state in closure — not reachable as module globals."""
    registry = _TrustedRegistry()
    lock = threading.RLock()

    def registry_op(method: str, *args: Any, **kwargs: Any) -> Any:
        with lock:
            return getattr(registry, method)(*args, **kwargs)

    def current_epoch() -> int:
        return registry._authority_epoch  # pylint: disable=protected-access

    return {"op": registry_op, "epoch": current_epoch}


def _make_registry_api() -> tuple[Any, Any]:
    """Return registry op dispatchers with closure-held trusted state."""
    facade = _build_registry_facade()

    def registry_op(method: str, *args: Any, **kwargs: Any) -> Any:
        return facade["op"](method, *args, **kwargs)

    def current_epoch() -> int:
        return facade["epoch"]()

    return registry_op, current_epoch


_registry_op, current_authority_epoch = _make_registry_api()


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
        "_REGISTRY",
        "_TRUSTED_REGISTRY",
        "_FACADE",
        "census_mint_window",
        "lease_acquisition_window",
        "source_composition_window",
    }
)


def __getattr__(name: str) -> Any:
    if name in _FORBIDDEN_MODULE_ATTRS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def register_diagnostic_ticket(
    capability: AuthorityMintCapability,
    ticket: DiagnosticMintTicket,
    *,
    provenance_seal: str,
) -> None:
    _registry_op(
        "register_diagnostic_ticket",
        capability,
        ticket,
        provenance_seal=provenance_seal,
    )


def finalize_diagnostic_and_mint_coverage(
    capability: AuthorityMintCapability,
    ticket_id: str | None,
    *,
    coverage_digest: str,
    provenance_seal: str,
    gate_identity: str,
    code_revision: str,
) -> AuthorityHandle:
    return _registry_op(
        "finalize_diagnostic_and_mint_coverage",
        capability,
        ticket_id,
        coverage_digest=coverage_digest,
        provenance_seal=provenance_seal,
        gate_identity=gate_identity,
        code_revision=code_revision,
    )


def mint_lease_handle(
    capability: AuthorityMintCapability,
    record: LeaseAuthorityRecord,
    *,
    custodian: Any,
) -> AuthorityHandle:
    return _registry_op("mint_lease_handle", capability, record, custodian=custodian)


def compose_and_mint_source_authority(
    capability: AuthorityMintCapability,
    *,
    lease_handle: AuthorityHandle,
    coverage_handle: AuthorityHandle,
    open_evidence_digest: str,
) -> AuthorityHandle:
    return _registry_op(
        "compose_and_mint_source_authority",
        capability,
        lease_handle=lease_handle,
        coverage_handle=coverage_handle,
        open_evidence_digest=open_evidence_digest,
    )


def lookup_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    return _registry_op("lookup_lease_handle", handle)


def lookup_coverage_handle(handle: AuthorityHandle) -> CoverageAuthorityRecord:
    return _registry_op("lookup_coverage_handle", handle)


def lookup_source_handle(handle: AuthorityHandle) -> SourceAuthorityRecord:
    return _registry_op("lookup_source_handle", handle)


def lookup_custodian(custodian_id: str) -> Any:
    return _registry_op("lookup_custodian", custodian_id)


def invalidate_lease_handle(handle: AuthorityHandle) -> None:
    _registry_op("invalidate_lease_handle", handle)


def release_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    return _registry_op("release_lease_handle", handle)


def invalidate_coverage_handle(handle: AuthorityHandle) -> None:
    _registry_op("invalidate_coverage_handle", handle)


def invalidate_all_authority() -> None:
    _registry_op("invalidate_all_authority")
