# pylint: disable=too-many-instance-attributes
"""Scratch-only C6 performance canary for the disabled Shadow implementation.

The canary deliberately creates a disposable Chroma root and Shadow artifacts
only below a caller-selected new private scratch directory.  It never opens a
production Chroma root for write and never changes the live configuration.
"""

from __future__ import annotations

import json
import math
import os
import platform
import re
import stat
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from chroma_readonly import collection_uuid
from chroma_store import ChromaStore
from chroma_write_store import DEFAULT_WRITER_LOCK, current_code_revision
from writer_census import WriterCensusRefused, load_writer_census_report
from shadow_authorization import open_directory_nofollow
from shadow_ledger import (
    ARTIFACT_FILE_MODE,
    SHADOW_DIR_MODE,
    atomic_write_json_private_secure,
    compute_ledger_header_hash,
    create_shadow_ledger_header,
    open_existing_shadow_ledger_fd,
    write_all_fd,
)
from shadow_sink import JsonlUnitMutationSink
from shadow_validation import build_valid_manifest_fixture, validate_shadow_activation


class CanaryRefused(RuntimeError):
    """A fail-closed canary refusal with a stable, redacted public code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class CanaryBudgets:
    """Ryan-approved C6 thresholds; not the legacy sink degradation marker."""

    append_p99_ms: float = 100.0
    append_max_ms: float = 500.0
    degradation_p99_factor: float = 2.0
    cold_open_p99_ms: float = 500.0
    rollback_p99_ms: float = 300.0
    rollback_factor: float = 3.0
    rollback_window_seconds: int = 60
    rollback_min_samples: int = 100
    horizon_events: int = 50_000


APPROVED_BUDGETS = CanaryBudgets()
MIN_TIMED_SAMPLES = 1_000
MIN_WARMUP_APPENDS = 100
MIN_WARMUP_SECONDS = 1.0
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CLI_INPUT_FIELDS = (
    "scratch_dir",
    "intended_ledger_path",
    "chroma_root",
    "unit_count",
    "p50_event_bytes",
    "p95_event_bytes",
    "maximum_event_bytes",
    "event_size_evidence_sha256",
    "writer_census_report",
)


@dataclass(frozen=True)
class CanaryInputs:
    """Operator-supplied, payload-free matrix inputs for one scratch run."""

    scratch_dir: Path
    intended_ledger_path: Path
    production_chroma_root: Path
    current_unit_count: int
    p50_event_bytes: int
    p95_event_bytes: int
    maximum_event_bytes: int
    peak_writers: int
    short_lived_opens_per_day: int
    event_size_evidence_sha256: str
    writer_census_sha256: str

    def event_sizes(self) -> tuple[tuple[str, int], ...]:
        return (
            ("control_1k", 1_024),
            ("p50", self.p50_event_bytes),
            ("p95", self.p95_event_bytes),
            ("maximum", self.maximum_event_bytes),
        )

    def volumes(self, budgets: CanaryBudgets = APPROVED_BUDGETS) -> tuple[tuple[str, int], ...]:
        return (
            ("header_only", 0),
            ("n", self.current_unit_count),
            ("2n", self.current_unit_count * 2),
            ("horizon", budgets.horizon_events),
        )

    def concurrency(self) -> tuple[tuple[str, int], ...]:
        return (
            ("one_writer", 1),
            ("census_peak", self.peak_writers),
            ("above_peak", self.peak_writers + 1),
        )


def inputs_from_cli_values(values: Mapping[str, Any]) -> CanaryInputs:
    """Convert the thin CLI's raw options into one complete canary request."""
    if any(values.get(field) is None for field in CLI_INPUT_FIELDS):
        raise CanaryRefused(
            "canary_input_missing",
            "all scratch, census, and redacted matrix inputs are required",
        )
    try:
        census, census_sha256 = load_writer_census_report(
            Path(values["writer_census_report"]),
            chroma_root=Path(values["chroma_root"]),
            writer_gate_path=DEFAULT_WRITER_LOCK.expanduser(),
        )
    except WriterCensusRefused as exc:
        raise CanaryRefused(exc.code, exc.detail) from exc
    return CanaryInputs(
        scratch_dir=Path(values["scratch_dir"]),
        intended_ledger_path=Path(values["intended_ledger_path"]),
        production_chroma_root=Path(values["chroma_root"]),
        current_unit_count=int(values["unit_count"]),
        p50_event_bytes=int(values["p50_event_bytes"]),
        p95_event_bytes=int(values["p95_event_bytes"]),
        maximum_event_bytes=int(values["maximum_event_bytes"]),
        peak_writers=int(census["max_concurrent_writer_sessions"]),
        short_lived_opens_per_day=int(census["conservative_short_lived_opens_per_day"]),
        event_size_evidence_sha256=str(values["event_size_evidence_sha256"]),
        writer_census_sha256=census_sha256,
    )


@dataclass(frozen=True)
class MountIdentity:
    mount_id: str
    filesystem: str
    mount_options: str
    super_options: str
    device: int


@dataclass(frozen=True)
class TimingSample:
    end_to_end_ms: float
    complete_append_ms: float | None
    lock_wait_ms: float | None
    ledger_append_ms: float | None
    health_persist_ms: float | None


@dataclass(frozen=True)
class WorkloadResult:
    samples: tuple[TimingSample, ...]
    errors: tuple[str, ...]
    elapsed_ms: float


@dataclass(frozen=True)
class CellEvaluation:
    passed: bool
    codes: tuple[str, ...]
    append: Mapping[str, float]
    baseline: Mapping[str, float]
    degradation_p99_factor: float
    cold_open: Mapping[str, float]


@dataclass
class CanaryReport:
    verdict: str
    budgets: Mapping[str, Any]
    provenance: Mapping[str, Any]
    matrix: list[Mapping[str, Any]] = field(default_factory=list)
    codes: list[str] = field(default_factory=list)
    evidence_path: str | None = None


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _is_same_or_under(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


def _nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists():
        if current == current.parent:
            raise CanaryRefused("canary_path_missing", "no existing intended-path ancestor")
        current = current.parent
    if not current.is_dir():
        raise CanaryRefused("canary_path_invalid", "intended-path ancestor is not a directory")
    return current


def _create_new_private_dir(target: Path) -> Path:
    """Create one new 0700 child without accepting an existing/raced directory."""
    parent_fd = open_directory_nofollow(target.parent)
    child_fd = -1
    try:
        try:
            os.mkdir(target.name, SHADOW_DIR_MODE, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise CanaryRefused("canary_scratch_exists", "scratch directory already exists") from exc
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        child_fd = os.open(target.name, flags, dir_fd=parent_fd)
        os.fchmod(child_fd, SHADOW_DIR_MODE)
        st = os.fstat(child_fd)
        entry = os.stat(target.name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            not stat.S_ISDIR(st.st_mode)
            or st.st_uid != os.geteuid()
            or stat.S_IMODE(st.st_mode) != SHADOW_DIR_MODE
            or (st.st_dev, st.st_ino) != (entry.st_dev, entry.st_ino)
        ):
            raise CanaryRefused("canary_scratch_private", "new scratch identity/mode invalid")
        os.fsync(parent_fd)
    except OSError as exc:
        raise CanaryRefused("canary_scratch_private", "cannot create private scratch") from exc
    finally:
        if child_fd >= 0:
            os.close(child_fd)
        os.close(parent_fd)
    return target


def _mount_identity(path: Path, mountinfo_text: str) -> MountIdentity:
    target = str(path)
    best_length = -1
    best_identity: MountIdentity | None = None
    for line in mountinfo_text.splitlines():
        if " - " not in line:
            continue
        before, after = line.split(" - ", 1)
        fields = before.split()
        suffix = after.split()
        if len(fields) < 6 or len(suffix) < 3:
            continue
        mountpoint = fields[4]
        for escaped, literal in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
            mountpoint = mountpoint.replace(escaped, literal)
        if target != mountpoint and not target.startswith(mountpoint.rstrip("/") + "/"):
            continue
        candidate = MountIdentity(
            mount_id=fields[0],
            filesystem=suffix[0],
            mount_options=fields[5],
            super_options=suffix[2],
            device=os.stat(path).st_dev,
        )
        if len(mountpoint) > best_length:
            best_length = len(mountpoint)
            best_identity = candidate
    if best_identity is None:
        raise CanaryRefused("canary_mount_unknown", "mount metadata did not cover path")
    return best_identity


def validate_scratch_target(
    inputs: CanaryInputs,
    *,
    mountinfo_text: str | None = None,
) -> tuple[Path, MountIdentity]:
    """Fail closed unless a new private scratch root shares the target mount.

    Only directory metadata is inspected for the intended production paths.  No
    ledger, manifest, health file, config, or Chroma database is opened.
    """
    scratch = _absolute(inputs.scratch_dir)
    target_ledger = _absolute(inputs.intended_ledger_path)
    chroma = _absolute(inputs.production_chroma_root)
    if scratch.exists():
        raise CanaryRefused("canary_scratch_exists", "scratch directory must be new")
    if not scratch.parent.is_dir():
        raise CanaryRefused("canary_path_missing", "scratch parent must already exist")
    if _is_same_or_under(scratch, chroma) or _is_same_or_under(chroma, scratch):
        raise CanaryRefused("canary_live_path", "scratch overlaps production Chroma")
    if _is_same_or_under(target_ledger, chroma):
        raise CanaryRefused("canary_live_path", "intended ledger lies inside production Chroma")
    if _is_same_or_under(scratch, target_ledger) or _is_same_or_under(target_ledger, scratch):
        raise CanaryRefused("canary_live_path", "scratch overlaps intended ledger")

    target_parent = _nearest_existing_parent(target_ledger.parent)
    try:
        text = mountinfo_text or Path("/proc/self/mountinfo").read_text(encoding="utf-8")
        target_mount = _mount_identity(target_parent, text)
        scratch_mount = _mount_identity(scratch.parent, text)
    except OSError as exc:
        raise CanaryRefused("canary_mount_unknown", "cannot inspect mount metadata") from exc
    if target_mount != scratch_mount:
        raise CanaryRefused(
            "canary_mount_mismatch",
            "scratch must use the same mount, filesystem, and options as intended ledger",
        )
    if target_mount.filesystem not in {"ext4", "xfs", "btrfs", "tmpfs"}:
        raise CanaryRefused("canary_filesystem_unsupported", target_mount.filesystem)
    _create_new_private_dir(scratch)
    return scratch, scratch_mount


def _validate_inputs(inputs: CanaryInputs, budgets: CanaryBudgets) -> None:
    if inputs.current_unit_count < 0:
        raise CanaryRefused("canary_input_invalid", "current_unit_count must be non-negative")
    if inputs.peak_writers < 1:
        raise CanaryRefused("canary_input_invalid", "peak_writers must be at least one")
    if inputs.short_lived_opens_per_day < 0:
        raise CanaryRefused("canary_input_invalid", "short_lived_opens_per_day must be non-negative")
    if budgets.horizon_events <= inputs.current_unit_count * 2:
        raise CanaryRefused("canary_input_invalid", "horizon must exceed 2N")
    sizes = [size for _label, size in inputs.event_sizes()]
    if any(size <= 0 for size in sizes):
        raise CanaryRefused("canary_input_invalid", "event sizes must be positive")
    if not inputs.p50_event_bytes <= inputs.p95_event_bytes <= inputs.maximum_event_bytes:
        raise CanaryRefused("canary_input_invalid", "event sizes must be ordered p50/p95/max")
    if not _SHA256_RE.fullmatch(inputs.event_size_evidence_sha256):
        raise CanaryRefused("canary_input_invalid", "event-size evidence must be a SHA-256")
    if not _SHA256_RE.fullmatch(inputs.writer_census_sha256):
        raise CanaryRefused("canary_input_invalid", "writer census evidence must be a SHA-256")


def _percentiles(values: Iterable[float]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise CanaryRefused("canary_no_samples", "metric has no samples")

    def rank(percent: float) -> float:
        index = max(0, math.ceil((percent / 100.0) * len(ordered)) - 1)
        return ordered[index]

    mean = sum(ordered) / len(ordered)
    variance = sum((value - mean) ** 2 for value in ordered) / len(ordered)
    return {
        "count": float(len(ordered)),
        "p50_ms": rank(50),
        "p95_ms": rank(95),
        "p99_ms": rank(99),
        "max_ms": ordered[-1],
        "mean_ms": mean,
        "stddev_ms": math.sqrt(variance),
    }


def evaluate_cell(
    *,
    append_samples: Iterable[TimingSample],
    baseline_samples: Iterable[TimingSample],
    cold_open_ms: Iterable[float],
    budgets: CanaryBudgets = APPROVED_BUDGETS,
) -> CellEvaluation:
    """Apply the approved absolute and relative limits without hiding errors."""
    appended = list(append_samples)
    baseline = list(baseline_samples)
    complete = [sample.complete_append_ms for sample in appended]
    if any(value is None for value in complete):
        return CellEvaluation(False, ("performance_budget_exceeded",), {}, {}, math.inf, {})
    append = _percentiles(value for value in complete if value is not None)
    baseline_stats = _percentiles(sample.end_to_end_ms for sample in baseline)
    cold = _percentiles(cold_open_ms)
    if baseline_stats["p99_ms"] <= 0:
        return CellEvaluation(False, ("performance_budget_exceeded",), append, baseline_stats, math.inf, cold)
    factor = append["p99_ms"] / baseline_stats["p99_ms"]
    codes: list[str] = []
    if append["p99_ms"] > budgets.append_p99_ms:
        codes.append("append_p99_exceeded")
    if append["max_ms"] > budgets.append_max_ms:
        codes.append("append_max_exceeded")
    if factor > budgets.degradation_p99_factor:
        codes.append("degradation_p99_exceeded")
    if cold["p99_ms"] > budgets.cold_open_p99_ms:
        codes.append("cold_open_p99_exceeded")
    return CellEvaluation(not codes, tuple(codes), append, baseline_stats, factor, cold)


def _timing_breakdown(samples: Iterable[TimingSample], elapsed_ms: float) -> dict[str, Any]:
    items = list(samples)
    fields = {
        "end_to_end": [sample.end_to_end_ms for sample in items],
        "complete_append": [sample.complete_append_ms for sample in items],
        "lock_wait": [sample.lock_wait_ms for sample in items],
        "ledger_append": [sample.ledger_append_ms for sample in items],
        "health_persist": [sample.health_persist_ms for sample in items],
    }
    out: dict[str, Any] = {}
    for name, values in fields.items():
        if any(value is None for value in values):
            out[name] = None
        else:
            out[name] = _percentiles(value for value in values if value is not None)
    out["throughput_ops_per_second"] = (
        (len(items) * 1000.0 / elapsed_ms) if elapsed_ms > 0 else 0.0
    )
    return out


def live_rollback_required(
    samples: Iterable[TimingSample],
    *,
    disabled_p99_ms: float,
    budgets: CanaryBudgets = APPROVED_BUDGETS,
) -> bool:
    """Evaluate samples already selected by a future live monitor.

    C6 is a batch canary and does not collect append timestamps.  The future
    activation monitor owns construction of the approved rolling 60-second
    window before calling this predicate.  This helper enforces only the
    minimum-100-sample qualification and the approved p99/factor thresholds;
    lower-volume input is telemetry-only.
    """
    values = list(samples)
    if len(values) < budgets.rollback_min_samples:
        return False
    complete = [sample.complete_append_ms for sample in values]
    if any(value is None for value in complete) or disabled_p99_ms <= 0:
        return False
    p99 = _percentiles(value for value in complete if value is not None)["p99_ms"]
    return p99 > budgets.rollback_p99_ms or (p99 / disabled_p99_ms) > budgets.rollback_factor


def _write_private_bytes(path: Path, data: bytes) -> None:
    parent_fd = open_directory_nofollow(path.parent)
    fd = -1
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path.name, flags, ARTIFACT_FILE_MODE, dir_fd=parent_fd)
        os.fchmod(fd, ARTIFACT_FILE_MODE)
        st = os.fstat(fd)
        if stat.S_IMODE(st.st_mode) != ARTIFACT_FILE_MODE or st.st_uid != os.geteuid():
            raise CanaryRefused("canary_private_write", "private evidence mode/owner mismatch")
        write_all_fd(fd, data)
        os.fsync(fd)
        os.fsync(parent_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(parent_fd)


def _private_child(parent: Path, name: str) -> Path:
    target = parent / name
    return _create_new_private_dir(target)


def _seed_event(sequence: int) -> bytes:
    """Synthetic, payload-free-in-report record valid for strict full scans."""
    event = {
        "shadow_schema_version": 1,
        "event_id": f"canary-seed-{sequence:08d}",
        "sequence": sequence,
        "collection": "knowledge_units",
        "operation": "replace",
        "stable_entity_id": f"canary-seed-{sequence:08d}",
        "post_state": {"document": "x", "metadata": {}, "deleted": False},
    }
    return (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def seed_synthetic_ledger(ledger_path: Path, event_count: int) -> None:
    """Bulk-seed a private ledger outside the timed path using synthetic records."""
    if event_count < 0:
        raise CanaryRefused("canary_input_invalid", "seed event count must be non-negative")
    fd, dir_fd, _st = open_existing_shadow_ledger_fd(ledger_path)
    try:
        os.lseek(fd, 0, os.SEEK_END)
        batch = bytearray()
        for sequence in range(1, event_count + 1):
            batch.extend(_seed_event(sequence))
            if len(batch) >= 1_048_576:
                write_all_fd(fd, bytes(batch))
                batch.clear()
        if batch:
            write_all_fd(fd, bytes(batch))
        os.fsync(fd)
    finally:
        os.close(fd)
        os.close(dir_fd)


def _prepare_validation_fixture(root: Path, event_count: int) -> tuple[Path, Path, Path]:
    """Create a full C1-valid scratch activation solely for cold-open timing."""
    shadow = _private_child(root, "shadow")
    chroma = _private_child(root, "chroma")
    config_path = root / "canary-config.toml"
    ledger_path = shadow / "ledger.jsonl"
    health_path = shadow / "health.json"
    manifest_path = shadow / "manifest.json"
    activation_id = f"canary-{uuid.uuid4()}"
    identity = str(uuid.uuid4())
    header = create_shadow_ledger_header(
        ledger_path,
        activation_id=activation_id,
        ledger_identity=identity,
        starting_sequence=0,
    )
    seed_synthetic_ledger(ledger_path, event_count)
    atomic_write_json_private_secure(health_path, {"status": "canary"})
    store = ChromaStore(str(chroma))
    try:
        store.count_units(include_superseded=True)
    finally:
        store.close()
    manifest = build_valid_manifest_fixture(
        activation_id=activation_id,
        code_commit=current_code_revision(),
        chroma_root=chroma,
        collection_uuid=collection_uuid(chroma, "knowledge_units"),
        shadow_ledger_identity=identity,
        ledger_header_hash=compute_ledger_header_hash(header),
    )
    atomic_write_json_private_secure(manifest_path, manifest)
    config = (
        "[index]\n"
        f"chroma_dir = {json.dumps(str(chroma))}\n\n"
        "[shadow_ledger]\n"
        "enabled = true\n"
        f"ledger_path = {json.dumps(str(ledger_path))}\n"
        f"activation_manifest_path = {json.dumps(str(manifest_path))}\n"
        f"health_path = {json.dumps(str(health_path))}\n"
        f"activation_id = {json.dumps(activation_id)}\n"
        f"manifest_sha256 = {json.dumps(manifest['manifest_canonical_hash'])}\n"
    )
    _write_private_bytes(config_path, config.encode("utf-8"))
    return config_path, chroma, ledger_path


def cold_open_validation_ms(root: Path, event_count: int) -> float:
    """Time the shared strict writer validation over one fresh scratch fixture."""
    config_path, chroma, _ledger = _prepare_validation_fixture(root, event_count)
    started = time.monotonic()
    result = validate_shadow_activation(
        config_path, chroma, "writer", runtime_code_revision=current_code_revision()
    )
    elapsed = (time.monotonic() - started) * 1000.0
    if not result.inject_eligible:
        codes = ",".join(result.codes()) or "unknown"
        raise CanaryRefused("canary_validation_failed", codes)
    return elapsed


def _synthetic_document(size: int) -> str:
    return "x" * size


def _run_workload(
    root: Path,
    *,
    event_bytes: int,
    concurrency: int,
    timed_samples: int,
    with_shadow: bool,
) -> WorkloadResult:
    """Run a disposable Chroma mutation workload; no production root is opened."""
    chroma = _private_child(root, "chroma")
    shadow = _private_child(root, "shadow") if with_shadow else None
    ledger = shadow / "ledger.jsonl" if shadow else None
    health = shadow / "health.json" if shadow else None
    if ledger is not None:
        create_shadow_ledger_header(
            ledger,
            activation_id=f"canary-{uuid.uuid4()}",
            ledger_identity=str(uuid.uuid4()),
        )
    document = _synthetic_document(event_bytes)
    metadata = {"canary": True, "synthetic_size": event_bytes}
    errors: list[str] = []

    def perform(
        store: ChromaStore,
        sink: JsonlUnitMutationSink | None,
        worker: int,
        ordinal: int,
        timed: bool,
    ) -> TimingSample | None:
        try:
            started = time.monotonic()
            store.add_unit(
                f"canary-{worker}-{ordinal}", document, [0.1, 0.2, 0.3, 0.4], metadata
            )
            elapsed = (time.monotonic() - started) * 1000.0
            if not timed:
                return None
            timing = sink.last_timing if sink is not None else None
            if sink is not None:
                telemetry = sink.telemetry()
                failure = telemetry.get("last_failure_class")
                if failure or telemetry.get("health_persist_failed"):
                    errors.append(f"shadow_{failure or 'health_persist_failed'}")
            return TimingSample(
                end_to_end_ms=elapsed,
                complete_append_ms=timing.complete_append_ms if timing else None,
                lock_wait_ms=timing.lock_wait_ms if timing else None,
                ledger_append_ms=timing.ledger_append_ms if timing else None,
                health_persist_ms=timing.health_persist_ms if timing else None,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(type(exc).__name__)
            return None

    # The warm-up is deliberately not timed.  It is at least 100 appends and
    # extends to one second when 100 appends finish sooner.
    warm_start = time.monotonic()
    warm_ordinal = 0
    warm_sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health) if ledger else None
    warm_store = ChromaStore(str(chroma), mutation_sink=warm_sink)
    try:
        while (
            warm_ordinal < MIN_WARMUP_APPENDS
            or time.monotonic() - warm_start < MIN_WARMUP_SECONDS
        ):
            perform(warm_store, warm_sink, 0, warm_ordinal, False)
            warm_ordinal += 1
    finally:
        warm_store.close()

    def worker(worker_id: int) -> list[TimingSample]:
        out: list[TimingSample] = []
        sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health) if ledger else None
        store = ChromaStore(str(chroma), mutation_sink=sink)
        try:
            for ordinal in range(worker_id, timed_samples, concurrency):
                sample = perform(store, sink, worker_id, warm_ordinal + ordinal, True)
                if sample is not None:
                    out.append(sample)
        finally:
            store.close()
        return out

    timed_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        samples = [sample for batch in executor.map(worker, range(concurrency)) for sample in batch]
    return WorkloadResult(
        samples=tuple(samples),
        errors=tuple(errors),
        elapsed_ms=(time.monotonic() - timed_start) * 1000.0,
    )


def _provenance(mount: MountIdentity, inputs: CanaryInputs) -> dict[str, Any]:
    return {
        "code_revision": current_code_revision(),
        "python": sys.version.split()[0],
        "kernel": platform.release(),
        "cpu_load": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
        "filesystem": mount.filesystem,
        "mount_id": mount.mount_id,
        "mount_options": mount.mount_options,
        "super_options": mount.super_options,
        "current_unit_count": inputs.current_unit_count,
        "short_lived_opens_per_day": inputs.short_lived_opens_per_day,
        "event_size_evidence_sha256": inputs.event_size_evidence_sha256,
        "writer_census_sha256": inputs.writer_census_sha256,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payloads": "synthetic lengths only; no production payloads retained",
    }


def run_shadow_canary(
    inputs: CanaryInputs,
    *,
    budgets: CanaryBudgets = APPROVED_BUDGETS,
    timed_samples: int = MIN_TIMED_SAMPLES,
    independent_runs: int = 3,
) -> CanaryReport:
    """Execute the complete C6 scratch matrix and retain private raw evidence."""
    _validate_inputs(inputs, budgets)
    if timed_samples < MIN_TIMED_SAMPLES:
        raise CanaryRefused("canary_input_invalid", "at least 1000 timed samples are required")
    if independent_runs != 3:
        raise CanaryRefused("canary_input_invalid", "exactly three independent runs are required")
    scratch, mount = validate_scratch_target(inputs)
    report = CanaryReport(
        verdict="PASS",
        budgets=asdict(budgets),
        provenance=_provenance(mount, inputs),
    )
    for size_label, event_bytes in inputs.event_sizes():
        for volume_label, volume in inputs.volumes(budgets):
            for concurrency_label, concurrency in inputs.concurrency():
                append_samples: list[TimingSample] = []
                baseline_samples: list[TimingSample] = []
                cold_samples: list[float] = []
                errors: list[str] = []
                append_elapsed_ms = 0.0
                baseline_elapsed_ms = 0.0
                for run_number in range(independent_runs):
                    run_root = _private_child(
                        scratch,
                        f"{size_label}-{volume_label}-{concurrency_label}-run{run_number + 1}",
                    )
                    cold_samples.append(cold_open_validation_ms(_private_child(run_root, "cold"), volume))
                    baseline = _run_workload(
                        _private_child(run_root, "baseline"),
                        event_bytes=event_bytes,
                        concurrency=concurrency,
                        timed_samples=timed_samples,
                        with_shadow=False,
                    )
                    appended = _run_workload(
                        _private_child(run_root, "shadow_enabled"),
                        event_bytes=event_bytes,
                        concurrency=concurrency,
                        timed_samples=timed_samples,
                        with_shadow=True,
                    )
                    baseline_samples.extend(baseline.samples)
                    append_samples.extend(appended.samples)
                    errors.extend(baseline.errors + appended.errors)
                    baseline_elapsed_ms += baseline.elapsed_ms
                    append_elapsed_ms += appended.elapsed_ms
                if errors or len(append_samples) != len(baseline_samples) or not append_samples:
                    evaluation = CellEvaluation(False, ("canary_workload_error",), {}, {}, math.inf, {})
                else:
                    evaluation = evaluate_cell(
                        append_samples=append_samples,
                        baseline_samples=baseline_samples,
                        cold_open_ms=cold_samples,
                        budgets=budgets,
                    )
                cell = {
                    "event_size_class": size_label,
                    "synthetic_event_bytes": event_bytes,
                    "ledger_volume": volume_label,
                    "ledger_events": volume,
                    "concurrency": concurrency_label,
                    "writers": concurrency,
                    "runs": independent_runs,
                    "timed_samples": len(append_samples),
                    "errors": sorted(set(errors)),
                    "passed": evaluation.passed,
                    "codes": list(evaluation.codes),
                    "append": dict(evaluation.append),
                    "baseline": dict(evaluation.baseline),
                    "append_timing": _timing_breakdown(
                        append_samples,
                        append_elapsed_ms,
                    ),
                    "baseline_timing": _timing_breakdown(
                        baseline_samples,
                        baseline_elapsed_ms,
                    ),
                    "degradation_p99_factor": evaluation.degradation_p99_factor,
                    "cold_open": dict(evaluation.cold_open),
                    "daily_cold_validation_ms": (
                        evaluation.cold_open.get("mean_ms", 0.0) * inputs.short_lived_opens_per_day
                        if evaluation.cold_open
                        else None
                    ),
                }
                report.matrix.append(cell)
                if not evaluation.passed:
                    report.verdict = "FAIL"
                    report.codes.extend(evaluation.codes)
    report.codes = sorted(set(report.codes))
    evidence_path = scratch / "c6-canary-evidence.json"
    evidence = asdict(report)
    evidence["evidence_path"] = None  # Absolute scratch paths never enter retained JSON.
    atomic_write_json_private_secure(evidence_path, evidence)
    report.evidence_path = str(evidence_path)
    return report


def redacted_report(report: CanaryReport) -> dict[str, Any]:
    """Return CLI-safe evidence: thresholds, metrics, hashes/metadata, never payloads."""
    return {
        "verdict": report.verdict,
        "codes": list(report.codes),
        "budgets": dict(report.budgets),
        "provenance": dict(report.provenance),
        "matrix": list(report.matrix),
        "evidence_written": report.evidence_path is not None,
    }
