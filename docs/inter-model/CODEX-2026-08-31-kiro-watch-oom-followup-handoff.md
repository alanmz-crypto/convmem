# Investigation Handoff: Repeated ConvMem watch index-child OOMs

**Arc: Trapdoor Hunt**

**Date:** 2026-08-31  
**Author:** OpenAI Codex  
**For:** Kiro (investigation/design review)  
**Authorization:** Ryan, 2026-08-31 (explicit request: “create a handoff for kiro to investigate and mitigate”)

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `NOT_STARTED` |
| **Branch** | `docs/2026-08-31-kiro-watch-oom-followup` |
| **Tip SHA** | see branch tip after this commit |
| **Push status** | pushed to origin after commit |
| **PR** | not opened |
| **Ryan GATE** | none for investigation/design; any runtime configuration or live service change remains Ryan-authorized operational work |
| **Track A ingest** | Codex rollout transcript for this session |

---

## Investigation goal

Determine and specify a safe mitigation for recurring OOM kills of ConvMem’s
watcher indexing children, without losing watched-source coverage or allowing a
runaway child to kill `convmem-watch.service`.

**Why this exists:** The subprocess-scope mitigation is active, but it has not
solved the resource problem. On 2026-08-31, multiple index children reached the
configured 6 GiB cgroup limit and were killed. The parent watcher survived, but
the affected files were left stale and desktop OOM notifications repeated.

---

## Evidence to ground the investigation

The following journal evidence was collected on the host on 2026-08-31:

1. `run-p354623-i339333.scope` started indexing
   `/home/lauer/.codex/history.jsonl` at **15:41:40** and was OOM-killed at
   **16:28:07**.
2. `run-p390909-i408468.scope` started indexing the Cursor transcript
   `~/.cursor/projects/home-lauer-Projects-convmem/agent-transcripts/5eff7386-b091-4f79-ab47-8d28c3051f84/5eff7386-b091-4f79-ab47-8d28c3051f84.jsonl`
   at **16:31:56** and was OOM-killed at **16:36:03**.
3. Both failures reported exactly:
   `usage 6291456kB, limit 6291456kB`, `swap: usage 0kB, limit 0kB`, and
   approximately 6.27 GiB anonymous RSS.
4. After each child failure, the watcher logged a per-file error and launched
   another index job. The watcher PID `342253` remained alive.
5. Ordinary files also showed high peaks: `LATEST.md` reached 5.4 GiB in a
   transient scope.
6. Host swap exists, but the child cgroup is explicitly swap-disabled:
   `/dev/zram0` is 8 GiB and the disk swapfile is 64 GiB; the OOM scope reports
   `swap limit 0`.

Current live configuration observed:

```toml
[watch]
subprocess_memory_max = "6G"
subprocess_memory_high = "6G"
```

The user-service drop-in currently has:

```ini
[Service]
MemoryMax=8G
MemoryHigh=
MemorySwapMax=0
OOMPolicy=continue
```

ConvMem’s direct follow-up answer confirmed that append-only incremental
`history.jsonl` indexing is **not currently documented**. The recorded
recommendation is the subprocess scope bound already implemented in `watch.py`;
the incremental-history idea is a new proposal, not an accepted ConvMem design.

---

## Existing implementation context

- `watch.py:_flush_path_subprocess()` launches one blocking `convmem index --file`
  child per debounced file.
- `watch.py:_scoped_index_cmd()` wraps the child in a transient user scope.
- `ingest.py:_index_one_file()` parses and processes the complete file when its
  content hash changes.
- `adapters/codex_history_jsonl.py:parse()` reads all history records into a
  list; an append causes the complete history file to be processed again.
- `ingest.py:_process_file_chunks()` performs summary generation, summary
  embedding, distillation, unit embedding, dedupe, and Chroma writes across the
  file’s chunks in one child process.
- `ingest_dedupe.py:evaluate_ingest_batch()` queries Chroma for each candidate
  unit before the batch write.

The current repository already has focused regression tests in
`tests/test_watch_subprocess_memcap.py`; they pass along with `tests/test_watch.py`
(26 tests passed in the latest check).

---

## Requested Kiro work

Kiro should investigate and produce a bounded mitigation/design recommendation,
not make runtime changes from this handoff.

1. Establish the dominant allocation source with a reproducible, scratch-only
   profile or targeted instrumentation. Distinguish Python/Chroma growth from
   Ollama-side model memory and from repeated full-file work.
2. Review whether the following are safe and sufficient, individually or in
   combination:
   - append-only cursor/offset indexing for Codex history;
   - bounded file/message batches for all watcher sources;
   - a per-child timeout and explicit retry/backoff policy;
   - a backlog/concurrency gate so the watcher cannot churn through expensive
     children indefinitely;
   - releasing or recreating Chroma/embedding state at a smaller unit of work.
3. Preserve exact source coverage and reindex correctness: truncation, rewrite,
   rotation, duplicate prompts, and crash interruption must not silently lose
   records.
4. Recommend final memory and swap policy from evidence. Do not assume that
   raising `MemoryMax` or enabling swap is a complete fix.
5. Return a Kiro design/review handoff with exact files, tests, acceptance
   criteria, and explicit non-goals. If implementation is warranted, route it
   to Cursor under a separate Execute grant.

---

## Safety and scope locks

- Do not exclude `history.jsonl` or Cursor/Kiro/Copilot transcript sources merely
  to suppress alerts.
- Do not perform live database mutation, bulk indexing, or service reconfiguration
  as part of this investigation.
- Do not edit the user systemd unit or drop-in from the implementation branch;
  live operational settings require a separate Ryan decision.
- Do not add concurrency to the watcher spawn loop.
- Do not claim incremental indexing is already approved or documented.
- Do not cross into R2b, Recovery Authority, Shadow Ledger, or other governed
  operational arcs.

---

## Acceptance criteria for the investigation

- [ ] Dominant memory-growth mechanism is supported by measurements or a clear
      source/code proof.
- [ ] Proposed mitigation preserves watched-source coverage and crash recovery.
- [ ] Proposal addresses both repeated full-file work and child blast radius.
- [ ] Focused test plan covers append, rewrite/truncate, timeout, OOM, retry,
      and backlog behavior as applicable.
- [ ] Kiro explicitly identifies what is design-only versus what Cursor may
      implement under a later grant.
- [ ] No live service or database mutation is performed.

---

## Related files

| What | Path |
|------|------|
| Watch spawn and scope wrapper | `watch.py` |
| Complete-file indexing pipeline | `ingest.py` |
| Codex history parser | `adapters/codex_history_jsonl.py` |
| Ingest-time Chroma dedupe | `ingest_dedupe.py` |
| Existing scope-cap tests | `tests/test_watch_subprocess_memcap.py` |
| Prior scope-cap handoff | `docs/inter-model/KIRO-2026-08-29-watch-oom-subprocess-cap-handoff.md` |
| Current watch OOM status evidence | This handoff's journal evidence section |

---

## Leaving / picking up checklist

**Codex (leaving):**

- [x] Handoff created on a docs branch.
- [ ] Commit and push this handoff.
- [ ] Add a top `LATEST.md` bullet if Ryan wants this lane in the active inbox.

**Kiro (picking up):**

- [ ] Read this handoff and the prior scope-cap handoff.
- [ ] State Goal / Role / System state / Next action.
- [ ] Use ConvMem evidence before proposing a new design.
- [ ] Return a design/review handoff; do not implement runtime code.
