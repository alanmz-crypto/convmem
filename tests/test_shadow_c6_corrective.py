# pylint: disable=duplicate-code
"""C6 corrective: oversize refusal, payload-free evidence, seed containment."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from event_size_evidence import (
    BoundedSizeHistogram,
    EventSizeBinding,
    EventSizeEvidenceRefused,
    MAX_RETAINED_OBSERVATIONS,
    MUTATION_CLASSES,
    STRUCTURAL_SHAPE_MATRIX,
    _benchmark_runtime,
    _execute_mutation,
    _production_mutation_once,
    _run_mode_samples,
    benchmark_control_bypass,
    benchmark_session_active,
    build_workload_spec,
    conservative_writer_concurrency_from_inventory,
    create_benchmark_fixture,
    finalize_session_companion,
    inertness_snapshot,
    is_companion_armed,
    open_event_size_companion,
    reset_inertness_counters,
    run_benchmark_cell,
    run_hermetic_overhead_benchmark,
    run_memory_exercise,
    run_multiprocess_concurrency_cell,
    validate_binding_against_report,
)
from shadow_authorization import ensure_private_directory
from shadow_canary import CanaryRefused, validate_seed_ledger_target
from shadow_ledger import (
    SHADOW_DIR_MODE,
    create_shadow_ledger_header,
    maximum_supported_event_bytes,
    open_existing_shadow_ledger_fd,
    read_ledger_header_and_tail,
)
from shadow_sink import JsonlUnitMutationSink, build_mutation_event, encode_event_line
from writer_census import HEADER_NAME, start_writer_census

DOCUMENT_SENTINEL = "C6_OVERSIZE_PRIVACY_DOCUMENT_SENTINEL"
ENTITY_SENTINEL = "C6_OVERSIZE_PRIVACY_ENTITY_SENTINEL"
META_SENTINEL = "C6_OVERSIZE_PRIVACY_META_SENTINEL"

FIXED_NOW = datetime(2026, 7, 29, 14, 0, tzinfo=timezone.utc)


class _FixedDatetime:
    @staticmethod
    def now(tz=None) -> datetime:
        return FIXED_NOW if tz is None else FIXED_NOW.astimezone(tz)


@pytest.fixture
def fixed_event_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stabilize recorded_at so encoded event sizes are deterministic."""
    monkeypatch.setattr("shadow_sink.datetime", _FixedDatetime)


def _shadow(tmp_path: Path) -> Path:
    shadow = tmp_path / "shadow"
    shadow.mkdir(parents=True, exist_ok=True)
    os.chmod(shadow, SHADOW_DIR_MODE)
    return shadow


def _header_ledger(
    tmp_path: Path, **kwargs: Any,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    shadow = _shadow(tmp_path)
    ledger = shadow / "ledger.jsonl"
    health = shadow / "health.json"
    header = create_shadow_ledger_header(
        ledger,
        activation_id=kwargs.get("activation_id", "act-1"),
        ledger_identity=kwargs.get("ledger_identity", "ledger-1"),
        starting_sequence=kwargs.get("starting_sequence", 0),
        hooks=kwargs.get("hooks"),
    )
    return shadow, ledger, health, header


def _events(ledger: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get("record_type") == "ledger_header":
            continue
        out.append(obj)
    return out


def _append_encoded_size(
    *,
    document: str,
    sequence: int,
    event_id: str,
    stable_entity_id: str,
    metadata: dict[str, Any],
    writer_route: str,
    operation: str = "replace",
) -> int:
    """Mirror observe → sequence assign → encode_event_line sizing."""
    event = build_mutation_event(
        event_id=event_id,
        sequence=None,
        operation=operation,
        stable_entity_id=stable_entity_id,
        document=document,
        metadata=metadata,
        deleted=False,
        writer_route=writer_route,
    )
    event["sequence"] = sequence
    return len(encode_event_line(event))


def _document_for_append_byte_size(
    target_bytes: int,
    *,
    sequence: int,
    event_id: str,
    stable_entity_id: str,
    metadata: dict[str, Any],
    writer_route: str,
    operation: str = "replace",
) -> str:
    """Brute-force document length for an exact post-sequence encoded size."""
    low, high = 0, target_bytes * 2
    while low < high:
        mid = (low + high) // 2
        if _append_encoded_size(
            document="x" * mid,
            sequence=sequence,
            event_id=event_id,
            stable_entity_id=stable_entity_id,
            metadata=metadata,
            writer_route=writer_route,
            operation=operation,
        ) < target_bytes:
            low = mid + 1
        else:
            high = mid
    doc = "x" * low
    size = _append_encoded_size(
        document=doc,
        sequence=sequence,
        event_id=event_id,
        stable_entity_id=stable_entity_id,
        metadata=metadata,
        writer_route=writer_route,
        operation=operation,
    )
    if size != target_bytes:
        pytest.fail(f"could not synthesize {target_bytes} bytes (got {size})")
    return doc


def _oversize_observe(
    sink: JsonlUnitMutationSink,
    *,
    document: str,
    stable_entity_id: str = ENTITY_SENTINEL,
    metadata: dict[str, Any] | None = None,
    event_id: str = "e-oversize",
) -> None:
    sink.observe(
        event_id=event_id,
        operation="replace",
        stable_entity_id=stable_entity_id,
        document=document,
        metadata=metadata or {META_SENTINEL: "value", "kind": "test"},
        deleted=False,
        writer_route="test.oversize",
    )


def _at(day: int, hour: int = 12) -> datetime:
    return datetime(2030, 1, day, hour, tzinfo=timezone.utc)


def _start_census(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, armed: bool,
) -> Path:
    monkeypatch.setattr(
        "chroma_write_store.current_code_revision", lambda: "c6-revision",
    )
    directory = tmp_path / "census"
    chroma = tmp_path / "chroma"
    gate = tmp_path / "gate.lock"
    chroma.mkdir()
    start_writer_census(
        census_dir=directory,
        chroma_root=chroma,
        writer_gate_path=gate,
        now=_at(1),
    )
    if armed:
        header_path = directory / HEADER_NAME
        header = json.loads(header_path.read_text(encoding="utf-8"))
        header["event_size_evidence_armed"] = True
        header_path.write_text(
            json.dumps(header, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
    return directory


def test_maximum_supported_event_bytes_is_tail_derived() -> None:
    assert maximum_supported_event_bytes() == 131071


def test_boundary_accept_then_refuse_preserves_ledger_and_allows_recovery(
    tmp_path: Path, fixed_event_clock: None,
) -> None:
    maximum = maximum_supported_event_bytes()
    boundary_meta = {"kind": "test"}
    accept_doc = _document_for_append_byte_size(
        maximum,
        sequence=1,
        event_id="e-boundary-ok",
        stable_entity_id="u1",
        metadata=boundary_meta,
        writer_route="test.boundary",
    )
    refuse_doc = _document_for_append_byte_size(
        maximum + 1,
        sequence=1,
        event_id="e-boundary-refuse",
        stable_entity_id="u2",
        metadata=boundary_meta,
        writer_route="test.boundary",
    )

    _shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)

    sink.observe(
        event_id="e-boundary-ok",
        operation="replace",
        stable_entity_id="u1",
        document=accept_doc,
        metadata={"kind": "test"},
        deleted=False,
        writer_route="test.boundary",
    )
    ledger_after_accept = ledger.read_bytes()
    assert len(_events(ledger)) == 1
    assert _events(ledger)[0]["sequence"] == 1

    sink.observe(
        event_id="e-boundary-refuse",
        operation="replace",
        stable_entity_id="u2",
        document=refuse_doc,
        metadata={"kind": "test"},
        deleted=False,
        writer_route="test.boundary",
    )
    assert ledger.read_bytes() == ledger_after_accept
    health_after_refuse = json.loads(health.read_text(encoding="utf-8"))
    assert health_after_refuse["last_failure_class"] == "event_too_large"
    assert health_after_refuse["last_oversize_attempted_bytes"] == maximum + 1
    assert health_after_refuse["last_oversize_max_bytes"] == maximum

    sink.observe(
        event_id="e-recover",
        operation="replace",
        stable_entity_id="u3",
        document="small",
        metadata={"kind": "test"},
        deleted=False,
        writer_route="test.boundary",
    )
    events = _events(ledger)
    assert len(events) == 2
    assert events[1]["sequence"] == 2

    health_obj = json.loads(health.read_text(encoding="utf-8"))
    assert health_obj.get("last_failure_class") is None
    assert "document" not in health_obj
    assert "post_state" not in health_obj
    assert "stable_entity_id" not in health_obj


def test_oversize_path_never_leaks_privacy_sentinels(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, fixed_event_clock: None,
) -> None:
    refuse_doc = _document_for_append_byte_size(
        maximum_supported_event_bytes() + 1,
        sequence=1,
        event_id="event-oversize",
        stable_entity_id="u1",
        metadata={"kind": "test"},
        writer_route="test.first-event-too-large",
    )
    _shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)

    with caplog.at_level(logging.DEBUG, logger="shadow_sink"):
        _oversize_observe(
            sink,
            document=DOCUMENT_SENTINEL + refuse_doc,
            stable_entity_id=ENTITY_SENTINEL,
            metadata={META_SENTINEL: "meta", "kind": "test"},
        )

    ledger_text = ledger.read_text(encoding="utf-8")
    health_text = health.read_text(encoding="utf-8")
    log_blob = caplog.text
    for sentinel in (DOCUMENT_SENTINEL, ENTITY_SENTINEL, META_SENTINEL):
        assert sentinel not in ledger_text
        assert sentinel not in health_text
        assert sentinel not in log_blob


def test_validate_binding_against_report_refuses_mismatch() -> None:
    binding = EventSizeBinding(
        census_id="census-a",
        window_start_utc="2030-01-02T00:00:00Z",
        window_end_utc="2030-01-09T00:00:00Z",
        code_revision="c6-revision",
        writer_gate_protocol=1,
        chroma_root_identity="chroma-a",
        writer_gate_identity="gate-a",
    )
    report = {
        "census_id": "census-b",
        "window_start_utc": binding.window_start_utc,
        "window_end_utc": binding.window_end_utc,
        "code_revision": binding.code_revision,
        "writer_gate_protocol": binding.writer_gate_protocol,
        "chroma_root_identity": binding.chroma_root_identity,
        "writer_gate_identity": binding.writer_gate_identity,
    }
    with pytest.raises(EventSizeEvidenceRefused, match="binding_mismatch"):
        validate_binding_against_report(binding, report)


def test_histogram_overflow_counts_beyond_retention_cap() -> None:
    histogram = BoundedSizeHistogram()
    for _ in range(MAX_RETAINED_OBSERVATIONS):
        histogram.observe(128)
    histogram.observe(256)
    payload = histogram.as_dict()
    assert payload["total_observations"] == MAX_RETAINED_OBSERVATIONS
    assert payload["overflow"] == 1


def test_is_companion_armed_false_when_unarmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = _start_census(tmp_path, monkeypatch, armed=False)
    reset_inertness_counters()
    assert is_companion_armed(directory) is False
    assert open_event_size_companion(
        census_dir=directory, session_nonce="nonce", now=_at(2),
    ) is None
    assert inertness_snapshot()["encoder_calls"] == 0


def test_validate_seed_ledger_target_refuses_production_chroma_overlap(
    tmp_path: Path,
) -> None:
    scratch = ensure_private_directory(tmp_path / "scratch")
    chroma = scratch / "chroma"
    chroma.mkdir()
    ledger = chroma / "ledger.jsonl"
    with pytest.raises(CanaryRefused, match="canary_live_path"):
        validate_seed_ledger_target(
            ledger,
            scratch_root=scratch,
            production_chroma_root=chroma,
        )


def test_first_event_too_large_rolls_back_activation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fixed_event_clock: None,
) -> None:
    import shadow_activation
    from tests.test_shadow_activation import _activate, _fixture, _hooks

    real_read_health = shadow_activation._read_shadow_health_failure_class

    def read_health_when_present(health_path: Path) -> str | None:
        if not health_path.is_file():
            return None
        return real_read_health(health_path)

    monkeypatch.setattr(
        shadow_activation,
        "_read_shadow_health_failure_class",
        read_health_when_present,
    )

    fixture = _fixture(tmp_path)
    refuse_doc = _document_for_append_byte_size(
        maximum_supported_event_bytes() + 1,
        sequence=1,
        event_id="event-oversize",
        stable_entity_id="u1",
        metadata={"kind": "test"},
        writer_route="test.first-event-too-large",
    )
    appended = {"done": False}

    def append_oversize(_seconds: float) -> None:
        if appended["done"]:
            return
        appended["done"] = True
        JsonlUnitMutationSink(
            ledger_path=fixture["ledger"], health_path=fixture["health"],
        ).observe(
            event_id="event-oversize",
            operation="replace",
            stable_entity_id="u1",
            document=refuse_doc,
            metadata={"kind": "test"},
            deleted=False,
            writer_route="test.first-event-too-large",
        )

    outcome = _activate(fixture, _hooks(sleep=append_oversize))
    assert outcome.refusal_code == "first_event_too_large"
    assert outcome.state == "disabled_after_rollback"
    assert __import__("config").load_config(fixture["config"])["shadow_ledger"]["enabled"] is False


def test_run_benchmark_cell_control_mode(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    marker = scratch / "marker.txt"
    calls = {"n": 0}

    def touch_marker() -> None:
        calls["n"] += 1
        marker.write_text(str(calls["n"]), encoding="utf-8")

    result = run_benchmark_cell(
        mode="control",
        mutation_class="noop",
        structural_shape="touch",
        operation=touch_marker,
        sample_count=20,
        warmup_count=5,
    )
    assert result.mode == "control"
    assert result.sample_count == 20
    assert result.errors == 0
    assert calls["n"] == 25
    assert marker.read_text(encoding="utf-8") == "25"


def test_append_path_encodes_event_line_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _shadow, ledger, health, _ = _header_ledger(tmp_path)
    sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    calls = {"n": 0}
    real_encode = encode_event_line

    def counted_encode(event: Any) -> bytes:
        calls["n"] += 1
        return real_encode(event)

    monkeypatch.setattr("shadow_sink.encode_event_line", counted_encode)
    sink.observe(
        event_id="e-once",
        operation="replace",
        stable_entity_id="u1",
        document="small payload",
        metadata={"kind": "test"},
        deleted=False,
        writer_route="test.encode-once",
    )
    assert calls["n"] == 1
    assert len(_events(ledger)) == 1


def test_seed_synthetic_ledger_requires_scratch_containment(tmp_path: Path) -> None:
    from shadow_canary import seed_synthetic_ledger

    scratch = ensure_private_directory(tmp_path / "scratch")
    ledger = scratch / "ledger.jsonl"
    create_shadow_ledger_header(
        ledger,
        activation_id="canary",
        ledger_identity="identity",
        starting_sequence=0,
    )
    seed_synthetic_ledger(ledger, 2, scratch_root=scratch)
    fd, dir_fd, _st = open_existing_shadow_ledger_fd(ledger)
    try:
        tail = read_ledger_header_and_tail(fd)
    finally:
        os.close(fd)
        os.close(dir_fd)
    assert tail.next_sequence == 3


def test_c7_close_suppressed_when_companion_finalize_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = _start_census(tmp_path, monkeypatch, armed=True)
    companion = open_event_size_companion(
        census_dir=directory,
        session_nonce="session-nonce-sticky",
        now=_at(2),
    )
    assert companion is not None
    companion.record_measurement_gap(reason="sticky_test_failure")
    assert finalize_session_companion() is False

    from writer_census import EVENTS_NAME

    gate = tmp_path / "gate.lock"
    attest = tmp_path / "attest"
    from chroma_write_store import shared_writer_lease

    with shared_writer_lease(
        lock_path=gate,
        attest_dir=attest,
        census_dir=directory,
        entrypoint="convmem.add",
    ) as att:
        active = open_event_size_companion(
            census_dir=directory,
            session_nonce="session-nonce-lease",
            now=_at(2),
        )
        assert active is not None
        active.record_measurement_gap(reason="lease_sticky_failure")

    events = (directory / EVENTS_NAME).read_text(encoding="utf-8").splitlines()
    assert len(events) == 1
    assert json.loads(events[0])["event"] == "open"
    assert att.entrypoint == "convmem.add"


def test_concurrent_valid_and_oversize_writers(
    tmp_path: Path, fixed_event_clock: None,
) -> None:
    import threading

    maximum = maximum_supported_event_bytes()
    refuse_doc = _document_for_append_byte_size(
        maximum + 1,
        sequence=1,
        event_id="e-oversize-concurrent",
        stable_entity_id="u-oversize",
        metadata={"kind": "test"},
        writer_route="test.concurrent.oversize",
    )
    _shadow, ledger, health, _ = _header_ledger(tmp_path)
    valid_sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    oversize_sink = JsonlUnitMutationSink(ledger_path=ledger, health_path=health)
    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def append_valid() -> None:
        try:
            barrier.wait()
            valid_sink.observe(
                event_id="e-valid-concurrent",
                operation="replace",
                stable_entity_id="u-valid",
                document="valid-payload",
                metadata={"kind": "test"},
                deleted=False,
                writer_route="test.concurrent.valid",
            )
        except BaseException as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    def append_oversize() -> None:
        try:
            barrier.wait()
            oversize_sink.observe(
                event_id="e-oversize-concurrent",
                operation="replace",
                stable_entity_id="u-oversize",
                document=refuse_doc,
                metadata={"kind": "test"},
                deleted=False,
                writer_route="test.concurrent.oversize",
            )
        except BaseException as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    threads = [
        threading.Thread(target=append_valid),
        threading.Thread(target=append_oversize),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors

    events = _events(ledger)
    assert len(events) == 1
    assert events[0]["event_id"] == "e-valid-concurrent"
    assert events[0]["sequence"] == 1

    fd, dir_fd, _st = open_existing_shadow_ledger_fd(ledger)
    try:
        tail = read_ledger_header_and_tail(fd)
    finally:
        os.close(fd)
        os.close(dir_fd)
    assert tail.next_sequence == 2

    health_obj = json.loads(health.read_text(encoding="utf-8"))
    assert health_obj.get("last_failure_class") in {None, "event_too_large"}


def test_companion_init_failure_blocks_armed_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = _start_census(tmp_path, monkeypatch, armed=True)
    header_path = directory / HEADER_NAME
    header = json.loads(header_path.read_text(encoding="utf-8"))
    header["window_end_utc"] = "2030-01-01T00:00:00Z"
    header_path.write_text(
        json.dumps(header, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )

    with pytest.raises(EventSizeEvidenceRefused, match="census_window_closed"):
        open_event_size_companion(
            census_dir=directory,
            session_nonce="closed-window",
            now=_at(9),
        )

    lease_root = tmp_path / "lease"
    lease_root.mkdir()
    lease_directory = _start_census(lease_root, monkeypatch, armed=True)
    gate = lease_root / "gate.lock"
    attest = lease_root / "attest"

    def refuse_companion_open(**kwargs: Any) -> None:
        raise EventSizeEvidenceRefused(
            "census_window_closed", "cannot open companion after window end",
        )

    monkeypatch.setattr(
        "event_size_evidence.open_event_size_companion", refuse_companion_open,
    )
    from chroma_write_store import shared_writer_lease

    with pytest.raises(EventSizeEvidenceRefused, match="census_window_closed"):
        with shared_writer_lease(
            lock_path=gate,
            attest_dir=attest,
            census_dir=lease_directory,
            entrypoint="convmem.add",
        ):
            pass


def test_measure_encoded_size_hermetic(tmp_path: Path) -> None:
    from event_size_evidence import SUMMARY_NAME, measure_encoded_size

    measure_sentinel = "C6_MEASURE_SIZE_SENTINEL"
    reset_inertness_counters()
    size = measure_encoded_size(
        operation="replace",
        document=measure_sentinel + "payload",
        metadata={META_SENTINEL: "meta"},
        deleted=False,
    )
    assert isinstance(size, int)
    assert size > 0

    snapshot = inertness_snapshot()
    assert snapshot["encoder_calls"] == 1
    assert snapshot["retained_observations"] == 0
    assert snapshot["evidence_io_ops"] == 0

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    for path in scratch.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert measure_sentinel not in text
            assert META_SENTINEL not in text
    assert not (scratch / SUMMARY_NAME).exists()


def test_hermetic_overhead_benchmark_mini(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")

    report = run_hermetic_overhead_benchmark(
        root=tmp_path / "bench",
        steady_samples=2,
        warmup_samples=1,
        h_events=100,
        matrix=(("create", "small_1k"), ("delete", "small_1k")),
        session_kinds=("context_short", "manual_short"),
        run_count=3,
    )
    assert report.verdict == "MEASURED"
    assert report.runs == 3
    assert len(report.comparisons) > 0
    assert report.concurrency_level >= 1
    assert conservative_writer_concurrency_from_inventory() >= 1


def test_structural_shape_matrix_covers_all_operations() -> None:
    assert set(m for m, _ in STRUCTURAL_SHAPE_MATRIX) == set(MUTATION_CLASSES)


def test_all_six_operations_use_production_emit_path(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    fixture = create_benchmark_fixture(tmp_path / "armed")
    _benchmark_runtime.session_active = True
    try:
        for mutation_class in MUTATION_CLASSES:
            spec = build_workload_spec(
                mutation_class=mutation_class,
                structural_shape="small_1k",
                seed=42,
            )
            result = _run_mode_samples(
                fixture,
                mode="armed",
                spec=spec,
                session_kind="context_short",
                sample_count=1,
                warmup_count=0,
            )
            assert result.encoder_calls > 0, mutation_class
    finally:
        _benchmark_runtime.session_active = False
        _benchmark_runtime.control_bypass = False


def test_control_bypass_unreachable_outside_benchmark() -> None:
    assert not benchmark_session_active()
    with pytest.raises(
        EventSizeEvidenceRefused, match="benchmark_control_bypass_forbidden"
    ):
        with benchmark_control_bypass():
            pass


def test_three_modes_share_same_workload_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("chromadb")
    fixture = create_benchmark_fixture(tmp_path / "modes")
    spec = build_workload_spec(
        mutation_class="replace",
        structural_shape="small_1k",
        seed=1,
    )
    calls: list[tuple[str, str, str]] = []
    real_execute = _execute_mutation
    current_mode = {"value": ""}

    def tracked_execute(store: Any, workload: Any) -> int:
        calls.append((current_mode["value"], workload.mutation_class, workload.structural_shape))
        return real_execute(store, workload)

    monkeypatch.setattr("event_size_evidence._execute_mutation", tracked_execute)
    _benchmark_runtime.session_active = True
    try:
        for mode in ("control", "unarmed", "armed"):
            current_mode["value"] = mode
            reset_inertness_counters()
            _production_mutation_once(
                fixture,
                mode=mode,
                spec=spec,
                session_kind="context_short",
            )
    finally:
        _benchmark_runtime.session_active = False
        _benchmark_runtime.control_bypass = False

    assert len(calls) == 3
    assert all(
        mutation_class == spec.mutation_class and shape == spec.structural_shape
        for _mode, mutation_class, shape in calls
    )


def test_multiprocess_writer_lease_concurrency(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    fixture = create_benchmark_fixture(tmp_path / "mp")
    errors, _results = run_multiprocess_concurrency_cell(fixture, concurrency=2)
    assert errors == 0


def test_long_and_short_session_kinds_exercised(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    report = run_hermetic_overhead_benchmark(
        root=tmp_path / "sessions",
        steady_samples=1,
        warmup_samples=0,
        h_events=10,
        matrix=(("create", "small_1k"),),
        session_kinds=("context_long", "manual_short"),
        run_count=1,
    )
    kinds = {cell.session_kind for cell in report.cells}
    assert "context_long" in kinds
    assert "manual_short" in kinds


def test_unarmed_hot_path_zero_encoder_calls(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    fixture = create_benchmark_fixture(tmp_path / "unarmed")
    spec = build_workload_spec(
        mutation_class="replace",
        structural_shape="small_1k",
        seed=1,
    )
    _benchmark_runtime.session_active = True
    try:
        result = _run_mode_samples(
            fixture,
            mode="unarmed",
            spec=spec,
            session_kind="context_short",
            sample_count=3,
            warmup_count=0,
        )
        assert result.encoder_calls == 0
    finally:
        _benchmark_runtime.session_active = False
        _benchmark_runtime.control_bypass = False


@pytest.mark.slow
def test_memory_exercise_50000_bounded(tmp_path: Path) -> None:
    pytest.importorskip("chromadb")
    fixture = create_benchmark_fixture(tmp_path / "memory")
    overflow, retained, _rss = run_memory_exercise(fixture, h_events=50_000)
    assert retained <= MAX_RETAINED_OBSERVATIONS
    assert overflow >= 0
