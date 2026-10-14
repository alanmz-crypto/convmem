# pylint: disable=wrong-import-position
# Project imports follow the mandatory isolation check.
"""Descriptor-level publication ordering on real isolated files and directories."""
from __future__ import annotations
import os
from pathlib import Path
import pytest
from tests._safe_harbor_bootstrap import require_t3_bootstrap
require_t3_bootstrap()
# Register only for this module; each child gets refusal before project imports.
from tests._safe_harbor_t4_pytest import isolated_t4_child_network  # pylint: disable=unused-import
from conflict_events import append_event_durable, ensure_event_log_durable, event_path, EventPublicationError

@pytest.mark.parametrize('failure', ['file', 'leaf', 'intermediate', 'root', 'none'])
def test_created_directory_chain_and_retry(tmp_path, monkeypatch, failure):
    root = tmp_path / 'preexisting-backup-root'
    root.mkdir()
    leaf = root / 'new' / 'nested'
    cfg = {'index': {'chroma_dir': str(leaf / 'chroma')}}
    path = event_path(cfg)
    real = os.fsync
    calls = []
    target = {'file': path, 'leaf': leaf, 'intermediate': leaf.parent, 'root': root}.get(failure)
    def fsync(fd):
        actual = Path(os.readlink(f'/proc/self/fd/{fd}'))
        calls.append(actual)
        if actual == target:
            raise OSError('injected descriptor failure')
        real(fd)
    monkeypatch.setattr(os, 'fsync', fsync)
    event = {'event_type': 'APPROVED', 'event_id': 'test-event', 'proposal_id': 'test-proposal'}
    if target is None:
        append_event_durable(cfg, event, durability_root=root)
    else:
        with pytest.raises(EventPublicationError):
            append_event_durable(cfg, event, durability_root=root)
        assert target in calls
    assert path.read_text().count('"event_id"') == 1
    # Already-visible bytes are re-synced: retry does not append or infer durability.
    calls.clear()
    target = None
    ensure_event_log_durable(cfg, durability_root=root)
    assert calls == [path, leaf, leaf.parent, root]
    assert path.read_text().count('"event_id"') == 1
    calls.clear()
    append_event_durable(cfg, {**event, 'event_id': 'second'}, durability_root=root)
    assert calls == [path, leaf, leaf.parent, root]
    assert path.read_text().count('"event_id"') == 2


def test_export_fsync_covers_new_parent_chain(tmp_path, monkeypatch):
    from propose_decision import _fsync_export_path
    root = tmp_path / 'backup-root'
    root.mkdir()
    export = root / 'new' / 'nested' / 'units.jsonl'
    export.parent.mkdir(parents=True)
    export.write_text('{}\n', encoding='utf-8')
    calls = []
    real = os.fsync
    def fsync(fd):
        calls.append(Path(os.readlink(f'/proc/self/fd/{fd}')))
        real(fd)
    monkeypatch.setattr(os, 'fsync', fsync)
    _fsync_export_path(export, root)
    assert calls == [export, export.parent, export.parent.parent, root]


def test_directory_chain_never_walks_outside_bound_root(tmp_path):
    from conflict_events import _ensure_directory_chain_durable
    root, other = tmp_path/'bound', tmp_path/'other'
    root.mkdir()
    other.mkdir()
    with pytest.raises(EventPublicationError, match='escapes'):
        _ensure_directory_chain_durable(other, stop=root)


def test_network_refusal_inherited_by_fresh_child():
    import subprocess
    import sys
    import json
    code = """import socket,sys
assert getattr(sys, '_safe_harbor_t4_network_refused', False)
try:
 socket.getaddrinfo('safe-harbor-canary.invalid',9)
except RuntimeError as exc:
 assert 'refuse Python network' in str(exc)
else:
 raise AssertionError('network refusal missing')
"""
    cmd = [sys.executable, '-s', '-B', '-c', code]
    child = subprocess.run(cmd, env=dict(os.environ), capture_output=True, text=True, timeout=10, check=False)
    assert child.returncode == 0, child.stdout + child.stderr
    log = Path(os.environ['SAFE_HARBOR_T4_NETWORK_LOG'])
    records = [json.loads(s) for s in log.read_text(encoding='utf-8').splitlines()]
    assert {'event':'socket.getaddrinfo','destination':'safe-harbor-canary.invalid'} in records
