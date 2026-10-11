# pylint: disable=redefined-outer-name,too-many-locals
"""Issue #268 D1 scratch harness — hermetic tests only (no D2 replay)."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import socket
import stat
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

from live_diagnosis import (
    LiveDiagnosisRefused,
    bootstrap_index_child,
    bootstrap_watch_worker,
    teardown_hermetic_guards,
)
from tests.watch_oom_exposure_index_e2e_support import PathCanary, snapshot_canaries
from tests.watch_oom_live_diagnosis_dual_boundary import parse_systemd_memory
from tests.watch_oom_live_diagnosis_parent import (
    D2_KERNEL_ISOLATION_BLOCKER,
    require_telemetry_after_kill,
    run_d1_capped_worker,
)
from tests.watch_oom_live_diagnosis_support import (
    PHASE_ORDER,
    ScratchCanary,
    arm_diagnosis_env,
    assert_no_production_writer_collision,
    assert_parent_production_canaries_unchanged,
    assert_scratch_canaries_unchanged,
    build_prefix_transcript,
    prepare_scratch_arm,
    production_canary_drift_lines,
    read_phases,
    snapshot_production_canaries_for_parent,
    verify_backup_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().parent / "watch_oom_live_diagnosis_worker.py"
RUN_CGROUP = os.environ.get("CONVMEM_D1_CGROUP") == "1"
SCRATCH_BASE = ROOT / "tests" / ".d1-scratch-arms"


def _worker_command(layout: dict) -> list[str]:
    return [
        sys.executable,
        str(WORKER),
        "--mode",
        "prefix_route",
        "--scratch-root",
        str(layout["scratch_root"]),
        "--config-path",
        str(layout["config_path"]),
        "--source",
        str(layout["source"]),
        "--source-sha256",
        layout["source_sha256"],
        "--chroma-dir",
        str(layout["chroma_dir"]),
        "--brief-path",
        str(layout["brief_path"]),
        "--writer-root",
        str(layout["writer_root"]),
        "--register-path",
        str(layout["register_path"]),
        "--phase-path",
        str(layout["phase_path"]),
    ]


def _run_worker(
    layout: dict,
    *,
    mode: str = "prefix_route",
    cgroup: bool = False,
    extra_env: dict[str, str] | None = None,
) -> dict:
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        config_path=layout["config_path"],
    )
    if extra_env:
        env.update(extra_env)
    command = _worker_command(layout)
    command[command.index("prefix_route")] = mode
    canaries_before = snapshot_production_canaries_for_parent()
    worker_payload: dict = {}
    cgroup_result = None
    error: Exception | None = None
    try:
        if cgroup:
            ready = layout["arm"] / f"cgroup-{uuid.uuid4().hex}.ready"
            command.extend(("--cgroup-enforced", "--cgroup-ready", str(ready)))
            env["CONVMEM_LIVE_DIAG_MEMORY_MAX"] = str(256 * 1024**2)
            try:
                cgroup_result = run_d1_capped_worker(
                    command,
                    ready_path=ready,
                    cwd=ROOT,
                    telemetry_path=layout["telemetry_path"],
                    phase_path=layout["phase_path"],
                    worker_pid_path=Path(env["CONVMEM_LIVE_DIAG_WORKER_PID_PATH"]),
                    expected_bytes=256 * 1024**2,
                    worker_env=env,
                    inner_scope_marker_path=layout["inner_scope_marker"],
                    index_pid_path=layout["index_pid_path"],
                    expected_inner_bytes=parse_systemd_memory("2G"),
                    require_dual_boundary=True,
                    timeout=120,
                )
            finally:
                ready.unlink(missing_ok=True)
            stdout = cgroup_result["stdout"].strip()
            if cgroup_result["returncode"] != 0 and mode != "injected_kill":
                raise AssertionError(cgroup_result["stderr"])
            worker_payload = json.loads(stdout) if stdout else {}
        else:
            import subprocess

            proc = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode != 0 and mode != "injected_kill":
                raise AssertionError(f"worker failed: rc={proc.returncode} stderr={proc.stderr}")
            worker_payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
            worker_payload["_stderr"] = proc.stderr
    except Exception as exc:
        error = exc
        raise
    finally:
        try:
            assert_parent_production_canaries_unchanged(canaries_before)
        except RuntimeError as drift_exc:
            if error is None:
                raise drift_exc
            raise drift_exc from error
    return {"worker": worker_payload, "cgroup": cgroup_result}


@pytest.fixture(scope="session", autouse=True)
def _cleanup_d1_scratch_base() -> None:
    yield
    if SCRATCH_BASE.is_dir():
        shutil.rmtree(SCRATCH_BASE, ignore_errors=True)


@pytest.fixture()
def layout() -> dict:
    scratch = SCRATCH_BASE / uuid.uuid4().hex
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        yield prepare_scratch_arm(scratch, corpus_n=8, prefix_lines=2)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_production_writer_lock_readonly_probe(tmp_path: Path) -> None:
    lock = tmp_path / "writer.lock"
    lock.write_text("held\n", encoding="utf-8")
    st_before = lock.stat()
    fd = os.open(str(lock), os.O_RDONLY | os.O_CLOEXEC)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with patch(
            "tests.watch_oom_live_diagnosis_support.production_writer_lock_path",
            return_value=lock,
        ):
            with pytest.raises(RuntimeError, match="production_writer_lock_held"):
                assert_no_production_writer_collision()
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    st_after = lock.stat()
    assert (st_before.st_size, st_before.st_mtime_ns) == (st_after.st_size, st_after.st_mtime_ns)


def test_production_writer_lock_unheld_does_not_mutate(tmp_path: Path) -> None:
    lock = tmp_path / "writer.lock"
    lock.write_text("free\n", encoding="utf-8")
    st_before = lock.stat()
    with patch(
        "tests.watch_oom_live_diagnosis_support.production_writer_lock_path",
        return_value=lock,
    ):
        assert_no_production_writer_collision()
    st_after = lock.stat()
    assert (st_before.st_size, st_before.st_mtime_ns, st_before.st_mode) == (
        st_after.st_size,
        st_after.st_mtime_ns,
        st_after.st_mode,
    )


def test_backup_manifest_mismatch_fail_closed(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "processed.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="backup_hash_mismatch"):
        verify_backup_manifest(
            manifest={"processed.json": "deadbeef" * 8},
            corpus_root=corpus,
        )


def test_source_write_open_denied(layout: dict) -> None:
    source = layout["source"]
    assert not source.stat().st_mode & stat.S_IWUSR
    with pytest.raises(PermissionError):
        source.open("a", encoding="utf-8")


def test_index_child_source_contract_fail_closed(
    layout: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_WRITER_ROOT", str(layout["writer_root"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_BRIEF_PATH", str(layout["brief_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_REGISTER_PATH", str(layout["register_path"]))
    monkeypatch.setenv(
        "CONVMEM_LIVE_DIAG_INDEX_PID_PATH",
        str(layout["index_pid_path"]),
    )
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_SOURCE_PATH", raising=False)
    with pytest.raises(LiveDiagnosisRefused, match="source_contract_missing"):
        bootstrap_index_child()


def test_inner_scope_unit_missing_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_INNER_SCOPE_UNIT", raising=False)
    import watch

    with patch.object(watch, "_user_systemd_session_available", return_value=True):
        with patch("watch.shutil.which", return_value="/usr/bin/systemd-run"):
            with pytest.raises(LiveDiagnosisRefused, match="inner_scope_unit_missing"):
                watch._scoped_index_cmd(
                    ["convmem", "index", "--file", "/tmp/x"], {}, verbose=False
                )


def test_missing_source_sha_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", raising=False)
    with pytest.raises(LiveDiagnosisRefused, match="source_sha_missing"):
        bootstrap_watch_worker()


def test_scratch_root_ancestor_of_production_fail_closed(
    layout: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    ancestor = str(Path.home())
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([ancestor]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    with pytest.raises(LiveDiagnosisRefused, match="scratch_is_ancestor_of_production"):
        bootstrap_watch_worker()


def test_scratch_root_production_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    prod = str(Path.home() / ".local/share/convmem")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([prod]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    with pytest.raises(LiveDiagnosisRefused, match="scratch_root_is_production"):
        bootstrap_watch_worker()


def test_config_outside_scratch_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(Path.home() / ".config/convmem/config.toml"))
    with pytest.raises(LiveDiagnosisRefused, match="outside_scratch"):
        bootstrap_watch_worker()


def test_network_denied_under_hermetic(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_WRITER_ROOT", str(layout["writer_root"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_BRIEF_PATH", str(layout["brief_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_REGISTER_PATH", str(layout["register_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_PATH", str(layout["source"]))
    monkeypatch.setenv(
        "CONVMEM_LIVE_DIAG_INDEX_PID_PATH",
        str(layout["index_pid_path"]),
    )
    try:
        bootstrap_index_child()
        with pytest.raises(LiveDiagnosisRefused, match="network_denied"):
            socket.create_connection(("127.0.0.1", 9), timeout=0.2)
    finally:
        teardown_hermetic_guards()


def test_canary_drift_fail_closed() -> None:
    key = "/tmp/example"
    before = {
        key: PathCanary(key, "brief", True, 1, 0o644, 1, "a" * 64, 0, 0)
    }
    after = {
        key: PathCanary(key, "brief", True, 2, 0o644, 2, "b" * 64, 0, 0)
    }
    drift = production_canary_drift_lines(before, after)
    assert len(drift) == 1
    assert "brief" in drift[0]


def test_missing_telemetry_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "telemetry.jsonl"
    with pytest.raises(RuntimeError, match="telemetry_missing"):
        require_telemetry_after_kill(missing)


def test_prefix_route_isolation_hermetic(layout: dict) -> None:
    out = _run_worker(layout, mode="prefix_route")
    worker = out["worker"]
    assert worker.get("status") == "succeeded"
    assert worker.get("denied_paths") == []
    assert worker.get("network_denied") == []
    phases = worker.get("phases") or read_phases(layout["phase_path"])
    assert phases.index("watch_skip_hash_begin") < phases.index("watch_skip_hash_admit")
    assert "index_hash_begin" in phases and "index_hash_done" in phases
    assert phases.index("parse_chunks_begin") < phases.index("parse_chunks_done")
    assert "per_chunk_build_begin" in phases and "per_chunk_chroma_write" in phases
    assert "processed_commit" in phases
    assert worker["source_sha256"] == layout["source_sha256"]
    assert "brief_refresh_done" in phases or "export_compaction_done" in phases


def test_injected_kill_preserves_phase_log(layout: dict) -> None:
    out = _run_worker(layout, mode="injected_kill")
    worker = out["worker"]
    assert worker.get("status") in {"blocked", "failed", "succeeded"}
    phases = read_phases(layout["phase_path"])
    assert "watch_route_start" in phases


@pytest.mark.skipif(not RUN_CGROUP, reason="set CONVMEM_D1_CGROUP=1 for cgroup integration")
def test_cgroup_dual_boundary_prefix_route(layout: dict) -> None:
    out = _run_worker(layout, mode="prefix_route", cgroup=True)
    cgroup = out["cgroup"]
    assert cgroup is not None
    assert cgroup.get("dual_boundary_verified") is True
    assert cgroup.get("inner_limit_claim")
    lines = layout["telemetry_path"].read_text(encoding="utf-8").splitlines()
    boundaries = {json.loads(line).get("boundary") for line in lines if line.strip()}
    assert "outer" in boundaries
    assert "inner" in boundaries


@pytest.mark.skipif(not RUN_CGROUP, reason="set CONVMEM_D1_CGROUP=1 for cgroup integration")
def test_cgroup_parent_sampler_survives_injected_kill(layout: dict) -> None:
    layout["telemetry_path"].unlink(missing_ok=True)
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        config_path=layout["config_path"],
    )
    command = _worker_command(layout)
    command[command.index("prefix_route")] = "injected_kill"
    ready = layout["arm"] / f"cgroup-kill-{uuid.uuid4().hex}.ready"
    command.extend(("--cgroup-enforced", "--cgroup-ready", str(ready)))
    canaries_before = snapshot_production_canaries_for_parent()
    try:
        result = run_d1_capped_worker(
            command,
            ready_path=ready,
            cwd=ROOT,
            telemetry_path=layout["telemetry_path"],
            phase_path=layout["phase_path"],
            worker_pid_path=Path(env["CONVMEM_LIVE_DIAG_WORKER_PID_PATH"]),
            expected_bytes=256 * 1024**2,
            worker_env=env,
            inner_scope_marker_path=layout["inner_scope_marker"],
            index_pid_path=layout["index_pid_path"],
            expected_inner_bytes=parse_systemd_memory("2G"),
            require_dual_boundary=False,
            timeout=120,
        )
    finally:
        ready.unlink(missing_ok=True)
        assert_parent_production_canaries_unchanged(canaries_before)
    assert result["parent_telemetry_samples"] >= 1
    assert result["parent_final_counters"]
    summary = require_telemetry_after_kill(layout["telemetry_path"], min_samples=2)
    assert summary["last"]["reason"] == "cgroup_final_counters"


def test_phase_order_subset(layout: dict) -> None:
    _run_worker(layout, mode="prefix_route")
    phases = read_phases(layout["phase_path"])
    ordered = [p for p in PHASE_ORDER if p in phases]
    assert len(ordered) >= 4
    assert phases.index(ordered[0]) < phases.index(ordered[-1])


def test_scratch_canary_detects_drift() -> None:
    before = {
        "processed.json": ScratchCanary("processed.json", "a" * 64, 1, 1),
    }
    after = {
        "processed.json": ScratchCanary("processed.json", "b" * 64, 2, 2),
    }
    with pytest.raises(RuntimeError, match="scratch canary drift"):
        assert_scratch_canaries_unchanged(before, after)


def test_arm_diagnosis_env_rejects_missing_config(layout: dict) -> None:
    with pytest.raises(ValueError, match="scratch config missing"):
        arm_diagnosis_env(
            scratch_root=layout["scratch_root"],
            phase_path=layout["phase_path"],
            telemetry_path=layout["telemetry_path"],
            source_sha256=layout["source_sha256"],
            config_path=layout["scratch_root"] / "missing.toml",
        )


def test_d2_kernel_isolation_documented() -> None:
    assert "IPAddressDeny" in D2_KERNEL_ISOLATION_BLOCKER


def test_source_prefix_fixture_hash_stable(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    h1 = build_prefix_transcript(path, lines=3)
    h2 = hashlib.sha256(path.read_bytes()).hexdigest()
    assert h1 == h2
