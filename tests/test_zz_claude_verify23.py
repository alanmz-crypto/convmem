"""Claude verify probes, round 23 (corrective 17): the new pre-capture unchanged shortcut and repeated refusals.

Scratch only: tmp_path HOME, fake providers, no network. Each probe prints a row so the same file can run at
74c8ee7 (before corrective 17) and at the tip for a differential.
"""

# pylint: disable=protected-access,duplicate-code

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _root(source, cfg):
    import incremental_jsonl as inc

    return Path(cfg["index"]["incremental_jsonl"]["state_dir"]) / inc.source_state_id(
        str(source.resolve()), format_id="jsonl_codex_rollout"
    )


def _metrics(source, cfg, calls):
    root = _root(source, cfg)
    snaps = list((root / "snapshots").glob("*/*")) if (root / "snapshots").exists() else []
    state = root / "retry_state.json"
    return {"paid": len(calls), "snapshots": len(snaps), "snap_bytes": sum(p.stat().st_size for p in snaps),
            "state": state.read_bytes() if state.is_file() else ("dir" if state.is_dir() else None)}


def _call(route):
    import incremental_jsonl as inc

    try:
        result = route()
        return ("ok", result[0] if isinstance(result, tuple) else result)
    except inc.IncrementalJsonlError as exc:
        return ("raised", exc.code, str(exc).splitlines()[0][:90])


def _commit(tmp_path, monkeypatch):
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    assert (_root(source, cfg) / "checkpoint.json").is_file()
    return source, cfg, route, calls


def test_x1_unchanged_source_after_legacy_reindex_lineage(tmp_path, monkeypatch) -> None:
    """D8 guard: the full path refuses an unchanged source whose processed lineage no longer matches."""
    source, cfg, route, calls = _commit(tmp_path, monkeypatch)
    plog = Path(cfg["index"]["processed_log"])
    data = json.loads(plog.read_text())  # pylint: disable=unspecified-encoding
    hits = 0
    for entry in data.values():
        if isinstance(entry, dict) and entry.get("incremental_jsonl_lineage"):
            entry["incremental_jsonl_lineage"] = "legacy-reindex-lineage"
            hits += 1
    assert hits == 1, hits
    plog.write_text(json.dumps(data))  # pylint: disable=unspecified-encoding
    paid = len(calls)
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(3)]
    print("\nX1", [(r, {k: v for k, v in m.items() if k != "state"}, m["state"] is not None) for r, m in rows])
    print("X1 lineage after:", [e.get("incremental_jsonl_lineage") for e in json.loads(plog.read_text()).values() if isinstance(e, dict)])  # pylint: disable=line-too-long, unspecified-encoding
    assert len(calls) == paid
    assert all(r[0] == "raised" for r, _ in rows), rows


def test_x2_mutated_prefix_repeated_calls_bound_snapshots(tmp_path, monkeypatch) -> None:
    source, cfg, route, calls = _commit(tmp_path, monkeypatch)
    raw = bytearray(source.read_bytes())
    second = raw.index(b"\n") + 1
    end = raw.index(b"\n", second)
    pos = max(i for i in range(second, end) if chr(raw[i]).isdigit())
    raw[pos] = ord("1") if raw[pos] != ord("1") else ord("2")
    with open(source, "r+b") as fh:  # same inode, same length
        fh.write(bytes(raw))
    paid = len(calls)
    rows = []
    for _ in range(6):
        rows.append((_call(route), _metrics(source, cfg, calls)))
    print("\nX2", [(r[:2], m["paid"], m["snapshots"], m["snap_bytes"]) for r, m in rows])
    for _, m in rows:
        print("X2state", m["state"][:200] if m["state"] else None)
    assert len(calls) == paid
    assert rows[-1][1]["snapshots"] == rows[2][1]["snapshots"], "snapshots must stop growing once held"
    assert rows[-1][1]["state"] == rows[3][1]["state"]


def test_x3_invalid_utf8_appended_after_commit(tmp_path, monkeypatch) -> None:
    source, cfg, route, calls = _commit(tmp_path, monkeypatch)
    with open(source, "ab") as fh:
        fh.write(b'{"type":"response_item","payload":"\xff\xfe"}\n')
    paid = len(calls)
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(5)]
    print("\nX3", [(r[:2], m["paid"], m["snapshots"]) for r, m in rows])
    assert len(calls) == paid
    assert rows[-1][1]["snapshots"] == rows[2][1]["snapshots"]
    assert rows[-1][1]["state"] == rows[3][1]["state"]


@pytest.mark.parametrize("kind", ["corrupt", "unavailable", "cap", "same_code"])
def test_x4_repeated_refusal_kinds(tmp_path, monkeypatch, kind) -> None:
    import incremental_jsonl as inc
    import ingest
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    state = _root(source, cfg) / "retry_state.json"
    if kind == "same_code":
        def fail_distill(*_a, **_k):
            raise RuntimeError("scratch distill unavailable")
        monkeypatch.setattr(ingest, "distill", fail_distill)
        monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    else:
        def fail(*_a, **_k):
            raise OSError("scratch prepared failure")
        monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail)
    if kind == "corrupt":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("{truncated\n")
    if kind == "unavailable":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.mkdir()  # a directory where the state file belongs
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(6)]
    print(f"\nX4 {kind}", [(r[:2], m["paid"], m["snapshots"], m["snap_bytes"]) for r, m in rows])
    paid = [m["paid"] for _, m in rows]
    assert paid[-1] == paid[2] and paid[-1] <= 4, paid
    assert rows[-1][1]["snapshots"] == rows[2][1]["snapshots"]
    assert rows[-1][1]["state"] == rows[2][1]["state"]
    if kind == "corrupt":
        assert state.read_text() == "{truncated\n"
