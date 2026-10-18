# pylint: disable=cyclic-import,duplicate-code,too-many-locals,too-many-arguments,too-many-lines
"""Authoritative production write-store factory and C3 writer gate.

Production sessions take a shared writer lease, then load live config. Sink
injection uses the C1 strict validator. Callers must not pass cfg into the
production session API.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Literal, Mapping

from chroma_store import ChromaStore
from chroma_write_guard import GUARD_DIR_SUFFIX, ChromaWriteGuard, write_guard_enabled
import config as config_mod
from shadow_ledger import (
    SinkInjectionDecision,
    resolve_shadow_settings,
)
from shadow_sink import JsonlUnitMutationSink
from shadow_validation import validate_shadow_activation

WritePurpose = Literal["production", "test"]


class WriterBoundaryError(RuntimeError):
    """A production-authoritative mutation was attempted outside its gate."""

WRITER_GATE_PROTOCOL_VERSION = 1
DEFAULT_WRITER_LOCK = Path("~/.local/share/convmem/locks/chroma_writer_gate.lock")
DEFAULT_ATTEST_DIR = Path("~/.local/share/convmem/writer_attestations")

# Known long-lived writer services / timers (census; refreshed at C3 tip).
KNOWN_WRITER_SYSTEMD_UNITS: tuple[str, ...] = (
    "convmem-watch.service",
    "convmem-refine.service",
    "convmem-monitor.timer",
)

KNOWN_WRITER_CMDLINE_SIGNATURES: tuple[str, ...] = (
    "convmem watch",
    "convmem refine",
    "python.*watch.py",
    "python.*refine.py",
)


@dataclass(frozen=True)
class ProductionWriteSession:
    """Authoritative live config + store under a held shared writer lease."""

    store: ChromaStore
    live_cfg: dict[str, Any]
    decision: SinkInjectionDecision


@dataclass(frozen=True)
class WriterAttestation:  # pylint: disable=too-many-instance-attributes
    pid: int
    start_time: str
    code_revision: str
    git_revision: str
    executable: str
    entrypoint: str
    protocol_version: int
    recorded_at_utc: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "start_time": self.start_time,
            "code_revision": self.code_revision,
            "git_revision": self.git_revision,
            "executable": self.executable,
            "entrypoint": self.entrypoint,
            "protocol_version": self.protocol_version,
            "recorded_at_utc": self.recorded_at_utc,
        }


@dataclass(frozen=True)
class CaptureGeneration:
    """One exclusive capture/sealing boundary over the writer gate."""

    generation_id: str
    lock_path: Path
    started_at_utc: str


@dataclass
class _HeldWriterLease:
    """Thread-local nesting state for one shared mutation boundary."""

    lock_path: Path
    attestation: WriterAttestation
    depth: int = 1


@dataclass
class _ProcessWriterLeaseRegistry:
    """Process-wide active shared-lease count for one PID attestation file.

    Thread-local ``_HeldWriterLease.depth`` tracks same-thread re-entry only.
    ``active_count`` is the union of all overlapping same-process leases
    (cross-thread and nested) so intermediate exits never unlink the PID
    attestation while any lease remains active.
    """

    lock: threading.Lock
    active_count: int = 0
    attestation: WriterAttestation | None = None
    attest_dir: Path | None = None


_writer_tls = threading.local()
_process_writer_leases = _ProcessWriterLeaseRegistry(lock=threading.Lock())


def _held_writer_lease() -> _HeldWriterLease | None:
    return getattr(_writer_tls, "held", None)


def production_write_session_depth() -> int:
    """Nested shared writer lease depth (admission / attestation gate)."""
    held = _held_writer_lease()
    return int(held.depth) if held is not None else 0


def production_chroma_store_session_depth() -> int:
    """Opened production Chroma store sessions on this thread (lock-order enforcement)."""
    return int(getattr(_writer_tls, "chroma_store_depth", 0) or 0)


def _enter_chroma_store_session() -> None:
    _writer_tls.chroma_store_depth = production_chroma_store_session_depth() + 1


def _exit_chroma_store_session() -> None:
    _writer_tls.chroma_store_depth = max(0, production_chroma_store_session_depth() - 1)


def require_writer_attestation() -> WriterAttestation:
    """Return the internal writer attestation for the current execution scope.

    The attestation is established only by ``shared_writer_lease``.  Caller
    metadata and direct store construction cannot manufacture it.
    """
    held = _held_writer_lease()
    if held is None:
        raise WriterBoundaryError(
            "production-authoritative mutation requires the shared writer boundary"
        )
    return held.attestation


def _same_lock_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def _acquire_process_writer_lease(
    *,
    attest_dir: Path | None,
    entrypoint: str,
) -> WriterAttestation:
    """Establish or extend process-scoped ownership of the PID attestation."""
    with _process_writer_leases.lock:
        first = _process_writer_leases.active_count == 0
        if first:
            attestation = build_writer_attestation(entrypoint=entrypoint)
            write_attestation(attestation, attest_dir=attest_dir)
            _process_writer_leases.attestation = attestation
            _process_writer_leases.attest_dir = attest_dir
        else:
            attestation = _process_writer_leases.attestation
            if attestation is None:
                raise RuntimeError("active writer lease missing attestation")
        _process_writer_leases.active_count += 1
        return attestation


def _release_process_writer_lease() -> bool:
    """Drop one process-scoped lease; return True when attestation may clear."""
    with _process_writer_leases.lock:
        if _process_writer_leases.active_count <= 0:
            raise RuntimeError("writer lease release without matching acquire")
        _process_writer_leases.active_count -= 1
        if _process_writer_leases.active_count == 0:
            attestation = _process_writer_leases.attestation
            attest_dir = _process_writer_leases.attest_dir
            _process_writer_leases.attestation = None
            _process_writer_leases.attest_dir = None
            if attestation is not None:
                clear_attestation(attestation.pid, attest_dir=attest_dir)
            return True
        return False


def current_git_revision() -> str:
    try:
        import subprocess

        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).resolve().parent),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except OSError:
        pass
    return "unknown"


def current_implementation_revision() -> str:
    """Authority-bound implementation identity shared with R2b coverage/proof."""
    from eval_corpus.r2b_v2.coverage.inventory import resolve_r2b_implementation_revision

    return resolve_r2b_implementation_revision()


def current_code_revision() -> str:
    """Git HEAD provenance for debugging and non-authority telemetry."""
    return current_git_revision()


def _proc_start_time(pid: int) -> str:
    try:
        # Field 22 in /proc/pid/stat is starttime (clock ticks).
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        # comm may contain spaces/parens — split after last ')'
        after = stat.rsplit(")", 1)[-1].split()
        return str(after[19])  # starttime
    except (OSError, IndexError, ValueError):
        return "unknown"


def build_writer_attestation(
    *,
    entrypoint: str = "production_chroma_write_session",
    code_revision: str | None = None,
    git_revision: str | None = None,
) -> WriterAttestation:
    pid = os.getpid()
    return WriterAttestation(
        pid=pid,
        start_time=_proc_start_time(pid),
        code_revision=code_revision or current_implementation_revision(),
        git_revision=git_revision or current_git_revision(),
        executable=os.path.realpath(f"/proc/{pid}/exe") if Path(f"/proc/{pid}/exe").exists() else "unknown",
        entrypoint=entrypoint,
        protocol_version=WRITER_GATE_PROTOCOL_VERSION,
        recorded_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def write_attestation(
    attestation: WriterAttestation,
    *,
    attest_dir: Path | None = None,
) -> Path:
    directory = (attest_dir or DEFAULT_ATTEST_DIR).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{attestation.pid}.json"
    payload = json.dumps(attestation.as_dict(), indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(directory),
    )
    published = False
    try:
        with os.fdopen(fd, "wb") as handle:
            fd = -1
            handle.write(payload.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
        published = True
    except BaseException:
        if not published:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
        raise
    return path


def clear_attestation(
    pid: int | None = None, *, attest_dir: Path | None = None
) -> None:
    directory = (attest_dir or DEFAULT_ATTEST_DIR).expanduser()
    path = directory / f"{pid or os.getpid()}.json"
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def load_attestation(
    pid: int, *, attest_dir: Path | None = None
) -> dict[str, Any] | None:
    path = (attest_dir or DEFAULT_ATTEST_DIR).expanduser() / f"{pid}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def generate_writer_census(
    *,
    code_revision: str | None = None,
    chroma_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Mechanical census for C5 quiescence — units, signatures, open-FD PIDs."""
    chroma = (
        str(Path(chroma_dir).expanduser())
        if chroma_dir
        else str(Path("~/.local/share/convmem/chroma").expanduser())
    )
    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_revision": code_revision or current_implementation_revision(),
        "git_revision": current_git_revision(),
        "protocol_version": WRITER_GATE_PROTOCOL_VERSION,
        "systemd_units": list(KNOWN_WRITER_SYSTEMD_UNITS),
        "cmdline_signatures": list(KNOWN_WRITER_CMDLINE_SIGNATURES),
        "chroma_dir": chroma,
        "open_fd_writer_pids": list_pids_with_open_path(chroma),
    }


def list_pids_with_open_path(target: str | Path) -> list[int]:
    """Return PIDs with an open FD whose path is under target (best-effort)."""
    root = str(Path(target).expanduser().resolve())
    found: set[int] = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        fd_dir = entry / "fd"
        try:
            for fd in fd_dir.iterdir():
                try:
                    dest = os.readlink(fd)
                except OSError:
                    continue
                if dest.startswith(root):
                    found.add(pid)
                    break
        except OSError:
            continue
    return sorted(found)


def classify_legacy_writer_pids(
    pids: list[int],
    *,
    attest_dir: Path | None = None,
    expected_revision: str | None = None,
) -> list[dict[str, Any]]:
    """Return refusal records for unattested / mismatched writer PIDs."""
    expected = expected_revision or current_implementation_revision()
    refusals: list[dict[str, Any]] = []
    for pid in pids:
        if pid == os.getpid():
            continue
        att = load_attestation(pid, attest_dir=attest_dir)
        if att is None:
            refusals.append(
                {
                    "code": "legacy_writer_process",
                    "pid": pid,
                    "detail": "unattested writer pid",
                }
            )
            continue
        if int(att.get("protocol_version") or 0) != WRITER_GATE_PROTOCOL_VERSION:
            refusals.append(
                {
                    "code": "legacy_writer_process",
                    "pid": pid,
                    "detail": "protocol version mismatch",
                }
            )
            continue
        if expected != "unknown" and att.get("code_revision") not in {
            expected,
            "unknown",
        }:
            # Allow unknown in hermetic tests; refuse clear mismatches.
            if att.get("code_revision") not in {None, "unknown"} and att.get(
                "code_revision"
            ) != expected:
                refusals.append(
                    {
                        "code": "legacy_writer_process",
                        "pid": pid,
                        "detail": "code revision mismatch",
                    }
                )
    return refusals


@contextmanager
def shared_writer_lease(
    *,
    lock_path: Path | None = None,
    attest_dir: Path | None = None,
    entrypoint: str = "production_chroma_write_session",
    timeout_ms: int = 30_000,
    census_dir: Path | None = None,
) -> Iterator[WriterAttestation]:
    """Acquire shared flock, emit C7 census events, and hold until context exit.

    The close event is deliberately persisted at the start of ``finally``:
    it must become durable while the shared flock is still held, including for
    ``open_production_write_store`` where ``store.close()`` releases this
    context manager through its callback.
    """
    path = (lock_path or DEFAULT_WRITER_LOCK).expanduser()
    held = _held_writer_lease()
    if held is not None:
        if lock_path is not None and not _same_lock_path(held.lock_path, path):
            raise WriterBoundaryError(
                "nested shared writer lease must reuse the outer lock path"
            )
        path = held.lock_path
        _acquire_process_writer_lease(
            attest_dir=attest_dir,
            entrypoint=entrypoint,
        )
        held.depth += 1
        try:
            yield held.attestation
        finally:
            held.depth -= 1
            _release_process_writer_lease()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            break
        except BlockingIOError as exc:
            if time.monotonic() >= deadline:
                os.close(fd)
                raise TimeoutError(
                    f"writer_quiesce_timeout: shared lease after {timeout_ms}ms"
                ) from exc
            time.sleep(0.01)
    try:
        attestation = _acquire_process_writer_lease(
            attest_dir=attest_dir,
            entrypoint=entrypoint,
        )
    except Exception:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        raise
    # C7's separate journal lock is taken only after this writer gate.  A
    # durable open failure refuses before the caller can mutate Chroma.
    from writer_census import record_writer_open

    try:
        census_session = record_writer_open(
            census_dir=census_dir, entrypoint=entrypoint, writer_gate_path=path
        )
    except Exception:
        _release_process_writer_lease()
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        raise
    _writer_tls.held = _HeldWriterLease(path, attestation)
    try:
        yield attestation
    finally:
        # Preserve a successful Chroma mutation if telemetry close fails; the
        # unmatched durable open makes the eventual census report fail closed.
        from writer_census import WriterCensusRefused, record_writer_close

        try:
            record_writer_close(census_session)
        except WriterCensusRefused:
            pass
        _release_process_writer_lease()
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            _writer_tls.held = None
            os.close(fd)


@contextmanager
def exclusive_writer_lease(
    *,
    lock_path: Path | None = None,
    timeout_ms: int = 30_000,
) -> Iterator[None]:
    """Exclusive flock for C5 activation (no compliant shared holders)."""
    path = (lock_path or DEFAULT_WRITER_LOCK).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError as exc:
            if time.monotonic() >= deadline:
                os.close(fd)
                raise TimeoutError(
                    f"writer_quiesce_timeout: exclusive lease after {timeout_ms}ms"
                ) from exc
            time.sleep(0.01)
    try:
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


@contextmanager
def production_writer_boundary(
    *,
    lock_path: Path | None = None,
    attest_dir: Path | None = None,
    census_dir: Path | None = None,
    entrypoint: str = "production.writer",
    timeout_ms: int = 30_000,
    affected_sources: tuple[str, ...] | None = None,
    maintenance_unscoped: bool = False,
    coordination_cfg: dict | None = None,
) -> Iterator[WriterAttestation]:
    """Cover a provenance-relevant mutation with the shared writer gate.

    Existing Chroma sessions and composite writers use this same boundary.
    Re-entry is deliberately safe so a composite route cannot open a second
    independent consistency system around an already leased store.
    """

    from bootstrap_codex_v3_writer_coordination import (
        COORDINATION_DEFERRAL_CODE,
        BootstrapWriterCoordinationError,
        WriterSourceScope,
        enforce_writer_scope,
        writer_source_scope,
    )

    cfg = coordination_cfg
    if cfg is None:
        try:
            import config as config_mod

            cfg = config_mod.load_config()
        except Exception:  # pylint: disable=broad-exception-caught
            cfg = {}
    scope = WriterSourceScope(
        entrypoint=entrypoint,
        affected_sources=tuple(affected_sources or ()),
        maintenance_unscoped=maintenance_unscoped,
    )
    with writer_source_scope(scope):
        try:
            enforce_writer_scope(cfg, scope)
        except BootstrapWriterCoordinationError as exc:
            if str(exc) == COORDINATION_DEFERRAL_CODE and scope.affected_sources:
                from incremental_jsonl import IncrementalJsonlError

                from bootstrap_codex_v3_writer_coordination import active_reservation_signal

                signal = active_reservation_signal(cfg, scope.affected_sources[0])
                if signal is not None:
                    raise IncrementalJsonlError(COORDINATION_DEFERRAL_CODE, signal.to_stderr_line()) from exc
            raise

    with shared_writer_lease(
        lock_path=lock_path,
        attest_dir=attest_dir,
        census_dir=census_dir,
        entrypoint=entrypoint,
        timeout_ms=timeout_ms,
    ) as attestation:
        yield attestation


@contextmanager
def capture_generation(
    *,
    lock_path: Path | None = None,
    timeout_ms: int = 30_000,
) -> Iterator[CaptureGeneration]:
    """Bind one seal/capture operation to an exclusive writer-free generation.

    All compliant mutation routes hold the same shared gate.  Therefore the
    exclusive interval is the only point at which a capture may read and seal
    its manifest-bound components; an overlapping mutation waits or times
    out, and cannot be combined into the captured logical state.
    """

    path = (lock_path or DEFAULT_WRITER_LOCK).expanduser()
    with exclusive_writer_lease(lock_path=path, timeout_ms=timeout_ms):
        yield CaptureGeneration(
            generation_id=f"capture-{uuid.uuid4().hex}",
            lock_path=path,
            started_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


def decide_production_sink_injection(
    cfg: Mapping[str, Any] | None,
    *,
    chroma_dir: str | Path,
    config_path: str | Path | None = None,
    runtime_code_revision: str | None = None,
) -> SinkInjectionDecision:
    """C1 strict validator gate for production writer sessions."""
    settings = resolve_shadow_settings(cfg)
    if not settings.injection_eligible_config:
        return SinkInjectionDecision(
            False, "shadow_ledger absent or enabled=false (no sink)"
        )
    result = validate_shadow_activation(
        config_path,
        chroma_dir,
        "writer",
        cfg=cfg,
        runtime_code_revision=runtime_code_revision or current_code_revision(),
    )
    if result.inject_eligible:
        return SinkInjectionDecision(
            True,
            "strict activation contract satisfied",
        )
    codes = ",".join(result.codes()) or "not_eligible"
    return SinkInjectionDecision(
        False, f"strict validation refused: {codes}"
    )


def open_chroma_for_write(
    cfg: Mapping[str, Any] | None,
    chroma_dir: str | Path,
    *,
    purpose: WritePurpose = "production",
    create_collections: bool = True,
    mutation_sink: Any | None = None,
    on_close: Any | None = None,
    use_strict_validator: bool | None = None,
) -> tuple[ChromaStore, SinkInjectionDecision]:
    """Open a write-capable ChromaStore; attach sink only when contract allows.

    Production purpose uses the C1 strict validator unless overridden.
    Test purpose never auto-injects; an explicit mutation_sink may be attached
    for hermetic tests (test-only override).
    """
    strict = True if use_strict_validator is None else use_strict_validator
    if purpose != "production":
        decision = SinkInjectionDecision(
            False, f"purpose={purpose} forces no auto sink injection"
        )
        sink = mutation_sink  # hermetic override
    elif strict:
        decision = decide_production_sink_injection(cfg, chroma_dir=chroma_dir)
        sink = None
        if mutation_sink is not None:
            sink = mutation_sink if decision.inject else None
        elif decision.inject:
            settings = resolve_shadow_settings(cfg)
            sink = JsonlUnitMutationSink(
                ledger_path=settings.ledger_path,
                health_path=settings.health_path,
            )
    else:
        # Legacy shallow gate — reserved; production defaults to strict.
        from shadow_ledger import decide_sink_injection

        decision = decide_sink_injection(cfg, chroma_dir=chroma_dir)
        sink = None
        if mutation_sink is not None:
            sink = mutation_sink if decision.inject else None
        elif decision.inject:
            settings = resolve_shadow_settings(cfg)
            sink = JsonlUnitMutationSink(
                ledger_path=settings.ledger_path,
                health_path=settings.health_path,
            )

    # Production writes run under the native-write guard (crash containment for the
    # shared HNSW); ``[index] chroma_write_guard = false`` is the operator off-switch.
    write_guard = None
    if purpose == "production" and write_guard_enabled(cfg):
        write_guard = ChromaWriteGuard(chroma_dir)
    store = ChromaStore(
        str(chroma_dir),
        create_collections=create_collections,
        mutation_sink=sink,
        on_close=on_close,
        require_writer_boundary=purpose == "production",
        write_guard=write_guard,
    )
    return store, decision


@contextmanager
def chroma_write_session(
    cfg: Mapping[str, Any] | None,
    chroma_dir: str | Path,
    *,
    purpose: WritePurpose = "production",
    create_collections: bool = True,
    mutation_sink: Any | None = None,
) -> Iterator[ChromaStore]:
    """Context-managed write store (closes on exit).

    Deprecated for production callers — use production_chroma_write_session
    so config is loaded only after the shared lease is held.
    """
    boundary = production_writer_boundary() if purpose == "production" else nullcontext()
    with boundary:
        store, _decision = open_chroma_for_write(
            cfg,
            chroma_dir,
            purpose=purpose,
            create_collections=create_collections,
            mutation_sink=mutation_sink,
        )
        try:
            yield store
        finally:
            store.close()


@dataclass(frozen=True)
class AdmittedWriteOperation:  # pylint: disable=too-many-instance-attributes
    """One operation's configuration, resolved once under the shared lease.

    Nested production sessions in the same thread reuse this configuration
    instead of reloading it, and refuse if its inputs changed.
    """

    entrypoint: str
    config_path: Path
    config_digest: str
    chroma_dir: Path
    configured_chroma_dir: Path
    affected_paths: tuple[Path, ...]
    preflight: Any
    _cfg: dict[str, Any]
    units_export: Path | None = None
    configured_units_export: Path | None = None
    _extra_affected_paths: (
        Callable[[Mapping[str, Any]], Iterable[str | Path]] | None
    ) = None

    def config(self) -> dict[str, Any]:
        """Private admitted-config copy for config-derived consumers.

        Production store factories pass ``op.chroma_dir`` (canonical) explicitly.
        Approval, recovery and other helpers that derive governed paths from
        ``index.chroma_dir`` receive the configured spelling admitted at
        preflight. Export binding stays on the canonical ``units_export`` pin.
        """
        import copy

        cfg = copy.deepcopy(self._cfg)
        index = cfg.get("index")
        if not isinstance(index, dict):
            index = {}
            cfg["index"] = index
        index["chroma_dir"] = str(self.configured_chroma_dir)
        if self.units_export is not None:
            index["units_export"] = str(self.units_export)
        return cfg


def _bound_operation() -> AdmittedWriteOperation | None:
    return getattr(_writer_tls, "bound_operation", None)


def _config_digest(path: Path) -> str:
    import hashlib

    from restic_gate import OperationAdmissionRefused
    from restic_snapshot import EXIT_INVALID_CONFIG

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise OperationAdmissionRefused(
            f"operation config unreadable: {path}: {exc}",
            EXIT_INVALID_CONFIG,
            "operation_config_unreadable",
        ) from exc


def _canonical_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def operation_affected_paths(cfg: Mapping[str, Any]) -> list[Path]:
    """Durable paths every guarded Chroma write session can touch."""
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    chroma = _canonical_path(index["chroma_dir"])
    paths = [chroma, chroma.parent / f"{chroma.name}{GUARD_DIR_SUFFIX}"]
    if index.get("units_export"):
        paths.append(_canonical_path(index["units_export"]))
    settings = resolve_shadow_settings(cfg)
    if settings.injection_eligible_config:
        paths.extend(
            _canonical_path(p) for p in (settings.ledger_path, settings.health_path)
        )
    return paths


def _resolve_operation_target(
    cfg: Mapping[str, Any],
    extra_affected_paths: Callable[[Mapping[str, Any]], Iterable[str | Path]] | None,
) -> tuple[Path, tuple[Path, ...]]:
    from restic_gate import OperationAdmissionRefused
    from restic_snapshot import EXIT_INVALID_CONFIG

    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    if not index.get("chroma_dir"):
        raise OperationAdmissionRefused(
            "live config missing index.chroma_dir",
            EXIT_INVALID_CONFIG,
            "operation_config_invalid",
        )
    paths = operation_affected_paths(cfg)
    if extra_affected_paths is not None:
        paths.extend(_canonical_path(p) for p in extra_affected_paths(cfg))
    unique = tuple(dict.fromkeys(paths))
    return _canonical_path(index["chroma_dir"]), unique


def verify_admitted_targets_unchanged(op: AdmittedWriteOperation) -> None:
    """Refuse when config bytes are unchanged but a bound alias now resolves elsewhere."""
    from restic_gate import (
        REASON_OPERATION_CONFIG_CHANGED,
        OperationAdmissionRefused,
    )
    from restic_snapshot import EXIT_WRONG_PATH

    live_cfg = config_mod.load_config(op.config_path)
    chroma_now, affected_now = _resolve_operation_target(
        live_cfg,
        op._extra_affected_paths,  # pylint: disable=protected-access
    )
    if chroma_now != op.chroma_dir or affected_now != op.affected_paths:
        raise OperationAdmissionRefused(
            f"{op.entrypoint}: operation target or affected paths changed after "
            "admission without editing config/env",
            EXIT_WRONG_PATH,
            REASON_OPERATION_CONFIG_CHANGED,
        )
    if op.units_export is not None:
        index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
        raw_export = index.get("units_export")
        if raw_export and _canonical_path(raw_export) != op.units_export:
            raise OperationAdmissionRefused(
                f"{op.entrypoint}: export path {raw_export!r} now resolves outside "
                "the admitted target",
                EXIT_WRONG_PATH,
                REASON_OPERATION_CONFIG_CHANGED,
            )


def admitted_units_export_path(cfg: Mapping[str, Any]) -> Path | None:
    """Export path from admitted pinned config, verifying binding when bound."""
    op = _bound_operation()
    if op is not None:
        verify_admitted_operation_unchanged(op)
    index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
    raw = index.get("units_export")
    if not raw:
        return None
    return _canonical_path(raw)


def verify_competing_guard_locations(
    op: AdmittedWriteOperation | None,
    live_cfg: Mapping[str, Any] | None = None,
) -> None:
    """Refuse alias/canonical guard-location conflicts before opening a client."""
    if op is not None:
        requested = op.configured_chroma_dir
    elif live_cfg is not None:
        index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
        raw = index.get("chroma_dir")
        if not raw:
            return
        requested = Path(raw).expanduser()
    else:
        return
    ChromaWriteGuard(requested).require_not_quarantined()


def verify_admitted_operation_unchanged(op: AdmittedWriteOperation) -> None:
    """Refuse when the admitted config or backup profile inputs changed."""
    from restic_gate import (
        REASON_OPERATION_CONFIG_CHANGED,
        OperationAdmissionRefused,
        verify_preflight_inputs_unchanged,
    )
    from restic_snapshot import EXIT_INVALID_CONFIG, EXIT_WRONG_PATH

    if _config_digest(op.config_path) != op.config_digest:
        code = EXIT_INVALID_CONFIG
        try:
            chroma, _paths = _resolve_operation_target(
                config_mod.load_config(op.config_path), None
            )
            if chroma != op.chroma_dir:
                code = EXIT_WRONG_PATH
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        raise OperationAdmissionRefused(
            f"{op.entrypoint}: operation config {op.config_path} changed after "
            "admission; refusing to adopt it",
            code,
            REASON_OPERATION_CONFIG_CHANGED,
        )
    verify_preflight_inputs_unchanged(op.preflight)
    verify_admitted_targets_unchanged(op)


@contextmanager
def admitted_write_operation(
    *,
    entrypoint: str,
    extra_affected_paths: Callable[[Mapping[str, Any]], Iterable[str | Path]]
    | None = None,
    config_path: str | Path | None = None,
    lock_path: Path | None = None,
    attest_dir: Path | None = None,
    census_dir: Path | None = None,
) -> Iterator[AdmittedWriteOperation]:
    """Shared lease → one config load → bound Restic preflight → admitted op.

    Must be entered before opening Chroma or changing approval state. Raises
    ``restic_gate.OperationAdmissionRefused`` instead of yielding when the
    preflight refuses or the configuration changes during admission.
    """
    from restic_gate import (
        REASON_OPERATION_CONFIG_CHANGED,
        OperationAdmissionRefused,
        OperationTarget,
        preflight_operation,
    )
    from restic_snapshot import EXIT_INVALID_CONFIG

    path = _canonical_path(config_path or config_mod.CONFIG_PATH)
    with shared_writer_lease(
        lock_path=lock_path,
        attest_dir=attest_dir,
        census_dir=census_dir,
        entrypoint=entrypoint,
    ):
        if _bound_operation() is not None:
            raise OperationAdmissionRefused(
                f"{entrypoint}: nested admitted operation is not supported",
                EXIT_INVALID_CONFIG,
                "nested_admitted_operation",
            )
        digest = _config_digest(path)
        live_cfg = config_mod.load_config(path)
        if _config_digest(path) != digest:
            raise OperationAdmissionRefused(
                f"{entrypoint}: operation config {path} changed while loading",
                EXIT_INVALID_CONFIG,
                REASON_OPERATION_CONFIG_CHANGED,
            )
        chroma_dir, affected = _resolve_operation_target(
            live_cfg, extra_affected_paths
        )
        index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
        configured_chroma_dir = Path(index["chroma_dir"]).expanduser()
        configured_units_export = (
            Path(index["units_export"]).expanduser()
            if index.get("units_export")
            else None
        )
        units_export = (
            _canonical_path(index["units_export"])
            if index.get("units_export")
            else None
        )
        preflight = preflight_operation(
            OperationTarget(
                entrypoint=entrypoint,
                chroma_dir=chroma_dir,
                affected_paths=affected,
                config_path=path,
            )
        )
        op = AdmittedWriteOperation(
            entrypoint=entrypoint,
            config_path=path,
            config_digest=digest,
            chroma_dir=chroma_dir,
            configured_chroma_dir=configured_chroma_dir,
            affected_paths=affected,
            preflight=preflight,
            _cfg=live_cfg,
            units_export=units_export,
            configured_units_export=configured_units_export,
            _extra_affected_paths=extra_affected_paths,
        )
        verify_admitted_operation_unchanged(op)
        _writer_tls.bound_operation = op
        try:
            yield op
        finally:
            _writer_tls.bound_operation = None


def _session_config(path: Path) -> dict[str, Any]:
    """Live config for a production session; the admitted one when bound."""
    op = _bound_operation()
    if op is None:
        return config_mod.load_config(path)
    from restic_gate import OperationAdmissionRefused
    from restic_snapshot import EXIT_INVALID_CONFIG

    if _canonical_path(path) != op.config_path:
        raise OperationAdmissionRefused(
            f"{op.entrypoint}: nested session requested config {path}, "
            f"not the admitted {op.config_path}",
            EXIT_INVALID_CONFIG,
            "operation_config_substituted",
        )
    verify_admitted_operation_unchanged(op)
    verify_competing_guard_locations(op)
    return op.config()


class _IndexWriteGuardedChromaStore:
    """Production store wrapper: mutations require the index write lock (deny by default).

    Read allow-list (CO-1): each method only reads Chroma state or metadata.
    - close: release client resources without mutation
    - query_summaries / count_summaries / summaries_metadata: read summary collection
    - query_units / count_units / units_metadata / active_units_for_ledger_id /
      get_units_with_embeddings / get_unit: read unit collection
    - count_for_source_path / ids_for_source / preview_supersede_for_source /
      snapshot_source_rows: read source-scoped inventory
    - non_source_inventory_digest: read-only digest helper
    """

    _READS = frozenset(
        {
            "close",
            "query_summaries",
            "count_summaries",
            "summaries_metadata",
            "query_units",
            "count_units",
            "units_metadata",
            "active_units_for_ledger_id",
            "get_units_with_embeddings",
            "get_unit",
            "count_for_source_path",
            "ids_for_source",
            "preview_supersede_for_source",
            "snapshot_source_rows",
            "non_source_inventory_digest",
        }
    )

    def __init__(self, inner: ChromaStore) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        if name == "client":
            raise RuntimeError(
                "raw Chroma client access is denied on production stores"
            )
        inner_attr = getattr(self._inner, name)
        if not callable(inner_attr):
            return inner_attr
        if name in self._READS:
            return inner_attr
        from purge_locks import require_index_write_lock_held

        if name == "_collection":

            def _collection(name_arg: str, *args: Any, **kwargs: Any) -> Any:
                require_index_write_lock_held(chroma_dir=self._inner.chroma_dir)
                return inner_attr(name_arg, *args, **kwargs)

            return _collection

        def _guarded(*args: Any, **kwargs: Any) -> Any:
            require_index_write_lock_held(chroma_dir=self._inner.chroma_dir)
            from bootstrap_codex_v3_writer_coordination import (
                enforce_writer_scope,
                inspect_chroma_mutation_scope,
            )
            import config as config_mod

            scope = inspect_chroma_mutation_scope(
                config_mod.load_config(), method=name, args=args, kwargs=kwargs
            )
            enforce_writer_scope(config_mod.load_config(), scope)
            return inner_attr(*args, **kwargs)

        return _guarded

    def close(self) -> None:
        self._inner.close()


@contextmanager
def production_chroma_write_session(
    config_path: str | Path | None = None,
    *,
    create_collections: bool = True,
    lock_path: Path | None = None,
    attest_dir: Path | None = None,
    census_dir: Path | None = None,
    entrypoint: str = "production_chroma_write_session",
) -> Iterator[ProductionWriteSession]:
    """Shared lease → load live config → open store; yield store+live_cfg.

    Accepts no caller-supplied config or Chroma root. Lease is held for the
    entire session including store.close().
    """
    path = Path(config_path or config_mod.CONFIG_PATH).expanduser()
    with shared_writer_lease(
        lock_path=lock_path,
        attest_dir=attest_dir,
        census_dir=census_dir,
        entrypoint=entrypoint,
    ):
        live_cfg = _session_config(path)
        op = _bound_operation()
        if op is not None:
            chroma_dir = op.chroma_dir
        else:
            index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
            chroma_dir = index.get("chroma_dir")
            verify_competing_guard_locations(None, live_cfg)
        if not chroma_dir:
            raise ValueError("live config missing index.chroma_dir")
        store, decision = open_chroma_for_write(
            live_cfg,
            chroma_dir,
            purpose="production",
            create_collections=create_collections,
            use_strict_validator=True,
        )
        guarded = _IndexWriteGuardedChromaStore(store)
        _enter_chroma_store_session()
        try:
            yield ProductionWriteSession(
                store=guarded, live_cfg=live_cfg, decision=decision
            )
        finally:
            _exit_chroma_store_session()
            store.close()


def verify_recovery_config_binding(
    op: AdmittedWriteOperation,
    cfg: Mapping[str, Any] | None,
) -> None:
    """Refuse recovery when caller cfg does not match the admitted operation."""
    from propose_decision import _governed_recovery_affected_paths
    from restic_gate import OperationAdmissionRefused
    from restic_snapshot import EXIT_WRONG_PATH

    if op.entrypoint != "propose_decision.write":
        raise OperationAdmissionRefused(
            f"{op.entrypoint}: recovery requires propose_decision.write admission",
            EXIT_WRONG_PATH,
            "operation_config_changed",
        )

    admitted = op.config()
    if cfg is not None and cfg is not admitted:
        seen_index = cfg.get("index") if isinstance(cfg.get("index"), dict) else {}
        admitted_index = (
            admitted.get("index") if isinstance(admitted.get("index"), dict) else {}
        )
        seen_chroma = seen_index.get("chroma_dir")
        admitted_chroma = admitted_index.get("chroma_dir")
        if not seen_chroma or not admitted_chroma:
            raise OperationAdmissionRefused(
                "recovery cfg missing chroma target", EXIT_WRONG_PATH,
                "operation_config_changed",
            )
        seen_export = seen_index.get("units_export")
        admitted_export = admitted_index.get("units_export")
        if bool(seen_export) != bool(admitted_export) or (
            seen_export and _canonical_path(seen_export) != op.units_export
        ):
            raise OperationAdmissionRefused(
                "recovery cfg export does not match admitted target", EXIT_WRONG_PATH,
                "operation_config_changed",
            )
        if seen_chroma and admitted_chroma:
            if Path(seen_chroma).expanduser() != Path(admitted_chroma).expanduser():
                raise OperationAdmissionRefused(
                    f"{op.entrypoint}: recovery cfg chroma_dir does not match admitted config",
                    EXIT_WRONG_PATH,
                    "operation_config_changed",
                )
        if seen_chroma and _canonical_path(seen_chroma) != op.chroma_dir:
            raise OperationAdmissionRefused(
                f"{op.entrypoint}: recovery cfg resolves outside admitted chroma target",
                EXIT_WRONG_PATH,
                "operation_config_changed",
            )

    expected_paths = {
        _canonical_path(p) for p in _governed_recovery_affected_paths(admitted)
    }
    admitted_paths = {_canonical_path(p) for p in op.affected_paths}
    missing = expected_paths - admitted_paths
    if missing:
        raise OperationAdmissionRefused(
            f"{op.entrypoint}: recovery admission missing governed affected paths: "
            f"{sorted(str(p) for p in missing)}",
            EXIT_WRONG_PATH,
            "operation_config_changed",
        )

    index = admitted.get("index") if isinstance(admitted.get("index"), dict) else {}
    configured_chroma = index.get("chroma_dir")
    if configured_chroma:
        lexical_root = Path(configured_chroma).expanduser().parent.resolve(strict=False)
        if lexical_root not in admitted_paths and not any(
            lexical_root == p or lexical_root in p.parents for p in admitted_paths
        ):
            raise OperationAdmissionRefused(
                f"{op.entrypoint}: lexical governed data root {lexical_root} "
                "is not covered by admitted affected paths",
                EXIT_WRONG_PATH,
                "operation_config_changed",
            )

    verify_admitted_operation_unchanged(op)


def recovery_durability_root(op: AdmittedWriteOperation) -> Path:
    """Use the admitted backup root as the pre-existing directory durability anchor.

    Recovery may create entries below this boundary, never the boundary itself.
    Re-sync every intermediate directory on retries: readable names alone do not
    establish that a previous directory-fsync attempt succeeded.
    """
    from restic_snapshot import BackupContext

    verify_admitted_operation_unchanged(op)
    if op.preflight.env_file is not None:
        root = BackupContext.from_env_file(op.preflight.env_file).data_root
    else:
        # Existing test/lab admission exception; never a production fallback.
        if op.preflight.status != "isolated-exception":
            raise WriterBoundaryError("recovery lacks a bound backup root")
        root = Path(op.config()["index"]["chroma_dir"]).expanduser().parent
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise WriterBoundaryError("recovery durability root must already exist")
    if any(path != root and root not in path.parents for path in op.affected_paths):
        raise WriterBoundaryError("recovery affected path outside durability root")
    verify_admitted_operation_unchanged(op)
    return root


def open_production_recovery_write_store(
    config_path: str | Path | None = None,
    *,
    lock_path: Path | None = None,
    attest_dir: Path | None = None,
    census_dir: Path | None = None,
    entrypoint: str = "propose_decision.write",
) -> ProductionWriteSession:
    """Recovery session: never auto-create collections (absence is review/unknown)."""
    return open_production_write_store(
        config_path,
        create_collections=False,
        lock_path=lock_path,
        attest_dir=attest_dir,
        census_dir=census_dir,
        entrypoint=entrypoint,
    )


def open_production_write_store(
    config_path: str | Path | None = None,
    *,
    create_collections: bool = True,
    lock_path: Path | None = None,
    attest_dir: Path | None = None,
    census_dir: Path | None = None,
    entrypoint: str = "production_chroma_write_session",
) -> ProductionWriteSession:
    """Open a leased production write session; caller must close store.

    Holds the shared lease until ``session.store.close()`` runs (via on_close).
    Prefer ``production_chroma_write_session`` when a ``with`` block is natural.
    """
    path = Path(config_path or config_mod.CONFIG_PATH).expanduser()
    # Manually enter shared lease and bind release to store.close.
    lease_cm = shared_writer_lease(
        lock_path=lock_path,
        attest_dir=attest_dir,
        census_dir=census_dir,
        entrypoint=entrypoint,
    )
    lease_cm.__enter__()
    closed = {"done": False}

    def _release() -> None:
        if closed["done"]:
            return
        closed["done"] = True
        _exit_chroma_store_session()
        lease_cm.__exit__(None, None, None)

    try:
        live_cfg = _session_config(path)
        op = _bound_operation()
        if op is not None:
            chroma_dir = op.chroma_dir
        else:
            index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
            chroma_dir = index.get("chroma_dir")
            verify_competing_guard_locations(None, live_cfg)
        if not chroma_dir:
            _release()
            raise ValueError("live config missing index.chroma_dir")
        store, decision = open_chroma_for_write(
            live_cfg,
            chroma_dir,
            purpose="production",
            create_collections=create_collections,
            use_strict_validator=True,
            on_close=_release,
        )
        _enter_chroma_store_session()
        return ProductionWriteSession(
            store=_IndexWriteGuardedChromaStore(store),
            live_cfg=live_cfg,
            decision=decision,
        )
    except Exception:
        _release()
        raise
