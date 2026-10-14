"""Claude verify probes, round 10 (61307d7): reader closed before write sessions.

The refine and monitor probes open the real production store session against a scratch
config, and a real second process saves to the same store through the write guard.
Scratch only.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tests.test_zz_claude_verify9 import _real_session_env, _where

ROOT = Path(__file__).resolve().parents[1]


def _small_sync_store(chroma: Path) -> None:
    """Create both collections with a small HNSW sync threshold, from another process."""
    code = (
        "import sys, chromadb\n"
        "from chroma_store import SUMMARIES, UNITS\n"
        "c = chromadb.PersistentClient(path=sys.argv[1])\n"
        "for n in (SUMMARIES, UNITS):\n"
        "    c.get_or_create_collection(n, configuration={'hnsw': {'space': 'cosine', 'sync_threshold': 100, 'batch_size': 10}})\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", code, str(chroma)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-1500:]


_FOREIGN = (
    "import random, sys\n"
    "from chroma_store import ChromaStore\n"
    "from chroma_write_guard import ChromaWriteGuard\n"
    "root, dim = sys.argv[1], int(sys.argv[2])\n"
    "store = ChromaStore(root, write_guard=ChromaWriteGuard(root))\n"
    "try:\n"
    "    for i in range(150):\n"
    "        rng = random.Random(i)\n"
    "        store.add_summary(f'foreign{i}', f'summary {i}', [rng.random() - 0.5 for _ in range(dim)],\n"
    "                          {'source_path': '/foreign', 'n': i})\n"
    "finally:\n"
    "    store.close()\n"
)


def _foreign_save(chroma: Path, dim: int = 16) -> None:
    """Another process saves: 150 guarded summaries, so the HNSW syncs at 100."""
    from chroma_write_guard import _synced_only, store_signature

    before = _synced_only(store_signature(chroma))
    done = subprocess.run(
        [sys.executable, "-c", _FOREIGN, str(chroma), str(dim)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-1500:]
    assert _synced_only(store_signature(chroma)) != before, (
        "the foreign save did not sync; the probe would be vacuous"
    )


def _store_env(tmp_path, monkeypatch):
    from chroma_store import ChromaStore

    cfg = _real_session_env(tmp_path, monkeypatch)
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    _small_sync_store(chroma)
    seed = ChromaStore(str(chroma))
    for n in range(3):
        seed.add_unit(
            f"u-untagged-{n}",
            f"notes about python packaging {n}",
            [0.1, 0.2, 0.3 + n],
            {
                "id": f"u-untagged-{n}",
                "title": f"Packaging {n}",
                "source_path": f"/scratch/{n}",
            },
        )
    seed.close()
    return cfg, chroma


def test_refine_write_survives_a_foreign_save_during_the_llm_call(tmp_path, monkeypatch) -> None:
    import llm
    import refine

    _cfg, chroma = _store_env(tmp_path, monkeypatch)
    paid: list[int] = []

    def generate(*_a, **_k):
        paid.append(1)
        if len(paid) == 1:
            _foreign_save(chroma)
        return "coding.tooling"

    monkeypatch.setattr(llm, "generate", generate)
    try:
        result, err = refine.run_job("backfill_domain", limit=3, verbose=False), None
    except Exception as exc:
        result, err = None, _where(exc)
    assert err is None, ("paid calls:", len(paid), err)
    assert result["updated"] == 3 and not result.get("errors"), (
        "paid calls:",
        len(paid),
        result,
    )


def test_monitor_write_survives_a_foreign_save_during_the_probes(tmp_path, monkeypatch) -> None:
    import convmem
    import llm
    import monitor
    from typer.testing import CliRunner

    _cfg, chroma = _store_env(tmp_path, monkeypatch)
    saved: list[int] = []

    def fetch(site, *, session=None, timeout=20.0):
        if not saved:
            saved.append(1)
            _foreign_save(chroma)
        return {}, "offline"

    monkeypatch.setattr(convmem, "_guard_write", lambda: None)
    monkeypatch.setattr(monitor, "fetch_https_headers", fetch)
    monkeypatch.setattr(
        monitor,
        "check_tls_redirect",
        lambda site, *, session=None, timeout=20.0: False,
    )
    monkeypatch.setattr(llm, "ollama_embed", lambda *a, **k: [0.1, 0.2, 0.3])
    out = CliRunner().invoke(convmem.app, ["monitor", "--site", "example.test"])
    err = (
        _where(out.exception)
        if out.exception and not isinstance(out.exception, SystemExit)
        else None
    )
    assert saved and out.exit_code == 0 and err is None, (out.exit_code, err, out.output[-300:])
    stats, _end = json.JSONDecoder().raw_decode(out.output[out.output.index("{") :])
    assert stats["observations"] > 0, stats


def test_corrupt_retry_state_cli_refusal_holds_the_watcher(tmp_path, monkeypatch) -> None:
    """S6/T2 end to end: the real CLI's exit-91 output makes the watcher hold the path."""
    import config
    import convmem
    import watch
    from typer.testing import CliRunner
    from watch_circuit_breaker import CircuitBreakerState

    import incremental_jsonl as inc
    import pytest

    from tests.test_zz_claude_verify8b import _count_summaries, _retry_state_path, _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    _retry_state_path(tmp_path).write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr("ingest.load_config", lambda *a, **k: cfg, raising=False)
    monkeypatch.setattr(convmem, "_guard_write", lambda: None, raising=False)
    out = CliRunner().invoke(convmem.app, ["index", "--file", str(source)])
    assert out.exit_code == 91, (out.exit_code, out.output[-400:], out.exception)
    assert len(calls) == 1, "no paid summary after the corrupt state"
    breaker = CircuitBreakerState(tmp_path / "breaker.json")
    exc = watch.IndexSubprocessError("index child failed", returncode=91, stderr=out.output)
    watch._record_ready_path_failure(str(source), exc, breaker=breaker, verbose=False)
    assert breaker.has_refusal_quarantine_for_path(str(source)), out.output[-400:]
    assert breaker.should_skip_refusal_quarantine(str(source), None)


def test_refine_daemon_survives_a_failing_job_with_one_limiter(tmp_path, monkeypatch) -> None:
    import config
    import refine

    cfg = {
        "refine": {
            "jobs": ["backfill_domain", "chroma_dedupe"],
            "interval_seconds": 1,
            "batch_size": 2,
        }
    }
    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    monkeypatch.setattr(refine, "_lock_path", lambda _cfg: tmp_path / "refine.lock")
    seen: list[tuple[str, int]] = []

    def run_job(job, **kwargs):
        seen.append((job, id(kwargs.get("limiter"))))
        if job == "backfill_domain":
            raise RuntimeError("lock ordering violation (probe)")
        return {}

    sleeps: list[int] = []

    def sleep(_s):
        sleeps.append(1)
        if len(sleeps) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(refine, "run_job", run_job)
    monkeypatch.setattr(refine.time, "sleep", sleep)
    refine.run_refine_daemon(verbose=False, use_lock=False)
    assert [j for j, _ in seen] == ["backfill_domain", "chroma_dedupe"] * 2, seen
    assert len({lid for _, lid in seen}) == 1 and seen[0][1] != id(None), seen


def test_index_route_commits_after_a_foreign_save_during_the_paid_summary(
    tmp_path, monkeypatch
) -> None:
    """The main burn path: another process saves while the route pays for a summary."""
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize
    from tests.test_zz_codex_audit import _route_fixture

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    chroma = Path(cfg["index"]["chroma_dir"]).expanduser()
    _small_sync_store(chroma)
    paid: list[int] = []

    def summarize(*args, **kwargs):
        paid.append(1)
        if len(paid) == 1:
            _foreign_save(chroma, dim=8)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)
    try:
        result, err = route(), None
    except Exception as exc:
        result, err = None, _where(exc)
    assert err is None, ("paid summaries:", len(paid), err)
    assert paid, result
