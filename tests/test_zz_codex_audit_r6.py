"""Round-6 scratch probes: real admission/accounting, fake providers."""
import dataclasses
import json
from pathlib import Path

import pytest

from tests.test_zz_codex_audit import _route_fixture
from tests.test_zz_claude_verify8b import _count_summaries


def _root(source, cfg):
    import incremental_jsonl as inc
    return Path(cfg['index']['incremental_jsonl']['state_dir']) / inc.source_state_id(
        str(source.resolve()), format_id='jsonl_codex_rollout')


def _call(route):
    import incremental_jsonl as inc
    try:
        return ('ok', route()[0])
    except inc.IncrementalJsonlError as exc:
        return ('raised', exc.code)


def test_alternating_real_capture_errors_do_not_reopen_admission(tmp_path, monkeypatch):
    """Same prefix, alternating real revalidation failures, then a quiet retry."""
    from incremental_jsonl_formats import FORMAT_SPECS
    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    original = source.read_bytes()
    spec = FORMAT_SPECS['jsonl_codex_rollout']
    state = _root(source, cfg) / 'retry_state.json'
    mutations = []
    rows = []
    for n in range(6):
        source.write_bytes(original)
        def parse(filepath, *, raw=None):
            view = spec.parse_complete_prefix(filepath, raw=raw)
            mutations.append(n)
            if n % 2 == 0:
                source.write_bytes(original.splitlines(keepends=True)[0])
            else:
                changed = original.replace(b'line-0', b'line-X', 1)
                if changed == original:
                    tail = bytearray(original)
                    pos = original.index(b'\n') + 1
                    pos = next(i for i in range(pos, len(tail)) if tail[i] == ord('0'))
                    tail[pos] = ord('9')
                    changed = bytes(tail)
                source.write_bytes(changed)
            return view
        with monkeypatch.context() as mp:
            mp.setitem(FORMAT_SPECS, 'jsonl_codex_rollout', dataclasses.replace(spec, parse_complete_prefix=parse))
            result = _call(route)
        saved = json.loads(state.read_bytes())
        rows.append((result, saved['error_code'], saved['consecutive'], saved['source_consecutive'], len(calls)))
        assert not (_root(source, cfg) / 'transaction.json').exists()
    source.write_bytes(original)
    final = _call(route)
    print('ALTERNATING_CAPTURE:', rows, 'captures=', len(mutations), 'quiet_retry=', final, 'summaries=', len(calls), 'state_retained=', state.exists())
    assert final == ('raised', 'live_route_refused'), 'specific error codes weakened the existing capture-error hold'
    assert len(calls) == 0


@pytest.mark.parametrize('kind', ['missing', 'empty', 'benign', 'corrupt', 'directory', 'prefix_cap', 'same_error', 'source_hold', 'unreadable'])
def test_readonly_check_has_no_mutation(tmp_path, monkeypatch, kind):
    import incremental_jsonl as inc
    import incremental_retry_state as retry
    path = tmp_path / 'state' / 'retry_state.json'
    path.parent.mkdir()
    paths = {'transaction': path.parent / 'transaction.json'}
    value = {'prefix_digest': 'abc', 'error_code': 'artifact_write_failed'}
    if kind == 'empty': value = {}
    if kind == 'prefix_cap': value['attempts_on_prefix'] = 3
    if kind == 'same_error': value['consecutive'] = 2
    if kind == 'source_hold': value['source_consecutive'] = 3
    if kind == 'directory': path.mkdir()
    elif kind != 'missing': path.write_text('{bad' if kind == 'corrupt' else json.dumps(value))
    def image():
        return [(str(p.relative_to(tmp_path)), p.is_dir(), p.read_bytes() if p.is_file() else None, p.stat().st_mtime_ns) for p in sorted(tmp_path.rglob('*'))]
    before = image()
    if kind == 'unreadable':
        read_text = Path.read_text
        def deny(self, *a, **kw):
            if self == path: raise PermissionError('scratch unreadable state')
            return read_text(self, *a, **kw)
        monkeypatch.setattr(Path, 'read_text', deny)
    def forbidden(*a, **kw):
        raise AssertionError('read-only admission invoked a writer')
    for name in ('_write', '_ensure_retry_state_available', 'reserve_incremental_retry_attempt', 'clear_incremental_retry_state'):
        monkeypatch.setattr(retry, name, forbidden)
    result = 'allowed'
    try:
        retry.check_incremental_retry_gates(paths, path_key='/scratch/source', prefix_digest='abc')
    except inc.IncrementalJsonlError as exc:
        result = exc.code
    expected = 'retry_state_unavailable' if kind in ('corrupt', 'directory', 'unreadable') else 'live_route_refused' if kind in ('prefix_cap', 'same_error', 'source_hold') else 'allowed'
    assert result == expected
    assert image() == before
    print('READ_ONLY:', kind, result, 'bytes+mtime+entries identical')

# src: /home/lauer/.kiro/audit-286-r5/harness/test_audit_r5.py — differential fixture conventions
