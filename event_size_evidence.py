# pylint: disable=too-many-lines
"""Payload-free C6 event-size evidence companion (disabled unless explicitly armed).

The companion observes encoded event sizes through the shared shadow_sink encoder
without retaining payload, metadata, identifiers, or paths.  It binds durable
summaries to one exact C7 census window and must finalize before the matching
C7 writer-session close is published.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from shadow_ledger import sha256_canonical
from shadow_sink import build_mutation_event, encode_event_line

EVENT_SIZE_CONTRACT_VERSION = 1
EVENT_SIZE_ENCODER_REVISION = 1
SUMMARY_NAME = "event-size-summary.json"
ARTIFACT_MODE = 0o600
DIRECTORY_MODE = 0o700
# Fixed histogram buckets (bytes); overflow counts land in histogram_overflow.
HISTOGRAM_BUCKETS = (
    256,
    512,
    1024,
    2048,
    4096,
    8192,
    16384,
    32768,
    65536,
    131071,
)
MAX_RETAINED_OBSERVATIONS = 50_000


class EventSizeEvidenceRefused(RuntimeError):
    """Fail-closed companion refusal with a stable code."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass
class InertnessCounters:
    """Test instrumentation: must remain zero when companion is unarmed."""

    encoder_calls: int = 0
    evidence_hashes: int = 0
    histogram_allocations: int = 0
    per_mutation_artifact_stats: int = 0
    evidence_io_ops: int = 0
    c7_header_parses: int = 0
    retained_observations: int = 0

    def snapshot(self) -> dict[str, int]:
        return {
            "encoder_calls": self.encoder_calls,
            "evidence_hashes": self.evidence_hashes,
            "histogram_allocations": self.histogram_allocations,
            "per_mutation_artifact_stats": self.per_mutation_artifact_stats,
            "evidence_io_ops": self.evidence_io_ops,
            "c7_header_parses": self.c7_header_parses,
            "retained_observations": self.retained_observations,
        }


_inertness = InertnessCounters()
_inertness_lock = threading.Lock()
_session_local = threading.local()


def inertness_snapshot() -> dict[str, int]:
    with _inertness_lock:
        return _inertness.snapshot()


def reset_inertness_counters() -> None:
    with _inertness_lock:
        for key in _inertness.snapshot():
            setattr(_inertness, key, 0)


def _bump_inertness(**kwargs: int) -> None:
    with _inertness_lock:
        for name, delta in kwargs.items():
            setattr(_inertness, name, getattr(_inertness, name) + int(delta))


@dataclass(frozen=True)
class EventSizeBinding:
    census_id: str
    window_start_utc: str
    window_end_utc: str
    code_revision: str
    writer_gate_protocol: int
    chroma_root_identity: str
    writer_gate_identity: str
    census_report_sha256: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "census_id": self.census_id,
            "window_start_utc": self.window_start_utc,
            "window_end_utc": self.window_end_utc,
            "code_revision": self.code_revision,
            "writer_gate_protocol": self.writer_gate_protocol,
            "chroma_root_identity": self.chroma_root_identity,
            "writer_gate_identity": self.writer_gate_identity,
            "contract_version": EVENT_SIZE_CONTRACT_VERSION,
            "encoder_revision": EVENT_SIZE_ENCODER_REVISION,
        }
        if self.census_report_sha256 is not None:
            out["census_report_sha256"] = self.census_report_sha256
        return out


@dataclass
class BoundedSizeHistogram:
    """Fixed-memory size histogram with explicit overflow accounting."""

    bucket_edges: tuple[int, ...] = HISTOGRAM_BUCKETS
    counts: dict[int, int] = field(default_factory=dict)
    overflow: int = 0
    total_observations: int = 0
    measurement_gaps: int = 0

    def __post_init__(self) -> None:
        _bump_inertness(histogram_allocations=1)
        for edge in self.bucket_edges:
            self.counts.setdefault(edge, 0)

    def observe(self, size_bytes: int) -> None:
        if self.total_observations >= MAX_RETAINED_OBSERVATIONS:
            self.overflow += 1
            return
        self.total_observations += 1
        _bump_inertness(retained_observations=1)
        placed = False
        for edge in self.bucket_edges:
            if size_bytes <= edge:
                self.counts[edge] = self.counts.get(edge, 0) + 1
                placed = True
                break
        if not placed:
            self.overflow += 1

    def record_gap(self) -> None:
        self.measurement_gaps += 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "bucket_edges": list(self.bucket_edges),
            "counts": {str(k): v for k, v in sorted(self.counts.items())},
            "overflow": self.overflow,
            "total_observations": self.total_observations,
            "measurement_gaps": self.measurement_gaps,
            "bounded": True,
            "max_retained": MAX_RETAINED_OBSERVATIONS,
        }


@dataclass
class EventSizeCompanion:
    """Session-scoped numeric observer; finalize before C7 close."""

    census_dir: Path
    binding: EventSizeBinding
    session_nonce: str
    histogram: BoundedSizeHistogram = field(default_factory=BoundedSizeHistogram)
    operation_counts: dict[str, int] = field(default_factory=dict)
    in_window_mutations: int = 0
    cross_boundary_mutations: int = 0
    sticky_failure: str | None = None
    finalized: bool = False
    opened_at_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    )

    def observe_mutation(
        self,
        *,
        operation: str,
        document: str | None,
        metadata: Mapping[str, Any] | None,
        deleted: bool,
        embed_model: str = "unknown",
        embed_dims: int | None = None,
        in_window: bool,
    ) -> None:
        if self.finalized or self.sticky_failure:
            return
        _bump_inertness(encoder_calls=1)
        event = build_mutation_event(
            event_id="00000000-0000-0000-0000-000000000000",
            sequence=1,
            operation=operation,
            stable_entity_id="size-estimate",
            document=document,
            metadata=metadata,
            deleted=deleted,
            embed_model=embed_model,
            embed_dims=embed_dims,
            writer_route="",
        )
        data = encode_event_line(event)
        size_bytes = len(data)
        _bump_inertness(evidence_hashes=1)
        self.histogram.observe(size_bytes)
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
        if in_window:
            self.in_window_mutations += 1
        else:
            self.cross_boundary_mutations += 1

    def record_measurement_gap(self, *, reason: str) -> None:
        self.histogram.record_gap()
        if self.sticky_failure is None:
            self.sticky_failure = reason

    def summary_payload(self) -> dict[str, Any]:
        digest_input = {
            "binding": self.binding.as_dict(),
            "histogram": self.histogram.as_dict(),
            "operation_counts": dict(sorted(self.operation_counts.items())),
            "in_window_mutations": self.in_window_mutations,
            "cross_boundary_mutations": self.cross_boundary_mutations,
            "session_nonce": self.session_nonce,
            "opened_at_utc": self.opened_at_utc,
            "closed_at_utc": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "sticky_failure": self.sticky_failure,
            "payloads": "none",
        }
        summary_hash = hashlib.sha256(
            json.dumps(digest_input, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return {
            **digest_input,
            "summary_sha256": summary_hash,
        }

    def finalize(self) -> dict[str, Any]:
        if self.finalized:
            raise EventSizeEvidenceRefused(
                "companion_already_finalized", "companion finalize called twice"
            )
        if self.sticky_failure:
            raise EventSizeEvidenceRefused(
                "companion_sticky_failure", self.sticky_failure
            )
        payload = self.summary_payload()
        _persist_summary(self.census_dir, payload)
        self.finalized = True
        return payload


def _utc_stamp(value: datetime | None = None) -> str:
    return (value or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _private_dir(path: Path, *, create: bool) -> Path:
    target = path.expanduser().absolute()
    if create:
        target.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
    st = os.lstat(target)
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise EventSizeEvidenceRefused("census_path_unsafe", "census directory unsafe")
    if st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != DIRECTORY_MODE:
        raise EventSizeEvidenceRefused(
            "census_permission_invalid", "census directory must be private 0700"
        )
    return target


def _read_census_header(census_dir: Path) -> dict[str, Any]:
    _bump_inertness(c7_header_parses=1)
    path = census_dir / "census-header.json"
    try:
        st = os.lstat(path)
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            raise EventSizeEvidenceRefused("census_path_unsafe", "header unsafe")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EventSizeEvidenceRefused(
            "census_header_unreadable", "cannot read census header"
        ) from exc
    if not isinstance(data, dict):
        raise EventSizeEvidenceRefused("census_header_invalid", "header not object")
    return data


def is_companion_armed(census_dir: Path | None) -> bool:
    if census_dir is None:
        return False
    directory = census_dir.expanduser()
    if not directory.is_dir():
        return False
    try:
        header = _read_census_header(_private_dir(directory, create=False))
    except EventSizeEvidenceRefused:
        return False
    return header.get("event_size_evidence_armed") is True


def _binding_from_header(header: Mapping[str, Any]) -> EventSizeBinding:
    required = (
        "census_id",
        "window_start_utc",
        "window_end_utc",
        "code_revision",
        "writer_gate_protocol",
        "chroma_root_identity",
        "writer_gate_identity",
    )
    missing = [key for key in required if header.get(key) is None]
    if missing:
        raise EventSizeEvidenceRefused(
            "binding_incomplete", f"missing binding fields: {','.join(missing)}"
        )
    return EventSizeBinding(
        census_id=str(header["census_id"]),
        window_start_utc=str(header["window_start_utc"]),
        window_end_utc=str(header["window_end_utc"]),
        code_revision=str(header["code_revision"]),
        writer_gate_protocol=int(header["writer_gate_protocol"]),
        chroma_root_identity=str(header["chroma_root_identity"]),
        writer_gate_identity=str(header["writer_gate_identity"]),
        census_report_sha256=(
            str(header["census_report_sha256"])
            if header.get("census_report_sha256")
            else None
        ),
    )


def validate_binding_against_report(
    binding: EventSizeBinding, report: Mapping[str, Any]
) -> None:
    """Refuse evidence from a different C7 window even if dates coincide."""
    checks = (
        ("census_id", binding.census_id, report.get("census_id")),
        ("window_start_utc", binding.window_start_utc, report.get("window_start_utc")),
        ("window_end_utc", binding.window_end_utc, report.get("window_end_utc")),
        ("code_revision", binding.code_revision, report.get("code_revision")),
        (
            "writer_gate_protocol",
            binding.writer_gate_protocol,
            report.get("writer_gate_protocol"),
        ),
        (
            "chroma_root_identity",
            binding.chroma_root_identity,
            report.get("chroma_root_identity"),
        ),
        (
            "writer_gate_identity",
            binding.writer_gate_identity,
            report.get("writer_gate_identity"),
        ),
    )
    for name, expected, actual in checks:
        if actual != expected:
            raise EventSizeEvidenceRefused(
                "binding_mismatch",
                f"{name} does not match bound C7 window",
            )
    if binding.census_report_sha256 is not None:
        report_hash = sha256_canonical(dict(report))
        if report_hash != binding.census_report_sha256:
            raise EventSizeEvidenceRefused(
                "binding_mismatch", "census report SHA does not match binding"
            )


def open_event_size_companion(
    *,
    census_dir: Path | None,
    session_nonce: str,
    now: datetime | None = None,
) -> EventSizeCompanion | None:
    if census_dir is None or not is_companion_armed(census_dir):
        return None
    directory = _private_dir(census_dir.expanduser(), create=False)
    header = _read_census_header(directory)
    binding = _binding_from_header(header)
    instant = now or datetime.now(timezone.utc)
    start = datetime.strptime(binding.window_start_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    end = datetime.strptime(binding.window_end_utc, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    if instant >= end:
        raise EventSizeEvidenceRefused(
            "census_window_closed", "cannot open companion after window end"
        )
    companion = EventSizeCompanion(
        census_dir=directory,
        binding=binding,
        session_nonce=session_nonce,
        opened_at_utc=_utc_stamp(instant),
    )
    _session_local.companion = companion
    _session_local.in_window = instant >= start
    return companion


def current_session_companion() -> EventSizeCompanion | None:
    return getattr(_session_local, "companion", None)


def session_in_window() -> bool:
    return bool(getattr(_session_local, "in_window", False))


def clear_session_companion() -> None:
    _session_local.companion = None
    _session_local.in_window = False


def finalize_session_companion() -> bool:
    """Finalize companion; return True when C7 close may proceed."""
    companion = current_session_companion()
    if companion is None:
        return True
    try:
        companion.finalize()
    except EventSizeEvidenceRefused:
        return False
    finally:
        clear_session_companion()
    return True


def _persist_summary(census_dir: Path, payload: Mapping[str, Any]) -> None:
    _bump_inertness(evidence_io_ops=1)
    path = census_dir / SUMMARY_NAME
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = -1
    dir_fd = os.open(census_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(SUMMARY_NAME, flags, ARTIFACT_MODE, dir_fd=dir_fd)
        os.fchmod(fd, ARTIFACT_MODE)
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise OSError("short summary write")
            offset += written
        os.fsync(fd)
        os.fsync(dir_fd)
    except FileExistsError as exc:
        raise EventSizeEvidenceRefused(
            "summary_exists", "event-size summary already persisted"
        ) from exc
    except OSError as exc:
        raise EventSizeEvidenceRefused(
            "summary_persist_failed", "cannot persist event-size summary"
        ) from exc
    finally:
        if fd >= 0:
            os.close(fd)
        os.close(dir_fd)


def measure_encoded_size(
    *,
    operation: str,
    document: str | None,
    metadata: Mapping[str, Any] | None,
    deleted: bool,
) -> int:
    """Hermetic size measurement via shared production encoder (no retention)."""
    _bump_inertness(encoder_calls=1)
    event = build_mutation_event(
        event_id="00000000-0000-0000-0000-000000000000",
        sequence=1,
        operation=operation,
        stable_entity_id="bench-estimate",
        document=document,
        metadata=metadata,
        deleted=deleted,
    )
    return len(encode_event_line(event))


# --- Hermetic benchmark harness (test-only entry; not reachable from CLI) ---

BENCHMARK_MODES = frozenset({"control", "unarmed", "armed"})


@dataclass(frozen=True)
class BenchmarkCellResult:
    mode: str
    mutation_class: str
    structural_shape: str
    sample_count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    mean_ms: float
    stddev_ms: float
    throughput_ops_per_s: float
    errors: int


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[index]


def _bench_stats(samples_ms: list[float]) -> dict[str, float]:
    if not samples_ms:
        return {
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "max_ms": 0.0,
            "mean_ms": 0.0,
            "stddev_ms": 0.0,
            "throughput_ops_per_s": 0.0,
        }
    mean = sum(samples_ms) / len(samples_ms)
    variance = sum((x - mean) ** 2 for x in samples_ms) / len(samples_ms)
    total_s = sum(samples_ms) / 1000.0
    return {
        "p50_ms": _percentile(samples_ms, 50),
        "p95_ms": _percentile(samples_ms, 95),
        "p99_ms": _percentile(samples_ms, 99),
        "max_ms": max(samples_ms),
        "mean_ms": mean,
        "stddev_ms": variance**0.5,
        "throughput_ops_per_s": len(samples_ms) / total_s if total_s > 0 else 0.0,
    }


def run_benchmark_cell(
    *,
    mode: str,
    mutation_class: str,
    structural_shape: str,
    operation: Callable[[], None],
    sample_count: int = 1000,
    warmup_count: int = 100,
) -> BenchmarkCellResult:
    if mode not in BENCHMARK_MODES:
        raise EventSizeEvidenceRefused("benchmark_mode_invalid", f"unknown mode {mode}")
    for _ in range(warmup_count):
        operation()
    samples: list[float] = []
    errors = 0
    for _ in range(sample_count):
        start = time.perf_counter()
        try:
            operation()
        except Exception:
            errors += 1
        samples.append((time.perf_counter() - start) * 1000.0)
    stats = _bench_stats(samples)
    return BenchmarkCellResult(
        mode=mode,
        mutation_class=mutation_class,
        structural_shape=structural_shape,
        sample_count=sample_count,
        errors=errors,
        **stats,
    )


