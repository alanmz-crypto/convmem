# pylint: disable=duplicate-code
"""C5 activation transaction, authorization, rollback, and crash recovery."""

from __future__ import annotations

import errno
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from config import (
    atomic_shadow_config_update,
    render_shadow_config_update,
)
from shadow_activation import (
    BASELINE_DERIVATION,
    FIRST_EVENT_TIMEOUT_SECONDS,
    MANIFEST_DERIVATION,
    QUIESCE_TIMEOUT_SECONDS,
    ActivationHooks,
    ActivationRefused,
    ActivationState,
    activate_shadow,
    assert_state_transition,
    recover_prepared_activation,
)
from shadow_authorization import (
    AuthorizationRefused,
    NonceStore,
    canonical_request_hash,
    validate_authorization_token,
)
from shadow_ledger import lexical_abspath

REVISION = "c5-test-revision"
NOW = datetime(2026, 7, 29, 14, 0, tzinfo=timezone.utc)
MOUNTINFO = "1 0 0:1 / / rw,relatime - ext4 /dev/test rw\n"


def _write_private(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    os.chmod(path, 0o600)


def _create_chroma(path: Path) -> None:
    pytest.importorskip("chromadb")
    from chroma_store import ChromaStore

    path.mkdir(parents=True)
    store = ChromaStore(str(path))
    try:
        store.add_unit("u1", "doc-u1", [0.1, 0.2, 0.3], {"kind": "test"})
    finally:
        store.close()


def _config_text(chroma: Path, shadow: Path) -> str:
    return (
        "[index]\n"
        f'chroma_dir = "{chroma}"\n'
        "[models]\n"
        'embed_model = "nomic-embed-text"\n'
        "[shadow_ledger]\n"
        "enabled = false\n"
        f'ledger_path = "{shadow / "ledger.jsonl"}"\n'
        f'activation_manifest_path = "{shadow / "manifest.json"}"\n'
        f'health_path = "{shadow / "health.json"}"\n'
    )


def _fixture(tmp_path: Path, *, activation_id: str = "act-c5-001") -> dict[str, Any]:
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True)
    os.chmod(data_root, 0o755)
    chroma = data_root / "chroma"
    shadow = data_root / "shadow"
    _create_chroma(chroma)
    config_path = tmp_path / "config.toml"
    _write_private(config_path, _config_text(chroma, shadow))
    census_path = tmp_path / "writer-census.json"
    census_path.write_text(
        json.dumps(
            {
                "generated_at_utc": "2026-07-29T13:59:00Z",
                "code_revision": REVISION,
                "protocol_version": 1,
                "systemd_units": ["convmem-watch.service"],
                "cmdline_signatures": ["convmem watch"],
                "chroma_dir": str(chroma),
                "open_fd_writer_pids": [],
            }
        ),
        encoding="utf-8",
    )
    nonce_store = shadow / "authorization-nonces.jsonl"
    writer_lock = tmp_path / "locks" / "writer.lock"
    auth_dir = tmp_path / "authorizations"
    auth_dir.mkdir()
    os.chmod(auth_dir, 0o700)
    token_path = auth_dir / "activate.json"
    target_config = {
        "activation_id": activation_id,
        "activation_manifest_path": str(shadow / "manifest.json"),
        "enabled": True,
        "health_path": str(shadow / "health.json"),
        "ledger_path": str(shadow / "ledger.jsonl"),
        "manifest_sha256": {"derive": MANIFEST_DERIVATION},
    }
    token = {
        "token_version": 1,
        "operation": "shadow_activate",
        "activation_id": activation_id,
        "nonce": "nonce-activation-0001",
        "issued_at_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at_utc": (NOW + timedelta(seconds=3600)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "code_revision": REVISION,
        "config_path": str(lexical_abspath(config_path)),
        "shadow_dir": str(lexical_abspath(shadow)),
        "ledger_path": str(lexical_abspath(shadow / "ledger.jsonl")),
        "manifest_path": str(lexical_abspath(shadow / "manifest.json")),
        "health_path": str(lexical_abspath(shadow / "health.json")),
        "first_event_timeout_seconds": FIRST_EVENT_TIMEOUT_SECONDS,
        "quiesce_timeout_seconds": QUIESCE_TIMEOUT_SECONDS,
        "allowed_filesystems": ["btrfs", "ext4", "tmpfs", "xfs"],
        "baseline_derivation": BASELINE_DERIVATION,
        "manifest_derivation": MANIFEST_DERIVATION,
        "target_config": target_config,
        "nonce_store_path": str(lexical_abspath(nonce_store)),
        "writer_lock_path": str(lexical_abspath(writer_lock)),
        "census_path": str(lexical_abspath(census_path)),
    }
    token["request_hash"] = canonical_request_hash(token)
    _write_private(token_path, json.dumps(token, indent=2, sort_keys=True) + "\n")
    return {
        "activation_id": activation_id,
        "attest_dir": tmp_path / "attestations",
        "chroma": chroma,
        "config": config_path,
        "census": census_path,
        "health": shadow / "health.json",
        "journal": shadow / f"activation-{activation_id}.journal.json",
        "ledger": shadow / "ledger.jsonl",
        "manifest": shadow / "manifest.json",
        "nonce_store": nonce_store,
        "shadow": shadow,
        "token": token_path,
        "token_payload": token,
        "writer_lock": writer_lock,
    }


def _hooks(**changes: Any) -> ActivationHooks:
    values: dict[str, Any] = {
        "now": lambda: NOW,
        "revision": lambda: REVISION,
        "service_state": lambda _unit: "inactive",
        "process_pids": lambda _census, _chroma: [],
        "mountinfo": lambda: MOUNTINFO,
    }
    values.update(changes)
    return ActivationHooks(**values)


def _activate(fixture: dict[str, Any], hooks: ActivationHooks):
    return activate_shadow(
        token_path=fixture["token"],
        config_path=fixture["config"],
        census_path=fixture["census"],
        nonce_store_path=fixture["nonce_store"],
        writer_lock_path=fixture["writer_lock"],
        attest_dir=fixture["attest_dir"],
        hooks=hooks,
    )


def _append_first_event(fixture: dict[str, Any]) -> None:
    from shadow_sink import JsonlUnitMutationSink

    sink = JsonlUnitMutationSink(
        ledger_path=fixture["ledger"], health_path=fixture["health"]
    )
    sink.observe(
        event_id="event-first",
        operation="replace",
        stable_entity_id="u1",
        document="doc-u1",
        metadata={"kind": "test"},
        deleted=False,
        writer_route="test.first-event",
    )


def test_transition_table_rejects_state_skips() -> None:
    assert_state_transition("disabled", "preparing")
    assert_state_transition("committed", "first_event_observed")
    assert_state_transition("committed", "rollback_pending")
    with pytest.raises(ActivationRefused, match="invalid activation transition"):
        assert_state_transition("preparing", "committed")
    with pytest.raises(ActivationRefused, match="unknown activation state"):
        assert_state_transition("bogus", "committed")


def test_cli_activation_defaults_to_authorization_refusal() -> None:
    from typer.testing import CliRunner

    from convmem import app

    result = CliRunner().invoke(app, ["shadow-activate"])
    assert result.exit_code == 2
    payload = json.loads(result.stdout)
    assert payload == {
        "committed": False,
        "refusal_code": "authorization_missing",
        "state": "disabled",
    }


def test_token_requires_exact_private_mode_and_self_hash(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    store = NonceStore(fixture["nonce_store"])
    expected = {
        key: fixture["token_payload"][key]
        for key in (
            "activation_id",
            "code_revision",
            "config_path",
            "nonce_store_path",
        )
    }
    validated = validate_authorization_token(
        fixture["token"], expected=expected, nonce_store=store, now=NOW
    )
    assert validated.activation_id == fixture["activation_id"]

    os.chmod(fixture["token"], 0o644)
    with pytest.raises(AuthorizationRefused, match="mode must be 0600"):
        validate_authorization_token(
            fixture["token"], expected=expected, nonce_store=store, now=NOW
        )


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda token: token.update(request_hash="0" * 64), "authorization_mismatch"),
        (
            lambda token: token.update(
                issued_at_utc=(NOW - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                expires_at_utc=(NOW - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            ),
            "authorization_expired",
        ),
        (
            lambda token: token.update(
                issued_at_utc=(NOW + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                expires_at_utc=(NOW + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            "authorization_mismatch",
        ),
    ],
)
def test_token_refusal_matrix(tmp_path: Path, mutation, code: str) -> None:
    fixture = _fixture(tmp_path)
    token = dict(fixture["token_payload"])
    mutation(token)
    if code != "authorization_mismatch" or token.get("request_hash") != "0" * 64:
        token["request_hash"] = canonical_request_hash(token)
    _write_private(fixture["token"], json.dumps(token) + "\n")
    with pytest.raises(AuthorizationRefused) as raised:
        validate_authorization_token(
            fixture["token"], expected={}, nonce_store=NonceStore(fixture["nonce_store"]), now=NOW
        )
    assert raised.value.code == code


def test_nonce_consumption_is_durable_and_one_shot(tmp_path: Path) -> None:
    parent = tmp_path / "shadow"
    parent.mkdir()
    os.chmod(parent, 0o700)
    store = NonceStore(parent / "nonces.jsonl")
    store.consume(nonce="nonce-activation-0001", activation_id="act", token_sha256="a" * 64)
    assert store.contains("nonce-activation-0001")
    assert stat_mode(parent / "nonces.jsonl") == 0o600
    with pytest.raises(AuthorizationRefused) as raised:
        store.consume(
            nonce="nonce-activation-0001", activation_id="act", token_sha256="a" * 64
        )
    assert raised.value.code == "authorization_reused"


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_nonce_short_write_failure_fails_closed(tmp_path: Path) -> None:
    parent = tmp_path / "shadow"
    parent.mkdir()
    os.chmod(parent, 0o700)
    store = NonceStore(parent / "nonces.jsonl", write=lambda _fd, _data: 0)
    with pytest.raises(OSError, match="short write"):
        store.consume(nonce="nonce-activation-0001", activation_id="act", token_sha256="b" * 64)


@pytest.mark.parametrize("mask", [0o000, 0o022, 0o077])
def test_activation_private_artifacts_are_umask_independent(tmp_path: Path, mask: int) -> None:
    fixture = _fixture(tmp_path)
    old_mask = os.umask(mask)
    try:
        ticks = iter([0.0, 301.0])
        _activate(fixture, _hooks(monotonic=lambda: next(ticks)))
    finally:
        os.umask(old_mask)
    assert stat_mode(fixture["shadow"]) == 0o700
    for path in (
        fixture["ledger"],
        fixture["manifest"],
        fixture["journal"],
        fixture["nonce_store"],
    ):
        assert stat_mode(path) == 0o600


def test_config_render_changes_only_shadow_table(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    before = fixture["config"].read_bytes()
    candidate = render_shadow_config_update(
        before,
        replacements={"enabled": True, "activation_id": "act"},
        expected_enabled=False,
    )
    assert candidate.parsed["shadow_ledger"]["enabled"] is True
    assert candidate.parsed["index"]["chroma_dir"] == str(fixture["chroma"])
    assert candidate.data.split(b"[shadow_ledger]", 1)[0] == before.split(
        b"[shadow_ledger]", 1
    )[0]


def test_config_commit_refuses_unsupported_and_cross_device(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    before = fixture["config"].read_bytes()
    digest = __import__("hashlib").sha256(before).hexdigest()
    with pytest.raises(RuntimeError) as unsupported:
        atomic_shadow_config_update(
            fixture["config"],
            expected_preimage_sha256=digest,
            replacements={"enabled": True},
            expected_enabled=False,
            mountinfo_text="1 0 0:1 / / rw - nfs server:/x rw\n",
        )
    assert unsupported.value.code == "config_filesystem_unsupported"

    def exdev(*_args, **_kwargs):
        raise OSError(errno.EXDEV, "cross device")

    with pytest.raises(RuntimeError) as cross:
        atomic_shadow_config_update(
            fixture["config"],
            expected_preimage_sha256=digest,
            replacements={"enabled": True},
            expected_enabled=False,
            mountinfo_text=MOUNTINFO,
            replace=exdev,
        )
    assert cross.value.code == "config_cross_device"
    assert fixture["config"].read_bytes() == before


def test_config_fsync_failures_classify_pre_and_post_commit(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    before = fixture["config"].read_bytes()
    digest = __import__("hashlib").sha256(before).hexdigest()

    def fail_first(_fd: int) -> None:
        raise OSError("temp fsync failed")

    with pytest.raises(OSError, match="temp fsync failed"):
        atomic_shadow_config_update(
            fixture["config"],
            expected_preimage_sha256=digest,
            replacements={"enabled": True},
            expected_enabled=False,
            mountinfo_text=MOUNTINFO,
            fsync=fail_first,
        )
    assert fixture["config"].read_bytes() == before

    calls = {"count": 0}

    def fail_parent(_fd: int) -> None:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("parent fsync failed")

    with pytest.raises(RuntimeError) as uncertain:
        atomic_shadow_config_update(
            fixture["config"],
            expected_preimage_sha256=digest,
            replacements={"enabled": True},
            expected_enabled=False,
            mountinfo_text=MOUNTINFO,
            fsync=fail_parent,
        )
    assert uncertain.value.committed is True
    assert __import__("config").load_config(fixture["config"])["shadow_ledger"]["enabled"] is True


def test_activation_commits_config_last_then_observes_first_event(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    appended = {"done": False}

    def sleep_after_release(_seconds: float) -> None:
        if not appended["done"]:
            appended["done"] = True
            _append_first_event(fixture)

    outcome = _activate(fixture, _hooks(sleep=sleep_after_release))
    assert outcome.state == "first_event_observed"
    assert outcome.committed is True
    cfg = __import__("config").load_config(fixture["config"])
    assert cfg["shadow_ledger"]["enabled"] is True
    assert cfg["shadow_ledger"]["activation_id"] == fixture["activation_id"]
    assert fixture["ledger"].is_file() and fixture["manifest"].is_file()
    assert stat_mode(fixture["ledger"]) == stat_mode(fixture["manifest"]) == 0o600
    assert stat_mode(fixture["shadow"]) == 0o700
    assert NonceStore(fixture["nonce_store"]).contains("nonce-activation-0001")
    journal = json.loads(fixture["journal"].read_text(encoding="utf-8"))
    assert journal["state"] == "first_event_observed"


def test_first_event_timeout_atomically_disables_and_retains_evidence(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    ticks = iter([0.0, 301.0])
    outcome = _activate(fixture, _hooks(monotonic=lambda: next(ticks)))
    assert outcome.state == "disabled_after_rollback"
    assert outcome.refusal_code == "first_event_timeout"
    cfg = __import__("config").load_config(fixture["config"])
    assert cfg["shadow_ledger"]["enabled"] is False
    assert fixture["ledger"].is_file() and fixture["manifest"].is_file()
    journal = json.loads(fixture["journal"].read_text(encoding="utf-8"))
    assert journal["state"] == "disabled_after_rollback"


def test_first_event_mismatch_rolls_back(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    appended = {"done": False}

    def append_wrong(_seconds: float) -> None:
        if appended["done"]:
            return
        appended["done"] = True
        from shadow_sink import JsonlUnitMutationSink

        JsonlUnitMutationSink(
            ledger_path=fixture["ledger"], health_path=fixture["health"]
        ).observe(
            event_id="event-wrong",
            operation="replace",
            stable_entity_id="u1",
            document="not-the-chroma-document",
            metadata={"kind": "test"},
            deleted=False,
            writer_route="test.mismatch",
        )

    outcome = _activate(fixture, _hooks(sleep=append_wrong))
    assert outcome.refusal_code == "first_event_mismatch"
    assert outcome.state == "disabled_after_rollback"
    assert __import__("config").load_config(fixture["config"])["shadow_ledger"]["enabled"] is False


def test_census_revision_and_service_state_refuse_before_artifacts(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    census = json.loads(fixture["census"].read_text(encoding="utf-8"))
    census["code_revision"] = "old"
    fixture["census"].write_text(json.dumps(census), encoding="utf-8")
    with pytest.raises(ActivationRefused) as stale:
        _activate(fixture, _hooks())
    assert stale.value.code == "census_stale"
    assert not fixture["shadow"].exists()

    fixture = _fixture(tmp_path / "active")
    with pytest.raises(ActivationRefused) as active:
        _activate(fixture, _hooks(service_state=lambda _unit: "active"))
    assert active.value.code == "writer_quiesce_timeout"
    assert not fixture["shadow"].exists()


def test_unattested_writer_pid_refuses_as_legacy(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    with pytest.raises(ActivationRefused) as legacy:
        _activate(
            fixture,
            _hooks(process_pids=lambda _census, _chroma: [99999999]),
        )
    assert legacy.value.code == "legacy_writer_process"
    assert not fixture["shadow"].exists()


class InjectedCrash(BaseException):
    pass


@pytest.mark.parametrize(
    "crash_point,committed",
    [
        ("preparing", False),
        ("quiesced", False),
        ("baseline_captured", False),
        ("artifacts_validated", False),
        ("ledger_installed", False),
        ("manifest_installed", False),
        ("nonce_consumed", False),
        ("committed", True),
    ],
)
def test_crash_matrix_has_unambiguous_config_commit(
    tmp_path: Path, crash_point: str, committed: bool
) -> None:
    fixture = _fixture(tmp_path)

    def checkpoint(name: str) -> None:
        if name == crash_point:
            raise InjectedCrash()

    with pytest.raises(InjectedCrash):
        _activate(fixture, _hooks(checkpoint=checkpoint))
    enabled = __import__("config").load_config(fixture["config"])["shadow_ledger"]["enabled"]
    assert enabled is committed
    journal = json.loads(fixture["journal"].read_text(encoding="utf-8"))
    if committed:
        assert journal["state"] == "committed"
        assert journal["committed"] is True
    else:
        assert journal["committed"] is False


def test_token_change_under_gate_is_refused_before_nonce_consumption(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    changed = {"done": False}

    def checkpoint(name: str) -> None:
        if name != "manifest_installed" or changed["done"]:
            return
        changed["done"] = True
        token = dict(fixture["token_payload"])
        token["nonce"] = "nonce-activation-CHANGED"
        token["request_hash"] = canonical_request_hash(token)
        _write_private(fixture["token"], json.dumps(token) + "\n")

    with pytest.raises(ActivationRefused) as refused:
        _activate(fixture, _hooks(checkpoint=checkpoint))
    assert refused.value.code == "authorization_mismatch"
    assert not fixture["nonce_store"].exists()
    assert not fixture["ledger"].exists() and not fixture["manifest"].exists()


def test_crash_after_nonce_before_config_requires_scoped_recovery(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def checkpoint(name: str) -> None:
        if name == "nonce_consumed":
            raise InjectedCrash()

    with pytest.raises(InjectedCrash):
        _activate(fixture, _hooks(checkpoint=checkpoint))
    cfg = __import__("config").load_config(fixture["config"])
    assert cfg["shadow_ledger"]["enabled"] is False
    assert fixture["ledger"].exists() and fixture["manifest"].exists()
    journal = json.loads(fixture["journal"].read_text(encoding="utf-8"))
    journal["owner_pid"] = 99999999
    journal["owner_start_time"] = "dead"
    _write_private(fixture["journal"], json.dumps(journal, indent=2) + "\n")
    outcome = recover_prepared_activation(
        journal_path=fixture["journal"],
        config_path=fixture["config"],
        activation_id=fixture["activation_id"],
        writer_lock_path=fixture["writer_lock"],
    )
    assert outcome.state == "aborted_precommit"
    assert not fixture["ledger"].exists() and not fixture["manifest"].exists()
    assert NonceStore(fixture["nonce_store"]).contains("nonce-activation-0001")


def test_recovery_refuses_replaced_artifact_inode(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)

    def checkpoint(name: str) -> None:
        if name == "nonce_consumed":
            raise InjectedCrash()

    with pytest.raises(InjectedCrash):
        _activate(fixture, _hooks(checkpoint=checkpoint))
    journal = json.loads(fixture["journal"].read_text(encoding="utf-8"))
    journal["owner_pid"] = 99999999
    journal["owner_start_time"] = "dead"
    _write_private(fixture["journal"], json.dumps(journal, indent=2) + "\n")
    fixture["ledger"].unlink()
    _write_private(fixture["ledger"], "replacement\n")
    replacement_inode = fixture["ledger"].stat().st_ino
    with pytest.raises(ActivationRefused) as refused:
        recover_prepared_activation(
            journal_path=fixture["journal"],
            config_path=fixture["config"],
            activation_id=fixture["activation_id"],
            writer_lock_path=fixture["writer_lock"],
        )
    assert refused.value.code == "prepared_not_committed"
    assert fixture["ledger"].stat().st_ino == replacement_inode


def test_precommit_failure_cleans_only_recorded_artifacts(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    sentinel = tmp_path / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")

    def checkpoint(name: str) -> None:
        if name == "artifacts_validated":
            raise RuntimeError("fault")

    with pytest.raises(RuntimeError, match="fault"):
        _activate(fixture, _hooks(checkpoint=checkpoint))
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert not fixture["ledger"].exists() and not fixture["manifest"].exists()
    journal = json.loads(fixture["journal"].read_text(encoding="utf-8"))
    assert journal["state"] == ActivationState.ABORTED_PRECOMMIT.value


def test_token_reuse_refuses_before_new_preparation(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    ticks = iter([0.0, 301.0])
    _activate(fixture, _hooks(monotonic=lambda: next(ticks)))
    with pytest.raises(ActivationRefused) as reused:
        _activate(fixture, _hooks())
    assert reused.value.code == "authorization_reused"
