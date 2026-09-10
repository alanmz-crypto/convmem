# Implementation Handoff: Isolated live-source JSONL canary

**Date:** 2026-09-09  
**Author:** Codex planning lane  
**For:** Codex Luna-High implementation lane  
**Authorization:** Ryan, 2026-09-09 ("Let's move ahead")  
**Arc:** none (ad-hoc)

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` |
| **Grant branch** | `plan/2026-09-09-jsonl-incremental-live-source-canary` |
| **Execute branch** | `feat/2026-09-09-jsonl-incremental-live-source-canary` created from the frozen grant tip |
| **Starting base** | merged PR #291 at `55fc69ee6609ba38f051f08b37a6a01959e6f447` |
| **Push status** | grant branch pushed; Execute branch must be pushed after every commit |
| **PR** | not opened; Ryan has not authorized PR creation or merge |
| **Ryan GATE** | Execute is authorized only within this file; stop at evidence for Kiro review |
| **Track A ingest** | disabled for this run; do not invoke `convmem index` |

The grant revision is the commit containing this file. Resolve and record its
exact SHA before creating the Execute branch. Do not silently follow later
branch movement.

---

## What to build

Add a scratch-only canary runner that reads one frozen, explicitly authorized
Kiro JSONL transcript without modifying it, copies a validated complete-record
prefix into a fresh temporary root, and exercises the merged incremental engine
against the existing real Chroma writer/pruner. Run clean, incremental,
mutation/fallback, repair, and abrupt subprocess crash/replay cases using bytes
derived from that real source. Produce content-free evidence and stop for
independent Kiro review.

**Why this exists:** PR #291 proved the real Chroma storage seam with synthetic
Kiro-shaped JSONL. The remaining bounded transfer question is whether real
source bytes, source capture, and cross-collection replay preserve the same
authority and isolation properties. This canary answers only that question. It
does not integrate the prototype into production ingest or the watcher.

---

## Frozen live-source authority

Only this source is authorized:

```text
alias: kiro-pr291-exact-tip-review
messages:
  /home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_9139c273-f6b3-4080-a3f0-d89406f7f0e4/messages.jsonl
messages_sha256: 27ce00afc7b86191bdd8f848546f1d6e10426310277d9d03656eb4f69e3611da
messages_size: 304730
physical_lines: 228
session_meta:
  /home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_9139c273-f6b3-4080-a3f0-d89406f7f0e4/session.json
session_meta_sha256: ad664aab6445f34a2bc509d8f9daa0427c7492285eb09790a2d078e879cf3172
session_meta_size: 1272
```

The runner must fail closed before Chroma construction if the canonical path,
regular-file type, device/inode, size, or either content digest no longer
matches this grant. A changed source requires a new Ryan authorization; Luna
must not substitute the then-latest transcript.

The live source and its sibling metadata are read-only. All append, partial
record, mutation, truncation, replacement, rotation, and race cases operate on
source-derived copies under the fresh scratch root.

---

## Integration points

Expected new surfaces:

- `scratch_jsonl_prototype/live_source_canary.py` — stdlib-first runner,
  frozen-source validation, copy, orchestration, and sanitized evidence.
- `tests/test_scratch_jsonl_live_source_canary.py` — hermetic contract tests
  plus subprocess fault/replay coverage using generated source-shaped fixtures.
- `docs/inter-model/VERIFY-jsonl-incremental-live-source-canary.md` — exact
  commands, results, source digests, transition coverage, and limitations.

Minimal scratch-only edits are allowed in:

- `scratch_jsonl_prototype/isolation.py`
- `scratch_jsonl_prototype/engine.py`
- `scratch_jsonl_prototype/chroma_projection.py`
- `tests/scratch_jsonl_isolation_worker.py`

Prefer composition around the merged engine. Refactor those files only when a
test demonstrates that the canary boundary cannot otherwise be expressed.
Production modules may be imported and exercised, but not edited.

---

## Specification

### Gate 0 — process and path isolation

Before any ConvMem adapter, Chroma, writer, provider, or production-config
import:

1. Confirm `convmem-watch.service` is inactive and no ConvMem watch process is
   running. This is a read-only check. Do not start or stop services. Treat an
   active or indeterminate result as a canary abort.
2. Resolve the two frozen source paths without following a substituted final
   symlink. Reject symlink components, non-regular files, digest/size drift, and
   a changed device/inode across capture.
3. Open sources read-only with close-on-exec and no-follow semantics where the
   platform provides them. Never open either path for write.
4. Create a tokenized fresh temporary root. Establish the existing
   `ScratchBoundary`, sanitized environment, and Python socket denial before
   later imports.
5. Reject production configuration overrides and inherited credential-like
   environment names. Do not read production configuration to discover paths.
6. Resolve every mutable path—Chroma, checkpoint, projection, snapshot, export,
   inventory, lock, attestation, census, and evidence scratch file—beneath that
   root. Reject outside, production, and symlinked aliases before constructors.
7. Assert the writer session receives the explicit scratch config, Chroma root,
   writer lock, attestation directory, and census directory. No production lock
   may be opened.

Gate 0 must pass before any canary write. Failure produces a nonzero exit and a
sanitized reason; it does not fall back to defaults.

### Source capture

1. Read at most the frozen `messages_size` from the already validated descriptor.
2. Select the largest newline-terminated prefix. Compute its SHA-256 and record
   byte and physical-line counts, never message text.
3. Copy that prefix and the frozen `session.json` into
   `<scratch>/sources/sess_canary/` with fsync plus atomic replace.
4. Re-stat the live descriptor and canonical path and re-hash the selected live
   prefix. Identity, shrinkage, or prefix mutation aborts before Chroma
   construction. A pure append beyond the frozen boundary is also an abort in
   this exact-source canary because the grant binds the full file digest.
5. All later mutation and crash cases use only the copied bytes. The evidence
   must explicitly say the live source was read, not mutated.

### Canary matrix

Use the normal `jsonl_kiro_session` detection and parser, deterministic local
four-dimensional embeddings, `ScratchIncrementalJsonl`, and
`ScratchChromaProjection`.

1. **Full real-shape baseline:** ingest the complete captured source; prove both
   Chroma collections, active projection, and checkpoint authority agree.
2. **Unchanged replay:** zero transform calls and exact authority equality.
3. **Frontier append:** derive two valid stages from the captured records; the
   second run transforms only the new frontier and reuses preceding rows.
4. **Boundary/partial record:** withhold an incomplete source-derived final line;
   it must not enter authority until completed.
5. **Fallbacks:** source-derived clone mutation, truncation, replacement/rotation,
   and transform-fingerprint change must take their declared fallback paths.
6. **Storage repair:** independently remove one summary and one unit row; replay
   repairs each with zero transform calls.
7. **Source scope:** a second-source sentinel in both collections survives every
   prune and prune-crash point.
8. **Clean rebuild:** incremental/replayed authority must equal a clean rebuild
   exactly for summaries, units, active projection, and checkpoint authority
   fields. Compare without normalization except the already documented
   diagnostic-only `fallback_reason`.
9. **Memory claim:** record `max_units_in_flight`; do not claim constant-memory
   parsing or watcher RSS.

For bounded runtime, the clean full-source baseline uses all captured bytes.
The exhaustive crash matrix may use the smallest complete prefix that yields
32 parsed user/assistant messages. It must still be byte-derived from the frozen
source and must record that boundary and digest.

### Fault/replay authority coverage

Use real subprocess exits with code 86 and contain descendants. Inject on both
sides of every declared transition:

- engine transitions: `fallback_marker`, `generation_prepare`, every discovered
  upsert authority point, `publish`, `prune`, `checkpoint_prepare`,
  `checkpoint_publish`, `fallback_cleanup`, `snapshot_cleanup`, `lock_acquire`,
  and `lock_release`;
- real Chroma transitions: `summary_upsert`, `unit_upsert`,
  `summaries_prune`, and `units_prune`;
- new capture transitions, if durable state is introduced: snapshot prepare,
  snapshot publish, and source revalidation.

A transition-inventory assertion must fail if any discovered durable authority
transition is absent from the crash matrix. After every crash, replay must
converge to the same authority as a clean rebuild. The evidence must retain the
known limitation: Chroma offers no atomic cross-collection commit; checkpoint-
governed replay is the tested recovery mechanism.

### Evidence contract

Evidence may contain only:

- grant and implementation revision;
- source alias, canonical path, device/inode, sizes, times, boundaries, counts,
  and SHA-256 digests;
- scratch path, sanitized environment-name checks, network-denial result, and
  production-path/lock open-file checks;
- modes, fallback reasons, transform/reuse counters, transition names, exit
  codes, authority digests, equality booleans, and test/static results.

Do not print or commit transcript content, parsed messages, Chroma documents,
embeddings, environment values, or credentials. Temporary Chroma and copied
source bytes remain untracked and are removed after evidence extraction.

---

## What NOT to build or run

- No production ingest, watcher integration, service/timer/config change,
  migration, backfill, or production collection mutation.
- No `convmem index`, `convmem add`, `convmem record`, bulk verify, or live
  retrieval/golden evaluation.
- No edits to production adapters, `chroma_store.py`, `chroma_write_store.py`,
  ingest, watcher, retrieval, or provider code.
- No production credentials/defaults, paid provider, local model provider,
  endpoint, or outbound network.
- No `.crush`, SQLite, Codex/Cursor/Copilot adapter, second live source, or
  copied production Chroma corpus.
- Do not run repository-wide pytest. Run only the focused files named below.
- Do not open a PR, merge, enable anything, or generalize PASS into production
  readiness. Stop after evidence and push for Kiro review.

If any required outcome needs one of these actions, stop and report the concrete
contradiction. Do not broaden the grant.

---

## Test expectations

Required focused tests:

```text
tests/test_scratch_jsonl_isolation.py
tests/test_scratch_jsonl_incremental.py
tests/test_kiro_session_jsonl.py
tests/test_scratch_jsonl_chroma.py
tests/test_scratch_jsonl_live_source_canary.py
```

At minimum, the new tests must prove:

1. Exact source path/digest/size and regular-file checks fail closed before
   Chroma construction.
2. Symlink, production mutable path, credential/default inheritance, network,
   active/unknown watcher, and production-lock cases fail closed.
3. Read-only live capture never opens the authorized source for write and emits
   no content in evidence.
4. Full-source baseline, unchanged replay, source-derived staged append,
   partial record, all fallbacks, repair, pruning, and exact rebuild equality.
5. Real subprocess crash/replay at every engine, Chroma, and new capture
   transition, with descendant containment and coverage completeness assertion.
6. Frontier-bounded call counters and the bounded-units-in-flight claim.

Static gates:

```bash
python -m compileall -q scratch_jsonl_prototype \
  tests/test_scratch_jsonl_isolation.py \
  tests/test_scratch_jsonl_incremental.py \
  tests/test_kiro_session_jsonl.py \
  tests/test_scratch_jsonl_chroma.py \
  tests/test_scratch_jsonl_live_source_canary.py
python -m pylint scratch_jsonl_prototype \
  tests/test_scratch_jsonl_isolation.py \
  tests/test_scratch_jsonl_incremental.py \
  tests/test_kiro_session_jsonl.py \
  tests/test_scratch_jsonl_chroma.py \
  tests/test_scratch_jsonl_live_source_canary.py
git diff --check
```

Do not count the actual canary execution as a test-suite substitute. Record its
separate command, exit status, and sanitized evidence in the VERIFY document.

---

## Acceptance criteria

- [ ] Gate 0 passes before any canary write or non-isolation import.
- [ ] The frozen live source matches this grant and is only read.
- [ ] Every mutable resource is constructed under a fresh temporary root.
- [ ] No network, provider, credential/default, production path, or production
      lock is reachable.
- [ ] The real-source full baseline and all source-derived fault/replay cases
      pass with exact clean-rebuild equality.
- [ ] Transition coverage fails closed if a durable authority point is missing.
- [ ] Unchanged and repair replays use zero transforms; append work is frontier
      bounded.
- [ ] Evidence contains no transcript content, parsed messages, documents,
      embeddings, or environment values.
- [ ] The five-file focused set, compileall, pylint, and diff check pass.
- [ ] Diff contains only scratch package, focused tests, VERIFY/handoff/LATEST,
      and any mechanically required writer-inventory correction.
- [ ] Branch is committed and pushed after every commit.
- [ ] Stop at evidence for independent Kiro review; no PR or activation.

---

## Branch convention

Create a dedicated worktree and branch from the frozen grant commit:

```text
feat/2026-09-09-jsonl-incremental-live-source-canary
```

Do not switch the shared checkout. Push with an explicit refspec after every
commit. Squash is acceptable if Ryan later authorizes and merges a PR.

---

## Related files

| What | Path |
|---|---|
| Merged scratch evidence | `docs/inter-model/VERIFY-jsonl-incremental-scratch-prototype.md` |
| Prior Luna handoff | `docs/inter-model/CODEX-2026-09-09-jsonl-incremental-chroma-scratch-luna-handoff.md` |
| Incremental engine | `scratch_jsonl_prototype/engine.py` |
| Real Chroma projection | `scratch_jsonl_prototype/chroma_projection.py` |
| Isolation boundary | `scratch_jsonl_prototype/isolation.py` |
| Current routing | `docs/inter-model/LATEST.md` |

---

## Leaving / picking up checklist

**Codex author:**

- [ ] Commit and push this frozen grant and `LATEST.md` pointer.
- [ ] Give Luna-High the exact grant revision and Execute branch name.
- [ ] Do not delegate scope decisions or authorize production changes.

**Luna-High implementer:**

- [ ] Read this entire file and the merged scratch VERIFY before first edit.
- [ ] Confirm branch starts at the frozen grant revision.
- [ ] Run Gate 0 before actual-source execution.
- [ ] Commit and push each bounded increment.
- [ ] Stop on any scope contradiction.
- [ ] Stop after evidence for Kiro; do not open a PR.

## TL;DR

This grant authorizes one no-cost, read-only-source, isolated-storage canary
using the frozen Kiro PR #291 review transcript. Luna-High may implement and run
the scratch-only matrix, then must stop at content-free evidence for Kiro review.
