"""Claude verify probes for issue #286 corrective 6 (e1914f5), burn bounds. Scratch only.

Codex's F2 probes flipped to the round-7 spec, plus Q2(c), Q2(d), Q7 and Q1 checks.
"""

# pylint: disable=protected-access

from __future__ import annotations

import json
import subprocess

import pytest
import requests

from tests.test_zz_codex_audit import _route_fixture


def _count_summaries(monkeypatch):
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize

    calls: list[int] = []

    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)

    monkeypatch.setattr(ingest, "summarize", summarize)
    return calls


def _cli_stderr(exc) -> tuple[int, str]:
    """Mirror convmem.py's index --file handling of a routed failure (exit code, stderr)."""
    from incremental_jsonl import format_live_route_refused

    if getattr(exc, "code", "") != "live_route_refused":
        return 1, str(exc)
    lines = str(exc.detail or "").splitlines()
    head = lines[0]
    tail = head.rsplit(":", maxsplit=1)[-1]
    outcome, digest = head.rsplit(":", maxsplit=1) if ":" in head and len(tail) == 64 else (head, "")
    return 91, "\n".join([format_live_route_refused(outcome, digest), *lines[1:2]])


def _watch_flush(monkeypatch, route, catch):
    import watch

    def flush(path, **kwargs):
        try:
            route()
        except catch as exc:
            code, stderr = _cli_stderr(exc)
            raise watch.IndexSubprocessError(str(exc), returncode=code, stderr=stderr) from exc

    monkeypatch.setattr(watch, "flush_path", flush)


def test_f2a_prepared_write_oserror_stops_paying(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import watch

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("simulated prepared-artifact write failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    _watch_flush(monkeypatch, route, (OSError, inc.IncrementalJsonlError))
    breaker = watch.CircuitBreakerState(tmp_path / "breaker.json")
    for _ in range(4):
        watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert len(calls) == 2, len(calls)
    assert breaker.has_refusal_quarantine_for_path(str(source))


def test_f2b_manual_retry_refuses_before_transform(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import ingest

    _source, _cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def failed_distill(*args, **kwargs):
        raise RuntimeError("simulated distill timeout")

    monkeypatch.setattr(ingest, "distill", failed_distill)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    codes = []
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        codes.append(caught.value.code)
    assert len(calls) == 2, (len(calls), codes)
    assert codes[2:] == ["live_route_refused", "live_route_refused"], codes


def test_f2c_provider_refusal_stops_paying(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import ingest
    import watch

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def failed_distill(*args, **kwargs):
        response = requests.Response()
        response.status_code = 402
        raise requests.HTTPError("synthetic provider unavailable", response=response)

    monkeypatch.setattr(ingest, "distill", failed_distill)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    _watch_flush(monkeypatch, route, (ingest.ProviderUnavailableError, inc.IncrementalJsonlError))
    breaker = watch.CircuitBreakerState(tmp_path / "breaker.json")
    for _ in range(4):
        watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert len(calls) == 2, len(calls)
    assert breaker.has_refusal_quarantine_for_path(str(source))


def test_q2d_source_hold_across_prefixes_and_clear_quarantine_releases(tmp_path, monkeypatch) -> None:
    import config
    import convmem
    import incremental_jsonl as inc
    from tests.incremental_jsonl_helpers import codex_rollout_record
    from typer.testing import CliRunner

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    codes = []
    for index in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        codes.append(caught.value.code)
        with source.open("ab") as handle:  # an active session: a new prefix every time
            handle.write(codex_rollout_record(100 + index))
    assert len(calls) == 3, (len(calls), codes)
    assert codes[3] == "live_route_refused", codes

    monkeypatch.setattr(config, "load_config", lambda *a, **k: cfg)
    out = CliRunner().invoke(convmem.app, ["watch", "--clear-quarantine", str(source)])
    assert out.exit_code == 0, (out.output, out.exception)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    assert len(calls) == 4, "clear-quarantine did not release the source hold"


def _retry_state_path(tmp_path):
    found = list((tmp_path / "data").rglob("retry_state.json"))
    assert len(found) == 1, found
    return found[0]


def _one_failure(tmp_path, monkeypatch):
    import incremental_jsonl as inc

    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    return route, calls, _retry_state_path(tmp_path)


def test_q2c_unreadable_retry_state_fails_closed(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc

    route, calls, state = _one_failure(tmp_path, monkeypatch)
    state.chmod(0)
    try:
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
    finally:
        state.chmod(0o600)
    assert caught.value.code == "retry_state_unavailable", caught.value.code
    assert len(calls) == 1


def test_q2c_corrupt_retry_state_fails_closed(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc

    route, calls, state = _one_failure(tmp_path, monkeypatch)
    state.write_text("{not json", encoding="utf-8")
    with pytest.raises(inc.IncrementalJsonlError) as caught:
        route()
    assert caught.value.code == "retry_state_unavailable", caught.value.code
    assert len(calls) == 1


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def test_q7_tracked_review_bundle_scanned_untracked_skipped(tmp_path, monkeypatch) -> None:
    from eval_corpus.r2b_v2.coverage import inventory

    ctor = 'from chroma_store import ChromaStore\nstore = ChromaStore("~/.local/share/convmem/chroma")\n'
    _git(tmp_path, "init", "-q")
    (tmp_path / "review-bundles").mkdir()
    (tmp_path / "review-bundles/tracked_writer.py").write_text(ctor)
    (tmp_path / "review-bundles/untracked_writer.py").write_text(ctor)
    _git(tmp_path, "add", "review-bundles/tracked_writer.py")
    manifest = tmp_path / "shadow.json"
    manifest.write_text('{"allowlisted_direct_sites": []}')
    monkeypatch.setattr(inventory, "ROOT", tmp_path)
    monkeypatch.setattr(inventory, "SHADOW_INVENTORY", manifest)
    assert inventory._scan_chroma_ctor_uncached() == ["review-bundles/tracked_writer.py:2"]


def test_q1_dedupe_rollback_removes_only_this_transaction(tmp_path, monkeypatch) -> None:
    from tests.test_issue_286_stage2_wedge_probes import _wedge_then_replay

    replay, _export, _foreign, _source = _wedge_then_replay(tmp_path, monkeypatch, "before_summary_upsert")
    paths = replay._dedupe_restore_paths()
    own, other = "tx-own", "tx-other"
    lines = [
        json.dumps({"event_id": "old", "transaction_id": other}, separators=(",", ":")) + "\n",
        json.dumps({"event_id": "mine-1", "transaction_id": own}) + "\n",
        '{"event_id": "legacy-no-tx"}\n',
        json.dumps({"event_id": "mine-2", "transaction_id": own}) + "\n",
        json.dumps({"z": 1, "event_id": "later-foreign", "a": 2}) + "\n",
    ]
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(lines), encoding="utf-8")
    replay._restore_dedupe_files(own)
    expected = "".join(lines[i] for i in (0, 2, 4))
    for path in paths.values():
        assert path.read_text(encoding="utf-8") == expected
