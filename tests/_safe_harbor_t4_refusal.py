# pylint: disable=protected-access
# Fault injection intentionally observes private operation boundaries.
"""Real malformed-state fixtures and a deliberately wrong unknown-to-absence control."""
from __future__ import annotations
import json
from pathlib import Path


def _edit_rows(path, transform):
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line]
    path.write_text(''.join(json.dumps(r) + '\n' for r in transform(rows)), encoding='utf-8')


# Each mode is a distinct fault-matrix row; none may silently bypass the final effect check.
def run_refusal(cfg, mode):  # pylint: disable=too-many-branches,too-many-locals
    import chroma_store as cs
    import propose_decision as pd
    from conflict_events import event_path
    from tests._safe_harbor_t4_common import (
        _setup_event_only, _dump_state, _unit_for_pid, _prime_ledger_cache,
    )
    pid = _setup_event_only(cfg)
    unit = _unit_for_pid(_dump_state(cfg), pid)
    _prime_ledger_cache(cfg)  # Every refusal is checked against a formerly warm index.
    files = [pd.queue_path(cfg), pd.approved_path(cfg), event_path(cfg), Path(cfg['index']['units_export'])]
    field_modes = {'tombstone': ('superseded', True), 'missing_hash': ('content_hash', ''),
                   'invalid_hash': ('content_hash', 'invalid'), 'false_hash': ('content_hash', 'f'*64),
                   'wrong_marker': ('proposal_id', 'dec_prop_conflicting'),
                   'stale_base': ('summary', 'changed since approval')}
    missing_collection = mode == 'missing_collection'
    if mode in field_modes or mode in {'duplicate', 'active_and_tombstone', 'wrong_document'}:
        store = cs.ChromaStore(cfg['index']['chroma_dir'])
        try:
            if mode in field_modes:
                key, value = field_modes[mode]
                meta = {**unit['metadata'], key: value}
                if mode == 'stale_base':
                    from ledger_content_hash import ledger_content_hash
                    meta['content_hash'] = ledger_content_hash(pd._metadata_semantic_record(meta, meta['ledger_id']))
                store.update_unit_metadata(unit['id'], meta)
            elif mode == 'wrong_document':
                original = store.get_unit(unit['id'], include_embedding=True)
                store._collection(cs.UNITS).update(
                    ids=[unit['id']], documents=['corrupt document'], embeddings=[original['embedding']]
                )
            else:
                original = store.get_unit(unit['id'], include_embedding=True)
                meta = {**unit['metadata'], 'id': 'duplicate-id'}
                if mode == 'active_and_tombstone':
                    meta['superseded'] = True
                store.add_unit('duplicate-id', unit['document'], original['embedding'], meta)
        finally:
            store.close()
    elif missing_collection:
        store = cs.ChromaStore(cfg['index']['chroma_dir'])
        store.client.delete_collection(cs.UNITS)
        store.close()
    elif mode.startswith(('queue_', 'approved_', 'events_', 'export_')):
        kind, defect = mode.split('_', 1)
        path = {'queue': files[0], 'approved': files[1], 'events': files[2], 'export': files[3]}[kind]
        if kind == 'export' and not path.exists():
            # A conflicting actual projection, rather than a missing projection (repairable).
            row = {'id': unit['id'], 'ledger_id': unit['metadata']['ledger_id'], 'summary': 'wrong'}
            path.write_text(json.dumps(row) + '\n', encoding='utf-8')
        if defect == 'malformed':
            with path.open('a', encoding='utf-8') as out:
                out.write('{bad tail')
        elif defect == 'missing':
            path.unlink()
        elif defect == 'duplicate':
            _edit_rows(path, lambda rows: rows + [rows[-1]])
        elif defect == 'conflict':
            def alter(rows):
                if kind == 'events':
                    rows.append({**rows[-1], 'event_type': 'REJECTED'})
                else:
                    rows[-1]['summary'] = 'different intent'
                return rows
            _edit_rows(path, alter)
        elif defect in {'target', 'base', 'hashschema'}:
            key, value = {'target': ('target_ledger_id', 'dec_other'),
                          'base': ('base_content_hash', 'f' * 64),
                          'hashschema': ('hash_schema_version', 999)}[defect]
            _edit_rows(path, lambda rows: [{**r, key: value} for r in rows])
        elif defect == 'unsigned':
            _edit_rows(path, lambda rows: [{**r, 'signer': ''} for r in rows])
    elif mode not in {'read_error', 'unknown_control', 'cfg_chroma', 'cfg_export', 'cfg_missing'}:
        raise AssertionError('unknown fixture mode ' + mode)

    def file_state():
        return {str(p): p.read_bytes() if p.exists() else None for p in files}
    before_files = file_state()
    before = None if missing_collection else _dump_state(cfg)
    original_read, original_classify = cs.ChromaStore.units_metadata, pd._recovery_classify_live
    injected = []
    def read_error(self, *args, **kwargs):
        if not injected:
            injected.append(True)
            raise OSError('injected actual units_metadata read failure')
        return original_read(self, *args, **kwargs)
    if mode in {'read_error', 'unknown_control'}:
        cs.ChromaStore.units_metadata = read_error
    if mode == 'unknown_control':
        def faulty(store, ledger_id):
            result = original_classify(store, ledger_id)
            if result.get('review') == 'missing_collection':
                return {'review': None, 'absent': True, 'marker': '', 'live_hash': '', 'unit': None}
            return result
        pd._recovery_classify_live = faulty
    error = None
    try:
        supplied = cfg
        if mode.startswith('cfg_'):
            supplied = {**cfg, 'index': dict(cfg['index'])}
            if mode == 'cfg_missing':
                supplied['index'].pop('chroma_dir')
            else:
                key = 'chroma_dir' if mode == 'cfg_chroma' else 'units_export'
                supplied['index'][key] = str(Path(cfg['index'][key]).with_name('other-target'))
        try:
            pd.recover_approval(supplied, pid)
        except (ValueError, RuntimeError) as exc:
            error = str(exc)
    finally:
        cs.ChromaStore.units_metadata, pd._recovery_classify_live = original_read, original_classify
    if mode == 'unknown_control':
        assert injected
        # Same real operation with the old bad classifier must violate this checker.
        try:
            assert file_state() == before_files, 'unknown state published durable success'
        except AssertionError:
            from conflict_events import load_events
            assert sum(r['event_type'] == 'APPROVED' and r['proposal_id'] == pid for r in load_events(cfg)) == 1
        else:
            raise AssertionError('unknown-to-empty negative control was not detected')
    else:
        assert error is not None, f'recovery unexpectedly succeeded for {mode}'
        assert file_state() == before_files, 'refusal changed a governed file'
        if mode.startswith('cfg_'):
            assert 'operation' in error or 'cfg' in error, error
        if mode == 'read_error':
            assert injected
        if missing_collection:
            store = cs.ChromaStore(cfg['index']['chroma_dir'], create_collections=False)
            try:
                assert cs.UNITS not in [c.name for c in store.client.list_collections()]
            finally:
                store.close()
        else:
            assert _dump_state(cfg) == before, 'refusal changed corpus/document/vector/export'
    return {'verdict': 'PASS', 'mode': mode, 'refusal': error, 'pid': pid}
