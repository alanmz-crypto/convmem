"""Claude verify probes, round 26 (corrective 19): the read-only retry check and the revalidating shortcut.

Scratch only: tmp_path HOME, fake providers, no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

import pytest

from tests.test_zz_claude_verify23 import _call, _metrics, _root


def _tree(root: Path):
    if not root.exists():
        return None
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            st = p.lstat()
            out[str(p.relative_to(root))] = (p.is_dir(), st.st_mtime_ns, None if p.is_dir() else p.read_bytes())
    return out


def _seed(state: Path, kind: str, prefix: str, source) -> None:
    state.parent.mkdir(parents=True, exist_ok=True)
    if kind == "absent":
        return
    if kind == "empty":
        state.write_text("{}\n")
    elif kind == "corrupt":
        state.write_text("{truncated\n")
    elif kind == "unavailable":
        state.mkdir()
    else:
        state.write_text(json.dumps({
            "source_path": str(source),
            "prefix_digest": "0" * 64 if kind == "other_prefix" else prefix,
            "error_code": "artifact_write_failed",
            "attempts_on_prefix": 3 if kind == "cap" else 0,
            "consecutive": 2 if kind in {"same_error", "other_prefix"} else 0,
            "source_consecutive": 3 if kind == "source_hold" else 0,
        }))


KINDS = ["absent", "empty", "corrupt", "unavailable", "cap", "same_error", "source_hold", "other_prefix"]
EXPECT = {"corrupt": "retry_state_unavailable", "unavailable": "retry_state_unavailable",
          "cap": "live_route_refused", "same_error": "live_route_refused", "source_hold": "live_route_refused"}


@pytest.mark.parametrize("kind", KINDS)
def test_z1_check_is_read_only(tmp_path, monkeypatch, kind) -> None:
    """The check refuses exactly like the gate and never creates, writes or touches anything."""
    import incremental_jsonl as inc
    from incremental_retry_state import check_incremental_retry_gates
    from watch import source_prefix_digest_for_watch
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    root = _root(source, cfg)
    state = root / "retry_state.json"
    prefix = source_prefix_digest_for_watch(str(source))
    if kind == "absent":
        assert not root.exists()
    else:
        _seed(state, kind, prefix, source)
    before = _tree(root)
    paths = {"transaction": root / "transaction.json", "lock": root / "lock.flock", "retry_state": state}
    from incremental_retry_state import _state_path
    assert _state_path(paths) == state, "probe must hit the real state path"
    try:
        check_incremental_retry_gates(paths, path_key=str(source), prefix_digest=prefix)
        got = None
    except inc.IncrementalJsonlError as exc:
        got = exc.code
    print(f"\nZ1 {kind}", got)
    assert got == EXPECT.get(kind)
    assert _tree(root) == before


@pytest.mark.parametrize("kind", KINDS)
def test_z2_shortcut_matches_full_path_for_every_retry_kind(tmp_path, monkeypatch, kind) -> None:
    """Seeded retry state, unchanged source: three calls, then a valid append and one more call."""
    import incremental_jsonl as inc
    from watch import source_prefix_digest_for_watch
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    original = inc.IncrementalJsonlCoordinator._unchanged_short_circuit_if_applicable
    arms = []
    for shortcut in (True, False):
        with monkeypatch.context() as mp:
            source, cfg, route = _route_fixture(tmp_path / str(shortcut), mp)
            calls = _count_summaries(mp)
            route()
            state = _root(source, cfg) / "retry_state.json"
            assert not state.exists()
            _seed(state, kind, source_prefix_digest_for_watch(str(source)), source)
            mp.setattr(inc.IncrementalJsonlCoordinator, "_unchanged_short_circuit_if_applicable",
                       original if shortcut else (lambda self: None))
            paid = len(calls)
            rows = []
            for i in range(4):
                if i == 3:
                    with source.open("ab") as fh:
                        fh.write(source.read_bytes().splitlines(keepends=True)[-1])
                r = _call(route)
                m = _metrics(source, cfg, calls)
                st = m["state"]
                if isinstance(st, bytes):
                    try:
                        st = {k: v for k, v in json.loads(st).items() if k != "source_path"}
                    except ValueError:
                        pass
                rows.append((r[:2], m["paid"] - paid, m["snapshots"], st))
            arms.append(rows)
    print(f"\nZ2 {kind}\n  shortcut: {[r[:3] for r in arms[0]]}\n  full:     {[r[:3] for r in arms[1]]}")
    assert arms[0] == arms[1]


def test_z3_capture_time_source_error_is_held(tmp_path, monkeypatch) -> None:
    """A source that rotates during every capture is refused, never paid, and held once its errors repeat."""
    import incremental_jsonl as inc
    from incremental_jsonl_formats import FORMAT_SPECS
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    with source.open("ab") as fh:
        fh.write(source.read_bytes().splitlines(keepends=True)[-1])
    spec = FORMAT_SPECS["jsonl_codex_rollout"]

    def parse(filepath, *, raw=None):
        view = spec.parse_complete_prefix(filepath, raw=raw)
        data = source.read_bytes()
        repl = source.with_suffix(".replacement")
        repl.write_bytes(data)
        repl.replace(source)  # rotate on every parse
        return view

    monkeypatch.setitem(FORMAT_SPECS, "jsonl_codex_rollout", dataclasses.replace(spec, parse_complete_prefix=parse))
    paid = len(calls)
    rows = []
    for _ in range(5):
        r = _call(route)
        m = _metrics(source, cfg, calls)
        st = json.loads(m["state"]) if isinstance(m["state"], bytes) else None
        rows.append((r[:2], m["paid"] - paid, m["snapshots"],
                     st and (st.get("error_code"), st.get("consecutive"), st.get("attempts_on_prefix"))))
    print("\nZ3", rows)
    assert all(r[0][0] == "raised" for r in rows)
    assert rows[-1][1] == 0
    assert rows[-1][2] == rows[2][2], "snapshots must stop growing once held"
