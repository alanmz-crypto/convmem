# pylint: disable=protected-access,too-many-lines
"""Subprocess worker + parent orchestration for T4 real concurrency evidence."""

from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import select
import subprocess
import sys
import time
from contextlib import contextmanager
from unittest import mock
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve()
T2_RUNNER = ROOT / "tests" / "_safe_harbor_t2_cli.py"
PYTHON_CHILD = [sys.executable, "-s", "-B"]
BARRIER_TIMEOUT_SECONDS = 20.0
CHILD_TIMEOUT_SECONDS = 90.0

_OOL_TRACKED_LOCK_FD: dict[str, int] = {}


# pylint: disable=duplicate-code
# Child stdlib entry must establish isolation before any project package imports.
def _load_bootstrap():
    path = ROOT / "tests" / "_safe_harbor_bootstrap.py"
    spec = importlib.util.spec_from_file_location("safe_harbor_t4_bootstrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bootstrap from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture_root() -> Path:
    raw = os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", "").strip()
    if not raw:
        raise RuntimeError("SAFE_HARBOR_T3_FIXTURE_ROOT required")
    return Path(raw).resolve(strict=False)


def _refuse_outside_fixture(path: Path) -> Path:
    root = _fixture_root()
    resolved = path.expanduser().resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise RuntimeError(f"refusing path outside fixture root: {resolved}")
    return resolved


def _require_child_isolation() -> None:
    bootstrap = _load_bootstrap()
    bootstrap.require_t3_bootstrap()
    if not getattr(sys, "_safe_harbor_t4_network_refused", False):
        raise RuntimeError("T4 network refusal hook missing before project imports")
    backend = bootstrap.load_stdlib_module(
        ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
        "safe_harbor_t4_concurrency_isolation",
    )
    backend._require_isolated()


# pylint: enable=duplicate-code

def _install_fakes():
    from tests._safe_harbor_t4_common import _install_fakes as shared
    return shared()


def _emit(payload: dict[str, Any], *, rc: int = 0) -> int:
    print(json.dumps(payload, sort_keys=True))
    return rc


def _load_cfg():
    from tests._safe_harbor_t4_common import _load_cfg as shared
    return shared()


def _dump_state(cfg):
    from tests._safe_harbor_t4_common import _dump_state as shared
    return shared(cfg)


def _guard_lock_path(cfg: dict) -> str:
    from chroma_write_guard import ChromaWriteGuard

    return str(ChromaWriteGuard(cfg["index"]["chroma_dir"]).lock_path)


def _read_line_fd(fd: int, *, timeout: float = BARRIER_TIMEOUT_SECONDS) -> str:
    buffer = bytearray()
    deadline = time.monotonic() + timeout
    while b"\n" not in buffer:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timed out waiting for line on fd {fd}")
        # pylint: disable=duplicate-code
        # Independent bounded pipe barrier, shared shape with existing T1 fixture.
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            continue
        chunk = os.read(fd, 1)
        if not chunk:
            raise EOFError(f"unexpected EOF on fd {fd}")
        buffer.extend(chunk)
    line, _, _ = bytes(buffer).partition(b"\n")
    return line.decode().strip()


def _read_line_fd_lossy(fd: int, *, timeout: float = BARRIER_TIMEOUT_SECONDS) -> str:
    """Historical T5-F1 reader: one large read drops bytes after the first newline."""
    # pylint: disable=duplicate-code
    # Keep the historical reader verbatim as an independent sensitivity control.
    buffer = bytearray()
    deadline = time.monotonic() + timeout
    while b"\n" not in buffer:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timed out waiting for line on fd {fd}")
        readable, _, _ = select.select([fd], [], [], remaining)
        if not readable:
            continue
        chunk = os.read(fd, 4096)
        if not chunk:
            raise EOFError(f"unexpected EOF on fd {fd}")
        buffer.extend(chunk)
    line, _, _ = bytes(buffer).partition(b"\n")
    return line.decode().strip()


# pylint: enable=duplicate-code

def _write_line_fd(fd: int, text: str) -> None:
    payload = text if text.endswith("\n") else f"{text}\n"
    data = payload.encode()
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError(f"failed to write line to fd {fd}")
        view = view[written:]


def _signal_fd(name: str) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise RuntimeError(f"{name} required")
    return int(raw)


def _lock_nb_probe(lock_path: str) -> bool:
    path = _refuse_outside_fixture(Path(lock_path))
    fd = os.open(str(path), os.O_RDONLY | os.O_CREAT)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return True
        except BlockingIOError:
            return False
    finally:
        os.close(fd)


def _install_ool_fcntl_tracker(lock_path: str, *extra_paths: str) -> Callable[[], None]:
    real_flock = fcntl.flock
    tracked = {lock_path, *extra_paths}

    def tracking_flock(fd: int, operation: int) -> None:
        target = os.readlink(f"/proc/self/fd/{fd}")
        key = target if target in tracked else ""
        if key and (operation & fcntl.LOCK_EX):
            _OOL_TRACKED_LOCK_FD[key] = fd
        if key and (operation & fcntl.LOCK_UN):
            _OOL_TRACKED_LOCK_FD.pop(key, None)
        real_flock(fd, operation)

    fcntl.flock = tracking_flock

    def restore() -> None:
        fcntl.flock = real_flock
        _OOL_TRACKED_LOCK_FD.clear()

    return restore


def _ool_release_tracked_lock(lock_path: str) -> None:
    fd = _OOL_TRACKED_LOCK_FD.get(lock_path)
    if fd is None:
        raise RuntimeError("OOL gap requested but guard flock fd was not tracked")
    fcntl.flock(fd, fcntl.LOCK_UN)
    _OOL_TRACKED_LOCK_FD.pop(lock_path, None)


@contextmanager
def _install_competitor_flock_observer(lock_path: str):
    """Signal PRE_FLOCK + NB probe, then real blocking flock; ACQUIRED after real acquire."""
    import chroma_write_guard
    import purge_locks

    real = chroma_write_guard._exclusive_flock
    real_index = purge_locks.index_write_flock
    if os.environ.get("SAFE_HARBOR_T4_COMPETE_SIGNAL_WRITE_FD"):
        signal_write = _signal_fd("SAFE_HARBOR_T4_COMPETE_SIGNAL_WRITE_FD")
    else:
        signal_write = _signal_fd("SAFE_HARBOR_T4_SIGNAL_WRITE_FD")
    signalled = {"done": False}

    @contextmanager
    def observe(probe_path: str, acquire):
        first = not signalled["done"]
        if first:
            _write_line_fd(signal_write, "PRE_FLOCK")
            if _lock_nb_probe(probe_path):
                _write_line_fd(signal_write, "NB_FREE")
            else:
                _write_line_fd(signal_write, "NB_BLOCKED")
        with acquire() as held:
            if first:
                signalled["done"] = True
                _write_line_fd(signal_write, "ACQUIRED")
            yield held

    @contextmanager
    def wrapped(path: Path, timeout_seconds: float):
        if str(path) != lock_path:
            with real(path, timeout_seconds) as held:
                yield held
            return
        with observe(lock_path, lambda: real(path, timeout_seconds)) as held:
            yield held

    @contextmanager
    def wrapped_index(cfg: dict):
        # Writers take the store-wide index write lock (C1) before the guard flock,
        # so a competitor first blocks there while recovery holds both.
        if purge_locks.index_write_lock_depth() > 0:
            with real_index(cfg) as held:
                yield held
            return
        index_lock = str(Path(purge_locks.index_write_lock_path(cfg)).resolve())
        if signalled["done"] or _lock_nb_probe(index_lock):
            # Uncontended C1: signal at the guard flock as before.
            with real_index(cfg) as held:
                yield held
            return
        with observe(index_lock, lambda: real_index(cfg)) as held:
            yield held

    chroma_write_guard._exclusive_flock = wrapped
    purge_locks.index_write_flock = wrapped_index
    try:
        yield
    finally:
        chroma_write_guard._exclusive_flock = real
        purge_locks.index_write_flock = real_index


def _invoke_forget_cli(unit_id: str) -> None:
    import convmem
    from typer.testing import CliRunner

    result = CliRunner().invoke(
        convmem.app,
        ["forget", unit_id, "-y", "--reason", "t4-concurrency"],
    )
    if result.exit_code != 0:
        raise RuntimeError(
            f"forget cli failed rc={result.exit_code}: {result.stdout} {result.stderr}"
        )


def _canonical_seed_unit_id(cfg: dict) -> str:
    state = _dump_state(cfg)
    for unit in state.get("chroma", {}).get("units") or []:
        if unit.get("id") == "seed-0":
            return "seed-0"
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock

    with index_write_flock(cfg), production_chroma_write_session(entrypoint="tests.t4_concurrency_seed") as session:
        store = session.store
        store.add_unit(
            "seed-0",
            "seed unit",
            [0.25] * 768,
            {
                "id": "seed-0",
                "title": "Seed",
                "ledger_id": "obs_seed_0",
                "type": "observation",
            },
        )
    return "seed-0"


def _mode_validate_isolation() -> dict[str, Any]:
    _require_child_isolation()
    return {"verdict": "PASS", "isolated": True}


def _mode_snapshot() -> dict[str, Any]:
    cfg = _load_cfg()
    state = _dump_state(cfg)
    units = state.get("chroma", {}).get("units") or []
    digest = hashlib.sha256(
        json.dumps(units, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {"verdict": "PASS", "state": state, "units_digest": digest}


def _mode_probe_lock_nb() -> dict[str, Any]:
    lock_path = os.environ.get("SAFE_HARBOR_T4_LOCK_PATH", "").strip()
    if not lock_path:
        raise RuntimeError("SAFE_HARBOR_T4_LOCK_PATH required")
    acquired = _lock_nb_probe(lock_path)
    return {"verdict": "PASS", "acquired": acquired, "lock_path": lock_path}



def _mode_recover_wait_config(proposal_id: str) -> dict[str, Any]:
    import convmem
    from typer.testing import CliRunner
    with _install_competitor_flock_observer(os.environ["SAFE_HARBOR_T4_LOCK_PATH"]):
        result = CliRunner().invoke(convmem.app, ["record", "--recover", proposal_id])
    return {"verdict": "OK", "cli_rc": result.exit_code, "output": result.output}

def _mode_recover(proposal_id: str) -> dict[str, Any]:
    from propose_decision import recover_approval

    cfg = _load_cfg()
    action = recover_approval(cfg, proposal_id.strip())
    after = _dump_state(cfg)
    return {"verdict": "OK", "action": action, "state": after}


def _mode_recover_refused(proposal_id: str) -> dict[str, Any]:
    from propose_decision import recover_approval

    cfg = _load_cfg()
    try:
        recover_approval(cfg, proposal_id.strip())
    except ValueError as exc:
        after = _dump_state(cfg)
        return {"verdict": "REFUSED", "error": str(exc), "state": after}
    after = _dump_state(cfg)
    return {
        "verdict": "UNEXPECTED_OK",
        "error": "recovery succeeded when refusal expected",
        "state": after,
    }


def _install_recover_held_hooks(captured: dict[str, Any]) -> Callable[[], None]:
    import chroma_write_guard
    import propose_decision

    real_classify = propose_decision._recovery_classify_live
    real_finalize = chroma_write_guard.ChromaWriteGuard.finalize_approval_recovery
    signal_write = _signal_fd("SAFE_HARBOR_T4_SIGNAL_WRITE_FD")
    continue_read = _signal_fd("SAFE_HARBOR_T4_CONTINUE_READ_FD")
    calls = {"n": 0}

    def classify(store, ledger_id: str) -> dict[str, Any]:
        calls["n"] += 1
        live = real_classify(store, ledger_id)
        if calls["n"] == 1:
            _write_line_fd(signal_write, "INSPECTED")
            _read_line_fd(continue_read)
        return live

    def finalize(self) -> None:
        real_finalize(self)
        captured["state"] = _dump_state(_load_cfg())

    propose_decision._recovery_classify_live = classify
    chroma_write_guard.ChromaWriteGuard.finalize_approval_recovery = finalize

    def restore() -> None:
        propose_decision._recovery_classify_live = real_classify
        chroma_write_guard.ChromaWriteGuard.finalize_approval_recovery = real_finalize

    return restore


def _mode_recover_held(proposal_id: str) -> dict[str, Any]:
    from propose_decision import recover_approval

    cfg = _load_cfg()
    os.environ["SAFE_HARBOR_T4_LOCK_PATH"] = _guard_lock_path(cfg)
    os.environ["SAFE_HARBOR_T4_RECOVER_HELD"] = "1"
    captured: dict[str, Any] = {}
    restore = _install_recover_held_hooks(captured)
    try:
        action = recover_approval(cfg, proposal_id.strip())
    finally:
        restore()
    state = captured.get("state") or _dump_state(cfg)
    return {"verdict": "OK", "action": action, "state": state, "captured_under_lock": bool(captured)}


def _mode_forget_cli(unit_id: str) -> dict[str, Any]:
    cfg = _load_cfg()
    lock_path = _guard_lock_path(cfg)
    os.environ["SAFE_HARBOR_T4_LOCK_PATH"] = lock_path
    if os.environ.get("SAFE_HARBOR_T4_PRE_FLOCK", "1") == "1":
        with _install_competitor_flock_observer(lock_path):
            _invoke_forget_cli(unit_id.strip())
    else:
        _invoke_forget_cli(unit_id.strip())
    after = _dump_state(cfg)
    return {"verdict": "OK", "state": after}


def _mode_refine_apply() -> dict[str, Any]:
    from chroma_write_store import production_chroma_write_session
    from refine import apply_dedupe_queue_record

    cfg = _load_cfg()
    lock_path = _guard_lock_path(cfg)
    os.environ["SAFE_HARBOR_T4_LOCK_PATH"] = lock_path
    tombstone_id = os.environ.get("SAFE_HARBOR_T4_TOMBSTONE_ID", "").strip()
    canonical_id = os.environ.get("SAFE_HARBOR_T4_CANONICAL_ID", "").strip()
    if not tombstone_id:
        raise RuntimeError("SAFE_HARBOR_T4_TOMBSTONE_ID required")
    if not canonical_id:
        canonical_id = _canonical_seed_unit_id(cfg)
    record = {
        "status": "approved_merge_a_canonical",
        "tombstone_id": tombstone_id,
        "canonical_id": canonical_id,
        "chroma_applied": False,
    }
    if os.environ.get("SAFE_HARBOR_T4_PRE_FLOCK", "1") == "1":
        ctx = _install_competitor_flock_observer(lock_path)
    else:
        from contextlib import nullcontext

        ctx = nullcontext()
    with ctx:
        from purge_locks import index_write_flock

        with index_write_flock(cfg), production_chroma_write_session(entrypoint="refine.apply_dedupe") as session:
            stats = apply_dedupe_queue_record(session.store, cfg, record, verbose=False)
    if stats.get("errors"):
        raise RuntimeError(f"apply_dedupe_queue_record errors: {stats}")
    if stats.get("tombstoned", 0) < 1:
        raise RuntimeError(f"expected tombstone stats: {stats}")
    after = _dump_state(cfg)
    return {
        "verdict": "OK",
        "stats": stats,
        "state": after,
        "canonical_id": canonical_id,
    }


def _install_faulty_classify_hooks(
    lock_path: str,
    saved: dict[str, Any],
    index_lock_path: str,
) -> tuple[Callable[[], None], Callable[[], None]]:
    import propose_decision

    real_classify = propose_decision._recovery_classify_live
    restore_fcntl = _install_ool_fcntl_tracker(lock_path, index_lock_path)
    signal_write = _signal_fd("SAFE_HARBOR_T4_SIGNAL_WRITE_FD")
    gap_read = _signal_fd("SAFE_HARBOR_T4_GAP_READ_FD")
    calls = {"n": 0}

    def classify(store, ledger_id: str) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            live = real_classify(store, ledger_id)
            saved["live"] = live
            _write_line_fd(signal_write, "INSPECTED")
            _read_line_fd(gap_read)
            # Out of every lock: recovery also holds the store-wide index write lock (C1).
            _ool_release_tracked_lock(lock_path)
            _ool_release_tracked_lock(index_lock_path)
            _write_line_fd(signal_write, "GAP")
            _read_line_fd(gap_read)
            return live
        if "live" in saved:
            return saved["live"]
        return real_classify(store, ledger_id)

    propose_decision._recovery_classify_live = classify

    def restore_classify() -> None:
        propose_decision._recovery_classify_live = real_classify

    def restore_all() -> None:
        restore_classify()
        restore_fcntl()

    return restore_all, restore_classify


def _mode_recover_faulty_oool(proposal_id: str) -> dict[str, Any]:
    from propose_decision import recover_approval

    cfg = _load_cfg()
    lock_path = _guard_lock_path(cfg)
    os.environ["SAFE_HARBOR_T4_LOCK_PATH"] = lock_path
    os.environ["SAFE_HARBOR_T4_FAULTY_OOL"] = "1"
    saved: dict[str, Any] = {}
    from purge_locks import index_write_lock_path

    index_lock_path = str(Path(index_write_lock_path(cfg)).resolve())
    restore_all, _ = _install_faulty_classify_hooks(lock_path, saved, index_lock_path)
    verdict = "OK"
    action = ""
    err = ""
    try:
        action = recover_approval(cfg, proposal_id.strip())
    except ValueError as exc:
        verdict = "REFUSED"
        err = str(exc)
    finally:
        restore_all()
    after = _dump_state(cfg)
    return {
        "verdict": verdict,
        "action": action,
        "error": err,
        "state": after,
        "faulty": True,
        "stale_classify": "live" in saved,
    }


MODES: dict[str, Callable[[], dict[str, Any]]] = {
    "validate-isolation": _mode_validate_isolation,
    "snapshot": _mode_snapshot,
    "probe-lock-nb": _mode_probe_lock_nb,
}


def _dispatch(argv: list[str]) -> int:
    _require_child_isolation()
    _refuse_outside_fixture(Path(os.environ.get("CONVMEM_CONFIG", ".")))
    if not argv:
        return _emit({"verdict": "FAIL", "error": "missing mode"}, rc=2)
    mode = argv[0]
    rest = argv[1:]
    if mode != "validate-isolation" and not os.environ.get("SAFE_HARBOR_T2_NOW"):
        return _emit({"verdict": "FAIL", "error": "SAFE_HARBOR_T2_NOW required"}, rc=2)
    sys.path.insert(0, str(ROOT))
    if mode != "validate-isolation":
        _install_fakes()
    try:
        if mode in MODES:
            return _emit(MODES[mode]())
        if mode == "recover":
            return _emit(_mode_recover(rest[0]))
        if mode == "recover-wait-config":
            return _emit(_mode_recover_wait_config(rest[0]))
        if mode == "recover-refused":
            return _emit(_mode_recover_refused(rest[0]))
        if mode == "recover-held":
            return _emit(_mode_recover_held(rest[0]))
        if mode == "forget-cli":
            return _emit(_mode_forget_cli(rest[0]))
        if mode == "refine-apply":
            return _emit(_mode_refine_apply())
        if mode == "recover-faulty-oool":
            return _emit(_mode_recover_faulty_oool(rest[0]))
        return _emit({"verdict": "FAIL", "error": f"unknown mode {mode}"}, rc=2)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return _emit({"verdict": "FAIL", "error": str(exc), "mode": mode}, rc=1)


def worker_env(cli, extra: dict[str, str] | None = None) -> dict[str, str]:
    from tests._safe_harbor_t4_harness import assert_cli_confined

    assert_cli_confined(cli)
    env = dict(os.environ)
    env.setdefault("SAFE_HARBOR_T3_BOOTSTRAPPED", "1")
    if "SAFE_HARBOR_T3_EXPECTED_UID" not in env:
        raise RuntimeError("SAFE_HARBOR_T3_EXPECTED_UID must be inherited from launcher")
    env.setdefault(
        "SAFE_HARBOR_T3_FIXTURE_ROOT",
        os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", str(cli.s.root)),
    )
    env["CONVMEM_CONFIG"] = str(cli.config)
    if extra:
        env.update(extra)
    return env


def spawn_worker(
    cli,
    mode: str,
    worker_args: tuple[str, ...] = (),
    *,
    extra_env: dict[str, str] | None = None,
    pass_fds: tuple[int, ...] = (),
    timeout: float = CHILD_TIMEOUT_SECONDS,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    env = worker_env(cli, extra=extra_env)
    cmd = [*PYTHON_CHILD, str(WORKER), mode, *worker_args]
    from tests._safe_harbor_t4_harness import run_fixture_child
    proc = run_fixture_child(
        cmd,
        env=env,
        timeout=timeout,
        pass_fds=pass_fds or (),
    )
    if proc.returncode is None:
        raise RuntimeError("worker missing returncode")
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(
            f"worker empty stdout mode={mode} rc={proc.returncode} stderr={proc.stderr}"
        )
    payload = json.loads(lines[-1])
    payload["_worker_rc"] = proc.returncode
    payload["_worker_stderr"] = proc.stderr
    return proc, payload


def spawn_worker_popen(
    cli,
    mode: str,
    worker_args: tuple[str, ...] = (),
    *,
    extra_env: dict[str, str] | None = None,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.Popen[str]:
    env = worker_env(cli, extra=extra_env)
    cmd = [*PYTHON_CHILD, str(WORKER), mode, *worker_args]
    return subprocess.Popen(
        cmd,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        pass_fds=pass_fds,
    )


def collect_popen_output(
    proc: subprocess.Popen[str],
    *,
    timeout: float = CHILD_TIMEOUT_SECONDS,
    kill_if_running: bool = False,
) -> tuple[str, str, int | None, dict[str, Any]]:
    """Gather once, retrying after kill only to drain a timed-out child's pipes."""
    meta: dict[str, Any] = {"returncode_before_gather": proc.poll()}
    if kill_if_running and proc.poll() is None:
        proc.kill()
        meta["killed_before_gather"] = True
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        meta["communicate_timeout"] = True
        meta["returncode_on_timeout"] = proc.poll()
        partial_out = exc.stdout or ""
        partial_err = exc.stderr or ""
        if proc.poll() is None:
            proc.kill()
            meta["killed_after_timeout"] = True
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired as exc2:
            meta["gather_failed_after_kill"] = True
            out = (exc2.stdout or partial_out or "") if exc2.stdout or partial_out else ""
            err = (exc2.stderr or partial_err or "") if exc2.stderr or partial_err else ""
        else:
            out = out or partial_out
            err = err or partial_err
    meta["returncode_after_gather"] = proc.returncode
    # TimeoutExpired may expose bytes even when Popen uses text=True.
    def as_text(value: str | bytes | None) -> str:
        return value.decode(errors="replace") if isinstance(value, bytes) else value or ""

    return as_text(out), as_text(err), proc.returncode, meta


@dataclass
class WorkerChildDiagnostic:
    """Retain worker stdout/stderr/returncode; one gather per process."""

    label: str
    proc: subprocess.Popen[str] | subprocess.CompletedProcess[str] | None = None
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    annotations: dict[str, Any] = field(default_factory=dict)
    _gathered: bool = False

    def ingest(
        self,
        stdout: str,
        stderr: str,
        returncode: int | None,
        **annotations: Any,
    ) -> None:
        if self._gathered:
            return
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.annotations.update(annotations)
        self._gathered = True

    def annotate(self, **extra: Any) -> None:
        self.annotations.update(extra)

    def finalize(
        self,
        *,
        timeout: float = CHILD_TIMEOUT_SECONDS,
        kill_if_running: bool = True,
    ) -> None:
        if self._gathered:
            return
        proc = self.proc
        if proc is None:
            self._gathered = True
            return
        if isinstance(proc, subprocess.CompletedProcess):
            self.ingest(proc.stdout or "", proc.stderr or "", proc.returncode)
            return
        if proc.stdout is None and proc.stderr is None:
            self.ingest("", "", proc.returncode)
            return
        stdout, stderr, rc, meta = collect_popen_output(
            proc, timeout=timeout, kill_if_running=kill_if_running
        )
        self.ingest(stdout, stderr, rc, **meta)

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "annotations": self.annotations,
        }


def attach_worker_diagnostic(
    proc: subprocess.Popen[str] | subprocess.CompletedProcess[str] | None,
    label: str,
) -> WorkerChildDiagnostic:
    return WorkerChildDiagnostic(label=label, proc=proc)


def parse_worker_stdout(
    proc: subprocess.CompletedProcess[str] | subprocess.Popen[str],
    *,
    timeout: float = CHILD_TIMEOUT_SECONDS,
    diagnostic: WorkerChildDiagnostic | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    if isinstance(proc, subprocess.Popen):
        if diagnostic is not None and diagnostic._gathered:
            stdout = diagnostic.stdout
            stderr = diagnostic.stderr
            rc = diagnostic.returncode
            meta = diagnostic.annotations
        else:
            stdout, stderr, rc, meta = collect_popen_output(
                proc, timeout=timeout, kill_if_running=False
            )
            if diagnostic is not None:
                diagnostic.ingest(stdout, stderr, rc, **meta)
    else:
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        rc = proc.returncode
        if diagnostic is not None:
            diagnostic.ingest(stdout, stderr, rc)
    if meta.get("communicate_timeout"):
        # Complete-looking output does not turn a timed-out worker into success.
        raise subprocess.TimeoutExpired(proc.args, timeout, output=stdout, stderr=stderr)
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        if diagnostic is not None:
            diagnostic.annotate(parse_error="empty_stdout")
        raise RuntimeError(f"worker empty stdout rc={rc} stderr={stderr}")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        if diagnostic is not None:
            diagnostic.annotate(parse_error=str(exc), malformed_tail=lines[-1][:240])
        raise RuntimeError(
            f"worker malformed json rc={rc} stderr={stderr} tail={lines[-1][:240]}"
        ) from exc
    payload["_worker_rc"] = rc
    payload["_worker_stderr"] = stderr
    return payload


def terminate_worker(
    proc: subprocess.Popen[str] | None,
    *,
    diagnostic: WorkerChildDiagnostic | None = None,
) -> None:
    if proc is None:
        if diagnostic is not None and not diagnostic._gathered:
            diagnostic.finalize(kill_if_running=False)
        return
    if diagnostic is not None and not diagnostic._gathered:
        diagnostic.finalize(kill_if_running=True)
        return
    if proc.poll() is None:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


@dataclass
class RaceTrace:
    parent_stages: dict[str, float] = field(default_factory=dict)
    signals: list[dict[str, Any]] = field(default_factory=list)
    holder_polls: list[dict[str, Any]] = field(default_factory=list)
    cleanup_errors: list[str] = field(default_factory=list)

    def stage(self, name: str) -> None:
        self.parent_stages[name] = time.monotonic()

    def record_signal(self, label: str, value: str) -> None:
        self.signals.append(
            {"label": label, "value": value, "t": time.monotonic()}
        )


def read_tracked_event(
    fd: int,
    trace: RaceTrace,
    label: str,
    *,
    timeout: float = BARRIER_TIMEOUT_SECONDS,
) -> str:
    value = _read_line_fd(fd, timeout=timeout)
    trace.record_signal(label, value)
    return value


def cleanup_race_workers(
    *,
    rec_proc: subprocess.Popen[str] | None,
    comp_proc: subprocess.Popen[str] | None,
    rec_diag: WorkerChildDiagnostic,
    comp_diag: WorkerChildDiagnostic,
    open_fds: list[int],
    trace: RaceTrace,
) -> None:
    for label, proc, diag in (
        ("recovery", rec_proc, rec_diag),
        ("competitor", comp_proc, comp_diag),
    ):
        try:
            terminate_worker(proc, diagnostic=diag)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            trace.cleanup_errors.append(f"{label} cleanup: {type(exc).__name__}: {exc}")
    try:
        close_fds(open_fds)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        trace.cleanup_errors.append(f"close_fds: {type(exc).__name__}: {exc}")


def persist_race_packet(
    cli,
    stem: str,
    trace: RaceTrace,
    *,
    race: str,
    competitor: str,
    proposal_id: str,
    children: dict[str, WorkerChildDiagnostic],
    race_exc: BaseException | None,
) -> Path:
    payload: dict[str, Any] = {
        "race": race,
        "competitor": competitor,
        "proposal_id": proposal_id,
        "outcome": "failure" if race_exc or trace.cleanup_errors else "success",
        "parent_stages": trace.parent_stages,
        "signals": trace.signals,
        "holder_polls": trace.holder_polls,
        "children": {key: diag.as_dict() for key, diag in children.items()},
        "cleanup_errors": trace.cleanup_errors,
    }
    if race_exc is not None:
        payload["failure"] = f"{type(race_exc).__name__}: {race_exc}"
    path = write_race_diagnostic(cli, stem, payload)
    print(compact_race_diagnostic_summary(path, payload), flush=True)
    return path


def finish_race_run(
    cli,
    stem: str,
    trace: RaceTrace,
    *,
    race: str,
    competitor: str,
    proposal_id: str,
    children: dict[str, WorkerChildDiagnostic],
    race_exc: BaseException | None,
) -> None:
    try:
        persist_race_packet(
            cli, stem, trace, race=race, competitor=competitor,
            proposal_id=proposal_id, children=children, race_exc=race_exc,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        detail = f"diagnostic publication failed: {type(exc).__name__}: {exc}"
        print(json.dumps({"error": detail, "children": {
            key: diag.as_dict() for key, diag in children.items()
        }, "signals": trace.signals, "holder_polls": trace.holder_polls,
            "cleanup_errors": trace.cleanup_errors}), file=sys.stderr, flush=True)
        if race_exc is not None:
            race_exc.add_note(detail)
            raise race_exc from exc
        raise
    if race_exc is not None:
        raise race_exc
    if trace.cleanup_errors:
        raise RuntimeError(
            "race cleanup failed: " + "; ".join(trace.cleanup_errors)
        )


@contextmanager
def pipe_read_fragment_delivery(read_fd: int, write_fd: int, fragments: list[bytes]):
    """Deliver pipe bytes one fragment at a time as the reader consumes them."""
    if not fragments:
        raise ValueError("fragments required")
    real_read = os.read
    os.write(write_fd, fragments[0])
    pending = fragments[0]
    pending_offset = 0
    next_idx = 1

    def delivering_read(fd: int, n: int) -> bytes:
        nonlocal pending, pending_offset, next_idx
        if fd != read_fd:
            return real_read(fd, n)
        chunk = real_read(fd, n)
        if not chunk:
            return chunk
        pending_offset += len(chunk)
        if pending_offset >= len(pending):
            if next_idx < len(fragments):
                pending = fragments[next_idx]
                pending_offset = 0
                next_idx += 1
                os.write(write_fd, pending)
        return chunk

    with mock.patch("os.read", delivering_read):
        yield


def race_diagnostic_path(cli, stem: str) -> Path:
    from tests._safe_harbor_t4_harness import assert_cli_confined

    assert_cli_confined(cli)
    root = Path(cli.s.root).resolve(strict=False)
    digest = hashlib.sha256(stem.encode()).hexdigest()[:12]
    path = (root / f"safe_harbor_t4_race_{digest}.json").resolve(strict=False)
    if path != root and root not in path.parents:
        raise RuntimeError(f"refusing race diagnostic outside fixture root: {path}")
    return path


def write_race_diagnostic(
    cli,
    stem: str,
    payload: dict[str, Any],
) -> Path:
    path = race_diagnostic_path(cli, stem)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return path


def compact_race_diagnostic_summary(path: Path, payload: dict[str, Any]) -> str:
    children = payload.get("children") or {}
    labels = ",".join(sorted(children))
    stages = payload.get("parent_stages") or {}
    last_stage = max(stages, key=stages.get) if stages else "none"
    return (
        f"race_diag path={path} children={labels} "
        f"last_stage={last_stage} competitor={payload.get('competitor', '?')}"
    )


def assert_holder_live(
    proc: subprocess.Popen[str] | None,
    *,
    stage: str,
    trace: RaceTrace,
) -> None:
    rc = proc.poll() if proc is not None else None
    trace.holder_polls.append(
        {"stage": stage, "t": time.monotonic(), "returncode": rc}
    )
    trace.parent_stages[f"holder_poll_{stage}"] = trace.holder_polls[-1]["t"]
    if proc is None:
        raise AssertionError(f"holder missing at {stage}")
    assert rc is None, f"holder exited before {stage} rc={rc}"


def close_fds(fds: list[int]) -> None:
    for fd in fds:
        try:
            os.close(fd)
        except OSError:
            pass


def lock_path_for_cli(cli) -> str:
    from tests._safe_harbor_t4_harness import assert_cli_confined
    from chroma_write_guard import ChromaWriteGuard

    assert_cli_confined(cli)
    return str(ChromaWriteGuard(cli.s.chroma).lock_path)


def seed_canonical_id(cli) -> str:
    state = cli.dump()
    for unit in state.get("chroma", {}).get("units") or []:
        if unit.get("id") == "seed-0":
            return "seed-0"
    raise AssertionError("fixture seed unit seed-0 missing from chroma dump")


def unit_for_proposal(state: dict, proposal_id: str) -> dict:
    for unit in state.get("chroma", {}).get("units") or []:
        if (unit.get("metadata") or {}).get("proposal_id") == proposal_id:
            return unit
    raise AssertionError(f"no chroma unit for proposal {proposal_id}")


def unit_by_id(state: dict, unit_id: str) -> dict:
    for unit in state.get("chroma", {}).get("units") or []:
        if unit.get("id") == unit_id:
            return unit
    raise AssertionError(f"no chroma unit id {unit_id}")


def corpus_triplet(unit: dict) -> dict[str, Any]:
    meta = unit.get("metadata") or {}
    return {
        "id": unit.get("id"),
        "document": unit.get("document"),
        "embedding_sha": unit.get("embedding_sha"),
        "metadata": meta,
        "content_hash": meta.get("content_hash"),
    }


def assert_child_isolation(cli, extra_env: dict[str, str] | None = None) -> None:
    proc, payload = spawn_worker(cli, "validate-isolation", extra_env=extra_env or {})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload.get("verdict") == "PASS", payload


def read_event(fd: int, *, timeout: float = BARRIER_TIMEOUT_SECONDS) -> str:
    return _read_line_fd(fd, timeout=timeout)


def read_event_lossy(fd: int, *, timeout: float = BARRIER_TIMEOUT_SECONDS) -> str:
    return _read_line_fd_lossy(fd, timeout=timeout)


def write_go(fd: int, text: str = "GO") -> None:
    _write_line_fd(fd, text)


def main(argv: list[str] | None = None) -> int:
    return _dispatch(argv or sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
