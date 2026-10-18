"""Codex bootstrap v3 writer mediation and coordination deferral (Arc #286 T3)."""

from __future__ import annotations

import contextvars
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator, Sequence

from bootstrap_codex_v2 import coordinator_source_state_id_for_path, v2_source_state_directory
from bootstrap_codex_v2_authority import CodexBootstrapV2AuthorityError, load_authority
from bootstrap_codex_v2_owner import require_owner_lock
from bootstrap_codex_v3_preparation_lease import SOURCE_WRITER_BUSY_CODE
from bootstrap_safety import BootstrapGrantError

if TYPE_CHECKING:
    from bootstrap_codex_v2_authority import AuthorityView

COORDINATION_DEFERRAL_EXIT = 93
COORDINATION_DEFERRAL_CODE = "coordination_deferral"
MAINTENANCE_DEFERRAL_OUTCOME = "maintenance_deferred"
_MARKER_PREFIX = "coordination_deferral:"
_MARKER_RE = re.compile(
    r"^coordination_deferral:(?P<source>.+):(?P<operation_id>[0-9a-f]{64}):(?P<revision>[0-9]+)$"
)

_SCOPE = contextvars.ContextVar("bootstrap_v3_writer_scope", default=None)
_OWNER_OPERATION = contextvars.ContextVar("bootstrap_v3_owner_operation", default=None)


class BootstrapWriterCoordinationError(BootstrapGrantError):
    """Writer mediation or scope violation."""


@dataclass(frozen=True)
class CoordinationDeferralSignal:
    canonical_source: str
    operation_id: str
    authority_revision: int

    def to_stderr_line(self) -> str:
        return (
            f"{_MARKER_PREFIX}{self.canonical_source}:"
            f"{self.operation_id}:{self.authority_revision}"
        )


@dataclass(frozen=True)
class WriterSourceScope:
    entrypoint: str
    affected_sources: tuple[str, ...]
    maintenance_unscoped: bool = False


@dataclass(frozen=True)
class ValidatedOwnerOperation:
    operation_id: str
    authority_revision: int
    grant_fingerprint_v2: str


def format_coordination_deferral(signal: CoordinationDeferralSignal) -> str:
    return signal.to_stderr_line()


def parse_coordination_deferral(message: str) -> CoordinationDeferralSignal | None:
    for line in message.splitlines():
        line = line.strip()
        parsed = _MARKER_RE.match(line)
        if not parsed:
            continue
        return CoordinationDeferralSignal(
            canonical_source=parsed.group("source"),
            operation_id=parsed.group("operation_id"),
            authority_revision=int(parsed.group("revision")),
        )
    return None


def validate_child_deferral_signal(
    signal: CoordinationDeferralSignal,
    *,
    launched_path: str,
    cfg: dict[str, Any] | None = None,
) -> None:
    launched = str(Path(launched_path).expanduser().resolve())
    if signal.canonical_source != launched:
        raise BootstrapWriterCoordinationError("coordination_deferral_path_mismatch")
    if cfg is None:
        return
    authority = authority_for_source(cfg, signal.canonical_source)
    if authority is None or not authority.reservation_active:
        raise BootstrapWriterCoordinationError("coordination_deferral_without_reservation")
    if authority.terminal:
        raise BootstrapWriterCoordinationError("coordination_deferral_terminal_authority")
    record_op = str(authority.record.get("operation_id") or "")
    if record_op != signal.operation_id:
        raise BootstrapWriterCoordinationError("coordination_deferral_operation_mismatch")
    if int(authority.revision) != int(signal.authority_revision):
        raise BootstrapWriterCoordinationError("coordination_deferral_revision_mismatch")


def _canonical_source(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def _configured_incremental_state_dir(cfg: dict[str, Any]) -> str:
    try:
        from config import incremental_jsonl_settings

        settings = incremental_jsonl_settings(cfg)
        raw = settings.state_dir
    except Exception:  # pylint: disable=broad-exception-caught
        settings = cfg.get("incremental_jsonl") or {}
        index_incr = (cfg.get("index") or {}).get("incremental_jsonl") or {}
        raw = (
            settings.get("state_dir")
            or index_incr.get("state_dir")
            or (cfg.get("index") or {}).get("incremental_state_dir")
        )
    if not raw:
        raise BootstrapWriterCoordinationError("incremental_state_root_missing")
    return str(raw)


def resolve_incremental_state_root(cfg: dict[str, Any]) -> Path:
    """Resolve configured incremental state root (production path or hermetic boundary)."""
    import os

    from incremental_jsonl_isolation import ISOLATION_ROOT_ENV, ISOLATION_TOKEN_ENV

    raw = _configured_incremental_state_dir(cfg)
    root_env = os.environ.get(ISOLATION_ROOT_ENV, "").strip()
    token_env = os.environ.get(ISOLATION_TOKEN_ENV, "").strip()
    if root_env and token_env:
        from bootstrap_codex_v2_owner import resolve_isolation_boundary

        boundary = resolve_isolation_boundary()
        return boundary.resolve_mutable(raw, label="incremental state")
    return Path(raw).expanduser().resolve()


def source_state_dir_for_path(cfg: dict[str, Any], source_path: str | Path) -> Path:
    from adapters.detect import detect_format
    from incremental_jsonl import source_state_id
    from incremental_jsonl_formats import get_format_spec

    path_key = _canonical_source(source_path)
    detected = detect_format(Path(path_key))
    spec = get_format_spec(detected)
    format_id = spec.format_id if spec is not None else detected
    state_id = source_state_id(path_key, format_id=format_id)
    return resolve_incremental_state_root(cfg) / state_id


def authority_for_source(
    cfg: dict[str, Any],
    source_path: str | Path,
    *,
    grant: dict[str, Any] | None = None,
):
    state_root = resolve_incremental_state_root(cfg)
    if grant is not None:
        state_dir = v2_source_state_directory(state_root, grant)
    else:
        state_id = coordinator_source_state_id_for_path(_canonical_source(source_path))
        state_dir = state_root / state_id
    try:
        return load_authority(state_dir)
    except CodexBootstrapV2AuthorityError:
        return None


def active_reservation_signal(
    cfg: dict[str, Any],
    source_path: str | Path,
    *,
    grant: dict[str, Any] | None = None,
) -> CoordinationDeferralSignal | None:
    authority = authority_for_source(cfg, source_path, grant=grant)
    if authority is None or not authority.reservation_active or authority.terminal:
        return None
    operation_id = str(authority.record.get("operation_id") or "")
    if len(operation_id) != 64:
        return None
    return CoordinationDeferralSignal(
        canonical_source=_canonical_source(source_path),
        operation_id=operation_id,
        authority_revision=authority.revision,
    )


def iter_active_reservations(cfg: dict[str, Any]) -> list[CoordinationDeferralSignal]:
    state_root = resolve_incremental_state_root(cfg)
    if not state_root.is_dir():
        return []
    signals: list[CoordinationDeferralSignal] = []
    for child in state_root.iterdir():
        if not child.is_dir():
            continue
        try:
            authority = load_authority(child)
        except CodexBootstrapV2AuthorityError:
            continue
        if authority is None or not authority.reservation_active or authority.terminal:
            continue
        snap = authority.record.get("grant_snapshot") or {}
        source = snap.get("source")
        if not source:
            continue
        operation_id = str(authority.record.get("operation_id") or "")
        if len(operation_id) != 64:
            continue
        signals.append(
            CoordinationDeferralSignal(
                canonical_source=_canonical_source(str(source)),
                operation_id=operation_id,
                authority_revision=authority.revision,
            )
        )
    return signals


def active_reservation_signal_from_authority(authority) -> CoordinationDeferralSignal | None:
    if authority is None or not authority.reservation_active or authority.terminal:
        return None
    snap = authority.record.get("grant_snapshot") or {}
    source = snap.get("source")
    if not source:
        return None
    operation_id = str(authority.record.get("operation_id") or "")
    if len(operation_id) != 64:
        return None
    return CoordinationDeferralSignal(
        canonical_source=_canonical_source(str(source)),
        operation_id=operation_id,
        authority_revision=int(authority.revision),
    )


@contextmanager
def legacy_source_preparation_participation(
    cfg: dict[str, Any], source_path: str | Path
) -> Iterator[None]:
    """Shared prep lease for ordinary legacy indexing through commit."""
    from adapters.detect import detect_format

    path = Path(_canonical_source(source_path))
    if detect_format(path) != "jsonl_codex_rollout":
        yield
        return
    state_dir = source_state_dir_for_path(cfg, path)
    from bootstrap_codex_v3_preparation_lease import legacy_shared_preparation_lease

    with legacy_shared_preparation_lease(state_dir):
        yield


def map_coordination_error_to_incremental(
    cfg: dict[str, Any], exc: BootstrapWriterCoordinationError, source_path: str | Path
) -> None:
    code = str(exc)
    if code == COORDINATION_DEFERRAL_CODE:
        raise_incremental_coordination_deferral(cfg, source_path)
    if code.startswith("stale_preparation_after_reservation"):
        from incremental_jsonl import IncrementalJsonlError

        raise IncrementalJsonlError("bootstrap_reservation_conflict", code) from exc
    raise exc


def recheck_reservation_before_commit(cfg: dict[str, Any], source_path: str | Path) -> None:
    signal = active_reservation_signal(cfg, source_path)
    if signal is None:
        return
    owner = _OWNER_OPERATION.get()
    if owner is not None and owner.operation_id == signal.operation_id:
        if owner.authority_revision == signal.authority_revision:
            return
        raise BootstrapWriterCoordinationError(
            "stale_preparation_after_reservation:authority_revision_mismatch"
        )
    raise BootstrapWriterCoordinationError(
        f"stale_preparation_after_reservation:{signal.operation_id}"
    )


def _validated_owner_operation(authority) -> ValidatedOwnerOperation:
    operation_id = str(authority.record.get("operation_id") or "")
    if len(operation_id) != 64:
        raise BootstrapWriterCoordinationError("owner_operation_identity_invalid")
    return ValidatedOwnerOperation(
        operation_id=operation_id,
        authority_revision=authority.revision,
        grant_fingerprint_v2=str(authority.record.get("grant_fingerprint_v2") or ""),
    )


def install_owner_operation_identity(authority) -> contextvars.Token:
    require_owner_lock()
    validated = _validated_owner_operation(authority)
    signal = active_reservation_signal_from_authority(authority)
    if signal is None:
        raise BootstrapWriterCoordinationError("owner_operation_without_reservation")
    if validated.operation_id != signal.operation_id:
        raise BootstrapWriterCoordinationError("owner_operation_identity_mismatch")
    if validated.authority_revision != signal.authority_revision:
        raise BootstrapWriterCoordinationError("owner_operation_revision_mismatch")
    return _OWNER_OPERATION.set(validated)


def clear_owner_operation_identity(token: contextvars.Token) -> None:
    _OWNER_OPERATION.reset(token)


@contextmanager
def owner_operation_context(authority) -> Iterator[ValidatedOwnerOperation]:
    require_owner_lock()
    validated = _validated_owner_operation(authority)
    token = _OWNER_OPERATION.set(validated)
    try:
        yield validated
    finally:
        _OWNER_OPERATION.reset(token)


@contextmanager
def writer_source_scope(scope: WriterSourceScope) -> Iterator[None]:
    token = _SCOPE.set(scope)
    try:
        yield
    finally:
        _SCOPE.reset(token)


def enforce_writer_scope(cfg: dict[str, Any], scope: WriterSourceScope) -> None:
    try:
        resolve_incremental_state_root(cfg)
    except BootstrapWriterCoordinationError:
        return
    if scope.maintenance_unscoped:
        if iter_active_reservations(cfg):
            raise BootstrapWriterCoordinationError(MAINTENANCE_DEFERRAL_OUTCOME)
        return
    if not scope.affected_sources:
        return
    owner = _OWNER_OPERATION.get()
    for source in scope.affected_sources:
        signal = active_reservation_signal(cfg, source)
        if signal is None:
            continue
        if owner is not None and owner.operation_id == signal.operation_id:
            continue
        raise BootstrapWriterCoordinationError(COORDINATION_DEFERRAL_CODE)


def should_defer_ordinary_writer(cfg: dict[str, Any], source_path: str | Path) -> bool:
    signal = active_reservation_signal(cfg, source_path)
    if signal is None:
        return False
    owner = _OWNER_OPERATION.get()
    if owner is not None and owner.operation_id == signal.operation_id:
        return False
    return True


def raise_incremental_coordination_deferral(cfg: dict[str, Any], source_path: str | Path) -> None:
    signal = active_reservation_signal(cfg, source_path)
    if signal is None:
        raise BootstrapWriterCoordinationError("coordination_deferral_without_reservation")
    from incremental_jsonl import IncrementalJsonlError

    raise IncrementalJsonlError(COORDINATION_DEFERRAL_CODE, signal.to_stderr_line())


def inspect_chroma_mutation_scope(
    cfg: dict[str, Any],
    *,
    method: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> WriterSourceScope:
    source_keys: list[str] = []
    for key in ("source_path", "path", "source"):
        if key in kwargs and kwargs[key]:
            source_keys.append(_canonical_source(str(kwargs[key])))
    if args and isinstance(args[0], str) and method in {
        "count_for_source_path",
        "ids_for_source",
        "preview_supersede_for_source",
        "snapshot_source_rows",
    }:
        source_keys.append(_canonical_source(args[0]))
    if method in {"add_summary", "add_unit"} and len(args) >= 4:
        meta = args[3]
        if isinstance(meta, dict) and meta.get("source_path"):
            source_keys.append(_canonical_source(str(meta["source_path"])))
    if source_keys:
        return WriterSourceScope(
            entrypoint=f"chroma.{method}",
            affected_sources=tuple(dict.fromkeys(source_keys)),
        )
    return WriterSourceScope(
        entrypoint=f"chroma.{method}",
        affected_sources=(),
        maintenance_unscoped=True,
    )
