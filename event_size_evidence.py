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
import uuid
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

BENCHMARK_MODES = frozenset({"control", "unarmed", "armed"})
MUTATION_CLASSES = (
    "create",
    "replace",
    "metadata_update",
    "supersede",
    "restore",
    "delete",
)
SESSION_KINDS = ("context_long", "context_short", "manual_long", "manual_short")
BENCHMARK_RUN_COUNT = 3
MODE_ORDERS = (
    ("control", "unarmed", "armed"),
    ("unarmed", "armed", "control"),
    ("armed", "control", "unarmed"),
)
DEFAULT_STEADY_SAMPLES = 1000
DEFAULT_WARMUP_SAMPLES = 100
DEFAULT_H_EVENTS = 50_000
INVENTORY_PATH = Path(__file__).resolve().parent / "docs/plans/SHADOW-WRITER-CENSUS.json"

# Justified matrix: every mutation class and every structural risk shape appears
# at least once; not full Cartesian product.
STRUCTURAL_SHAPE_MATRIX: tuple[tuple[str, str], ...] = (
    ("create", "empty"),
    ("create", "small_1k"),
    ("create", "doc_heavy"),
    ("create", "escape_heavy"),
    ("create", "utf8_multibyte"),
    ("create", "region_64k"),
    ("create", "boundary_131071"),
    ("replace", "small_1k"),
    ("replace", "doc_heavy"),
    ("replace", "meta_heavy"),
    ("replace", "escape_heavy"),
    ("replace", "utf8_multibyte"),
    ("replace", "region_64k"),
    ("replace", "boundary_131071"),
    ("metadata_update", "empty"),
    ("metadata_update", "small_1k"),
    ("metadata_update", "meta_heavy"),
    ("supersede", "small_1k"),
    ("supersede", "meta_heavy"),
    ("restore", "small_1k"),
    ("delete", "small_1k"),
)

_benchmark_runtime = threading.local()


def benchmark_control_bypass_active() -> bool:
    return bool(getattr(_benchmark_runtime, "control_bypass", False))


def benchmark_session_active() -> bool:
    return bool(getattr(_benchmark_runtime, "session_active", False))


@dataclass(frozen=True)
class BenchmarkCellKey:
    mutation_class: str
    structural_shape: str
    session_kind: str


@dataclass(frozen=True)
class BenchmarkCellResult:
    mode: str
    mutation_class: str
    structural_shape: str
    session_kind: str
    run_index: int
    sample_count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    mean_ms: float
    stddev_ms: float
    throughput_ops_per_s: float
    errors: int
    encoder_calls: int
    bytes_processed: int
    evidence_gaps: int
    peak_rss_delta_kb: int
    close_p99_ms: float = 0.0
    close_max_ms: float = 0.0
    close_sample_count: int = 0


@dataclass(frozen=True)
class BenchmarkComparisonMetrics:
    unarmed_vs_control_p99_delta_ms: float
    unarmed_vs_control_p99_factor: float
    unarmed_throughput_loss: float
    armed_vs_unarmed_p99_delta_ms: float
    armed_vs_unarmed_p99_factor: float
    armed_max_delta_ms: float
    short_session_close_p99_ms: float
    short_session_close_max_ms: float
    peak_rss_delta_kb: int


@dataclass(frozen=True)
class HermeticBenchmarkReport:
    verdict: str
    runs: int
    cells: tuple[BenchmarkCellResult, ...]
    comparisons: tuple[BenchmarkComparisonMetrics, ...]
    h_events_memory_exercise: int
    memory_exercise_overflow: int
    memory_exercise_peak_rss_delta_kb: int
    concurrency_level: int
    concurrency_errors: int
    mode_orders: tuple[tuple[str, ...], ...]
    payloads: str = "none"


@dataclass(frozen=True)
class BenchmarkFixture:
    root: Path
    chroma_dir: Path
    config_path: Path
    census_armed_dir: Path
    census_unarmed_dir: Path
    gate_path: Path
    attest_dir: Path


@dataclass(frozen=True)
class SharedGateArena:
    root: Path
    gate_path: Path
    attest_dir: Path
    process_roots: tuple[Path, ...]


@dataclass(frozen=True)
class ConcurrencyOverlapReport:
    concurrency: int
    mode: str
    errors: int
    overlapping_pairs: int
    hold_samples_ms: tuple[float, ...]
    payloads: str = "none"


@dataclass(frozen=True)
class WorkloadSpec:
    mutation_class: str
    structural_shape: str
    unit_id: str
    source_path: str
    document: str | None
    metadata: dict[str, Any]
    embedding: list[float]


def conservative_writer_concurrency_from_inventory(
    inventory_path: Path | None = None,
) -> int:
    """Derive conservative concurrent writers from static writer census binding."""
    path = inventory_path or INVENTORY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EventSizeEvidenceRefused(
            "benchmark_inventory_unreadable", "writer inventory unavailable"
        ) from exc
    units = payload.get("systemd_units") if isinstance(payload, dict) else None
    if not isinstance(units, list):
        raise EventSizeEvidenceRefused(
            "benchmark_inventory_invalid", "writer inventory lacks systemd_units"
        )
    writers = {
        name
        for name in units
        if isinstance(name, str) and ("watch" in name or "refine" in name)
    }
    if len(writers) < 2:
        return 1
    return 2


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


def _peak_rss_kb() -> int:
    import resource

    usage = resource.getrusage(resource.RUSAGE_SELF)
    # Linux reports kilobytes; other platforms may differ — store raw value.
    return int(usage.ru_maxrss)


def _shape_document(shape: str, *, mutation_class: str) -> str | None:
    if mutation_class == "delete":
        return "deleted-document"
    if shape == "empty":
        return ""
    if shape == "small_1k":
        return "x" * 1024
    if shape == "doc_heavy":
        return "d" * 16_384
    if shape == "meta_heavy":
        return "metadata-shape-body"
    if shape == "escape_heavy":
        return 'quote"\\backslash\x01control'
    if shape == "utf8_multibyte":
        return "日本語テスト🔒"
    if shape == "region_64k":
        return "r" * 60_000
    if shape == "boundary_131071":
        from shadow_ledger import maximum_supported_event_bytes

        target = maximum_supported_event_bytes()
        low, high = 0, target * 2
        while low < high:
            mid = (low + high) // 2
            size = measure_encoded_size(
                operation="replace",
                document="b" * mid,
                metadata={},
                deleted=False,
            )
            if size < target:
                low = mid + 1
            else:
                high = mid
        return "b" * low
    raise EventSizeEvidenceRefused("benchmark_shape_invalid", f"unknown shape {shape}")


def _shape_metadata(shape: str, *, unit_id: str, source_path: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": unit_id,
        "source_path": source_path,
        "kind": "benchmark",
    }
    if shape == "meta_heavy":
        base.update({f"meta_{i}": "m" * 256 for i in range(32)})
    if shape == "empty":
        base = {"id": unit_id, "source_path": source_path, "kind": "benchmark"}
    return base


def build_workload_spec(
    *, mutation_class: str, structural_shape: str, seed: int
) -> WorkloadSpec:
    unit_id = f"bench-{mutation_class}-{structural_shape}-{seed}"
    source_path = f"/bench/source/{seed}"
    document = _shape_document(structural_shape, mutation_class=mutation_class)
    metadata = _shape_metadata(
        structural_shape, unit_id=unit_id, source_path=source_path
    )
    embedding = [0.01 * (i % 8) for i in range(8)]
    return WorkloadSpec(
        mutation_class=mutation_class,
        structural_shape=structural_shape,
        unit_id=unit_id,
        source_path=source_path,
        document=document,
        metadata=metadata,
        embedding=embedding,
    )


def _write_benchmark_config(config_path: Path, chroma_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "[index]\n" + f'chroma_dir = {json.dumps(str(chroma_dir))}\n',
        encoding="utf-8",
    )


def _arm_census_header(census_dir: Path, *, armed: bool, chroma_dir: Path, gate_path: Path) -> None:
    from datetime import timedelta
    from writer_census import HEADER_NAME, _create_events, _write_new_json

    from chroma_write_store import WRITER_GATE_PROTOCOL_VERSION, current_code_revision

    directory = _private_dir(census_dir, create=True)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=1)
    end = now + timedelta(days=7)
    header = {
        "schema_version": 1,
        "census_id": f"bench-{uuid.uuid4().hex}",
        "created_at_utc": _utc_stamp(now),
        "window_start_utc": _utc_stamp(start),
        "window_end_utc": _utc_stamp(end),
        "code_revision": current_code_revision(),
        "writer_gate_protocol": WRITER_GATE_PROTOCOL_VERSION,
        "chroma_root_identity": hashlib.sha256(str(chroma_dir.resolve()).encode()).hexdigest(),
        "writer_gate_identity": hashlib.sha256(str(gate_path.resolve()).encode()).hexdigest(),
        "event_size_evidence_armed": bool(armed),
    }
    if (directory / HEADER_NAME).exists():
        (directory / HEADER_NAME).unlink()
    if (directory / "session-events.jsonl").exists():
        (directory / "session-events.jsonl").unlink()
    _write_new_json(directory, HEADER_NAME, header)
    _create_events(directory)


def _session_kind_is_long(session_kind: str) -> bool:
    return session_kind.endswith("_long")


def _session_kind_is_short(session_kind: str) -> bool:
    return session_kind.endswith("_short")


def create_benchmark_fixture(
    root: Path,
    *,
    gate_path: Path | None = None,
    attest_dir: Path | None = None,
) -> BenchmarkFixture:
    chroma_dir = root / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    config_path = root / "config.toml"
    _write_benchmark_config(config_path, chroma_dir)
    resolved_gate = gate_path or (root / "gate.lock")
    resolved_attest = attest_dir or (root / "attest")
    resolved_attest.mkdir(parents=True, exist_ok=True)
    census_armed = root / "census-armed"
    census_unarmed = root / "census-unarmed"
    _arm_census_header(
        census_armed, armed=True, chroma_dir=chroma_dir, gate_path=resolved_gate
    )
    _arm_census_header(
        census_unarmed, armed=False, chroma_dir=chroma_dir, gate_path=resolved_gate
    )
    return BenchmarkFixture(
        root=root,
        chroma_dir=chroma_dir,
        config_path=config_path,
        census_armed_dir=census_armed,
        census_unarmed_dir=census_unarmed,
        gate_path=resolved_gate,
        attest_dir=resolved_attest,
    )


def create_shared_gate_arena(root: Path, *, concurrency: int) -> SharedGateArena:
    shared = root / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    gate_path = shared / "gate.lock"
    attest_dir = shared / "attest"
    attest_dir.mkdir(parents=True, exist_ok=True)
    process_roots: list[Path] = []
    for index in range(concurrency):
        proc_root = root / f"proc-{index}"
        proc_root.mkdir(parents=True, exist_ok=True)
        create_benchmark_fixture(
            proc_root, gate_path=gate_path, attest_dir=attest_dir
        )
        process_roots.append(proc_root)
    return SharedGateArena(
        root=root,
        gate_path=gate_path,
        attest_dir=attest_dir,
        process_roots=tuple(process_roots),
    )


def initialize_equivalent_workload_state(
    fixture: BenchmarkFixture, spec: WorkloadSpec
) -> None:
    """Establish identical disposable Chroma state before a comparison cell."""
    if spec.mutation_class == "create":
        return
    seed_spec = WorkloadSpec(
        mutation_class=spec.mutation_class,
        structural_shape=spec.structural_shape,
        unit_id=spec.unit_id,
        source_path=spec.source_path,
        document=spec.document,
        metadata=dict(spec.metadata),
        embedding=list(spec.embedding),
    )

    def _seed(store: Any) -> None:
        _prepare_entity(store, seed_spec)

    _with_production_session(
        fixture,
        mode="unarmed",
        session_kind="context_short",
        mutate=_seed,
    )


def create_mode_fixture_group(
    root: Path,
    *,
    mutation_class: str,
    structural_shape: str,
    run_index: int,
    cell_tag: str,
    gate_path: Path | None = None,
    attest_dir: Path | None = None,
) -> dict[str, BenchmarkFixture]:
    """Fresh equivalently initialized fixture per mode (no cross-mode state)."""
    spec = build_workload_spec(
        mutation_class=mutation_class,
        structural_shape=structural_shape,
        seed=run_index,
    )
    fixtures: dict[str, BenchmarkFixture] = {}
    for mode in ("control", "unarmed", "armed"):
        fx = create_benchmark_fixture(
            root / f"run-{run_index}-{cell_tag}-{mode}",
            gate_path=gate_path,
            attest_dir=attest_dir,
        )
        initialize_equivalent_workload_state(fx, spec)
        fixtures[mode] = fx
    return fixtures


def _census_dir_for_mode(fixture: BenchmarkFixture, mode: str) -> Path | None:
    if mode == "unarmed":
        return fixture.census_unarmed_dir
    if mode in {"control", "armed"}:
        return fixture.census_armed_dir
    raise EventSizeEvidenceRefused("benchmark_mode_invalid", mode)


def _with_production_session(
    fixture: BenchmarkFixture,
    *,
    mode: str,
    session_kind: str,
    mutate: Callable[[Any], None],
) -> tuple[float, float]:
    """Run one session block; return (mutation_ms, close_persistence_ms)."""
    from chroma_write_store import (
        open_production_write_store,
        production_chroma_write_session,
    )

    census_dir = _census_dir_for_mode(fixture, mode)
    ctx: Any = benchmark_control_bypass() if mode == "control" else _null_context()
    close_ms = 0.0
    with ctx:
        if session_kind in {"context_short", "context_long"}:
            if _session_kind_is_short(session_kind):
                mut_start = time.perf_counter()
                with production_chroma_write_session(
                    fixture.config_path,
                    lock_path=fixture.gate_path,
                    attest_dir=fixture.attest_dir,
                    census_dir=census_dir,
                    entrypoint="production.writer",
                ) as session:
                    mutate(session.store)
                    mutation_ms = (time.perf_counter() - mut_start) * 1000.0
                    close_start = time.perf_counter()
                close_ms = (time.perf_counter() - close_start) * 1000.0
                return mutation_ms, close_ms
            mut_start = time.perf_counter()
            with production_chroma_write_session(
                fixture.config_path,
                lock_path=fixture.gate_path,
                attest_dir=fixture.attest_dir,
                census_dir=census_dir,
                entrypoint="production.writer",
            ) as session:
                mutate(session.store)
            mutation_ms = (time.perf_counter() - mut_start) * 1000.0
            return mutation_ms, 0.0
        if session_kind in {"manual_short", "manual_long"}:
            session = open_production_write_store(
                fixture.config_path,
                lock_path=fixture.gate_path,
                attest_dir=fixture.attest_dir,
                census_dir=census_dir,
                entrypoint="production.writer",
            )
            mut_start = time.perf_counter()
            try:
                mutate(session.store)
            finally:
                mutation_ms = (time.perf_counter() - mut_start) * 1000.0
                if _session_kind_is_short(session_kind):
                    close_start = time.perf_counter()
                    session.store.close()
                    close_ms = (time.perf_counter() - close_start) * 1000.0
                    return mutation_ms, close_ms
                session.store.close()
            return mutation_ms, 0.0
    raise EventSizeEvidenceRefused("benchmark_session_invalid", session_kind)


def _prepare_entity(store: Any, spec: WorkloadSpec) -> None:
    existing = store.get_unit(spec.unit_id)
    if spec.mutation_class == "create":
        if existing is None:
            store.add_unit(
                spec.unit_id,
                spec.document or "",
                spec.embedding,
                spec.metadata,
            )
        return
    if existing is None:
        store.add_unit(
            spec.unit_id,
            spec.document or "seed",
            spec.embedding,
            dict(spec.metadata),
        )
        existing = store.get_unit(spec.unit_id)
    if spec.mutation_class == "supersede":
        if not ((existing or {}).get("metadata") or {}).get("superseded"):
            store.supersede_units_for_source(
                spec.source_path,
                superseded_by="bench",
                candidate_ids={spec.unit_id},
            )
    if spec.mutation_class == "restore":
        meta = dict((existing or {}).get("metadata") or spec.metadata)
        meta["superseded"] = True
        meta["superseded_by"] = "bench"
        store.update_unit_metadata(spec.unit_id, meta)


def _execute_mutation(store: Any, spec: WorkloadSpec) -> int:
    before = inertness_snapshot()
    if spec.mutation_class == "create":
        if store.get_unit(spec.unit_id) is None:
            store.add_unit(
                spec.unit_id,
                spec.document or "",
                spec.embedding,
                spec.metadata,
            )
    elif spec.mutation_class == "replace":
        _prepare_entity(store, spec)
        store.update_unit(
            spec.unit_id,
            spec.document or "replaced",
            spec.embedding,
            dict(spec.metadata),
        )
    elif spec.mutation_class == "metadata_update":
        _prepare_entity(store, spec)
        meta = dict(spec.metadata)
        meta["bench_tag"] = "updated"
        store.update_unit_metadata(spec.unit_id, meta)
    elif spec.mutation_class == "supersede":
        _prepare_entity(store, spec)
        store.supersede_units_for_source(
            spec.source_path,
            superseded_by="bench",
            candidate_ids={spec.unit_id},
        )
    elif spec.mutation_class == "restore":
        _prepare_entity(store, spec)
        meta = dict((store.get_unit(spec.unit_id) or {}).get("metadata") or spec.metadata)
        meta.pop("superseded", None)
        meta.pop("superseded_by", None)
        store.update_unit_metadata(spec.unit_id, meta)
    elif spec.mutation_class == "delete":
        _prepare_entity(store, spec)
        store.delete_units_for_source(
            spec.source_path,
            candidate_ids={spec.unit_id},
        )
    else:
        raise EventSizeEvidenceRefused(
            "benchmark_mutation_invalid", spec.mutation_class
        )
    after = inertness_snapshot()
    gaps = after["retained_observations"] - before["retained_observations"]
    return max(0, gaps)


def _production_mutation_once(
    fixture: BenchmarkFixture,
    *,
    mode: str,
    spec: WorkloadSpec,
    session_kind: str,
) -> tuple[float, float]:
    return _with_production_session(
        fixture,
        mode=mode,
        session_kind=session_kind,
        mutate=lambda store: _execute_mutation(store, spec),
    )


class _null_context:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *args: object) -> None:
        return None


class benchmark_control_bypass:
    """Hermetic/test-only companion bypass; only valid during benchmark sessions."""

    def __enter__(self) -> None:
        if not benchmark_session_active():
            raise EventSizeEvidenceRefused(
                "benchmark_control_bypass_forbidden",
                "control bypass is unreachable outside benchmark harness",
            )
        _benchmark_runtime.control_bypass = True

    def __exit__(self, *args: object) -> None:
        _benchmark_runtime.control_bypass = False


def _run_mode_samples(
    fixture: BenchmarkFixture,
    *,
    mode: str,
    spec: WorkloadSpec,
    session_kind: str,
    sample_count: int,
    warmup_count: int,
) -> BenchmarkCellResult:
    ctx: Any = (
        benchmark_control_bypass() if mode == "control" else _null_context()
    )
    samples: list[float] = []
    close_samples: list[float] = []
    errors = 0
    encoder_delta = 0
    gaps = 0
    rss_before = _peak_rss_kb()

    def _timed_mutation(store: Any, workload: WorkloadSpec) -> None:
        nonlocal encoder_delta, gaps
        enc_before = inertness_snapshot()["encoder_calls"]
        gap_before = inertness_snapshot()["retained_observations"]
        _execute_mutation(store, workload)
        enc_after = inertness_snapshot()["encoder_calls"]
        gap_after = inertness_snapshot()["retained_observations"]
        encoder_delta += max(0, enc_after - enc_before)
        gaps += max(0, gap_after - gap_before)

    if _session_kind_is_long(session_kind):
        from chroma_write_store import (
            open_production_write_store,
            production_chroma_write_session,
        )

        census_dir = _census_dir_for_mode(fixture, mode)
        with ctx:
            if session_kind == "context_long":
                with production_chroma_write_session(
                    fixture.config_path,
                    lock_path=fixture.gate_path,
                    attest_dir=fixture.attest_dir,
                    census_dir=census_dir,
                    entrypoint="production.writer",
                ) as session:
                    for i in range(warmup_count):
                        warm_spec = build_workload_spec(
                            mutation_class=spec.mutation_class,
                            structural_shape=spec.structural_shape,
                            seed=10_000 + i,
                        )
                        _timed_mutation(session.store, warm_spec)
                    for i in range(sample_count):
                        sample_spec = build_workload_spec(
                            mutation_class=spec.mutation_class,
                            structural_shape=spec.structural_shape,
                            seed=20_000 + i,
                        )
                        start = time.perf_counter()
                        try:
                            _timed_mutation(session.store, sample_spec)
                        except Exception:
                            errors += 1
                        samples.append((time.perf_counter() - start) * 1000.0)
            else:
                session = open_production_write_store(
                    fixture.config_path,
                    lock_path=fixture.gate_path,
                    attest_dir=fixture.attest_dir,
                    census_dir=census_dir,
                    entrypoint="production.writer",
                )
                try:
                    for i in range(warmup_count):
                        warm_spec = build_workload_spec(
                            mutation_class=spec.mutation_class,
                            structural_shape=spec.structural_shape,
                            seed=10_000 + i,
                        )
                        _timed_mutation(session.store, warm_spec)
                    for i in range(sample_count):
                        sample_spec = build_workload_spec(
                            mutation_class=spec.mutation_class,
                            structural_shape=spec.structural_shape,
                            seed=20_000 + i,
                        )
                        start = time.perf_counter()
                        try:
                            _timed_mutation(session.store, sample_spec)
                        except Exception:
                            errors += 1
                        samples.append((time.perf_counter() - start) * 1000.0)
                finally:
                    session.store.close()
    else:
        with ctx:
            for i in range(warmup_count):
                warm_spec = build_workload_spec(
                    mutation_class=spec.mutation_class,
                    structural_shape=spec.structural_shape,
                    seed=10_000 + i,
                )
                _with_production_session(
                    fixture,
                    mode=mode,
                    session_kind=session_kind,
                    mutate=lambda store, ws=warm_spec: _timed_mutation(store, ws),
                )
            for i in range(sample_count):
                sample_spec = build_workload_spec(
                    mutation_class=spec.mutation_class,
                    structural_shape=spec.structural_shape,
                    seed=20_000 + i,
                )
                try:
                    mutation_ms, close_ms = _with_production_session(
                        fixture,
                        mode=mode,
                        session_kind=session_kind,
                        mutate=lambda store, ws=sample_spec: _timed_mutation(store, ws),
                    )
                    samples.append(mutation_ms)
                    close_samples.append(close_ms)
                except Exception:
                    errors += 1

    bytes_total = measure_encoded_size(
        operation=spec.mutation_class,
        document=spec.document,
        metadata=spec.metadata,
        deleted=spec.mutation_class == "delete",
    ) * max(1, sample_count)
    stats = _bench_stats(samples)
    close_stats = _bench_stats(close_samples) if close_samples else {
        "p99_ms": 0.0,
        "max_ms": 0.0,
    }
    return BenchmarkCellResult(
        mode=mode,
        mutation_class=spec.mutation_class,
        structural_shape=spec.structural_shape,
        session_kind=session_kind,
        run_index=-1,
        sample_count=sample_count,
        errors=errors,
        encoder_calls=encoder_delta,
        bytes_processed=bytes_total,
        evidence_gaps=gaps,
        peak_rss_delta_kb=max(0, _peak_rss_kb() - rss_before),
        close_p99_ms=close_stats["p99_ms"],
        close_max_ms=close_stats["max_ms"],
        close_sample_count=len(close_samples),
        **stats,
    )


def _compare_modes(
    control: BenchmarkCellResult,
    unarmed: BenchmarkCellResult,
    armed: BenchmarkCellResult,
) -> BenchmarkComparisonMetrics:
    def factor(base: float, other: float) -> float:
        if base <= 0:
            return 0.0
        return other / base

    throughput_loss = 0.0
    if control.throughput_ops_per_s > 0:
        throughput_loss = 1.0 - (
            unarmed.throughput_ops_per_s / control.throughput_ops_per_s
        )
    close_p99 = max(unarmed.close_p99_ms, armed.close_p99_ms)
    close_max = max(unarmed.close_max_ms, armed.close_max_ms)
    return BenchmarkComparisonMetrics(
        unarmed_vs_control_p99_delta_ms=unarmed.p99_ms - control.p99_ms,
        unarmed_vs_control_p99_factor=factor(control.p99_ms, unarmed.p99_ms),
        unarmed_throughput_loss=throughput_loss,
        armed_vs_unarmed_p99_delta_ms=armed.p99_ms - unarmed.p99_ms,
        armed_vs_unarmed_p99_factor=factor(unarmed.p99_ms, armed.p99_ms),
        armed_max_delta_ms=armed.max_ms - unarmed.max_ms,
        short_session_close_p99_ms=close_p99,
        short_session_close_max_ms=close_max,
        peak_rss_delta_kb=max(
            control.peak_rss_delta_kb,
            unarmed.peak_rss_delta_kb,
            armed.peak_rss_delta_kb,
        ),
    )


def run_memory_exercise(
    fixture: BenchmarkFixture,
    *,
    h_events: int = DEFAULT_H_EVENTS,
) -> tuple[int, int, int]:
    """Armed long session through actual companion lifecycle."""
    from chroma_write_store import production_chroma_write_session

    rss_before = _peak_rss_kb()
    with production_chroma_write_session(
        fixture.config_path,
        lock_path=fixture.gate_path,
        attest_dir=fixture.attest_dir,
        census_dir=fixture.census_armed_dir,
        entrypoint="production.writer",
    ) as session:
        companion = current_session_companion()
        if companion is None:
            raise EventSizeEvidenceRefused(
                "benchmark_companion_missing",
                "armed memory exercise requires companion",
            )
        for i in range(h_events):
            sample_spec = build_workload_spec(
                mutation_class="replace",
                structural_shape="small_1k",
                seed=30_000 + i,
            )
            _execute_mutation(session.store, sample_spec)
        overflow = companion.histogram.overflow
        retained = companion.histogram.total_observations
    if retained > MAX_RETAINED_OBSERVATIONS:
        raise EventSizeEvidenceRefused(
            "benchmark_unbounded_memory", "companion retained observations exceeded cap"
        )
    return overflow, retained, max(0, _peak_rss_kb() - rss_before)


_mp_barrier: Any = None


def _init_shared_gate_worker(barrier: Any) -> None:
    global _mp_barrier
    _mp_barrier = barrier


def _shared_gate_worker_entry(
    barrier: Any, payload: dict[str, str], out_queue: Any
) -> None:
    _init_shared_gate_worker(barrier)
    _shared_gate_worker(payload, out_queue)


def _shared_gate_worker(payload: dict[str, str], out_queue: Any) -> None:
    import chromadb  # noqa: F401

    global _mp_barrier
    _benchmark_runtime.session_active = True
    proc_root = Path(payload["proc_root"])
    fixture = create_benchmark_fixture(
        proc_root,
        gate_path=Path(payload["gate_path"]),
        attest_dir=Path(payload["attest_dir"]),
    )
    spec = build_workload_spec(
        mutation_class="create",
        structural_shape="small_1k",
        seed=int(payload["seed"]),
    )
    hold_ms = float(payload["hold_ms"])
    error = None
    acquired_at = 0.0
    released_at = 0.0
    try:
        if _mp_barrier is not None:
            _mp_barrier.wait()
        from chroma_write_store import production_chroma_write_session

        census_dir = _census_dir_for_mode(fixture, payload["mode"])
        ctx: Any = (
            benchmark_control_bypass()
            if payload["mode"] == "control"
            else _null_context()
        )
        with ctx:
            with production_chroma_write_session(
                fixture.config_path,
                lock_path=fixture.gate_path,
                attest_dir=fixture.attest_dir,
                census_dir=census_dir,
                entrypoint="production.writer",
            ) as session:
                acquired_at = time.monotonic()
                _execute_mutation(session.store, spec)
                time.sleep(hold_ms / 1000.0)
                released_at = time.monotonic()
    except Exception as exc:  # pragma: no cover - reported via queue
        error = type(exc).__name__
    out_queue.put(
        {
            "error": error,
            "acquired_at": acquired_at,
            "released_at": released_at,
            "gate_path": str(fixture.gate_path.resolve()),
        }
    )


def _intervals_overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> bool:
    return a_start < b_end and b_start < a_end


def run_multiprocess_concurrency_cell(
    arena: SharedGateArena,
    *,
    concurrency: int,
    mode: str = "unarmed",
    hold_ms: float = 200.0,
) -> ConcurrencyOverlapReport:
    import multiprocessing

    if concurrency < 1:
        raise EventSizeEvidenceRefused(
            "benchmark_concurrency_invalid", "concurrency must be positive"
        )
    if concurrency > len(arena.process_roots):
        raise EventSizeEvidenceRefused(
            "benchmark_concurrency_invalid", "arena lacks process roots"
        )
    ctx = multiprocessing.get_context("spawn")
    out: Any = ctx.Queue()
    barrier = ctx.Barrier(concurrency) if concurrency > 1 else None
    processes = []
    for index in range(concurrency):
        payload = {
            "proc_root": str(arena.process_roots[index]),
            "gate_path": str(arena.gate_path.resolve()),
            "attest_dir": str(arena.attest_dir.resolve()),
            "seed": str(50_000 + index),
            "mode": mode,
            "hold_ms": str(hold_ms),
        }
        if barrier is not None:
            proc = ctx.Process(
                target=_shared_gate_worker_entry,
                args=(barrier, payload, out),
            )
        else:
            proc = ctx.Process(target=_shared_gate_worker, args=(payload, out))
        proc.start()
        processes.append(proc)
    results: list[dict[str, Any]] = []
    for _ in processes:
        results.append(out.get(timeout=180))
    for proc in processes:
        proc.join(timeout=60)
    gate_identity = str(arena.gate_path.resolve())
    if not all(item.get("gate_path") == gate_identity for item in results):
        raise EventSizeEvidenceRefused(
            "benchmark_gate_mismatch", "worker did not use shared gate path"
        )
    errors = sum(1 for item in results if item.get("error"))
    intervals = [
        (float(item["acquired_at"]), float(item["released_at"]))
        for item in results
        if item.get("acquired_at") and item.get("released_at")
    ]
    overlapping = 0
    for left in range(len(intervals)):
        for right in range(left + 1, len(intervals)):
            a0, a1 = intervals[left]
            b0, b1 = intervals[right]
            if _intervals_overlap(a0, a1, b0, b1):
                overlapping += 1
    hold_samples = tuple(
        max(0.0, (float(item["released_at"]) - float(item["acquired_at"])) * 1000.0)
        for item in results
        if item.get("acquired_at") and item.get("released_at")
    )
    if concurrency > 1 and overlapping == 0 and errors == 0:
        raise EventSizeEvidenceRefused(
            "benchmark_no_contention", "shared gate showed no overlapping holds"
        )
    return ConcurrencyOverlapReport(
        concurrency=concurrency,
        mode=mode,
        errors=errors,
        overlapping_pairs=overlapping,
        hold_samples_ms=hold_samples,
    )


def run_hermetic_overhead_benchmark(
    *,
    root: Path,
    steady_samples: int = DEFAULT_STEADY_SAMPLES,
    warmup_samples: int = DEFAULT_WARMUP_SAMPLES,
    h_events: int = DEFAULT_H_EVENTS,
    inventory_path: Path | None = None,
    matrix: tuple[tuple[str, str], ...] | None = None,
    session_kinds: tuple[str, ...] | None = None,
    run_count: int = BENCHMARK_RUN_COUNT,
) -> HermeticBenchmarkReport:
    """Execute three independent counterbalanced runs; verdict is MEASURED only."""
    try:
        import chromadb  # noqa: F401
    except ImportError as exc:
        raise EventSizeEvidenceRefused(
            "benchmark_chroma_missing", "chromadb required"
        ) from exc

    _benchmark_runtime.session_active = True
    try:
        concurrency = conservative_writer_concurrency_from_inventory(inventory_path)
        all_cells: list[BenchmarkCellResult] = []
        comparisons: list[BenchmarkComparisonMetrics] = []
        shape_matrix = matrix or STRUCTURAL_SHAPE_MATRIX
        kinds = session_kinds or SESSION_KINDS
        for run_index in range(run_count):
            mode_order = MODE_ORDERS[run_index % len(MODE_ORDERS)]
            for cell_index, (mutation_class, structural_shape) in enumerate(
                shape_matrix
            ):
                cell_tag = f"{cell_index}-{mutation_class}-{structural_shape}"
                mode_fixtures = create_mode_fixture_group(
                    root,
                    mutation_class=mutation_class,
                    structural_shape=structural_shape,
                    run_index=run_index,
                    cell_tag=cell_tag,
                )
                for session_kind in kinds:
                    spec = build_workload_spec(
                        mutation_class=mutation_class,
                        structural_shape=structural_shape,
                        seed=run_index,
                    )
                    mode_results: dict[str, BenchmarkCellResult] = {}
                    for mode in mode_order:
                        result = _run_mode_samples(
                            mode_fixtures[mode],
                            mode=mode,
                            spec=spec,
                            session_kind=session_kind,
                            sample_count=steady_samples,
                            warmup_count=warmup_samples,
                        )
                        mode_results[mode] = BenchmarkCellResult(
                            **{**result.__dict__, "run_index": run_index}
                        )
                    comparisons.append(
                        _compare_modes(
                            mode_results["control"],
                            mode_results["unarmed"],
                            mode_results["armed"],
                        )
                    )
                    all_cells.extend(mode_results.values())
        mem_fixture = create_benchmark_fixture(root / "memory")
        overflow, _retained, mem_rss = run_memory_exercise(mem_fixture, h_events=h_events)
        arena = create_shared_gate_arena(root / "concurrency", concurrency=concurrency)
        mp_unarmed = run_multiprocess_concurrency_cell(
            arena, concurrency=concurrency, mode="unarmed"
        )
        mp_errors = mp_unarmed.errors
        if concurrency > 1:
            arena_armed = create_shared_gate_arena(
                root / "concurrency-armed", concurrency=concurrency
            )
            mp_armed = run_multiprocess_concurrency_cell(
                arena_armed, concurrency=concurrency, mode="armed"
            )
            mp_errors += mp_armed.errors
        return HermeticBenchmarkReport(
            verdict="MEASURED",
            runs=run_count,
            cells=tuple(all_cells),
            comparisons=tuple(comparisons),
            h_events_memory_exercise=h_events,
            memory_exercise_overflow=overflow,
            memory_exercise_peak_rss_delta_kb=mem_rss,
            concurrency_level=concurrency,
            concurrency_errors=mp_errors,
            mode_orders=MODE_ORDERS,
        )
    finally:
        _benchmark_runtime.session_active = False
        _benchmark_runtime.control_bypass = False


def run_benchmark_cell(
    *,
    mode: str,
    mutation_class: str,
    structural_shape: str,
    operation: Callable[[], None],
    sample_count: int = 1000,
    warmup_count: int = 100,
) -> BenchmarkCellResult:
    """Low-level timing helper for hermetic micro-benchmarks."""
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
        session_kind="micro",
        run_index=0,
        sample_count=sample_count,
        errors=errors,
        encoder_calls=0,
        bytes_processed=0,
        evidence_gaps=0,
        peak_rss_delta_kb=0,
        close_p99_ms=0.0,
        close_max_ms=0.0,
        close_sample_count=0,
        **stats,
    )

