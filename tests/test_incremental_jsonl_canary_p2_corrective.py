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
    CanaryRefused,
    ProductionCanaryBoundary,
    bind_p2_append_source,
    decode_grant,
    freeze_p2_evidence,
    gate0_preflight_p2,
    is_p2_grant,
    prove_cli_watcher_unreachable,
    run_p2_append_adoption,
    run_p2_fault_observation,
    run_p2_initial_adoption,
    validate_grant,
    validate_p2_grant,
    write_canary_overlay,
)
from incremental_jsonl_isolation import known_production_roots
BASELINE_HASHES = {
    "watch.py": "b72fd6380d48bf4256371f4b3f4f8eda03f2ca7f1dd9c107f4d6db60c05da2e2",
    "ingest.py": "03246a6c104ad9bb6d9c4df9ab9d34bac165080c725ed1545b64aef8f76f6d23",
    "incremental_jsonl.py": "e51509c2423db2f2ef5ca414457332aa37d945747b9f7ef8e73a9eb6705db12d",
    "incremental_jsonl_isolation.py": "818325221d46b1501795895b82d2465151b12ab76f0f11f21f42d8438c0a6df1",
}
from tests.incremental_jsonl_canary_helpers import (
    append_kiro_source,
    build_grant,
    build_p2_grant,
    hermetic_root,
    p2_gate0_hooks_pass,
    write_grant_file,
    write_kiro_source,
)
from tests.incremental_jsonl_helpers import install_fakes


@pytest.fixture(autouse=True)
def _fake_providers(monkeypatch):
    install_fakes(monkeypatch)


def _p2_fixture(tmp_path: Path, *, messages: int = 61):
    root = hermetic_root(tmp_path)
    source, source_grant = write_kiro_source(root, messages)
    grant, digest = build_p2_grant(root, source_grant, code_revision=current_code_revision())
    grant_path = root / "p2-grant.json"
    boundary = ProductionCanaryBoundary.from_p2_grant(grant, root=root)
    write_canary_overlay(boundary)
    return {
        "root": root,
        "source": source,
        "grant": grant,
        "digest": digest,
        "grant_path": grant_path,
        "boundary": boundary,
    }


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
    grant, digest = build_grant(root, source_grant)
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
    fx = _p2_fixture(tmp_path)
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
    grant, _digest = build_p2_grant(root, source_grant)
    payload = grant.to_payload()
    for resource in payload["resources"]:
        if resource["role"] == "processed":
            resource["path"] = str(share / "processed.json")
    path = root / "p2-prod-grant.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    loaded = decode_grant(path)
    with pytest.raises(CanaryRefused, match="canary_boundary_production"):
        ProductionCanaryBoundary.from_grant(loaded, root=root, forbidden_roots=())


def test_p2_c4_full_gate0_passes_with_stubs(tmp_path: Path) -> None:
    fx = _p2_fixture(tmp_path)
    report = gate0_preflight_p2(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=p2_gate0_hooks_pass(),
    )
    assert report["mode"] == "p2-exact-resource-v1"
    assert len(report["checks"]) == 12
    hooks = p2_gate0_hooks_pass()
    bad = p2_gate0_hooks_pass()
    bad.watcher_probe = lambda: {"pass": "false"}
    with pytest.raises(CanaryRefused, match="canary_gate0_watcher"):
        gate0_preflight_p2(
            fx["grant"],
            fx["boundary"],
            expected_sha256=fx["digest"],
            code_revision=current_code_revision(),
            hooks=bad,
        )


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
    result = subprocess.run(cmd, cwd=str(Path(__file__).resolve().parents[1]), capture_output=True, text=True)
    assert result.returncode == 2
    assert "canary_p2_unauthorized" in result.stderr


def test_p2_c6_initial_adoption_two_chunk_replay(tmp_path: Path) -> None:
    fx = _p2_fixture(tmp_path)
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
    fx = _p2_fixture(tmp_path)
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


def test_p2_c8_fault_selector_restores(tmp_path: Path) -> None:
    fx = _p2_fixture(tmp_path, messages=2)
    payload = run_p2_fault_observation(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        fault_selector="summary_upsert",
    )
    assert payload["disposition"] == "restored"


def test_p2_c9_evidence_freeze(tmp_path: Path) -> None:
    fx = _p2_fixture(tmp_path)
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
        import hashlib

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
    with coord._session() as session:
        before = unrelated_sentinel_digest(session.store, [str(sentinel)])
    coord.run()
    with coord._session() as session:
        after = unrelated_sentinel_digest(session.store, [str(sentinel)])
    assert before == after


def test_p2_c12_nonce_receipt_one_run(tmp_path: Path) -> None:
    from incremental_jsonl_canary import assert_not_reused, consume_nonce, nonce_receipt_path

    fx = _p2_fixture(tmp_path)
    consume_nonce(fx["root"], fx["grant"], expected_sha256=fx["digest"])
    receipt_path = nonce_receipt_path(fx["root"])
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload["stage"] = "completed"
    receipt_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CanaryRefused):
        assert_not_reused(fx["root"], fx["grant"])
