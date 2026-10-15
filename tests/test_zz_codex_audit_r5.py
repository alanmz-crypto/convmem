"""Codex audit round-5 probes (issue #286 corrective 19)."""

# pylint: disable=protected-access

from __future__ import annotations

import dataclasses
import fcntl
import json
import os
from pathlib import Path

import pytest

from tests.test_zz_codex_audit import _route_fixture
from tests.test_zz_claude_verify8b import _count_summaries


def _state_root(source, cfg):
    import incremental_jsonl as inc

    return Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / inc.source_state_id(
        str(source.resolve()), format_id="jsonl_codex_rollout"
    )


def _lock_held(path):
    fd = os.open(path, os.O_RDWR)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _call(route):
    import incremental_jsonl as inc

    try:
        return ("ok", route()[0])
    except inc.IncrementalJsonlError as exc:
        return ("raised", exc.code)


@pytest.mark.parametrize("kind", ["corrupt", "prefix_cap", "same_error", "source_hold"])
def test_unchanged_preserves_gate_refusal(tmp_path, monkeypatch, kind):
    import incremental_jsonl as inc
    from watch import source_prefix_digest_for_watch

    original_shortcut = getattr(
        inc.IncrementalJsonlCoordinator,
        "_unchanged_short_circuit_if_applicable",
        lambda self: None,
    )
    rows = []
    for shortcut in (False, True):
        with monkeypatch.context() as mp:
            source, cfg, route = _route_fixture(tmp_path / str(shortcut), mp)
            calls = _count_summaries(mp)
            route()
            root = _state_root(source, cfg)
            state = root / "retry_state.json"
            prefix = source_prefix_digest_for_watch(str(source))
            if kind == "corrupt":
                state.write_bytes(b"{truncated retry evidence\n")
            else:
                state.write_text(
                    json.dumps(
                        {
                            "source_path": str(source),
                            "prefix_digest": prefix,
                            "error_code": "artifact_write_failed",
                            "attempts_on_prefix": 3 if kind == "prefix_cap" else 0,
                            "consecutive": 2 if kind == "same_error" else 0,
                            "source_consecutive": 3 if kind == "source_hold" else 0,
                        }
                    )
                )
            before = state.read_bytes()
            paid = len(calls)
            mp.setattr(
                inc.IncrementalJsonlCoordinator,
                "_unchanged_short_circuit_if_applicable",
                original_shortcut if shortcut else lambda self: None,
                raising=False,
            )
            results = [_call(route) for _ in range(3)]
            rows.append(
                (
                    shortcut,
                    results,
                    len(calls) - paid,
                    state.exists() and state.read_bytes() == before,
                )
            )
    print("UNCHANGED_GATE", kind, rows)
    assert rows[0][1:] == rows[1][1:], (
        "shortcut bypassed full-path refusal and erased retry evidence"
    )


def test_natural_source_hold_survives_return_to_checkpoint(tmp_path, monkeypatch):
    import incremental_jsonl as inc

    original_shortcut = getattr(
        inc.IncrementalJsonlCoordinator,
        "_unchanged_short_circuit_if_applicable",
        lambda self: None,
    )
    rows = []
    for shortcut in (False, True):
        with monkeypatch.context() as mp:
            source, cfg, route = _route_fixture(tmp_path / str(shortcut), mp)
            calls = _count_summaries(mp)
            route()
            original_bytes = source.read_bytes()
            root = _state_root(source, cfg)
            state = root / "retry_state.json"
            for n in range(3):
                with source.open("ab") as fh:
                    fh.write(b'{"invalid":"\xff", "n":' + str(n).encode() + b"}\n")
                assert _call(route)[0] == "raised"
            assert json.loads(state.read_bytes())["source_consecutive"] == 3
            assert not (root / "transaction.json").exists()
            before = state.read_bytes()
            paid = len(calls)
            source.write_bytes(original_bytes)
            mp.setattr(
                inc.IncrementalJsonlCoordinator,
                "_unchanged_short_circuit_if_applicable",
                original_shortcut if shortcut else lambda self: None,
                raising=False,
            )
            result = _call(route)
            held = state.exists() and state.read_bytes() == before
            from tests.incremental_jsonl_helpers import codex_rollout_record

            with source.open("ab") as fh:
                fh.write(codex_rollout_record(100))
            next_result = _call(route)
            rows.append((shortcut, result, held, next_result, len(calls) - paid))
    print("NATURAL_HOLD", rows)
    assert rows[0][1:] == rows[1][1:], "real source-wide hold was silently cleared"


@pytest.mark.parametrize("mutation", ["truncate", "rewrite", "rotate"])
def test_shortcut_revalidates_source_after_read(tmp_path, monkeypatch, mutation):
    import incremental_jsonl as inc
    from incremental_jsonl_formats import FORMAT_SPECS

    original_spec = FORMAT_SPECS["jsonl_codex_rollout"]
    original_shortcut = getattr(
        inc.IncrementalJsonlCoordinator,
        "_unchanged_short_circuit_if_applicable",
        lambda self: None,
    )
    rows = []
    for shortcut in (False, True):
        with monkeypatch.context() as mp:
            source, cfg, route = _route_fixture(tmp_path / str(shortcut), mp)
            calls = _count_summaries(mp)
            route()
            paid = len(calls)
            mutated = []

            def parse(filepath, *, raw=None):
                view = original_spec.parse_complete_prefix(filepath, raw=raw)
                if not mutated:
                    mutated.append(True)
                    data = source.read_bytes()
                    if mutation == "truncate":
                        source.write_bytes(data.splitlines(keepends=True)[0])
                    elif mutation == "rewrite":
                        data = data.replace(b"line-0", b"line-X", 1)
                        if data == source.read_bytes():
                            split = data.index(b"\n") + 1
                            tail = bytearray(data[split:])
                            i = next(i for i, value in enumerate(tail) if value == ord("0"))
                            tail[i] = ord("9")
                            data = data[:split] + bytes(tail)
                        source.write_bytes(data)
                    else:
                        replacement = source.with_suffix(".replacement")
                        replacement.write_bytes(data)
                        replacement.replace(source)
                return view

            mp.setitem(
                FORMAT_SPECS,
                "jsonl_codex_rollout",
                dataclasses.replace(original_spec, parse_complete_prefix=parse),
            )
            mp.setattr(
                inc.IncrementalJsonlCoordinator,
                "_unchanged_short_circuit_if_applicable",
                original_shortcut if shortcut else lambda self: None,
                raising=False,
            )
            result = _call(route)
            state = _state_root(source, cfg) / "retry_state.json"
            rows.append((shortcut, result, len(calls) - paid, state.exists()))
            assert mutated
    print("SOURCE_RACE", mutation, rows)
    assert rows[0][1:] == rows[1][1:], (
        "shortcut acknowledged a prefix that failed source revalidation"
    )


def test_adapted_lock_sequence_has_correct_reservation_semantics(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import incremental_retry_state as retry

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    seen = []
    gate_original = retry.enforce_incremental_retry_gates
    live_check_original = inc.IncrementalJsonlCoordinator._check_live_retry_admission_if_needed
    capture_original = inc.IncrementalJsonlCoordinator._capture
    record_original = retry.record_incremental_retry_failure

    def live_check(self):
        assert _lock_held(self.paths["lock"])
        state = self.paths["transaction"].parent / "retry_state.json"
        prior = state.read_bytes() if state.exists() else None
        seen.append(("check",))
        live_check_original(self)
        assert (state.read_bytes() if state.exists() else None) == prior

    def gate(paths, **kw):
        assert _lock_held(paths["lock"])
        seen.append(("gate",))
        return gate_original(paths, **kw)

    def capture(self, *a, **kw):
        assert _lock_held(self.paths["lock"])
        seen.append(("capture",))
        return capture_original(self, *a, **kw)

    def fail(self, *a, **kw):
        assert _lock_held(self.paths["lock"])
        seen.append(("work",))
        raise OSError("scratch prepared failure")

    def record(paths, **kw):
        assert _lock_held(paths["lock"])
        seen.append(("account",))
        return record_original(paths, **kw)

    monkeypatch.setattr(
        inc.IncrementalJsonlCoordinator,
        "_check_live_retry_admission_if_needed",
        live_check,
    )
    monkeypatch.setattr(retry, "enforce_incremental_retry_gates", gate)
    monkeypatch.setattr(retry, "record_incremental_retry_failure", record)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_capture", capture)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    for _ in range(4):
        assert _call(route)[0] == "raised"
        assert not _lock_held(_state_root(source, cfg) / "lock.flock")
    print("RESERVATION_SEQUENCE", seen, "summaries", len(calls))
    assert seen == [
        ("check",),
        ("capture",),
        ("gate",),
        ("work",),
        ("account",),
        ("gate",),
        ("work",),
        ("account",),
        ("gate",),
        ("gate",),
    ]
    state = json.loads((_state_root(source, cfg) / "retry_state.json").read_bytes())
    assert len(calls) == state["attempts_on_prefix"] == 2


@pytest.mark.parametrize("scenario", ["clean", "append", "partial_tail", "oversized"])
def test_nonfaulted_shortcut_controls(tmp_path, monkeypatch, scenario):
    import incremental_jsonl as inc
    from tests.incremental_jsonl_helpers import codex_rollout_record
    from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config

    original_shortcut = inc.IncrementalJsonlCoordinator._unchanged_short_circuit_if_applicable
    rows = []
    for shortcut in (False, True):
        with monkeypatch.context() as mp:
            source, cfg, route = _route_fixture(tmp_path / str(shortcut), mp)
            calls = _count_summaries(mp)
            route()
            paid = len(calls)
            if scenario == "append":
                with source.open("ab") as fh:
                    fh.write(codex_rollout_record(100))
            elif scenario == "partial_tail":
                with source.open("ab") as fh:
                    fh.write(b'{"partial":')
            elif scenario == "oversized":
                cfg["index"]["incremental_jsonl"]["codex_rollout_admission"][
                    "max_source_bytes"
                ] = source.stat().st_size - 1
                _write_user_config(tmp_path / str(shortcut) / "config.toml", cfg)
            mp.setattr(
                inc.IncrementalJsonlCoordinator,
                "_unchanged_short_circuit_if_applicable",
                original_shortcut if shortcut else lambda self: None,
            )
            result = _call(route)
            root = _state_root(source, cfg)
            rows.append(
                (
                    shortcut,
                    result,
                    len(calls) - paid,
                    (root / "retry_state.json").exists(),
                )
            )
    print("NORMAL_CONTROL", scenario, rows)
    assert rows[0][1:] == rows[1][1:]


def test_bootstrap_grant_cannot_shortcut_existing_checkpoint(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_incremental_jsonl_live_boundary import _bootstrap_binding

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    paid = len(calls)
    checkpoint = json.loads(
        (_state_root(source, cfg) / "checkpoint.json").read_bytes()
    )
    coordinator = inc.IncrementalJsonlCoordinator(
        inc.ProductionBoundary(cfg, source),
        source,
        cfg=cfg,
        chunk_size=4,
        overlap=0,
        min_confidence=0.0,
        bootstrap_existing=True,
        expected_prefix_sha256=checkpoint["prefix_sha256"],
        max_bootstrap_chunks=20,
        **_bootstrap_binding(),
    )
    assert coordinator._unchanged_short_circuit_if_applicable() is None
    result = coordinator.run()
    print("BOOTSTRAP_CONTROL", result.outcome, "extra summaries", len(calls) - paid)
    assert result.outcome == "bootstrap_not_required"
    assert len(calls) == paid
