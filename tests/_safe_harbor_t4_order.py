# pylint: disable=protected-access
# Fault injection intentionally observes private operation boundaries.
"""Actual recovery native-validation/publication ordering and failure effects."""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path


def run_guard_case(cfg, mode):
    import propose_decision as pd
    from chroma_write_guard import ChromaWriteGuard, ChromaWriteGuardError
    from tests._safe_harbor_t4_common import (
        _setup_approval_started, _dump_state, _spawn_probe_case,
    )
    pid = _setup_approval_started(cfg)
    path = Path(cfg['index']['chroma_dir']).parent / 'pending_decision_events.jsonl'
    export = Path(cfg['index']['units_export'])
    events_before = path.read_bytes()
    export_before = export.read_bytes() if export.exists() else None
    original_finalize, original_publish = ChromaWriteGuard.finalize_approval_recovery, pd._publish_recovery_event
    original_classify, original_after = pd._recovery_classify_live, ChromaWriteGuard._after_write
    calls, captured = [], {}
    def classify(store, ledger_id):
        captured['store'] = store
        return original_classify(store, ledger_id)
    def after(self, *args, **kwargs):
        calls.append(('after', kwargs.get('system_trusted')))
        if mode == 'after_failure':
            raise ChromaWriteGuardError('injected post-native validator failure')
        return original_after(self, *args, **kwargs)
    def finalize(self):
        calls.append(('finalize_start', None))
        original_finalize(self)
        assert not b'"APPROVED"' in path.read_bytes()
        calls.append(('finalize_done', None))
    def publish(*args, **kwargs):
        calls.append(('publish', None))
        assert ('finalize_done', None) in calls
        guard = captured['store']._write_guard
        # A fresh process must fail to take the real native lock at publication.
        code = '''import fcntl,os,sys
fd=os.open(sys.argv[1],os.O_RDONLY)
try:
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
 sys.exit(0)
sys.exit(3)
'''
        cmd = [sys.executable, '-I', '-S', '-B', '-c', code, str(guard.lock_path)]
        child = subprocess.run(cmd, env=dict(os.environ), capture_output=True, timeout=10, check=False)
        assert child.returncode == 0, 'native lock released before APPROVED publication'
        # Finalization is a one-way boundary: a new native mutation is refused.
        try:
            with guard.native_write(identifier=str(guard.chroma_dir), reload_client=captured['store']._reload_client):
                raise AssertionError('mutation admitted after finalize')
        except ChromaWriteGuardError as exc:
            assert 'after approval recovery finalize' in str(exc)
        return original_publish(*args, **kwargs)
    pd._recovery_classify_live = classify
    ChromaWriteGuard._after_write = after
    ChromaWriteGuard.finalize_approval_recovery = finalize
    pd._publish_recovery_event = publish
    error = None
    try:
        try:
            pd.recover_approval(cfg, pid)
        except ValueError as exc:
            error = str(exc)
    finally:
        pd._recovery_classify_live, ChromaWriteGuard._after_write = original_classify, original_after
        ChromaWriteGuard.finalize_approval_recovery, pd._publish_recovery_event = original_finalize, original_publish
    guard = captured['store']._write_guard
    assert guard._approval_recovery_depth == 0
    assert guard._approval_recovery_owner is None
    if mode == 'after_failure':
        assert error and 'validator failure' in error
        assert ('publish', None) not in calls
        assert path.read_bytes() == events_before
        assert (export.read_bytes() if export.exists() else None) == export_before
        assert ('after', False) in calls, 'failed write cleanup was skipped'
        rc, result = _spawn_probe_case('recover.only', pid=pid)
        assert rc == 0, result
    else:
        assert error is None
        assert calls.index(('after', True)) < calls.index(('finalize_done', None)) < calls.index(('publish', None))
    assert sum(json.loads(s)['event_type']=='APPROVED' for s in path.read_text(encoding='utf-8').splitlines()) == 1
    assert export.is_file()
    return {'verdict':'PASS','pid':pid,'calls':calls,'mode':mode,'state':_dump_state(cfg)}
