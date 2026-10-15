"""Claude verify probes, round 16 (2ffaf79): one ledger id on several lines of one file.

Scratch only: real production store sessions against a scratch config; fake providers; no network.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json

import pytest

from tests.test_zz_claude_verify15 import _commit_fn, _depth_embed, _FreshReader, _obs, _seed
from tests.test_zz_claude_verify9 import _real_session_env


def _rows(cfg, lid):
    from chroma_store import ChromaStore

    store = ChromaStore(cfg["index"]["chroma_dir"])
    try:
        return [m for m in store.units_metadata() if m.get("ledger_id") == lid]
    finally:
        store.close()


@pytest.mark.parametrize("copies,seeded", [(2, False), (3, False), (2, True), (3, True)])
def test_u1_repeated_ledger_id_in_one_file(tmp_path, monkeypatch, copies, seeded) -> None:
    from observe import ingest_observation_file_with_drift_retry

    cfg = _real_session_env(tmp_path, monkeypatch)
    lid = f"obs_v16_dup_{copies}_{int(seeded)}"
    if seeded:
        _seed(cfg, _obs(lid, "Seeded text."))
    path = tmp_path / "obs.jsonl"
    path.write_text("".join(json.dumps(_obs(lid, f"Version {i}.")) + "\n" for i in range(copies)))
    _depth_embed(monkeypatch, [])
    owc, calls = _commit_fn(cfg)
    try:
        result, err = ingest_observation_file_with_drift_retry(
            str(path), embed_store=_FreshReader(cfg["index"]["chroma_dir"]), open_write_commit=owc,
            embed_model="fake", ollama_host="offline", upsert=True, verbose=False), None
    except Exception as exc:  # noqa: BLE001
        result, err = None, repr(exc)[:160]
    rows = _rows(cfg, lid)
    summary = (rows[0].get("summary") or rows[0].get("title")) if rows else None
    print(f"\nU1 copies={copies} seeded={seeded} rounds={calls['n']} err={err} result={result} "
          f"rows={len(rows)} summary={summary!r}")
    assert err is None and len(rows) == 1 and calls["n"] == 1, (calls["n"], err, len(rows))
    assert summary == f"Version {copies - 1}.", summary  # last line wins, as on main


def test_n4_real_add_file_upsert_survives_a_drift_round(tmp_path, monkeypatch) -> None:
    """The real `convmem add --file --upsert` command; only the Restic admission body is stubbed (still single-use)."""
    from typer.testing import CliRunner

    import convmem
    import purge_locks

    cfg = _real_session_env(tmp_path, monkeypatch)
    rec = _obs("obs_v16_n4", "Old text.")
    unit, = _seed(cfg, rec)
    path = tmp_path / "upsert.jsonl"
    path.write_text(json.dumps({**rec, "summary": "New text from the file."}) + "\n")
    _depth_embed(monkeypatch, [])
    opens, flocks = [], {"n": 0}

    def admission_steps(_entrypoint, _governed, _expected_cfg):
        opens.append(1)
        yield

    real_flock = purge_locks.index_write_flock

    def flock(*a, **k):
        flocks["n"] += 1
        if flocks["n"] == 1:
            from tests.test_zz_claude_verify15 import _foreign_update
            _foreign_update(cfg, unit["id"], "foreign change")
        return real_flock(*a, **k)

    monkeypatch.setattr(convmem, "_admission_steps", admission_steps)
    monkeypatch.setattr(purge_locks, "index_write_flock", flock)
    res = CliRunner().invoke(convmem.app, ["add", "--file", str(path), "--upsert"])
    print(f"\nN4 exit={res.exit_code} opens={len(opens)} exc={res.exception!r} out={res.output[-160:]!r}")
    assert res.exit_code == 0 and len(opens) == 2 and "updated=1" in res.output, res.output


def test_s1_batch_commit_does_no_full_store_scan_under_c1(tmp_path, monkeypatch) -> None:
    """Validation under C1 must not rescan the whole store (one 10 s scan per row at 109k units)."""
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from observe import commit_prepared_observation_file_rows, prepare_observation_file_rows
    from purge_locks import index_write_flock

    cfg = _real_session_env(tmp_path, monkeypatch)
    recs = [_obs(f"obs_v16_s{i}", "Old text.") for i in range(3)]
    _seed(cfg, *recs)
    path = tmp_path / "obs.jsonl"
    path.write_text("".join(json.dumps({**r, "summary": "New text."}) + "\n" for r in recs)
                    + json.dumps(_obs("obs_v16_s_new", "Brand new.")) + "\n")
    _depth_embed(monkeypatch, [])
    rows, _ = prepare_observation_file_rows(str(path), embed_store=open_readonly_unit_store(cfg["index"]["chroma_dir"]),
                                            embed_model="fake", ollama_host="offline", upsert=True)
    scans = []
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint="claude_verify16.s1") as session:
            inner = session.store
            real = inner.units_metadata
            monkeypatch.setattr(inner, "units_metadata", lambda *a, **k: scans.append(1) or real(*a, **k),
                                raising=False)
            stats = commit_prepared_observation_file_rows(rows, store=inner, upsert=True, verbose=False)
    print(f"\nS1 full_scans={len(scans)} stats={stats}")
    assert stats["updated"] == 3 and stats["accepted"] == 1, stats
    assert scans == [], len(scans)
