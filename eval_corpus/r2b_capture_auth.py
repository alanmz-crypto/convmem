"""R2b capture authorization — binder-only HMAC capability + materialization.

Mirrors the R2a hardened capability design: opaque _R2bCapability sealed by HMAC
over manifest_path + approval_digest. Write-time code re-derives every binding
from the approved manifest.
"""
# pylint: disable=too-many-lines

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from eval_corpus.run_manifest import (
    CAPTURE_FIELDS,
    _EVAL_ROOT_MARKER,
    _load_and_validate_manifest,
    _require_exact_fields,
    approval_sidecar_path,
    assert_manifest_file_matches_approval,
    assert_operation_allowed,
    canonical_manifest_body_sha256,
    load_run_manifest,
    validate_r2b_manifest_schema,
)

_AUTH_ROOT_MARKER = "/.local/share/convmem/authorizations/r2b"
_MAX_SNAPSHOT_AGE_SECONDS = 3600

# Sentinel: callers must not pass None to skip live gates — use an explicit no-op
# only in hermetic tests (e.g. restic_gate_fn=lambda: None).
_USE_LIVE_DEFAULT = object()

SnapshotRecomputeFn = Callable[..., dict[str, Any]]


def _default_restic_gate() -> None:
    from restic_gate import ensure_chroma_snapshot_for_live_write

    ensure_chroma_snapshot_for_live_write()


@dataclass(frozen=True)
class R2bBindings:  # pylint: disable=too-many-instance-attributes
    """Bindings re-derived from an approved R2b manifest (never from grant fields)."""

    capture_dir: Path
    export: Path
    processed: Path
    chroma_dir: Path
    query_set: Path
    query_set_sha256: str
    run_id: str
    merged_harness_sha256: str
    manifest_path: Path
    source_snapshot: dict[str, Any]
    authorization_body_sha256: str


def _has_symlink_component(path: Path) -> bool:
    """True if path or any ancestor is a symlink."""
    parts = path.parts
    current = Path(parts[0])
    for part in parts[1:]:
        current = current / part
        try:
            if current.is_symlink():
                return True
        except OSError:
            pass
    return False


def _validate_snapshot_freshness(snapshot: dict[str, Any]) -> None:
    """Reject naive, future, or stale (>1h) snapshot timestamps."""
    ts_str = snapshot.get("snapshot_timestamp", "")
    try:
        dt = datetime.fromisoformat(ts_str)
    except (ValueError, TypeError) as exc:
        raise PermissionError(
            f"snapshot_timestamp not valid ISO-8601: {ts_str}"
        ) from exc
    if dt.tzinfo is None:
        raise PermissionError("snapshot_timestamp must be timezone-aware")
    now = datetime.now(timezone.utc)
    if dt > now:
        raise PermissionError("snapshot_timestamp is in the future")
    age = (now - dt).total_seconds()
    if age > _MAX_SNAPSHOT_AGE_SECONDS:
        raise PermissionError(
            f"snapshot_timestamp is {age:.0f}s old "
            f"(max {_MAX_SNAPSHOT_AGE_SECONDS}s)"
        )


def canonical_source_snapshot_sha256(snapshot: dict[str, Any]) -> str:
    """SHA-256 of source_snapshot serialized with canonical JSON rules."""
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compare_source_snapshots(
    approved: dict[str, Any], recomputed: dict[str, Any]
) -> None:
    """Verify recomputed snapshot matches approved snapshot (except timestamp)."""
    compare_keys = (
        "export_sha256",
        "processed_state",
        "processed_sha256",
        "chroma_collection_name",
        "chroma_collection_id",
        "chroma_extracted_unit_count",
        "chroma_sorted_id_hash",
        "chroma_capture_slice_sha256",
    )
    for key in compare_keys:
        approved_val = approved.get(key)
        recomputed_val = recomputed.get(key)
        if approved_val != recomputed_val:
            raise PermissionError(
                f"source_snapshot.{key} mismatch: "
                f"approved={approved_val!r}, recomputed={recomputed_val!r}"
            )


def _validate_r2b_paths(
    *,
    manifest_paths: dict[str, Any],
    runtime: Mapping[str, Any],
    run_id: str,
    manifest_path: Path,
) -> None:
    """Lexical path equality + resolved containment for R2b."""
    for key in ("export", "processed", "capture_dir", "chroma_dir", "query_set"):
        val = str(manifest_paths.get(key, ""))
        if not val.startswith("/"):
            raise PermissionError(f"R2b paths.{key} must be absolute")
        if "~" in val or "/./" in val or "/../" in val or "//" in val:
            raise PermissionError(
                f"R2b paths.{key} must be canonical (no ~, ., .., //)"
            )

    capture_dir_str = str(manifest_paths["capture_dir"])
    resolved_capture = Path(capture_dir_str).resolve(strict=False)
    if _EVAL_ROOT_MARKER not in str(resolved_capture):
        raise PermissionError("R2b capture_dir must be under eval root")
    parts = resolved_capture.parts
    if len(parts) < 2 or parts[-1] != "capture" or parts[-2] != run_id:
        raise PermissionError(
            f"R2b capture_dir must end with {run_id}/capture"
        )

    resolved_manifest_parent = Path(manifest_path).resolve(strict=False).parent
    if _AUTH_ROOT_MARKER not in str(resolved_manifest_parent):
        raise PermissionError("R2b manifest must be under authorization root")
    if resolved_manifest_parent.name != run_id:
        raise PermissionError(
            f"R2b manifest parent must be named {run_id}"
        )

    for key in CAPTURE_FIELDS:
        manifest_val = str(manifest_paths.get(key, ""))
        runtime_val = str(runtime.get(key, ""))
        if manifest_val != runtime_val:
            raise PermissionError(
                f"R2b {key}: runtime must be lexically equal to manifest "
                f"({runtime_val!r} vs {manifest_val!r})"
            )
        resolved_m = Path(manifest_val).resolve(strict=False)
        resolved_r = Path(runtime_val).resolve(strict=False)
        if resolved_m != resolved_r:
            raise PermissionError(f"R2b {key}: resolved path mismatch")


def _check_no_symlinks(
    manifest_path: Path,
    manifest_paths: dict[str, Any],
    runtime: Mapping[str, Any],
) -> None:
    """Reject paths with symlink components (manifest and runtime)."""
    to_check = [Path(manifest_path).resolve(strict=False)]
    sidecar = approval_sidecar_path(Path(manifest_path))
    if sidecar.exists():
        to_check.append(sidecar.resolve(strict=False))
    for key in ("export", "processed", "chroma_dir", "capture_dir", "query_set"):
        for raw in (manifest_paths.get(key), runtime.get(key)):
            if raw is None:
                continue
            p = Path(str(raw))
            if p.exists() or key == "capture_dir":
                # capture_dir must not exist, but parents are checked below
                if p.exists():
                    to_check.append(p)
                for parent in p.parents:
                    if parent.exists() and parent != Path(parent.anchor):
                        to_check.append(parent)
                        break

    for p in to_check:
        if _has_symlink_component(p):
            raise PermissionError(
                f"R2b rejects symlink in path: {p}"
            )


def _open_query_set_no_follow(path: Path) -> int:
    """Open an absolute query path by walking every component no-follow."""
    if not path.is_absolute():
        raise PermissionError("R2b query_set path must be absolute")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PermissionError("R2b query_set path must be canonical")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_fd = os.open(path.anchor, flags)
    try:
        components = list(path.parts[1:])
        if not components:
            raise PermissionError("R2b query_set path must name a file")
        for component in components[:-1]:
            next_fd = os.open(
                component,
                flags,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        file_fd = os.open(
            components[-1],
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=current_fd,
        )
        os.close(current_fd)
        return file_fd
    except Exception:
        os.close(current_fd)
        raise


def read_immutable_query_set(path: Path | str) -> dict[str, Any]:
    """Read/hash one stable query-file snapshot without reopening its path."""
    query_path = Path(path)
    if not query_path.is_absolute():
        raise PermissionError("R2b query_set path must be absolute")
    if "~" in str(query_path) or "/./" in str(query_path) or "/../" in str(query_path) or "//" in str(query_path):
        raise PermissionError("R2b query_set path must be canonical")

    file_fd: int | None = None
    try:
        file_fd = _open_query_set_no_follow(query_path)
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode):
            raise PermissionError("R2b query_set must be a regular file")
        if before.st_nlink != 1:
            raise PermissionError(
                f"R2b query_set must have link_count=1, got {before.st_nlink}"
            )
        chunks: list[bytes] = []
        while True:
            chunk = os.read(file_fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        data = b"".join(chunks)
        after = os.fstat(file_fd)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
            raise PermissionError("R2b query_set changed while being read")
        path_info = query_path.lstat()
        if stat.S_ISLNK(path_info.st_mode) or not stat.S_ISREG(path_info.st_mode):
            raise PermissionError("R2b query_set path is no longer a regular file")
        if path_info.st_nlink != 1:
            raise PermissionError("R2b query_set path became hard-linked")
        if any(
            getattr(path_info, field) != getattr(before, field)
            for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        ):
            raise PermissionError("R2b query_set path identity changed while being read")
        return {
            "path": str(query_path),
            "bytes": data,
            "sha256": hashlib.sha256(data).hexdigest(),
            "device": before.st_dev,
            "inode": before.st_ino,
            "size": before.st_size,
            "link_count": before.st_nlink,
        }
    except OSError as exc:
        raise PermissionError(f"cannot read R2b query_set safely: {query_path}: {exc}") from exc
    finally:
        if file_fd is not None:
            os.close(file_fd)


def _verify_query_set_binding(manifest_paths: Mapping[str, Any], expected_sha256: str) -> None:
    """Require the live query path to match the exact approved manifest SHA."""
    snapshot = read_immutable_query_set(Path(str(manifest_paths["query_set"])))
    if snapshot["sha256"] != expected_sha256:
        raise PermissionError(
            "R2b query_set_sha256 does not match the bytes at the approved query_set path"
        )
    try:
        from eval_corpus.query_set import parse_query_set_jsonl_bytes

        parse_query_set_jsonl_bytes(snapshot["bytes"])
    except ValueError as exc:
        raise PermissionError(
            "R2b query_set bytes are not valid UTF-8 JSONL"
        ) from exc


def _derive_r2b_bindings(
    manifest: dict[str, Any], *, manifest_path: Path
) -> R2bBindings:
    """Derive every R2b binding from the approved manifest body."""
    paths = manifest["paths"]
    body_digest = canonical_manifest_body_sha256(manifest)
    return R2bBindings(
        capture_dir=Path(paths["capture_dir"]),
        export=Path(paths["export"]),
        processed=Path(paths["processed"]),
        chroma_dir=Path(paths["chroma_dir"]),
        query_set=Path(paths["query_set"]),
        query_set_sha256=str(manifest["query_set_sha256"]),
        run_id=manifest["run_id"],
        merged_harness_sha256=str(manifest["merged_harness_sha256"]),
        manifest_path=Path(manifest_path).resolve(strict=False),
        source_snapshot=dict(manifest["source_snapshot"]),
        authorization_body_sha256=body_digest,
    )


def _build_r2b_capability_api() -> tuple[Any, Any]:
    """Closure-held MAC key + binder-only mint (no raw issuer export).

    Returns ``(bind_r2b_capture, authenticate)``.
    MAC seals ``manifest_path`` + approval digest so path-preserving retargets fail.
    """
    mac_key = secrets.token_bytes(32)

    class _R2bCapability:
        """Opaque authenticated capability. Construct only via binder mint."""

        __slots__ = ("_manifest_path", "_approval_digest", "_mac", "_frozen")

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise TypeError("R2bCapability is binder-issued only")

        def __setattr__(self, name: str, value: Any) -> None:
            if getattr(self, "_frozen", False):
                raise AttributeError("R2bCapability is immutable")
            object.__setattr__(self, name, value)

    def _mac_message(path: Path, approval_digest: str) -> bytes:
        return f"{path}\0{approval_digest}".encode("utf-8")

    def authenticate(obj: Any) -> Path:
        if type(obj) is not _R2bCapability:  # pylint: disable=unidiomatic-typecheck
            raise PermissionError(
                "eval-root capture requires a binder-issued R2b capability"
            )
        path = object.__getattribute__(obj, "_manifest_path")
        digest = object.__getattribute__(obj, "_approval_digest")
        mac = object.__getattribute__(obj, "_mac")
        expected = hmac.new(
            mac_key, _mac_message(path, digest), "sha256"
        ).digest()
        if not hmac.compare_digest(mac, expected):
            raise PermissionError("forged or corrupted R2b capability")
        side = approval_sidecar_path(Path(path))
        if not side.is_file():
            raise PermissionError(
                "R2b capability requires approval sidecar at authenticate"
            )
        live = side.read_text(encoding="utf-8").strip().split()[0].lower()
        if not hmac.compare_digest(live, digest):
            raise PermissionError(
                "R2b capability sealed to a different approval digest "
                "(manifest/sidecar retarget refused)"
            )
        return Path(path)

    def _bind_impl(
        *,
        run_manifest_path: Path,
        runtime: Mapping[str, Any],
        snapshot_recompute_fn: SnapshotRecomputeFn,
        restic_gate_fn: Any = _USE_LIVE_DEFAULT,
    ) -> Any:
        """Authorize R2b capture; return an immutable authenticated capability.

        The capability seals manifest path + approval digest. Write-time code
        must re-verify the sidecar and re-derive every binding from that manifest.

        ``snapshot_recompute_fn`` is required (trusted recompute — typically
        ``eval_corpus.capture.recompute_source_snapshot``). Hermetic tests may
        pass ``restic_gate_fn=lambda: None``.
        """
        _require_exact_fields("capture", CAPTURE_FIELDS, runtime)
        path = Path(run_manifest_path)
        manifest = _load_and_validate_manifest(path)

        if str(manifest.get("authorization_phase") or "") != "r2b":
            raise PermissionError(
                'bind_r2b_capture requires authorization_phase="r2b"'
            )
        assert_operation_allowed(manifest, "capture")

        errs = validate_r2b_manifest_schema(manifest)
        if errs:
            raise PermissionError("; ".join(errs))

        if restic_gate_fn is _USE_LIVE_DEFAULT:
            _default_restic_gate()
        elif restic_gate_fn is not None:
            restic_gate_fn()

        run_id = manifest["run_id"]
        manifest_paths = manifest["paths"]

        _validate_r2b_paths(
            manifest_paths=manifest_paths,
            runtime=runtime,
            run_id=run_id,
            manifest_path=path,
        )
        _check_no_symlinks(path, manifest_paths, runtime)

        _verify_query_set_binding(
            manifest_paths, str(manifest["query_set_sha256"])
        )

        source_snapshot = manifest["source_snapshot"]
        _validate_snapshot_freshness(source_snapshot)

        recomputed = snapshot_recompute_fn(
            export=Path(manifest_paths["export"]),
            processed=Path(manifest_paths["processed"]),
            chroma_dir=Path(manifest_paths["chroma_dir"]),
        )
        compare_source_snapshots(source_snapshot, recomputed)

        capture_dir = Path(manifest_paths["capture_dir"])
        if capture_dir.exists():
            raise PermissionError(
                "R2b capture_dir must not exist before authorization"
            )

        approval_digest = (
            str(manifest.get("ryan_approved_manifest_sha256") or "")
            .strip()
            .lower()
        )
        sealed_path = Path(path).resolve(strict=False)
        if len(approval_digest) != 64 or any(
            c not in "0123456789abcdef" for c in approval_digest
        ):
            raise PermissionError(
                "R2b capability requires a 64-hex approval digest"
            )
        mac = hmac.new(
            mac_key, _mac_message(sealed_path, approval_digest), "sha256"
        ).digest()
        obj = object.__new__(_R2bCapability)
        object.__setattr__(obj, "_manifest_path", sealed_path)
        object.__setattr__(obj, "_approval_digest", approval_digest)
        object.__setattr__(obj, "_mac", mac)
        object.__setattr__(obj, "_frozen", True)
        return obj

    return _bind_impl, authenticate


bind_r2b_capture, _authenticate_r2b_capability = _build_r2b_capability_api()


def is_r2b_eval_root_grant(obj: Any) -> bool:
    """True only for binder-issued authenticated R2b capabilities."""
    try:
        _authenticate_r2b_capability(obj)
    except PermissionError:
        return False
    return True


def materialize_r2b_capability(capability: Any) -> R2bBindings:
    """Authenticate capability, re-verify sidecar, re-derive all bindings."""
    manifest_path = _authenticate_r2b_capability(capability)
    manifest = load_run_manifest(manifest_path)
    assert_manifest_file_matches_approval(manifest_path, manifest)
    assert_operation_allowed(manifest, "capture")
    errs = validate_r2b_manifest_schema(manifest)
    if errs:
        raise PermissionError("; ".join(errs))
    _verify_query_set_binding(
        manifest["paths"], str(manifest["query_set_sha256"])
    )
    return _derive_r2b_bindings(manifest, manifest_path=manifest_path)


def materialize_r2b_write_authorization(
    capability: Any,
    *,
    snapshot_recompute_fn: SnapshotRecomputeFn,
) -> R2bBindings:
    """Authenticate + re-verify everything before the first eval-root write.

    Does not trust caller-mutated grant fields — every value is re-derived from
    the approved manifest after sidecar verification. Callers must pass a trusted
    ``snapshot_recompute_fn`` (typically ``recompute_source_snapshot``).
    """
    bindings = materialize_r2b_capability(capability)
    manifest = load_run_manifest(bindings.manifest_path)

    source_snapshot = manifest["source_snapshot"]
    _validate_snapshot_freshness(source_snapshot)

    manifest_paths = manifest["paths"]
    _check_no_symlinks(
        bindings.manifest_path, manifest_paths, manifest_paths
    )
    _verify_query_set_binding(manifest_paths, bindings.query_set_sha256)

    recomputed = snapshot_recompute_fn(
        export=bindings.export,
        processed=bindings.processed,
        chroma_dir=bindings.chroma_dir,
    )
    compare_source_snapshots(source_snapshot, recomputed)

    if bindings.capture_dir.exists():
        raise PermissionError(
            "R2b capture_dir must not exist at materialization"
        )

    return bindings


__all__ = [
    "R2bBindings",
    "SnapshotRecomputeFn",
    "bind_r2b_capture",
    "canonical_source_snapshot_sha256",
    "compare_source_snapshots",
    "is_r2b_eval_root_grant",
    "materialize_r2b_capability",
    "materialize_r2b_write_authorization",
    "read_immutable_query_set",
]
