"""Claude verify probes, round 24 (corrective 18): the pre-capture shortcut must agree with the full path.

Scratch only: tmp_path HOME, fake providers, no network. Each scenario runs twice from a fresh fixture, once with
the shortcut and once with it disabled, and the observable results must match call for call.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.test_zz_claude_verify23 import _call, _metrics


def _lineage(cfg, value):
    plog = Path(cfg["index"]["processed_log"])
    data = json.loads(plog.read_text())
    for entry in data.values():
        if isinstance(entry, dict) and entry.get("incremental_jsonl_lineage"):
            entry["incremental_jsonl_lineage"] = value
    plog.write_text(json.dumps(data))


def _drop_processed(cfg):
    plog = Path(cfg["index"]["processed_log"])
    plog.write_text(
        json.dumps(
            {
                k: v
                for k, v in json.loads(plog.read_text()).items()
                if not (isinstance(v, dict) and v.get("incremental_jsonl_lineage"))
            }
        )
    )


def _exclude_processed(cfg):
    plog = Path(cfg["index"]["processed_log"])
    data = json.loads(plog.read_text())
    for entry in data.values():
        if isinstance(entry, dict) and entry.get("incremental_jsonl_lineage"):
            entry["excluded"] = True
    plog.write_text(json.dumps(data))


def _fingerprint(cfg, source):
    from tests.test_zz_claude_verify23 import _root

    cp = _root(source, cfg) / "checkpoint.json"
    data = json.loads(cp.read_text())
    data["transform_fingerprint"] = "older-transform"
    cp.write_text(json.dumps(data))


SCENARIOS = {
    "plain": lambda cfg, source: None,
    "lineage": lambda cfg, source: _lineage(cfg, "legacy-reindex-lineage"),
    "processed_dropped": lambda cfg, source: _drop_processed(cfg),
    "processed_excluded": lambda cfg, source: _exclude_processed(cfg),
    "fingerprint": _fingerprint,
}


def _run(tmp_path, monkeypatch, scenario, shortcut):
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    route()
    SCENARIOS[scenario](cfg, source)
    if not shortcut:
        monkeypatch.setattr(
            inc.IncrementalJsonlCoordinator,
            "_unchanged_short_circuit_if_applicable",
            lambda self: None,
        )
    rows = []
    for _ in range(4):
        result = _call(route)
        m = _metrics(source, cfg, calls)
        state = None
        if isinstance(m["state"], bytes):
            state = {
                k: v
                for k, v in json.loads(m["state"]).items()
                if k in ("attempts_on_prefix", "consecutive", "error_code")
            }
        rows.append((result[:2], m["paid"], m["snapshots"], state))
    return rows


@pytest.mark.parametrize("scenario", sorted(SCENARIOS))
def test_y1_shortcut_matches_full_path(tmp_path, monkeypatch, scenario) -> None:
    with_shortcut = _run(tmp_path / "a", monkeypatch, scenario, True)
    without = _run(tmp_path / "b", monkeypatch, scenario, False)
    print(f"\nY1 {scenario}\n  shortcut: {with_shortcut}\n  full:     {without}")
    assert with_shortcut == without


@pytest.mark.parametrize("when", ["first_run", "after_commit"])
def test_y2_session_identity_mismatch_refuses_and_logs(
    tmp_path, monkeypatch, when
) -> None:
    import incremental_jsonl as inc
    from tests.test_zz_claude_verify8b import _count_summaries
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    if when == "after_commit":
        route()
    raw = bytearray(source.read_bytes())
    meta_end = raw.index(b"\n")
    uid = source.name.split("-", 6)[-1].removesuffix(".jsonl")[-12:].encode()
    pos = raw.index(uid, 0, meta_end) + len(uid) - 1
    raw[pos] = ord("0") if raw[pos] != ord("0") else ord("1")
    with open(source, "r+b") as fh:
        fh.write(bytes(raw))
    logged = []
    real = inc.IncrementalJsonlCoordinator._emit_codex_admitted_log

    def spy(self, result, **kw):
        logged.append(result.outcome)
        return real(self, result, **kw)

    monkeypatch.setattr(
        inc.IncrementalJsonlCoordinator, "_emit_codex_admitted_log", spy
    )
    paid = len(calls)
    rows = [(_call(route), _metrics(source, cfg, calls)) for _ in range(3)]
    print(
        f"\nY2 {when}",
        [(r[:3], m["paid"], m["snapshots"]) for r, m in rows],
        "logged",
        logged,
    )
    assert len(calls) == paid
    assert all(r[0] == "raised" for r, _ in rows)
    assert "codex_session_identity_mismatch" in rows[0][0][2]
    assert all(m["snapshots"] == 0 for _, m in rows)
    assert "codex_session_identity_mismatch" in logged
