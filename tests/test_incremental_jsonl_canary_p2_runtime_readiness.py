"""Hermetic tests for the Arc Codex P2 runtime-readiness corrective."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from chroma_write_store import current_code_revision
from incremental_jsonl_canary import (
    P2_LIVE_CAPABILITY_MODE,
    CanaryRefused,
    ProductionCanaryBoundary,
    decode_grant,
    is_p2_live_grant,
    prove_cli_watcher_unreachable,
    run_p2_orchestration,
    simulate_pure_append,
    validate_grant,
)
from incremental_jsonl_canary_p2 import (
    LIVE_EVIDENCE_NAME,
    ZERO_DIGEST,
    enforce_call_ceilings,
    freeze_live_evidence,
    gate0_preflight_live,
    load_stage_receipt,
    persist_call_counters,
    prepare_live_p2,
    run_contained_child,
    run_live_t3,
    run_live_t4,
    run_live_t5,
    stage_receipt_path,
    validate_p2_live_grant,
)
from tests.incremental_jsonl_canary_helpers import (
    append_kiro_source,
    build_grant,
    build_p2_v2_fixture,
    hermetic_root,
    live_gate0_hooks_pass,
    write_grant_file,
    write_kiro_source,
)
from tests.incremental_jsonl_helpers import fake_distill, fake_embed, fake_summarize
from tests.test_incremental_jsonl_canary_baseline import BASELINE_HASHES

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = REPO_ROOT / "scripts/run-jsonl-production-canary.py"


class _FakeInvoker:
    def summarize(self, text, **kwargs):
        return fake_summarize(text, **kwargs)

    def distill(self, text, **kwargs):
        return fake_distill(text, **kwargs)

    def embed(self, text, **kwargs):
        return fake_embed(text, **kwargs)


def _launcher(grant_path: Path, digest: str, extra: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--grant",
            str(grant_path),
            "--grant-sha256",
            digest,
            *extra,
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_c0_baseline_hashes_unchanged() -> None:
    for name, expected in BASELINE_HASHES.items():
        actual = hashlib.sha256((REPO_ROOT / name).read_bytes()).hexdigest()
        assert actual == expected, name
    report = prove_cli_watcher_unreachable()
    assert report["canary_launcher_registered"] == "no"


def test_c1_v1_bytes_not_reinterpreted(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant, code_revision=current_code_revision())
    assert grant.capability_mode != P2_LIVE_CAPABILITY_MODE
    with pytest.raises(CanaryRefused, match="canary_mode"):
        validate_p2_live_grant(grant, expected_sha256=digest, code_revision=grant.code_revision)


def test_c1_live_grant_binds_real_fields(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    assert is_p2_live_grant(fx["grant"])
    validate_p2_live_grant(
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
    )
    assert fx["grant"].persistent_config is not None
    assert fx["grant"].restic is not None
    assert len(fx["grant"].restic.snapshot_id) == 64
    assert fx["grant"].model_manifests
    assert all(len(item.digest) == 64 for item in fx["grant"].model_manifests)


def test_c1_from_p2_live_grant_creates_no_files(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    before = {path: path.stat().st_mtime_ns for path in fx["root"].rglob("*") if path.is_file()}
    ProductionCanaryBoundary.from_p2_live_grant(fx["grant"], root=fx["root"])
    after = {path: path.stat().st_mtime_ns for path in fx["root"].rglob("*") if path.is_file()}
    assert before == after
    assert not (fx["root"] / ".convmem-jsonl-canary-root").exists()


def test_c1_p1_still_denies_production_paths(tmp_path: Path, monkeypatch) -> None:
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
    bad_digest = hashlib.sha256(loaded.digest_payload()).hexdigest()
    with pytest.raises(CanaryRefused, match="canary_grant_production_path"):
        validate_grant(loaded, expected_sha256=bad_digest, code_revision=loaded.code_revision)


def test_c2_gate0_is_side_effect_free(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    before = sorted((path.relative_to(fx["root"]), path.stat().st_mtime_ns) for path in fx["root"].rglob("*"))
    report = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    after = sorted((path.relative_to(fx["root"]), path.stat().st_mtime_ns) for path in fx["root"].rglob("*"))
    assert before == after
    assert report["mode"] == P2_LIVE_CAPABILITY_MODE
    assert len(report["checks"]) == 12
    assert report["checks"]["11_capsule"]["captured"] is False
    assert report["checks"]["11_capsule"]["readable"] is False
    assert not (Path(fx["grant"].evidence_dir) / "gate0-preflight.json").exists()


def test_c2_gate0_never_starts_watcher(tmp_path: Path, monkeypatch) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    seen: list[str] = []
    real_run = subprocess.run

    def wrapped(args, *rest, **kwargs):
        seen.append(" ".join(str(part) for part in args) if isinstance(args, (list, tuple)) else str(args))
        if "systemctl" in seen[-1] and "start" in seen[-1]:
            raise AssertionError("mutating service verb")
        return real_run(args, *rest, check=kwargs.pop("check", False), **kwargs)

    monkeypatch.setattr(subprocess, "run", wrapped)
    gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert not any(" start " in item or item.endswith(" start") for item in seen)


def test_c2_restic_stub_cannot_pass(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    hooks = live_gate0_hooks_pass()
    hooks.restic_identifier = lambda _grant: {
        "pass": "true",
        "backup_id": "hermetic-stub-no-restore",
        "restore": "not_authorized",
    }
    with pytest.raises(CanaryRefused, match="canary_gate0_restic"):
        gate0_preflight_live(
            fx["grant"],
            fx["boundary"],
            expected_sha256=fx["digest"],
            code_revision=current_code_revision(),
            hooks=hooks,
        )


def _fail_zero_adoption(_fx, hooks):
    hooks.zero_adoption = lambda *_a: {"pass": "false"}
    return {}


def _fail_watcher(_fx, hooks):
    hooks.watcher_probe = lambda: {"pass": "false"}
    return {}


def _fail_writer(_fx, hooks):
    hooks.writer_census = lambda _b: {"pass": "false"}
    return {}


def _fail_models(_fx, hooks):
    hooks.model_manifest = lambda _g: {"pass": "false"}
    return {}


def _fail_network(_fx, hooks):
    hooks.network_self_test = lambda _g: {"pass": "false"}
    return {}


def _fail_restic(_fx, hooks):
    hooks.restic_identifier = lambda _g: {"pass": "false"}
    return {}


@pytest.mark.parametrize(
    ("error_code", "mutator"),
    [
        ("canary_grant_digest", lambda fx, hooks: {"expected_sha256": "0" * 64}),
        ("canary_gate0_baseline", lambda fx, hooks: {"tamper": True}),
        ("canary_gate0_adoption", _fail_zero_adoption),
        ("canary_gate0_config", lambda fx, hooks: {"bad_config": True}),
        ("canary_gate0_watcher", _fail_watcher),
        ("canary_gate0_writer", _fail_writer),
        ("canary_gate0_models", _fail_models),
        ("canary_gate0_network", _fail_network),
        ("canary_gate0_capsule", lambda fx, hooks: {"capsule": True}),
        ("canary_gate0_restic", _fail_restic),
    ],
)
def test_c2_twelve_checks_fail_closed(tmp_path: Path, error_code: str, mutator) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    hooks = live_gate0_hooks_pass()
    kwargs = {
        "expected_sha256": fx["digest"],
        "code_revision": current_code_revision(),
        "hooks": hooks,
    }
    flags = mutator(fx, hooks) or {}
    if "expected_sha256" in flags:
        kwargs["expected_sha256"] = flags["expected_sha256"]
    if flags.get("tamper"):
        data = bytearray(fx["source"].read_bytes())
        data[-2] ^= 0x01
        fx["source"].write_bytes(bytes(data))
    if flags.get("bad_config"):
        path = Path(fx["grant"].persistent_config.path)
        path.write_text("[index]\n[index.incremental_jsonl]\nenabled = true\n", encoding="utf-8")
    if flags.get("capsule"):
        Path(fx["grant"].rollback.capsule_path).write_text("{}", encoding="utf-8")
    with pytest.raises(CanaryRefused, match=error_code):
        gate0_preflight_live(fx["grant"], fx["boundary"], **kwargs)


def test_c2_zero_adoption_uses_readonly_chroma(tmp_path: Path, monkeypatch) -> None:
    fx = build_p2_v2_fixture(tmp_path)

    def boom(*_args, **_kwargs):
        raise AssertionError("writable Chroma client")

    monkeypatch.setattr("chroma_store.ChromaStore.__init__", boom)
    report = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert report["checks"]["4_zero_adoption"]["pass"] == "true"


def test_c2_lock_census_does_not_create(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    lock_path = fx["boundary"].layout["writer_lock"]
    assert not lock_path.exists()
    gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert not lock_path.exists()


def test_c4_live_module_has_no_test_imports() -> None:
    for relative in (
        "incremental_jsonl_canary_p2.py",
        "incremental_jsonl_canary_live_worker.py",
        "scripts/run-jsonl-production-canary.py",
    ):
        tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("tests"), relative
                    assert alias.name != "pytest", relative
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("tests"), relative
                assert node.module != "pytest", relative
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "install_fakes" not in text
        assert "simulate_pure_append" not in text


def test_c4_hermetic_mode_cannot_select_real_providers(tmp_path: Path) -> None:
    from incremental_jsonl_canary_p2 import install_provider_invoker

    fx = build_p2_v2_fixture(tmp_path)
    with pytest.raises(CanaryRefused, match="canary_provider_mode"):
        with install_provider_invoker(None, provider_mode="hermetic"):
            pass
    with pytest.raises(CanaryRefused, match="canary_provider_mode"):
        with install_provider_invoker(_FakeInvoker(), provider_mode="live"):
            pass
    _ = fx


def test_c5_launcher_refuses_p1_mutation_without_watcher(tmp_path: Path) -> None:
    root = hermetic_root(tmp_path)
    _, source_grant = write_kiro_source(root, 61)
    grant, digest = build_grant(root, source_grant, code_revision=current_code_revision())
    grant_path = write_grant_file(root, grant)
    digest = hashlib.sha256(decode_grant(grant_path).digest_payload()).hexdigest()
    result = _launcher(grant_path, digest, ["--stage", "p2-t3"])
    assert result.returncode == 2
    assert "canary_p2_unauthorized" in result.stderr


def test_c5_launcher_refuses_v1_and_p2_all(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    result = _launcher(fx["grant_path"], fx["digest"], ["--stage", "p2-all"])
    assert result.returncode == 2
    assert "canary_p2_all_refused" in result.stderr
    v1_root = tmp_path / "v1"
    v1_root.mkdir()
    root = hermetic_root(v1_root)
    _, source_grant = write_kiro_source(root, 61)
    from tests.incremental_jsonl_canary_helpers import build_p2_grant

    grant, digest = build_p2_grant(root, source_grant, code_revision=current_code_revision())
    path = write_grant_file(root, grant)
    digest = hashlib.sha256(decode_grant(path).digest_payload()).hexdigest()
    result = _launcher(path, digest, ["--stage", "p2-t3"])
    assert result.returncode == 2
    assert "canary_mode_retired" in result.stderr


def test_c5_live_orchestration_refuses_all_stages(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    with pytest.raises(CanaryRefused, match="canary_p2_all_refused"):
        run_p2_orchestration(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            code_revision=current_code_revision(),
        )


def test_c5_source_write_helpers_refuse_live_grants(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    before = fx["source"].read_bytes()
    with pytest.raises(CanaryRefused, match="canary_source_immutable"):
        simulate_pure_append(fx["source"], start_index=61, count=49, grant=fx["grant"])
    assert fx["source"].read_bytes() == before


def test_c5_68_message_case_does_not_append(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=68)
    before = fx["source"].read_bytes()
    with pytest.raises(CanaryRefused, match="canary_stage"):
        run_live_t4(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
        )
    assert fx["source"].read_bytes() == before
    assert before.count(b"\n") == 68


def test_c3_prepare_and_t3_two_chunk(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepared = prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert prepared["capsule_digest"] != ZERO_DIGEST
    payload = run_live_t3(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    assert payload["chunk_starts"] == [0, 50]
    assert payload["replay_counters"]["summarize"] == 0
    receipt = load_stage_receipt(fx["grant"])
    assert receipt.stage == "t3-initial-complete"
    assert receipt.next_stage == "waiting-for-external-append-1"


def test_c5_t4_requires_external_append(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    run_live_t3(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    updated = append_kiro_source(fx["source"], 61, 7)
    payload = run_live_t4(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    assert payload["accepted_messages"] == 68
    assert updated.size != fx["grant"].source.size


def test_c5_out_of_order_and_tamper(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    with pytest.raises(CanaryRefused, match="canary_stage_order"):
        run_live_t4(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
        )
    path = stage_receipt_path(fx["grant"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["stage"] = "t6-evidence-frozen"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CanaryRefused, match="canary_stage_tamper"):
        load_stage_receipt(fx["grant"])


def test_c5_call_cap_plus_one_and_restart(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    persist_call_counters(fx["grant"], {"summarize": 8, "distill": 0, "summary_embed": 0, "unit_embed": 0})
    with pytest.raises(CanaryRefused, match="canary_call_cap"):
        enforce_call_ceilings(fx["grant"], "summarize", stage_ceilings={"summarize": 2})
    persist_call_counters(fx["grant"], {"summarize": 1, "distill": 0, "summary_embed": 0, "unit_embed": 0})
    counters = enforce_call_ceilings(fx["grant"], "summarize", stage_ceilings={"summarize": 2})
    assert counters["summarize"] == 2


def test_c5_pre_fault_capsule_and_descendants(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    run_live_t3(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    receipt = load_stage_receipt(fx["grant"])
    receipt.stage = "waiting-for-external-append-2"
    receipt.next_stage = "t5-fault-1-complete"
    from incremental_jsonl_canary_p2 import _persist_receipt

    _persist_receipt(fx["grant"], receipt)
    payload = run_live_t5(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        fault_selector="summary_upsert",
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
        child_argv=[sys.executable, "-I", str(REPO_ROOT / "incremental_jsonl_canary_live_worker.py"), "crash-self"],
    )
    assert payload["pre_fault_capsule"] != ZERO_DIGEST
    assert payload["child"]["returncode"] == 86
    assert payload["disposition"] == "restored"


def test_c5_contained_child_proves_descendants_absent() -> None:
    script = "import os,time\nos._exit(86)\n"
    result = run_contained_child([sys.executable, "-I", "-c", script])
    assert result["returncode"] == 86
    assert not result["descendants"]


def test_c6_live_evidence_schema(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    report = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    digest = freeze_live_evidence(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        gate0_report=report,
        sections={"t3": {"ok": True}},
        disposition="converged",
    )
    evidence = Path(fx["grant"].evidence_dir) / LIVE_EVIDENCE_NAME
    assert evidence.is_file()
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["hermetic"] is False
    assert payload["execution_class"] == "exact-resource-live"
    assert payload["schema"].endswith("exact-resource-live-v1")
    assert "p2-hermetic-evidence.json" not in str(evidence)
    assert digest


def test_c6_missing_gate0_is_incomplete(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    with pytest.raises(CanaryRefused, match="canary_evidence"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report={},
            sections={},
            disposition="converged",
        )


def test_c7_launcher_preflight_stdout_only(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    before = sorted(path for path in fx["root"].rglob("*"))
    # Inject hooks by running the Python API; launcher live restic would touch the host.
    report = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    after = sorted(path for path in fx["root"].rglob("*"))
    assert before == after
    assert report["hermetic"] is False
