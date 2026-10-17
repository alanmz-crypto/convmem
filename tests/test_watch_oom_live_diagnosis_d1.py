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
    GATE_INDEX_AT_GATE,
    LiveDiagnosisRefused,
    bootstrap_index_child,
    bootstrap_watch_worker,
    teardown_hermetic_guards,
)
from tests.watch_oom_exposure_index_e2e_support import PathCanary
from tests.watch_oom_live_diagnosis_bwrap import d1_bwrap_integration_available
from tests.watch_oom_live_diagnosis_parent import (
    D2_KERNEL_ISOLATION_BLOCKER,
    _raise_d1_worker_run_failure,
    assert_inject_kill_index_at_gate_allowed,
    build_d1_worker_exit_diagnostic,
    d1_systemd_network_properties,
    require_telemetry_after_kill,
    run_d1_capped_worker,
    sanitize_d1_worker_stream,
)
from tests.watch_oom_live_diagnosis_support import (
    BACKUP_MANIFEST_SHA256_ENV,
    PHASE_ORDER,
    ScratchCanary,
    arm_diagnosis_env,
    assert_no_production_writer_collision,
    assert_scratch_canaries_unchanged,
    bind_backup_manifest_digest,
    build_prefix_transcript,
    d1_parent_teardown_postcheck,
    load_external_backup_manifest,
    overlay_live_diagnosis_env,
    prepare_scratch_arm,
    production_canary_drift_lines,
    read_d1_harness_limits,
    read_phases,
    snapshot_production_canaries_for_parent,
    backup_manifest_entries_fingerprint,
    backup_manifest_file_sha256,
    parent_verify_backup_manifest_supply,
    supply_external_backup_manifest_file,
    verify_backup_manifest,
    worker_bind_backup_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve().parent / "watch_oom_live_diagnosis_worker.py"
RUN_CGROUP = os.environ.get("CONVMEM_D1_CGROUP") == "1"
requires_bwrap_userns = pytest.mark.skipif(
    not d1_bwrap_integration_available(),
    reason="bwrap user-ns integration unavailable on this host",
)
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
        "--source-size",
        str(layout["source_size"]),
        "--source-mtime-ns",
        str(layout["source_mtime_ns"]),
        "--backup-manifest-path",
        str(layout["backup_manifest_path"]),
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


def _d1_cgroup_memory_limits(layout: dict) -> tuple[int, int]:
    outer, inner = read_d1_harness_limits(layout["config_path"])
    assert outer == layout["d1_outer_memory_bytes"]
    assert inner == layout["d1_inner_memory_bytes"]
    return outer, inner


def _run_cgroup_dual_boundary(
    layout: dict,
    *,
    command: list[str],
    env: dict[str, str],
    ready_path: Path,
    inject_kill_index_at_gate: bool = False,
) -> dict:
    outer_bytes, inner_bytes = _d1_cgroup_memory_limits(layout)
    env = dict(env)
    env["CONVMEM_LIVE_DIAG_MEMORY_MAX"] = str(outer_bytes)
    env["CONVMEM_LIVE_DIAG_INNER_MEMORY_BYTES"] = str(inner_bytes)
    return run_d1_capped_worker(
        command,
        ready_path=ready_path,
        cwd=ROOT,
        telemetry_path=layout["telemetry_path"],
        phase_path=layout["phase_path"],
        worker_pid_path=Path(env["CONVMEM_LIVE_DIAG_WORKER_PID_PATH"]),
        expected_bytes=outer_bytes,
        worker_env=env,
        inner_scope_marker_path=layout["inner_scope_marker"],
        index_pid_path=layout["index_pid_path"],
        index_gate_path=Path(env["CONVMEM_LIVE_DIAG_INDEX_GATE_PATH"]),
        denial_path=Path(env["CONVMEM_LIVE_DIAG_DENIAL_PATH"]),
        expected_inner_bytes=inner_bytes,
        require_dual_boundary=True,
        use_bwrap=True,
        scratch_root=layout["scratch_root"],
        source_path=layout["source"],
        timeout=120,
        inject_kill_index_at_gate=inject_kill_index_at_gate,
    )


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
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
        gate_auto_go=not cgroup,
    )
    bind_backup_manifest_digest(env, layout["backup_manifest_file_sha256"])
    env["CONVMEM_LIVE_DIAG_SOURCE_PATH"] = str(layout["source"])
    if extra_env:
        env.update(extra_env)
    command = _worker_command(layout)
    command[command.index("prefix_route")] = mode
    denial_path = Path(env["CONVMEM_LIVE_DIAG_DENIAL_PATH"])
    parent_verify_backup_manifest_supply(
        manifest_path=layout["backup_manifest_path"],
        scratch_roots_json=env["CONVMEM_LIVE_DIAG_SCRATCH_ROOTS"],
        expected_file_sha256=layout["backup_manifest_file_sha256"],
        corpus_root=layout["arm"] / "seed",
        expected_fingerprint=layout["backup_manifest_fingerprint"],
    )
    canaries_before = snapshot_production_canaries_for_parent(
        layout["incident_source_path"]
    )
    worker_payload: dict = {}
    cgroup_result = None
    error: Exception | None = None
    try:
        if cgroup:
            ready = layout["arm"] / f"cgroup-{uuid.uuid4().hex}.ready"
            command.extend(("--cgroup-enforced", "--cgroup-ready", str(ready)))
            try:
                cgroup_result = _run_cgroup_dual_boundary(
                    layout,
                    command=command,
                    env=env,
                    ready_path=ready,
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
            d1_parent_teardown_postcheck(
                env=env,
                source_path=layout["source"],
                denial_path=denial_path,
                incident_source=layout["incident_source_path"],
                canaries_before=canaries_before,
                manifest_path=layout["backup_manifest_path"],
                manifest_sha256=layout["backup_manifest_file_sha256"],
            )
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
    external_supply: Path | None = None
    try:
        layout = prepare_scratch_arm(scratch, corpus_n=8, prefix_lines=2)
        seed = layout["arm"] / "seed"
        external_supply = SCRATCH_BASE.parent / "d1-parent-supply" / uuid.uuid4().hex
        external_supply.mkdir(parents=True, exist_ok=True)
        manifest_entries = {
            "processed.json": hashlib.sha256(
                (seed / "processed.json").read_bytes()
            ).hexdigest(),
            "chroma/chroma.sqlite3": hashlib.sha256(
                (layout["chroma_dir"] / "chroma.sqlite3").read_bytes()
            ).hexdigest(),
        }
        manifest_path = external_supply / "backup_manifest.json"
        supply_external_backup_manifest_file(manifest_path, entries=manifest_entries)
        layout["backup_manifest_path"] = manifest_path
        layout["backup_manifest_file_sha256"] = backup_manifest_file_sha256(manifest_path)
        layout["backup_manifest_fingerprint"] = backup_manifest_entries_fingerprint(
            manifest_entries
        )
        original_source = external_supply / "original-source.jsonl"
        original_source.write_bytes(layout["source"].read_bytes())
        layout["incident_source_path"] = original_source
        yield layout
    finally:
        if external_supply is not None:
            shutil.rmtree(external_supply, ignore_errors=True)
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
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(layout["denial_path"]))
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_SOURCE_PATH", raising=False)
    with pytest.raises(LiveDiagnosisRefused, match="source_contract_missing"):
        bootstrap_index_child()


def test_inner_scope_unit_missing_fail_closed(
    layout: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv(
        "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])])
    )
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_INNER_SCOPE_UNIT", raising=False)
    import watch

    with patch.object(watch, "_user_systemd_session_available", return_value=True):
        with patch("watch.shutil.which", return_value="/usr/bin/systemd-run"):
            with pytest.raises(LiveDiagnosisRefused, match="inner_scope_unit_missing"):
                watch._scoped_index_cmd(  # pylint: disable=protected-access
                    ["convmem", "index", "--file", "/tmp/x"], {}, verbose=False
                )


def test_missing_source_sha_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(layout["denial_path"]))
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", raising=False)
    with pytest.raises(LiveDiagnosisRefused, match="source_sha_missing"):
        bootstrap_watch_worker()


def test_scratch_root_ancestor_of_production_fail_closed(
    layout: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    ancestor = str(Path.home())
    monkeypatch.setenv(
        "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"]), ancestor])
    )
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(layout["denial_path"]))
    with pytest.raises(LiveDiagnosisRefused, match="scratch_is_ancestor_of_production"):
        bootstrap_watch_worker()


def test_scratch_root_production_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    prod = str(Path.home() / ".local/share/convmem")
    monkeypatch.setenv(
        "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"]), prod])
    )
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(layout["denial_path"]))
    with pytest.raises(LiveDiagnosisRefused, match="scratch_root_is_production"):
        bootstrap_watch_worker()


def test_config_outside_scratch_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    outside_config = layout["backup_manifest_path"].parent / "config-outside-scratch.toml"
    shutil.copyfile(layout["config_path"], outside_config)
    assert not outside_config.resolve().is_relative_to(layout["scratch_root"].resolve())
    monkeypatch.setenv("CONVMEM_CONFIG", str(outside_config))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(layout["denial_path"]))
    with pytest.raises(LiveDiagnosisRefused, match="config_path_outside_scratch"):
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
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", str(layout["denial_path"]))
    monkeypatch.setenv(
        "CONVMEM_LIVE_DIAG_INDEX_PID_PATH",
        str(layout["index_pid_path"]),
    )
    import brief
    import ingest

    # bootstrap_index_child() is a child-process entry hook: its patches never stop.
    monkeypatch.setattr(brief, "DEFAULT_BRIEF_PATH", brief.DEFAULT_BRIEF_PATH)
    monkeypatch.setattr(ingest, "_LIVE_DIAG_PATCHED", False, raising=False)
    try:
        bootstrap_index_child()
        with pytest.raises(LiveDiagnosisRefused, match="network_denied"):
            socket.create_connection(("127.0.0.1", 9), timeout=0.2)
    finally:
        teardown_hermetic_guards()
        patch.stopall()


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
    assert "modified" in drift[0]
    assert "brief" in drift[0]


def test_canary_created_fail_closed() -> None:
    key = "/tmp/new-canary"
    before = {
        key: PathCanary(key, "export", False, None, None, None, None, None, None)
    }
    after = {
        key: PathCanary(key, "export", True, 1, 0o644, 1, "c" * 64, 0, 0)
    }
    drift = production_canary_drift_lines(before, after)
    assert len(drift) == 1
    assert drift[0].startswith("created ")


def test_worker_never_receives_incident_source(layout: dict) -> None:
    original = layout["incident_source_path"]
    assert not original.resolve().is_relative_to(layout["scratch_root"].resolve())
    assert str(original) not in _worker_command(layout)
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
    )
    bind_backup_manifest_digest(env, layout["backup_manifest_file_sha256"])
    assert not any(str(original) in value for value in env.values())


def _incident_only(snapshot: dict, key: str) -> dict:
    return {k: v for k, v in snapshot.items() if k == key}


def test_parent_detects_external_incident_source_drift(layout: dict) -> None:
    original = layout["incident_source_path"]
    key = str(original)
    before = _incident_only(snapshot_production_canaries_for_parent(original), key)
    assert before[key].exists is True

    original.write_bytes(original.read_bytes() + b'{"role":"user"}\n')
    modified = _incident_only(snapshot_production_canaries_for_parent(original), key)
    assert production_canary_drift_lines(before, modified) == [f"modified incident_source {key}"]

    original.unlink()
    deleted = _incident_only(snapshot_production_canaries_for_parent(original), key)
    assert production_canary_drift_lines(modified, deleted) == [f"deleted incident_source {key}"]

    original.write_bytes(b"{}\n")
    created = _incident_only(snapshot_production_canaries_for_parent(original), key)
    assert production_canary_drift_lines(deleted, created) == [f"created incident_source {key}"]


def test_denial_path_missing_fail_closed(layout: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SCRATCH_ROOTS", json.dumps([str(layout["scratch_root"])]))
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.setenv("CONVMEM_LIVE_DIAG_SOURCE_SHA256", layout["source_sha256"])
    monkeypatch.setenv("CONVMEM_CONFIG", str(layout["config_path"]))
    monkeypatch.delenv("CONVMEM_LIVE_DIAG_DENIAL_PATH", raising=False)
    with pytest.raises(LiveDiagnosisRefused, match="denial_path_missing"):
        bootstrap_watch_worker()


def test_backup_manifest_in_scratch_rejected(layout: dict) -> None:
    inside = layout["arm"] / "internal_manifest.json"
    inside.write_text('{"processed.json": "' + "a" * 64 + '"}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="backup_manifest_must_be_external_to_scratch"):
        parent_verify_backup_manifest_supply(
            manifest_path=inside,
            scratch_roots_json=json.dumps([str(layout["scratch_root"])]),
            expected_file_sha256=backup_manifest_file_sha256(inside),
            corpus_root=layout["arm"] / "seed",
            expected_fingerprint=layout["backup_manifest_fingerprint"],
        )


def _manifest_parent_args(layout: dict) -> dict:
    return {
        "manifest_path": layout["backup_manifest_path"],
        "scratch_roots_json": json.dumps([str(layout["scratch_root"])]),
        "expected_file_sha256": layout["backup_manifest_file_sha256"],
        "corpus_root": layout["arm"] / "seed",
        "expected_fingerprint": layout["backup_manifest_fingerprint"],
    }


def test_backup_manifest_parent_supply_accepts_bound_manifest(layout: dict) -> None:
    parent_verify_backup_manifest_supply(**_manifest_parent_args(layout))


def test_backup_fingerprint_mismatch_fail_closed(layout: dict) -> None:
    args = _manifest_parent_args(layout)
    args["expected_fingerprint"] = backup_manifest_entries_fingerprint(
        {"processed.json": "0" * 64}
    )
    with pytest.raises(RuntimeError, match="backup_fingerprint_mismatch"):
        parent_verify_backup_manifest_supply(**args)


def test_backup_manifest_identity_drift_fail_closed(layout: dict) -> None:
    manifest_path = layout["backup_manifest_path"]
    expected = layout["backup_manifest_file_sha256"]
    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["processed.json"] = "f" * 64
    manifest_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")
    with pytest.raises(RuntimeError, match="backup_manifest_identity_drift"):
        parent_verify_backup_manifest_supply(**_manifest_parent_args(layout))
    env = {
        "CONVMEM_LIVE_DIAG_SCRATCH_ROOTS": json.dumps([str(layout["scratch_root"])]),
        BACKUP_MANIFEST_SHA256_ENV: expected,
    }
    with pytest.raises(RuntimeError, match="backup_manifest_identity_drift"):
        worker_bind_backup_manifest(manifest_path, env)
    with pytest.raises(RuntimeError, match="backup_manifest_identity_drift"):
        d1_parent_teardown_postcheck(
            env=env,
            source_path=layout["source"],
            denial_path=layout["denial_path"],
            incident_source=layout["incident_source_path"],
            canaries_before={},
            manifest_path=manifest_path,
            manifest_sha256=expected,
        )


def test_backup_manifest_expected_sha_missing_fail_closed(layout: dict) -> None:
    roots = json.dumps([str(layout["scratch_root"])])
    with pytest.raises(RuntimeError, match="backup_manifest_expected_sha_missing"):
        worker_bind_backup_manifest(
            layout["backup_manifest_path"], {"CONVMEM_LIVE_DIAG_SCRATCH_ROOTS": roots}
        )
    with pytest.raises(RuntimeError, match="backup_manifest_expected_sha_missing"):
        d1_parent_teardown_postcheck(
            env={"CONVMEM_LIVE_DIAG_SCRATCH_ROOTS": roots},
            source_path=layout["source"],
            denial_path=layout["denial_path"],
            incident_source=layout["incident_source_path"],
            canaries_before={},
            manifest_path=layout["backup_manifest_path"],
            manifest_sha256="",
        )


def test_missing_telemetry_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "telemetry.jsonl"
    with pytest.raises(RuntimeError, match="telemetry_missing"):
        require_telemetry_after_kill(missing)


@requires_bwrap_userns
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


@requires_bwrap_userns
def test_injected_kill_blocked_with_phase_evidence(layout: dict) -> None:
    out = _run_worker(layout, mode="injected_kill")
    worker = out["worker"]
    assert worker.get("status") == "blocked"
    assert worker.get("mode") == "injected_kill"
    assert worker.get("kill_marker") == "worker_popen_sigkill"
    phases = read_phases(layout["phase_path"])
    assert "watch_route_start" in phases
    assert "injected_kill_before_index_spawn" in phases
    assert "injected_kill_index_sigkill" in phases
    assert "watch_route_error" in phases
    assert "index_hash_done" not in phases


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
def test_cgroup_dual_boundary_injected_kill_stages(layout: dict) -> None:
    layout["telemetry_path"].unlink(missing_ok=True)
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
        gate_auto_go=False,
    )
    bind_backup_manifest_digest(env, layout["backup_manifest_file_sha256"])
    env["CONVMEM_LIVE_DIAG_SOURCE_PATH"] = str(layout["source"])
    gate_path = Path(env["CONVMEM_LIVE_DIAG_INDEX_GATE_PATH"])
    command = _worker_command(layout)
    command[command.index("prefix_route")] = "injected_kill"
    ready = layout["arm"] / f"cgroup-kill-{uuid.uuid4().hex}.ready"
    command.extend(("--cgroup-enforced", "--cgroup-ready", str(ready)))
    canaries_before = snapshot_production_canaries_for_parent(
        layout["incident_source_path"]
    )
    try:
        result = _run_cgroup_dual_boundary(
            layout,
            command=command,
            env=env,
            ready_path=ready,
            inject_kill_index_at_gate=True,
        )
    finally:
        ready.unlink(missing_ok=True)
        d1_parent_teardown_postcheck(
            env=env,
            source_path=layout["source"],
            denial_path=Path(env["CONVMEM_LIVE_DIAG_DENIAL_PATH"]),
            incident_source=layout["incident_source_path"],
            canaries_before=canaries_before,
            manifest_path=layout["backup_manifest_path"],
            manifest_sha256=layout["backup_manifest_file_sha256"],
        )
    assert result["index_killed_at_gate"] is True
    assert result["dual_boundary_verified"] is True
    assert result["parent_telemetry_samples"] >= 1
    assert gate_path.read_text(encoding="ascii").strip() == GATE_INDEX_AT_GATE
    worker_payload = json.loads(result["stdout"]) if result["stdout"].strip() else {}
    assert worker_payload.get("status") == "blocked"
    phases = read_phases(layout["phase_path"])
    assert "index_hash_begin" not in phases
    inner_final = json.loads(
        Path(env["CONVMEM_LIVE_DIAG_INNER_FINAL_PATH"]).read_text(encoding="utf-8")
    )
    assert inner_final.get("memory_peak") is not None
    assert inner_final.get("memory_events")
    assert Path(env["CONVMEM_LIVE_DIAG_INNER_ACK_PATH"]).is_file()
    summary = require_telemetry_after_kill(layout["telemetry_path"], min_samples=2)
    assert summary["last"]["reason"] == "cgroup_final_counters"


def test_cgroup_route_refuses_synthetic_fast(layout: dict) -> None:
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
        gate_auto_go=True,
    )
    ready = layout["arm"] / "refuse-synthetic.ready"
    ready.parent.mkdir(parents=True, exist_ok=True)
    outer_bytes, inner_bytes = _d1_cgroup_memory_limits(layout)
    with pytest.raises(RuntimeError, match="cgroup_route_refuses_synthetic_fast"):
        run_d1_capped_worker(
            [sys.executable, "-c", "pass"],
            ready_path=ready,
            cwd=ROOT,
            telemetry_path=layout["telemetry_path"],
            phase_path=layout["phase_path"],
            worker_pid_path=None,
            expected_bytes=outer_bytes,
            worker_env=env,
            inner_scope_marker_path=layout["inner_scope_marker"],
            index_pid_path=layout["index_pid_path"],
            expected_inner_bytes=inner_bytes,
            require_dual_boundary=True,
            use_bwrap=True,
            scratch_root=layout["scratch_root"],
            source_path=layout["source"],
            timeout=5,
        )


def test_dual_boundary_requires_bwrap(layout: dict) -> None:
    outer_bytes, inner_bytes = _d1_cgroup_memory_limits(layout)
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
        gate_auto_go=False,
    )
    ready = layout["arm"] / "refuse-no-bwrap.ready"
    ready.parent.mkdir(parents=True, exist_ok=True)
    with pytest.raises(RuntimeError, match="dual_boundary_requires_bwrap"):
        run_d1_capped_worker(
            [sys.executable, "-c", "pass"],
            ready_path=ready,
            cwd=ROOT,
            telemetry_path=layout["telemetry_path"],
            phase_path=layout["phase_path"],
            worker_pid_path=None,
            expected_bytes=outer_bytes,
            worker_env=env,
            inner_scope_marker_path=layout["inner_scope_marker"],
            index_pid_path=layout["index_pid_path"],
            expected_inner_bytes=inner_bytes,
            require_dual_boundary=True,
            use_bwrap=False,
            timeout=5,
        )


def test_overlay_live_diagnosis_env_restores_os_environ(layout: dict) -> None:
    sentinel = "CONVMEM_LIVE_DIAG_ENV_LEAK_PROBE"
    prior = os.environ.get(sentinel)
    os.environ.pop(sentinel, None)
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
    )
    env[sentinel] = "set-during-overlay"
    with overlay_live_diagnosis_env(env):
        assert os.environ.get(sentinel) == "set-during-overlay"
    assert os.environ.get(sentinel) is None
    if prior is not None:
        os.environ[sentinel] = prior


def test_d1_harness_limits_match_fixture_config(layout: dict) -> None:
    outer, inner = read_d1_harness_limits(layout["config_path"])
    assert (outer, inner) == (
        layout["d1_outer_memory_bytes"],
        layout["d1_inner_memory_bytes"],
    )


def test_sanitize_d1_worker_stream_redacts_secrets(layout: dict) -> None:
    scratch = layout["scratch_root"]
    raw = (
        "CONVMEM_LIVE_DIAG_SOURCE_SHA256=abc\n"
        "DEEPSEEK_API_KEY=supersecret\n"
        f"open failed: {layout['source']}\n"
        '{"api_key": "nested-secret"}\n'
    )
    cleaned = sanitize_d1_worker_stream(raw, allowed_scratch_roots=[scratch])
    assert "supersecret" not in cleaned
    assert "nested-secret" not in cleaned
    assert "<redacted>" in cleaned
    assert str(scratch) not in cleaned
    assert "arm/" in cleaned or "seed/" in cleaned or cleaned.count("<path") >= 0


def test_early_exit_diagnostic_includes_returncode_and_stderr_tail(layout: dict) -> None:
    scratch = layout["scratch_root"]
    stderr = (
        "bwrap: exec failed\n"
        "CONVMEM_CONFIG=/tmp/leak.toml\n"
        f"source={layout['source']}\n"
    )
    message = build_d1_worker_exit_diagnostic(
        reason="parent_sampler_no_samples",
        unit="convmem-oom-measure-deadbeef.service",
        returncode=1,
        stdout="",
        stderr=stderr,
        control_group="",
        oom_policy_verified=False,
        allowed_scratch_roots=[scratch],
    )
    assert "parent_sampler_no_samples" in message
    assert "unit=convmem-oom-measure-deadbeef.service" in message
    assert "returncode=1" in message
    assert "parent_cgroup_unattached=true" in message
    assert "stderr_tail=" in message
    assert "bwrap: exec failed" in message
    assert "leak.toml" not in message
    assert layout["source_sha256"] not in message

    class _FakeStream:
        pass

    class _FakeProc:
        returncode = 1
        stdout = _FakeStream()
        stderr = _FakeStream()

    proc = _FakeProc()
    output = {
        proc.stdout: bytearray(),
        proc.stderr: bytearray(stderr.encode("utf-8")),
    }
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
    )
    with pytest.raises(RuntimeError, match="returncode=1") as exc:
        _raise_d1_worker_run_failure(
            "parent_sampler_no_samples",
            unit="convmem-oom-measure-test.service",
            proc=proc,
            output=output,
            oom_policy_verified=False,
            worker_env=env,
        )
    assert "stderr_tail=" in str(exc.value)
    assert env["CONVMEM_LIVE_DIAG_SOURCE_SHA256"] not in str(exc.value)


@requires_bwrap_userns
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
            source_size=layout["source_size"],
            source_mtime_ns=layout["source_mtime_ns"],
            config_path=layout["scratch_root"] / "missing.toml",
        )


def test_backup_manifest_unavailable_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="backup_manifest_unavailable"):
        load_external_backup_manifest(tmp_path / "missing.json")


def test_d2_kernel_isolation_documented() -> None:
    assert "IPAddressDeny" in D2_KERNEL_ISOLATION_BLOCKER
    assert "supplemental" in D2_KERNEL_ISOLATION_BLOCKER


def test_inject_kill_index_at_gate_refused_without_bwrap(layout: dict) -> None:
    env = arm_diagnosis_env(
        scratch_root=layout["scratch_root"],
        phase_path=layout["phase_path"],
        telemetry_path=layout["telemetry_path"],
        source_sha256=layout["source_sha256"],
        source_size=layout["source_size"],
        source_mtime_ns=layout["source_mtime_ns"],
        config_path=layout["config_path"],
        gate_auto_go=False,
    )
    with pytest.raises(RuntimeError, match="inject_kill_index_at_gate_unavailable"):
        assert_inject_kill_index_at_gate_allowed(
            inject_kill_index_at_gate=True,
            require_dual_boundary=True,
            use_bwrap=False,
            worker_env=env,
        )


def test_cgroup_injected_kill_skips_worker_systemd_popen_patch() -> None:
    """Cgroup route must not SIGKILL systemd-run from worker injected_kill mode."""
    worker_src = (
        Path(__file__).resolve().parent / "watch_oom_live_diagnosis_worker.py"
    ).read_text(encoding="utf-8")
    assert 'if args.mode == "injected_kill" and not args.cgroup_enforced:' in worker_src


def test_bwrap_dual_boundary_systemd_argv_omits_af_unix_restriction() -> None:
    props = d1_systemd_network_properties(
        kernel_network_deny=True,
        use_bwrap=True,
        require_dual_boundary=True,
    )
    assert props == ["--property=IPAddressDeny=any"]
    non_bwrap = d1_systemd_network_properties(
        kernel_network_deny=True,
        use_bwrap=False,
        require_dual_boundary=True,
    )
    assert any("RestrictAddressFamilies=AF_UNIX" in p for p in non_bwrap)


def test_source_prefix_fixture_hash_stable(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    h1 = build_prefix_transcript(path, lines=3)
    h2 = hashlib.sha256(path.read_bytes()).hexdigest()
    assert h1 == h2
