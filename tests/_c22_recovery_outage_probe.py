"""Claude round 29: recovery with the embedding provider down, then back (real embed gate, fake transport)."""
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('c22_common', ROOT/'tests/_safe_harbor_t4_common.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
helpers._require_child_isolation()
helpers._refuse_outside_fixture(Path(os.environ['CONVMEM_CONFIG']))
import llm
real_embed = llm.ollama_embed
helpers._install_fakes()
fake_embed = llm.ollama_embed
state = {'down': True, 'http': 0, 'depths': []}

def post(url, *, json, timeout):
    state['http'] += 1
    if state['down']:
        raise ConnectionError('ollama down (probe)')
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'embedding': fake_embed(json['prompt'])}
    return Response()

def embed(*args, **kwargs):
    import purge_locks
    import chroma_write_store
    state['depths'].append((purge_locks.index_write_lock_depth(),
                            chroma_write_store.production_chroma_store_session_depth()))
    return real_embed(*args, **kwargs)

llm.requests.post = post
llm.ollama_embed = embed
case = sys.argv[1]
out = {'case': case}
try:
    cfg = helpers._load_cfg()
    if case == 'create_absence_down_then_up':
        pid = helpers._setup_approval_started(cfg)
        before = helpers._dump_state(cfg)
        try:
            helpers._recover(cfg, pid)
            raise AssertionError('recovery succeeded with the provider down')
        except ValueError as exc:
            out['down_error'] = str(exc)
            assert 'recovery deferred (embedding unavailable' in str(exc), exc
        mid = helpers._dump_state(cfg)
        assert mid == before, 'deferred recovery changed state'
        assert helpers._lifecycle_state(cfg, pid) == 'APPROVAL_STARTED'
        state['down'] = False
        out['action'] = helpers._recover(cfg, pid)
        assert out['action'] == 'retry_chroma'
        assert helpers._lifecycle_state(cfg, pid) == 'APPROVED'
        unit = helpers._unit_for_pid(helpers._dump_state(cfg), pid)
        assert unit['metadata'].get('content_hash') == helpers._independent_ingest_hash(helpers._approved_row(cfg, pid))
        assert unit.get('embedding_sha') == helpers._expected_embedding_sha(unit.get('document') or '')
    elif case in ('event_only_down', 'marker_repair_down'):
        out.update(getattr(helpers, '_matrix_' + case[:-5])(cfg))
    else:
        raise AssertionError(case)
    assert all(d == (0, 0) for d in state['depths']), state['depths']
    out.setdefault('verdict', 'PASS')
except Exception as exc:  # noqa: BLE001
    out.update(verdict='FAIL', error=str(exc), type=type(exc).__name__, traceback=traceback.format_exc())
out.update(http=state['http'], depths=state['depths'])
print(json.dumps(out, sort_keys=True))
raise SystemExit(0 if out['verdict'] == 'PASS' else 1)
