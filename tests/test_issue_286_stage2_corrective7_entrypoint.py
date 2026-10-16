"""Burn-bound probes through ``ingest.index(force_file=...)`` (issue #286 corrective 7)."""

# pylint: disable=protected-access

from __future__ import annotations

from unittest import mock

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


def _index_file(source, cfg):
    import ingest

    with mock.patch("ingest.load_config", return_value=cfg), mock.patch(
        "config.load_config", return_value=cfg
    ), mock.patch("brief.refresh_brief_after_change", lambda *_a, **_k: None):
        return ingest.index(verbose=False, force_file=str(source))


def test_f2a_index_entrypoint_oserror_stops_paying(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def fail_save(*args, **kwargs):
        raise OSError("simulated prepared-artifact write failure")

    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, "_write_prepared", fail_save)
    codes = []
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            _index_file(source, cfg)
        codes.append(caught.value.code)
    assert len(calls) == 2, (len(calls), codes)
    assert codes[2:] == ["live_route_refused", "live_route_refused"], codes


def test_f2b_index_entrypoint_refuses_before_transform(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import ingest

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def failed_distill(*args, **kwargs):
        raise RuntimeError("simulated distill timeout")

    monkeypatch.setattr(ingest, "distill", failed_distill)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    codes = []
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            _index_file(source, cfg)
        codes.append(caught.value.code)
    assert len(calls) == 2, (len(calls), codes)
    assert codes[2:] == ["live_route_refused", "live_route_refused"], codes


def test_f2c_index_entrypoint_provider_refusal_stops_paying(tmp_path, monkeypatch) -> None:
    import incremental_jsonl as inc
    import ingest

    source, cfg, _route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)

    def failed_distill(*args, **kwargs):  # pylint: disable=unused-argument
        response = requests.Response()
        response.status_code = 402
        raise requests.HTTPError("synthetic provider unavailable", response=response)

    monkeypatch.setattr(ingest, "distill", failed_distill)
    monkeypatch.setattr(ingest, "_SYNTHESIS_FAIL_LOG", tmp_path / "synthesis_failures.jsonl")
    codes = []
    for _ in range(4):
        with pytest.raises((ingest.ProviderUnavailableError, inc.IncrementalJsonlError)):
            _index_file(source, cfg)
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            _index_file(source, cfg)
        codes.append(caught.value.code)
    assert len(calls) == 2, len(calls)
    assert codes[-2:] == ["live_route_refused", "live_route_refused"], codes
