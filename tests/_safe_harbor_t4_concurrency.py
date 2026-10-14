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
        chunk = os.read(fd, 4096)
        if not chunk:
            raise EOFError(f"unexpected EOF on fd {fd}")
        buffer.extend(chunk)
    line, _, _ = bytes(buffer).partition(b"\n")
    return line.decode().strip()


# pylint: enable=duplicate-code

def _write_line_fd(fd: int, text: str) -> None:
    payload = text if text.endswith("\n") else f"{text}\n"
    os.write(fd, payload.encode())


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


def _install_ool_fcntl_tracker(lock_path: str) -> Callable[[], None]:
    real_flock = fcntl.flock

    def tracking_flock(fd: int, operation: int) -> None:
        key = lock_path if os.readlink(f"/proc/self/fd/{fd}") == lock_path else ""
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

    real = chroma_write_guard._exclusive_flock
    if os.environ.get("SAFE_HARBOR_T4_COMPETE_SIGNAL_WRITE_FD"):
        signal_write = _signal_fd("SAFE_HARBOR_T4_COMPETE_SIGNAL_WRITE_FD")
    else:
        signal_write = _signal_fd("SAFE_HARBOR_T4_SIGNAL_WRITE_FD")

    @contextmanager
    def wrapped(path: Path, timeout_seconds: float):
        key = str(path)
        if key == lock_path:
            _write_line_fd(signal_write, "PRE_FLOCK")
            if _lock_nb_probe(lock_path):
                _write_line_fd(signal_write, "NB_FREE")
            else:
                _write_line_fd(signal_write, "NB_BLOCKED")
        with real(path, timeout_seconds):
            if key == lock_path:
                _write_line_fd(signal_write, "ACQUIRED")
            yield

    chroma_write_guard._exclusive_flock = wrapped
    try:
        yield
    finally:
        chroma_write_guard._exclusive_flock = real


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

    with production_chroma_write_session(entrypoint="tests.t4_concurrency_seed") as session:
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
        with production_chroma_write_session(entrypoint="refine.apply_dedupe") as session:
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
) -> tuple[Callable[[], None], Callable[[], None]]:
    import propose_decision

    real_classify = propose_decision._recovery_classify_live
    restore_fcntl = _install_ool_fcntl_tracker(lock_path)
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
            _ool_release_tracked_lock(lock_path)
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
    restore_all, _ = _install_faulty_classify_hooks(lock_path, saved)
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


def parse_worker_stdout(
    proc: subprocess.CompletedProcess[str] | subprocess.Popen[str],
    *,
    timeout: float = CHILD_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if isinstance(proc, subprocess.Popen):
        out, err = proc.communicate(timeout=timeout)
        stdout = out or ""
        stderr = err or ""
        rc = proc.returncode
    else:
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        rc = proc.returncode
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"worker empty stdout rc={rc} stderr={stderr}")
    payload = json.loads(lines[-1])
    payload["_worker_rc"] = rc
    payload["_worker_stderr"] = stderr
    return payload


def terminate_worker(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.kill()
        proc.communicate(timeout=5)


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


def write_go(fd: int, text: str = "GO") -> None:
    _write_line_fd(fd, text)


def main(argv: list[str] | None = None) -> int:
    return _dispatch(argv or sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
