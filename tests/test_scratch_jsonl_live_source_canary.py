"""Contract tests for the frozen live-source canary boundary."""

# pylint: disable=protected-access,subprocess-run-check,duplicate-code

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from scratch_jsonl_prototype import live_source_canary as canary
from scratch_jsonl_prototype.isolation import (
    IsolationViolation,
    ScratchBoundary,
    create_fresh_root,
    sanitized_worker_env,
)


def _source_bytes(count: int = 4) -> bytes:
    rows = []
    for index in range(count):
        rows.append(
            json.dumps(
                {
                    "timestamp": f"2026-09-09T00:00:{index:02d}Z",
                    "payload": {
                        "type": "user" if index % 2 == 0 else "assistant",
                        "content": f"canary-message-{index}",
                    },
                },
                sort_keys=True,
            ).encode()
            + b"\n"
        )
    return b"".join(rows)


def _spec(path: Path, alias: str = "fixture") -> canary.FrozenSourceSpec:
    data = path.read_bytes()
    return canary.FrozenSourceSpec(alias, path, hashlib.sha256(data).hexdigest(), len(data))


def _case(tmp_path: Path) -> tuple[ScratchBoundary, Path, Path, canary.FrozenSourceSpec, canary.FrozenSourceSpec]:
    root, token = create_fresh_root(tmp_path)
    source_dir = tmp_path / "frozen" / "sess_fixture"
    source_dir.mkdir(parents=True)
    source = source_dir / "messages.jsonl"
    meta = source_dir / "session.json"
    source.write_bytes(_source_bytes())
    meta.write_text(json.dumps({"id": "sess_fixture"}), encoding="utf-8")
    return ScratchBoundary(root, token), source, meta, _spec(source), _spec(meta, "fixture-meta")


def test_frozen_source_validates_exact_identity_digest_and_boundary(tmp_path: Path) -> None:
    _boundary, source, _meta, spec, _meta_spec = _case(tmp_path)
    descriptor, data = canary.validate_frozen_source(spec)
    assert descriptor.canonical_path == str(source)
    assert descriptor.size == len(data) == spec.size
    assert descriptor.complete_boundary == len(data)
    assert descriptor.physical_lines == data.count(b"\n")
    assert descriptor.sha256 == spec.sha256
    evidence = json.dumps(descriptor.__dict__, sort_keys=True)
    assert "canary-message" not in evidence

    source.write_bytes(data + b"append\n")
    with pytest.raises(IsolationViolation, match="size drift"):
        canary.validate_frozen_source(spec)


def test_frozen_source_rejects_digest_drift_and_symlink(tmp_path: Path) -> None:
    _boundary, source, _meta, spec, _meta_spec = _case(tmp_path)
    original = source.read_bytes()
    source.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    with pytest.raises(IsolationViolation, match="digest drift"):
        canary.validate_frozen_source(spec)

    source.write_bytes(original)
    link = source.parent / "link.jsonl"
    link.symlink_to(source)
    with pytest.raises(IsolationViolation, match="symlinked"):
        canary.validate_frozen_source(
            canary.FrozenSourceSpec("link", link, spec.sha256, spec.size)
        )


def test_capture_is_atomic_read_only_and_content_free(tmp_path: Path, monkeypatch) -> None:
    boundary, source, meta, spec, meta_spec = _case(tmp_path)
    calls: list[tuple[str, int]] = []
    original_open = canary.os.open

    def record_open(path, flags, *args):
        if str(path) in {str(source), str(meta)}:
            calls.append((str(path), flags))
        return original_open(path, flags, *args)

    monkeypatch.setattr(canary.os, "open", record_open)
    message_desc, meta_desc, complete, _meta_bytes = canary.capture_sources(
        boundary, spec, meta_spec
    )
    assert complete == source.read_bytes()
    copied = boundary.root / "sources/sess_canary"
    assert (copied / "messages.jsonl").read_bytes() == complete
    assert (copied / "session.json").read_bytes() == meta.read_bytes()
    assert calls
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
    assert all(not (flags & write_flags) for _path, flags in calls)
    evidence = json.dumps({"messages": message_desc.__dict__, "meta": meta_desc.__dict__})
    assert "canary-message" not in evidence
    assert "session_fixture" not in evidence


def test_capture_fault_inventory_and_wrapper_subsumption_are_explicit(tmp_path: Path) -> None:
    boundary, _source, _meta, spec, meta_spec = _case(tmp_path)
    events: list[str] = []
    canary.capture_sources(boundary, spec, meta_spec, fault=events.append)
    assert events == [
        "before_snapshot_prepare",
        "after_snapshot_prepare",
        "before_snapshot_publish",
        "after_snapshot_publish",
        "before_source_revalidation",
        "after_source_revalidation",
    ]
    assert canary.CHROMA_WRAPPER_SUBSUMPTION == {
        "chroma_repair": ("summary_upsert", "unit_upsert"),
        "chroma_upsert": ("summary_upsert", "unit_upsert"),
        "chroma_prune": ("summaries_prune", "units_prune"),
    }
    assert Path("/home/lauer/Projects/convmem") in canary.PRODUCTION_ROOTS


def test_transition_coverage_fails_closed_when_declared_point_is_missing() -> None:
    canary._assert_transition_coverage(
        ("prepare", "publish"),
        ("before_prepare", "after_prepare", "before_publish", "after_publish"),
        label="fixture",
    )
    with pytest.raises(IsolationViolation, match="missing: publish"):
        canary._assert_transition_coverage(
            ("prepare", "publish"),
            ("before_prepare", "after_prepare", "before_publish"),
            label="fixture",
        )


def test_gate0_aborts_active_or_indeterminate_watcher(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = "active\n"

    def active_run(*args, **_kwargs):
        calls.append(args[0])
        return Result()

    monkeypatch.setattr(canary.subprocess, "run", active_run)
    with pytest.raises(IsolationViolation, match="active or indeterminate"):
        canary.gate0()
    assert calls == [["systemctl", "--user", "is-active", "convmem-watch.service"]]

    class UnknownResult:
        returncode = 1
        stdout = "unknown\n"

    monkeypatch.setattr(canary.subprocess, "run", lambda *args, **kwargs: UnknownResult())
    with pytest.raises(IsolationViolation, match="active or indeterminate"):
        canary.gate0()


def test_gate0_uses_host_user_manager_when_local_bus_is_unavailable(monkeypatch) -> None:
    calls: list[list[str]] = []

    class Result:
        def __init__(self, returncode: int, stdout: str):
            self.returncode = returncode
            self.stdout = stdout

    def run(command, **_kwargs):
        calls.append(command)
        if len(calls) == 1:
            return Result(1, "")
        return Result(3, "inactive\n")

    monkeypatch.setattr(canary.subprocess, "run", run)
    monkeypatch.setattr(canary, "_watcher_processes", lambda: [])
    evidence = canary.gate0()
    assert evidence == {
        "service": "inactive",
        "service_probe": "host-user-manager",
        "watcher_processes": 0,
    }
    assert calls[0] == [
        "systemctl", "--user", "is-active", "convmem-watch.service"
    ]
    assert calls[1][:2] == ["systemctl", "--user"]
    assert calls[1][2].startswith("--machine=")
    assert calls[1][2].endswith("@.host")
    assert calls[1][3:] == ["is-active", "convmem-watch.service"]


def test_watcher_cmdline_detection_catches_module_and_script_forms() -> None:
    assert canary._watcher_command_matches("python", "python\0-m\0convmem.watch\0")
    assert canary._watcher_command_matches("python", "/opt/convmem-watch.py\0")
    assert not canary._watcher_command_matches("python", "python\0worker.py\0")


def test_worker_uses_explicit_scratch_env_and_fingerprint_fallback(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    source = root / "sources" / "sess_worker" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(_source_bytes(2))
    env = sanitized_worker_env(root, token)
    assert not any("KEY" in name or "SECRET" in name for name in env)
    first = canary._run_engine_worker(root, token, source)
    assert first.returncode == 0, first.stderr
    changed = canary._run_engine_worker(
        root, token, source, fingerprint="deterministic-transform-v2"
    )
    assert changed.returncode == 0, changed.stderr
    payload = json.loads(changed.stdout)
    assert payload["run"]["fallback_reason"] == "transform_fingerprint_changed"
    assert payload["checkpoint"]["commit_state"] == "complete"

    chroma = canary._run_engine_worker(root, token, source, chroma=True)
    assert chroma.returncode == 0, chroma.stderr
    assert json.loads(chroma.stdout)["authority"]["summaries"]


def test_capture_worker_fault_name_reaches_explicit_fault_option(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    crashed = canary._run_capture_worker(
        root, token, fault="before_snapshot_prepare"
    )
    assert crashed.returncode == canary.EXIT_CRASH, crashed.stderr


def test_worker_crash_exit_is_replayable_without_content_evidence(tmp_path: Path) -> None:
    root, token = create_fresh_root(tmp_path)
    source = root / "sources" / "sess_worker" / "messages.jsonl"
    source.parent.mkdir(parents=True)
    source.write_bytes(_source_bytes(4))
    crashed = canary._run_engine_worker(root, token, source, fault="before_publish")
    assert crashed.returncode == canary.EXIT_CRASH
    replay = canary._run_engine_worker(root, token, source)
    assert replay.returncode == 0, replay.stderr
    payload = json.loads(replay.stdout)
    assert payload["checkpoint"]["commit_state"] == "complete"
    assert payload["run"]["records"] == 4
    assert "canary-message" not in replay.stdout
