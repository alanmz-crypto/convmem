"""Default-off production coordinator for incremental Kiro JSONL ingest.

Production code must not import ``scratch_jsonl_prototype``. This module lifts
the reviewed prefix/continuity/frontier/replay rules and adds a prepared-output
cache plus source-scoped Chroma before-image rollback.
"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-locals
# pylint: disable=too-many-branches,too-many-statements,too-many-lines,duplicate-code

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from adapters.detect import detect_format, get_parser
from adapters.jsonl_prefix import (
    RawLineOutcome,
    complete_line_outcomes_cover_prefix,
    serialize_raw_line_coverage,
)
from chroma_store import SUMMARIES, UNITS
from incremental_jsonl_formats import (
    IncrementalFormatSpec,
    KIRO_ROUTE_FORMATS,
    get_format_spec,
    routed_formats,
    source_state_id as format_source_state_id,
)
from config import IncrementalJsonlConfigError, incremental_jsonl_settings, load_config
from incremental_jsonl_isolation import (
    IsolationBoundary,
    IsolationViolation,
    SourceAdvisoryLock,
    SourceCaptureError,
    open_source_readonly,
    validate_regular_source,
)
from incremental_jsonl_production import ProductionBoundary
from ingest import (
    ChunkArtifact,
    build_chunk_artifact,
    chunk_messages,
    load_processed,
    render_chunk,
)

ELIGIBLE_FORMAT = "jsonl_kiro_session"
ADAPTER_CONTRACT_VERSION = "kiro-complete-prefix-v1"
CHECKPOINT_VERSION = 1
TRANSACTION_VERSION = 1
PREPARED_VERSION = 1
ROLLBACK_VERSION = 2
DEDUPE_FILENAMES = ("dedupe_queue.jsonl", "ingest_duplicate_suppressions.jsonl")
CONTINUITY_REASONS = (
    "initial_full",
    "source_identity_changed",
    "transform_fingerprint_changed",
    "source_replaced_or_rotated",
    "source_truncated",
    "validated_prefix_mutated",
)
DURABLE_TRANSITIONS = (
    "source_snapshot_prepare",
    "source_snapshot_publish",
    "source_revalidate",
    "transaction_prepare",
    "transaction_phase_publish",
    "prepared_output_prepare",
    "prepared_output_publish",
    "rollback_prepare",
    "rollback_publish",
    "summary_upsert",
    "unit_upsert",
    "summaries_prune",
    "units_prune",
    "checkpoint_prepare",
    "checkpoint_publish",
    "export_reconcile",
    "dedupe_reconcile",
    "processed_publish",
    "transaction_cleanup",
    "snapshot_cleanup",
    "lock_acquire",
    "lock_release",
)
REQUIRED_CHECKPOINT_FIELDS = (
    "version",
    "commit_state",
    "adapter_format",
    "source_identity",
    "source_path",
    "generation_identity",
    "complete_boundary",
    "prefix_sha256",
    "transform_fingerprint",
    "record_count",
    "chunk_frontier",
    "active_generation",
    "summary_ids",
    "unit_ids",
    "processed_hash",
    "raw_line_coverage",
)

FaultHook = Callable[[str], None]


class IncrementalJsonlError(RuntimeError):
    """Stable recovery/refusal code for the incremental route."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass
class CallCounters:
    summarize: int = 0
    distill: int = 0
    summary_embed: int = 0
    unit_embed: int = 0
    summarize_success: int = 0
    distill_success: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            name: value
            for name, value in asdict(self).items()
            if name not in {"summarize_success", "distill_success"}
        }

    @property
    def total(self) -> int:
        return self.summarize + self.distill + self.summary_embed + self.unit_embed


@dataclass
class IncrementalRunResult:
    outcome: str
    mode: str
    fallback_reason: str | None
    adapter_format: str
    selected_boundary: int
    records: int
    frontier_record: int
    counters: CallCounters
    reused_artifacts: int
    max_units_in_flight: int
    active_generation: str
    chunks: int = 0
    units: int = 0
    exact_suppressed: int = 0
    semantic_queued: int = 0
    ingest_status: str = "skipped"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["counters"] = self.counters.as_dict()
        return payload

    def ingest_tuple(self) -> tuple[str, int, int, int, int]:
        return (
            self.ingest_status,
            self.chunks,
            self.units,
            self.exact_suppressed,
            self.semantic_queued,
        )


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            fd = -1
    finally:
        if fd >= 0:
            os.close(fd)
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def source_state_id(canonical_path: str, *, format_id: str = ELIGIBLE_FORMAT) -> str:
    return format_source_state_id(format_id, canonical_path)


def frontier_start(prior_count: int, chunk_size: int, overlap: int) -> int:
    if prior_count <= 0:
        return 0
    chunks = chunk_messages([{}] * prior_count, chunk_size, overlap)
    if not chunks:
        return 0
    return int(chunks[-1]["start_offset"])


def compute_transform_fingerprint(
    *,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    models: dict,
    embed_dimension: int,
    implementation_revision: str,
    adapter_format: str = ELIGIBLE_FORMAT,
    adapter_contract_version: str = ADAPTER_CONTRACT_VERSION,
) -> str:
    payload = {
        "adapter_format": adapter_format,
        "adapter_contract_version": adapter_contract_version,
        "chunk_size": chunk_size,
        "overlap": overlap,
        "rendering_limits": {"summary_max_chars": 8000, "distill_max_chars": 8000},
        "message_selection": "chunk_messages",
        "summary_prompt_version": "locked-summarize-prompt-v1",
        "distill_prompt_version": "locked-distill-prompt-v1",
        "summary_temperature": 0.2,
        "distill_temperature": 0.2,
        "summarize_model": models.get("summarize_model"),
        "distill_model": models.get("distill_model"),
        "embed_model": models.get("embed_model"),
        "embed_dimension": embed_dimension,
        "normalization_contract": "normalize_unit-v1",
        "confidence_threshold": min_confidence,
        "provenance_envelope": "build_ingest_envelope-v1",
        "id_contract": "make_unit_id-v1",
        "dedupe_contract": "ingest_dedupe-v1",
        "implementation_revision": implementation_revision,
    }
    return _sha(_canonical_json(payload))


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _validate_raw_line_coverage(
    coverage: dict,
    *,
    complete_boundary: int,
    prefix_sha256: str,
) -> None:
    if coverage.get("prefix_sha256") != prefix_sha256:
        raise IncrementalJsonlError("invalid_state", "coverage prefix mismatch")
    outcomes_raw = coverage.get("outcomes")
    if not isinstance(outcomes_raw, list):
        raise IncrementalJsonlError("invalid_state", "coverage outcomes invalid")
    try:
        outcomes = [
            RawLineOutcome(
                start=int(item["start"]),
                end=int(item["end"]),
                outcome=str(item["outcome"]),
                message_index=item.get("message_index"),
            )
            for item in outcomes_raw
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise IncrementalJsonlError(
            "invalid_state", "coverage outcomes malformed"
        ) from exc
    if not complete_line_outcomes_cover_prefix(outcomes, int(complete_boundary)):
        raise IncrementalJsonlError("invalid_state", "coverage outcomes incomplete")
    recomputed = serialize_raw_line_coverage(outcomes, prefix_sha256)
    if coverage.get("coverage_digest") != recomputed["coverage_digest"]:
        raise IncrementalJsonlError("invalid_state", "coverage digest mismatch")
    if outcomes_raw != recomputed["outcomes"]:
        raise IncrementalJsonlError("invalid_state", "coverage outcomes tampered")


def validate_checkpoint(
    payload: dict,
    *,
    source_path: str | None = None,
    adapter_format: str | None = None,
) -> dict:
    if not isinstance(payload, dict):
        raise IncrementalJsonlError("invalid_state", "checkpoint is not an object")
    if payload.get("version") != CHECKPOINT_VERSION:
        raise IncrementalJsonlError("invalid_state", "unsupported checkpoint version")
    missing = [name for name in REQUIRED_CHECKPOINT_FIELDS if name not in payload]
    if missing:
        raise IncrementalJsonlError("invalid_state", f"checkpoint missing {missing}")
    expected_format = adapter_format or ELIGIBLE_FORMAT
    if payload.get("adapter_format") != expected_format:
        raise IncrementalJsonlError("invalid_state", "checkpoint adapter mismatch")
    if source_path is not None and payload.get("source_path") != source_path:
        raise IncrementalJsonlError("invalid_state", "cross-source checkpoint")
    summaries = payload.get("summary_ids")
    units = payload.get("unit_ids")
    if not isinstance(summaries, list) or not isinstance(units, list):
        raise IncrementalJsonlError("invalid_state", "manifest must be lists")
    if len(summaries) != len(set(summaries)) or len(units) != len(set(units)):
        raise IncrementalJsonlError("invalid_state", "duplicate manifest ids")
    coverage = payload.get("raw_line_coverage")
    if not isinstance(coverage, dict):
        raise IncrementalJsonlError("invalid_state", "raw_line_coverage missing")
    _validate_raw_line_coverage(
        coverage,
        complete_boundary=int(payload.get("complete_boundary") or 0),
        prefix_sha256=str(payload.get("prefix_sha256") or ""),
    )
    return payload


def validate_rollback(payload: dict, *, source_path: str | None = None) -> dict:
    if not isinstance(payload, dict):
        raise IncrementalJsonlError("recovery_unproven", "rollback is not an object")
    if payload.get("version") != ROLLBACK_VERSION:
        raise IncrementalJsonlError("recovery_unproven", "unsupported rollback version")
    required = (
        "summaries",
        "units",
        "export_preimage",
        "processed_preimage",
        "source_path",
    )
    missing = [name for name in required if name not in payload]
    if missing:
        raise IncrementalJsonlError("recovery_unproven", f"rollback missing {missing}")
    if source_path is not None and payload.get("source_path") != source_path:
        raise IncrementalJsonlError("recovery_unproven", "cross-source rollback")
    if not isinstance(payload.get("summaries"), list) or not isinstance(
        payload.get("units"), list
    ):
        raise IncrementalJsonlError("recovery_unproven", "rollback collections must be lists")
    return payload


def _path_has_processed_entry(processed: dict, path_key: str) -> bool:
    for entry in processed.values():
        if not isinstance(entry, dict) or entry.get("excluded"):
            continue
        if entry.get("path") == path_key:
            return True
    return False


def decide_eligibility(
    *,
    enabled: bool,
    detected_format: str | None,
    path_key: str,
    processed: dict,
    chroma_row_count: int,
    checkpoint: dict | None,
    force_reindex: bool = False,
    supersede_on_reindex: bool = False,
    eligible_formats: frozenset[str] | None = None,
) -> str:
    """Pure eligibility decision. Does not construct checkpoint machinery."""
    allowed = eligible_formats or KIRO_ROUTE_FORMATS
    if not enabled:
        return "disabled"
    if detected_format not in allowed:
        return "ineligible_format"
    if force_reindex or supersede_on_reindex:
        return "incremental_force_unsupported"
    if checkpoint is None:
        if _path_has_processed_entry(processed, path_key) or chroma_row_count > 0:
            return "bootstrap_required"
        return "eligible_new_source"
    try:
        validate_checkpoint(
            checkpoint,
            source_path=path_key,
            adapter_format=detected_format,
        )
    except IncrementalJsonlError:
        return "invalid_state"
    return "eligible_checkpointed_source"


def _continuity_reason(checkpoint: dict | None, snapshot: dict, fingerprint: str) -> str | None:
    if checkpoint is None:
        return "initial_full"
    if checkpoint.get("source_identity") != snapshot["source_identity"]:
        return "source_identity_changed"
    if checkpoint.get("transform_fingerprint") != fingerprint:
        return "transform_fingerprint_changed"
    prior_gen = checkpoint.get("generation_identity") or {}
    current_gen = snapshot["generation_identity"]
    if (
        int(prior_gen.get("device", -1)) != int(current_gen["device"])
        or int(prior_gen.get("inode", -1)) != int(current_gen["inode"])
    ):
        return "source_replaced_or_rotated"
    if int(snapshot["complete_boundary"]) < int(checkpoint["complete_boundary"]):
        return "source_truncated"
    prior_boundary = int(checkpoint["complete_boundary"])
    if snapshot["raw"][:prior_boundary]:
        if _sha(snapshot["raw"][:prior_boundary]) != checkpoint.get("prefix_sha256"):
            return "validated_prefix_mutated"
    return None


class IncrementalJsonlCoordinator:
    """Source capture, cache, transaction, and follower reconciliation."""

    def __init__(
        self,
        boundary: IsolationBoundary | ProductionBoundary,
        source: Path | str,
        *,
        cfg: dict | None = None,
        enabled: bool = True,
        fault: FaultHook | None = None,
        counters: CallCounters | None = None,
        retry_sleep: bool = False,
        embed_dimension: int = 8,
        transform_fingerprint: str | None = None,
        models: dict | None = None,
        chunk_size: int | None = None,
        overlap: int | None = None,
        min_confidence: float | None = None,
        force_reindex: bool = False,
        supersede_on_reindex: bool = False,
        file_hash: str | None = None,
        processed: dict | None = None,
        bootstrap_existing: bool = False,
        expected_prefix_sha256: str | None = None,
        max_bootstrap_chunks: int | None = None,
        bootstrap_grant_fingerprint: str | None = None,
        bootstrap_operation_id: str | None = None,
        bootstrap_binding_fingerprint: str | None = None,
    ):
        if os.environ.get("CONVMEM_INCREMENTAL_ROOT"):
            IsolationBoundary.require_fake_provider("deterministic-fake")
        self.boundary = boundary
        source_resolver = getattr(boundary, "resolve_source", boundary.resolve_mutable)
        self.source = source_resolver(source, label="source fixture")
        self.cfg = cfg or self._load_isolated_config()
        settings = incremental_jsonl_settings(self.cfg)
        self.settings = settings
        self.enabled = bool(settings.enabled if cfg is not None else enabled)
        self.fault = fault or (lambda _point: None)
        self.counters = counters or CallCounters()
        self.retry_sleep = retry_sleep
        self.embed_dimension = embed_dimension
        self.force_reindex = force_reindex
        self.supersede_on_reindex = supersede_on_reindex
        self.file_hash = file_hash
        self.processed_override = processed
        self.bootstrap_existing = bootstrap_existing
        self.expected_prefix_sha256 = expected_prefix_sha256
        self.max_bootstrap_chunks = max_bootstrap_chunks
        self.bootstrap_grant_fingerprint = bootstrap_grant_fingerprint
        self.bootstrap_operation_id = bootstrap_operation_id
        self.bootstrap_binding_fingerprint = bootstrap_binding_fingerprint
        if bootstrap_existing:
            if not isinstance(boundary, ProductionBoundary):
                raise IncrementalJsonlError("bootstrap_requires_production_boundary")
            try:
                if len(expected_prefix_sha256 or "") != 64:
                    raise ValueError("expected prefix digest length")
                int(expected_prefix_sha256 or "", 16)
            except ValueError as exc:
                raise IncrementalJsonlError("bootstrap_digest_invalid") from exc
            if not isinstance(max_bootstrap_chunks, int) or max_bootstrap_chunks < 1:
                raise IncrementalJsonlError("bootstrap_chunk_limit_invalid")
            for value, code in (
                (bootstrap_grant_fingerprint, "bootstrap_grant_fingerprint_invalid"),
                (bootstrap_operation_id, "bootstrap_operation_id_invalid"),
                (bootstrap_binding_fingerprint, "bootstrap_binding_invalid"),
            ):
                try:
                    if len(value or "") != 64:
                        raise ValueError("digest length")
                    int(value or "", 16)
                except ValueError as exc:
                    raise IncrementalJsonlError(code) from exc
        index = self.cfg.get("index") if isinstance(self.cfg.get("index"), dict) else {}
        self.chunk_size = int(chunk_size if chunk_size is not None else index.get("chunk_size", 2))
        self.overlap = int(overlap if overlap is not None else index.get("chunk_overlap", 0))
        distill_cfg = self.cfg.get("distill") if isinstance(self.cfg.get("distill"), dict) else {}
        self.min_confidence = float(
            min_confidence if min_confidence is not None else distill_cfg.get("min_confidence", 0.6)
        )
        self.models = models or dict(self.cfg.get("models") or {})
        self.path_key = str(self.source)
        detected_format = detect_format(self.source)
        self.format_spec: IncrementalFormatSpec | None = get_format_spec(detected_format)
        self.routed_formats = routed_formats(
            isolated_codex=bool(os.environ.get("CONVMEM_INCREMENTAL_ROOT"))
        )
        if self.format_spec is None:
            self.format_spec = get_format_spec(ELIGIBLE_FORMAT)
        self.source_id = source_state_id(
            self.path_key, format_id=self.format_spec.format_id
        )
        state_root = boundary.resolve_mutable(settings.state_dir, label="incremental state")
        if state_root.exists() and not stat.S_ISDIR(state_root.stat().st_mode):
            raise IncrementalJsonlConfigError("invalid_state_dir", "state_dir is not a directory")
        state_root.mkdir(parents=True, exist_ok=True)
        os.chmod(state_root, 0o700)
        self.state_dir = state_root / self.source_id
        self.state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.state_dir, 0o700)
        self.paths = {
            "checkpoint": self.state_dir / "checkpoint.json",
            "transaction": self.state_dir / "transaction.json",
            "rollback": self.state_dir / "rollback.json",
            "prepared": self.state_dir / "prepared",
            "snapshots": self.state_dir / "snapshots",
            "lock": self.state_dir / "lock.flock",
        }
        for name in ("prepared", "snapshots"):
            self.paths[name].mkdir(parents=True, exist_ok=True)
            os.chmod(self.paths[name], 0o700)
        layout = boundary.layout
        self.config_path = layout["user_config"]
        self.writer_lock = layout["locks"] / "chroma_writer_gate.lock"
        self.attest_dir = layout["attest"]
        self.census_dir = layout["census"]
        layout["locks"].mkdir(parents=True, exist_ok=True)
        os.chmod(layout["locks"], 0o700)
        try:
            from chroma_write_store import current_implementation_revision

            revision = current_implementation_revision()
        except Exception:  # pylint: disable=broad-exception-caught
            revision = "hermetic-test"
        self.transform_fingerprint = transform_fingerprint or compute_transform_fingerprint(
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            min_confidence=self.min_confidence,
            models=self.models,
            embed_dimension=self.embed_dimension,
            implementation_revision=str(revision),
            adapter_format=self.format_spec.format_id,
            adapter_contract_version=self.format_spec.adapter_contract_version,
        )
        self.last_result: IncrementalRunResult | None = None
        self.last_evidence: dict[str, Any] = {}
        self._lock: SourceAdvisoryLock | None = None
        self._max_units_in_flight = 0

    @classmethod
    def from_isolated_boundary(
        cls,
        boundary: IsolationBoundary,
        source: Path | str,
        *,
        enabled: bool = True,
        **kwargs: Any,
    ) -> "IncrementalJsonlCoordinator":
        cfg = kwargs.pop("cfg", None)
        if cfg is None:
            import tomllib

            cfg = tomllib.loads(boundary.layout["user_config"].read_text(encoding="utf-8"))
            if enabled:
                index = cfg.setdefault("index", {})
                table = index.setdefault("incremental_jsonl", {})
                table["enabled"] = True
                table["state_dir"] = str(boundary.layout["state"])
                table["allow_full_rebuild"] = bool(table.get("allow_full_rebuild", False))
        return cls(boundary, source, cfg=cfg, enabled=enabled, **kwargs)

    def _load_isolated_config(self) -> dict:
        return load_config(self.boundary.layout["user_config"])

    def _transition(self, name: str, action: Callable[[], None]) -> None:
        if name not in DURABLE_TRANSITIONS:
            raise IncrementalJsonlError("undeclared_transition", name)
        self.fault(f"before_{name}")
        action()
        self.fault(f"after_{name}")

    def checkpoint(self) -> dict | None:
        payload = _read_json(self.paths["checkpoint"])
        if payload is None:
            return None
        return validate_checkpoint(
            payload,
            source_path=self.path_key,
            adapter_format=self.format_spec.format_id,
        )

    def _session(self):
        from chroma_write_store import production_chroma_write_session

        return production_chroma_write_session(
            self.config_path,
            lock_path=self.writer_lock,
            attest_dir=self.attest_dir,
            census_dir=self.census_dir,
            entrypoint="incremental_jsonl.apply",
        )

    @staticmethod
    def _validate_incremental_prefix_view(view) -> None:
        if any(item.outcome == "skipped_invalid_utf8" for item in view.line_outcomes):
            raise IncrementalJsonlError(
                "invalid_prefix_encoding",
                "complete line contains invalid UTF-8",
            )

    @staticmethod
    def _unit_owned_by_source(store, unit_id: str, source_path: str) -> bool:
        row = store.get_unit(unit_id)
        if row is None:
            return False
        metadata = row.get("metadata") or {}
        return metadata.get("source_path") == source_path

    @staticmethod
    def _export_unit_payload(row: dict) -> dict:
        payload = dict(row.get("metadata") or {})
        payload["id"] = row["id"]
        return payload

    def _chroma_row_count(self) -> int:
        chroma_dir = Path(self.cfg["index"]["chroma_dir"])
        if not chroma_dir.exists():
            return 0
        with self._session() as session:
            return len(session.store.ids_for_source(SUMMARIES, self.path_key)) + len(
                session.store.ids_for_source(UNITS, self.path_key)
            )

    def require_existing_embedding_dimension(self, expected: int) -> dict[str, int]:
        """Prove the effective dimension from existing source rows, not config."""

        dimensions: dict[str, int] = {}
        with self._session() as session:
            for name in (SUMMARIES, UNITS):
                rows = session.store.snapshot_source_rows(name, self.path_key)
                row_dimensions = {
                    len(row.get("embedding") or [])
                    for row in rows
                    if row.get("embedding") is not None
                }
                if not rows or len(row_dimensions) != 1 or 0 in row_dimensions:
                    raise IncrementalJsonlError(
                        "embedding_dimension_unproven",
                        f"{name} has no single non-empty source embedding dimension",
                    )
                dimensions[name] = row_dimensions.pop()
        if set(dimensions.values()) != {expected}:
            raise IncrementalJsonlError(
                "embedding_dimension_mismatch",
                f"existing collection dimensions {dimensions} differ from {expected}",
            )
        self.last_evidence["embedding_dimension_authority"] = dict(dimensions)
        return dimensions

    def _processed(self) -> dict:
        if self.processed_override is not None:
            return self.processed_override
        return load_processed(str(self.cfg["index"]["processed_log"]))

    def _capture(self, transaction_id: str) -> dict:
        detected = detect_format(self.source)
        if detected not in self.routed_formats:
            raise IsolationViolation(
                f"incremental route does not support format {detected}"
            )
        parser = get_parser(self.source)
        if (
            self.format_spec is None
            or parser is None
            or parser.__module__ != self.format_spec.adapter_module
        ):
            raise IsolationViolation("normal adapter dispatch did not select expected JSONL")
        snapshot_dir = self.paths["snapshots"] / transaction_id
        snapshot_path = snapshot_dir / self.format_spec.snapshot_basename

        def prepare() -> None:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(snapshot_dir, 0o700)

        self._transition("source_snapshot_prepare", prepare)
        fd = open_source_readonly(self.source)
        try:
            info = validate_regular_source(fd)
            raw = os.read(fd, info.st_size)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        if (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino):
            raise SourceCaptureError("source_identity_changed", "source rotated during capture")
        boundary = raw.rfind(b"\n") + 1
        prefix = raw[:boundary]

        def publish() -> None:
            _atomic_bytes(snapshot_path, prefix)
            if self.format_spec.session_meta_path:
                sibling = self.source.parent / self.format_spec.session_meta_path
                if sibling.is_file() and not sibling.is_symlink():
                    _atomic_bytes(
                        snapshot_dir / self.format_spec.session_meta_path,
                        sibling.read_bytes(),
                    )

        self._transition("source_snapshot_publish", publish)
        view = self.format_spec.parse_complete_prefix(str(snapshot_path), raw=prefix)
        self._validate_incremental_prefix_view(view)
        if len(view.messages) != len(view.byte_ranges):
            raise IncrementalJsonlError("invalid_state", "adapter output/byte-range disagreement")
        snapshot = {
            "raw": prefix,
            "complete_boundary": view.complete_boundary,
            "prefix_sha256": view.prefix_sha256,
            "messages": view.messages,
            "byte_ranges": view.byte_ranges,
            "line_outcomes": view.line_outcomes,
            "raw_line_coverage": serialize_raw_line_coverage(
                view.line_outcomes, view.prefix_sha256
            ),
            "generation_identity": {"device": int(info.st_dev), "inode": int(info.st_ino)},
            "session_meta_digest": view.session_meta_digest,
            "source_identity": self.source_id,
            "snapshot_path": snapshot_path,
            "snapshot_dir": snapshot_dir,
            "size": int(info.st_size),
        }
        self._revalidate_live_prefix(snapshot)
        return snapshot

    def _revalidate_live_prefix(self, snapshot: dict) -> None:
        def revalidate() -> None:
            fd = open_source_readonly(self.source)
            try:
                info = validate_regular_source(fd)
                raw = os.read(fd, max(snapshot["complete_boundary"], info.st_size))
            finally:
                os.close(fd)
            current = {
                "device": int(info.st_dev),
                "inode": int(info.st_ino),
            }
            if current != snapshot["generation_identity"]:
                raise SourceCaptureError("source_identity_changed", "live identity changed")
            if info.st_size < snapshot["complete_boundary"]:
                raise SourceCaptureError("source_truncated", "live size below selected boundary")
            if _sha(raw[: snapshot["complete_boundary"]]) != snapshot["prefix_sha256"]:
                raise SourceCaptureError("validated_prefix_mutated", "selected prefix changed")
            digest = None
            if self.format_spec.session_meta_path:
                sibling = self.source.parent / self.format_spec.session_meta_path
                digest = (
                    _sha(sibling.read_bytes())
                    if sibling.is_file() and not sibling.is_symlink()
                    else None
                )
            if digest != snapshot["session_meta_digest"]:
                raise SourceCaptureError("source_identity_changed", "session metadata changed")

        self._transition("source_revalidate", revalidate)

    def _prepared_key(self, chunk_start: int, input_digest: str) -> str:
        return _sha(
            f"{self.source_id}:{input_digest}:{self.transform_fingerprint}:{chunk_start}"
        )

    def _prepared_path(self, key: str) -> Path:
        return self.paths["prepared"] / f"{key}.json"

    def _write_prepared(self, artifact: dict) -> None:
        key = artifact["cache_key"]
        path = self._prepared_path(key)
        staged = dict(artifact)
        body = {name: value for name, value in staged.items() if name != "digest"}
        staged["digest"] = _sha(_canonical_json(body))

        def prepare() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)

        self._transition("prepared_output_prepare", prepare)

        def publish() -> None:
            _atomic_json(path, staged)

        self._transition("prepared_output_publish", publish)

    def _validate_prepared_artifact(
        self,
        payload: dict | None,
        *,
        expected: dict | None = None,
        key: str | None = None,
    ) -> dict:
        if payload is None:
            raise IncrementalJsonlError("recovery_unproven", "prepared artifact unreadable")
        if payload.get("version") != PREPARED_VERSION:
            raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared version mismatch")
        if payload.get("source_identity") != self.source_id:
            raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared source mismatch")
        if payload.get("transform_fingerprint") != self.transform_fingerprint:
            raise IncrementalJsonlError(
                "prepared_artifact_corrupt", "prepared fingerprint mismatch"
            )
        try:
            chunk_start = int(payload["chunk_start"])
            input_digest = str(payload["input_digest"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IncrementalJsonlError(
                "prepared_artifact_corrupt", "prepared chunk metadata invalid"
            ) from exc
        if expected is not None:
            if chunk_start != int(expected["chunk_start"]):
                raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared chunk_start mismatch")
            if input_digest != str(expected["input_digest"]):
                raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared input_digest mismatch")
        cache_key = payload.get("cache_key")
        derived_key = self._prepared_key(chunk_start, input_digest)
        if cache_key != derived_key:
            raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared cache_key mismatch")
        if key is not None and key != derived_key:
            raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared key mismatch")
        if not payload.get("complete"):
            raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared artifact incomplete")
        try:
            embeddings = [payload["summary_embedding"]] + [
                unit["embedding"] for unit in payload.get("units", [])
            ]
        except (TypeError, KeyError) as exc:
            raise IncrementalJsonlError(
                "prepared_artifact_corrupt", "prepared embeddings missing"
            ) from exc
        for embedding in embeddings:
            if len(embedding) != self.embed_dimension:
                raise IncrementalJsonlError(
                    "prepared_artifact_corrupt", "prepared embedding shape mismatch"
                )
        body = {name: value for name, value in payload.items() if name != "digest"}
        if payload.get("digest") != _sha(_canonical_json(body)):
            raise IncrementalJsonlError("prepared_artifact_corrupt", "prepared digest mismatch")
        return payload

    def _load_prepared(self, key: str, *, expected: dict) -> dict | None:
        path = self._prepared_path(key)
        if not path.is_file():
            return None
        payload = _read_json(path)
        return self._validate_prepared_artifact(payload, expected=expected, key=key)

    def _chunk_input_digest(self, chunk: dict) -> str:
        text = render_chunk(chunk["messages"])
        return hashlib.sha256(
            json.dumps(
                {
                    "start": chunk["start_offset"],
                    "end": chunk["end_offset"],
                    "text": text,
                    "messages": chunk["messages"],
                },
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()

    def _build_frontier(
        self,
        messages: list[dict],
        frontier: int,
        *,
        cache_required_before: int = 0,
    ) -> tuple[list[dict], int]:
        chunks = chunk_messages(messages, self.chunk_size, self.overlap)
        prepared: list[dict] = []
        reused = 0
        for chunk in chunks:
            expected = {
                "chunk_start": int(chunk["start_offset"]),
                "input_digest": self._chunk_input_digest(chunk),
            }
            key = self._prepared_key(expected["chunk_start"], expected["input_digest"])
            try:
                cached = self._load_prepared(key, expected=expected)
            except IncrementalJsonlError as exc:
                if (
                    exc.code == "prepared_artifact_corrupt"
                    and int(chunk["start_offset"]) < cache_required_before
                ):
                    raise IncrementalJsonlError(
                        "historical_cache_unavailable",
                        f"chunk {chunk['start_offset']}",
                    ) from exc
                raise
            if cached is not None:
                prepared.append(cached)
                reused += 1
                continue
            if int(chunk["start_offset"]) < cache_required_before:
                raise IncrementalJsonlError(
                    "historical_cache_unavailable",
                    f"chunk {chunk['start_offset']}",
                )
            built = build_chunk_artifact(
                chunk=chunk,
                path=self.path_key,
                path_key=self.path_key,
                models=self.models,
                tool=self.format_spec.tool,
                chunk_size=self.chunk_size,
                overlap=self.overlap,
                min_confidence=self.min_confidence,
                verbose=False,
                counters=self.counters,
                retry_sleep=self.retry_sleep,
            )
            if built is None or not built.complete or built.degraded:
                raise IncrementalJsonlError("transform_failed", f"chunk {chunk['start_offset']}")
            artifact = self._artifact_from_build(built, built.start_offset)
            self._write_prepared(artifact)
            loaded = self._load_prepared(artifact["cache_key"], expected=expected)
            prepared.append(loaded or artifact)
        _ = frontier  # retained for call-site evidence; cache hits encode stability
        return prepared, reused

    def _artifact_from_build(self, built: ChunkArtifact, chunk_start: int) -> dict:
        units = []
        for unit, document, embedding, metadata in built.units_to_add:
            units.append(
                {
                    "unit": unit,
                    "document": document,
                    "embedding": list(embedding),
                    "metadata": metadata,
                    "id": unit["id"],
                }
            )
        payload = {
            "version": PREPARED_VERSION,
            "source_identity": self.source_id,
            "transform_fingerprint": self.transform_fingerprint,
            "chunk_start": chunk_start,
            "input_digest": built.input_digest,
            "doc_id": built.doc_id,
            "summary": built.summary,
            "summary_embedding": list(built.summary_embedding),
            "metadata": built.metadata,
            "units": units,
            "complete": bool(built.complete and not built.degraded),
            "cache_key": self._prepared_key(chunk_start, built.input_digest),
        }
        self._max_units_in_flight = max(self._max_units_in_flight, len(units) + 1)
        return payload

    def _write_transaction(self, payload: dict) -> None:
        def prepare() -> None:
            self.paths["transaction"].parent.mkdir(parents=True, exist_ok=True)

        self._transition("transaction_prepare", prepare)

        def publish() -> None:
            _atomic_json(self.paths["transaction"], payload)

        self._transition("transaction_phase_publish", publish)

    def _bootstrap_transaction_binding(self) -> dict[str, str]:
        if not self.bootstrap_existing:
            return {}
        return {
            "grant_fingerprint": str(self.bootstrap_grant_fingerprint),
            "operation_id": str(self.bootstrap_operation_id),
            "binding_fingerprint": str(self.bootstrap_binding_fingerprint),
        }

    def _validate_bootstrap_transaction_binding(self, transaction: dict) -> None:
        if not self.bootstrap_existing:
            return
        expected = self._bootstrap_transaction_binding()
        actual = {name: transaction.get(name) for name in expected}
        if actual != expected:
            raise IncrementalJsonlError("bootstrap_replay_grant_mismatch")

    def _write_rollback(self, payload: dict) -> None:
        def prepare() -> None:
            self.paths["rollback"].parent.mkdir(parents=True, exist_ok=True)

        self._transition("rollback_prepare", prepare)

        def publish() -> None:
            _atomic_json(self.paths["rollback"], payload)

        self._transition("rollback_publish", publish)

    def _write_checkpoint(self, payload: dict) -> None:
        prepared = self.paths["checkpoint"].with_name(self.paths["checkpoint"].name + ".next")

        def prepare() -> None:
            _atomic_json(prepared, payload)

        self._transition("checkpoint_prepare", prepare)

        def publish() -> None:
            os.replace(prepared, self.paths["checkpoint"])
            _fsync_dir(self.paths["checkpoint"].parent)

        self._transition("checkpoint_publish", publish)

    def _apply_prepared(
        self,
        prepared: list[dict],
    ) -> tuple[int, int, list, set[str], set[str]]:
        from ingest_dedupe import evaluate_ingest_batch
        from provenance_binding import provenance_identity

        chunks = 0
        units = 0
        events: list = []
        keep_summaries: set[str] = set()
        keep_units: set[str] = set()
        with self._session() as session:
            for artifact in prepared:
                keep_summaries.add(str(artifact["doc_id"]))

                def summary_write(current=artifact) -> None:
                    session.store.add_summary(
                        current["doc_id"],
                        current["summary"],
                        current["summary_embedding"],
                        current["metadata"],
                    )

                self._transition("summary_upsert", summary_write)

                def unit_write(current=artifact) -> None:
                    nonlocal chunks, units
                    units_to_add = [
                        (row["unit"], row["document"], row["embedding"], row["metadata"])
                        for row in current["units"]
                    ]
                    dedupe = evaluate_ingest_batch(session.store, session.live_cfg, units_to_add)
                    events.append(dedupe)
                    written = 0
                    for unit, doc, unit_embedding, unit_meta in dedupe.accepted:
                        projection_unit = dict(unit)
                        projection_meta = dict(unit_meta)
                        existing = session.store.get_unit(unit["id"])
                        existing_identity = (
                            provenance_identity(existing.get("metadata") or {})
                            if existing is not None
                            else None
                        )
                        candidate_identity = provenance_identity(unit_meta)
                        if (
                            existing is not None
                            and candidate_identity is not None
                            and existing_identity != candidate_identity
                            and (existing_identity is not None or candidate_identity is not None)
                        ):
                            projection_id = hashlib.sha256(
                                (
                                    "convmem-p3-projection-v1:"
                                    f"{unit['id']}:{candidate_identity[0]}:{candidate_identity[1]}"
                                ).encode("utf-8")
                            ).hexdigest()
                            projection_unit["id"] = projection_id
                            projection_meta["id"] = projection_id
                        physical_id = str(projection_unit["id"])
                        session.store.add_unit(
                            physical_id, doc, unit_embedding, projection_meta
                        )
                        keep_units.add(physical_id)
                        written += 1
                    for suppression in dedupe.exact_suppressions:
                        matched_id = str(suppression["matched_id"])
                        if self._unit_owned_by_source(
                            session.store, matched_id, self.path_key
                        ):
                            keep_units.add(matched_id)
                    chunks += 1
                    units += written

                self._transition("unit_upsert", unit_write)

            def prune_summaries() -> None:
                session.store.delete_summaries_for_source(
                    self.path_key,
                    keep_ids=keep_summaries,
                    candidate_ids=session.store.ids_for_source(SUMMARIES, self.path_key),
                )

            self._transition("summaries_prune", prune_summaries)

            def prune_units() -> None:
                session.store.delete_units_for_source(
                    self.path_key,
                    keep_ids=keep_units,
                    candidate_ids=session.store.ids_for_source(UNITS, self.path_key),
                )

            self._transition("units_prune", prune_units)
        return chunks, units, events, keep_summaries, keep_units

    @staticmethod
    def _export_line_owned_by_source(raw: bytes, source_path: str) -> bool:
        try:
            row = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        return isinstance(row, dict) and row.get("source_path") == source_path

    def _snapshot_export_before_image(self) -> dict:
        from purge_locks import export_flock

        export_path = Path(self.cfg["index"]["units_export"])
        foreign_digest = hashlib.sha256()
        full_digest = hashlib.sha256()
        foreign_bytes = 0
        foreign_lines = 0
        source_lines: list[dict[str, Any]] = []
        with export_flock(self.cfg):
            existed = export_path.is_file()
            if existed:
                with export_path.open("rb") as handle:
                    for raw in handle:
                        full_digest.update(raw)
                        if self._export_line_owned_by_source(raw, self.path_key):
                            source_lines.append(
                                {
                                    "foreign_lines_before": foreign_lines,
                                    "payload_base64": base64.b64encode(raw).decode("ascii"),
                                }
                            )
                        else:
                            foreign_digest.update(raw)
                            foreign_bytes += len(raw)
                            foreign_lines += 1
        return {
            "version": 1,
            "existed": existed,
            "file_sha256": full_digest.hexdigest(),
            "foreign_sha256": foreign_digest.hexdigest(),
            "foreign_bytes": foreign_bytes,
            "foreign_lines": foreign_lines,
            "source_lines": source_lines,
        }

    def _snapshot_before_images(self) -> dict:
        with self._session() as session:
            summaries = session.store.snapshot_source_rows(SUMMARIES, self.path_key)
            units = session.store.snapshot_source_rows(UNITS, self.path_key)
            non_source_collections = {
                name: session.store.non_source_inventory_digest(name, self.path_key)
                for name in (SUMMARIES, UNITS)
            }
        processed = self._processed()
        processed_preimage = {
            key: value
            for key, value in processed.items()
            if isinstance(value, dict) and value.get("path") == self.path_key
        }
        export_preimage = self._snapshot_export_before_image()
        self.last_evidence["non_source_collections_before"] = non_source_collections
        self.last_evidence["export_before"] = {
            key: value
            for key, value in export_preimage.items()
            if key != "source_lines"
        }
        return {
            "version": ROLLBACK_VERSION,
            "summaries": summaries,
            "units": units,
            "export_preimage": export_preimage,
            "processed_preimage": processed_preimage,
            "source_path": self.path_key,
            "state_files": self._capture_state_files(),
            "prepared_files": self._capture_prepared_files(),
            "dedupe_files": self._capture_dedupe_files(),
            "non_source_collections": non_source_collections,
        }

    def _verify_non_source_collections(self, expected: dict) -> None:
        with self._session() as session:
            current = {
                name: session.store.non_source_inventory_digest(name, self.path_key)
                for name in (SUMMARIES, UNITS)
            }
        self.last_evidence["non_source_collections_after"] = current
        if current != expected:
            raise IncrementalJsonlError(
                "non_source_isolation_changed",
                "non-source collection id/metadata/document/embedding evidence differs",
            )

    def _file_preimage(self, path: Path) -> str | None:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def _capture_state_files(self) -> dict[str, str | None]:
        return {
            name: self._file_preimage(self.paths[name])
            for name in ("checkpoint", "transaction", "rollback")
        }

    def _capture_prepared_files(self) -> dict[str, str]:
        prepared_dir = self.paths["prepared"]
        captured: dict[str, str] = {}
        if not prepared_dir.is_dir():
            return captured
        for child in sorted(prepared_dir.iterdir()):
            if child.is_file():
                captured[child.name] = child.read_text(encoding="utf-8")
        return captured

    def _require_granted_path(self, path: Path | str, *, label: str) -> Path:
        try:
            return self.boundary.resolve_mutable(path, label=label)
        except IsolationViolation as exc:
            raise IncrementalJsonlError(
                "recovery_unproven",
                f"{label} outside granted role",
            ) from exc

    def _granted_dedupe_paths(self) -> dict[str, Path]:
        layout = getattr(self.boundary, "layout", None)
        if not isinstance(layout, dict) or "dedupe" not in layout:
            raise IncrementalJsonlError("recovery_unproven", "dedupe role missing from boundary")
        granted = self._require_granted_path(layout["dedupe"], label="dedupe role")
        paths: dict[str, Path] = {}
        for name in DEDUPE_FILENAMES:
            candidate = granted if granted.name == name else granted / name
            paths[name] = self._require_granted_path(candidate, label=f"dedupe {name}")
        return paths

    def _dedupe_restore_paths(self) -> dict[str, Path]:
        granted = self._granted_dedupe_paths()
        chroma = self._require_granted_path(self.cfg["index"]["chroma_dir"], label="chroma")
        for name, path in granted.items():
            derived = self._require_granted_path(
                chroma.parent / name,
                label=f"dedupe derived {name}",
            )
            if derived != path:
                raise IncrementalJsonlError(
                    "recovery_unproven",
                    f"dedupe location outside granted role: {derived}",
                )
        return granted

    def _capture_dedupe_files(self) -> dict[str, str | None]:
        paths = self._dedupe_restore_paths()
        return {name: self._file_preimage(path) for name, path in paths.items()}

    def _restore_file_preimage(self, path: Path, payload: str | None) -> None:
        if payload is None:
            path.unlink(missing_ok=True)
            return
        _atomic_bytes(path, payload.encode("utf-8"))

    def _restore_processed(self, processed_preimage: dict) -> None:
        from ingest import save_processed

        processed_path = str(self.cfg["index"]["processed_log"])
        current = load_processed(processed_path)
        restored = {
            key: value
            for key, value in current.items()
            if not (isinstance(value, dict) and value.get("path") == self.path_key)
        }
        restored.update(processed_preimage)
        save_processed(processed_path, restored)

    def _restore_state_files(
        self,
        state_files: dict | None,
        *,
        preserve_recovery_authority: bool = False,
    ) -> None:
        if not state_files:
            return
        for name in ("checkpoint", "transaction", "rollback"):
            if preserve_recovery_authority and name in {"transaction", "rollback"}:
                continue
            if name not in state_files:
                continue
            self._restore_file_preimage(self.paths[name], state_files[name])

    def _restore_prepared_files(self, prepared_files: dict | None) -> None:
        prepared_dir = self.paths["prepared"]
        prepared_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(prepared_dir, 0o700)
        expected = set((prepared_files or {}).keys())
        if prepared_dir.is_dir():
            for child in prepared_dir.iterdir():
                if child.is_file() and child.name not in expected:
                    child.unlink(missing_ok=True)
        for name, payload in (prepared_files or {}).items():
            self._restore_file_preimage(prepared_dir / name, payload)

    def _restore_dedupe_files(self, dedupe_files: dict | None) -> None:
        if not dedupe_files:
            return
        paths = self._dedupe_restore_paths()
        for name in DEDUPE_FILENAMES:
            if name not in dedupe_files:
                continue
            self._restore_file_preimage(paths[name], dedupe_files[name])

    def _restore_before_images(
        self,
        rollback: dict,
        *,
        preserve_recovery_authority: bool = False,
    ) -> None:
        if rollback.get("version") != ROLLBACK_VERSION:
            raise IncrementalJsonlError("recovery_unproven", "rollback version mismatch")
        if rollback.get("source_path") != self.path_key:
            raise IncrementalJsonlError("recovery_unproven", "rollback source mismatch")
        with self._session() as session:
            before_summary_ids = {row["id"] for row in rollback.get("summaries", [])}
            before_unit_ids = {row["id"] for row in rollback.get("units", [])}
            current_summaries = session.store.ids_for_source(SUMMARIES, self.path_key)
            current_units = session.store.ids_for_source(UNITS, self.path_key)
            extra_summaries = current_summaries - before_summary_ids
            extra_units = current_units - before_unit_ids
            if extra_summaries:
                session.store.delete_summaries_for_source(
                    self.path_key,
                    candidate_ids=extra_summaries,
                    keep_ids=before_summary_ids,
                )
            if extra_units:
                session.store.delete_units_for_source(
                    self.path_key,
                    candidate_ids=extra_units,
                    keep_ids=before_unit_ids,
                )
            session.store.restore_source_rows(SUMMARIES, rollback.get("summaries") or [])
            session.store.restore_source_rows(UNITS, rollback.get("units") or [])
        self._restore_export(rollback.get("export_preimage") or {})
        self._restore_processed(rollback.get("processed_preimage") or {})
        self._restore_state_files(
            rollback.get("state_files"),
            preserve_recovery_authority=preserve_recovery_authority,
        )
        self._restore_prepared_files(rollback.get("prepared_files"))
        self._restore_dedupe_files(rollback.get("dedupe_files"))

    @staticmethod
    def _export_temp(export_path: Path):  # pylint: disable=consider-using-with
        export_path.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(  # pylint: disable=consider-using-with
            mode="w+b",
            dir=export_path.parent,
            prefix=export_path.name + ".",
            suffix=".tmp",
            delete=False,
        )
        os.chmod(handle.name, 0o600)
        return handle

    def _restore_export(self, preimage: dict) -> None:
        if preimage.get("version") != 1:
            raise IncrementalJsonlError("recovery_unproven", "export preimage invalid")
        export_path = Path(self.cfg["index"]["units_export"])
        source_lines = list(preimage.get("source_lines") or [])
        from purge_locks import export_flock

        with export_flock(self.cfg):
            temp = self._export_temp(export_path)
            temp_path = Path(temp.name)
            foreign_digest = hashlib.sha256()
            foreign_bytes = 0
            foreign_lines = 0
            source_index = 0
            try:
                current = (  # pylint: disable=consider-using-with
                    export_path.open("rb")  # pylint: disable=consider-using-with
                    if export_path.is_file()
                    else None
                )
                try:
                    if current is not None:
                        for raw in current:
                            if self._export_line_owned_by_source(raw, self.path_key):
                                continue
                            while (
                                source_index < len(source_lines)
                                and source_lines[source_index].get("foreign_lines_before")
                                == foreign_lines
                            ):
                                temp.write(
                                    base64.b64decode(
                                        source_lines[source_index]["payload_base64"],
                                        validate=True,
                                    )
                                )
                                source_index += 1
                            temp.write(raw)
                            foreign_digest.update(raw)
                            foreign_bytes += len(raw)
                            foreign_lines += 1
                finally:
                    if current is not None:
                        current.close()
                while (
                    source_index < len(source_lines)
                    and source_lines[source_index].get("foreign_lines_before")
                    == foreign_lines
                ):
                    temp.write(
                        base64.b64decode(
                            source_lines[source_index]["payload_base64"], validate=True
                        )
                    )
                    source_index += 1
                authority = (
                    foreign_digest.hexdigest() == preimage.get("foreign_sha256")
                    and foreign_bytes == preimage.get("foreign_bytes")
                    and foreign_lines == preimage.get("foreign_lines")
                    and source_index == len(source_lines)
                )
                if not authority:
                    raise IncrementalJsonlError(
                        "rollback_export_foreign_changed",
                        "unrelated export bytes differ from rollback authority",
                    )
                temp.flush()
                os.fsync(temp.fileno())
                temp.close()
                if not preimage.get("existed") and temp_path.stat().st_size == 0:
                    export_path.unlink(missing_ok=True)
                    temp_path.unlink(missing_ok=True)
                else:
                    os.replace(temp_path, export_path)
                _fsync_dir(export_path.parent)
            finally:
                if not temp.closed:
                    temp.close()
                temp_path.unlink(missing_ok=True)

    def _reconcile_export(self) -> None:
        from purge_locks import export_flock

        export_path = Path(self.cfg["index"]["units_export"])

        def reconcile() -> None:
            with self._session() as session:
                rows = session.store.snapshot_source_rows(UNITS, self.path_key)
            with export_flock(self.cfg):
                temp = self._export_temp(export_path)
                temp_path = Path(temp.name)
                try:
                    if export_path.is_file():
                        with export_path.open("rb") as current:
                            for raw in current:
                                if not self._export_line_owned_by_source(
                                    raw, self.path_key
                                ):
                                    temp.write(raw)
                    for row in rows:
                        payload = self._export_unit_payload(row)
                        temp.write(
                            (json.dumps(payload, separators=(",", ":")) + "\n").encode(
                                "utf-8"
                            )
                        )
                    temp.flush()
                    os.fsync(temp.fileno())
                    temp.close()
                    os.replace(temp_path, export_path)
                    _fsync_dir(export_path.parent)
                finally:
                    if not temp.closed:
                        temp.close()
                    temp_path.unlink(missing_ok=True)

        self._transition("export_reconcile", reconcile)

    def _reconcile_dedupe(self, transaction_id: str, events: list) -> tuple[int, int]:
        from ingest_dedupe import persist_ingest_dedupe, IngestDedupeResult

        exact = []
        semantic = []
        sequence = 0
        for result in events:
            for row in result.exact_suppressions:
                sequence += 1
                event = dict(row)
                event.pop("suppressed_at", None)
                event["transaction_id"] = transaction_id
                event["transaction_sequence"] = sequence
                event["event_id"] = _sha(
                    f"{transaction_id}:exact:{sequence}:"
                    f"{row.get('suppressed_id')}:{row.get('matched_id')}"
                )
                exact.append(event)
            for row in result.semantic_candidates:
                sequence += 1
                event = dict(row)
                event.pop("queued_at", None)
                event["transaction_id"] = transaction_id
                event["transaction_sequence"] = sequence
                event["event_id"] = _sha(
                    f"{transaction_id}:semantic:{sequence}:"
                    f"{row.get('id_a')}:{row.get('id_b')}"
                )
                semantic.append(event)
        combined = IngestDedupeResult(exact_suppressions=exact, semantic_candidates=semantic)
        paths = self._dedupe_restore_paths()
        before = {
            name: self._file_prefix_authority(path) for name, path in paths.items()
        }

        stats: dict[str, int] = {}

        def reconcile() -> None:
            stats.update(persist_ingest_dedupe(self.cfg, combined))

        self._transition("dedupe_reconcile", reconcile)
        expected_ids = {
            name: {
                str(row["event_id"])
                for row in (exact if name == "ingest_duplicate_suppressions.jsonl" else semantic)
            }
            for name in DEDUPE_FILENAMES
        }
        self.last_evidence["dedupe"] = {
            name: self._verify_dedupe_append(
                paths[name], before[name], transaction_id, expected_ids[name]
            )
            for name in DEDUPE_FILENAMES
        }
        return (
            int(stats.get("exact_suppressed", 0)),
            int(stats.get("semantic_candidates_queued", 0)),
        )

    @staticmethod
    def _file_prefix_authority(path: Path) -> dict[str, Any]:
        digest = hashlib.sha256()
        size = 0
        if path.is_file():
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
                    size += len(block)
        return {"size": size, "sha256": digest.hexdigest()}

    @staticmethod
    def _verify_dedupe_append(
        path: Path,
        before: dict[str, Any],
        transaction_id: str,
        expected_event_ids: set[str],
    ) -> dict[str, Any]:
        digest = hashlib.sha256()
        suffix = b""
        if not path.is_file():
            if int(before["size"]) == 0 and not expected_event_ids:
                return {
                    "old_size": 0,
                    "old_sha256": before["sha256"],
                    "new_bytes": 0,
                    "event_ids": [],
                }
            raise IncrementalJsonlError(
                "dedupe_append_missing", "expected dedupe append file is absent"
            )
        with path.open("rb") as handle:
            remaining = int(before["size"])
            while remaining:
                block = handle.read(min(1024 * 1024, remaining))
                if not block:
                    raise IncrementalJsonlError(
                        "dedupe_prefix_changed", "dedupe file was truncated"
                    )
                digest.update(block)
                remaining -= len(block)
            suffix = handle.read()
        if digest.hexdigest() != before["sha256"]:
            raise IncrementalJsonlError(
                "dedupe_prefix_changed", "old dedupe bytes are not an exact prefix"
            )
        observed: set[str] = set()
        for raw in suffix.splitlines():
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise IncrementalJsonlError(
                    "dedupe_append_invalid", "new dedupe row is invalid JSON"
                ) from exc
            if row.get("transaction_id") != transaction_id:
                raise IncrementalJsonlError(
                    "dedupe_append_unbound", "new dedupe row belongs to another transaction"
                )
            observed.add(str(row.get("event_id") or ""))
        if not observed.issubset(expected_event_ids):
            raise IncrementalJsonlError(
                "dedupe_append_unbound", "new dedupe event was not deterministically derived"
            )
        return {
            "old_size": int(before["size"]),
            "old_sha256": before["sha256"],
            "new_bytes": len(suffix),
            "event_ids": sorted(observed),
        }

    def _publish_processed(self, processed_hash: str, chunks: int, units: int) -> bool:
        from ingest import commit_processed_index_entry, _path_is_excluded

        committed = {"ok": False}

        def publish() -> None:
            if _path_is_excluded(self._processed(), self.path_key):
                committed["ok"] = False
                return
            committed["ok"] = commit_processed_index_entry(
                str(self.cfg["index"]["processed_log"]),
                file_hash=processed_hash,
                path_key=self.path_key,
                chunks=chunks,
                units=units,
            )

        self._transition("processed_publish", publish)
        return committed["ok"]

    def _cleanup(self, snapshot_dir: Path) -> None:
        def tx_cleanup() -> None:
            self.paths["transaction"].unlink(missing_ok=True)
            self.paths["rollback"].unlink(missing_ok=True)

        self._transition("transaction_cleanup", tx_cleanup)

        def snap_cleanup() -> None:
            if snapshot_dir.exists():
                for child in snapshot_dir.iterdir():
                    child.unlink(missing_ok=True)
                snapshot_dir.rmdir()

        self._transition("snapshot_cleanup", snap_cleanup)

    def _refusal(
        self,
        outcome: str,
        *,
        mode: str = "refused",
        fallback: str | None = None,
        snapshot: dict | None = None,
        ingest_status: str = "skipped",
    ) -> IncrementalRunResult:
        result = IncrementalRunResult(
            outcome=outcome,
            mode=mode,
            fallback_reason=fallback,
            adapter_format=self.format_spec.format_id,
            selected_boundary=int(snapshot["complete_boundary"]) if snapshot else 0,
            records=len(snapshot["messages"]) if snapshot else 0,
            frontier_record=0,
            counters=self.counters,
            reused_artifacts=0,
            max_units_in_flight=self._max_units_in_flight,
            active_generation="",
            ingest_status=ingest_status,
        )
        self.last_result = result
        return result

    def _commit_generation(
        self,
        *,
        snapshot: dict,
        prepared: list[dict],
        frontier: int,
        fallback: str | None,
        reused: int,
        transaction_id: str,
        mode: str,
        rollback_authority_sha256: str | None = None,
    ) -> IncrementalRunResult:
        from ingest import _path_is_excluded
        from purge_locks import source_flock

        generation = _sha(
            "jsonl-incremental-generation-v1:"
            f"{self.source_id}:{snapshot['prefix_sha256']}:{snapshot['complete_boundary']}:"
            f"{self.transform_fingerprint}"
        )
        self._revalidate_live_prefix(snapshot)
        with source_flock(self.cfg, self.path_key):
            if _path_is_excluded(self._processed(), self.path_key):
                return self._refusal("excluded", snapshot=snapshot)
            if rollback_authority_sha256 is None:
                rollback = self._snapshot_before_images()
                self._write_rollback(rollback)
                rollback_authority_sha256 = hashlib.sha256(
                    self.paths["rollback"].read_bytes()
                ).hexdigest()
                self._write_transaction(
                    {
                        "version": TRANSACTION_VERSION,
                        "transaction_id": transaction_id,
                        "phase": "APPLYING",
                        "bootstrap_existing": self.bootstrap_existing,
                        **self._bootstrap_transaction_binding(),
                        "source_path": self.path_key,
                        "source_identity": self.source_id,
                        "generation": generation,
                        "prepared_keys": [item["cache_key"] for item in prepared],
                        "generation_identity": snapshot["generation_identity"],
                        "complete_boundary": snapshot["complete_boundary"],
                        "prefix_sha256": snapshot["prefix_sha256"],
                        "session_meta_digest": snapshot["session_meta_digest"],
                        "rollback_authority_sha256": rollback_authority_sha256,
                    }
                )
            else:
                rollback = self._require_rollback_authority(
                    rollback_authority_sha256
                )
                self._verify_non_source_collections(
                    rollback.get("non_source_collections") or {}
                )
            chunks, units, events, keep_summaries, keep_units = self._apply_prepared(
                prepared
            )
            if rollback_authority_sha256 is not None:
                rollback = self._require_rollback_authority(
                    rollback_authority_sha256
                )
            self._verify_non_source_collections(
                rollback.get("non_source_collections") or {}
            )
            self._revalidate_live_prefix(snapshot)
            checkpoint = {
                "version": CHECKPOINT_VERSION,
                "commit_state": "complete",
                "adapter_format": self.format_spec.format_id,
                "source_identity": self.source_id,
                "source_path": self.path_key,
                "generation_identity": snapshot["generation_identity"],
                "complete_boundary": snapshot["complete_boundary"],
                "prefix_sha256": snapshot["prefix_sha256"],
                "transform_fingerprint": self.transform_fingerprint,
                "record_count": len(snapshot["messages"]),
                "chunk_frontier": frontier,
                "active_generation": generation,
                "summary_ids": sorted(keep_summaries),
                "unit_ids": sorted(keep_units),
                "processed_hash": snapshot["prefix_sha256"],
                "raw_line_coverage": snapshot["raw_line_coverage"],
                "fallback_reason": fallback,
            }
            self._write_checkpoint(checkpoint)
            self._reconcile_export()
            exact, semantic = self._reconcile_dedupe(transaction_id, events)
        committed = self._publish_processed(snapshot["prefix_sha256"], chunks, units)
        self._cleanup(snapshot["snapshot_dir"])
        result = IncrementalRunResult(
            outcome="committed" if committed else "excluded_after_checkpoint",
            mode=mode,
            fallback_reason=fallback,
            adapter_format=self.format_spec.format_id,
            selected_boundary=snapshot["complete_boundary"],
            records=len(snapshot["messages"]),
            frontier_record=frontier,
            counters=self.counters,
            reused_artifacts=reused,
            max_units_in_flight=self._max_units_in_flight,
            active_generation=generation,
            chunks=chunks,
            units=units,
            exact_suppressed=exact,
            semantic_queued=semantic,
            ingest_status="processed" if committed else "skipped",
        )
        self.last_result = result
        return result

    def _require_rollback_authority(self, expected_sha256: str) -> dict:
        try:
            raw = self.paths["rollback"].read_bytes()
        except OSError as exc:
            raise IncrementalJsonlError(
                "recovery_unproven", "original rollback journal is unavailable"
            ) from exc
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise IncrementalJsonlError(
                "recovery_unproven", "original rollback journal changed during replay"
            )
        rollback = _read_json(self.paths["rollback"])
        if rollback is None:
            raise IncrementalJsonlError(
                "recovery_unproven", "rollback journal corrupt"
            )
        return validate_rollback(rollback, source_path=self.path_key)

    def _restore_replay_before_images(
        self,
        rollback: dict,
        rollback_sha256: str,
        snapshot_dir: Path,
    ) -> None:
        self._restore_before_images(
            rollback,
            preserve_recovery_authority=True,
        )
        self._verify_non_source_collections(
            rollback.get("non_source_collections") or {}
        )
        self._require_rollback_authority(rollback_sha256)
        self._cleanup(snapshot_dir)

    def _roll_forward(self, transaction: dict) -> IncrementalRunResult:
        phase = str(transaction.get("phase") or "")
        if phase not in {"PREPARING", "transform_failed", "APPLYING"}:
            raise IncrementalJsonlError("recovery_unproven", "unknown transaction phase")
        rollback_path = self.paths["rollback"]
        rollback_sha256 = None
        if rollback_path.is_file():
            if phase == "APPLYING":
                rollback_sha256 = str(
                    transaction.get("rollback_authority_sha256") or ""
                )
                if len(rollback_sha256) != 64 or any(
                    char not in "0123456789abcdef" for char in rollback_sha256
                ):
                    raise IncrementalJsonlError(
                        "recovery_unproven",
                        "applying transaction lacks bound rollback authority",
                    )
                rollback = self._require_rollback_authority(rollback_sha256)
            else:
                rollback_sha256 = hashlib.sha256(
                    rollback_path.read_bytes()
                ).hexdigest()
                rollback = _read_json(rollback_path)
                if rollback is None:
                    raise IncrementalJsonlError(
                        "recovery_unproven", "rollback journal corrupt"
                    )
                rollback = validate_rollback(rollback, source_path=self.path_key)
        else:
            rollback = None
        if phase == "APPLYING" and (rollback is None or rollback_sha256 is None):
            raise IncrementalJsonlError(
                "recovery_unproven", "applying transaction lacks rollback authority"
            )
        if phase == "transform_failed" and rollback is not None:
            raise IncrementalJsonlError(
                "recovery_unproven", "rollback authority exists after transform failure"
            )
        snapshot_dirs = list(self.paths["snapshots"].glob("*"))
        if not snapshot_dirs:
            raise IncrementalJsonlError("recovery_unproven", "missing snapshot")
        snapshot_dir = Path(snapshot_dirs[0])
        snapshot_path = snapshot_dir / self.format_spec.snapshot_basename
        raw = snapshot_path.read_bytes()
        view = self.format_spec.parse_complete_prefix(str(snapshot_path), raw=raw)
        self._validate_incremental_prefix_view(view)
        if self.bootstrap_existing and (
            view.prefix_sha256 != self.expected_prefix_sha256
            or len(chunk_messages(view.messages, self.chunk_size, self.overlap))
            > int(self.max_bootstrap_chunks or 0)
        ):
            raise IncrementalJsonlError("bootstrap_replay_grant_mismatch")
        snapshot = {
            "raw": raw,
            "complete_boundary": view.complete_boundary,
            "prefix_sha256": view.prefix_sha256,
            "messages": view.messages,
            "byte_ranges": view.byte_ranges,
            "line_outcomes": view.line_outcomes,
            "raw_line_coverage": serialize_raw_line_coverage(
                view.line_outcomes, view.prefix_sha256
            ),
            "generation_identity": transaction.get("generation_identity")
            or {"device": view.device, "inode": view.inode},
            "session_meta_digest": view.session_meta_digest,
            "source_identity": self.source_id,
            "snapshot_path": snapshot_path,
            "snapshot_dir": snapshot_dir,
        }
        try:
            self._revalidate_live_prefix(snapshot)
            prepared = []
            reused = 0
            keys = list(transaction.get("prepared_keys") or [])
            if phase == "APPLYING" and not keys:
                raise IncrementalJsonlError(
                    "recovery_unproven", "applying transaction lacks prepared keys"
                )
            if keys:
                for key in keys:
                    payload = _read_json(self._prepared_path(key))
                    prepared.append(
                        self._validate_prepared_artifact(payload, key=key)
                    )
                reused = len(prepared)
            else:
                prior_count = 0
                try:
                    prior_cp = self.checkpoint()
                    prior_count = int(prior_cp.get("record_count") or 0) if prior_cp else 0
                except IncrementalJsonlError:
                    prior_count = 0
                frontier = frontier_start(prior_count, self.chunk_size, self.overlap)
                prepared, reused = self._build_frontier(
                    snapshot["messages"],
                    frontier,
                    cache_required_before=frontier,
                )
            prior = None
            try:
                prior = self.checkpoint()
            except IncrementalJsonlError:
                prior = None
            frontier = frontier_start(len(view.messages), self.chunk_size, self.overlap)
            if prior:
                frontier = int(prior.get("chunk_frontier") or 0)
            return self._commit_generation(
                snapshot=snapshot,
                prepared=prepared,
                frontier=frontier,
                fallback=None,
                reused=reused,
                transaction_id=str(transaction.get("transaction_id") or uuid.uuid4().hex),
                mode={
                    "APPLYING": "replay_forward",
                    "PREPARING": "preparing_recovery",
                    "transform_failed": "transform_failed_recovery",
                }[phase],
                rollback_authority_sha256=rollback_sha256,
            )
        except SourceCaptureError:
            if rollback is None:
                return self._refusal("source_moved", mode="aborted", snapshot=snapshot)
            assert rollback_sha256 is not None
            self._restore_replay_before_images(
                rollback,
                rollback_sha256,
                snapshot_dir,
            )
            return self._refusal("rolled_back", mode="rollback", snapshot=snapshot)
        except IncrementalJsonlError as exc:
            if rollback is None:
                if not self.bootstrap_existing:
                    self._cleanup(snapshot_dir)
                return self._refusal(exc.code, mode="aborted", snapshot=snapshot)
            assert rollback_sha256 is not None
            self._restore_replay_before_images(
                rollback,
                rollback_sha256,
                snapshot_dir,
            )
            return self._refusal("rolled_back", mode="rollback", snapshot=snapshot)

    def run(self) -> IncrementalRunResult:  # pylint: disable=too-many-return-statements
        if not self.enabled:
            return self._refusal("disabled")
        detected = detect_format(self.source)
        if detected not in self.routed_formats:
            return self._refusal("ineligible_format")
        if self.force_reindex or self.supersede_on_reindex:
            return self._refusal("incremental_force_unsupported")

        def acquire() -> None:
            self._lock = SourceAdvisoryLock(self.boundary, self.paths["lock"])
            self._lock.acquire()

        self._transition("lock_acquire", acquire)
        try:
            existing_tx = _read_json(self.paths["transaction"])
            if existing_tx:
                if isinstance(self.boundary, ProductionBoundary):
                    was_bootstrap = existing_tx.get("bootstrap_existing") is True
                    if was_bootstrap != self.bootstrap_existing:
                        return self._refusal("bootstrap_requires_one_shot")
                    if was_bootstrap and (
                        existing_tx.get("prefix_sha256") != self.expected_prefix_sha256
                    ):
                        return self._refusal("bootstrap_replay_grant_mismatch")
                    try:
                        self._validate_bootstrap_transaction_binding(existing_tx)
                    except IncrementalJsonlError as exc:
                        return self._refusal(exc.code)
                return self._roll_forward(existing_tx)
            transaction_id = uuid.uuid4().hex
            try:
                snapshot = self._capture(transaction_id)
            except IncrementalJsonlError as exc:
                return self._refusal(exc.code, fallback=exc.detail or None)
            checkpoint = None
            try:
                checkpoint = self.checkpoint()
            except IncrementalJsonlError:
                return self._refusal("invalid_state", snapshot=snapshot)
            if self.bootstrap_existing and snapshot["prefix_sha256"] != self.expected_prefix_sha256:
                self._cleanup(snapshot["snapshot_dir"])
                return self._refusal("bootstrap_source_digest_mismatch")
            processed = self._processed()
            chroma_count = 0
            if checkpoint is None and not _path_has_processed_entry(processed, self.path_key):
                chroma_count = self._chroma_row_count()
            outcome = decide_eligibility(
                enabled=True,
                detected_format=detected,
                path_key=self.path_key,
                processed=processed,
                chroma_row_count=chroma_count,
                checkpoint=checkpoint,
                force_reindex=self.force_reindex,
                supersede_on_reindex=self.supersede_on_reindex,
                eligible_formats=self.routed_formats,
            )
            if self.bootstrap_existing and outcome != "bootstrap_required":
                self._cleanup(snapshot["snapshot_dir"])
                return self._refusal("bootstrap_not_required")
            if outcome == "bootstrap_required" and self.bootstrap_existing:
                chunk_count = len(chunk_messages(
                    snapshot["messages"], self.chunk_size, self.overlap
                ))
                if chunk_count > int(self.max_bootstrap_chunks or 0):
                    self._cleanup(snapshot["snapshot_dir"])
                    return self._refusal("bootstrap_chunk_limit_exceeded")
                outcome = "eligible_bootstrap_existing"
            if outcome in {"bootstrap_required", "invalid_state"}:
                self._cleanup(snapshot["snapshot_dir"])
                return self._refusal(outcome, snapshot=snapshot)
            continuity = _continuity_reason(checkpoint, snapshot, self.transform_fingerprint)
            if continuity and continuity != "initial_full" and not self.settings.allow_full_rebuild:
                return self._refusal(
                    f"rebuild_required:{continuity}",
                    fallback=continuity,
                    snapshot=snapshot,
                )
            if (
                checkpoint is not None
                and continuity is None
                and checkpoint.get("complete_boundary") == snapshot["complete_boundary"]
                and checkpoint.get("record_count") == len(snapshot["messages"])
            ):
                # Unchanged selected prefix: repair followers with zero transform calls.
                self._cleanup(snapshot["snapshot_dir"])
                result = IncrementalRunResult(
                    outcome="unchanged",
                    mode="unchanged",
                    fallback_reason=None,
                    adapter_format=self.format_spec.format_id,
                    selected_boundary=snapshot["complete_boundary"],
                    records=len(snapshot["messages"]),
                    frontier_record=int(checkpoint.get("chunk_frontier") or 0),
                    counters=self.counters,
                    reused_artifacts=0,
                    max_units_in_flight=0,
                    active_generation=str(checkpoint.get("active_generation") or ""),
                    ingest_status="skipped",
                )
                self.last_result = result
                return result
            frontier = 0 if continuity else frontier_start(
                int(checkpoint["record_count"]) if checkpoint else 0,
                self.chunk_size,
                self.overlap,
            )
            self._write_transaction(
                {
                    "version": TRANSACTION_VERSION,
                    "transaction_id": transaction_id,
                    "phase": "PREPARING",
                    "bootstrap_existing": self.bootstrap_existing,
                    **self._bootstrap_transaction_binding(),
                    "source_path": self.path_key,
                    "source_identity": self.source_id,
                    "generation_identity": snapshot["generation_identity"],
                    "complete_boundary": snapshot["complete_boundary"],
                    "prefix_sha256": snapshot["prefix_sha256"],
                    "session_meta_digest": snapshot["session_meta_digest"],
                    "prior_checkpoint_digest": _sha(_canonical_json(checkpoint))
                    if checkpoint
                    else None,
                }
            )
            mode = "bootstrap_existing" if self.bootstrap_existing else (
                "full_rebuild_fallback" if continuity and continuity != "initial_full" else (
                    "initial_full" if continuity == "initial_full" else "incremental"
                )
            )
            cache_required_before = frontier if mode == "incremental" else 0
            try:
                prepared, reused = self._build_frontier(
                    snapshot["messages"],
                    frontier,
                    cache_required_before=cache_required_before,
                )
            except Exception as exc:  # bootstrap preserves paid-work recovery state
                if self.bootstrap_existing:
                    transaction = _read_json(self.paths["transaction"]) or {}
                    transaction.update(
                        {
                            "phase": "transform_failed",
                            "failure_code": getattr(
                                exc, "code", type(exc).__name__
                            ),
                        }
                    )
                    self._write_transaction(transaction)
                    if isinstance(exc, IncrementalJsonlError):
                        return self._refusal(
                            exc.code,
                            fallback=exc.detail or None,
                            snapshot=snapshot,
                        )
                    raise
                if isinstance(exc, IncrementalJsonlError):
                    self._cleanup(snapshot["snapshot_dir"])
                    return self._refusal(
                        exc.code,
                        fallback=exc.detail or None,
                        snapshot=snapshot,
                    )
                raise
            self._write_transaction(
                {
                    "version": TRANSACTION_VERSION,
                    "transaction_id": transaction_id,
                    "phase": "PREPARING",
                    "bootstrap_existing": self.bootstrap_existing,
                    **self._bootstrap_transaction_binding(),
                    "source_path": self.path_key,
                    "source_identity": self.source_id,
                    "generation_identity": snapshot["generation_identity"],
                    "complete_boundary": snapshot["complete_boundary"],
                    "prefix_sha256": snapshot["prefix_sha256"],
                    "session_meta_digest": snapshot["session_meta_digest"],
                    "prepared_keys": [item["cache_key"] for item in prepared],
                    "prior_checkpoint_digest": _sha(_canonical_json(checkpoint))
                    if checkpoint
                    else None,
                }
            )
            return self._commit_generation(
                snapshot=snapshot,
                prepared=prepared,
                frontier=frontier,
                fallback=continuity if continuity != "initial_full" else None,
                reused=reused,
                transaction_id=transaction_id,
                mode=mode,
            )
        finally:
            def release() -> None:
                if self._lock is not None:
                    self._lock.release()
                    self._lock = None

            self._transition("lock_release", release)


def maybe_route_incremental(
    *,
    cfg: dict,
    idx: dict,
    path: str,
    path_key: str,
    file_hash: str,
    processed: dict,
    models: dict,
    tool: str,
    units_export: Path | None,
    chunk_size: int,
    overlap: int,
    min_confidence: float,
    force_reindex: bool,
    supersede_on_reindex: bool,
    verbose: bool,
    detected_format: str | None,
) -> tuple[str, int, int, int, int] | None:
    """Return ingest tuple when the incremental route owns the file, else None."""
    _ = (idx, tool, units_export, verbose)
    settings = incremental_jsonl_settings(cfg)
    if not settings.enabled:
        return None
    isolated = bool(os.environ.get("CONVMEM_INCREMENTAL_ROOT"))
    if isolated:
        if detected_format not in routed_formats(isolated_codex=True):
            return None
        boundary = IsolationBoundary.from_environment()
    else:
        # An enabled table alone does not select production sources. Unselected
        # files retain the legacy route, including formats without a spec.
        if path_key not in settings.live_sources:
            return None
        if detected_format not in routed_formats():
            raise IncrementalJsonlError("live_format_not_eligible", str(detected_format))
        if force_reindex or supersede_on_reindex:
            raise IncrementalJsonlError("live_force_unsupported")
        if settings.embed_dimension is None:
            raise IncrementalJsonlConfigError(
                "live_embed_dimension_required",
                "selected live sources require an explicit embed_dimension",
            )
        boundary = ProductionBoundary(cfg, path)
    coordinator = IncrementalJsonlCoordinator(
        boundary,
        path,
        cfg=cfg,
        enabled=True,
        models=models,
        chunk_size=chunk_size,
        overlap=overlap,
        min_confidence=min_confidence,
        embed_dimension=settings.embed_dimension or 8,
        force_reindex=force_reindex,
        supersede_on_reindex=supersede_on_reindex,
        file_hash=file_hash,
        processed=processed,
    )
    result = coordinator.run()
    if not isolated and result.outcome not in {"committed", "unchanged"}:
        raise IncrementalJsonlError("live_route_refused", result.outcome)
    return result.ingest_tuple()
