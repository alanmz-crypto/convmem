"""Runtime census + zero-bypass coverage proof aggregator (I3)."""
# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-branches

from __future__ import annotations

import copy
import hashlib
import json
import os
import pickle
import re
import secrets
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from chroma_write_store import (
    WRITER_GATE_PROTOCOL_VERSION,
    classify_legacy_writer_pids,
    current_code_revision,
    list_pids_with_open_path,
    load_attestation,
)

from eval_corpus.r2b_v2._authority_capability import (
    issue_census_capability,
    issue_source_capability,
    trust_class_for_gate_policy,
)
from eval_corpus.r2b_v2._registry_mint import (
    DiagnosticMintTicket,
    compose_and_mint_source_authority,
    finalize_diagnostic_and_mint_coverage,
    register_diagnostic_ticket,
)
from eval_corpus.r2b_v2.authority_registry import (
    AuthorityHandle,
    AuthorityRegistryError,
    CoverageAuthorityRecord,
    lookup_coverage_handle,
    lookup_lease_handle,
    lookup_source_handle,
)
from eval_corpus.r2b_v2.coverage_evidence import CoverageEvidenceIdentity
from eval_corpus.r2b_v2.coverage.inventory import (
    build_static_route_inventory,
    load_v2_implementation_tip,
    verify_inventory_matches_tip,
    verify_shadow_inventory_unchanged,
)
from eval_corpus.r2b_v2.gate_policy import GatePolicy, resolve_trusted_gate_policy
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease


KNOWN_WRITER_ENTRYPOINTS: frozenset[str] = frozenset(
    {
        "production_chroma_write_session",
        "production.writer",
        "watch_index_event",
        "run_startup_reconciliation",
        "run_refine_job",
        "convmem.py:index_command",
        "file_generation_pointer.py",
        "source_reconciler.py",
        "recovery_authority.py",
        "observe.py:monitor",
    }
)


class CoverageHoldClass(str, Enum):
    UNKNOWN_WRITER = "unknown_writer"
    STALE_REVISION = "stale_revision"
    UNATTESTED_WRITER = "unattested_writer"
    UNINSPECTABLE_PROCESS = "uninspectable_process"
    PID_REUSE = "pid_reuse"
    ALTERNATE_GATE = "alternate_gate"
    BYPASS_CAPABLE_ROUTE = "bypass_capable_route"
    MISSING_PROCESS_INSPECTION = "missing_process_inspection"
    UNKNOWN_WRITER_SIGNATURE = "unknown_writer_signature"
    INCOMPLETE_STATIC_COVERAGE = "incomplete_static_coverage"


class CoverageProofError(RuntimeError):
    """Coverage proof refused — fail closed."""


@dataclass(frozen=True)
class RuntimeWriterRecord:
    pid: int
    start_time: str
    executable: str
    entrypoint: str
    code_revision: str
    gate_path: str
    gate_protocol: int
    mutable_surfaces: tuple[str, ...]
    attestation_digest: str


@dataclass
class DiagnosticCoverageResult:
    """Diagnostic census output — not trusted authority by itself."""

    identity: CoverageEvidenceIdentity
    runtime_census_skipped: bool = False
    hold_classes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    passed: bool = False
    _mint_ticket: str | None = field(default=None, repr=False, compare=False)
    _provenance_seal: str | None = field(default=None, repr=False, compare=False)
    _census_capability: Any = field(default=None, repr=False, compare=False)

    def __init__(
        self,
        *,
        code_revision: str,
        inventory_digest: str,
        runtime_census_digest: str,
        coverage_digest: str,
        gate_identity: str,
        gate_path: str,
        gate_protocol: int,
        runtime_census_skipped: bool = False,
        hold_classes: dict[str, list[dict[str, Any]]] | None = None,
        passed: bool = False,
        _mint_ticket: str | None = None,
        _provenance_seal: str | None = None,
        _census_capability: Any = None,
    ) -> None:
        self.identity = CoverageEvidenceIdentity(
            code_revision=code_revision,
            inventory_digest=inventory_digest,
            runtime_census_digest=runtime_census_digest,
            coverage_digest=coverage_digest,
            gate_identity=gate_identity,
            gate_path=gate_path,
            gate_protocol=gate_protocol,
        )
        self.runtime_census_skipped = runtime_census_skipped
        self.hold_classes = hold_classes if hold_classes is not None else {}
        self.passed = passed
        self._mint_ticket = _mint_ticket
        self._provenance_seal = _provenance_seal
        self._census_capability = _census_capability
        self.__post_init__()

    @property
    def code_revision(self) -> str:
        return self.identity.code_revision

    @property
    def inventory_digest(self) -> str:
        return self.identity.inventory_digest

    @property
    def runtime_census_digest(self) -> str:
        return self.identity.runtime_census_digest

    @property
    def coverage_digest(self) -> str:
        return self.identity.coverage_digest

    @property
    def gate_identity(self) -> str:
        return self.identity.gate_identity

    @property
    def gate_path(self) -> str:
        return self.identity.gate_path

    @property
    def gate_protocol(self) -> int:
        return self.identity.gate_protocol

    @property
    def mint_ticket(self) -> str | None:
        return self._mint_ticket

    @property
    def provenance_seal(self) -> str | None:
        return self._provenance_seal

    def require_census_capability(self) -> Any:
        """Return the bound census capability or fail closed."""
        if self._census_capability is None:
            raise CoverageProofError("diagnostic census capability missing")
        return self._census_capability

    def __post_init__(self) -> None:
        empty_required = (
            CoverageHoldClass.UNKNOWN_WRITER.value,
            CoverageHoldClass.STALE_REVISION.value,
            CoverageHoldClass.UNATTESTED_WRITER.value,
            CoverageHoldClass.UNINSPECTABLE_PROCESS.value,
            CoverageHoldClass.PID_REUSE.value,
            CoverageHoldClass.ALTERNATE_GATE.value,
            CoverageHoldClass.BYPASS_CAPABLE_ROUTE.value,
            CoverageHoldClass.MISSING_PROCESS_INSPECTION.value,
            CoverageHoldClass.UNKNOWN_WRITER_SIGNATURE.value,
            CoverageHoldClass.INCOMPLETE_STATIC_COVERAGE.value,
        )
        for key in empty_required:
            self.hold_classes.setdefault(key, [])


class TrustedCoverageProof:
    """Process-local trusted coverage proof — not constructible by callers."""

    __slots__ = ("_handle",)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise CoverageProofError("TrustedCoverageProof cannot be constructed by callers")

    def __bool__(self) -> bool:
        raise CoverageProofError(
            "TrustedCoverageProof is not reducible to a boolean authority claim"
        )

    def __copy__(self) -> TrustedCoverageProof:
        raise CoverageProofError("TrustedCoverageProof cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> TrustedCoverageProof:
        raise CoverageProofError("TrustedCoverageProof cannot be deep-copied")

    def __reduce__(self) -> Any:
        raise CoverageProofError("TrustedCoverageProof is not serializable")

    @property
    def authority_handle(self) -> AuthorityHandle:
        return self._handle

    @property
    def code_revision(self) -> str:
        return lookup_coverage_handle(self._handle).code_revision

    @property
    def inventory_digest(self) -> str:
        return lookup_coverage_handle(self._handle).inventory_digest

    @property
    def runtime_census_digest(self) -> str:
        return lookup_coverage_handle(self._handle).runtime_census_digest

    @property
    def coverage_digest(self) -> str:
        return lookup_coverage_handle(self._handle).coverage_digest

    @property
    def gate_identity(self) -> str:
        return lookup_coverage_handle(self._handle).gate_identity

    @property
    def gate_path(self) -> str:
        return lookup_coverage_handle(self._handle).gate_path

    @property
    def gate_protocol(self) -> int:
        return lookup_coverage_handle(self._handle).gate_protocol


def _trusted_coverage_from_handle(handle: AuthorityHandle) -> TrustedCoverageProof:
    lookup_coverage_handle(handle)
    proof = object.__new__(TrustedCoverageProof)
    proof._handle = handle  # pylint: disable=attribute-defined-outside-init,protected-access
    return proof


_GIT_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class SourceAuthorityProof:
    """Process-local source authority proof — not constructible by callers."""

    __slots__ = ("_handle",)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise CoverageProofError("SourceAuthorityProof cannot be constructed by callers")

    def __bool__(self) -> bool:
        raise CoverageProofError(
            "SourceAuthorityProof is not reducible to a boolean authority claim"
        )

    def __copy__(self) -> SourceAuthorityProof:
        raise CoverageProofError("SourceAuthorityProof cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> SourceAuthorityProof:
        raise CoverageProofError("SourceAuthorityProof cannot be deep-copied")

    def __reduce__(self) -> Any:
        raise CoverageProofError("SourceAuthorityProof is not serializable")

    @property
    def authority_handle(self) -> AuthorityHandle:
        return self._handle

    @property
    def run_id(self) -> str:
        return lookup_source_handle(self._handle).run_id

    @property
    def coverage_digest(self) -> str:
        return lookup_source_handle(self._handle).coverage_digest

    @property
    def gate_held(self) -> bool:
        lookup_source_handle(self._handle)
        return True

    @property
    def gate_identity(self) -> str:
        return lookup_source_handle(self._handle).gate_identity

    @property
    def gate_path(self) -> str:
        return lookup_source_handle(self._handle).gate_path


def _source_authority_from_handle(handle: AuthorityHandle) -> SourceAuthorityProof:
    lookup_source_handle(handle)
    proof = object.__new__(SourceAuthorityProof)
    proof._handle = handle  # pylint: disable=attribute-defined-outside-init,protected-access
    return proof


def _resolve_gate_policy(
    gate_policy: GatePolicy | None,
    test_gate_path: Path | None,
) -> GatePolicy:
    return resolve_trusted_gate_policy(
        gate_policy,
        test_gate_path,
        error_cls=CoverageProofError,
        mutual_exclusion_message="gate_policy and test_gate_path are mutually exclusive",
        untrusted_policy_message="caller-supplied gate policy cannot mint trusted authority",
    )


def _resolve_implementation_revision(
    *,
    code_revision: str | None,
    test_override: bool,
) -> str:
    if code_revision is not None and not _GIT_SHA40.match(code_revision):
        raise CoverageProofError("implementation revision must be an authoritative git SHA")
    if test_override:
        revision = code_revision or current_code_revision()
        if revision == "unknown" or not _GIT_SHA40.match(revision):
            raise CoverageProofError("trusted implementation revision is unavailable")
        return revision
    if code_revision is not None:
        tip = load_v2_implementation_tip()
        if tip and tip != "unknown" and code_revision != tip:
            raise CoverageProofError("implementation revision does not match bound inventory tip")
        return code_revision
    tip = load_v2_implementation_tip()
    if tip and tip != "unknown":
        if not _GIT_SHA40.match(tip):
            raise CoverageProofError("bound inventory implementation tip is not authoritative")
        return tip
    revision = current_code_revision()
    if revision == "unknown" or not _GIT_SHA40.match(revision):
        raise CoverageProofError("trusted implementation revision is unavailable")
    return revision


def _attestation_digest(att: dict[str, Any] | None) -> str:
    if att is None:
        return "missing"
    payload = json.dumps(att, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _proc_exe(pid: int) -> str:
    try:
        return os.path.realpath(f"/proc/{pid}/exe")
    except OSError:
        return "unknown"


def _proc_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _proc_start_time(pid: int) -> str:
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        after = stat.rsplit(")", 1)[-1].split()
        return str(after[19])
    except (OSError, IndexError, ValueError):
        return "unknown"


def _required_attestation_fields(att: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key in ("pid", "start_time", "code_revision", "executable", "entrypoint", "protocol_version"):
        value = att.get(key)
        if value in (None, "", "unknown"):
            missing.append(key)
    return missing


def _validate_live_writer(
    *,
    pid: int,
    surface_name: str,
    att: dict[str, Any],
    start: str,
    exe: str,
    cmd: str,
    revision: str,
    gate_policy: GatePolicy,
    gate_path: str,
) -> tuple[RuntimeWriterRecord | None, list[tuple[str, dict[str, Any]]]]:
    """Return a writer record or hold events for one PID."""
    holds: list[tuple[str, dict[str, Any]]] = []
    missing_fields = _required_attestation_fields(att)
    if missing_fields:
        holds.append(
            (
                CoverageHoldClass.MISSING_PROCESS_INSPECTION.value,
                {"pid": pid, "missing_fields": missing_fields},
            )
        )
        return None, holds
    att_pid = int(att["pid"])
    if att_pid != pid:
        holds.append((CoverageHoldClass.PID_REUSE.value, {"pid": pid, "attested_pid": att_pid}))
        return None, holds
    entrypoint = str(att.get("entrypoint"))
    att_revision = str(att.get("code_revision"))
    att_start = str(att.get("start_time"))
    att_exe = str(att.get("executable"))
    att_protocol = int(att.get("protocol_version"))
    if att_start != start:
        holds.append(
            (CoverageHoldClass.PID_REUSE.value, {"pid": pid, "att_start": att_start, "proc_start": start})
        )
        return None, holds
    if att_exe != exe:
        holds.append(
            (
                CoverageHoldClass.UNKNOWN_WRITER_SIGNATURE.value,
                {"pid": pid, "att_executable": att_exe, "proc_executable": exe},
            )
        )
        return None, holds
    if entrypoint not in KNOWN_WRITER_ENTRYPOINTS:
        holds.append((CoverageHoldClass.UNKNOWN_WRITER_SIGNATURE.value, {"pid": pid, "entrypoint": entrypoint}))
        return None, holds
    if not cmd:
        holds.append(
            (CoverageHoldClass.UNKNOWN_WRITER_SIGNATURE.value, {"pid": pid, "entrypoint": entrypoint, "cmdline": cmd})
        )
        return None, holds
    if revision not in ("unknown", att_revision):
        holds.append(
            (CoverageHoldClass.STALE_REVISION.value, {"pid": pid, "revision": att_revision, "expected": revision})
        )
        return None, holds
    if att_protocol != gate_policy.protocol:
        holds.append(
            (
                CoverageHoldClass.ALTERNATE_GATE.value,
                {"pid": pid, "protocol": att_protocol, "expected": gate_policy.protocol},
            )
        )
        return None, holds
    if att_protocol != WRITER_GATE_PROTOCOL_VERSION:
        holds.append(
            (
                CoverageHoldClass.ALTERNATE_GATE.value,
                {"pid": pid, "protocol": att_protocol, "expected": WRITER_GATE_PROTOCOL_VERSION},
            )
        )
        return None, holds
    record = RuntimeWriterRecord(
        pid=pid,
        start_time=start,
        executable=exe,
        entrypoint=entrypoint,
        code_revision=att_revision,
        gate_path=gate_path,
        gate_protocol=gate_policy.protocol,
        mutable_surfaces=(surface_name,),
        attestation_digest=_attestation_digest(att),
    )
    return record, holds


def inspect_runtime_writers(
    *,
    chroma_dir: Path,
    processed_path: Path,
    export_root: Path,
    gate_policy: GatePolicy,
    attest_dir: Path | None,
    expected_revision: str | None = None,
) -> tuple[list[RuntimeWriterRecord], dict[str, list[dict[str, Any]]]]:
    """Bind runtime identity for every observed writer-like process."""
    revision = expected_revision or current_code_revision()
    gate_path = str(gate_policy.resolve_path())
    holds: dict[str, list[dict[str, Any]]] = {
        cls.value: [] for cls in CoverageHoldClass
    }
    surfaces = {
        "chroma": chroma_dir,
        "processed": processed_path,
        "export": export_root,
    }
    seen: dict[int, RuntimeWriterRecord] = {}
    for surface_name, surface_path in surfaces.items():
        for pid in list_pids_with_open_path(surface_path):
            if pid in seen:
                prior = seen[pid]
                merged = tuple(sorted(set(prior.mutable_surfaces + (surface_name,))))
                seen[pid] = RuntimeWriterRecord(
                    pid=prior.pid,
                    start_time=prior.start_time,
                    executable=prior.executable,
                    entrypoint=prior.entrypoint,
                    code_revision=prior.code_revision,
                    gate_path=prior.gate_path,
                    gate_protocol=prior.gate_protocol,
                    mutable_surfaces=merged,
                    attestation_digest=prior.attestation_digest,
                )
                continue
            att = load_attestation(pid, attest_dir=attest_dir)
            cmd = _proc_cmdline(pid)
            start = _proc_start_time(pid)
            exe = _proc_exe(pid)
            if start == "unknown" or exe == "unknown":
                holds[CoverageHoldClass.UNINSPECTABLE_PROCESS.value].append(
                    {"pid": pid, "surface": surface_name}
                )
                continue
            if att is None:
                holds[CoverageHoldClass.UNATTESTED_WRITER.value].append(
                    {"pid": pid, "surface": surface_name}
                )
                continue
            record, att_holds = _validate_live_writer(
                pid=pid,
                surface_name=surface_name,
                att=att,
                start=start,
                exe=exe,
                cmd=cmd,
                revision=revision,
                gate_policy=gate_policy,
                gate_path=gate_path,
            )
            for hold_key, hold_payload in att_holds:
                holds[hold_key].append(hold_payload)
            if record is None:
                continue
            seen[pid] = record
    legacy = classify_legacy_writer_pids(
        list(seen.keys()),
        attest_dir=attest_dir,
        expected_revision=revision,
    )
    for refusal in legacy:
        code = str(refusal.get("code") or "")
        if code == "legacy_writer_process":
            detail = str(refusal.get("detail") or "")
            if "unattested" in detail:
                holds[CoverageHoldClass.UNATTESTED_WRITER.value].append(refusal)
            else:
                holds[CoverageHoldClass.UNKNOWN_WRITER.value].append(refusal)
    return list(seen.values()), holds


def _register_passing_census_ticket(
    *,
    policy: GatePolicy,
    revision: str,
    inventory: dict[str, Any],
    runtime_digest: str,
    coverage_digest: str,
    gate_path: str,
    mint_ticket: str,
    provenance_seal: str,
) -> Any:
    trust_class = trust_class_for_gate_policy(policy.policy_class)
    census_capability = issue_census_capability(
        coverage_digest=coverage_digest,
        gate_identity=policy.canonical_identity,
        code_revision=revision,
        trust_class=trust_class,
    )
    evidence = CoverageEvidenceIdentity(
        code_revision=revision,
        inventory_digest=inventory["inventory_digest"],
        runtime_census_digest=runtime_digest,
        coverage_digest=coverage_digest,
        gate_identity=policy.canonical_identity,
        gate_path=gate_path,
        gate_protocol=policy.protocol,
    )
    ticket = DiagnosticMintTicket(ticket_id=mint_ticket, evidence=evidence)
    register_diagnostic_ticket(
        census_capability,
        ticket,
        provenance_seal=provenance_seal,
    )
    return census_capability


def prove_zero_bypass_coverage(
    *,
    chroma_dir: Path,
    processed_path: Path,
    export_root: Path,
    gate_policy: GatePolicy | None = None,
    test_gate_path: Path | None = None,
    attest_dir: Path | None = None,
    code_revision: str | None = None,
    static_inventory: dict[str, Any] | None = None,
    bypass_capable_routes: list[dict[str, Any]] | None = None,
    skip_runtime: bool = False,
) -> DiagnosticCoverageResult:
    """Combine static inventory and runtime census; returns diagnostic result only."""
    policy = _resolve_gate_policy(gate_policy, test_gate_path)
    gate_path = str(policy.resolve_path())
    revision = _resolve_implementation_revision(
        code_revision=code_revision,
        test_override=test_gate_path is not None,
    )
    inventory = static_inventory or build_static_route_inventory(code_revision=revision)
    holds: dict[str, list[dict[str, Any]]] = {
        cls.value: [] for cls in CoverageHoldClass
    }
    for msg in verify_inventory_matches_tip(inventory, code_revision=revision):
        holds[CoverageHoldClass.INCOMPLETE_STATIC_COVERAGE.value].append({"detail": msg})
    for msg in verify_shadow_inventory_unchanged():
        holds[CoverageHoldClass.BYPASS_CAPABLE_ROUTE.value].append({"detail": msg})
    if bypass_capable_routes:
        holds[CoverageHoldClass.BYPASS_CAPABLE_ROUTE.value].extend(bypass_capable_routes)
    runtime_records: list[RuntimeWriterRecord] = []
    if not skip_runtime:
        runtime_records, runtime_holds = inspect_runtime_writers(
            chroma_dir=chroma_dir,
            processed_path=processed_path,
            export_root=export_root,
            gate_policy=policy,
            attest_dir=attest_dir,
            expected_revision=revision,
        )
        for key, items in runtime_holds.items():
            holds[key].extend(items)
    runtime_payload = [
        {
            "pid": r.pid,
            "start_time": r.start_time,
            "executable": r.executable,
            "entrypoint": r.entrypoint,
            "code_revision": r.code_revision,
            "gate_path": r.gate_path,
            "gate_protocol": r.gate_protocol,
            "mutable_surfaces": list(r.mutable_surfaces),
            "attestation_digest": r.attestation_digest,
        }
        for r in runtime_records
    ]
    runtime_digest = hashlib.sha256(
        json.dumps(runtime_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    combined = {
        "code_revision": revision,
        "inventory_digest": inventory["inventory_digest"],
        "runtime_census_digest": runtime_digest,
        "gate_identity": policy.canonical_identity,
        "gate_path": gate_path,
        "gate_protocol": policy.protocol,
        "runtime_census_skipped": skip_runtime,
        "hold_classes": holds,
    }
    coverage_digest = hashlib.sha256(
        json.dumps(combined, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    passed = all(not items for items in holds.values())
    mint_ticket = secrets.token_hex(16) if passed and not skip_runtime else None
    provenance_seal = secrets.token_hex(16) if mint_ticket is not None else None
    census_capability = None
    if mint_ticket is not None and provenance_seal is not None:
        census_capability = _register_passing_census_ticket(
            policy=policy,
            revision=revision,
            inventory=inventory,
            runtime_digest=runtime_digest,
            coverage_digest=coverage_digest,
            gate_path=gate_path,
            mint_ticket=mint_ticket,
            provenance_seal=provenance_seal,
        )
    return DiagnosticCoverageResult(
        code_revision=revision,
        inventory_digest=inventory["inventory_digest"],
        runtime_census_digest=runtime_digest,
        coverage_digest=coverage_digest,
        gate_identity=policy.canonical_identity,
        gate_path=gate_path,
        gate_protocol=policy.protocol,
        runtime_census_skipped=skip_runtime,
        hold_classes=holds,
        passed=passed,
        _mint_ticket=mint_ticket,
        _provenance_seal=provenance_seal,
        _census_capability=census_capability,
    )


def mint_trusted_coverage_proof(
    diagnostic: DiagnosticCoverageResult,
) -> TrustedCoverageProof:
    """Mint trusted coverage proof from a passing diagnostic census."""
    if diagnostic.runtime_census_skipped:
        raise CoverageProofError("skip_runtime cannot mint trusted coverage authority")
    if not diagnostic.passed:
        raise CoverageProofError("diagnostic coverage did not pass — cannot mint trusted proof")
    if not diagnostic.provenance_seal:
        raise CoverageProofError("diagnostic census provenance seal missing")
    census_capability = diagnostic.require_census_capability()
    try:
        handle = finalize_diagnostic_and_mint_coverage(
            census_capability,
            diagnostic.mint_ticket,
            coverage_digest=diagnostic.coverage_digest,
            provenance_seal=diagnostic.provenance_seal,
            gate_identity=diagnostic.gate_identity,
            code_revision=diagnostic.code_revision,
        )
    except AuthorityRegistryError as exc:
        raise CoverageProofError(str(exc)) from exc
    return _trusted_coverage_from_handle(handle)


def _bind_lease_and_coverage_records(
    lease: R2bQuiescenceLease,
    trusted_coverage: TrustedCoverageProof,
    *,
    open_evidence_digest: str,
) -> tuple[Any, CoverageAuthorityRecord]:
    verify_r2b_quiescence_lease(
        lease,
        expected_coverage_digest=trusted_coverage.coverage_digest,
        expected_gate_identity=trusted_coverage.gate_identity,
        expected_implementation_revision=trusted_coverage.code_revision,
    )
    lease_record = lookup_lease_handle(lease.authority_handle)
    coverage_record = lookup_coverage_handle(trusted_coverage.authority_handle)
    if lease_record.open_evidence_digest != open_evidence_digest:
        raise CoverageProofError("open_evidence_digest mismatch")
    if lease_record.gate_path != coverage_record.gate_path:
        raise CoverageProofError("gate_path mismatch between lease and trusted coverage")
    if lease_record.gate_protocol != coverage_record.gate_protocol:
        raise CoverageProofError("gate_protocol mismatch between lease and trusted coverage")
    if lease_record.writer_coverage_digest != coverage_record.coverage_digest:
        raise CoverageProofError("writer_coverage_digest mismatch — cross-slice binding failed")
    if lease_record.implementation_revision != coverage_record.code_revision:
        raise CoverageProofError("implementation revision mismatch between lease and coverage")
    return lease_record, coverage_record


def source_authority_from_lease_and_coverage(
    lease: R2bQuiescenceLease,
    trusted_coverage: TrustedCoverageProof,
    *,
    open_evidence_digest: str,
    expected_run_id: str | None = None,
    expected_grant_digest: str | None = None,
    expected_authority_digest: str | None = None,
    expected_inventory_digest: str | None = None,
    expected_runtime_census_digest: str | None = None,
) -> SourceAuthorityProof:
    """Gate lock alone is insufficient — trusted coverage must bind cross-slice."""
    lease_record, coverage_record = _bind_lease_and_coverage_records(
        lease,
        trusted_coverage,
        open_evidence_digest=open_evidence_digest,
    )
    if expected_run_id is not None and lease_record.run_id != expected_run_id:
        raise CoverageProofError("run_id mismatch")
    if expected_grant_digest is not None and lease_record.grant_digest != expected_grant_digest:
        raise CoverageProofError("grant_digest mismatch")
    if (
        expected_authority_digest is not None
        and lease_record.authority_digest != expected_authority_digest
    ):
        raise CoverageProofError("authority_digest mismatch")
    if (
        expected_inventory_digest is not None
        and coverage_record.inventory_digest != expected_inventory_digest
    ):
        raise CoverageProofError("inventory_digest mismatch")
    if (
        expected_runtime_census_digest is not None
        and coverage_record.runtime_census_digest != expected_runtime_census_digest
    ):
        raise CoverageProofError("runtime_census_digest mismatch")
    source_capability = issue_source_capability(
        lease_handle_id=lease.authority_handle.handle_id,
        coverage_handle_id=trusted_coverage.authority_handle.handle_id,
        open_evidence_digest=open_evidence_digest,
        trust_class=lease_record.trust_class,
    )
    source_handle = compose_and_mint_source_authority(
        source_capability,
        lease_handle=lease.authority_handle,
        coverage_handle=trusted_coverage.authority_handle,
        open_evidence_digest=open_evidence_digest,
    )
    return _source_authority_from_handle(source_handle)


def attempt_forge_source_authority_proof(**kwargs: Any) -> None:
    """Attack seam: refuse caller-constructed source authority proofs."""
    SourceAuthorityProof(**kwargs)


def attempt_forge_trusted_coverage_proof(**kwargs: Any) -> None:
    """Attack seam: refuse caller-constructed trusted proofs."""
    TrustedCoverageProof(**kwargs)


def attempt_copy_trusted_coverage_proof(proof: TrustedCoverageProof) -> None:
    copy.copy(proof)


def attempt_deepcopy_trusted_coverage_proof(proof: TrustedCoverageProof) -> None:
    copy.deepcopy(proof)


def attempt_pickle_trusted_coverage_proof(proof: TrustedCoverageProof) -> None:
    pickle.dumps(proof)
