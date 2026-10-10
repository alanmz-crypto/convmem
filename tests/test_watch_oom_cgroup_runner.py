"""Pure fail-closed checks for the gated cgroup service boundary."""

import json
import sys
from pathlib import Path

import pytest

from tests.watch_oom_cgroup_runner import (
    MEMORY_LIMIT_BYTES,
    TELEMETRY_MARKER,
    _parse_exit_telemetry,
    worker_limit_claim,
)


def _fake_membership(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "cgroup"
    parent = root / "user.slice"
    group = parent / "measurement.service"
    group.mkdir(parents=True)
    for location in (root, parent):
        (location / "memory.max").write_text("max\n", encoding="ascii")
        (location / "memory.swap.max").write_text("max\n", encoding="ascii")
    (group / "memory.max").write_text(f"{MEMORY_LIMIT_BYTES}\n", encoding="ascii")
    (group / "memory.swap.max").write_text("0\n", encoding="ascii")
    membership = tmp_path / "self.cgroup"
    membership.write_text("0::/user.slice/measurement.service\n", encoding="ascii")
    return root, parent, membership


def test_worker_claim_requires_own_effective_cap(tmp_path: Path) -> None:
    root, parent, membership = _fake_membership(tmp_path)
    claim = worker_limit_claim(
        MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root
    )
    assert claim["memory_max_bytes"] == MEMORY_LIMIT_BYTES
    assert claim["memory_swap_max_bytes"] == 0

    (parent / "memory.max").write_text(f"{MEMORY_LIMIT_BYTES // 2}\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="differs from the reviewed cap"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)


def test_worker_claim_rejects_unbounded_or_swapping_service(tmp_path: Path) -> None:
    root, _parent, membership = _fake_membership(tmp_path)
    group = root / "user.slice" / "measurement.service"
    (group / "memory.max").write_text("max\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="differs from the reviewed cap"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)

    (group / "memory.max").write_text(f"{MEMORY_LIMIT_BYTES}\n", encoding="ascii")
    (group / "memory.swap.max").write_text("max\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="differs from the reviewed cap"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)


def test_worker_claim_rejects_ambiguous_membership(tmp_path: Path) -> None:
    root, _parent, membership = _fake_membership(tmp_path)
    membership.write_text("0::/user.slice/measurement.service\n0::/other\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="unambiguous"):
        worker_limit_claim(MEMORY_LIMIT_BYTES, proc_cgroup=membership, root=root)


def test_exit_telemetry_requires_one_complete_matching_record() -> None:
    claim = {"memory_max_bytes": MEMORY_LIMIT_BYTES}
    evidence = {
        "claim": claim,
        "peak_bytes": 4096,
        "events": {"max": 0, "oom": 1, "oom_kill": 1},
        "worker_returncode": -9,
    }
    stderr = "worker log\n" + TELEMETRY_MARKER + json.dumps(evidence) + "\n"
    assert _parse_exit_telemetry(stderr, claim) == evidence
    assert _parse_exit_telemetry(stderr + stderr, claim) is None
    assert _parse_exit_telemetry(stderr, {"memory_max_bytes": 1}) is None
    assert _parse_exit_telemetry("worker log only\n", claim) is None


def test_standalone_smoke_rejects_production_scratch(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.test_watch_oom_exposure_index_e2e import _validated_scratch

    unsafe = Path.home() / ".local/share/convmem" / "cgroup-smoke-probe"
    monkeypatch.setenv("CONVMEM_E2E_SCRATCH", str(unsafe))
    with pytest.raises(AssertionError):
        _validated_scratch()
    assert not unsafe.exists()


def test_supervisor_emits_final_counters_before_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from tests import watch_oom_cgroup_runner as runner
    from tests.watch_oom_cgroup_supervisor import main

    group = tmp_path / "measurement.service"
    group.mkdir()
    (group / "memory.peak").write_text("8192\n", encoding="ascii")
    (group / "memory.events").write_text(
        "max 1\noom 1\noom_kill 1\n", encoding="ascii"
    )
    claim = {"cgroup_path": str(group), "memory_max_bytes": MEMORY_LIMIT_BYTES}
    monkeypatch.setattr(runner, "worker_limit_claim", lambda _cap: claim)
    monkeypatch.setattr(
        sys, "argv", ["supervisor", str(MEMORY_LIMIT_BYTES), sys.executable,
                      "-c", "import sys; sys.exit(17)"]
    )
    assert main() == 17
    stderr = capsys.readouterr().err
    assert _parse_exit_telemetry(stderr, claim) == {
        "claim": claim,
        "peak_bytes": 8192,
        "events": {"max": 1, "oom": 1, "oom_kill": 1},
        "worker_returncode": 17,
    }
