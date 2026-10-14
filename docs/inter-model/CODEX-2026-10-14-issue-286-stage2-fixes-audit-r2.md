# [Arc Codex] Stage 2 independent safety and isolation audit — round 2

**This audit stands in for the GitHub Copilot audit lane, as Ryan authorized on 2026-10-13.**

**Verdict: FAIL — `0ee6994467ac4621d81651f1a095c70a15e7f9b6`.**

**Auditor:** Codex. **Date:** 2026-10-14. **Implementation owner:** Cursor.
**Target:** `fix/2026-10-12-issue-286-stage2-wedge-fixes`, issue #286 Stage 2 wedge fixes, correctives 6–11 since `c7072fc`.

The common-case corrections pass their focused tests, but four safety findings remain: retry accounting can fail open, rollback can lose a concurrent refine queue append, embedding can still execute under C1, and monitor can publish an export update after its target Chroma row disappeared. This report does not authorize implementation, merge, runtime promotion, providers, or a live canary.

## Scope and evidence identity

I fetched origin and read Claude's round-13 verification and its Astra Review focus items 1–6 from `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`, document `docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md`, at `fcabc465408c40f1c0ac236081144a83941d21d1`. I read the round-1 safety audit, including F1–F5 and O1–O2, from `origin/docs/2026-10-13-issue-286-stage2-fixes-audit` at `e1cec559c8ae6bbed04eddef8cad438923713dea`.

The review compares `git diff origin/main...0ee6994`, weighted toward `git diff c7072fc 0ee6994`. Fetched main and the documentation branch base are `fdc8da7fa67c1d7b31bc5cd44de466001df04260`. All implementation file:line references below refer to **0ee6994**, not the documentation branch. The arc STATUS brief on main was read for orientation; its older activation narrative is not evidence of the current live runtime. No live runtime inspection was performed.

Known #393, Z1, and X2–X4 remain out of scope. No opposing same-revision Kiro verdict was established here; this report does not invoke conflict adjudication.

## Blocking findings

### R2-F1 — High: retry-state persistence failure permits repeated paid transforms

**Locations:** `incremental_retry_state.py:147` (admission check), `incremental_retry_state.py:219` (counter keys), `incremental_retry_state.py:235` (failed write swallowed), `incremental_jsonl.py:2861` (caller interprets false as ordinary first failure).

When `retry_state.json` already exists, `_ensure_retry_state_available` checks only whether it can be read. If it is readable but unwritable, the coordinator performs transform work, then `record_incremental_retry_failure` catches the write's `OSError` and returns `False`. The caller raises the original failure, not `retry_state_unavailable` or a wedge refusal. The unchanged persisted counter remains below the gate on every subsequent invocation.

**Reproduced:** after one synthetic prepared-artifact failure, I changed the scratch retry file to mode `0400` and invoked the real production route four more times. All five invocations called the fake summary provider. The last four raised `artifact_write_failed`; retry-state bytes remained identical to the initial one-failure record. No complete prepared artifact existed to reuse. This is a filesystem permission failure, not a mocked retry-state implementation. The ordinary exit-1 path also lacks the watcher's refusal hold, so the original round-1 F2 persistence-policy requirement is still unmet.

There is a second accounting gap: both `consecutive` and `source_consecutive` reset when the error code changes. Alternating a prepared-artifact `OSError` and `ValueError` on unchanged input produced **six summaries in six attempts**, with both counters still `1`. Thus the source hold is a same-error hold, not an overall bound on repeated unsuccessful paid attempts. This secondary probe uses synthetic alternating faults; it demonstrates the counter semantics, not observed live provider behavior.

**Required correction:** make inability to durably record an attempt fail closed, including when persistence fails after admission. A preflight read or write probe alone cannot cover later disk errors. Preserve complete prepared work, and use an attempt reservation/recovery policy that survives process exit. Bound repeated unsuccessful work independently of the last exception category, or explicitly adopt a narrower contract that does not claim general burn containment. Add real-route tests for unwritable existing state, post-admission persistence failure, and mixed failure codes.

### R2-F2 — High: refine's unlocked dedupe append can be erased by locked rollback

**Locations:** `refine.py:663` (semantic queue append without C1), `incremental_jsonl.py:1651` (read current sidecar), `incremental_jsonl.py:1676` (replace from that snapshot). Related stale-snapshot window: `refine.py:318` loads the approval queue before C1 at `refine.py:338` and later rewrites it at `refine.py:363`.

Transaction-scoped filtering fixes the original whole-file-before-image loss when foreign work is already present before rollback reads the sidecar. It does not protect against an actual production writer that ignores C1. `job_semantic_dedupe` still appends to `dedupe_queue.jsonl` without the index lock. A rollback reads the queue under C1; refine appends; rollback replaces the file from its earlier in-memory lines. Refine's new candidate disappears even though it belongs to another operation.

**Reproduced:** the real rollback sidecar helper held C1. At the read/replace seam, a second thread ran the actual `job_semantic_dedupe` with two fake vector candidates. That thread completed at index-lock depth **0**, reported one queued candidate, and its row was visible on disk. Rollback then replaced the file; the candidate disappeared while the earlier foreign row remained. Only the vector reader was faked; the queue append, filesystem, lock, and rollback filter were real. The test starts from the repository's real scratch wedge/replay fixture.

The approval route also reads `rows` before acquiring C1. Even adding a lock to the append is insufficient if approval later writes a snapshot taken before a cooperating append. This second window is a code-path finding, not an additional executed probe.

**Required correction:** put all queue appends and read-modify-write operations under the same lock. Acquire it before reading the queue for approval, or reload and merge under the lock. Keep vector reads and any provider work outside the mutation window. Test actual refine operations against rollback and ingestion appends, rather than only lock-helper exclusion.

### R2-F3 — Medium: provider work still occurs inside C1 and an open write session

**Locations:** `observe.py:170`–`173`, `observe.py:346`–`356`; callers `convmem.py:510`–`529` and `propose_decision.py:569`–`586`. Unconditional fast path: `propose_decision.py:611`–`626`. Additional inspected path: `observe.py:410`–`466`, empty-document repair.

Batch preparation uses `embedding=None` to mean an unchanged readonly row. During commit, `ingest_observation_file` calls `ingest_observation` again with that `None`. If another cooperating writer changed or removed the row between preparation and commit, the fresh check no longer finds it unchanged. `prepare_observation_ingest` then calls `ollama_embed` while its caller holds C1 and the production Chroma session.

**Reproduced with real scratch Chroma and the real production session:** prepare an unchanged observation file, assert its prepared embedding is `None`, change its stored document through a cooperating locked writer, then commit the prepared batch. The fake embedding provider recorded `(index_write_lock_depth, production_chroma_store_session_depth) == (1, 1)`. Both `add --file --upsert` and approved-file ingest use this batch path.

Separately, `ingest_approved_ledger`, the single-approved-record fast path, still invokes unprepared observation ingest inside both scopes. Its independent probe likewise recorded `(1, 1)` for the embedding call. Empty-document repair has the same direct call shape by inspection. These paths were modified to acquire C1 in the reviewed corrective range.

**Failure scenario:** a slow or stalled embedding endpoint monopolizes the store-wide write lock, blocking unrelated incremental apply/rollback and ordinary writers. No claim of a reproduced ABBA deadlock or actual billed call is made.

**Required correction:** commit must never fall back to provider work. Distinguish “unchanged at preparation” from “embedding missing”; on drift, release the write scope and reprepare or refuse. Move the single-record and repair preparation outside their mutation scopes too. Test provider/session depths with a real interleaving between readonly preparation and commit.

### R2-F4 — Medium: monitor trusts a stale prepared target and exports a nonexistent update

**Locations:** `observe.py:209`–`222`, reached by `monitor.py:394` and `monitor.py:594`–`598`.

Monitor freezes its upsert/skip decision and target Chroma ID against the readonly snapshot, then commits that decision later. `commit_observation_ingest` does not revalidate a skipped row or resolve the current target before using `existing_chroma_id`. Although `ChromaStore.update_unit` reads the target for provenance checks, a missing row is not an error: its native operation is Chroma `update`, not `upsert`. The observation helper nevertheless marks the result `_upserted` and writes the export line.

**Reproduced with real scratch Chroma:** prepare a changed monitor observation from the readonly reader; delete the target via a cooperating C1 writer; commit the prepared observation under the real C1/session. The result reports `_upserted=True` and the export contains its ID, but `get_unit(id)` remains `None`. A companion mock probe confirms the observation commit helper itself makes no fresh target lookup. This exercises monitor's actual prepare/commit functions, not a complete HTTP monitor invocation.

**Failure scenario:** a concurrent purge or other deletion between monitor's probes and final commit produces a successful-looking monitor result and an export-only row. An unchanged prepared row can likewise be skipped after it changed or disappeared. Holding C1 only at the final write does not make the earlier decision current.

**Required correction:** revalidate existence, current identity, and skip/update eligibility under C1. Refuse or deliberately reprepare/re-resolve on drift; do not implicitly resurrect a purged row. Publish an export and successful update only after a real store mutation has been established, without embedding inside the lock.

## Disposition of the original findings and the six review-focus items

- **Original F1:** transaction-scoped filtering preserves foreign dedupe entries present before rollback, and its regression passes. **Not fully closed:** concurrent refine appends are still lost (R2-F2).
- **Original F2:** the normal prepared-write, provider-refusal, manual-retry, corrupt-state, and changed-prefix tests pass. **Not fully closed:** R2-F1 permits repeated work when state persistence fails and when failure categories alternate.
- **Original F3 / focus 1:** inter-model indexing, repository ingestion/retirement, purge, refine metadata mutations, and ordinary ingestion now wrap their inspected Chroma mutation windows in C1. The production wrapper rejects missing C1 and a different canonical Chroma target. My independent probe confirms rejection of another store and acceptance of a symlink alias to the same store. I found no exercised Chroma mutation under the wrong-store lock. **Sidecar isolation is still incomplete** as R2-F2 shows; this is not a claim that the wrapper protects raw arbitrary Python access.
- **Original F4 / focus 3:** ordinary `add` and monitor preparation/HTTP probes are outside C1; source-after-index and index-after-open-session order checks are present. `forget` releases its initial session before acquiring C1 for the fresh mutation, so its prompt no longer holds C1. **Not fully closed:** R2-F3. Refine closes its vector reader before semantic candidate processing; that job has no LLM call in this implementation. Backfill LLM work occurs before its write scope.
- **Original F5:** **closed for the exercised contract**. A real recognized Claude transcript beneath a containing watch root is explicitly excluded from deferral; the regression passes.
- **Original O1:** **closed for the tracked-artifact concern**. The scan checks tracked `review-bundles/` Python files, and the real temporary-Git test passes. Untracked review artifacts remain intentionally excluded; this is not a general execution sandbox.
- **Original O2:** **closed for unknown-digest holds**. An empty/unknown current digest retains the wedge hold; a demonstrated different digest releases that watcher check. The regression passes.
- **Focus 2, readonly rows:** the SQLite reader avoids opening a persistent Chroma system. Refine's inspected backfill/stale-source/chroma-dedupe mutation paths fetch write-store metadata before updating; I did not find a new `document`-metadata contamination result in those paths. Monitor's prepared decision remains stale (R2-F4), and batch rechecking can re-enter embedding (R2-F3). These prevent a blanket readonly-to-write safety PASS.
- **Focus 4, burn:** common-case prevention is supported by the 61-test focused run, but the counterexamples in R2-F1 remain. Complete prepared-artifact reuse is not challenged by these partial-transform probes.
- **Focus 5, hermeticity:** the autouse fixture redirects config, default writer lock/attestation/census paths, and incremental state defaults. It is not itself HOME isolation or a network-denial mechanism. This audit additionally uses `env -i`, scratch HOME/TMPDIR, provider fakes, endpoint overrides, and a pre-import audit hook denying Python network connections and live-path opens. The D1 bootstrap test restores its patches in the tested sequence; the following burn/retry probes pass. No full-suite or all-possible-test hermeticity certification is claimed.
- **Focus 6:** #393, Z1, X2–X4 were not re-audited or used as blockers.

## Independent execution and limits

- Implementation worktree: `/home/lauer/.kiro/audit-286-r2/code`, created by `git worktree add --detach ... 0ee6994`; ext4 on `/dev/nvme0n1p2`, not tmpfs. Its tracked files remain unchanged.
- Documentation worktree: `/home/lauer/.kiro/audit-286-r2/docs`, created from fetched `origin/main` on `docs/2026-10-14-issue-286-stage2-fixes-audit-r2`.
- Test interpreter: `/home/lauer/miniforge3/envs/convmem/bin/python`. Every pytest invocation used `env -i`, the scratch HOME, and its own private disk-backed `--basetemp`. No paid provider call occurred; “summary calls” above are counts of fake provider invocations.
- **Focused repository tests: 61 passed**, 15.09 s. Files: `test_issue_286_stage2_wedge_fixes.py`, `test_issue_286_stage2_wedge_probes.py`, `test_issue_286_stage2_corrective6_audit.py`, `test_issue_286_stage2_corrective7_entrypoint.py`, `test_issue_286_stage2_corrective7_q8.py`, and `test_zz_claude_verify8.py`, `8b.py`, `8c.py`, `8d.py`, `9.py`, `10.py` (all under `tests/`, with the full `test_zz_claude_verify` prefix for the numbered suffixes).
- **Independent probes: 8 passed**, 2.14 s. Seven assert the observed unsafe behavior; the eighth checks store binding. Their passing supports the findings, not an implementation PASS. Full source follows.
- **D1 file followed by `test_zz_claude_verify8b.py` and `test_zz_claude_verify8d.py`: 47 passed, 2 skipped, 3 failed**, 6.20 s. The three failures are `test_prefix_route_isolation_hermetic`, `test_injected_kill_blocked_with_phase_evidence`, and `test_phase_order_subset`; their subprocesses report `bwrap: Can't mkdir parents for .../harness/home/.local/share/convmem: Read-only file system`. This matches the environment error described in Claude's round-13 report. I did not independently run main's D1 baseline, so I do not label the failures independently proven baseline-equivalent. The corrected in-process bootstrap test and the subsequent retry probes pass.
- The only warning in the successful runs is the existing importlib-metadata deprecation warning. An initial independent drift-probe setup retained the seed operation's empty process ledger-index cache; the probe was corrected to invalidate that cache before modeling a separate readonly preparation. The final result above uses the corrected setup. A missed initial fake used the invalid endpoint string `offline` and failed URL parsing; no network request occurred.
- `git diff --check origin/main...0ee6994` passed. No full-suite rerun or production verification command was performed.
- No `convmem doctor`, brief, unresolved, index (including Track A), watch service, add command, monitor command, or refine command ran against live data. Repository tests exercise fake/scratch functions and CLI invocations only. No service, runtime pin, live config, corpus, or Cursor checkout content was changed. Git worktree registration necessarily updates shared Git metadata; it does not switch Cursor's checkout. No PR is being created.

## Reproduction

The harness lives outside both worktrees. Its files are reproduced below so the evidence does not depend on retaining local scratch paths. Create `home/` and `tmp/`, save the four blocks under `/home/lauer/.kiro/audit-286-r2/harness/`, and use a fresh private basetemp for each run. The path-specific guard must be adjusted if reproducing in another location.

Independent probes:

```bash
bash /home/lauer/.kiro/audit-286-r2/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r2/harness/base-reproduce \
  -q /home/lauer/.kiro/audit-286-r2/harness/test_audit_r2.py
```

<details>
<summary>sitecustomize.py</summary>

```python
import os
import sys

SAFE = '/home/lauer/.kiro/audit-286-r2'
LIVE = ('/home/lauer/.local/share/convmem', '/home/lauer/.config/convmem', '/home/lauer/.codex/sessions', '/home/lauer/.cursor', '/home/lauer/.kiro/sessions', '/home/lauer/.copilot', '/home/lauer/Projects/convmem')
def audit(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
        raise RuntimeError('AUDIT_NETWORK_DENIED')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        p = os.path.realpath(os.fsdecode(args[0]))
        if any(p == x or p.startswith(x + '/') for x in LIVE):
            raise RuntimeError('AUDIT_LIVE_PATH_DENIED: ' + p)
        flags = args[2] if len(args) > 2 else 0
        if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            if not (p.startswith(SAFE + '/') or p.startswith('/tmp/') or p.startswith('/dev/')):
                raise RuntimeError('AUDIT_WRITE_OUTSIDE_SCRATCH: ' + p)
sys.addaudithook(audit)
```

</details>

<details>
<summary>run-tests.sh</summary>

```bash
#!/bin/sh
cd /home/lauer/.kiro/audit-286-r2/code || exit 1
exec env -i HOME=/home/lauer/.kiro/audit-286-r2/harness/home PATH=/home/lauer/miniforge3/envs/convmem/bin:/usr/bin:/bin PYTHONPATH=/home/lauer/.kiro/audit-286-r2/harness:/home/lauer/.kiro/audit-286-r2/code TMPDIR=/home/lauer/.kiro/audit-286-r2/harness/tmp PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 OLLAMA_HOST=http://127.0.0.1:9 OPENAI_BASE_URL=http://127.0.0.1:9 DEEPSEEK_BASE_URL=http://127.0.0.1:9 ANONYMIZED_TELEMETRY=False /home/lauer/miniforge3/envs/convmem/bin/python -m pytest -p no:cacheprovider "$@"
```

</details>

<details>
<summary>conftest.py</summary>

```python
from tests.conftest import _block_live_config_and_writer_defaults
```

</details>

<details>
<summary>test_audit_r2.py</summary>

```python
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from contextlib import contextmanager
from unittest.mock import Mock
import pytest


def test_readonly_retry_file_allows_unbounded_paid_retries(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_codex_audit import _route_fixture
    from tests.test_zz_claude_verify8b import _count_summaries
    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    def fail(*a, **k):
        raise OSError('prepared write failed')
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, '_write_prepared', fail)
    with pytest.raises(inc.IncrementalJsonlError):
        route()
    state, = list((tmp_path / 'data').rglob('retry_state.json'))
    original = state.read_bytes()
    state.chmod(0o400)
    try:
        for _ in range(4):
            with pytest.raises(inc.IncrementalJsonlError) as caught:
                route()
            assert caught.value.code == 'artifact_write_failed'
    finally:
        state.chmod(0o600)
    assert len(calls) == 5
    assert state.read_bytes() == original


def test_alternating_failures_reset_both_paid_retry_counters(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_zz_codex_audit import _route_fixture
    from tests.test_zz_claude_verify8b import _count_summaries
    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = _count_summaries(monkeypatch)
    def fail(*a, **k):
        if len(calls) % 2:
            raise OSError('prepared write failed')
        raise ValueError('artifact serialization failure')
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, '_write_prepared', fail)
    for _ in range(6):
        with pytest.raises(inc.IncrementalJsonlError):
            route()
    state, = list((tmp_path / 'data').rglob('retry_state.json'))
    assert len(calls) == 6
    assert json.loads(state.read_text())['source_consecutive'] == 1
    assert json.loads(state.read_text())['consecutive'] == 1


def observation():
    return {'id': 'obs_audit_r2', 'title': 'Audit observation',
            'summary': 'A valid observation from the scratch audit.',
            'keywords': ['audit', 'scratch', 'safety'], 'author_model': 'audit',
            'type': 'observation', 'domain': 'coding.tooling', 'confidence': 0.9}


def test_unchanged_preparation_then_drift_embeds_inside_real_c1_session(tmp_path, monkeypatch):
    import llm
    from chroma_store import ChromaStore
    from chroma_write_store import production_chroma_write_session, production_chroma_store_session_depth
    from chroma_readonly import open_readonly_unit_store
    from purge_locks import index_write_flock, index_write_lock_depth
    from observe import ingest_observation, prepare_observation_file_rows, ingest_observation_file
    from tests.test_zz_claude_verify9 import _real_session_env
    cfg = _real_session_env(tmp_path, monkeypatch)
    record = observation()
    seed = ChromaStore(cfg['index']['chroma_dir'])
    unit = ingest_observation(record, store=seed, embed_model='fake', ollama_host='offline', upsert=True, precomputed_embedding=[0.1,0.2,0.3])
    seed.close()
    from ledger import invalidate_ledger_index_cache
    invalidate_ledger_index_cache(cfg['index']['chroma_dir'])
    path = tmp_path / 'observations.jsonl'
    path.write_text(json.dumps(record) + '\n')
    reader = open_readonly_unit_store(cfg['index']['chroma_dir'])
    monkeypatch.setattr(llm, 'ollama_embed', lambda *a, **k: [0.1,0.2,0.3])
    rows, _ = prepare_observation_file_rows(str(path), embed_store=reader, embed_model='fake', ollama_host='offline', upsert=True)
    assert rows[0][2] is None, (reader.units_metadata(), reader.get_unit(unit['id']), unit)
    # A cooperating writer changes the durable text after preparation.
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint='audit.drift') as session:
            fresh = session.store.get_unit(unit['id'])
            session.store.update_unit(unit['id'], 'changed after preparation', [0.1,0.2,0.3], fresh['metadata'])
    depths = []
    def embed(*a, **k):
        depths.append((index_write_lock_depth(), production_chroma_store_session_depth()))
        return [0.1,0.2,0.3]
    monkeypatch.setattr(llm, 'ollama_embed', embed)
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint='audit.commit') as session:
            ingest_observation_file(str(path), store=session.store, embed_model='fake', ollama_host='offline', upsert=True, prepared_rows=rows, verbose=False)
    assert depths == [(1, 1)]


def test_prepared_monitor_update_never_rechecks_missing_target(tmp_path, monkeypatch):
    from observe import prepare_observation_ingest, commit_observation_ingest
    reader = Mock()
    reader.get_unit.return_value = {'id': 'old', 'metadata': {}, 'document': 'old text'}
    prepared = prepare_observation_ingest(observation(), store=reader, embed_model='fake', ollama_host='offline', upsert=True,
        by_ledger_id={'obs_audit_r2': {'id': 'old'}}, precomputed_embedding=[0.1,0.2,0.3])
    assert prepared.existing_chroma_id == 'old'
    writer = Mock()
    writer.get_unit.return_value = None
    commit_observation_ingest(prepared, store=writer)
    writer.get_unit.assert_not_called()
    writer.update_unit.assert_called_once()


def test_refine_queue_append_is_lost_by_locked_rollback(tmp_path, monkeypatch):
    import refine
    from purge_locks import index_write_flock, index_write_lock_depth
    from tests.test_issue_286_stage2_wedge_probes import _wedge_then_replay
    replay, _, _, _ = _wedge_then_replay(tmp_path, monkeypatch, 'before_summary_upsert')
    queue = replay._dedupe_restore_paths()['dedupe_queue.jsonl']
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text(json.dumps({'event_id': 'keep', 'transaction_id': 'foreign'}) + '\n' + json.dumps({'event_id': 'remove', 'transaction_id': 'mine'}) + '\n')
    vectors = Mock()
    vectors.get_units_with_embeddings.return_value = [
        {'id': 'a', 'metadata': {'domain': 'general'}, 'embedding': [1.0, 0.0]},
        {'id': 'b', 'metadata': {'domain': 'general'}, 'embedding': [1.0, 0.0]}]
    monkeypatch.setattr(refine, 'ChromaStore', lambda *a, **k: vectors)
    real_temp = replay._export_temp
    observed = []
    errors = []
    def temp(path):
        if path == queue:
            def append():
                try:
                    observed.append(index_write_lock_depth())
                    result = refine.job_semantic_dedupe(None, replay.cfg, verbose=False)
                    assert result['queued'] == 1
                except BaseException as exc:
                    errors.append(exc)
            thread = threading.Thread(target=append)
            thread.start()
            thread.join(2)
            assert not thread.is_alive()
            assert not errors, errors
            assert '"id_a": "a"' in queue.read_text()
        return real_temp(path)
    monkeypatch.setattr(replay, '_export_temp', temp)
    with index_write_flock(replay.cfg):
        replay._restore_dedupe_files('mine')
    assert observed == [0]
    assert '"id_a": "a"' not in queue.read_text()
    assert '"event_id": "keep"' in queue.read_text()


def test_approved_single_ledger_embeds_under_c1(tmp_path, monkeypatch):
    import llm
    import propose_decision
    from purge_locks import index_write_lock_depth
    from chroma_write_store import production_chroma_store_session_depth
    from tests.test_zz_claude_verify9 import _real_session_env
    cfg = _real_session_env(tmp_path, monkeypatch)
    depths = []
    def embed(*a, **k):
        depths.append((index_write_lock_depth(), production_chroma_store_session_depth()))
        return [0.1,0.2,0.3]
    monkeypatch.setattr(llm, 'ollama_embed', embed)
    result = propose_decision.ingest_approved_ledger(cfg, observation())
    assert result['accepted'] == 1
    assert depths == [(1,1)]


def test_monitor_prepared_update_exports_a_row_deleted_before_commit(tmp_path, monkeypatch):
    from tests.test_zz_claude_verify9 import _real_session_env
    from chroma_store import ChromaStore
    from chroma_readonly import open_readonly_unit_store
    from chroma_write_store import production_chroma_write_session
    from purge_locks import index_write_flock
    from ledger import invalidate_ledger_index_cache
    from observe import ingest_observation, prepare_observation_ingest, commit_observation_ingest
    cfg = _real_session_env(tmp_path, monkeypatch)
    record = observation()
    seed = ChromaStore(cfg['index']['chroma_dir'])
    unit = ingest_observation(record, store=seed, embed_model='fake', ollama_host='offline', upsert=True, precomputed_embedding=[0.1,0.2,0.3])
    seed.close()
    invalidate_ledger_index_cache(cfg['index']['chroma_dir'])
    reader = open_readonly_unit_store(cfg['index']['chroma_dir'])
    prepared = prepare_observation_ingest({**record, 'summary': 'New monitor result'}, store=reader, embed_model='fake', ollama_host='offline', upsert=True, precomputed_embedding=[0.1,0.2,0.3])
    assert prepared.existing_chroma_id == unit['id']
    export = tmp_path / 'monitor-export.jsonl'
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint='audit.delete') as session:
            session.store.delete_units_for_source(unit['source_path'])
            assert session.store.get_unit(unit['id']) is None
    with index_write_flock(cfg):
        with production_chroma_write_session(entrypoint='audit.commit') as session:
            result = commit_observation_ingest(prepared, store=session.store, units_export=export)
            assert result['_upserted'] is True
            assert session.store.get_unit(unit['id']) is None
    assert json.loads(export.read_text())['id'] == unit['id']


def test_guard_rejects_wrong_store_and_accepts_canonical_alias(tmp_path):
    from chroma_write_store import _IndexWriteGuardedChromaStore
    from purge_locks import index_write_flock
    cfg = {'index': {'chroma_dir': str(tmp_path / 'a' / 'chroma')}}
    wrong = Mock()
    wrong.chroma_dir = str(tmp_path / 'b' / 'chroma')
    guarded = _IndexWriteGuardedChromaStore(wrong)
    with index_write_flock(cfg):
        with pytest.raises(RuntimeError, match='not'):
            guarded.add_unit('a', 'doc', [1.], {})
    wrong.add_unit.assert_not_called()
    target = tmp_path / 'a' / 'chroma'
    target.mkdir(parents=True)
    alias = tmp_path / 'alias'
    alias.symlink_to(target, target_is_directory=True)
    right = Mock()
    right.chroma_dir = str(alias)
    with index_write_flock(cfg):
        _IndexWriteGuardedChromaStore(right).add_unit('a', 'doc', [1.], {})
    right.add_unit.assert_called_once()
```

</details>

## [Arc Codex] Handoff

I finished: independent round-2 safety and isolation audit of `0ee6994` — **FAIL**.
Next step: Ryan routes R2-F1–F4 to Cursor for authorized correction, followed by targeted verification and exact-revision safety/design review.
Next lane: Ryan for disposition; Cursor for implementation if authorized.
See my work: this report's four blocking findings and executable probe appendix.

Documentation branch: `docs/2026-10-14-issue-286-stage2-fixes-audit-r2`, based on `fdc8da7fa67c1d7b31bc5cd44de466001df04260`. The report is the only tracked change. Commit SHA and explicit-refspec push result are reported in the chat handoff. No PR requested or created.

Optional later PR title: **Document remaining Stage 2 recovery safety gaps**.

Optional later PR description: Records Codex's independent round-2 safety audit of Cursor's issue #286 fixes at `0ee6994`, standing in for the Copilot audit lane under Ryan's October 13 authorization. The report identifies four blockers and supplies reproducible scratch probes so Cursor can correct them before another exact-revision review. Focused tests: 61 passed; independent probes: 8 passed; D1 sequence: 47 passed, 2 skipped, 3 scratch-HOME bwrap failures. Production is unchanged. **TL;DR:** safety verdict FAIL; this PR would publish audit evidence only.

**TL;DR:** [Arc Codex] **FAIL at `0ee6994`**. Retry persistence can fail open, concurrent refine queue work can be lost, embedding can hold C1, and monitor can export a stale update with no Chroma row. Focused regressions pass, but the independent counterexamples block safety approval. No live operations, paid calls, or PR.
