# [Arc Codex] Independent Stage 2 safety and isolation audit

**This audit stands in for the GitHub Copilot audit lane, as Ryan authorized on 2026-10-13.**

**Verdict: FAIL — `c7072fc6821910df21ea4ced7e4a67cff3e99181`.**

Codex independently audited Cursor's issue #286 Stage 2 wedge fixes on
`fix/2026-10-12-issue-286-stage2-wedge-fixes`. The comparison base is fetched
`origin/main`, `458b9f6bb0bf98048c11ac0baf46a2340dcdcbf3`.
The fixes do not yet establish the claimed writer isolation or bound all
repeated transform failures. Rollback can also erase another source's dedupe
records. Five blocking findings follow, most severe first; two narrower
observations follow them. This is a safety verdict, not a deployment grant.

The review used Claude's round-6 Review focus items 1–5 and Cursor's C1–C4
handoff from `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`, then
`git diff origin/main...c7072fc`. The round-6 decision to restore source-owned
export tamper rather than refuse it was treated as the intended behavior.
All implementation file:line references below refer to the audited revision.

## Blocking findings

### F1 — High: rollback deletes foreign dedupe work committed between attempts

**Location:** `incremental_jsonl.py:1640`, called at `incremental_jsonl.py:1734`
from the newly relaxed rollback at `incremental_jsonl.py:2218`.

Rollback still restores the *entire* `dedupe_queue.jsonl` and
`ingest_duplicate_suppressions.jsonl` from transaction-start before-images.
`_restore_file_preimage` deletes a file when its old image was absent. The
per-attempt digest covers the two Chroma collections, not these sidecars.
Holding C1 during rollback cannot protect legitimate writes made between
attempts from being overwritten by the old image.

**Concrete failure:** source A wedges after a summary upsert. Source B then
adds a foreign summary and appends suppression/semantic-candidate records via
`persist_ingest_dedupe`, which correctly takes C1. A's replay fails before its
next summary upsert and rolls back. Both dedupe files are deleted if absent
before A's original attempt, or overwritten with stale contents otherwise.
B's Chroma rows and export line survive, so the isolation check passes and
the result is `rolled_back` despite the lost work.

**Independent evidence:** `test_rollback_erases_foreign_dedupe_added_between_attempts`
reproduced this with real scratch Chroma and the real locked dedupe append.
Both files disappeared; foreign collection digests and export lines remained
equal. The whole-file restore predates this branch, but accepting foreign
growth between attempts makes it incompatible with the new recovery contract.

**Required correction:** make dedupe rollback transaction-scoped, preserving
foreign entries and edits, and test rollback after a cooperating foreign
writer has appended to both files.

### F2 — High: repeat failures can still repeat paid transforms indefinitely

**Location:** `incremental_jsonl.py:2722`–`2730`,
`incremental_jsonl.py:2768`; downstream `watch.py:706`–`740`.

There are two distinct holes in C3:

- The retry backstop catches only `IncrementalJsonlError`. An `OSError`
  saving a completed artifact at `incremental_jsonl.py:1017`, or a
  `ProviderUnavailableError` raised after a successful summary at
  `ingest.py:907`, bypasses it. Ordinary exit-1 errors are neither refusal
  quarantines nor counted native faults/timeouts in the watcher.
- For errors that *are* counted, `coordinator.run()` executes before retry
  state is consulted. With no live watcher, repeated `index --file` calls
  can keep transforming an unchanged source; each returns exit 91 only
  **after** the new work. `--now` likewise does not provide a pre-transform
  wedge check. A complete prepared artifact is reused, but a partially
  successful chunk has no complete artifact to reuse.

**Concrete failures and independent evidence:**

1. Inject a persistent prepared-artifact write error after a fake successful
   transform. Four watcher events produced four summary calls, no
   `retry_state.json`, and no refusal hold.
2. Let summary succeed and distillation raise a synthetic HTTP 402. Four
   watcher events again produced four summary calls and no retry state or
   refusal hold. Different summary/distillation provider availability can
   produce this shape; no actual provider was contacted in the probe.
3. Let summary succeed and distillation exhaust its ordinary retries. Four
   direct route calls on the same bytes produced four summaries; calls 2–4
   reported `wedged_incremental_transaction_transform_failed` *afterward*.

These are incremental-route failures, not the separately deferred legacy P4.
The probes use the real coordinator/build path with fake providers. The
watcher probes substitute only its subprocess transport, converting the
raised exception into the same exit-1 `IndexSubprocessError` it receives from
a failed child.

**Required correction:** classify and durably bound failures escaping after
transform work, and enforce the unchanged-prefix hold before starting new
transform work in both CLI and watcher routes. Preserve complete artifacts.
Define an explicit recovery policy for failures to persist the retry state.

### F3 — High: C1 misses real writers, so foreign mutations can still interleave

**Location:** new locking at `ingest.py:652`–`662` and
`ingest_dedupe.py:300`–`303`; uncovered sinks include
`inter_model_index.py:323`, `refine.py:203`, and `refine.py:388`.

Wrapping the normal legacy chunk writer and dedupe *sidecar append* does
not wrap all legacy or dedupe writers. Inter-model ingestion calls
`store.add_unit` before `export_flock_path` implicitly acquires C1. Refine's
approved semantic dedupe and `chroma_dedupe` mutations never take C1; their
outer production writer boundary is a shared lease, not the exclusive index
lock. The same late-acquisition shape exists in repository knowledge ingestion
at `repository_knowledge_index.py:280`; purge deletes collections before its
export lock at `source_purge.py:357` and `source_purge.py:386`.

**Concrete failure:** while source A holds C1 between its attempt digest and
post-apply check, an inter-model document B upserts a unit, then waits at its
export lock. A sees B's changed collection and fails isolation. An approved
refine tombstone on B can likewise mutate metadata while A holds C1. Thus
`non_source_isolation_changed` still has a cooperating production-writer
explanation; it is not proof of an unauthorized writer.

**Independent evidence:** with one thread holding the real C1 lock, a second
thread executed the actual semantic-dedupe tombstone helper against a fake
store. Its metadata write completed at index-lock depth 0 before release.
The parent refine routes were inspected and contain no enclosing C1 lock.

**Required correction:** cover the actual Chroma mutation windows for the
remaining production routes, including the explicitly required dedupe
writers. Test actual entrypoints concurrently, not only two calls to the
lock helper (the current test named `test_legacy_write_blocks_during_index_write_lock`
only exercises the helper).

### F4 — Medium: add/monitor embed under C1, and the specified order is not enforced

**Location:** `convmem.py:441`–`455`, `monitor.py:381`–`382`,
`observe.py:113` and `observe.py:125`; guard `purge_locks.py:65`–`76`.

`add` takes C1 around `ingest_observation` / `ingest_observation_file`, which
perform embedding inside that scope. Monitor does the same for every
observation. Both take the Chroma writer session before C1, as does `forget`
at `convmem.py:1801`. `forget` additionally waits for interactive confirmation
while holding C1 at `convmem.py:1838`.

**Concrete failure:** an embedding provider stalls during `add --file`; all
incremental and normal legacy writers wait on the global lock until the
provider returns or the process dies. A forgotten `forget` confirmation
prompt has the same global-stall effect. Whether a particular embedding
backend is billed does not change the C1 prohibition on embedding in this
window.

**Independent evidence:** a CLI `add` probe recorded Chroma session entry at
index-lock depth 0 and the fake embedding call at depth 1. A second probe
confirmed `index_write_flock -> source_flock` is accepted by
`assert_lock_ordering_ok`; it checks source-after-export but not
source-after-index, and does not track the Chroma lease ordering.

**Required correction:** separate preparation/confirmation from the mutation
window; acquire and validate locks in the prescribed order. The unchecked
reverse order permits an ABBA cycle if paired with a source-then-index
caller. I did **not** establish a current production call path taking that
reverse source order, so this report does not claim a reproduced production
deadlock. The global provider/prompt stalls are direct call-path findings.

### F5 — Medium: a real Claude transcript can be deferred

**Location:** `watch.py:624`–`635`; `watch.py:138`–`160`.

`should_defer_index_file` has no Claude-format exclusion. `is_watchable`
accepts anything with a parser that is not excluded or a skipped live DB;
Claude's parser is registered. The new deferral test substitutes an
`is_watchable` function that returns false for its synthetic `claude.jsonl`,
so it does not exercise a recognized Claude transcript.

**Concrete failure:** a configured root contains `~/.claude/projects` (for
example, a broader HOME root), and a live watcher owns the singleton PID
lock. `index --file` on a valid Claude session then exits successfully with
the deferral message, contrary to the explicit “never for Claude” exception.

**Independent evidence:** a scratch HOME with a valid
`.claude/projects/project/session.jsonl` produced detection
`jsonl_claude_session`, `is_watchable == True`, and deferral `True`. Only
watcher PID liveness and the processed cache were stubbed; detection and
deferral logic were real.

**Required correction:** explicitly exclude the Claude transcript format from
deferral and add a real-format test under a containing watch root.

## Additional safety observations

### O1 — Medium: the new G7 skip can hide a production writer

**Location:** `eval_corpus/r2b_v2/coverage/inventory.py:313`, `:328`, `:496`.

The skip is an unconditional path-prefix rule, not a check that files are
untracked review artifacts. A tracked or runnable
`review-bundles/production_writer.py` containing a direct production
`ChromaStore(...)` constructor becomes invisible to this scan. A scratch
scan returned no findings for such a file, then detected the exact same file
when moved outside the prefix. No writer was executed.

No files under this prefix are tracked at `c7072fc`; I found no hidden
current production writer there. This is a coverage blind spot, not evidence
of a live bypass. Before accepting the relaxed guard, constrain the exclusion
to non-production artifacts, or explicitly reject tracked/executable writer
code there. `.gitignore` alone is not an execution boundary.

### O2 — Low: an unreadable prefix is treated as a changed prefix

**Location:** `watch.py:618`–`621`, `watch_circuit_breaker.py:121`–`124`.

A held wedge is retried when digest calculation returns an empty string,
not only when a different nonempty digest is established. The probe recorded
a wedge with digest A, verified that A holds, and then verified that `""`
releases that check. A transient read error can therefore spawn another child
without proof of a source-prefix change. This does not itself prove paid
work: a child still unable to read the source fails before transforming.
Retain the hold on an unknown digest if the contract is strictly
“release only on demonstrated prefix change.” The round-6 K1 no-digest edge
also remains a pre-paid retry behavior, not evidence of charges by itself.

## Answers and bounded positive evidence

1. **C2 Chroma/export isolation:** the attempt digest is taken and checked
   under the same C1 hold on apply (`incremental_jsonl.py:2099`, `:2102`,
   `:2134`) and rollback (`:2218`–`:2225`). Normal source-scoped deletion and
   export restoration preserve foreign collection rows and foreign export
   bytes/order in the exercised scenarios. I found no direct foreign
   Chroma/export deletion by the new restore loop. **The whole recovery
   operation is not source-isolated**, because F1 loses foreign sidecars and
   F3 disproves the universal-writer premise. Original rollback authority,
   source identity, prepared-key, and prefix checks remain in the replay path.
2. **C1:** incremental apply, normal legacy chunk commit, legacy snapshot/prune,
   `add`, `forget`, monitor's observation writes, dedupe sidecar persistence,
   and export-lock helpers have C1 coverage. Rollback takes C1 but not the
   common purge `source_flock`; it has the coordinator's separate transaction
   advisory lock. Coverage and order are incomplete, as F3/F4 detail. The
   existing source transaction advisory lock also spans transforms; a literal
   claim that *no kind of lock* spans any provider call is false. No concrete
   production ABBA deadlock was reproduced.
3. **C3/C4:** an established wedge with a matching nonempty prefix is held,
   and a different prefix allows a retry. `rolled_back` remains terminal by
   path until explicit clearing (round-6 G5); it is burn-safe but may stop
   capture indefinitely. Prepared APPLYING recovery reuses artifacts.
   F2/O2 qualify the broader burn and hold claims. Deferral checks watchability,
   configured roots, and a live watcher PID, but F5 violates the Claude
   exception. This audit did not start a watcher.
4. **G3:** the restore loop drops current source-owned lines and writes the
   before-image payload bytes, retaining foreign lines in order. It restores
   placements by foreign-line count where possible and appends remaining
   source lines when foreign lines have shrunk. The diagnostic at
   `incremental_jsonl.py:1834` prints only the count and source path (plus
   fixed explanatory text), not export content. Before-image IDs are compared
   by parsed content; non-before-image IDs present in source store rows may
   be removed without being counted, as round 6 disclosed. The clean-growth
   rollback and real-tamper tests pass. This guarantee assumes valid rollback
   authority and successful filesystem writes; I/O errors can still interrupt
   restoration and are part of F2's retry concern.
5. **G7:** yes, the skip can hide a writer by location; no such tracked writer
   exists at the audited revision. See O1.
6. **Test hermeticity:** reviewed all four changed/new Python test files and
   their relevant helpers. Ran them with `env -i`, scratch HOME/TMPDIR,
   disabled third-party pytest plugin autoload, no credentials, provider
   endpoint overrides at `http://127.0.0.1:9`, and a pre-import guard rejecting
   network connections and opens of live corpus/session paths. Real Chroma
   was confined to temporary paths; providers were fake. This is evidence for
   the prescribed hermetic execution, not a certification of the repository's
   full suite under a normal live HOME.

## Verification and reproducibility

- Detached implementation worktree: `/tmp/convmem-codex-audit-c7072fc`.
- Separate documentation worktree: `/tmp/convmem-codex-audit-docs`, based on
  fetched `origin/main`, on `docs/2026-10-13-issue-286-stage2-fixes-audit`.
- Existing/changed focused tests: **56 passed** in 6.45 seconds:
  `tests/test_issue_286_stage2_wedge_fixes.py`,
  `tests/test_issue_286_stage2_wedge_probes.py`,
  `tests/test_incremental_jsonl_live_boundary.py`,
  `tests/test_incremental_jsonl_canary_baseline.py`.
- Independent audit probes: **10 passed** in 1.69 seconds. These probes assert
  the observed unsafe behavior, so their passing supports **FAIL**, not PASS.
  Full source and the execution guard are preserved below.
- Both runs emitted only an existing importlib-metadata deprecation warning.
- `git diff --check origin/main...c7072fc` passed; the detached implementation
  worktree remained clean. No full-suite claim is made.
- No live `convmem doctor`, `brief`, `unresolved`, `index` (including Track A),
  `watch`, `add`, or `monitor` command was run. The fake CLI `add` probe ran
  only in scratch with its production session replaced. No production code,
  Cursor checkout, runtime pin, live config, or service was changed. No paid
  calls, PR, or merge.

The same command shape was used for both runs, replacing the final test path
with the four repository files for the 56-test run:

```bash
cd /tmp/convmem-codex-audit-c7072fc
env -i \
  HOME=/tmp/convmem-codex-audit-harness/home \
  PATH=/home/lauer/miniforge3/envs/convmem/bin:/usr/bin:/bin \
  PYTHONPATH=/tmp/convmem-codex-audit-harness:/tmp/convmem-codex-audit-c7072fc \
  TMPDIR=/tmp/convmem-codex-audit-harness/tmp \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  OLLAMA_HOST=http://127.0.0.1:9 \
  OPENAI_BASE_URL=http://127.0.0.1:9 \
  DEEPSEEK_BASE_URL=http://127.0.0.1:9 \
  ANONYMIZED_TELEMETRY=False \
  /home/lauer/miniforge3/envs/convmem/bin/python -m pytest -q \
  /tmp/convmem-codex-audit-harness/test_audit.py
```

Provider stubs do not make HTTP requests. The explicit route fixture also
sets the model's DeepSeek base URL to port 9. The guard denies all socket
connections, including that port, if a fake is missed. Two initial probe
drafts were corrected before the final run: a `None` distill return was not a
valid failure simulation, and HTTP 503 is retried/degraded rather than the
fatal-refusal path (the latter probe uses 402). These were harness corrections,
not implementation edits or evidence against additional code paths.

## [Arc Codex] Disposition

I finished: independent safety and isolation audit of the pinned Stage 2 fixes.
Next step: Cursor corrects F1–F5 and addresses O1/O2's explicit contract decisions;
then obtain fresh verification and exact-revision safety/design verdicts.
Next lane: Ryan to route the findings; Cursor for any authorized corrective work.
See my work: this audit, beginning with F1–F5; probe source is in the appendix.

Claude's round-6 readiness statement is not the independent safety verdict.
This report does not infer a Sol-High conflict: no same-artifact,
same-revision opposing Kiro PASS/FAIL was established in this audit.

Suggested eventual docs PR title (no PR created):
`Document safety blockers in Stage 2 incremental recovery fixes`.

Suggested description: “Records Codex's Ryan-authorized independent safety
audit, standing in for the Copilot lane, of Cursor's issue #286 fixes at
`c7072fc`. The audit finds cross-source dedupe loss, retry burn gaps, incomplete
writer locking, provider work inside C1, and Claude deferral. It includes
56 passing focused tests and 10 reproducible probes of unsafe behavior;
production remains unchanged. TL;DR: safety verdict FAIL; corrective review
is required.”

## Appendix: independent probes

The helper imports below come from the pinned implementation worktree.
Extract the two code blocks to the harness paths used in the command above.
Create its empty `home/` and `tmp/` directories before running.

<details>
<summary>sitecustomize.py</summary>

```python
import os
import socket
import sys

def denied_network(*args, **kwargs):
    raise RuntimeError('AUDIT: network disabled')

socket.socket.connect = denied_network
socket.socket.connect_ex = denied_network
socket.create_connection = denied_network

def guard(event, args):
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.fsdecode(args[0])
        absolute = os.path.abspath(path)
        forbidden = ('/home/lauer/.local/share/convmem', '/home/lauer/.config/convmem',
                     '/home/lauer/.codex', '/home/lauer/.kiro', '/home/lauer/.cursor',
                     '/home/lauer/Projects/convmem/')
        if any(absolute == p or absolute.startswith(p.rstrip('/') + '/') for p in forbidden):
            raise RuntimeError('AUDIT: live path access denied: ' + absolute)
sys.addaudithook(guard)
```

</details>

<details>
<summary>test_audit.py</summary>

```python
import json
import re
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def test_add_embeds_under_index_lock(tmp_path, monkeypatch):
    import chroma_write_store as cs
    import convmem
    import llm
    from purge_locks import index_write_lock_depth
    from tests.purge_test_util import purge_cfg
    from typer.testing import CliRunner
    cfg = purge_cfg(tmp_path)
    cfg['models'] = {'embed_model': 'fake', 'ollama_host': 'http://127.0.0.1:9'}
    cfg['index']['units_export'] = None
    depths = []
    @contextmanager
    def session(**kwargs):
        depths.append(('session_enter', index_write_lock_depth()))
        yield SimpleNamespace(store=Mock(), live_cfg=cfg)
    def embed(*args, **kwargs):
        depths.append(('embed', index_write_lock_depth()))
        return [0.1] * 8
    monkeypatch.setattr(convmem, '_guard_write', lambda: None)
    monkeypatch.setattr(cs, 'production_chroma_write_session', session)
    monkeypatch.setattr(llm, 'ollama_embed', embed)
    result = CliRunner().invoke(convmem.app, ['add', '--title', 'Audit example',
        '--summary', 'A valid observation from a hermetic audit.', '--author', 'audit',
        '--keyword', 'one', '--keyword', 'two', '--keyword', 'three'])
    assert result.exit_code == 0, (result.output, result.exception)
    assert depths == [('session_enter', 0), ('embed', 1)]


def test_refine_writes_while_other_thread_holds_index_lock(tmp_path, monkeypatch):
    import refine
    from purge_locks import index_write_flock, index_write_lock_depth
    from tests.purge_test_util import purge_cfg
    cfg = purge_cfg(tmp_path)
    store = Mock()
    store.chroma_dir = cfg['index']['chroma_dir']
    store.get_unit.side_effect = lambda uid: {'id': uid, 'metadata': {'id': uid}}
    writes = []
    store.update_unit_metadata.side_effect = lambda *args: writes.append(index_write_lock_depth())
    monkeypatch.setattr(refine, 'write_undo_snapshot', lambda *args: None)
    monkeypatch.setattr(refine, 'invalidate_superseded_cache', lambda *args: None)
    done = threading.Event()
    errors = []
    def contender():
        try:
            refine._tombstone_semantic_duplicate(store, cfg, tombstone_id='a', canonical_id='b', verbose=False)
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()
    with index_write_flock(cfg):
        worker = threading.Thread(target=contender)
        worker.start()
        completed_while_locked = done.wait(2)
    worker.join(2)
    assert not errors, errors
    assert completed_while_locked and writes == [0]


def test_claude_is_deferred_under_broad_watch_root(tmp_path, monkeypatch):
    import watch
    from adapters.detect import detect_format
    monkeypatch.setenv('HOME', str(tmp_path))
    source = tmp_path / '.claude/projects/project/session.jsonl'
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps({'sessionId': 'audit-session', 'type': 'user',
        'message': {'role': 'user', 'content': 'test'}}) + '\n')
    monkeypatch.setattr(watch, '_processed_cache', {})
    monkeypatch.setattr(watch, '_is_live_watch_pid', lambda pid: True)
    lock = tmp_path / 'watch.lock'
    lock.write_text('999999\n')
    cfg = {'watch': {'paths': [str(tmp_path)], 'lock_file': str(lock)}}
    assert detect_format(str(source)) == 'jsonl_claude_session'
    assert watch.is_watchable(source)
    assert watch.should_defer_index_file(cfg, str(source))


def test_review_bundle_writer_is_invisible(tmp_path, monkeypatch):
    from eval_corpus.r2b_v2.coverage import inventory
    bundle = tmp_path / 'review-bundles/production_writer.py'
    bundle.parent.mkdir()
    bundle.write_text('from chroma_store import ChromaStore\n'
        'store = ChromaStore("~/.local/share/convmem/chroma")\n')
    manifest = tmp_path / 'shadow.json'
    manifest.write_text('{"allowlisted_direct_sites": []}')
    monkeypatch.setattr(inventory, 'ROOT', tmp_path)
    monkeypatch.setattr(inventory, 'SHADOW_INVENTORY', manifest)
    assert inventory._scan_chroma_ctor_uncached() == []
    bundle.rename(tmp_path / 'production_writer.py')
    assert inventory._scan_chroma_ctor_uncached() == ['production_writer.py:2']


def _route_fixture(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    from tests.test_issue_286_stage2_wedge_probes import _codex_env, _route
    from tests.test_incremental_jsonl_codex_rollout_route import _write_user_config
    from tests.incremental_jsonl_helpers import install_fakes
    from incremental_jsonl_production import ProductionBoundary
    source, cfg = _codex_env(tmp_path, monkeypatch)
    cfg['models']['deepseek_base_url'] = 'http://127.0.0.1:9'
    config_path = tmp_path / 'config.toml'
    _write_user_config(config_path, cfg)
    install_fakes(monkeypatch)
    class ScratchBoundary(ProductionBoundary):
        def __init__(self, cfg, path):
            super().__init__(cfg, path, config_path=config_path)
    monkeypatch.setattr(inc, 'ProductionBoundary', ScratchBoundary)
    return source, cfg, lambda: _route(cfg, source)


def test_prepared_write_oserror_repeats_transform_on_every_watch_event(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import ingest
    import watch
    from tests.incremental_jsonl_helpers import fake_summarize
    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = []
    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)
    def fail_save(*args, **kwargs):
        raise OSError('simulated prepared-artifact write failure')
    monkeypatch.setattr(ingest, 'summarize', summarize)
    monkeypatch.setattr(inc.IncrementalJsonlCoordinator, '_write_prepared', fail_save)
    def flush(path, **kwargs):
        try:
            route()
        except OSError as exc:
            raise watch.IndexSubprocessError(str(exc), returncode=1, stderr=str(exc)) from exc
    monkeypatch.setattr(watch, 'flush_path', flush)
    breaker = watch.CircuitBreakerState(tmp_path / 'breaker.json')
    for _ in range(4):
        watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert len(calls) == 4
    assert not breaker.has_refusal_quarantine_for_path(str(source))
    assert not list((tmp_path / 'data').rglob('retry_state.json'))


def test_manual_retries_transform_before_checking_retry_state(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import ingest
    from tests.incremental_jsonl_helpers import fake_summarize
    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = []
    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)
    # A successful summary followed by a failed/degraded distillation leaves
    # no complete artifact to reuse, and yields transform_failed.
    monkeypatch.setattr(ingest, 'summarize', summarize)
    def failed_distill(*args, **kwargs):
        raise RuntimeError('simulated distill timeout')
    monkeypatch.setattr(ingest, 'distill', failed_distill)
    monkeypatch.setattr(ingest, '_SYNTHESIS_FAIL_LOG', tmp_path / 'synthesis_failures.jsonl')
    errors = []
    for _ in range(4):
        with pytest.raises(inc.IncrementalJsonlError) as caught:
            route()
        errors.append((caught.value.code, caught.value.detail))
    assert len(calls) == 4, (len(calls), errors)
    assert all(code == 'live_route_refused' for code, _ in errors)
    assert all('wedged_incremental_transaction_transform_failed' in detail for _, detail in errors[1:])


def test_provider_refusal_repeats_paid_summary_on_every_watch_event(tmp_path, monkeypatch):
    import incremental_jsonl as inc
    import ingest
    import requests
    import watch
    from tests.incremental_jsonl_helpers import fake_summarize
    source, cfg, route = _route_fixture(tmp_path, monkeypatch)
    calls = []
    def summarize(*args, **kwargs):
        calls.append(1)
        return fake_summarize(*args, **kwargs)
    def failed_distill(*args, **kwargs):
        response = requests.Response()
        response.status_code = 402
        raise requests.HTTPError('synthetic provider unavailable', response=response)
    monkeypatch.setattr(ingest, 'summarize', summarize)
    monkeypatch.setattr(ingest, 'distill', failed_distill)
    monkeypatch.setattr(ingest, '_SYNTHESIS_FAIL_LOG', tmp_path / 'synthesis_failures.jsonl')
    def flush(path, **kwargs):
        try:
            route()
        except ingest.ProviderUnavailableError as exc:
            raise watch.IndexSubprocessError(str(exc), returncode=1, stderr=str(exc)) from exc
    monkeypatch.setattr(watch, 'flush_path', flush)
    breaker = watch.CircuitBreakerState(tmp_path / 'breaker.json')
    for _ in range(4):
        watch._process_ready_path(str(source), cfg=cfg, breaker=breaker, verbose=False)
    assert len(calls) == 4
    assert not breaker.has_refusal_quarantine_for_path(str(source))
    assert not list((tmp_path / 'data').rglob('retry_state.json'))


def test_rollback_erases_foreign_dedupe_added_between_attempts(tmp_path, monkeypatch):
    from tests.test_issue_286_stage2_wedge_probes import _wedge_then_replay
    from ingest_dedupe import IngestDedupeResult, persist_ingest_dedupe
    replay, export, foreign, source = _wedge_then_replay(tmp_path, monkeypatch, 'before_summary_upsert')
    # This is a cooperating C1 writer: its own helper acquires the index lock.
    persist_ingest_dedupe(replay.cfg, IngestDedupeResult(
        exact_suppressions=[{'event_id': 'foreign-event', 'source_path': '/other',
                            'suppressed_id': 'foreign-a', 'matched_id': 'foreign-b'}],
        semantic_candidates=[{'id_a': 'foreign-a', 'id_b': 'foreign-b', 'status': 'pending'}]))
    paths = replay._dedupe_restore_paths()
    assert all(p.exists() and p.read_bytes() for p in paths.values())
    before_foreign_rows = replay._non_source_collection_digest()
    before_foreign_lines = [line for line in export.read_bytes().splitlines(keepends=True)
                            if not replay._export_line_owned_by_source(line, str(source))]
    result = replay.run()
    assert result.outcome == 'rolled_back'
    assert all(not p.exists() for p in paths.values())
    assert foreign.encode() in export.read_bytes()
    assert replay._non_source_collection_digest() == before_foreign_rows
    assert [line for line in export.read_bytes().splitlines(keepends=True)
            if not replay._export_line_owned_by_source(line, str(source))] == before_foreign_lines


def test_lock_guard_accepts_reversed_index_then_source(tmp_path):
    from purge_locks import index_write_flock, source_flock, source_lock_depth
    from tests.purge_test_util import purge_cfg
    cfg = purge_cfg(tmp_path)
    with index_write_flock(cfg):
        with source_flock(cfg, '/audit/source'):
            assert source_lock_depth() == 1


def test_wedge_digest_failure_releases_hold(tmp_path):
    from watch_circuit_breaker import CircuitBreakerState
    breaker = CircuitBreakerState(tmp_path / 'breaker.json')
    breaker.record_refusal('/audit/source', outcome='wedged_incremental_transaction_recovery_unproven',
                           prefix_digest='a' * 64)
    assert breaker.should_skip_refusal_quarantine('/audit/source', 'a' * 64)
    assert not breaker.should_skip_refusal_quarantine('/audit/source', '')
```

</details>

**TL;DR:** [Arc Codex] **FAIL at `c7072fc`**. Rollback can erase foreign dedupe work, retry paths can repeat paid transforms, and C1/Claude deferral requirements remain incomplete. All audit execution was hermetic; only this documentation branch is being published.
