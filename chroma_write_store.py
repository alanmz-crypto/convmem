# pylint: disable=cyclic-import,duplicate-code,too-many-locals,too-many-arguments
"""Authoritative production write-store factory and C3 writer gate.

Production sessions take a shared writer lease, then load live config. Sink
injection uses the C1 strict validator. Callers must not pass cfg into the
production session API.
"""

from __future__ import annotations

import fcntl
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping

from chroma_store import ChromaStore
import config as config_mod
from shadow_ledger import (
    SinkInjectionDecision,
    resolve_shadow_settings,
)
from shadow_sink import JsonlUnitMutationSink
from shadow_validation import validate_shadow_activation

WritePurpose = Literal["production", "test"]

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
class WriterAttestation:
    pid: int
    start_time: str
    code_revision: str
    executable: str
    entrypoint: str
    protocol_version: int
    recorded_at_utc: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "start_time": self.start_time,
            "code_revision": self.code_revision,
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
    """Process-local nesting state for one shared mutation boundary."""

    lock_path: Path
    attestation: WriterAttestation
    depth: int = 1


_writer_tls = threading.local()


def _held_writer_lease() -> _HeldWriterLease | None:
    return getattr(_writer_tls, "held", None)


def _same_lock_path(left: Path, right: Path) -> bool:
    return left.resolve(strict=False) == right.resolve(strict=False)


def current_code_revision() -> str:
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
) -> WriterAttestation:
    pid = os.getpid()
    return WriterAttestation(
        pid=pid,
        start_time=_proc_start_time(pid),
        code_revision=code_revision or current_code_revision(),
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
    path.write_text(payload, encoding="utf-8")
    os.chmod(path, 0o600)
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
        "code_revision": code_revision or current_code_revision(),
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
    expected = expected_revision or current_code_revision()
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
    if held is not None and (lock_path is None or _same_lock_path(held.lock_path, path)):
        path = held.lock_path
        held.depth += 1
        try:
            yield held.attestation
        finally:
            held.depth -= 1
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
    attestation = build_writer_attestation(entrypoint=entrypoint)
    write_attestation(attestation, attest_dir=attest_dir)
    # C7's separate journal lock is taken only after this writer gate.  A
    # durable open failure refuses before the caller can mutate Chroma.
    from writer_census import record_writer_open

    try:
        census_session = record_writer_open(
            census_dir=census_dir, entrypoint=entrypoint, writer_gate_path=path
        )
    except Exception:
        clear_attestation(attestation.pid, attest_dir=attest_dir)
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
        clear_attestation(attestation.pid, attest_dir=attest_dir)
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
) -> Iterator[WriterAttestation]:
    """Cover a provenance-relevant mutation with the shared writer gate.

    Existing Chroma sessions and composite writers use this same boundary.
    Re-entry is deliberately safe so a composite route cannot open a second
    independent consistency system around an already leased store.
    """

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

    store = ChromaStore(
        str(chroma_dir),
        create_collections=create_collections,
        mutation_sink=sink,
        on_close=on_close,
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
        live_cfg = config_mod.load_config(path)
        index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
        chroma_dir = index.get("chroma_dir")
        if not chroma_dir:
            raise ValueError("live config missing index.chroma_dir")
        store, decision = open_chroma_for_write(
            live_cfg,
            chroma_dir,
            purpose="production",
            create_collections=create_collections,
            use_strict_validator=True,
        )
        try:
            yield ProductionWriteSession(
                store=store, live_cfg=live_cfg, decision=decision
            )
        finally:
            store.close()


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
        lease_cm.__exit__(None, None, None)

    try:
        live_cfg = config_mod.load_config(path)
        index = live_cfg.get("index") if isinstance(live_cfg.get("index"), dict) else {}
        chroma_dir = index.get("chroma_dir")
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
        return ProductionWriteSession(
            store=store, live_cfg=live_cfg, decision=decision
        )
    except Exception:
        _release()
        raise
