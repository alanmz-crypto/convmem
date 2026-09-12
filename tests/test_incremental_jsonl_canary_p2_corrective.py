"""Hermetic P2 corrective tests for the JSONL production canary."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from chroma_write_store import current_code_revision
from incremental_jsonl_canary import (
    FAULT_SELECTORS,
    CanaryRefused,
    ProductionCanaryBoundary,
    bind_p2_append_source,
    decode_grant,
    derive_p2_disposition,
    freeze_p2_evidence,
    gate0_preflight_p2,
    is_p2_grant,
    prove_cli_watcher_unreachable,
    run_p2_append_adoption,
    run_p2_fault_observation,
    run_p2_initial_adoption,
    run_p2_orchestration,
    validate_grant,
    validate_p2_grant,
)
from tests.incremental_jsonl_canary_helpers import (
    append_kiro_source,
    build_grant,
    build_p2_fixture,
    build_p2_grant,
    grant_payload_with_resource_path,
    hermetic_root,
    p2_gate0_hooks_pass,
    write_grant_file,
    write_kiro_source,
)
from tests.test_incremental_jsonl_canary_baseline import BASELINE_HASHES
from tests.incremental_jsonl_helpers import install_fakes


@pytest.fixture(autouse=True)
def _fake_providers(monkeypatch):
    install_fakes(monkeypatch)



def test_p2_c1_p1_still_denies_production_paths(tmp_path: Path, monkeypatch) -> None:
    blocked = tmp_path / "prod-root"
    blocked.mkdir()
    share = blocked / "share/convmem"
    share.mkdir(parents=True)
    monkeypatch.setattr(
        "incremental_jsonl_canary.known_production_roots",
        lambda **kwargs: (blocked,),
    )
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, _digest = build_grant(root, source_grant)
    payload = grant.to_payload()
    for resource in payload["resources"]:
        if resource["role"] == "processed":
            resource["path"] = str(share / "processed.json")
    path = root / "prod-grant.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    loaded = decode_grant(path)
    bad_digest = __import__("hashlib").sha256(loaded.digest_payload()).hexdigest()
    with pytest.raises(CanaryRefused, match="canary_grant_production_path"):
        validate_grant(loaded, expected_sha256=bad_digest, code_revision=loaded.code_revision)
    with pytest.raises(CanaryRefused, match="canary_boundary_production"):
        ProductionCanaryBoundary.from_grant(loaded, root=root)


def test_p2_c2_positive_mode_binds_exact_resources(tmp_path: Path) -> None:
    fx = build_p2_fixture(tmp_path)
    assert is_p2_grant(fx["grant"])
    validate_p2_grant(
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
    )
    bad = fx["grant"].to_payload()
    bad["resources"].append({"role": "chroma", "path": str(fx["root"] / "extra-chroma")})
    path = fx["root"] / "bad-extra.json"
    path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    with pytest.raises(CanaryRefused):
        decode_grant(path)


def test_p2_c3_empty_override_cannot_disable_p1_denial(tmp_path: Path, monkeypatch) -> None:
    blocked = tmp_path / "prod-root"
    blocked.mkdir()
    share = blocked / "share/convmem"
    share.mkdir(parents=True)
    monkeypatch.setattr(
        "incremental_jsonl_canary.known_production_roots",
        lambda **kwargs: (blocked,),
    )
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    payload = grant_payload_with_resource_path(
        root,
        source_grant,
        role="processed",
        path_value=str(share / "processed.json"),
        build_fn=build_p2_grant,
    )
    path = root / "p2-prod-grant.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    loaded = decode_grant(path)
    with pytest.raises(CanaryRefused, match="canary_boundary_production"):
        ProductionCanaryBoundary.from_grant(loaded, root=root, forbidden_roots=())


def test_p2_c4_full_gate0_passes_with_stubs(tmp_path: Path) -> None:
    fx = build_p2_fixture(tmp_path)
    report = gate0_preflight_p2(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=p2_gate0_hooks_pass(),
    )
    assert report["mode"] == "p2-exact-resource-v1"
    assert len(report["checks"]) == 12


@pytest.mark.parametrize(
    ("check_id", "error_code", "mutator"),
    [
        ("1_grant", "canary_grant_digest", lambda fx: {"expected_sha256": "0" * 64}),
        ("2_baseline", "canary_gate0_baseline", lambda fx: {"tamper_source_byte": True}),
        ("3_source", "canary_gate0_source", lambda fx: {"missing_metadata_path": True}),
        ("4_zero_adoption", "canary_gate0_adoption", lambda fx: {"zero_adoption": False}),
        ("5_persistent_config", "canary_gate0_config", lambda fx: {"bad_persistent_config": True}),
        ("6_watcher", "canary_gate0_watcher", lambda fx: {"watcher": False}),
        ("7_writer", "canary_gate0_writer", lambda fx: {"writer": False}),
        ("8_paths", "canary_gate0_paths", lambda fx: {"resource_symlink": True}),
        ("9_models", "canary_gate0_models", lambda fx: {"models": False}),
        ("10_network", "canary_gate0_network", lambda fx: {"network": False}),
        ("11_capsule", "canary_gate0_capsule", lambda fx: {"bad_capsule": True}),
        ("12_restic", "canary_gate0_restic", lambda fx: {"restic": False}),
    ],
)
def test_p2_gate0_checks_fail_closed_individually(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    check_id: str,
    error_code: str,
    mutator,
) -> None:
    fx = build_p2_fixture(tmp_path)
    hooks = p2_gate0_hooks_pass()
    kwargs = {
        "expected_sha256": fx["digest"],
        "code_revision": current_code_revision(),
        "hooks": hooks,
    }
    flags = mutator(fx)
    if "expected_sha256" in flags:
        kwargs["expected_sha256"] = flags["expected_sha256"]
    if flags.get("tamper_source_byte"):
        data = bytearray(fx["source"].read_bytes())
        data[-2] ^= 0x01
        fx["source"].write_bytes(bytes(data))
    if flags.get("missing_metadata_path"):
        monkeypatch.setattr(
            "incremental_jsonl_canary._gate0_source_binding",
            lambda _grant: {"accepted_messages": 61},
        )
        payload = fx["grant"].to_payload()
        payload["source"]["metadata_path"] = str(fx["root"] / "missing-session.json")
        bad = fx["root"] / "gate0-missing-metadata.json"
        bad.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.chmod(bad, 0o600)
        loaded = decode_grant(bad)
        fx = dict(fx)
        fx["grant"] = loaded
        kwargs["expected_sha256"] = hashlib.sha256(loaded.digest_payload()).hexdigest()
    if flags.get("zero_adoption") is False:
        hooks.zero_adoption = lambda _b, _g: {"pass": "false"}
    if flags.get("bad_persistent_config"):
        cfg = fx["boundary"].layout["home"] / ".config" / "convmem" / "config.toml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("[index]\n[index.incremental_jsonl]\nenabled = true\n", encoding="utf-8")
    if flags.get("watcher") is False:
        hooks.watcher_probe = lambda: {"pass": "false"}
    if flags.get("writer") is False:
        hooks.writer_census = lambda _b: {"pass": "false"}
    if flags.get("resource_symlink"):
        target = Path(fx["grant"].resources[0].path)
        link = target.parent / "escape-link"
        link.symlink_to(target)
        payload = fx["grant"].to_payload()
        payload["resources"][0] = {"role": payload["resources"][0]["role"], "path": str(link)}
        bad = fx["root"] / f"gate0-{check_id}.json"
        bad.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.chmod(bad, 0o600)
        loaded = decode_grant(bad)
        fx = dict(fx)
        fx["grant"] = loaded
        kwargs["expected_sha256"] = hashlib.sha256(loaded.digest_payload()).hexdigest()
    if flags.get("models") is False:
        hooks.model_manifest = lambda _g: {"pass": "false"}
    if flags.get("network") is False:
        hooks.network_self_test = lambda: {"pass": "false"}
    if flags.get("bad_capsule"):
        capsule = Path(fx["grant"].rollback.capsule_path)
        capsule.parent.mkdir(parents=True, exist_ok=True)
        capsule.write_text('{"version": 1}', encoding="utf-8")
        os.chmod(capsule, 0o600)
        payload = fx["grant"].to_payload()
        payload["rollback"]["expected_digest"] = "1" * 64
        bad = fx["root"] / "gate0-bad-capsule.json"
        bad.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.chmod(bad, 0o600)
        loaded = decode_grant(bad)
        fx = dict(fx)
        fx["grant"] = loaded
        kwargs["expected_sha256"] = hashlib.sha256(loaded.digest_payload()).hexdigest()
    if flags.get("restic") is False:
        hooks.restic_identifier = lambda: {"pass": "false"}
    with pytest.raises(CanaryRefused, match=error_code):
        gate0_preflight_p2(fx["grant"], fx["boundary"], **kwargs)


def test_p2_c5_launcher_refuses_p1_mutation(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant, code_revision=current_code_revision())
    grant_path = write_grant_file(root, grant)
    digest = hashlib.sha256(decode_grant(grant_path).digest_payload()).hexdigest()
    cmd = [
        sys.executable,
        "scripts/run-jsonl-production-canary.py",
        "--grant",
        str(grant_path),
        "--grant-sha256",
        digest,
        "--stage",
        "p2-t3",
    ]
    repo_root = str(Path(__file__).resolve().parents[1])
    result = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "canary_p2_unauthorized" in result.stderr


def test_p2_c6_initial_adoption_two_chunk_replay(tmp_path: Path) -> None:
    fx = build_p2_fixture(tmp_path)
    gate0_preflight_p2(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=p2_gate0_hooks_pass(),
    )
    payload = run_p2_initial_adoption(fx["boundary"], fx["grant"], expected_sha256=fx["digest"])
    assert payload["stage"] == "p2-t3"
    assert payload["replay_counters"]["summarize"] == 0


def test_p2_c7_append_reuses_chunk_zero(tmp_path: Path) -> None:
    fx = build_p2_fixture(tmp_path)
    gate0_preflight_p2(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=p2_gate0_hooks_pass(),
    )
    run_p2_initial_adoption(fx["boundary"], fx["grant"], expected_sha256=fx["digest"])
    updated = append_kiro_source(fx["source"], 61, 49)
    grant = bind_p2_append_source(fx["grant"], updated)
    payload = run_p2_append_adoption(fx["boundary"], grant, expected_sha256=fx["digest"])
    assert payload["stage"] == "p2-t4"
    assert payload["accepted_messages"] == 110


@pytest.mark.parametrize("selector", tuple(FAULT_SELECTORS))
def test_p2_c8_fault_selectors_restore_on_two_chunk_source(tmp_path: Path, selector: str) -> None:
    fx = build_p2_fixture(tmp_path, messages=61)
    payload = run_p2_fault_observation(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        fault_selector=selector,
    )
    assert payload["stage"] == "p2-t5"
    assert payload["disposition"] == "restored"


def test_p2_c9_evidence_freeze(tmp_path: Path) -> None:
    fx = build_p2_fixture(tmp_path)
    report = gate0_preflight_p2(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=p2_gate0_hooks_pass(),
    )
    digest = freeze_p2_evidence(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        gate0_report=report,
        sections={"t3": {"ok": True}},
        disposition="converged",
    )
    evidence = Path(fx["grant"].evidence_dir) / "p2-hermetic-evidence.json"
    assert evidence.is_file()
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["hermetic"] is True
    assert digest


def test_p2_c10_baseline_hashes_and_routes_unchanged() -> None:
    report = prove_cli_watcher_unreachable()
    assert report["canary_launcher_registered"] == "no"
    root = Path(__file__).resolve().parents[1]
    for name, expected in BASELINE_HASHES.items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        assert actual == expected, name


def test_p2_c11_unrelated_sentinels_unchanged(tmp_path: Path, monkeypatch) -> None:
    from incremental_jsonl import IncrementalJsonlCoordinator
    from incremental_jsonl_canary import unrelated_sentinel_digest
    from tests.incremental_jsonl_helpers import apply_env, enable_incremental, isolated_env, write_source

    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    enable_incremental(boundary)
    primary = write_source(boundary.root, 2, name="primary")
    sentinel = write_source(boundary.root, 1, name="sentinel")
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True).run()
    IncrementalJsonlCoordinator.from_isolated_boundary(boundary, sentinel, enabled=True).run()
    coord = IncrementalJsonlCoordinator.from_isolated_boundary(boundary, primary, enabled=True)
    with coord._session() as session:  # pylint: disable=protected-access
        before = unrelated_sentinel_digest(session.store, [str(sentinel)])
    coord.run()
    with coord._session() as session:  # pylint: disable=protected-access
        after = unrelated_sentinel_digest(session.store, [str(sentinel)])
    assert before == after



def test_p2_orchestration_runs_t3_t4_t5_t6_in_order(tmp_path: Path) -> None:
    fx = build_p2_fixture(tmp_path)
    payload = run_p2_orchestration(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=p2_gate0_hooks_pass(),
        include_faults=True,
    )
    sections = payload["sections"]
    assert sections["t3"]["stage"] == "p2-t3"
    assert sections["t4"]["stage"] == "p2-t4"
    assert set(sections["t5"]) == set(FAULT_SELECTORS)
    assert sections["t6"]["disposition"] == payload["disposition"]
    assert payload["disposition"] == "restored"
    assert derive_p2_disposition(sections) == "restored"
    evidence = Path(fx["grant"].evidence_dir) / "p2-hermetic-evidence.json"
    assert evidence.is_file()
    frozen = json.loads(evidence.read_text(encoding="utf-8"))
    assert frozen["hermetic"] is True
    assert frozen["sections"]["disposition"] == "restored"


def test_p2_derive_disposition_converged_without_faults() -> None:
    sections = {
        "t3": {"stage": "p2-t3", "outcome": "committed"},
        "t4": {"stage": "p2-t4"},
    }
    assert derive_p2_disposition(sections) == "converged"


def test_p2_c12_nonce_receipt_one_run(tmp_path: Path) -> None:
    from incremental_jsonl_canary import assert_not_reused, consume_nonce, nonce_receipt_path

    fx = build_p2_fixture(tmp_path)
    consume_nonce(fx["root"], fx["grant"], expected_sha256=fx["digest"])
    receipt_path = nonce_receipt_path(fx["root"])
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["stage"] = "completed"
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CanaryRefused):
        assert_not_reused(fx["root"], fx["grant"])
