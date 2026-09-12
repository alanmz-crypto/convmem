"""Hermetic tests for the Arc Codex P2 runtime-readiness corrective."""

# pylint: disable=too-many-lines

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from chroma_write_store import current_code_revision
from incremental_jsonl_canary import (
    P2_LIVE_CAPABILITY_MODE,
    CanaryRefused,
    ProductionCanaryBoundary,
    canary_coordinator,
    capture_rollback_capsule,
    decode_grant,
    is_p2_live_grant,
    prove_cli_watcher_unreachable,
    restore_rollback_capsule,
    run_p2_orchestration,
    simulate_pure_append,
    validate_grant,
)
from incremental_jsonl import IncrementalJsonlError
from incremental_jsonl_canary_p2 import (
    FAULT_STAGE,
    LIVE_EVIDENCE_NAME,
    REQUIRED_SERVING_STAGES,
    ZERO_DIGEST,
    _persist_receipt,
    _source_immutability_token,
    bind_live_append_for_faults,
    default_model_manifest,
    default_network_self_test,
    default_writer_census,
    default_zero_adoption,
    enforce_call_ceilings,
    freeze_live_evidence,
    gate0_preflight_live,
    install_p2_network_policy,
    load_stage_receipt,
    next_float32,
    persist_call_counters,
    prepare_live_p2,
    recovery_equivalent,
    run_contained_child,
    run_live_t3,
    run_live_t4,
    run_live_t5,
    serving_observation_from_timeline,
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
    production = tmp_path / "live-share"
    production.mkdir()
    monkeypatch.setattr(
        "incremental_jsonl_canary.known_production_roots",
        lambda **kwargs: (production,),
    )
    fixture_root = hermetic_root(tmp_path)
    _source_path, source_grant = write_kiro_source(fixture_root, 68)
    grant, _unused_digest = build_grant(fixture_root, source_grant)
    mutated = grant.to_payload()
    for entry in mutated["resources"]:
        if entry["role"] == "processed":
            entry["path"] = str(production / "processed.json")
    grant_file = fixture_root / "blocked-production-grant.json"
    grant_file.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
    os.chmod(grant_file, 0o600)
    loaded = decode_grant(grant_file)
    expected = hashlib.sha256(loaded.digest_payload()).hexdigest()
    with pytest.raises(CanaryRefused, match="canary_grant_production_path"):
        validate_grant(loaded, expected_sha256=expected, code_revision=loaded.code_revision)


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
    launcher_tmp = tmp_path / "p1-launcher"
    launcher_tmp.mkdir()
    workspace = hermetic_root(launcher_tmp)
    _source_path, source = write_kiro_source(workspace, 68)
    p1_grant, _unused = build_grant(workspace, source, code_revision=current_code_revision())
    stored = write_grant_file(workspace, p1_grant)
    sha = hashlib.sha256(decode_grant(stored).digest_payload()).hexdigest()
    launched = _launcher(stored, sha, ["--stage", "p2-t3"])
    assert launched.returncode == 2
    assert "canary_p2_unauthorized" in launched.stderr


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
    assert payload["serving"]["samples"] >= 3
    assert isinstance(payload["serving"]["mixed_s"], float)
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
    receipt = load_stage_receipt(fx["grant"])
    receipt.next_stage = "t5-fault-1-complete"
    _persist_receipt(fx["grant"], receipt)
    payload = run_live_t5(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        fault_selector="summary_upsert",
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    assert payload["pre_fault_capsule"] != ZERO_DIGEST
    assert payload["child"]["returncode"] == 86
    assert payload["disposition"] in {"restored", "recovery_unproven"}
    assert payload["replay_outcome"] is None
    assert payload["serving"]["samples"] >= 3


def test_c5_contained_child_proves_descendants_absent() -> None:
    script = "import os,time\nos._exit(86)\n"
    result = run_contained_child([sys.executable, "-I", "-c", script])
    assert result["returncode"] == 86
    assert not result["descendants"]


def test_n5_grandchild_is_absent_after_exit() -> None:
    script = (
        "import os,time\n"
        "if os.fork() == 0:\n"
        "    time.sleep(20)\n"
        "    os._exit(0)\n"
        "os._exit(86)\n"
    )
    result = run_contained_child([sys.executable, "-I", "-c", script])
    assert result["returncode"] == 86
    assert not result["descendants"]
    try:
        os.killpg(result["pgid"], 0)
        raise AssertionError("process group still exists")
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        raise AssertionError(f"cannot prove process group absent: {exc}") from exc


def test_n6_non_crash_exit_is_refused(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    receipt = load_stage_receipt(fx["grant"])
    receipt.next_stage = "t5-fault-1-complete"
    _persist_receipt(fx["grant"], receipt)
    with pytest.raises(CanaryRefused, match="canary_fault_exit"):
        run_live_t5(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            fault_selector="summary_upsert",
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
            child_argv=[sys.executable, "-I", "-c", "raise SystemExit(0)"],
        )


def test_c6_live_evidence_schema_rejects_incomplete(tmp_path: Path) -> None:
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
    with pytest.raises(CanaryRefused, match="canary_stage_order|canary_evidence"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={"t3-incomplete": True},
            disposition="recovery_unproven",
        )
    assert not (Path(fx["grant"].evidence_dir) / LIVE_EVIDENCE_NAME).exists()


def test_c6_missing_gate0_is_incomplete(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    with pytest.raises(CanaryRefused, match="canary_evidence|canary_stage_order"):
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


def _stable_serving_timeline() -> list[dict]:
    return [
        {"monotonic_s": 1.0, "summary": 1, "unit": 1, "mixed": False, "error": None},
        {"monotonic_s": 1.1, "summary": 1, "unit": 1, "mixed": False, "error": None},
        {"monotonic_s": 1.2, "summary": 1, "unit": 1, "mixed": False, "error": None},
    ]


def _complete_serving_observations() -> list[dict]:
    return [
        serving_observation_from_timeline(stage, _stable_serving_timeline())
        for stage in REQUIRED_SERVING_STAGES
    ]


def _forge_t6_receipt(
    grant,
    digest,
    *,
    faults=None,
    appends=None,
    dispositions=None,
    next_stage="t6-evidence-frozen",
    serving=None,
):
    receipt = load_stage_receipt(grant)
    receipt.grant_digest = digest
    receipt.next_stage = next_stage
    receipt.faults_completed = list(faults or FAULT_STAGE)
    receipt.append_identities = list(appends or ["append-one"])
    receipt.recovery_dispositions = list(dispositions or (["restored"] * 5))
    receipt.capsule_digest = "a" * 64
    receipt.serving_observations = (
        list(serving) if serving is not None else _complete_serving_observations()
    )
    _persist_receipt(grant, receipt)
    return receipt


def test_b1_freeze_requires_t6_and_five_faults(tmp_path: Path) -> None:
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
    with pytest.raises(CanaryRefused, match="canary_stage_order"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={},
            disposition="converged",
        )
    _forge_t6_receipt(fx["grant"], fx["digest"], faults=["dedupe_reconcile"])
    with pytest.raises(CanaryRefused, match="canary_evidence"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={},
            disposition="converged",
        )


def test_b1_freeze_derives_disposition(tmp_path: Path) -> None:
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
    _forge_t6_receipt(fx["grant"], fx["digest"])
    digest = freeze_live_evidence(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        gate0_report=report,
        sections={"t5": {"ok": True}},
    )
    evidence = Path(fx["grant"].evidence_dir) / LIVE_EVIDENCE_NAME
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["disposition"] == "restored"
    assert payload["hermetic"] is False
    assert set(payload["faults_completed"]) == set(FAULT_STAGE)
    assert payload["append_receipts"]
    assert payload["serving"]["observations"]
    assert "mixed_s" in payload["serving"]
    assert "recovery_s" in payload["serving"]
    assert digest


def test_b2_mismatch_is_recovery_unproven(tmp_path: Path, monkeypatch) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    receipt = load_stage_receipt(fx["grant"])
    receipt.next_stage = "t5-fault-1-complete"
    _persist_receipt(fx["grant"], receipt)
    original = capture_rollback_capsule
    calls = {"n": 0}

    def wrapped(*args, **kwargs):
        payload = original(*args, **kwargs)
        calls["n"] += 1
        if calls["n"] > 1:
            mutated = dict(payload)
            mutated["state_digests"] = dict(payload.get("state_digests") or {})
            mutated["state_digests"]["checkpoint"] = "0" * 64
            return mutated
        return payload

    monkeypatch.setattr("incremental_jsonl_canary_p2.capture_rollback_capsule", wrapped)
    payload = run_live_t5(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        fault_selector="summary_upsert",
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    assert payload["disposition"] == "recovery_unproven"


def test_b2_caller_disposition_cannot_override(tmp_path: Path) -> None:
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
    _forge_t6_receipt(
        fx["grant"],
        fx["digest"],
        dispositions=["restored"] * 4 + ["recovery_unproven"],
    )
    with pytest.raises(CanaryRefused, match="does not match observed"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={},
            disposition="restored",
        )


def test_b4_restore_rewinds_checkpoint_after_tamper(tmp_path: Path) -> None:
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
    coordinator = canary_coordinator(fx["boundary"], fx["grant"].source.path)
    capsule = capture_rollback_capsule(coordinator, unrelated_manifest={})
    checkpoint = coordinator.paths["checkpoint"]
    original = json.loads(checkpoint.read_text(encoding="utf-8"))
    tampered = dict(original)
    tampered["record_count"] = 999
    checkpoint.write_text(json.dumps(tampered), encoding="utf-8")
    restore_rollback_capsule(coordinator, capsule)
    restored = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert restored == original
    assert restored["record_count"] != 999


def test_b7_serving_visibility_fails_closed_without_probe(tmp_path: Path, monkeypatch) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )

    class BrokenRepo:
        def __enter__(self):
            raise RuntimeError("serving unavailable")

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        "serving_index_repository.open_serving_index_repository",
        lambda *_args, **_kwargs: BrokenRepo(),
    )
    with pytest.raises(CanaryRefused, match="canary_serving_visible"):
        run_live_t3(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
        )


def test_b3_crash_self_is_not_fault_evidence(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    receipt = load_stage_receipt(fx["grant"])
    receipt.next_stage = "t5-fault-1-complete"
    _persist_receipt(fx["grant"], receipt)
    with pytest.raises(CanaryRefused, match="canary_fault_evidence"):
        run_live_t5(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            fault_selector="summary_upsert",
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
            child_argv=[sys.executable, "-I", str(REPO_ROOT / "incremental_jsonl_canary_live_worker.py"), "crash-self"],
        )


def test_b5_prepare_does_not_chmod_source(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    source = Path(fx["grant"].source.path)
    meta = Path(fx["grant"].source.metadata_path)
    os.chmod(source, 0o644)
    os.chmod(meta, 0o644)
    before = _source_immutability_token(fx["grant"])
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    after = _source_immutability_token(fx["grant"])
    assert before == after
    assert stat.S_IMODE(source.stat().st_mode) == 0o644
    assert stat.S_IMODE(meta.stat().st_mode) == 0o644


def test_b6_capsule_exists_before_overlay_mutation(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    capsule = Path(fx["grant"].rollback.capsule_path)
    census = fx["boundary"].layout["census"] / "census-header.json"
    assert not capsule.exists()
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert capsule.is_file()
    payload = json.loads(capsule.read_text(encoding="utf-8"))
    assert payload["source_path"] == fx["grant"].source.path
    assert census.is_file()


def test_b8_out_of_order_fault_is_refused(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    with pytest.raises(CanaryRefused, match="canary_stage_order"):
        run_live_t5(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            fault_selector="dedupe_reconcile",
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
        )


def test_n1_network_denial_is_policy_specific(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    result = default_network_self_test(fx["grant"])
    assert result["pass"] == "true"
    assert result["loopback"].startswith("allowed")
    assert result["non_loopback"] == "denied-before-socket"
    import socket
    from incremental_jsonl_isolation import IsolationViolation

    real_create = socket.create_connection
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    try:
        install_p2_network_policy(fx["grant"].provider.loopback_host, dry_run=True)
        with pytest.raises(IsolationViolation, match="denied before socket"):
            socket.create_connection(("203.0.113.1", 9), timeout=0.2)
    finally:
        socket.create_connection = real_create
        socket.socket.connect = real_connect
        socket.socket.connect_ex = real_connect_ex


def test_n4_writer_census_is_non_creating(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    lock_path = fx["boundary"].layout["writer_lock"]
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(b"")
    os.chmod(lock_path, 0o600)
    before = {path: path.stat().st_mtime_ns for path in fx["root"].rglob("*") if path.is_file()}
    result = default_writer_census(fx["boundary"])
    after = {path: path.stat().st_mtime_ns for path in fx["root"].rglob("*") if path.is_file()}
    assert result["pass"] == "true"
    assert before == after


def test_n7_unrelated_manifest_is_derived(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    from incremental_jsonl_canary_p2 import _unrelated_readonly_manifest

    manifest = _unrelated_readonly_manifest(fx["boundary"], grant=fx["grant"])
    assert manifest["derived"] is True
    assert "digest" in manifest


def test_n9_production_probes_run_real_code(tmp_path: Path, monkeypatch) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    assert default_model_manifest(fx["grant"])["pass"] == "true"
    assert default_zero_adoption(fx["boundary"], fx["grant"])["pass"] == "true"
    network = default_network_self_test(fx["grant"])
    assert network["pass"] == "true"
    seen: list[str] = []

    def fake_run(args, *_rest, **_kwargs):
        seen.append(" ".join(str(part) for part in args) if isinstance(args, (list, tuple)) else str(args))

        class Result:
            stdout = "inactive\n"
            stderr = ""
            returncode = 3

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    from incremental_jsonl_canary_p2 import default_service_status

    status = default_service_status()
    assert status["pass"] == "true"
    assert any("is-active" in item for item in seen)
    assert not any(" start " in f" {item} " for item in seen)


def test_n13_directory_role_does_not_grant_subtree(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    sneaky = Path(fx["boundary"].layout["dedupe"]) / "unrelated-escape.json"
    sneaky.write_text("nope", encoding="utf-8")
    with pytest.raises(CanaryRefused, match="canary_boundary_escape"):
        fx["boundary"].resolve_mutable(sneaky, label="escape")


def test_n3_grant_bound_identities_are_validated(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    overlay = Path(fx["grant"].config_overlay)
    overlay.unlink()
    overlay.write_text("tampered-overlay\n", encoding="utf-8")
    os.chmod(overlay, 0o600)
    with pytest.raises(CanaryRefused, match="canary_gate0_paths"):
        gate0_preflight_live(
            fx["grant"],
            fx["boundary"],
            expected_sha256=fx["digest"],
            code_revision=current_code_revision(),
            hooks=live_gate0_hooks_pass(),
        )


def _sample_recovery_capsule(
    *,
    embedding: list[float] | None = None,
    row_id: str = "row-1",
    document: str = "body",
    metadata: dict | None = None,
    checkpoint: str = "a" * 64,
) -> dict:
    row = {
        "id": row_id,
        "document": document,
        "embedding": list(embedding or [0.25, -0.9529412388801575]),
        "metadata": dict(metadata or {"source_path": "/tmp/src"}),
        "collection": "conversation_summaries",
    }
    return {
        "rollback": {
            "version": 1,
            "summaries": [row],
            "units": [],
            "export_lines": [],
            "processed_preimage": {},
            "source_path": "/tmp/src",
            "state_files": {},
            "prepared_files": {},
            "dedupe_files": {},
        },
        "state_digests": {"checkpoint": checkpoint},
        "unrelated_manifest": {"derived": True, "sources": {}},
    }


def test_r1_one_ulp_embedding_is_restored() -> None:
    base = -0.9529412388801575
    pre = _sample_recovery_capsule(embedding=[base])
    post = _sample_recovery_capsule(embedding=[next_float32(base, 1)])
    assert recovery_equivalent(pre, post)


def test_r1_adversarial_mismatches_stay_unproven() -> None:
    base = -0.9529412388801575
    pre = _sample_recovery_capsule(embedding=[base])
    assert not recovery_equivalent(
        pre, _sample_recovery_capsule(embedding=[next_float32(base, 2)])
    )
    assert not recovery_equivalent(pre, _sample_recovery_capsule(row_id="other"))
    assert not recovery_equivalent(pre, _sample_recovery_capsule(document="changed"))
    assert not recovery_equivalent(
        pre, _sample_recovery_capsule(metadata={"source_path": "/tmp/other"})
    )
    assert not recovery_equivalent(
        pre, _sample_recovery_capsule(checkpoint="b" * 64)
    )


def test_r2_restored_path_does_not_claim_zero_replay(tmp_path: Path) -> None:
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
    append_kiro_source(fx["source"], 61, 7)
    run_live_t4(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    append_kiro_source(fx["source"], 68, 7)
    bound = bind_live_append_for_faults(fx["grant"], expected_sha256=fx["digest"])
    assert bound["stage"] == "waiting-for-external-append-2"
    payload = run_live_t5(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        fault_selector="summary_upsert",
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    assert payload["disposition"] == "restored"
    assert payload["replay_outcome"] is None


def test_r3_gate0_passes_after_prepare_and_fails_on_mutation(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    report = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert report["checks"]["11_capsule"]["captured"] is True
    capsule = Path(fx["grant"].rollback.capsule_path)
    original = capsule.read_bytes()
    capsule.write_text('{"tampered": true}\n', encoding="utf-8")
    with pytest.raises(CanaryRefused, match="canary_gate0_capsule"):
        gate0_preflight_live(
            fx["grant"],
            fx["boundary"],
            expected_sha256=fx["digest"],
            code_revision=current_code_revision(),
            hooks=live_gate0_hooks_pass(),
        )
    capsule.write_bytes(original)
    overlay = Path(fx["grant"].config_overlay)
    overlay.unlink()
    overlay.write_text("mutated-overlay\n", encoding="utf-8")
    os.chmod(overlay, 0o600)
    with pytest.raises(CanaryRefused, match="canary_gate0_paths"):
        gate0_preflight_live(
            fx["grant"],
            fx["boundary"],
            expected_sha256=fx["digest"],
            code_revision=current_code_revision(),
            hooks=live_gate0_hooks_pass(),
        )


def test_r4_launcher_bind_stage_is_separately_invoked(tmp_path: Path) -> None:
    fx = build_p2_v2_fixture(tmp_path, messages=61)
    prepare_live_p2(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    with pytest.raises(CanaryRefused, match="canary_stage_order"):
        bind_live_append_for_faults(fx["grant"], expected_sha256=fx["digest"])
    launcher = (REPO_ROOT / "scripts/run-jsonl-production-canary.py").read_text(encoding="utf-8")
    assert '"t5-bind-append"' in launcher
    assert '"p2-t5-bind"' in launcher
    assert "bind_live_append_for_faults" in launcher
    worker = (REPO_ROOT / "incremental_jsonl_canary_live_worker.py").read_text(encoding="utf-8")
    assert 'command == "t5-bind"' in worker
    all_stages = _launcher(fx["grant_path"], fx["digest"], ["--stage", "p2-all"])
    assert all_stages.returncode == 2
    assert "canary_p2_all_refused" in all_stages.stderr


def test_r4_documented_sequence_prepare_through_t6(tmp_path: Path) -> None:
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
    append_kiro_source(fx["source"], 61, 7)
    run_live_t4(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        provider_mode="hermetic",
        invoker=_FakeInvoker(),
    )
    after_t4 = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    assert after_t4["checks"]["11_capsule"]["captured"] is True
    append_kiro_source(fx["source"], 68, 7)
    bind_live_append_for_faults(fx["grant"], expected_sha256=fx["digest"])
    dispositions: list[str] = []
    for selector in FAULT_STAGE:
        payload = run_live_t5(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            fault_selector=selector,
            provider_mode="hermetic",
            invoker=_FakeInvoker(),
        )
        assert payload["child"]["returncode"] == 86
        assert payload["replay_outcome"] is None
        dispositions.append(payload["disposition"])
    assert "restored" in dispositions
    report = gate0_preflight_live(
        fx["grant"],
        fx["boundary"],
        expected_sha256=fx["digest"],
        code_revision=current_code_revision(),
        hooks=live_gate0_hooks_pass(),
    )
    digest = freeze_live_evidence(
        fx["boundary"],
        fx["grant"],
        expected_sha256=fx["digest"],
        gate0_report=report,
        sections={"t5": {"dispositions": dispositions}},
    )
    evidence = Path(fx["grant"].evidence_dir) / LIVE_EVIDENCE_NAME
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["disposition"] in {"restored", "recovery_unproven"}
    assert payload["disposition"] != "converged"
    assert set(payload["faults_completed"]) == set(FAULT_STAGE)
    assert len(payload["append_receipts"]) == 2
    serving = payload["serving"]
    assert [item["stage"] for item in serving["observations"]] == list(REQUIRED_SERVING_STAGES)
    for item in serving["observations"]:
        assert item["timeline"]
        assert "mixed_s" in item
        assert "recovery_s" in item
    assert serving["mixed_s"] >= 0
    assert serving["recovery_s"] >= 0
    assert digest


def _prepared_live_fixture(tmp_path: Path, *, messages: int = 61):
    fx = build_p2_v2_fixture(tmp_path, messages=messages)
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
    return fx, report


def test_c2_converged_disposition_is_refused(tmp_path: Path) -> None:
    fx, report = _prepared_live_fixture(tmp_path)
    _forge_t6_receipt(fx["grant"], fx["digest"], dispositions=["converged"] * 5)
    with pytest.raises(CanaryRefused, match="unknown recovery disposition"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={},
        )


def test_c3_missing_timeline_fails_closed(tmp_path: Path) -> None:
    fx, report = _prepared_live_fixture(tmp_path)
    _forge_t6_receipt(fx["grant"], fx["digest"], serving=[])
    with pytest.raises(CanaryRefused, match="canary_serving_evidence"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={},
        )


def test_c3_malformed_timeline_fails_closed(tmp_path: Path) -> None:
    fx, report = _prepared_live_fixture(tmp_path)
    malformed = _complete_serving_observations()
    malformed[0] = dict(malformed[0])
    malformed[0]["timeline"] = [{"monotonic_s": 1.0}]
    _forge_t6_receipt(fx["grant"], fx["digest"], serving=malformed)
    with pytest.raises(CanaryRefused, match="canary_serving_evidence"):
        freeze_live_evidence(
            fx["boundary"],
            fx["grant"],
            expected_sha256=fx["digest"],
            gate0_report=report,
            sections={},
        )


def test_c4_dedupe_outside_granted_role_refused_before_mutation(tmp_path: Path) -> None:
    fx, _report = _prepared_live_fixture(tmp_path)
    coordinator = canary_coordinator(fx["boundary"], fx["grant"].source.path)
    outside = Path(fx["boundary"].layout["chroma"]) / "nested-escape"
    outside.mkdir(parents=True, exist_ok=True)
    os.chmod(outside, 0o755)
    before_mode = stat.S_IMODE(outside.stat().st_mode)
    sentinel = outside / "untouched"
    sentinel.write_text("keep", encoding="utf-8")
    coordinator.cfg["index"]["chroma_dir"] = str(outside)
    with pytest.raises((IncrementalJsonlError, CanaryRefused), match="outside granted role|canary_boundary"):
        coordinator._restore_dedupe_files(  # pylint: disable=protected-access
            {"dedupe_queue.jsonl": "sneaky\n", "ingest_duplicate_suppressions.jsonl": None}
        )
    assert stat.S_IMODE(outside.stat().st_mode) == before_mode
    assert sentinel.read_text(encoding="utf-8") == "keep"
    assert not (outside / "dedupe_queue.jsonl").exists()


def test_c4_valid_exact_role_restore_still_succeeds(tmp_path: Path) -> None:
    fx, _report = _prepared_live_fixture(tmp_path)
    coordinator = canary_coordinator(fx["boundary"], fx["grant"].source.path)
    granted = Path(fx["boundary"].layout["dedupe"]) / "dedupe_queue.jsonl"
    granted.write_text("keep-me\n", encoding="utf-8")
    snapshot = coordinator._snapshot_before_images()  # pylint: disable=protected-access
    granted.write_text("tampered\n", encoding="utf-8")
    coordinator._restore_before_images(snapshot)  # pylint: disable=protected-access
    assert granted.read_text(encoding="utf-8") == "keep-me\n"
