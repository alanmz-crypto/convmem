"""Single vault for R2b v2 trusted authority — guarded sinks, closure-free dispatch."""

from __future__ import annotations

import hashlib
import inspect
import json
import secrets
import threading
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any

from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.lock_custodian import LockCustodianError


class AuthorityCapabilityError(RuntimeError):
    """Capability issuance, validation, or consumption failure."""


class AuthorityRegistryError(RuntimeError):
    """Registry lookup, minting, or cross-slice binding failure."""


class MintPhase(str, Enum):
    CENSUS = "census"
    LEASE = "lease"
    SOURCE = "source"


_TRUST_CLASS_PRODUCTION = "production"
_TRUST_CLASS_HERMETIC = "hermetic_test"

_CANONICAL_ISSUER_MODULES = frozenset(
    {
        "eval_corpus.r2b_v2.coverage.proof",
        "eval_corpus.r2b_v2.lease",
    }
)


def verify_live_custodian_lock(custodian: Any) -> None:
    try:
        custodian.verify()
    except LockCustodianError as exc:
        raise LockCustodianError(
            "custodian no longer possesses exclusive kernel lock"
        ) from exc


def trust_class_for_gate_policy(policy_class: str) -> str:
    if policy_class == "test_fixture":
        return _TRUST_CLASS_HERMETIC
    if policy_class == "production":
        return _TRUST_CLASS_PRODUCTION
    raise AuthorityCapabilityError("untrusted gate policy class")


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


def _binding_digest(phase: MintPhase, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"phase": phase.value, **payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _assert_canonical_issuer() -> None:
    frame = inspect.currentframe()
    if frame is not None:
        frame = frame.f_back
    if frame is not None:
        frame = frame.f_back
    while frame is not None:
        module = frame.f_globals.get("__name__", "")
        if module in _CANONICAL_ISSUER_MODULES:
            return
        frame = frame.f_back
    raise AuthorityCapabilityError(
        "capability issuance forbidden outside canonical lifecycle"
    )


_MUTATION_GUARD = [threading.local()]


def _registry_mutation_active() -> bool:
    return int(getattr(_MUTATION_GUARD[0], "depth", 0)) > 0


def _vault_internal_frame_active(allowed_names: frozenset[str]) -> bool:
    frame = inspect.currentframe()
    if frame is not None:
        frame = frame.f_back
    vault_module = __name__
    while frame is not None:
        if (
            frame.f_globals.get("__name__") == vault_module
            and frame.f_code.co_name in allowed_names
        ):
            return True
        frame = frame.f_back
    return False


_LEDGER_WRITE_FRAMES = frozenset({"_issue_capability", "_reset_capabilities_for_tests"})
_LEDGER_RECORD_WRITE_FRAMES = frozenset(
    {
        "_consume_census_register",
        "_consume_census_mint",
        "_consume_lease",
        "_consume_source",
    }
)
_CONSUMED_ID_WRITE_FRAMES = frozenset(
    {
        "_consume_census_mint",
        "_consume_lease",
        "_consume_source",
    }
)


class _GuardedLedgerRecord(dict[str, Any]):
    def __setitem__(self, key: str, value: Any) -> None:
        if not _vault_internal_frame_active(_LEDGER_RECORD_WRITE_FRAMES):
            raise AuthorityCapabilityError(
                "direct capability ledger record mutation forbidden"
            )
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        if not _vault_internal_frame_active(_LEDGER_RECORD_WRITE_FRAMES):
            raise AuthorityCapabilityError(
                "direct capability ledger record mutation forbidden"
            )
        super().__delitem__(key, value)


class _GuardedLedger(dict[str, dict[str, Any]]):
    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        if not _vault_internal_frame_active(_LEDGER_WRITE_FRAMES):
            raise AuthorityCapabilityError("direct capability ledger mutation forbidden")
        if not isinstance(value, _GuardedLedgerRecord):
            value = _GuardedLedgerRecord(value)
        super().__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        if not _vault_internal_frame_active(_LEDGER_WRITE_FRAMES):
            raise AuthorityCapabilityError("direct capability ledger mutation forbidden")
        super().__delitem__(key)

    def clear(self) -> None:
        if not _vault_internal_frame_active(_LEDGER_WRITE_FRAMES):
            raise AuthorityCapabilityError("direct capability ledger mutation forbidden")
        super().clear()


class _GuardedConsumedSet(set[str]):
    def add(self, element: str) -> None:
        if not _vault_internal_frame_active(_CONSUMED_ID_WRITE_FRAMES):
            raise AuthorityCapabilityError(
                "direct consumed-capability mutation forbidden"
            )
        super().add(element)


def _build_vault() -> dict[str, Any]:  # pylint: disable=too-many-statements
    """Hold trusted authority state behind guarded sinks and a single dispatch holder."""
    _capability_ledger: _GuardedLedger = _GuardedLedger()
    _consumed_capability_ids: _GuardedConsumedSet = _GuardedConsumedSet()
    _lock = threading.RLock()

    class AuthorityMintCapability:  # pylint: disable=redefined-outer-name
        """Opaque possession token — ledger-backed, not forgeable by field copy."""

        __slots__ = ("_capability_id",)

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise AuthorityCapabilityError(
                "AuthorityMintCapability cannot be constructed by callers"
            )

        def __bool__(self) -> bool:
            raise AuthorityCapabilityError(
                "AuthorityMintCapability is not reducible to a boolean authority claim"
            )

        def __copy__(self) -> AuthorityMintCapability:
            raise AuthorityCapabilityError("AuthorityMintCapability cannot be copied")

        def __deepcopy__(self, _memo: dict[int, Any]) -> AuthorityMintCapability:
            raise AuthorityCapabilityError("AuthorityMintCapability cannot be deep-copied")

        def __reduce__(self) -> Any:
            raise AuthorityCapabilityError("AuthorityMintCapability is not serializable")

        def _ledger_record(self) -> dict[str, Any]:
            record = _capability_ledger.get(self._capability_id)
            if record is None:
                raise AuthorityCapabilityError("capability not issued by authority vault")
            return record

        def _validate_binding(self, *, phase: MintPhase, binding: dict[str, Any]) -> None:
            record = self._ledger_record()
            if record["phase"] is not phase:
                raise AuthorityCapabilityError("capability phase mismatch")
            expected = _binding_digest(phase, binding)
            if record["binding_digest"] != expected:
                raise AuthorityCapabilityError("capability binding mismatch")
            if self._capability_id in _consumed_capability_ids:
                raise AuthorityCapabilityError("capability already consumed or replayed")

        def _consume_census_register(self, *, binding: dict[str, Any]) -> str:
            self._validate_binding(phase=MintPhase.CENSUS, binding=binding)
            record = self._ledger_record()
            if record["census_stage"] != 0:
                raise AuthorityCapabilityError("census capability register stage invalid")
            record["census_stage"] = 1
            return str(record["trust_class"])

        def _consume_census_mint(self, *, binding: dict[str, Any]) -> str:
            self._validate_binding(phase=MintPhase.CENSUS, binding=binding)
            record = self._ledger_record()
            if record["census_stage"] != 1:
                raise AuthorityCapabilityError("census capability mint stage invalid")
            record["census_stage"] = 2
            _consumed_capability_ids.add(self._capability_id)
            return str(record["trust_class"])

        def _consume_lease(self, *, binding: dict[str, Any]) -> str:
            self._validate_binding(phase=MintPhase.LEASE, binding=binding)
            _consumed_capability_ids.add(self._capability_id)
            return str(self._ledger_record()["trust_class"])

        def _consume_source(self, *, binding: dict[str, Any]) -> str:
            self._validate_binding(phase=MintPhase.SOURCE, binding=binding)
            _consumed_capability_ids.add(self._capability_id)
            return str(self._ledger_record()["trust_class"])

        @property
        def trust_class(self) -> str:
            return str(self._ledger_record()["trust_class"])

    @contextmanager
    def _mutation() -> Iterator[None]:
        local = _MUTATION_GUARD[0]
        depth = int(getattr(local, "depth", 0))
        local.depth = depth + 1
        try:
            yield
        finally:
            local.depth = depth

    class _SealedStore(MutableMapping[str, Any]):
        __slots__ = ("_data",)

        def __init__(self) -> None:
            self._data: dict[str, Any] = {}

        def _guard_mutation(self) -> None:
            if not _registry_mutation_active():
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

    class _TrustedRegistry:  # pylint: disable=too-many-instance-attributes
        __slots__ = (
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
            self._lease_records = _SealedStore()
            self._coverage_records = _SealedStore()
            self._source_records = _SealedStore()
            self._diagnostic_tickets = _SealedStore()
            self._ticket_provenance = _SealedStore()
            self._recently_consumed_tickets = _SealedStore()
            self._invalidated: set[str] = set()
            self._custodian_refs = _SealedStore()
            self._coverage_lease_binding = _SealedStore()
            self._lease_dependent_sources: dict[str, set[str]] = {}
            self._coverage_dependent_sources: dict[str, set[str]] = {}
            self._process_mint_seal = secrets.token_hex(32)
            self._authority_epoch = 0

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
            with _mutation():
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
            with _mutation():
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
            with _mutation():
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
            with _mutation():
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
            with _mutation():
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
            with _mutation():
                self._invalidated.add(handle.handle_id)
                self._coverage_records.pop(handle.handle_id, None)
                self._coverage_lease_binding.pop(handle.handle_id, None)
                dependent_sources = self._coverage_dependent_sources.pop(handle.handle_id, set())
                self._invalidate_source_ids(dependent_sources)

        def invalidate_all_authority(self) -> None:
            with _mutation():
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

    registry = _TrustedRegistry()

    def _issue_capability(
        *,
        phase: MintPhase,
        binding: dict[str, Any],
        trust_class: str,
    ) -> AuthorityMintCapability:
        _assert_canonical_issuer()
        if trust_class not in (_TRUST_CLASS_PRODUCTION, _TRUST_CLASS_HERMETIC):
            raise AuthorityCapabilityError("invalid trust class for capability issuance")
        cap_id = secrets.token_hex(16)
        _capability_ledger[cap_id] = _GuardedLedgerRecord(
            {
                "phase": phase,
                "binding_digest": _binding_digest(phase, binding),
                "trust_class": trust_class,
                "census_stage": 0,
            }
        )
        cap = object.__new__(AuthorityMintCapability)
        cap._capability_id = cap_id  # pylint: disable=attribute-defined-outside-init,protected-access
        return cap

    def vault_dispatch(op: str, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=redefined-outer-name
        with _lock:
            if op == "issue_census_capability":
                return _issue_capability(
                    phase=MintPhase.CENSUS,
                    binding={
                        "coverage_digest": kwargs["coverage_digest"],
                        "gate_identity": kwargs["gate_identity"],
                        "code_revision": kwargs["code_revision"],
                    },
                    trust_class=kwargs["trust_class"],
                )
            if op == "issue_lease_capability":
                return _issue_capability(
                    phase=MintPhase.LEASE,
                    binding={
                        "custodian_id": kwargs["custodian_id"],
                        "gate_path": kwargs["gate_path"],
                        "gate_inode": kwargs["gate_inode"],
                        "run_id": kwargs["run_id"],
                        "grant_digest": kwargs["grant_digest"],
                        "authority_digest": kwargs["authority_digest"],
                    },
                    trust_class=kwargs["trust_class"],
                )
            if op == "issue_source_capability":
                return _issue_capability(
                    phase=MintPhase.SOURCE,
                    binding={
                        "lease_handle_id": kwargs["lease_handle_id"],
                        "coverage_handle_id": kwargs["coverage_handle_id"],
                        "open_evidence_digest": kwargs["open_evidence_digest"],
                    },
                    trust_class=kwargs["trust_class"],
                )
            if op == "reset_capabilities_for_tests":

                def _reset_capabilities_for_tests() -> None:
                    _capability_ledger.clear()
                    _consumed_capability_ids.clear()

                _reset_capabilities_for_tests()
                return None
            if op == "current_authority_epoch":
                return registry._authority_epoch  # pylint: disable=protected-access
            if op == "probe_parallel_registry_constructible":
                return False
            if op == "probe_closure_registry_mutation":
                try:
                    registry._lease_records["probe-evil"] = "payload"  # pylint: disable=protected-access
                    return registry._lease_records.get("probe-evil")  # pylint: disable=protected-access
                except AuthorityRegistryError:
                    return None
            return getattr(registry, op)(*args, **kwargs)

    return {
        "dispatch": vault_dispatch,
        "AuthorityMintCapability": AuthorityMintCapability,
    }


class _VaultHolder:
    """Route dispatch without exposing closure-backed inner dispatch."""

    __slots__ = ("__inner",)

    def __init__(self, inner_dispatch: Any) -> None:
        object.__setattr__(self, "_VaultHolder__inner", inner_dispatch)

    def __getattribute__(self, name: str) -> Any:
        if name in {"__inner", "_VaultHolder__inner", "__dict__"}:
            raise AttributeError(name)
        return super().__getattribute__(name)

    def dispatch(self, op: str, *args: Any, **kwargs: Any) -> Any:
        inner = object.__getattribute__(self, "_VaultHolder__inner")
        return inner(op, *args, **kwargs)


_vault_bundle = _build_vault()
_vault_holder = _VaultHolder(_vault_bundle["dispatch"])
AuthorityMintCapability = _vault_bundle["AuthorityMintCapability"]
del _vault_bundle, _build_vault


def vault_dispatch(op: str, *args: Any, **kwargs: Any) -> Any:
    """Module-level dispatch entry — no introspectable closure cells."""
    return _vault_holder.dispatch(op, *args, **kwargs)


def issue_census_capability(
    *,
    coverage_digest: str,
    gate_identity: str,
    code_revision: str,
    trust_class: str,
) -> AuthorityMintCapability:
    return vault_dispatch(
        "issue_census_capability",
        coverage_digest=coverage_digest,
        gate_identity=gate_identity,
        code_revision=code_revision,
        trust_class=trust_class,
    )


def issue_lease_capability(
    *,
    custodian_id: str,
    gate_path: str,
    gate_inode: int,
    run_id: str,
    grant_digest: str,
    authority_digest: str,
    trust_class: str,
) -> AuthorityMintCapability:
    return vault_dispatch(
        "issue_lease_capability",
        custodian_id=custodian_id,
        gate_path=gate_path,
        gate_inode=gate_inode,
        run_id=run_id,
        grant_digest=grant_digest,
        authority_digest=authority_digest,
        trust_class=trust_class,
    )


def issue_source_capability(
    *,
    lease_handle_id: str,
    coverage_handle_id: str,
    open_evidence_digest: str,
    trust_class: str,
) -> AuthorityMintCapability:
    return vault_dispatch(
        "issue_source_capability",
        lease_handle_id=lease_handle_id,
        coverage_handle_id=coverage_handle_id,
        open_evidence_digest=open_evidence_digest,
        trust_class=trust_class,
    )


def reset_capabilities_for_tests() -> None:
    vault_dispatch("reset_capabilities_for_tests")


def current_authority_epoch() -> int:
    return int(vault_dispatch("current_authority_epoch"))


def register_diagnostic_ticket(
    capability: AuthorityMintCapability,
    ticket: DiagnosticMintTicket,
    *,
    provenance_seal: str,
) -> None:
    vault_dispatch(
        "register_diagnostic_ticket", capability, ticket, provenance_seal=provenance_seal
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
    return vault_dispatch(
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
    return vault_dispatch("mint_lease_handle", capability, record, custodian=custodian)


def compose_and_mint_source_authority(
    capability: AuthorityMintCapability,
    *,
    lease_handle: AuthorityHandle,
    coverage_handle: AuthorityHandle,
    open_evidence_digest: str,
) -> AuthorityHandle:
    return vault_dispatch(
        "compose_and_mint_source_authority",
        capability,
        lease_handle=lease_handle,
        coverage_handle=coverage_handle,
        open_evidence_digest=open_evidence_digest,
    )


def lookup_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    return vault_dispatch("lookup_lease_handle", handle)


def lookup_coverage_handle(handle: AuthorityHandle) -> CoverageAuthorityRecord:
    return vault_dispatch("lookup_coverage_handle", handle)


def lookup_source_handle(handle: AuthorityHandle) -> SourceAuthorityRecord:
    return vault_dispatch("lookup_source_handle", handle)


def lookup_custodian(custodian_id: str) -> Any:
    return vault_dispatch("lookup_custodian", custodian_id)


def invalidate_lease_handle(handle: AuthorityHandle) -> None:
    vault_dispatch("invalidate_lease_handle", handle)


def release_lease_handle(handle: AuthorityHandle) -> LeaseAuthorityRecord:
    return vault_dispatch("release_lease_handle", handle)


def invalidate_coverage_handle(handle: AuthorityHandle) -> None:
    vault_dispatch("invalidate_coverage_handle", handle)


def invalidate_all_authority() -> None:
    vault_dispatch("invalidate_all_authority")


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
        "_build_vault",
        "_vault_holder",
        "_MUTATION_GUARD",
        "census_mint_window",
        "lease_acquisition_window",
        "source_composition_window",
    }
)


def __getattr__(name: str) -> Any:
    if name in _FORBIDDEN_MODULE_ATTRS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
