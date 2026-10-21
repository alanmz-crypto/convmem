"""Boundary tests for the separate personal-project Restic profile."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import tempfile
from unittest import mock

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/restic-personal-projects.py"
SPEC = importlib.util.spec_from_file_location("restic_personal_projects", SCRIPT)
profile = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profile)


def test_snapshot_requires_full_id():
    full_id = "a" * 64
    summary = json.dumps({"message_type": "summary", "snapshot_id": full_id})
    assert profile.snapshot_id(summary) == full_id
    with pytest.raises(profile.GateError):
        profile.snapshot_id("{}")


def test_snapshot_rejects_missing_root_or_wrong_lineage():
    sid = "b" * 64
    expected = [str(path) for path in profile.SOURCES]
    with mock.patch.object(profile, "restic", return_value=[
        {"id": sid, "paths": expected[:-1], "original": "a" * 64}
    ]):
        with pytest.raises(profile.GateError, match="exact thirteen"):
            profile.exact_snapshot(profile.EXTERNAL, sid, original="a" * 64)
    with mock.patch.object(profile, "restic", return_value=[
        {"id": sid, "paths": expected, "original": "c" * 64}
    ]):
        with pytest.raises(profile.GateError, match="lineage"):
            profile.exact_snapshot(profile.EXTERNAL, sid, original="a" * 64)


def test_external_failure_keeps_local_snapshot_distinct():
    sid = "d" * 64
    sample = Path("/tmp/example")
    inventory = {str(sample): {"sha256": "e" * 64}}
    with mock.patch.object(profile, "require_local_ready"), \
            mock.patch.object(profile, "restic", side_effect=[[], "json output"]), \
            mock.patch.object(profile, "quiesce_services", return_value=["writer.service"]), \
            mock.patch.object(profile, "restart_services") as restart, \
            mock.patch.object(profile, "writable_open_files", return_value=[]), \
            mock.patch.object(profile, "source_inventory",
                              side_effect=[(inventory, [sample]), (inventory, [sample])]), \
            mock.patch.object(profile, "snapshot_id", return_value=sid), \
            mock.patch.object(profile, "exact_snapshot"), \
            mock.patch.object(profile, "copy_and_verify",
                              side_effect=profile.GateError("drive absent")):
        result = profile.backup(quiesce=True, full_read=False)
    restart.assert_called_once_with(["writer.service"])
    assert result["result"] == "LOCAL_ONLY"
    assert result["local_snapshot"] == sid
    assert result["external_copy"] == "failed or unverified"


def test_new_outside_symlink_is_unreviewed(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "escape").symlink_to("/etc/hosts")
    with mock.patch.object(profile, "SOURCES", (root,)):
        result = profile.symlink_report()
    assert result["outside_manifest"] == 1
    assert len(result["unreviewed_outside"]) == 1


def test_copy_uses_explicit_source_repository_flags_after_subcommand():
    completed = mock.Mock(returncode=0, stdout="ok", stderr="")
    with mock.patch.object(profile.subprocess, "run", return_value=completed) as run:
        assert profile.restic(profile.EXTERNAL, "copy", "f" * 64,
                              from_repo=profile.LOCAL) == "ok"
    command = run.call_args.args[0]
    index = command.index("copy")
    assert command[index + 1:index + 5] == [
        "--from-repo", str(profile.LOCAL),
        "--from-password-file", str(profile.PASSWORD),
    ]
    assert command[-1] == "f" * 64


def test_reviewed_socket_is_transient_and_fifo_entry_is_inventoried():
    with tempfile.TemporaryDirectory(prefix="rp-", dir="/tmp") as scratch:
        base = Path(scratch)
        viewer = base / "butsaba-index-preview"
        runtime = viewer / "profiles/office/runtime"
        runtime.mkdir(parents=True)
        (viewer / "sample.txt").write_text("data")
        endpoint = runtime / "bus"
        bound = socket.socket(socket.AF_UNIX)
        bound.bind(str(endpoint))
        fixture = base / "ryan-index-preview/crush-tests-v2/evidence/save-snapshot-test"
        fixture.mkdir(parents=True)
        (fixture / "sample.txt").write_text("data")
        os.mkfifo(fixture / "pipe")
        try:
            with mock.patch.object(profile, "SHARE", base), \
                    mock.patch.object(profile, "SOURCES", (viewer, fixture.parents[2])):
                specials = profile.special_report()
                entries, samples = profile.source_inventory()
        finally:
            bound.close()
        assert specials["unreviewed"] == []
        assert specials["runtime_sockets_not_restorable"] == 1
        assert specials["fifo_entries"] == 1
        assert str(endpoint) not in entries
        assert entries[str(fixture / "pipe")]["fifo"] >= 0
        assert len(samples) == 2


# ref: ../scripts/restic-personal-projects.py — source, lineage, and result boundaries
