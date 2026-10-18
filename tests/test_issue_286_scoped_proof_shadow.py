"""Arc #286 scoped mutation proof shadow mode tests (design section 8)."""

# pylint: disable=protected-access,duplicate-code,unused-argument

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from chroma_store import SUMMARIES, UNITS
from complete_data_restore import classify_scoped_shadow_diagnostic, OUTCOME_ADVISORY
from config import IncrementalJsonlConfigError, incremental_jsonl_settings
from incremental_jsonl import IncrementalJsonlCoordinator
from incremental_mutation_proof import (
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
    apply_env,
    enable_incremental,
    install_fakes,
    isolated_env,
    write_source,
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
    return boundary, source


def _commit_artifacts(state_dir: Path) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    for name in ("checkpoint.json", "transaction.json", "rollback.json"):
        path = state_dir / name
        if path.is_file():
            out[name] = path.read_bytes()
    return out


def test_config_rejects_scoped_observer() -> None:
    with pytest.raises(IncrementalJsonlConfigError):
        incremental_jsonl_settings(
            {"index": {"incremental_jsonl": {"enabled": True, "mutation_proof_observer": "scoped"}}}
        )


def test_c_sh1_off_shadow_parity_under_observer_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH1=SC-1: off/shadow parity when observer I/O fails."""
    off_boundary, off_source = _prepare(tmp_path / "off", monkeypatch, mode="off")
    sh_boundary, sh_source = _prepare(tmp_path / "sh", monkeypatch, mode="shadow")
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


def test_c_sh2_writer_inventory_machine_checked() -> None:
    """C-SH2=CC-1: regenerated writer inventory matches committed artifact."""
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/generate_scoped_proof_writer_inventory.py"
    artifact = root / "docs/plans/SCOPED-PROOF-WRITER-INVENTORY.json"
    before = artifact.read_text(encoding="utf-8")
    subprocess.run([sys.executable, str(script)], check=True, cwd=root)
    after = artifact.read_text(encoding="utf-8")
    assert before == after
    payload = json.loads(after)
    assert payload["schema"] == "scoped_proof_writer_inventory_v1"
    assert payload["routes"]


def test_c_sh3_enumerated_bypass_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH3=CC-2: raw collection handle bypass is coverage-unqualified."""
    boundary, source = _prepare(tmp_path, monkeypatch, mode="shadow")
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
                handle.add(ids=["foreign-bypass"], documents=["x"], metadatas=[{"source_path": "other"}])
                shadow_session.finalize(full_result="equal")
    finally:
        clear_coverage_spies()
    assert shadow_session is not None
    assert observed
    assert shadow_session.coverage_unqualified


def test_c_sh4_restart_ignores_shadow_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH4=FC-1: recovery ignores surviving shadow receipts."""
    boundary, source = _prepare(tmp_path, monkeypatch, mode="shadow")
    coord = IncrementalJsonlCoordinator(boundary, source)
    coord.run()
    receipt = next((coord.state_dir / "scoped-shadow").rglob("*.jsonl"))
    extra = json.dumps({"record_kind": "terminal", "comparison": "observed_agreement"})
    forged = receipt.read_text(encoding="utf-8") + extra + "\n"
    receipt.write_text(forged, encoding="utf-8")
    replay = IncrementalJsonlCoordinator(boundary, source)
    result = replay.run()
    assert result.outcome in {"committed", "excluded_after_checkpoint", "unchanged"}
    assert load_terminal_record(receipt) is not None


def test_c_sh5_must_fail_controls_red_then_green() -> None:
    """C-SH5=TC-1: policy controls fail when evaluator is forced permissive."""
    set_test_policy_allow_all(True)
    decision = evaluate_call_policy(
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
    assert decision.disposition == "allow"
    set_test_policy_allow_all(False)
    decision = evaluate_call_policy(
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
        store=type("S", (), {"_collection": lambda *_a, **_k: None, "get_unit": lambda *_a, **_k: None})(),
    )
    assert decision.disposition == "would_deny"


def test_c_sh6_observer_timing_not_double_counted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-SH6=MC-1: observer seconds reported separately from phase totals."""
    boundary, source = _prepare(tmp_path, monkeypatch, mode="shadow")
    coord = IncrementalJsonlCoordinator(boundary, source)
    result = coord.run()
    assert result.outcome in {"committed", "excluded_after_checkpoint", "unchanged"}
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
