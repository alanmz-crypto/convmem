"""Arc #286 scoped mutation proof shadow mode tests (design section 8)."""

# pylint: disable=protected-access,duplicate-code,unused-argument

from __future__ import annotations

import io
import json
import subprocess
import sys
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import pytest

from chroma_store import SUMMARIES, UNITS
from complete_data_restore import classify_scoped_shadow_diagnostic, OUTCOME_ADVISORY
from incremental_jsonl import IncrementalJsonlCoordinator
from incremental_mutation_proof import (
    DIAGNOSTIC_SCHEMA,
    POLICY_ID,
    _notify_coverage,
    classify_comparison,
    clear_coverage_spies,
    evaluate_call_policy,
    extract_target_ids,
    load_terminal_record,
    register_coverage_spy,
    receipts_complete,
    set_test_observer_io_error,
    set_test_policy_allow_all,
    shadow_proof_attempt,
)
from tests.incremental_jsonl_helpers import (
    WORKER,
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    worker_run,
    write_source,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "docs/plans/SCOPED-PROOF-WRITER-INVENTORY.json"
KNOWN_BYPASS_ROUTE_IDS = (
    "chroma_write_store:_IndexWriteGuardedChromaStore._collection",
    "nested_production_chroma_write_session",
    "thread_fork_attempt_token_copy",
    "stale_chroma_client_outside_reload",
)


def _set_observer(cfg_path: Path, mode: str) -> None:
    text = cfg_path.read_text(encoding="utf-8")
    if "mutation_proof_observer" not in text:
        text = text.replace(
            "allow_full_rebuild = false\n",
            f"allow_full_rebuild = false\nmutation_proof_observer = \"{mode}\"\n",
            1,
        )
    else:
        import re

        text = re.sub(
            r"mutation_proof_observer\s*=\s*\"[^\"]*\"",
            f'mutation_proof_observer = "{mode}"',
            text,
        )
    cfg_path.write_text(text, encoding="utf-8")


def _prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, mode: str = "off"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    boundary, env = isolated_env(tmp_path)
    apply_env(monkeypatch, env)
    install_fakes(monkeypatch)
    enable_incremental(boundary)
    if mode != "off":
        _set_observer(boundary.layout["user_config"], mode)
    source = write_source(boundary.root, 2)
    return boundary, source, env


def _commit_artifacts(state_dir: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for name in ("checkpoint.json", "transaction.json", "rollback.json"):
        path = state_dir / name
        if path.is_file():
            out[name] = path.read_bytes()
    return out


def _timing_events(stderr: str) -> list[dict]:
    events: list[dict] = []
    for line in stderr.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events



def _checkpoint_commit_state(coord: IncrementalJsonlCoordinator) -> str:
    path = coord.state_dir / "checkpoint.json"
    return json.loads(path.read_text(encoding="utf-8"))["commit_state"]


def test_config_rejects_scoped_observer() -> None:
    import config

    with pytest.raises(config.IncrementalJsonlConfigError) as excinfo:
        config.incremental_jsonl_settings(
            {"index": {"incremental_jsonl": {"enabled": True, "mutation_proof_observer": "scoped"}}}
        )
    assert excinfo.value.code == "invalid_mutation_proof_observer"


def test_c_sh1_sc1_off_shadow_parity_under_observer_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH1 / SC-1: off/shadow authoritative parity when observer I/O fails."""
    off_boundary, off_source, _ = _prepare(tmp_path / "off", monkeypatch, mode="off")
    sh_boundary, sh_source, _ = _prepare(tmp_path / "sh", monkeypatch, mode="shadow")
    off = IncrementalJsonlCoordinator(off_boundary, off_source)
    off_result = off.run()
    assert not (off.state_dir / "scoped-shadow").exists()
    set_test_observer_io_error(OSError("ENOSPC"))
    try:
        sh = IncrementalJsonlCoordinator(sh_boundary, sh_source)
        sh_result = sh.run()
    finally:
        set_test_observer_io_error(None)
    assert off_result.outcome == sh_result.outcome == "committed"
    assert off_result.chunks == sh_result.chunks
    assert off_result.units == sh_result.units
    assert off_result.exact_suppressed == sh_result.exact_suppressed
    assert _checkpoint_commit_state(off) == _checkpoint_commit_state(sh)


def test_c_sh2_cc1_writer_inventory_machine_checked() -> None:
    """C-SH2 / CC-1: regenerable writer inventory matches committed artifact."""
    script = ROOT / "scripts/generate_scoped_proof_writer_inventory.py"
    before = INVENTORY.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT)
    after = INVENTORY.read_text(encoding="utf-8")
    assert before == after
    payload = json.loads(after)
    assert payload["schema"] == "scoped_proof_writer_inventory_v1"
    routes = payload["routes"]
    assert routes
    for route in routes:
        assert route.get("disposition")
        assert route.get("coverage_status")
    route_ids = {route["route_id"] for route in routes}
    missing = [route_id for route_id in KNOWN_BYPASS_ROUTE_IDS if route_id not in route_ids]
    assert not missing, missing


@pytest.mark.parametrize("bypass_route_id", KNOWN_BYPASS_ROUTE_IDS)
def test_c_sh3_cc2_enumerated_bypass_route_present(bypass_route_id: str) -> None:
    """C-SH3 / CC-2: every known bypass is inventoried with explicit disposition."""
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    matches = [route for route in payload["routes"] if route["route_id"] == bypass_route_id]
    assert len(matches) == 1
    route = matches[0]
    assert route["disposition"]
    assert route["coverage_status"] in {
        "promotion_blocker",
        "shadow_observed",
        "coverage_unqualified",
    }


def test_c_sh3_cc2_raw_collection_handle_bypass_unqualified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH3 / CC-2: raw handle bypass is coverage-unqualified."""
    boundary, source, _ = _prepare(tmp_path, monkeypatch, mode="shadow")
    coord = IncrementalJsonlCoordinator(boundary, source)
    observed: list[tuple[str, str]] = []

    def spy(collection: str, operation: str, _kwargs) -> None:  # type: ignore[no-untyped-def]
        observed.append((collection, operation))

    register_coverage_spy(spy)
    shadow_session = None
    try:
        with coord._session() as session:
            with shadow_proof_attempt(
                mode="shadow",
                state_dir=coord.state_dir,
                transaction_id="tx-bypass",
                source_path=coord.path_key,
                source_identity=coord.source_id,
                generation="gen",
                prepared=[],
                store=session.store,
                chroma_dir=str(session.store.chroma_dir),
                coordinator_revision=coord.coordinator_implementation_revision,
            ) as shadow_session:
                assert shadow_session is not None
                handle = session.store._collection(UNITS)
                original_add = handle.add

                def instrumented_add(**kwargs):  # type: ignore[no-untyped-def]
                    _notify_coverage(UNITS, "add", kwargs)
                    spy(UNITS, "add", kwargs)
                    return original_add(**kwargs)

                handle.add = instrumented_add
                handle.add(
                    ids=["foreign-bypass"],
                    documents=["x"],
                    metadatas=[{"source_path": "other"}],
                )
                shadow_session.finalize(full_result="equal")
    finally:
        clear_coverage_spies()
    assert shadow_session is not None
    assert observed
    assert shadow_session.coverage_unqualified


def test_cc2_thread_mismatch_marks_coverage_unqualified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CC-2: cross-thread native observation is coverage-unqualified."""
    boundary, source, _ = _prepare(tmp_path, monkeypatch, mode="shadow")
    coord = IncrementalJsonlCoordinator(boundary, source)
    shadow_session = None
    with coord._session() as session:
        with shadow_proof_attempt(
            mode="shadow",
            state_dir=coord.state_dir,
            transaction_id="tx-thread",
            source_path=coord.path_key,
            source_identity=coord.source_id,
            generation="gen",
            prepared=[],
            store=session.store,
            chroma_dir=str(session.store.chroma_dir),
            coordinator_revision=coord.coordinator_implementation_revision,
        ) as shadow_session:
            assert shadow_session is not None
            with mock.patch(
                "incremental_mutation_proof.threading.get_ident",
                return_value=shadow_session.context.bound_thread + 1,
            ):
                shadow_session.on_native_before(UNITS, "delete", ids=["x"])
            shadow_session.finalize(full_result="equal")
    assert shadow_session is not None
    assert shadow_session.coverage_unqualified


def test_c_sh4_fc1_restart_ignores_shadow_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH4 / FC-1: forged shadow receipts do not change recovery authority."""
    boundary, source, _ = _prepare(tmp_path, monkeypatch, mode="shadow")
    coord = IncrementalJsonlCoordinator(boundary, source)
    coord.run()
    checkpoint_before = (coord.state_dir / "checkpoint.json").read_bytes()
    receipt = next((coord.state_dir / "scoped-shadow").rglob("*.jsonl"))
    extra = json.dumps({"record_kind": "terminal", "comparison": "observed_agreement"})
    forged = receipt.read_text(encoding="utf-8") + extra + "\n"
    receipt.write_text(forged, encoding="utf-8")
    replay = IncrementalJsonlCoordinator(boundary, source)
    result = replay.run()
    checkpoint_after = (replay.state_dir / "checkpoint.json").read_bytes()
    assert result.outcome in {"committed", "excluded_after_checkpoint", "unchanged"}
    assert checkpoint_before == checkpoint_after
    assert load_terminal_record(receipt) is not None


def test_c_sh5_tc1_must_fail_controls_red_then_green() -> None:
    """C-SH5 / TC-1: must-fail controls are red under broken policy, green when fixed."""
    set_test_policy_allow_all(True)
    broken = evaluate_call_policy(
        collection=UNITS,
        operation="delete",
        kwargs={"ids": ["foreign"]},
        context=type(
            "Ctx",
            (),
            {
                "collection_names": (SUMMARIES, UNITS),
                "source_path": "/src",
                "owned_summary_ids": frozenset(),
                "owned_unit_ids": frozenset(),
                "authorized_summary_ids": frozenset(),
                "authorized_unit_ids": frozenset(),
            },
        )(),
        store=object(),
    )
    assert broken.disposition == "allow"
    set_test_policy_allow_all(False)
    fixed = evaluate_call_policy(
        collection=UNITS,
        operation="delete",
        kwargs={"ids": ["foreign"]},
        context=type(
            "Ctx",
            (),
            {
                "collection_names": (SUMMARIES, UNITS),
                "source_path": "/src",
                "owned_summary_ids": frozenset(),
                "owned_unit_ids": frozenset(),
                "authorized_summary_ids": frozenset(),
                "authorized_unit_ids": frozenset(),
            },
        )(),
        store=type(
            "S",
            (),
            {"_collection": lambda *_a, **_k: None, "get_unit": lambda *_a, **_k: None},
        )(),
    )
    assert fixed.disposition == "would_deny"


def test_tc1_receipt_completeness_red_then_green(tmp_path: Path) -> None:
    """TC-1: receipt completeness control fails without terminal, passes with one."""
    path = tmp_path / "receipt.jsonl"
    assert receipts_complete(path) is False
    path.write_text(
        json.dumps({"record_kind": "terminal", "comparison": "observed_agreement"}) + "\n",
        encoding="utf-8",
    )
    assert receipts_complete(path) is True


def test_tc2_hermetic_child_network_denied_shadow_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-2: shadow commit runs in network-denied disposable child with fake providers."""
    boundary, source, env = _prepare(tmp_path, monkeypatch, mode="shadow")
    probe = subprocess.run(
        [sys.executable, "-I", str(WORKER), "probe", str(source)],
        cwd=boundary.root,
        env=env,
        close_fds=True,
        start_new_session=True,
        check=True,
        capture_output=True,
        text=True,
    )
    evidence = json.loads(probe.stdout)
    assert evidence["network"] == "IsolationViolation"
    assert evidence["watcher"] == "IsolationViolation"
    assert evidence["credential_names"] == []
    completed = worker_run(boundary, env, source)
    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["run"]["outcome"] == "committed"
    state_root = boundary.layout["state"]
    assert any(Path(state_root).rglob("scoped-shadow"))


def test_tc3_no_envelope_externalization_in_shadow_slice() -> None:
    """TC-3: diagnostic slice does not introduce envelope side store or hash redefinition."""
    module = ROOT / "incremental_mutation_proof.py"
    text = module.read_text(encoding="utf-8")
    assert DIAGNOSTIC_SCHEMA == "scoped_writes_shadow_v1"
    assert POLICY_ID == "scoped_writes_v1"
    forbidden = (
        "envelope_side_store",
        "reference_format_v",
        "provenance_hash_redefinition",
        "externalize_envelope",
    )
    lowered = text.lower()
    for token in forbidden:
        assert token not in lowered
    assert "envelope_side_store" not in lowered


def test_c_sh6_mc1_observer_timing_not_double_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH6 / MC-1: observer timing is a separate span and event field."""
    boundary, source, _ = _prepare(tmp_path, monkeypatch, mode="shadow")
    coord = IncrementalJsonlCoordinator(boundary, source)
    stderr_buf = io.StringIO()
    with redirect_stderr(stderr_buf):
        result = coord.run()
    assert result.outcome in {"committed", "excluded_after_checkpoint", "unchanged"}
    events = _timing_events(stderr_buf.getvalue())
    timing = [event for event in events if event.get("event") == "incremental_commit_phase_timing"]
    shadow_events = [
        event for event in events if event.get("event") == "incremental_scoped_proof_shadow"
    ]
    assert timing
    assert shadow_events
    phases = timing[-1]["phases"]
    assert "scoped_proof_observer" in phases
    assert "observer_seconds" in shadow_events[-1]
    observer_phase = float(phases["scoped_proof_observer"])
    assert observer_phase >= 0.0
    receipt = next((coord.state_dir / "scoped-shadow").rglob("*.jsonl"), None)
    assert receipt is not None
    terminal = load_terminal_record(receipt)
    assert terminal is not None
    assert "observer_seconds" in terminal


def test_classify_scoped_shadow_subtree() -> None:
    cls = classify_scoped_shadow_diagnostic("/data/incremental/foo/scoped-shadow/tx/a.jsonl")
    assert cls is not None
    assert cls.outcome == OUTCOME_ADVISORY


def test_comparison_matrix_detection_gap() -> None:
    assert classify_comparison("changed", "observed_compliant") == "detection_gap"


def test_receipt_completeness_requires_terminal() -> None:
    assert extract_target_ids({"ids": ["a"]}) == ("a",)
    assert receipts_complete(Path("/does/not/exist")) is False
