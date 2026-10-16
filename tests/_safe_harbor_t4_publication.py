# pylint: disable=protected-access
# Fault injection intentionally observes private operation boundaries.
"""Isolated recovery fault injection; called only after the T4 probe bootstrap."""
from __future__ import annotations

import json
import os
from pathlib import Path


def _check_completion(cfg, pid, before_unit):
    from tests._safe_harbor_t4_common import (
        _dump_state, _unit_for_pid, _assert_event_only_unit_unchanged,
        _pid_events, _lifecycle_state,
    )
    after = _dump_state(cfg)
    _assert_event_only_unit_unchanged(before_unit, _unit_for_pid(after, pid))
    assert sum(e['event_type'] == 'APPROVED' for e in _pid_events(cfg, pid)) == 1
    assert _lifecycle_state(cfg, pid) == 'APPROVED'
    rows = [json.loads(s) for s in Path(cfg['index']['units_export']).read_text(encoding='utf-8').splitlines() if s]
    assert len([r for r in rows if r.get('id') == before_unit['id']]) == 1


def run_publication(cfg, mode):
    import conflict_events as ce
    import propose_decision as pd
    from tests._safe_harbor_t4_common import (
        _setup_event_only, _dump_state, _unit_for_pid, _spawn_probe_case,
    )
    pid = _setup_event_only(cfg)
    before_unit = _unit_for_pid(_dump_state(cfg), pid)
    path = ce.event_path(cfg)
    real_append, real_fsync, real_export = ce.append_event_durable, os.fsync, pd._ensure_export_for_recovery
    hits = []
    error = None

    def fsync(fd):
        target = Path(os.readlink(f'/proc/self/fd/{fd}'))
        if mode == 'file_fsync' and target == path and b'"APPROVED"' in path.read_bytes():
            hits.append('file_fsync')
            raise OSError('injected APPROVED file fsync failure')
        if mode == 'dir_fsync' and target == path.parent and b'"APPROVED"' in path.read_bytes():
            hits.append('dir_fsync')
            raise OSError('injected APPROVED parent directory fsync failure')
        return real_fsync(fd)

    def append(config, event, **kwargs):
        if mode == 'before':
            hits.append('before')
            raise ce.EventPublicationError('before append')
        if mode == 'partial':
            hits.append('partial')
            with path.open('a', encoding='utf8') as out:
                out.write(json.dumps(event)[:23])
                out.flush()
                real_fsync(out.fileno())
            raise ce.EventPublicationError('partial append')
        result = real_append(config, event, **kwargs)
        if mode in {'lost_return', 'rollback_control'}:
            hits.append('lost_return')
            raise ce.EventPublicationError('durable APPROVED, acknowledgement lost')
        return result

    def export(*_args, **_kwargs):
        hits.append('export')
        raise OSError('injected export failure after corpus success')

    ce.append_event_durable = append
    os.fsync = fsync
    if mode == 'export':
        pd._ensure_export_for_recovery = export
    try:
        try:
            pd.recover_approval(cfg, pid)
        except pd.RecoveryCompletionUnknown as exc:
            error = str(exc)
        else:
            raise AssertionError('faulty invocation falsely reported success')
    finally:
        ce.append_event_durable, os.fsync, pd._ensure_export_for_recovery = real_append, real_fsync, real_export
    assert hits, f'fault injection never reached: {mode}'
    bytes_after = path.read_bytes()
    # Restart uses a new process with no failure patch left installed.
    retry_case = 'retry.assume_rollback' if mode == 'rollback_control' else 'recover.only'
    rc, result = _spawn_probe_case(retry_case, pid=pid)
    if mode == 'partial':
        assert rc != 0, result
        assert path.read_bytes() == bytes_after, 'retry discarded or changed malformed tail'
        assert b'"APPROVED"' not in bytes_after
    elif mode == 'rollback_control':
        assert rc == 0, result
        try:
            _check_completion(cfg, pid, before_unit)
        except AssertionError:
            # The wrong retry actually appended a duplicate terminal event.
            events = ce.load_events(cfg)
            assert sum(e['event_type'] == 'APPROVED' and e['proposal_id'] == pid for e in events) == 2
        else:
            raise AssertionError('duplicate-approval negative control escaped independent checker')
    else:
        assert rc == 0, result
        _check_completion(cfg, pid, before_unit)
    from tests._safe_harbor_t4_common import _assert_event_only_unit_unchanged
    _assert_event_only_unit_unchanged(before_unit, _unit_for_pid(_dump_state(cfg), pid))
    return {'verdict': 'PASS', 'case': mode, 'pid': pid, 'first_outcome': error, 'retry_rc': rc, 'fault_hits': hits}


def rollback_retry(cfg, pid):
    import propose_decision as pd
    from conflict_events import append_event_durable, new_event
    def wrong(config, proposal_id, *, lifecycle_approved, durability_root):
        del lifecycle_approved
        # Deliberately faulty historical assumption: failed caller => no APPROVED.
        append_event_durable(config, new_event('APPROVED', proposal_id), durability_root=durability_root)
    pd._publish_recovery_event = wrong
    return {'verdict': 'PASS', 'action': pd.recover_approval(cfg, pid)}
