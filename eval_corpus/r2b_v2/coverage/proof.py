"""Runtime census + zero-bypass coverage proof aggregator (I3)."""
# pylint: disable=too-many-instance-attributes,too-many-arguments

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from chroma_write_store import (
    classify_legacy_writer_pids,
    current_code_revision,
    list_pids_with_open_path,
    load_attestation,
)

from eval_corpus.r2b_v2.coverage.inventory import (
    build_static_route_inventory,
    verify_inventory_matches_tip,
    verify_shadow_inventory_unchanged,
)
from eval_corpus.r2b_v2.gate_policy import GatePolicy, production_gate_policy, test_gate_policy
from eval_corpus.r2b_v2.lease import R2bQuiescenceLease, verify_r2b_quiescence_lease
from eval_corpus.r2b_v2.trusted import coverage_token


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

    code_revision: str
    inventory_digest: str
    runtime_census_digest: str
    coverage_digest: str
    gate_identity: str
    gate_path: str
    gate_protocol: int
    runtime_census_skipped: bool = False
    hold_classes: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    passed: bool = False

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

    __slots__ = (
        "code_revision",
        "coverage_digest",
        "gate_identity",
        "gate_path",
        "gate_protocol",
        "inventory_digest",
        "runtime_census_digest",
        "_token",
    )

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
        token: bytes,
    ) -> None:
        if token != coverage_token():
            raise CoverageProofError("TrustedCoverageProof cannot be constructed by callers")
        self.code_revision = code_revision
        self.inventory_digest = inventory_digest
        self.runtime_census_digest = runtime_census_digest
        self.coverage_digest = coverage_digest
        self.gate_identity = gate_identity
        self.gate_path = gate_path
        self.gate_protocol = gate_protocol
        self._token = token

    def __bool__(self) -> bool:
        raise CoverageProofError(
            "TrustedCoverageProof is not reducible to a boolean authority claim"
        )


@dataclass(frozen=True)
class SourceAuthorityProof:
    """Distinct proof that source authority was established — not gate alone."""

    run_id: str
    coverage_digest: str
    gate_held: bool
    gate_identity: str
    gate_path: str


def _resolve_gate_policy(
    gate_policy: GatePolicy | None,
    test_gate_path: Path | None,
) -> GatePolicy:
    if gate_policy is not None and test_gate_path is not None:
        raise CoverageProofError("gate_policy and test_gate_path are mutually exclusive")
    if gate_policy is not None:
        return gate_policy
    if test_gate_path is not None:
        return test_gate_policy(test_gate_path)
    return production_gate_policy()


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
            entrypoint = str(att.get("entrypoint") or "unknown")
            att_revision = str(att.get("code_revision") or "unknown")
            att_gate = str(att.get("gate_path") or "")
            att_protocol = int(att.get("protocol_version") or 0)
            if entrypoint == "unknown" or not cmd:
                holds[CoverageHoldClass.UNKNOWN_WRITER_SIGNATURE.value].append(
                    {"pid": pid, "entrypoint": entrypoint, "cmdline": cmd}
                )
            if revision != "unknown" and att_revision not in {revision, "unknown"}:
                holds[CoverageHoldClass.STALE_REVISION.value].append(
                    {"pid": pid, "revision": att_revision}
                )
            if att_protocol != gate_policy.protocol:
                holds[CoverageHoldClass.ALTERNATE_GATE.value].append(
                    {"pid": pid, "protocol": att_protocol, "expected": gate_policy.protocol}
                )
            if att_gate and att_gate != gate_path:
                holds[CoverageHoldClass.ALTERNATE_GATE.value].append(
                    {"pid": pid, "gate_path": att_gate, "expected": gate_path}
                )
            seen[pid] = RuntimeWriterRecord(
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
    for pid, record in list(seen.items()):
        att = load_attestation(pid, attest_dir=attest_dir)
        if att is None:
            continue
        att_start = str(att.get("start_time") or "")
        if att_start and att_start != "unknown" and att_start != record.start_time:
            holds[CoverageHoldClass.PID_REUSE.value].append(
                {"pid": pid, "att_start": att_start, "proc_start": record.start_time}
            )
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
    revision = code_revision or current_code_revision()
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
    )


def mint_trusted_coverage_proof(
    diagnostic: DiagnosticCoverageResult,
) -> TrustedCoverageProof:
    """Mint trusted coverage proof from a passing diagnostic census."""
    if diagnostic.runtime_census_skipped:
        raise CoverageProofError("skip_runtime cannot mint trusted coverage authority")
    if not diagnostic.passed:
        raise CoverageProofError("diagnostic coverage did not pass — cannot mint trusted proof")
    return TrustedCoverageProof(
        code_revision=diagnostic.code_revision,
        inventory_digest=diagnostic.inventory_digest,
        runtime_census_digest=diagnostic.runtime_census_digest,
        coverage_digest=diagnostic.coverage_digest,
        gate_identity=diagnostic.gate_identity,
        gate_path=diagnostic.gate_path,
        gate_protocol=diagnostic.gate_protocol,
        token=coverage_token(),
    )


def source_authority_from_lease_and_coverage(
    lease: R2bQuiescenceLease,
    trusted_coverage: TrustedCoverageProof,
    *,
    open_evidence_digest: str,
) -> SourceAuthorityProof:
    """Gate lock alone is insufficient — trusted coverage must bind cross-slice."""
    verify_r2b_quiescence_lease(
        lease,
        expected_coverage_digest=trusted_coverage.coverage_digest,
        expected_gate_identity=trusted_coverage.gate_identity,
    )
    bindings = lease.bindings
    if bindings.open_evidence_digest != open_evidence_digest:
        raise CoverageProofError("open_evidence_digest mismatch")
    if bindings.gate_path != trusted_coverage.gate_path:
        raise CoverageProofError("gate_path mismatch between lease and trusted coverage")
    if bindings.gate_protocol != trusted_coverage.gate_protocol:
        raise CoverageProofError("gate_protocol mismatch between lease and trusted coverage")
    if bindings.writer_coverage_digest != trusted_coverage.coverage_digest:
        raise CoverageProofError("writer_coverage_digest mismatch — cross-slice binding failed")
    return SourceAuthorityProof(
        run_id=bindings.run_id,
        coverage_digest=trusted_coverage.coverage_digest,
        gate_held=True,
        gate_identity=trusted_coverage.gate_identity,
        gate_path=trusted_coverage.gate_path,
    )
