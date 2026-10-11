"""D1 isolation probes: network namespace artifacts and non-mutating bwrap FS checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.watch_oom_live_diagnosis_bwrap import (
    BWRAP_RO_ROOT_ARGS,
    d1_bwrap_integration_available,
    run_bwrap_capability_check,
    write_denied_without_mutation,
)
from tests.watch_oom_live_diagnosis_net_probe import (
    NetProbeVerificationError,
    parent_can_connect_loopback,
    parent_loopback_listener,
    parent_net_namespace_id,
    verify_dual_net_probe_artifacts,
)
from tests.watch_oom_live_diagnosis_support import (
    D1_BWRAP_ACTIVE_ENV,
    d1_worker_enter_bwrap_or_exit,
)

ROOT = Path(__file__).resolve().parents[1]


def test_worker_without_bwrap_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tests.watch_oom_live_diagnosis_bwrap as bwrap_mod

    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.delenv(D1_BWRAP_ACTIVE_ENV, raising=False)
    monkeypatch.setattr(bwrap_mod, "bwrap_available", lambda: False)
    with pytest.raises(RuntimeError, match="d1_bwrap_unavailable"):
        d1_worker_enter_bwrap_or_exit(
            argv=["unused"],
            scratch_root=tmp_path,
            source_path=tmp_path / "source.jsonl",
            repo_root=ROOT,
        )


def test_worker_bwrap_launch_failure_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tests.watch_oom_live_diagnosis_bwrap as bwrap_mod

    monkeypatch.setenv("CONVMEM_LIVE_DIAG_HERMETIC", "1")
    monkeypatch.delenv(D1_BWRAP_ACTIVE_ENV, raising=False)
    monkeypatch.setattr(bwrap_mod, "bwrap_available", lambda: True)
    monkeypatch.setattr(bwrap_mod, "build_bwrap_command", lambda *_a, **_k: ["false"])
    with pytest.raises(SystemExit) as exc:
        d1_worker_enter_bwrap_or_exit(
            argv=["unused"],
            scratch_root=tmp_path,
            source_path=tmp_path / "source.jsonl",
            repo_root=ROOT,
        )
    assert exc.value.code != 0


def test_write_probe_never_mutates_when_isolation_broken(tmp_path: Path) -> None:
    writable = tmp_path / "writable.txt"
    writable.write_bytes(b"original\n")
    os.utime(writable, ns=(1_000_000_000, 1_000_000_000))
    before = writable.stat()
    assert write_denied_without_mutation(writable) is False
    after = writable.stat()
    assert writable.read_bytes() == b"original\n"
    assert (after.st_size, after.st_mtime_ns, after.st_ino) == (
        before.st_size,
        before.st_mtime_ns,
        before.st_ino,
    )

    missing = tmp_path / "missing.txt"
    assert write_denied_without_mutation(missing) is False
    assert not missing.exists()

    readonly = tmp_path / "readonly.txt"
    readonly.write_bytes(b"ro\n")
    readonly.chmod(0o444)
    assert write_denied_without_mutation(readonly) is True
    assert readonly.read_bytes() == b"ro\n"


def test_net_probe_parent_positive_control() -> None:
    with parent_loopback_listener() as port:
        assert parent_can_connect_loopback(port) is True


def _write_probe_artifact(path: Path, *, role: str, pid: int, netns_id: str, errno: int | None) -> None:
    payload = {
        "role": role,
        "pid": pid,
        "port": 12345,
        "netns_id": netns_id,
        "connected": False,
        "status": "connect_failed",
    }
    if errno is not None:
        payload["errno"] = errno
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_net_probe_verify_dual_artifacts(tmp_path: Path) -> None:
    parent_ns = parent_net_namespace_id() or "net:[parent]"
    outer_path = tmp_path / "outer.json"
    inner_path = tmp_path / "inner.json"
    _write_probe_artifact(outer_path, role="outer", pid=100, netns_id="net:[child]", errno=111)
    _write_probe_artifact(inner_path, role="inner", pid=200, netns_id="net:[child]", errno=111)
    verify_dual_net_probe_artifacts(
        outer_path=outer_path,
        inner_path=inner_path,
        port=12345,
        parent_netns=parent_ns,
        parent_positive_control=True,
        outer_pid=100,
        inner_pid=200,
    )
    bad_outer = tmp_path / "bad_outer.json"
    bad_inner = tmp_path / "bad_inner.json"
    _write_probe_artifact(bad_outer, role="outer", pid=1, netns_id=parent_ns, errno=None)
    _write_probe_artifact(bad_inner, role="inner", pid=2, netns_id=parent_ns, errno=None)
    with pytest.raises(NetProbeVerificationError, match="net_probe_target_netns_equals_parent"):
        verify_dual_net_probe_artifacts(
            outer_path=bad_outer,
            inner_path=bad_inner,
            port=12345,
            parent_netns=parent_ns,
            parent_positive_control=True,
        )


@pytest.mark.skipif(
    not d1_bwrap_integration_available(),
    reason="bwrap user-ns integration unavailable on this host",
)
def test_net_probe_self_artifact_in_isolated_net(tmp_path: Path) -> None:
    outer_artifact = tmp_path / "outer.json"
    with parent_loopback_listener() as port:
        cmd = [
            "bwrap",
            "--unshare-net",
            *BWRAP_RO_ROOT_ARGS,
            "--bind",
            str(tmp_path),
            str(tmp_path),
            "--",
            sys.executable,
            "-c",
            (
                "import sys\n"
                f"sys.path.insert(0, {str(ROOT)!r})\n"
                "from pathlib import Path\n"
                "from tests.watch_oom_live_diagnosis_net_probe import write_self_loopback_probe\n"
                f"write_self_loopback_probe(port={port}, result_path=Path({str(outer_artifact)!r}), role='outer')\n"
            ),
        ]
        result = subprocess.run(
            cmd, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False
        )
        assert result.returncode == 0, result.stderr
    payload = json.loads(outer_artifact.read_text(encoding="utf-8"))
    assert payload["connected"] is False
    assert payload["port"] == port
    parent_ns = parent_net_namespace_id()
    assert parent_ns
    assert payload["netns_id"] != parent_ns


@pytest.mark.skipif(
    not d1_bwrap_integration_available(),
    reason="bwrap user-ns integration unavailable on this host",
)
def test_bwrap_filesystem_capabilities(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    source = tmp_path / "source.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    repo_probe = ROOT / "tests" / "watch_oom_live_diagnosis_bwrap.py"
    repo_before = repo_probe.stat()
    caps = run_bwrap_capability_check(
        scratch_root=scratch,
        source_path=source,
        repo_root=ROOT,
        repo_probe_file=repo_probe,
    )
    assert caps["scratch_writable"] is True
    assert caps["source_readonly"] is True
    assert caps["repo_readonly"] is True
    assert caps["production_share_read_blocked"] is True
    assert caps["production_share_write_blocked"] is True
    assert source.read_text(encoding="utf-8") == "{}\n"
    repo_after = repo_probe.stat()
    assert (repo_after.st_size, repo_after.st_mtime_ns) == (
        repo_before.st_size,
        repo_before.st_mtime_ns,
    )
