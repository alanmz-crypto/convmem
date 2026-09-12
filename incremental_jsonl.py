"""Default-off production coordinator for incremental Kiro JSONL ingest.

Production code must not import ``scratch_jsonl_prototype``. This module lifts
the reviewed prefix/continuity/frontier/replay rules and adds a prepared-output
cache plus source-scoped Chroma before-image rollback.
"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-locals
# pylint: disable=too-many-branches,too-many-statements,too-many-lines,duplicate-code

from __future__ import annotations

import hashlib
import json
import os
import stat
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from adapters.detect import detect_format, get_parser
from adapters.kiro_session_jsonl import parse_complete_prefix
from chroma_store import SUMMARIES, UNITS
from config import IncrementalJsonlConfigError, incremental_jsonl_settings, load_config
from incremental_jsonl_isolation import (
    IsolationBoundary,
    IsolationViolation,
    SourceAdvisoryLock,
    SourceCaptureError,
    open_source_readonly,
    validate_regular_source,
)
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
ROLLBACK_VERSION = 1
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

    def as_dict(self) -> dict[str, int]:
        return asdict(self)

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


def source_state_id(canonical_path: str) -> str:
    return _sha(f"jsonl_kiro_session:{canonical_path}")


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
) -> str:
    payload = {
        "adapter_format": ELIGIBLE_FORMAT,
        "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
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


def validate_checkpoint(payload: dict, *, source_path: str | None = None) -> dict:
    if not isinstance(payload, dict):
        raise IncrementalJsonlError("invalid_state", "checkpoint is not an object")
    if payload.get("version") != CHECKPOINT_VERSION:
        raise IncrementalJsonlError("invalid_state", "unsupported checkpoint version")
    missing = [name for name in REQUIRED_CHECKPOINT_FIELDS if name not in payload]
    if missing:
        raise IncrementalJsonlError("invalid_state", f"checkpoint missing {missing}")
    if payload.get("adapter_format") != ELIGIBLE_FORMAT:
        raise IncrementalJsonlError("invalid_state", "checkpoint adapter mismatch")
    if source_path is not None and payload.get("source_path") != source_path:
        raise IncrementalJsonlError("invalid_state", "cross-source checkpoint")
    summaries = payload.get("summary_ids")
    units = payload.get("unit_ids")
    if not isinstance(summaries, list) or not isinstance(units, list):
        raise IncrementalJsonlError("invalid_state", "manifest must be lists")
    if len(summaries) != len(set(summaries)) or len(units) != len(set(units)):
        raise IncrementalJsonlError("invalid_state", "duplicate manifest ids")
    return payload


def validate_rollback(payload: dict, *, source_path: str | None = None) -> dict:
    if not isinstance(payload, dict):
        raise IncrementalJsonlError("recovery_unproven", "rollback is not an object")
    if payload.get("version") != ROLLBACK_VERSION:
        raise IncrementalJsonlError("recovery_unproven", "unsupported rollback version")
    required = ("summaries", "units", "export_lines", "processed_preimage", "source_path")
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
) -> str:
    """Pure eligibility decision. Does not construct checkpoint machinery."""
    if not enabled:
        return "disabled"
    if detected_format != ELIGIBLE_FORMAT:
        return "ineligible_format"
    if force_reindex or supersede_on_reindex:
        return "incremental_force_unsupported"
    if checkpoint is None:
        if _path_has_processed_entry(processed, path_key) or chroma_row_count > 0:
            return "bootstrap_required"
        return "eligible_new_source"
    try:
        validate_checkpoint(checkpoint, source_path=path_key)
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
        boundary: IsolationBoundary,
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
    ):
        if os.environ.get("CONVMEM_INCREMENTAL_ROOT"):
            IsolationBoundary.require_fake_provider("deterministic-fake")
        self.boundary = boundary
        self.source = boundary.resolve_mutable(source, label="source fixture")
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
        index = self.cfg.get("index") if isinstance(self.cfg.get("index"), dict) else {}
        self.chunk_size = int(chunk_size if chunk_size is not None else index.get("chunk_size", 2))
        self.overlap = int(overlap if overlap is not None else index.get("chunk_overlap", 0))
        distill_cfg = self.cfg.get("distill") if isinstance(self.cfg.get("distill"), dict) else {}
        self.min_confidence = float(
            min_confidence if min_confidence is not None else distill_cfg.get("min_confidence", 0.6)
        )
        self.models = models or dict(self.cfg.get("models") or {})
        self.path_key = str(self.source)
        self.source_id = source_state_id(self.path_key)
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
        )
        self.last_result: IncrementalRunResult | None = None
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
        return validate_checkpoint(payload, source_path=self.path_key)

    def _session(self):
        from chroma_write_store import production_chroma_write_session

        return production_chroma_write_session(
            self.config_path,
            lock_path=self.writer_lock,
            attest_dir=self.attest_dir,
            census_dir=self.census_dir,
            entrypoint="incremental_jsonl.apply",
        )

    def _chroma_row_count(self) -> int:
        chroma_dir = Path(self.cfg["index"]["chroma_dir"])
        if not chroma_dir.exists():
            return 0
        with self._session() as session:
            return len(session.store.ids_for_source(SUMMARIES, self.path_key)) + len(
                session.store.ids_for_source(UNITS, self.path_key)
            )

    def _processed(self) -> dict:
        if self.processed_override is not None:
            return self.processed_override
        return load_processed(str(self.cfg["index"]["processed_log"]))

    def _capture(self, transaction_id: str) -> dict:
        parser = get_parser(self.source)
        if detect_format(self.source) != ELIGIBLE_FORMAT:
            raise IsolationViolation("incremental route supports only jsonl_kiro_session")
        if parser is None or parser.__module__ != "adapters.kiro_session_jsonl":
            raise IsolationViolation("normal adapter dispatch did not select Kiro JSONL")
        snapshot_dir = self.paths["snapshots"] / transaction_id
        snapshot_path = snapshot_dir / "messages.jsonl"

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
            sibling = self.source.parent / "session.json"
            if sibling.is_file() and not sibling.is_symlink():
                _atomic_bytes(snapshot_dir / "session.json", sibling.read_bytes())

        self._transition("source_snapshot_publish", publish)
        view = parse_complete_prefix(str(snapshot_path), raw=prefix)
        if len(view.messages) != len(view.byte_ranges):
            raise IncrementalJsonlError("invalid_state", "adapter output/byte-range disagreement")
        snapshot = {
            "raw": prefix,
            "complete_boundary": view.complete_boundary,
            "prefix_sha256": view.prefix_sha256,
            "messages": view.messages,
            "byte_ranges": view.byte_ranges,
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
            sibling = self.source.parent / "session.json"
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

    def _load_prepared(self, key: str, *, expected: dict) -> dict | None:
        path = self._prepared_path(key)
        payload = _read_json(path)
        if payload is None:
            return None
        try:
            if payload.get("version") != PREPARED_VERSION:
                return None
            if payload.get("source_identity") != self.source_id:
                return None
            if payload.get("transform_fingerprint") != self.transform_fingerprint:
                return None
            if payload.get("chunk_start") != expected["chunk_start"]:
                return None
            if payload.get("input_digest") != expected["input_digest"]:
                return None
            if not payload.get("complete"):
                return None
            embeddings = [payload["summary_embedding"]] + [
                unit["embedding"] for unit in payload.get("units", [])
            ]
            for embedding in embeddings:
                if len(embedding) != self.embed_dimension:
                    return None
            body = {name: value for name, value in payload.items() if name != "digest"}
            if payload.get("digest") != _sha(_canonical_json(body)):
                return None
        except (TypeError, KeyError, ValueError):
            return None
        return payload

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

    def _build_frontier(self, messages: list[dict], frontier: int) -> tuple[list[dict], int]:
        chunks = chunk_messages(messages, self.chunk_size, self.overlap)
        prepared: list[dict] = []
        reused = 0
        for chunk in chunks:
            expected = {
                "chunk_start": int(chunk["start_offset"]),
                "input_digest": self._chunk_input_digest(chunk),
            }
            key = self._prepared_key(expected["chunk_start"], expected["input_digest"])
            cached = self._load_prepared(key, expected=expected)
            if cached is not None:
                prepared.append(cached)
                reused += 1
                continue
            built = build_chunk_artifact(
                chunk=chunk,
                path=self.path_key,
                path_key=self.path_key,
                models=self.models,
                tool="kiro",
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
        keep_summaries: set[str],
        keep_units: set[str],
    ) -> tuple[int, int, list]:
        from ingest_dedupe import evaluate_ingest_batch
        from provenance_binding import provenance_identity

        chunks = 0
        units = 0
        events: list = []
        with self._session() as session:
            for artifact in prepared:
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
                        session.store.add_unit(
                            projection_unit["id"], doc, unit_embedding, projection_meta
                        )
                        written += 1
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
        return chunks, units, events

    def _snapshot_before_images(self) -> dict:
        with self._session() as session:
            summaries = session.store.snapshot_source_rows(SUMMARIES, self.path_key)
            units = session.store.snapshot_source_rows(UNITS, self.path_key)
        export_path = Path(self.cfg["index"]["units_export"])
        export_lines = []
        if export_path.is_file():
            for line in export_path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    export_lines.append(("keep", line))
                    continue
                if isinstance(row, dict) and row.get("source_path") == self.path_key:
                    export_lines.append(("source", line))
                else:
                    export_lines.append(("keep", line))
        processed = self._processed()
        processed_preimage = {
            key: value
            for key, value in processed.items()
            if isinstance(value, dict) and value.get("path") == self.path_key
        }
        return {
            "version": ROLLBACK_VERSION,
            "summaries": summaries,
            "units": units,
            "export_lines": export_lines,
            "processed_preimage": processed_preimage,
            "source_path": self.path_key,
            "state_files": self._capture_state_files(),
            "prepared_files": self._capture_prepared_files(),
            "dedupe_files": self._capture_dedupe_files(),
        }

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

    def _capture_dedupe_files(self) -> dict[str, str | None]:
        data_dir = Path(self.cfg["index"]["chroma_dir"]).expanduser().parent
        return {
            "dedupe_queue.jsonl": self._file_preimage(data_dir / "dedupe_queue.jsonl"),
            "ingest_duplicate_suppressions.jsonl": self._file_preimage(
                data_dir / "ingest_duplicate_suppressions.jsonl"
            ),
        }

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

    def _restore_state_files(self, state_files: dict | None) -> None:
        if not state_files:
            return
        for name in ("checkpoint", "transaction", "rollback"):
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
        data_dir = Path(self.cfg["index"]["chroma_dir"]).expanduser().parent
        for name in ("dedupe_queue.jsonl", "ingest_duplicate_suppressions.jsonl"):
            if name not in dedupe_files:
                continue
            self._restore_file_preimage(data_dir / name, dedupe_files[name])

    def _restore_before_images(self, rollback: dict) -> None:
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
        self._restore_export(rollback.get("export_lines") or [])
        self._restore_processed(rollback.get("processed_preimage") or {})
        self._restore_state_files(rollback.get("state_files"))
        self._restore_prepared_files(rollback.get("prepared_files"))
        self._restore_dedupe_files(rollback.get("dedupe_files"))

    def _restore_export(self, export_lines: list) -> None:
        export_path = Path(self.cfg["index"]["units_export"])
        if not export_lines and not export_path.exists():
            return
        kept = []
        if export_path.is_file():
            for line in export_path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    kept.append(line)
                    continue
                if isinstance(row, dict) and row.get("source_path") == self.path_key:
                    continue
                kept.append(line)
        restored = [line for kind, line in export_lines if kind == "source"]
        foreign = [line for kind, line in export_lines if kind == "keep"]
        # Preserve unrelated current lines plus the preimage source lines.
        merged = foreign + kept
        seen = set(merged)
        output = list(merged)
        for line in restored:
            if line not in seen:
                output.append(line)
        from purge_locks import export_flock

        with export_flock(self.cfg):
            _atomic_bytes(export_path, ("".join(f"{line}\n" for line in output)).encode("utf-8"))

    def _reconcile_export(self, prepared: list[dict]) -> None:
        from purge_locks import export_flock

        export_path = Path(self.cfg["index"]["units_export"])

        def reconcile() -> None:
            existing: list[str] = []
            if export_path.is_file():
                for line in export_path.read_text(encoding="utf-8").splitlines():
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        existing.append(line)
                        continue
                    if isinstance(row, dict) and row.get("source_path") == self.path_key:
                        continue
                    existing.append(line)
            for artifact in prepared:
                for row in artifact["units"]:
                    existing.append(json.dumps(row["unit"], separators=(",", ":")))
            with export_flock(self.cfg):
                _atomic_bytes(
                    export_path,
                    ("".join(f"{line}\n" for line in existing)).encode("utf-8"),
                )

        self._transition("export_reconcile", reconcile)

    def _reconcile_dedupe(self, transaction_id: str, events: list) -> tuple[int, int]:
        from ingest_dedupe import persist_ingest_dedupe, IngestDedupeResult

        exact = []
        semantic = []
        for result in events:
            for row in result.exact_suppressions:
                event = dict(row)
                event["transaction_id"] = transaction_id
                event["event_id"] = _sha(
                    f"{transaction_id}:{row.get('suppressed_id')}:{row.get('matched_id')}"
                )
                exact.append(event)
            for row in result.semantic_candidates:
                event = dict(row)
                event["transaction_id"] = transaction_id
                event["event_id"] = _sha(
                    f"{transaction_id}:{row.get('id_a')}:{row.get('id_b')}"
                )
                semantic.append(event)
        combined = IngestDedupeResult(exact_suppressions=exact, semantic_candidates=semantic)

        def reconcile() -> None:
            persist_ingest_dedupe(self.cfg, combined)

        self._transition("dedupe_reconcile", reconcile)
        return len(exact), len(semantic)

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
            adapter_format=ELIGIBLE_FORMAT,
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
    ) -> IncrementalRunResult:
        from ingest import _path_is_excluded
        from purge_locks import source_flock

        keep_summaries = {item["doc_id"] for item in prepared}
        keep_units = {row["id"] for item in prepared for row in item["units"]}
        generation = _sha(
            "jsonl-kiro-generation-v1:"
            f"{self.source_id}:{snapshot['prefix_sha256']}:{snapshot['complete_boundary']}:"
            f"{self.transform_fingerprint}"
        )
        candidate_ids = sorted(keep_summaries | keep_units)
        self._revalidate_live_prefix(snapshot)
        with source_flock(self.cfg, self.path_key):
            if _path_is_excluded(self._processed(), self.path_key):
                return self._refusal("excluded", snapshot=snapshot)
            rollback = self._snapshot_before_images()
            rollback["candidate_ids"] = candidate_ids
            self._write_rollback(rollback)
            self._write_transaction(
                {
                    "version": TRANSACTION_VERSION,
                    "transaction_id": transaction_id,
                    "phase": "APPLYING",
                    "source_path": self.path_key,
                    "source_identity": self.source_id,
                    "generation": generation,
                    "prepared_keys": [item["cache_key"] for item in prepared],
                    "candidate_ids": candidate_ids,
                    "generation_identity": snapshot["generation_identity"],
                    "complete_boundary": snapshot["complete_boundary"],
                    "prefix_sha256": snapshot["prefix_sha256"],
                    "session_meta_digest": snapshot["session_meta_digest"],
                }
            )
            chunks, units, events = self._apply_prepared(prepared, keep_summaries, keep_units)
            self._revalidate_live_prefix(snapshot)
            checkpoint = {
                "version": CHECKPOINT_VERSION,
                "commit_state": "complete",
                "adapter_format": ELIGIBLE_FORMAT,
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
                "fallback_reason": fallback,
            }
            self._write_checkpoint(checkpoint)
            self._reconcile_export(prepared)
            exact, semantic = self._reconcile_dedupe(transaction_id, events)
        committed = self._publish_processed(snapshot["prefix_sha256"], chunks, units)
        self._cleanup(snapshot["snapshot_dir"])
        result = IncrementalRunResult(
            outcome="committed" if committed else "excluded_after_checkpoint",
            mode=mode,
            fallback_reason=fallback,
            adapter_format=ELIGIBLE_FORMAT,
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

    def _roll_forward(self, transaction: dict) -> IncrementalRunResult:
        rollback_path = self.paths["rollback"]
        if rollback_path.is_file():
            rollback = _read_json(rollback_path)
            if rollback is None:
                raise IncrementalJsonlError("recovery_unproven", "rollback journal corrupt")
            rollback = validate_rollback(rollback, source_path=self.path_key)
        else:
            rollback = None
        snapshot_dirs = list(self.paths["snapshots"].glob("*"))
        if not snapshot_dirs:
            raise IncrementalJsonlError("recovery_unproven", "missing snapshot")
        snapshot_dir = Path(snapshot_dirs[0])
        snapshot_path = snapshot_dir / "messages.jsonl"
        raw = snapshot_path.read_bytes()
        view = parse_complete_prefix(str(snapshot_path), raw=raw)
        snapshot = {
            "raw": raw,
            "complete_boundary": view.complete_boundary,
            "prefix_sha256": view.prefix_sha256,
            "messages": view.messages,
            "byte_ranges": view.byte_ranges,
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
            if keys:
                for key in keys:
                    payload = _read_json(self._prepared_path(key))
                    if not payload or not payload.get("complete"):
                        raise IncrementalJsonlError(
                            "recovery_unproven", "prepared artifact missing"
                        )
                    prepared.append(payload)
                reused = len(prepared)
            else:
                prior_count = 0
                try:
                    prior_cp = self.checkpoint()
                    prior_count = int(prior_cp.get("record_count") or 0) if prior_cp else 0
                except IncrementalJsonlError:
                    prior_count = 0
                frontier = frontier_start(prior_count, self.chunk_size, self.overlap)
                prepared, reused = self._build_frontier(snapshot["messages"], frontier)
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
                mode="replay_forward",
            )
        except SourceCaptureError:
            if rollback is None:
                return self._refusal("source_moved", mode="aborted", snapshot=snapshot)
            self._restore_before_images(rollback)
            self._cleanup(snapshot_dir)
            return self._refusal("rolled_back", mode="rollback", snapshot=snapshot)
        except IncrementalJsonlError:
            if rollback is None:
                raise
            self._restore_before_images(rollback)
            self._cleanup(snapshot_dir)
            return self._refusal("rolled_back", mode="rollback", snapshot=snapshot)

    def run(self) -> IncrementalRunResult:
        if not self.enabled:
            return self._refusal("disabled")
        detected = detect_format(self.source)
        if detected != ELIGIBLE_FORMAT:
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
                return self._roll_forward(existing_tx)
            transaction_id = uuid.uuid4().hex
            snapshot = self._capture(transaction_id)
            checkpoint = None
            try:
                checkpoint = self.checkpoint()
            except IncrementalJsonlError:
                return self._refusal("invalid_state", snapshot=snapshot)
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
            )
            if outcome in {"bootstrap_required", "invalid_state"}:
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
                    adapter_format=ELIGIBLE_FORMAT,
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
            prepared, reused = self._build_frontier(snapshot["messages"], frontier)
            self._write_transaction(
                {
                    "version": TRANSACTION_VERSION,
                    "transaction_id": transaction_id,
                    "phase": "PREPARING",
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
            mode = "full_rebuild_fallback" if continuity and continuity != "initial_full" else (
                "initial_full" if continuity == "initial_full" else "incremental"
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
    _ = (idx, path_key, tool, units_export, verbose)
    settings = incremental_jsonl_settings(cfg)
    if not settings.enabled:
        return None
    if detected_format != ELIGIBLE_FORMAT:
        return None
    if os.environ.get("CONVMEM_INCREMENTAL_ROOT"):
        boundary = IsolationBoundary.from_environment()
        coordinator = IncrementalJsonlCoordinator(
            boundary,
            path,
            cfg=cfg,
            enabled=True,
            models=models,
            chunk_size=chunk_size,
            overlap=overlap,
            min_confidence=min_confidence,
            force_reindex=force_reindex,
            supersede_on_reindex=supersede_on_reindex,
            file_hash=file_hash,
            processed=processed,
        )
        result = coordinator.run()
        return result.ingest_tuple()
    # Live activation is unauthorized for this Execute; refuse rather than
    # constructing production-state machinery outside a hermetic root.
    if force_reindex or supersede_on_reindex:
        return "skipped", 0, 0, 0, 0
    return "skipped", 0, 0, 0, 0
