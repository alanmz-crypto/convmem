"""Hermetic acknowledgment contract: exact identity, FAIL preservation and durable writes."""

# pylint: disable=too-many-lines

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import shlex
import shutil
import socket
import stat
import subprocess
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import cpu_tripwire as tripwire
import cpu_tripwire_ack as ack
import cpu_tripwire_cli as cli
from cpu_tripwire_events import Fault, ackable, parse_kernel_journal
from tests.test_cpu_tripwire import (
    GP_NO_CPU,
    INVALID_OPCODE,
    MCE,
    NOISE,
    SEGV_CPU4,
    SEGV_CPU8,
    TYPORA_GPF,
)

BOOT = "7f8e9d592ecc46c7aeb599df6b9457b2"
OTHER_BOOT = "a" * 32
REALTIME = 1792692082959438
MONOTONIC = 216789351540
CURSOR = (
    "s=e02dcabee64b4080b72afc4344ccf25d;i=56398d5;b=7f8e9d592ecc46c7aeb599df6b9457b2;"
    "m=327a1c130d;t=65e71a6cbe44e;x=81580ac8b8a26341"
)
MESSAGE = (
    "timeshift[835726]: segfault at 0 ip 0000557bdb8648da sp 00007ffe1ccb1ff0 error 4 "
    "in timeshift[168da,557bdb854000+40000] likely on CPU 13 (core 33, socket 0)"
)
ACK_ID = "bab67b49aa4f5178700bbab29af53533a3bc4da7a74c6bdde16c051c2902675b"
CFG = {"hardware": {"known_bad_cpus": [4, 5, 8, 9]}}
NOW = "2026-10-23T05:00:00Z"
OPERATOR = ack.Operator(
    "ryan", "Investigated storage disconnect", "docs/plans/grant.md"
)


@pytest.fixture(autouse=True)
def hermetic(tmp_path, monkeypatch):
    old_tz = os.environ.get("TZ")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("TZ", "America/Chicago")
    time.tzset()
    real_run = subprocess.run
    real_read = Path.read_text

    def guarded_run(argv, *args, **kwargs):
        if isinstance(argv, (list, tuple)) and Path(str(argv[0])).name in (
            "journalctl",
            "coredumpctl",
        ):
            raise AssertionError("real host journal access forbidden")
        return real_run(argv, *args, check=kwargs.pop("check", False), **kwargs)

    def guarded_read(path, *args, **kwargs):
        if str(path).startswith(("/proc/", "/sys/")):
            raise AssertionError("real host proc/sys access forbidden")
        return real_read(path, *args, **kwargs)

    def no_network(*_args, **_kwargs):
        raise AssertionError("network access forbidden")

    monkeypatch.setattr(subprocess, "run", guarded_run)
    monkeypatch.setattr(Path, "read_text", guarded_read)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    yield
    if old_tz is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old_tz
    time.tzset()


def entry(message=MESSAGE, **changes):
    row = {
        "MESSAGE": message,
        "_BOOT_ID": BOOT,
        "__REALTIME_TIMESTAMP": str(REALTIME),
        "_SOURCE_MONOTONIC_TIMESTAMP": str(MONOTONIC),
        "__CURSOR": CURSOR,
        "_HOSTNAME": "archlinux",
    }
    row.update(changes)
    return row


def parsed(rows=None):
    return parse_kernel_journal(
        json.dumps(row) if not isinstance(row, str) else row
        for row in ([entry()] if rows is None else rows)
    )


def context(rows=None, boot=BOOT):
    journal = parsed(rows)
    return ack.AckContext(journal.faults, boot, {4, 5, 8, 9})


def _confirmed(_fault, identifier):
    return identifier


def write(path, ctx=None, **options):
    ctx = context() if ctx is None else ctx
    options = {
        "confirm": _confirmed,
        "tty_check": lambda: "/dev/pts/test",
        "now": lambda: NOW,
        **options,
    }
    return ack.write_ack(ctx.faults[0].key, OPERATOR, lambda: ctx, path=path, **options)


@pytest.fixture(name="stored")
def stored_ack(tmp_path):
    path = tmp_path / "ack.json"
    write(path)
    return path


def evaluate(path, rows=None, boot=BOOT, online=None, dumps=None):
    return tripwire.evaluate(
        parsed(rows).faults,
        dumps or [],
        set() if online is None else online,
        {4, 5, 8, 9},
        acks=ack.load_acks(path),
        current_boot_id=boot,
    )


class FakeRunner:
    def __init__(self, rows, dumps=None, returncode=0):
        self.lines = [
            json.dumps(row) if not isinstance(row, str) else row for row in rows
        ]
        self.dumps = [] if dumps is None else dumps
        self.returncode = returncode
        self.calls = []

    def __call__(self, argv):
        self.calls.append(list(argv))
        if argv[0] == "journalctl":
            return subprocess.CompletedProcess(
                argv, self.returncode, "\n".join(self.lines), ""
            )
        if argv[0] == "coredumpctl":
            return subprocess.CompletedProcess(argv, 0, json.dumps(self.dumps), "")
        raise AssertionError(f"unexpected command: {argv}")


def paths(tmp_path, *, online="0-3,6-7,10-19", boot=BOOT):
    for name, content in (
        ("online", online),
        ("stat", "cpu 1 2\nbtime 1790000000\n"),
        ("boot", boot),
    ):
        (tmp_path / name).write_text(content, encoding="utf-8")
    return {
        "online_path": tmp_path / "online",
        "proc_stat": tmp_path / "stat",
        "boot_id_path": tmp_path / "boot",
    }


@pytest.mark.parametrize(
    "line", [SEGV_CPU8, SEGV_CPU4, GP_NO_CPU, INVALID_OPCODE, MCE, TYPORA_GPF, *NOISE]
)
def test_t1_short_iso_and_json_policy_are_identical(line):
    head, _, message = line.partition(" kernel: ")
    stamp = datetime.fromisoformat(head.split(" ", 1)[0])
    new = parsed(
        [entry(message, __REALTIME_TIMESTAMP=str(int(stamp.timestamp()) * 1_000_000))]
    ).faults
    old = tripwire.parse_kernel_faults([line])
    fields = ("when", "kind", "cpu", "process", "pid")
    assert [[getattr(f, key) for key in fields] for f in old] == [
        [getattr(f, key) for key in fields] for f in new
    ]
    assert tripwire.evaluate(old, [], set(), {8, 9}) == tripwire.evaluate(
        new, [], set(), {8, 9}
    )


def test_t2_identity_and_published_hash():
    fault = parsed().faults[0]
    assert (
        fault.describe()
        == "timeshift[835726] segfault on CPU 13 at 2026-10-22T13:01:22-05:00"
    )
    assert fault.key.ack_id == ACK_ID
    assert fault.key.message_sha256 == hashlib.sha256(MESSAGE.encode()).hexdigest()
    assert fault.key.cursor == CURSOR


def test_t3_missing_file_is_not_opened(tmp_path, monkeypatch):
    real_open = os.open
    target = ack.default_ack_path()

    def guarded(path, *args, **kwargs):
        assert Path(path) != target
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", guarded)
    result = tripwire.check(CFG, runner=FakeRunner([entry()]), **paths(tmp_path))
    assert result == tripwire.evaluate(parsed().faults, [], set(), {4, 5, 8, 9})


def test_t4_t5_visible_warning_and_explained_dump(stored):
    result = evaluate(
        stored, dumps=[{"pid": 835726, "sig": 11, "exe": "/usr/bin/timeshift"}]
    )
    assert result.status == "warn"
    assert all(
        text in result.detail
        for text in ("acknowledged", ACK_ID[:12], "ryan", "hardware health unproven")
    )
    assert (
        "orphan" not in result.detail
        and "no CPU in the kernel log" not in result.detail
    )


@pytest.mark.parametrize(
    "change",
    [
        {
            "MESSAGE": MESSAGE.replace("835726", "999999"),
            "__REALTIME_TIMESTAMP": str(REALTIME + 1),
        },
        {
            "__REALTIME_TIMESTAMP": str(REALTIME + 1),
            "_SOURCE_MONOTONIC_TIMESTAMP": str(MONOTONIC + 1),
        },
        {"MESSAGE": MESSAGE.replace("0000557bdb8648da", "0000557bdb8648db")},
        {"MESSAGE": MESSAGE.replace("CPU 13", "CPU 14")},
    ],
)
def test_t6_t7_t8_t12_new_faults_fail(stored, change):
    result = evaluate(stored, [entry(), entry(**change)])
    assert result.status == "fail"
    assert f"plus 1 acknowledged fault (ack {ACK_ID[:12]})" in result.detail
    assert "by ryan" in result.detail


def test_t9_duplicate_full_key_is_ambiguous(stored):
    result = evaluate(stored, [entry(), entry()])
    assert result.status == "fail" and "ambiguous key" in result.detail


def test_t10_t11_machine_check_and_online_bad_cpu_cannot_be_hidden(stored):
    mce = MCE.partition(" kernel: ")[2]
    result = evaluate(stored, [entry(), entry(mce, __CURSOR="mce")])
    assert result.status == "fail" and "by ryan" in result.detail
    result = evaluate(stored, online={4})
    assert result.status == "fail" and "ONLINE again" in result.detail
    assert "by ryan" in result.detail


def test_t13_userspace_advisory_is_preserved(stored):
    result = evaluate(
        stored,
        [entry(), entry(TYPORA_GPF.partition(" kernel: ")[2], __CURSOR="typora")],
    )
    assert (
        result.status == "warn"
        and "userspace" in result.detail
        and "acknowledged" in result.detail
    )


def test_t14_t15_t17_inert_records_do_not_change_the_base_policy(stored):
    result = evaluate(stored, [entry(_BOOT_ID=OTHER_BOOT)], boot=OTHER_BOOT)
    assert result.status == "fail" and "previous boot" in result.detail
    result = evaluate(stored, [], boot=OTHER_BOOT)
    assert result.status == "pass" and "previous boot" in result.detail
    result = evaluate(stored, [])
    assert result.status == "pass" and "entry not present" in result.detail


@pytest.mark.parametrize("boot", ["invalid", "", OTHER_BOOT])
def test_t16_boot_mismatch_disables_ack(stored, tmp_path, boot):
    result = tripwire.check(
        CFG, runner=FakeRunner([entry()]), ack_path=stored, **paths(tmp_path, boot=boot)
    )
    assert result.status == "fail" and "boot identity mismatch" in result.detail


def test_t16_noise_boot_mismatch_and_missing_boot_file(stored, tmp_path):
    injected = paths(tmp_path)
    noise = entry("noise", _BOOT_ID=OTHER_BOOT, __CURSOR="noise")
    result = tripwire.check(
        CFG, runner=FakeRunner([entry(), noise]), ack_path=stored, **injected
    )
    assert result.status == "fail" and "boot identity mismatch" in result.detail
    (tmp_path / "boot").unlink()
    result = tripwire.check(CFG, runner=FakeRunner([]), ack_path=stored, **injected)
    assert result.status == "warn" and "boot identity mismatch" in result.detail


@pytest.mark.parametrize(
    "body", [b"", b"{", b"[]", b"x" * (ack.MAX_FILE_BYTES + 1), b"\xff"]
)
def test_t18_invalid_file_rejects_all_records(stored, body):
    stored.write_bytes(body)
    assert evaluate(stored).status == "fail"
    result = evaluate(stored, [])
    assert result.status == "warn" and "acknowledgment file invalid" in result.detail


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema",), "wrong"),
        (("version",), 2),
        (("version",), "1"),
        (("version",), True),
        (("extra",), 1),
        (("acknowledgments",), {}),
        (("acknowledgments", 0, "extra"), 1),
        (("acknowledgments", 0, "event", "realtime_us"), str(REALTIME)),
        (("acknowledgments", 0, "event", "realtime_us"), -1),
        (("acknowledgments", 0, "event", "cpu"), None),
        (("acknowledgments", 0, "event", "cpu"), True),
        (("acknowledgments", 0, "event", "boot_id"), BOOT.upper()),
        (
            ("acknowledgments", 0, "event", "boot_id"),
            "7f8e9d59-2ecc-46c7-aeb5-99df6b9457b2",
        ),
        (("acknowledgments", 0, "event", "message_sha256"), "F" * 64),
        (("acknowledgments", 0, "event", "cursor"), ""),
        (("acknowledgments", 0, "event", "cursor"), "x" * 257),
        (("acknowledgments", 0, "event", "cursor"), "x\n"),
        (("acknowledgments", 0, "event", "cursor"), "é"),
        (("acknowledgments", 0, "ack_id"), "0" * 64),
        (("acknowledgments", 0, "evidence", "message"), MESSAGE + "x"),
        (("acknowledgments", 0, "event", "kind"), "machine_check"),
        (("acknowledgments", 0, "event", "kind"), "kernel_oops"),
        (("acknowledgments", 0, "event", "cpu"), 14),
        (("acknowledgments", 0, "event", "process"), "other"),
        (("acknowledgments", 0, "event", "pid"), None),
        (("acknowledgments", 0, "reason"), ""),
        (("acknowledgments", 0, "reason"), "x" * 501),
        (("acknowledgments", 0, "reason"), "\x1b[2J"),
        (("acknowledgments", 0, "authority_ref"), "../outside"),
        (("acknowledgments", 0, "acknowledged_at"), "yesterday"),
        (("acknowledgments", 0, "revoked_at"), NOW),
    ],
)
def test_t19_to_t28_schema_failures(stored, path, value):
    document = json.loads(stored.read_text())
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    stored.write_text(json.dumps(document))
    result = evaluate(stored)
    assert result.status == "fail" and "no acknowledgments applied" in result.detail
    assert evaluate(stored, []).status == "warn"


def test_t20_t27_missing_fields_and_duplicate_ids(stored):
    document = json.loads(stored.read_text())
    document["acknowledgments"].append(copy.deepcopy(document["acknowledgments"][0]))
    stored.write_text(json.dumps(document))
    assert "duplicate ack_id" in ack.load_acks(stored).problem
    document["acknowledgments"].pop()
    del document["acknowledgments"][0]["reason"]
    stored.write_text(json.dumps(document))
    assert "wrong record fields" in ack.load_acks(stored).problem


def test_duplicate_json_keys_rejected(stored):
    stored.write_text(
        '{"schema":"wrong","schema":"'
        + ack.ACK_SCHEMA
        + '","version":1,"acknowledgments":[]}'
    )
    assert "duplicate JSON field" in ack.load_acks(stored).problem


def test_t29_directory_permissions_symlink_and_read_error(
    stored, tmp_path, monkeypatch
):
    assert ack.load_acks(tmp_path).problem
    link = tmp_path / "link"
    link.symlink_to(stored)
    assert ack.load_acks(link).problem
    stored.chmod(0)
    if os.geteuid() != 0:
        assert ack.load_acks(stored).problem
    stored.chmod(0o600)
    monkeypatch.setattr(
        os, "open", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError(5, "I/O"))
    )
    assert "EIO" in ack.load_acks(stored).problem


def test_insecure_acknowledgment_file_is_not_applied(stored, monkeypatch):
    stored.chmod(0o666)
    assert "mode" in ack.load_acks(stored).problem
    assert evaluate(stored).status == "fail"

    stored.chmod(0o600)
    actual_euid = os.geteuid()
    with monkeypatch.context() as patch:
        patch.setattr(os, "geteuid", lambda: actual_euid + 1)
        assert "owner" in ack.load_acks(stored).problem
        assert evaluate(stored).status == "fail"


def test_t30_stray_temp_files_are_ignored(stored):
    stored.with_name(stored.name + ".tmp-abandoned").write_text("garbage")
    assert evaluate(stored).status == "warn"
    stored.unlink()
    assert evaluate(stored).status == "fail"


def test_t31_t32_revocation_and_same_key_reack_refusal(stored):
    before = json.loads(stored.read_text())["acknowledgments"][0]
    identifier, changed = ack.revoke_ack(
        ACK_ID[:12], OPERATOR, path=stored, now=lambda: NOW
    )
    assert identifier == ACK_ID and changed
    after = json.loads(stored.read_text())["acknowledgments"][0]
    assert after["revoked_at"] == NOW and after["revoked_by"] == "ryan"
    assert all(
        after[key] == value
        for key, value in before.items()
        if not key.startswith("revok") and key != "revocation_reason"
    )
    assert evaluate(stored).status == "fail"
    content = stored.read_bytes()
    with pytest.raises(ack.AckError, match="was revoked"):
        write(stored)
    assert stored.read_bytes() == content
    assert ack.revoke_ack(ACK_ID, OPERATOR, path=stored)[1] is False
    assert stored.read_bytes() == content
    stored.write_text("{")
    with pytest.raises(ack.AckError):
        ack.revoke_ack(ACK_ID, OPERATOR, path=stored)
    assert stored.read_text() == "{"


def test_t33_t34_t35_t36_writer_refusals(tmp_path):
    path = tmp_path / "ack.json"
    with pytest.raises(ack.TtyRequired):
        write(path, tty_check=lambda: None)
    ctx = context()
    for faults in ([], ctx.faults * 2):
        with pytest.raises(ack.AckError, match="exactly one"):
            ack.write_ack(
                ctx.faults[0].key,
                OPERATOR,
                lambda faults=faults: replace(ctx, faults=faults),
                path=path,
                tty_check=lambda: "/dev/pts/test",
            )
    for message in (
        MCE.partition(" kernel: ")[2],
        "Oops: likely on CPU 13",
        GP_NO_CPU.partition(" kernel: ")[2],
        MESSAGE.replace("CPU 13", "CPU 4"),
    ):
        with pytest.raises(ack.AckError, match="FAIL contributor"):
            write(path, context([entry(message)]))
    with pytest.raises(ack.AckError, match="confirmation"):
        write(path, confirm=lambda *_args: "wrong")
    assert not path.exists()


def test_t37_t38_success_atomic_mode_evidence_idempotence(tmp_path):
    path = tmp_path / "ack.json"
    ctx = context()
    ctx.dumps = [
        {
            "pid": 835726,
            "sig": 11,
            "time": REALTIME + 118215,
            "exe": "/usr/bin/timeshift",
        }
    ]
    assert write(path, ctx) == (ACK_ID, True)
    assert path.stat().st_mode & 0o777 == 0o600
    loaded = ack.load_acks(path)
    assert (
        loaded.problem is None
        and loaded.records[0]["evidence"]["coredump"]["pid"] == 835726
    )
    original = path.read_bytes()
    assert write(path, ctx) == (ACK_ID, False)
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.tmp-*"))


def test_t39_lock_contention(stored):
    with (stored.parent / ".cpu-tripwire-acknowledgments.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = stored.read_bytes()
        with pytest.raises(ack.AckError, match="lock is busy"):
            write(stored)
        assert stored.read_bytes() == original


@pytest.mark.parametrize("operation", ["replace", "fsync"])
@pytest.mark.parametrize(
    "action,existing", [("ack", False), ("ack", True), ("revoke", True)]
)
def test_t40_pre_replace_failure_keeps_old_document(
    tmp_path, monkeypatch, operation, action, existing
):
    path = tmp_path / "ack.json"
    if existing:
        write(path)
    original = path.read_bytes() if existing else None
    ctx = context([entry(__CURSOR="new-cursor")])

    def fail(*_args):
        raise OSError("simulated interruption")

    monkeypatch.setattr(os, operation, fail)
    with pytest.raises(OSError):
        if action == "ack":
            write(path, ctx)
        else:
            ack.revoke_ack(ACK_ID, OPERATOR, path=path, now=lambda: NOW)
    assert (path.read_bytes() if path.exists() else None) == original
    assert not list(tmp_path.glob("*.tmp-*"))


def test_t41_doctor_warn_mapping_and_exit(stored, monkeypatch):
    from doctor import _check_cpu_tripwire, doctor_exit_code

    monkeypatch.setattr(tripwire, "check", lambda _cfg: evaluate(stored))
    result = _check_cpu_tripwire({})
    assert result.ok and result.effective_status() == "warn"
    assert doctor_exit_code([result]) == 0


def test_t42_invalid_utf8_is_hashed_and_persisted_losslessly(tmp_path):
    raw = MESSAGE.encode() + b"\xff"
    ctx = context([entry(list(raw))])
    assert ctx.faults[0].message_sha256 == hashlib.sha256(raw).hexdigest()
    path = tmp_path / "ack.json"
    write(path, ctx)
    assert ack.load_acks(path).records[0]["evidence"]["message"] == list(raw)
    assert evaluate(path, [entry(list(raw))]).status == "warn"


@pytest.mark.parametrize(
    "bad", ["{", "[]", entry(None), entry([999]), entry([True]), entry({})]
)
@pytest.mark.parametrize(
    "new_fault", [MESSAGE.replace("CPU 13", "CPU 14"), MCE.partition(" kernel: ")[2]]
)
@pytest.mark.parametrize("bad_first", [False, True])
def test_t43_partial_json_failure_preserves_fail(
    stored, tmp_path, bad, new_fault, bad_first
):
    rows = [entry(), entry(new_fault, __CURSOR="new-fault")]
    rows.insert(0 if bad_first else len(rows), bad)
    runner = FakeRunner(rows)
    result = tripwire.check(CFG, runner=runner, ack_path=stored, **paths(tmp_path))
    assert result.status == "fail" and "no acknowledgments applied" in result.detail
    assert "unreadable" in result.detail
    assert (
        "machine_check" if "Machine Check" in new_fault else "CPU 14"
    ) in result.detail
    assert len([args for args in runner.calls if args[0] == "journalctl"]) == 1
    assert "--all" in runner.calls[0]


def test_blind_read_keeps_online_bad_cpu_failure(tmp_path):
    result = tripwire.check(
        CFG, runner=FakeRunner(["{"], returncode=1), **paths(tmp_path, online="0-23")
    )
    assert result.status == "fail" and "ONLINE again" in result.detail


def test_large_and_repeated_messages_preserve_failures(tmp_path):
    long_message = MESSAGE + " x" * 5000
    for message in (long_message, ["noise", MESSAGE]):
        result = tripwire.check(
            CFG, runner=FakeRunner([entry(message)]), **paths(tmp_path)
        )
        assert result.status == "fail" and "timeshift" in result.detail


def test_t45_t46_t47_vacuum_cursor_change_and_missing_cursor(stored):
    survivor = entry(__CURSOR="different-entry")
    result = evaluate(stored, [survivor])
    assert result.status == "fail" and "entry not present" in result.detail
    assert evaluate(stored).status == "warn"
    missing = entry()
    del missing["__CURSOR"]
    assert parsed([missing]).faults[0].key is None
    assert evaluate(stored, [missing]).status == "fail"
    ctx = context([survivor])
    ack.revoke_ack(ACK_ID, OPERATOR, path=stored, now=lambda: NOW)
    assert write(stored, ctx)[1]
    assert len(ack.load_acks(stored).records) == 2
    assert evaluate(stored, [survivor]).status == "warn"


@pytest.mark.parametrize(
    "field",
    ["_BOOT_ID", "__REALTIME_TIMESTAMP", "_SOURCE_MONOTONIC_TIMESTAMP", "__CURSOR"],
)
def test_missing_identity_never_drops_classification(field):
    row = entry()
    del row[field]
    fault = parsed([row]).faults[0]
    assert not ackable(fault, set())
    assert tripwire.evaluate([fault], [], set(), set()).status == "fail"


def test_t44_show_json_states_and_shell_quoted_command(monkeypatch):
    import convmem

    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))
    runner = CliRunner()
    response = runner.invoke(convmem.app, ["tripwire", "show", "--json"])
    assert response.exit_code == 0, response.output
    payload = json.loads(response.output)
    command = payload["faults"][0]["ack_command"]
    args = shlex.split(command)
    assert args[args.index("--cursor") + 1] == CURSOR
    assert "tripwire" in convmem._SUBCOMMANDS  # pylint: disable=protected-access
    no_tty = runner.invoke(convmem.app, args[1:])
    assert no_tty.exit_code == 2 and not ack.default_ack_path().exists()
    path = ack.default_ack_path()
    write(path)
    response = runner.invoke(convmem.app, ["tripwire", "show", "--json"])
    assert json.loads(response.output)["acknowledgments"][0]["state"] == "applied"
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, OTHER_BOOT))
    assert (
        cli.show_payload(tripwire.SignalRead(parsed([]), [], set(), set()), OTHER_BOOT)[
            "acknowledgments"
        ][0]["state"]
        == "inert (previous boot)"
    )
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))
    response = runner.invoke(
        convmem.app,
        ["tripwire", "revoke", ACK_ID[:12], "--by", "ryan", "--reason", "undo"],
    )
    assert response.exit_code == 0 and "FAIL" in response.output
    payload = cli.show_payload(signals, BOOT)
    assert payload["acknowledgments"][0]["state"] == "revoked"
    assert payload["faults"][0]["ack_command"] is None
    response = runner.invoke(convmem.app, ["tripwire", "show"])
    assert response.exit_code == 0 and "revoked" in response.output


@pytest.mark.parametrize("shell", ["bash", "zsh"])
def test_printed_ack_command_survives_real_shell_parsing(shell):
    shell_path = shutil.which(shell)
    if shell_path is None:
        pytest.skip(f"{shell} is not installed on this test host")
    command = cli._ack_command(parsed().faults[0].key)  # pylint: disable=protected-access
    script = "convmem() { printf '%s\\0' \"$@\"; }\n" + command
    done = subprocess.run([shell_path, "-c", script], capture_output=True, check=True)
    args = done.stdout.decode().rstrip("\0").split("\0")
    assert args[args.index("--cursor") + 1] == CURSOR
    assert args[args.index("--reason") + 1] == "<reason>"


def test_acknowledgment_is_inert_if_fault_becomes_known_bad(stored):
    result = tripwire.evaluate(
        parsed().faults,
        [],
        set(),
        {13},
        acks=ack.load_acks(stored),
        current_boot_id=BOOT,
    )
    assert result.status == "warn" and "not needed" in result.detail
    assert "not cleared" not in result.detail


def test_invalid_utc_and_unreadable_metadata(stored, monkeypatch):
    document = json.loads(stored.read_text())
    document["acknowledgments"][0]["acknowledged_at"] = "invalidZ"
    stored.write_text(json.dumps(document))
    assert "invalid acknowledged_at" in ack.load_acks(stored).problem
    original_stat = Path.lstat

    def fail_target(path, *args, **kwargs):
        if path == stored:
            raise PermissionError(13, "denied")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", fail_target)
    assert "EACCES" in ack.load_acks(stored).problem


def test_cli_ack_success_confirmation_and_refusal(monkeypatch):
    import convmem

    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))
    monkeypatch.setattr(ack, "interactive_tty", lambda: "/dev/pts/test")
    payload = cli.show_payload(signals, BOOT)
    args = shlex.split(payload["faults"][0]["ack_command"])[1:]
    runner = CliRunner()
    response = runner.invoke(convmem.app, ["tripwire", "show"])
    assert response.exit_code == 0 and "--cursor" in response.output
    response = runner.invoke(convmem.app, args, input=ACK_ID[:12] + "\n")
    assert response.exit_code == 0, response.output
    assert "Acknowledged" in response.output and "WARN" in response.output
    response = runner.invoke(convmem.app, args)
    assert response.exit_code == 0 and "Already acknowledged" in response.output
    response = runner.invoke(
        convmem.app,
        ["tripwire", "revoke", "invalid", "--by", "ryan", "--reason", "undo"],
    )
    assert response.exit_code == 1 and "Refused" in response.output
    ack.default_ack_path().write_text("{")
    response = runner.invoke(convmem.app, ["tripwire", "show"])
    assert response.exit_code == 0 and "file invalid" in response.output


def test_cli_snapshot_collects_only_injected_inputs(monkeypatch, capsys):
    import config

    monkeypatch.setattr(config, "load_config", lambda: CFG)
    monkeypatch.setattr(
        cli,
        "read_signals",
        lambda cfg: (
            tripwire.SignalRead(parsed([]), [], set(), set()) if cfg == CFG else None
        ),
    )
    monkeypatch.setattr(cli, "read_boot_id", lambda: BOOT)
    assert cli.run_show(True) == 0
    assert json.loads(capsys.readouterr().out)["verdict"]["status"] == "pass"


def test_tty_check_requires_both_streams_and_a_real_tty_name(monkeypatch):
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert ack.interactive_tty() is None
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdin, "fileno", lambda: 0)
    monkeypatch.setattr(os, "ttyname", lambda _fd: "/dev/pts/test")
    assert ack.interactive_tty() == "/dev/pts/test"

    def fail(_fd):
        raise OSError("not a tty")

    monkeypatch.setattr(os, "ttyname", fail)
    assert ack.interactive_tty() is None


def test_dump_evidence_only_records_matching_hardware_dump(tmp_path):
    ctx = context()
    ctx.dumps = [
        {"pid": 835726, "sig": 11, "time": REALTIME - 1, "exe": "/bin/timeshift"},
        {"pid": 835726, "sig": 6, "time": REALTIME + 1, "exe": "/bin/timeshift"},
    ]
    path = tmp_path / "ack.json"
    write(path, ctx)
    assert ack.load_acks(path).records[0]["evidence"]["coredump"] is None


def test_non_dict_coredump_does_not_interrupt_ack_write(tmp_path):
    ctx = context()
    ctx.dumps = [
        None,
        "bad row",
        {"pid": 835726, "sig": 11, "time": REALTIME + 1, "exe": "/bin/timeshift"},
    ]
    path = tmp_path / "ack.json"
    assert write(path, ctx)[1]
    assert ack.load_acks(path).records[0]["evidence"]["coredump"]["pid"] == 835726


def test_missing_time_retains_classification():
    fault = parsed([entry(__REALTIME_TIMESTAMP="99999999999999999999")]).faults[0]
    assert fault.when == "unknown time" and fault.key is None
    assert tripwire.evaluate([fault], [], set(), set()).status == "fail"


def test_partial_read_without_detected_fault_warns(tmp_path):
    result = tripwire.check(CFG, runner=FakeRunner(["{"]), **paths(tmp_path))
    assert result.status == "warn" and "blind" in result.detail
    assert not result.detail.startswith("0 native faults this boot")


def test_unreadable_journal_does_not_claim_zero_faults(tmp_path):
    def denied(argv):
        if argv[0] == "journalctl":
            raise OSError("journal unavailable")
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    result = tripwire.check(CFG, runner=denied, **paths(tmp_path))
    assert result.status == "warn" and result.detail.startswith(
        "kernel fault count unknown"
    )


def test_journal_timeout_and_partial_nonzero_exit_preserve_other_evidence(tmp_path):
    def timeout(argv):
        if argv[0] == "journalctl":
            raise subprocess.TimeoutExpired(argv, 1)
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    result = tripwire.check(CFG, runner=timeout, **paths(tmp_path, online="0-23"))
    assert result.status == "fail" and "ONLINE again" in result.detail
    result = tripwire.check(
        CFG, runner=FakeRunner([entry()], returncode=1), **paths(tmp_path)
    )
    assert result.status == "fail" and "timeshift" in result.detail


def test_command_runner_arguments_without_running_host_tools(monkeypatch):
    def fake_run(argv, **options):
        assert argv == ["journalctl", "--example"]
        assert options == {
            "capture_output": True,
            "text": True,
            "timeout": 30,
            "check": False,
        }
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert tripwire._run(["journalctl", "--example"]).returncode == 0  # pylint: disable=protected-access


def test_ack_context_rejects_wrong_boot_before_confirmation(tmp_path):
    path = tmp_path / "ack.json"
    for ctx in (context(boot=OTHER_BOOT), replace(context(), problem="incomplete log")):
        with pytest.raises(ack.AckError):
            write(path, ctx)
    assert not path.exists()


def test_mixed_invalid_store_rejects_otherwise_valid_ack(stored):
    ctx = context([entry(__CURSOR="other")])
    write(stored, ctx)
    document = json.loads(stored.read_text())
    document["acknowledgments"][1]["reason"] = ""
    stored.write_text(json.dumps(document))
    assert evaluate(stored).status == "fail"
    assert not ack.load_acks(stored).records


def test_corrupt_or_missing_sysfs_and_boot_stat(tmp_path):
    injected = paths(tmp_path)
    (tmp_path / "stat").unlink()
    (tmp_path / "online").write_text("invalid")
    result = tripwire.check(CFG, runner=FakeRunner([entry()]), **injected)
    assert result.status == "fail"
    (tmp_path / "stat").write_text("cpu 1 2\n")
    result = tripwire.check(CFG, runner=FakeRunner([]), **injected)
    assert result.status == "warn" and "coredump list unreadable" in result.detail


def test_coredump_failure_cannot_erase_fault(tmp_path):
    runner = FakeRunner([entry()])

    def failed_dump(argv):
        if argv[0] == "coredumpctl":
            raise OSError("unreadable")
        return runner(argv)

    assert tripwire.check(CFG, runner=failed_dump, **paths(tmp_path)).status == "fail"
    assert (
        tripwire.read_coredumps(
            0, lambda argv: subprocess.CompletedProcess(argv, 0, "{", "")
        )
        is None
    )


@pytest.mark.parametrize("operation", ["ack", "revoke"])
@pytest.mark.parametrize("failure_site", ["directory_open", "directory_fsync"])
def test_post_replace_failure_and_same_command_retry(
    stored, monkeypatch, operation, failure_site
):
    ctx = context([entry(__CURSOR="new-cursor")])

    def operate():
        if operation == "ack":
            return write(stored, ctx)
        return ack.revoke_ack(ACK_ID, OPERATOR, path=stored, now=lambda: NOW)

    real_open, real_fsync = os.open, os.fsync

    def fail_open(path, flags, *args, **kwargs):
        if flags & os.O_DIRECTORY:
            raise OSError("directory open failed")
        return real_open(path, flags, *args, **kwargs)

    def fail_sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("directory fsync failed")
        return real_fsync(fd)

    monkeypatch.setattr(
        os,
        "open" if failure_site == "directory_open" else "fsync",
        fail_open if failure_site == "directory_open" else fail_sync,
    )
    with pytest.raises(ack.DurabilityUnconfirmed, match="document replaced"):
        operate()
    loaded = ack.load_acks(stored)
    assert loaded.problem is None
    if operation == "ack":
        assert (
            len(loaded.records) == 2
            and loaded.records[-1]["event"]["cursor"] == "new-cursor"
        )
    else:
        assert loaded.records[0]["revoked_at"] == NOW
    visible = stored.read_bytes()

    def no_replace(*_args):
        raise AssertionError("idempotent retry must not rewrite the document")

    monkeypatch.setattr(os, "replace", no_replace)
    with pytest.raises(ack.DurabilityUnconfirmed, match="existing document"):
        operate()
    assert stored.read_bytes() == visible
    monkeypatch.setattr(os, "open", real_open)
    synced = []

    def successful_sync(fd):
        synced.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", successful_sync)
    assert operate()[1] is False
    assert synced == ["file", "directory"]
    assert stored.read_bytes() == visible
    assert not list(stored.parent.glob("*.tmp-*"))


def test_existing_ack_retry_syncs_without_rereading_journal(stored, monkeypatch):
    before = stored.read_bytes()
    real_fsync = os.fsync
    synced = []

    def track_sync(fd):
        synced.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        return real_fsync(fd)

    def unavailable_context():
        raise AssertionError("an existing record must not need the journal")

    monkeypatch.setattr(os, "fsync", track_sync)
    assert ack.write_ack(
        context().faults[0].key,
        OPERATOR,
        unavailable_context,
        path=stored,
        tty_check=lambda: "/dev/pts/test",
        confirm=lambda *_args: pytest.fail("retry must not prompt"),
    ) == (ACK_ID, False)
    assert synced == ["file", "directory"]
    assert stored.read_bytes() == before


@pytest.mark.parametrize("fault_first", [False, True])
def test_duplicate_message_json_members_preserve_detected_fault(tmp_path, fault_first):
    fault = MCE.partition(" kernel: ")[2]
    messages = [fault, "noise"] if fault_first else ["noise", fault]
    row = json.dumps(entry())
    row = (
        row[:-1]
        + ',"MESSAGE":'
        + json.dumps(messages[0])
        + ',"MESSAGE":'
        + json.dumps(messages[1])
        + "}"
    )
    result = tripwire.check(CFG, runner=FakeRunner([row]), **paths(tmp_path))
    assert result.status == "fail" and "machine_check" in result.detail
    assert "duplicate JSON field" in result.detail
    assert all(fault.key is None for fault in parsed([row]).faults)


@pytest.mark.parametrize("as_bytes", [False, True])
def test_timed_out_journal_retains_partial_fault_output(stored, tmp_path, as_bytes):
    output = json.dumps(entry(MCE.partition(" kernel: ")[2])) + "\n{"

    def timed_out(argv):
        if argv[0] == "journalctl":
            raise subprocess.TimeoutExpired(
                argv, 30, output=output.encode() if as_bytes else output
            )
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    result = tripwire.check(CFG, runner=timed_out, ack_path=stored, **paths(tmp_path))
    assert result.status == "fail" and "machine_check" in result.detail
    assert "no acknowledgments applied" in result.detail


def test_timed_out_journal_retains_cpu_fault_and_machine_check(tmp_path):
    mce = MCE.partition(" kernel: ")[2]
    output = "\n".join(json.dumps(entry(message)) for message in (MESSAGE, mce))

    def timed_out(argv):
        if argv[0] == "journalctl":
            raise subprocess.TimeoutExpired(argv, 30, output=output.encode())
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    result = tripwire.check(CFG, runner=timed_out, **paths(tmp_path))
    assert result.status == "fail"
    assert "timeshift" in result.detail and "machine_check" in result.detail
    assert "timed out" in result.detail


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\u0085"])
def test_unicode_separator_inside_json_message_is_not_a_record_boundary(
    tmp_path, separator
):
    row = json.dumps(entry(MESSAGE + separator + "more context"), ensure_ascii=False)
    result = tripwire.check(CFG, runner=FakeRunner([row]), **paths(tmp_path))
    assert result.status == "fail" and "timeshift" in result.detail
    assert "malformed JSON line" not in result.detail


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
@pytest.mark.parametrize("read_mode", ["complete", "timeout_text", "timeout_bytes"])
def test_unicode_separator_preserves_fault_identity_across_reader_modes(
    separator, read_mode
):
    message = MESSAGE.replace("CPU 13", "CPU 14") + separator + "diagnostic suffix"
    output = "\n\n" + json.dumps(entry(message), ensure_ascii=False) + "\n\n"

    def journal(argv):
        assert argv[0] == "journalctl"
        if read_mode != "complete":
            partial = output.encode() if read_mode == "timeout_bytes" else output
            raise subprocess.TimeoutExpired(argv, 1, output=partial)
        return subprocess.CompletedProcess(argv, 0, output, "")

    result = tripwire.read_kernel_faults(journal)
    assert len(result.faults) == 1
    fault = result.faults[0]
    assert fault.cpu == 14 and fault.kind == "segfault"
    assert fault.message == message.encode()
    assert fault.key.message_sha256 == hashlib.sha256(message.encode()).hexdigest()
    assert result.problems == (
        [] if read_mode == "complete" else ["journalctl timed out"]
    )
    verdict = tripwire.evaluate_signals(
        tripwire.SignalRead(result, [], set(), {4, 5, 8, 9}), ack.AckSet(), None
    )
    assert verdict.status == "fail" and "CPU 14" in verdict.detail


def test_fault_description_escapes_control_characters():
    description = Fault(
        "time\nnext", "segfault", 13, "name\x1b[31m\u2028", 4
    ).describe()
    assert (
        "\n" not in description
        and "\x1b" not in description
        and "\u2028" not in description
    )
    assert (
        "\\u000a" in description
        and "\\u001b" in description
        and "\\u2028" in description
    )


def test_cli_reports_uncertain_commit_without_claiming_refusal(monkeypatch, capsys):
    def uncertain(*_args):
        raise ack.DurabilityUnconfirmed("document replaced; retry the same command")

    monkeypatch.setattr(cli, "revoke_ack", uncertain)
    assert cli.run_revoke(ACK_ID, OPERATOR) == 3
    message = capsys.readouterr().err
    assert "Document was written, but durability is unconfirmed" in message
    assert "Refused" not in message


def test_cli_post_replace_failure_has_distinct_exit_and_applied_ack(monkeypatch):
    import convmem

    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))
    monkeypatch.setattr(ack, "interactive_tty", lambda: "/dev/pts/test")

    def failed_directory_sync(_directory):
        raise OSError("directory fsync failed")

    monkeypatch.setattr(ack, "_sync_directory", failed_directory_sync)
    args = shlex.split(cli._ack_command(signals.journal.faults[0].key))[1:]  # pylint: disable=protected-access
    response = CliRunner().invoke(convmem.app, args, input=ACK_ID[:12] + "\n")
    assert response.exit_code == 3, response.output
    assert "Document was written, but durability is unconfirmed" in response.output
    assert "Refused" not in response.output
    assert ack.load_acks().records[0]["ack_id"] == ACK_ID
    assert tripwire.evaluate_signals(signals, ack.load_acks(), BOOT).status == "warn"


def test_cli_revoke_post_replace_failure_has_distinct_exit_and_effect(monkeypatch):
    import convmem

    write(ack.default_ack_path())
    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))

    def failed_directory_sync(_directory):
        raise OSError("directory fsync failed")

    monkeypatch.setattr(ack, "_sync_directory", failed_directory_sync)
    response = CliRunner().invoke(
        convmem.app,
        ["tripwire", "revoke", ACK_ID[:12], "--by", "ryan", "--reason", "undo"],
    )
    assert response.exit_code == 3, response.output
    assert "Document was written, but durability is unconfirmed" in response.output
    assert "Refused" not in response.output
    assert ack.load_acks().records[0]["revoked_at"] is not None
    assert tripwire.evaluate_signals(signals, ack.load_acks(), BOOT).status == "fail"


@pytest.mark.parametrize("operation", ["ack", "revoke"])
def test_cli_post_replace_cleanup_cannot_mask_uncertain_durability(
    monkeypatch, operation
):
    import convmem

    path = ack.default_ack_path()
    if operation == "revoke":
        write(path)
    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))
    monkeypatch.setattr(ack, "interactive_tty", lambda: "/dev/pts/test")
    real_unlink = Path.unlink

    def read_only_cleanup(target, *args, **kwargs):
        if ".tmp-" in target.name:
            raise OSError("read-only filesystem during cleanup")
        return real_unlink(target, *args, **kwargs)

    def failed_directory_sync(_directory):
        raise OSError("directory fsync failed after replacement")

    monkeypatch.setattr(Path, "unlink", read_only_cleanup)
    monkeypatch.setattr(ack, "_sync_directory", failed_directory_sync)
    args = (
        shlex.split(cli._ack_command(signals.journal.faults[0].key))[1:]  # pylint: disable=protected-access
        if operation == "ack"
        else ["tripwire", "revoke", ACK_ID[:12], "--by", "ryan", "--reason", "undo"]
    )
    response = CliRunner().invoke(convmem.app, args, input=ACK_ID[:12] + "\n")
    assert response.exit_code == 3, response.output
    assert "durability is unconfirmed" in response.output
    assert "Refused" not in response.output
    loaded = ack.load_acks(path)
    assert loaded.problem is None
    assert (loaded.records[0]["revoked_at"] is not None) == (operation == "revoke")


@pytest.mark.parametrize("operation", ["ack", "revoke"])
def test_cli_retry_sync_failure_reports_visible_document_without_new_write(
    monkeypatch, operation
):
    import convmem

    path = ack.default_ack_path()
    write(path)
    if operation == "revoke":
        ack.revoke_ack(ACK_ID[:12], OPERATOR, path=path, now=lambda: NOW)
    before = path.read_bytes()
    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    monkeypatch.setattr(cli, "_snapshot", lambda: (signals, BOOT))
    monkeypatch.setattr(ack, "interactive_tty", lambda: "/dev/pts/test")

    def failed_directory_sync(_directory):
        raise OSError("directory fsync failed")

    def no_replace(*_args):
        raise AssertionError("retry must not replace the document")

    monkeypatch.setattr(ack, "_sync_directory", failed_directory_sync)
    monkeypatch.setattr(os, "replace", no_replace)
    args = (
        shlex.split(cli._ack_command(signals.journal.faults[0].key))[1:]  # pylint: disable=protected-access
        if operation == "ack"
        else ["tripwire", "revoke", ACK_ID[:12], "--by", "ryan", "--reason", "undo"]
    )
    response = CliRunner().invoke(convmem.app, args)
    assert response.exit_code == 3, response.output
    assert (
        "Existing document is visible, but durability is unconfirmed" in response.output
    )
    assert "Document was written" not in response.output
    assert "Refused" not in response.output
    assert path.read_bytes() == before


@pytest.mark.parametrize("operation", ["ack", "revoke"])
def test_cli_committed_write_survives_verdict_refresh_error(monkeypatch, operation):
    import convmem

    path = ack.default_ack_path()
    if operation == "revoke":
        write(path)
    signals = tripwire.SignalRead(parsed(), [], set(), {4, 5, 8, 9})
    reads = 0

    def snapshot():
        nonlocal reads
        reads += 1
        if operation == "ack" and reads == 1:
            return signals, BOOT
        raise RuntimeError("config disappeared after commit")

    monkeypatch.setattr(cli, "_snapshot", snapshot)
    monkeypatch.setattr(ack, "interactive_tty", lambda: "/dev/pts/test")
    args = (
        shlex.split(cli._ack_command(signals.journal.faults[0].key))[1:]  # pylint: disable=protected-access
        if operation == "ack"
        else ["tripwire", "revoke", ACK_ID[:12], "--by", "ryan", "--reason", "undo"]
    )
    response = CliRunner().invoke(
        convmem.app, args, input=ACK_ID[:12] + "\n" if operation == "ack" else None
    )
    assert response.exit_code == 0, response.output
    assert response.exception is None
    assert "Current verdict unavailable" in response.output
    assert "Refused" not in response.output
    loaded = ack.load_acks(path)
    assert loaded.problem is None
    assert (loaded.records[0]["revoked_at"] is not None) == (operation == "revoke")
    assert tripwire.evaluate_signals(signals, loaded, BOOT).status == (
        "fail" if operation == "revoke" else "warn"
    )


@pytest.mark.parametrize("dumps", [[None], [{"pid": 1, "sig": []}], {"pid": 1}])
def test_malformed_coredump_rows_do_not_erase_kernel_failure(tmp_path, dumps):
    result = tripwire.check(
        CFG, runner=FakeRunner([entry()], dumps=dumps), **paths(tmp_path)
    )
    assert result.status == "fail" and "timeshift" in result.detail


@pytest.mark.parametrize("kind", ["segfault", "machine_check"])
def test_unclassifiable_numeric_field_preserves_known_fault_fields(
    stored, tmp_path, kind
):
    huge = "9" * 5000
    malformed = (
        f"p[{huge}]: segfault at 0 likely on CPU 13"
        if kind == "segfault"
        else f"mce: [Hardware Error]: CPU {huge}: Machine Check"
    )
    result = tripwire.check(
        CFG,
        runner=FakeRunner([entry(), entry(malformed)]),
        ack_path=stored,
        **paths(tmp_path),
    )
    assert result.status == "fail" and "timeshift" in result.detail
    assert "unclassifiable" in result.detail
    assert "no acknowledgments applied" in result.detail
    alone = tripwire.check(
        CFG, runner=FakeRunner([entry(malformed)]), **paths(tmp_path)
    )
    assert alone.status == "fail" and kind in alone.detail


def test_journal_oserror_still_checks_online_cpus(tmp_path):
    def denied(argv):
        if argv[0] == "journalctl":
            raise OSError("journal unavailable")
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    result = tripwire.check(CFG, runner=denied, **paths(tmp_path, online="0-23"))
    assert result.status == "fail" and "ONLINE again" in result.detail


@pytest.mark.parametrize("bad_value", [["invalid"], ["8"], [True], "8", None])
def test_invalid_known_bad_config_still_fails_cpu_attributed_fault(tmp_path, bad_value):
    cfg = {"hardware": {"known_bad_cpus": bad_value}}
    result = tripwire.check(cfg, runner=FakeRunner([entry()]), **paths(tmp_path))
    assert result.status == "fail" and "timeshift" in result.detail
    assert "known_bad_cpus" in result.detail


def test_journal_decode_error_still_checks_known_bad_online(tmp_path):
    def undecodable(argv):
        if argv[0] == "journalctl":
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad byte")
        return subprocess.CompletedProcess(argv, 0, "[]", "")

    result = tripwire.check(CFG, runner=undecodable, **paths(tmp_path, online="0-23"))
    assert result.status == "fail" and "ONLINE again" in result.detail
    assert "journalctl failed" in result.detail


def test_coredump_decode_error_retains_kernel_fault(tmp_path):
    def undecodable(argv):
        if argv[0] == "journalctl":
            return subprocess.CompletedProcess(argv, 0, json.dumps(entry()), "")
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad byte")

    result = tripwire.check(CFG, runner=undecodable, **paths(tmp_path))
    assert result.status == "fail" and "timeshift" in result.detail


# ref: ../cpu_tripwire.py, ../cpu_tripwire_ack.py, ../cpu_tripwire_cli.py — hermetic behavior coverage
# src: ../docs/plans/EXECUTION-doctor-fault-acknowledgment.md — T0–T53 and review corrections
