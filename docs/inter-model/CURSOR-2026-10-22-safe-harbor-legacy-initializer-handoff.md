# Implementation Handoff: Safe Harbor legacy-source initializer

**Arc: Safe Harbor**
**Date:** 2026-10-22
**Author:** Claude Opus 5.5 (resume check and handoff preparation only; not the supervisor or a reviewer of this task)
**For:** Cursor (authoring) under Codex supervision. Ryan starts the task by pasting the [starting prompt](#starting-prompt-for-codex) into Codex; Codex sets up Cursor's locked-down authoring copy and runs all execution.
**Authorization:** Ryan, 2026-10-22, in a Claude Code session. He resumed the arc ("Yes, Safe Harbor. Can we pick that work up.") and answered **"yes"** to "Do you approve Cursor building the initializer, as Kiro approved the spec at `c46fbc6`?". Recorded in [EXECUTION §23](../plans/EXECUTION-safe-harbor.md#23-legacy-initializer-implementation-and-isolated-evidence--owner-authorized). He did not name a supervisor, so STATUS's named supervisor (Codex) applies.

> **PARKED (2026-10-22).** The starting prompt below reached Cursor, not Codex. Cursor delivered `dd0c467` without the isolation model and with four §22 cases missing; Ryan parked it unreviewed. This handoff is consumed; do not rerun its prompt. A resumption needs a new grant ([findings](../plans/VERIFY-safe-harbor.md#claude-verification-and-owner-parking-2026-10-22)).

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `PARKED` at `dd0c467` (originally `NOT_STARTED`) |
| **Branch** | `feat/2026-10-22-safe-harbor-legacy-initializer`, created from the commit that adds this file |
| **Base** | That commit = `feat/2026-10-15-safe-harbor-rollout-evidence` after merge `7cea298` of main `5c0a01b`, plus this grant record. `chroma_write_guard.py` and `scripts/chroma_guard.py` are byte-identical to main `5c0a01b`. Pin with `git rev-parse origin/feat/2026-10-22-safe-harbor-legacy-initializer` before authoring. |
| **Worktree** | Codex creates `.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer` (disk-backed). Never switch branches or stash in `~/Projects/convmem`. |
| **Push status** | Branch pushed to origin; no implementation commits yet |
| **PR** | Not opened, and not authorized |
| **Ryan GATE** | None for isolated implementation and evidence. A PR, hosted CI, merge, deployment and any live or production action each need a separate grant. |
| **Track A ingest** | Not part of this task (arc hard stop: no session indexing during execution) |

---

## What to build

One explicit maintenance command, `scripts/chroma_guard.py initialize-legacy`, that creates fresh evidence-bearing snapshot saves for Chroma segments whose CURRENT generation is a pre-Safe-Harbor legacy save. It is a read-only preview by default. Apply requires an explicit canonical Chroma root, a fresh archive directory, `--apply` and the preview's `--expect-state` digest. Originals are archived durably before anything changes; every new generation is prepared and verified before any CURRENT is published; nothing is pruned; partial completion is reported as such.

**Why this exists:** the 2026-10-14 preflight found two legacy snapshot generations in the live guard without release evidence. Ordinary reconcile skips unchanged signatures, so they never gain evidence, and Safe Harbor's strict release refuses them as a repair source. The §20 readiness work showed the public CLI has no supported way to fix this. §22 is the reviewed design for that way. This task builds and proves it in isolation only; running it against the live store is a later, separate grant.

---

## Specification: EXECUTION §22 is the contract

Implement exactly [EXECUTION §22](../plans/EXECUTION-safe-harbor.md#22-bounded-legacy-source-initialization--proposed-scope-not-a-grant) as Kiro passed it at `8e0cfda` and the B1–B3 delta at `c46fbc6` ([review record](../plans/VERIFY-safe-harbor.md#legacy-initializer-scope--governing-review)). Read all of §22 before authoring. This file summarizes it and changes nothing; where they differ, §22 wins.

Load-bearing points:

- **Command contract.** Preview: `initialize-legacy --chroma-dir <abs canonical root> --archive-dir <abs fresh destination>`; both are required even in preview and are rejected before the config fallback. Apply adds `--apply --expect-state <digest>`; either without the other is a usage error. One JSON result with `status` in `preview_ready | refused | complete | partial_or_uncertain | unavailable`. Exit 0 = ready preview or complete apply; 1 = known refusal; 2 = usage, unavailable, or partial/uncertain. Only a complete legacy set is accepted.
- **Preview is inert.** No Chroma client, native lock, event, archive or staging directory. Its call graph never reaches preparation or publication helpers, including on refusal. Read-only SQLite; report concurrent change instead of claiming atomicity. The digest binds target, archive and every input §22 lists.
- **Apply admission.** Take the existing native lock; recheck quarantine, target and digest; hold a read-only SQLite transaction across validation and capture. Re-read backend identity under the lock, apply `_assert_supported_backend_identity`, and require exact equality with the preview. Every segment passes the existing strict empty-changed-set predicate before the first publication; a mixed set refuses as a whole.
- **Durable originals first.** Fresh, non-overlapping, symlink-free archive; copy and verify; fsync files and directory entries; publish a write-once completion manifest. Re-read live and original source facts against the preview-bound facts with `_source_facts_equal` / `_require_live_source_facts_match` (extended only to manifest/pointer inputs) and repeat at the pre-publication boundary. Checking the archive copy alone is not enough.
- **Prepare all, then publish.** `_refresh_snapshot` combines capture, publication and pruning, so calling it and checking afterwards cannot satisfy the contract. Factor a preparation/publication boundary inside the two allowed files. The initializer never prunes. Ordinary capture behavior stays the same and stays covered.
- **No atomicity claim across segments.** A failure after one publication reports `partial_or_uncertain` with observed old/new references and the archive identity. No rollback, retry or cleanup.
- **Fail closed.** Quarantine, pending work (`watermark_drift`, `queue_pending`), unavailable evidence, backend mismatch or unexpected state stop the operation. Never clear an incident or change the release predicate. Use existing event/output surfaces, not a new ledger.

---

## Integration point

Only these two runtime files may change (line numbers at base; re-check):

- `chroma_write_guard.py` (2,944 lines): `ChromaWriteGuard` (:1547); `_refresh_snapshot` (:2633, the function to factor); `_require_live_source_facts_match` (:2036); `_source_facts_equal` (:745); `_assert_supported_backend_identity` (:634); `_exclusive_flock` (:1062, the native lock); `build_release_evidence_for_collection` (:566) and `evaluate_release_evidence` (:885, the strict empty-changed-set oracle).
- `scripts/chroma_guard.py` (206 lines): `main()` (:123) dispatches a fixed `choices=` list (`status`, `validate`, `census`, `audit`, `reconcile`, `clear-quarantine`). Add `initialize-legacy` and its flags without changing the other subcommands.

---

## Resume drift check (static, 2026-10-22)

Between hold base `c6f0724` and main `5c0a01b` (20 merged PRs, #395–#414):

- **Initializer surface unchanged.** Both runtime files are byte-identical and the named helpers are unchanged, so Kiro's scope PASS applies to unchanged source.
- **New index-write lock (PR #395) — supervisor confirms before authoring.** `purge_locks.index_write_flock` is new, with an `assert_lock_ordering_ok` rule: the index-write lock may not be taken while holding an export lock or a production Chroma writer session, and the source lock may not be taken while holding the index-write or export lock. `chroma_write_guard.py` uses none of these locks, and production Chroma writer sessions already pass through `ChromaWriteGuard`'s native lock. Claude's reading: §22's locking is unaffected and the initializer should not take `index_write_flock`. If the supervisor finds it needs that lock, that is a contract change: stop and return (§22: "A needed surface/contract expansion returns before implementation").
- **Readiness evidence base moved.** #395 changed three T4 test helpers (`tests/_safe_harbor_t4_common.py`, `_safe_harbor_t4_concurrency.py`, `_safe_harbor_t4_terminal.py`) used by the readiness selection. Kiro's readiness PASS stays pinned to `f45b051`; step 0 below re-establishes the baseline on the merged base.
- **Repository-knowledge manifest guard (PR #403).** CI now fails if any tracked file is unclassified in `config/repository-knowledge/openclaw-watch-scope-v1.json` or an `include` file's sha256 is stale. The grant commit already classifies this branch's new files and refreshes `docs/RECOVER.md`'s hash. **Every new tracked file this task adds** (tests, helpers) must be classified like its siblings (`unrelated`, "outside the W0 maintenance inventory"). Any further edit to `docs/RECOVER.md` (an `include`) needs its sha256 refreshed. Both runtime files are `unrelated` with no hash.
- #396 and #411 changed recovery-adjacent code in `incremental_jsonl.py` and `ingest.py`, outside §22's surface.

---

## Division of work and isolation (same model as §15 and §18)

- **Authoring.** Cursor authors in a disposable source copy with a temporary HOME, no home MCP definitions, and project rules denying Shell, MCP and WebFetch. Allow file edits to the two runtime files and to tests only. Codex runs a harmless command-denial canary before authoring and checks the trace afterwards. Cursor runs nothing.
- **Supervision.** Codex inspects the delta statically, copies only permitted files into the task worktree, may make narrow corrections (and records each), and runs all execution. Neither Cursor nor Codex is an independent reviewer.
- **Execution.** Only through the reviewed stdlib `-I -S -B` entry and bootstrap (`tests/_safe_harbor_rollout_evidence.py`, `tests/_safe_harbor_bootstrap.py`): fresh allowlisted HOME/XDG/CONVMEM/TMPDIR before imports, uid/euid binding, pre-import Python network refusal, inert providers, real disposable Chroma fixture stores. Interpreter: `/home/lauer/miniforge3/envs/convmem/bin/python` (3.11), as in the readiness evidence.
- **Pinned restic.** The launcher needs `/tmp/safe-harbor-restic-tool/restic`, which is gone (`/tmp` was cleared). A verified copy is at `/home/lauer/.cache/issue286-restic-bin/restic`, SHA-256 `ae7fe58ab3511f830fd31d157158620b209522ff1332b119199d2e938d72338c` (restic 0.19.0, the pinned value). Copy it into place; the launcher's verifier rechecks it. Do **not** use `~/.local/bin/restic`, which is a different binary.
- **Forbidden throughout.** No production CLI, MCP, doctor/brief/unresolved/search, services or watcher, live Chroma, drives, backups, keys or real Restic repositories, ledger writes or session indexing. This task-specific restriction overrides the general session-start ritual and Track A.
- **Host note.** Doctor acceptance is currently unmet (the Timeshift crash; see the [Arc Codex brief](../plans/STATUS-codex-jsonl-production-integration.md)), and this machine's CPU has faulted test workers before. Ryan's grant does not depend on doctor. If a test worker dies on a signal, check `coredumpctl list --since <run start>` before calling it a regression. Never retry for green.

---

## What NOT to build

- No change outside the two runtime files, tests/helpers, the manifest classifications they require, and the existing Safe Harbor docs (EXECUTION/VERIFY/ROLLOUT/STATUS, CLI operator guidance, LATEST and the cross-arc STATUS row).
- No dependency, workflow or lint-baseline change; no backup resolver/profile, governed recovery, watch/service, general HOLD or other-arc authority change.
- No startup hook, timer, environment bypass, config-selected production target or automatic first-write initialization.
- No queue flush, embedding/indexing, repair, automatic release, SQLite write or pruning. Nothing for mixed, partial or already-initialized sets beyond reporting them.
- No live or production run of the new command, and no operator procedure claimed as qualified.

---

## Test expectations

0. **Baseline before any edit.** On the pinned base, run the readiness launcher in both modes (`... -I -S -B tests/_safe_harbor_rollout_evidence.py interpreter`, then `legacy`). Record cases, skips, exits and source hashes. Any failure, skip or drift: stop and return before authoring.
1. **§22's minimum isolated acceptance evidence, every bullet**, through actual CLI invocations with effects inspected outside the result object: preview no-effect (success and refusal), including a faulty preview that calls preparation and must fail the assertion; two populated legacy segments end to end; mixed synced/pending refusal before any CURRENT changes; the refusal set (unknown authority, changed digest, wrong target, alias retarget, unexpected segment/schema, existing destination); source-fact change after preview or during archival, and backend-identity change between preview and apply; archive short-write, hash-mismatch and fsync faults, including a faulty omit-archive control that must fail; second-segment preparation failure, including a publish-during-preparation control that must fail; no pruning on success; interruption at the three named points with honest restart inspection; and the unchanged meaning of the stale-vector and census-only negative controls.
2. **Affected regressions** for ordinary snapshot, incident, repair and release behavior (at least the existing guard/T3/T4 cases that cover `_refresh_snapshot` callers), then the readiness launcher again in both modes on the final candidate.
3. **Repository gates on a clean commit:** the whole-repo lint regression gate against the unchanged baseline (as CI runs it, not per-file scores), and `tests/test_repository_knowledge_committed_manifest.py` (it skips on a dirty tree, so run it after committing).

Fault, fsync and restart evidence establishes implementation boundaries, not hardware power-loss survival.

---

## Acceptance criteria

- [ ] `initialize-legacy` implements §22 as reviewed, within the two runtime files
- [ ] Every §22 evidence bullet passes, and every named faulty control fails its assertion
- [ ] Baseline and final readiness runs pass in both modes, with no skips or source drift
- [ ] Affected regressions pass; ordinary capture behavior is unchanged
- [ ] Whole-repo lint regression gate passes against the unchanged baseline; manifest guard passes on a clean commit
- [ ] VERIFY records the exact source hashes, commands, results, corrections and limitations; STATUS/LATEST route to independent review
- [ ] Nothing ran against production, and no PR, merge or deployment happened

---

## Stops (return to Codex/Ryan before continuing)

- The index-write-lock question or any other finding needs a contract, surface or authority change.
- The baseline fails, a required case fails or skips, a faulty control passes, or the source drifts unexpectedly.
- Any unexpected resource access or isolation lapse: stop that run and exclude it from evidence.
- Results return for **independent Kiro review**; no self-acceptance. Prior outage exceptions do not carry over.

---

## Branch convention

```
feat/2026-10-22-safe-harbor-legacy-initializer
```

Push every commit immediately with an explicit refspec: `git push -u origin "${branch}:refs/heads/${branch}"` (braces matter in zsh). Never push `main`, force-push, merge or open a PR under this grant.

---

## Starting prompt for Codex

```text
[Arc Safe Harbor] You supervise Ryan's 2026-10-22 grant: Cursor implements the
legacy-source initializer (EXECUTION §22, Kiro PASS at c46fbc6) with isolated
evidence. Read, in order, on origin branch
feat/2026-10-22-safe-harbor-legacy-initializer: docs/plans/STATUS-safe-harbor.md,
docs/inter-model/CURSOR-2026-10-22-safe-harbor-legacy-initializer-handoff.md,
then EXECUTION §22-§23. Create worktree
.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer for that branch and pin
its base SHA; never switch branches or stash in ~/Projects/convmem.
First: confirm or refute the handoff's index-write-lock drift note, copy the
verified restic from ~/.cache/issue286-restic-bin/restic to
/tmp/safe-harbor-restic-tool/restic, and rerun the readiness launcher
(interpreter, then legacy) on the base. Stop and report if anything fails.
Then run Cursor's authoring in a disposable copy with Shell/MCP/WebFetch denied
(show the denial canary), inspect and copy only the two runtime files and tests,
classify any new tracked file in the repository-knowledge manifest, and run the
handoff's test expectations through the reviewed -I -S -B bootstrap, plus the
whole-repo lint regression gate and the manifest guard on a clean commit.
No production commands, doctor, services, live Chroma, drives, backups, ledger
or session indexing. No PR, merge or deploy. Push every commit with an explicit
refspec. Return: tip SHA, evidence (cases/skips/exits/source hashes), your
corrections, limitations, and `git log origin/main..HEAD --oneline`, for
independent Kiro review.
```

---

## Related files

| What | Path |
|------|------|
| Contract | `docs/plans/EXECUTION-safe-harbor.md` §22 (scope), §23 (this grant) |
| Scope review record | `docs/plans/VERIFY-safe-harbor.md` → "Legacy initializer scope — governing review" |
| Readiness evidence and launcher | `docs/plans/VERIFY-safe-harbor.md` → "Isolated rollout readiness"; `tests/_safe_harbor_rollout_evidence.py`; `tests/test_safe_harbor_rollout_legacy.py` |
| Arc brief | `docs/plans/STATUS-safe-harbor.md` |
| Operational draft (live use is out of scope) | `docs/plans/ROLLOUT-safe-harbor.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` routing bullet with link and resume state
- [x] `STATUS-safe-harbor.md` Update Log line
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file and EXECUTION §22 before the first edit
- [ ] Work in `.worktrees/feat-2026-10-22-safe-harbor-legacy-initializer`
- [ ] State Goal / role / system state / next action and `**Arc: Safe Harbor**`

<!-- ref: ../plans/EXECUTION-safe-harbor.md — §22 contract, §23 grant record -->
<!-- ref: ../plans/STATUS-safe-harbor.md — arc brief routing to this handoff -->
<!-- src: ../plans/VERIFY-safe-harbor.md — readiness launcher commands and pinned restic identity -->
