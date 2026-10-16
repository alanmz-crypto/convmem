# pylint: disable=duplicate-code
"""Preserve real embedding admission; fake only the HTTP transport in T4 recovery."""
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('r7_common', ROOT/'tests/_safe_harbor_t4_common.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
helpers._require_child_isolation()  # pylint: disable=protected-access
helpers._refuse_outside_fixture(Path(os.environ['CONVMEM_CONFIG']))  # pylint: disable=protected-access
import llm  # pylint: disable=wrong-import-position
real_embed = llm.ollama_embed
helpers._install_fakes()  # pylint: disable=protected-access
fake_embed = llm.ollama_embed
calls = []
transport = []

def post(url, *, json, timeout):  # pylint: disable=redefined-outer-name, unused-argument
    assert url.endswith('/api/embeddings'), url
    transport.append(url)
    class Response:
        def raise_for_status(self): pass  # pylint: disable=multiple-statements
        def json(self): return {'embedding': fake_embed(json['prompt'])}  # pylint: disable=multiple-statements
    return Response()

def embed(*args, **kwargs):
    import purge_locks
    import chroma_write_store
    calls.append({'c1_depth': getattr(purge_locks,'index_write_lock_depth',lambda:0)(),
                  'session_depth': getattr(chroma_write_store,'production_chroma_store_session_depth',lambda:0)()})
    return real_embed(*args, **kwargs)

llm.requests.post = post
llm.ollama_embed = embed
try:
    cfg = helpers._load_cfg()  # pylint: disable=protected-access
    payload = getattr(helpers, '_matrix_' + sys.argv[1])(cfg)
except Exception as exc:  # pylint: disable=broad-exception-caught
    payload = {'verdict':'FAIL','error':str(exc),'type':type(exc).__name__,'traceback':traceback.format_exc()}
payload.update(embed_entries=calls, fake_http_calls=len(transport), case=sys.argv[1])
print(json.dumps(payload,sort_keys=True))
raise SystemExit(0 if payload['verdict']=='PASS' else 1)

# src: /home/lauer/.cache/audit-286-r7/code/tests/_safe_harbor_t4_common.py — existing isolated recovery scenarios
