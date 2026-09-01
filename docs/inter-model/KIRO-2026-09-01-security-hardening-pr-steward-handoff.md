# PR Steward Handoff: Security-hardening branch → GitHub PR lifecycle

**Date:** 2026-09-01
**Author:** Kiro (design/review)
**For:** PR Steward (default lane: Codex Luna) — **pending Ryan's explicit Steward grant**
**Authorization:** Ryan, 2026-09-01 (verbal — "give Luna a handoff to PR Steward with your advice")

---

## Role gate (read first — do not skip)

**PR Steward is a Ryan-granted overlay. It is never inferred and never self-assigned.**
This handoff *prepares* the Steward brief and recommends Luna as Steward, but Luna may act as
PR Steward only after Ryan explicitly grants the role for this brief. Until then, Luna holds
implementation lane only.

PR Steward is **brief-bound** and has **no merge / no grant / no ledger** authority. The
Steward may open the PR and shepherd its checks; **Ryan owns the squash-merge.** Do not
merge, do not approve required reviews on your own behalf, do not write ledger records.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_PR` (implementation done + Kiro-reviewed; only PR lifecycle remains) |
| **Branch** | `fix/2026-09-01-security-hardening` |
| **Tip SHA** | `b3f34c4` (Luna correctives) |
| **Push status** | `pushed to origin` |
| **PR** | `not opened` (verified no open PR for this head) |
| **Ryan GATE** | (1) PR Steward role grant; (2) squash-merge. Both Ryan-owned. |
| **Kiro review** | PASS on `b3f34c4` (see review handoff below) |

---

## What remains

Only the GitHub PR lifecycle. Implementation is complete (`b3f34c4`) and independently
Kiro-reviewed PASS. Nothing in the runtime needs further change.

Steward tasks, in order:
1. Confirm Ryan's Steward grant is in hand (role gate above).
2. Open the PR from `fix/2026-09-01-security-hardening` into `main` using the **full-branch**
   title and body below.
3. Shepherd required checks (Pylint, Pytest, CodeQL, Analyze) to green; report status.
4. Hand back to Ryan for squash-merge. **Do not merge.**

---

## Kiro advice (the reason this handoff exists)

### 1. Describe the WHOLE branch, not just the last commit

Luna's earlier proposed PR body described only the two correctives (`b3f34c4`). **That is
wrong for this PR.** The PR squashes **5 commits** from `main`:

```
b3f34c4 fix: restore adaptive scoped query recall        (Luna correctives)
8b3b102 docs: Kiro review sign-off + two correctives...   (Kiro handoff doc)
d8aa057 fix: page large corpus metadata reads             (Codex hardening)
3db219e fix: bound retrieval and harden watcher file...    (Codex hardening)
ac6a56b fix: bound retrieval and harden watcher file...    (Codex hardening)
```

Because Ryan squash-merges, the PR title/body **becomes the single `main` commit message**.
It must describe the entire security-hardening change (prompt boundary, retrieval bounds,
symlink-safe locks, watcher timeout, atomic processed writes, paged metadata reads) **plus**
the two correctives — not just the recall fix. Use the body in the next section.

### 2. Flag the public behavior change

The PR introduces a **public API behavior change**: callers requesting more than 100 query
results now receive an error (`validate_top_k`, 1–100). Call this out explicitly in the body
so it is not a surprise on merge.

### 3. Do not squash-split; squash is correct here

No `Do not squash` line is needed — there are no signed bisect points or commit-by-commit
provenance requirements. Squash is fine (charter default).

### 4. Dependabot note (do not scope-creep)

The push warned of 4 default-branch Dependabot vulnerabilities (2 critical, 2 high). These
are **out of scope** for this PR (the hardening branch deliberately made no dependency
changes). Do not fold dependency upgrades into this PR; leave them for a separate Ryan-owned
decision. Mention their existence to Ryan if useful, but do not act.

### 5. DeepSeek-401 is unrelated

The session-ingest DeepSeek 401 is a Ryan-owned credential matter, independent of this PR.
Not a merge blocker.

---

## PR title

```
Harden retrieval, locks, watcher, and processed-state writes
```

## PR body (paste verbatim)

```markdown
## What this changes for you

Security hardening across the retrieval, locking, watcher, and ingest paths, plus two
Kiro-reviewed correctives. After merge: the public query API rejects oversized result
requests (1–100), PID locks are symlink-safe, a hung index child is force-terminated,
processed-state writes are atomic, and large-corpus metadata reads are paged. Retrieval
recall for sparse domain/site queries is preserved (no silent 300-neighbor cap), and the
watcher timeout default is documented as an unratified interim backstop — not a tuned value.

## Public behavior change

Callers requesting more than 100 query results now receive an error (`validate_top_k`,
1–100). This is intentional DoS/resource protection and is the one caller-visible change.

## Who / What / When / Why / How

- **Who:** Codex authored the hardening; Kiro reviewed and specified two correctives;
  Codex Luna implemented the correctives (`b3f34c4`); Kiro re-reviewed PASS.
- **What:** retrieval bounds + prompt-injection boundary (`ask.py`, `query.py`),
  symlink-safe PID locks (`process_lock.py`, reusing `shadow_authorization` primitives),
  hung-child process-group termination layered over the landed memory cap (`watch.py`),
  atomic processed-state writes (`ingest.py`), paged Chroma metadata reads
  (`chroma_store.py`); correctives de-ratify the 900s watch timeout in comments and remove
  the internal `MAX_QUERY_FETCH` clamp that had reduced sparse-scope recall.
- **When:** branch rebased onto current `main`; hardening tip `d8aa057`, correctives
  `b3f34c4`.
- **Why:** reduce prompt-injection risk, DoS/resource exhaustion, symlink attacks on lock
  files, watcher hangs, and large-corpus read failures — without degrading planned or
  completed security work.
- **How on merge:** no live data, systemd config, writer-gate protocol (`chroma_writer_gate.
  lock` / `fcntl.flock`), R2b/Shadow work, or project docs changed.

## Kiro review verdict

PASS on `b3f34c4`. Independently confirmed: no degradation of planned/completed security
work — the writer-gate protocol and R2b/Shadow surfaces are untouched, `process_lock.py`
reuses convmem's own `shadow_authorization` primitives (used only by `watch.py`/`refine.py`),
and the watch timeout is additive over the landed memory cap (PR #245). Both correctives
match the reviewed spec with no scope creep.

## Test plan

- Focused security suite: 20/20 pass (query harden, retrieve_for_ask, watch subprocess
  memcap) — independently re-run by Kiro.
- Corrective B ships a regression test (`test_scoped_fetch_adapts_to_collection_size`)
  proving scoped over-fetch can exceed 300 while bounded by `count_units()`; public-limit
  rejections (`validate_top_k(101)`→ValueError, `(True)`→TypeError) added.
- Pylint 9.83/10 on changed modules (no regression vs baseline; score up +0.11).

## Merge reading

- Kiro review + corrective spec: `docs/inter-model/KIRO-2026-09-01-security-hardening-review-and-corrective-handoff.md`
- This Steward brief: `docs/inter-model/KIRO-2026-09-01-security-hardening-pr-steward-handoff.md`
- Landed OOM memory cap context: PR #245

Squash OK.
```

---

## Suggested `gh` invocation (Steward runs after Ryan grant)

```bash
cd /home/lauer/.local/share/convmem/worktrees/fix-2026-09-01-security-hardening
gh pr create \
  --base main \
  --head fix/2026-09-01-security-hardening \
  --title "Harden retrieval, locks, watcher, and processed-state writes" \
  --body-file <(...)   # paste the PR body above into a file first
```

Do not pass `--merge` / do not auto-merge. Report the PR URL and check status back to Ryan.

---

## What NOT to do

- Do NOT act as PR Steward without Ryan's explicit grant.
- Do NOT merge, enable auto-merge, or approve required reviews to unblock yourself.
- Do NOT fold Dependabot upgrades or the DeepSeek-401 credential fix into this PR.
- Do NOT re-touch runtime code — implementation is frozen at `b3f34c4` and reviewed.
- Do NOT edit tracked files on `main` or force-push.

---

## Related files

| What | Path / ref |
|------|------------|
| Branch tip (implementation) | `b3f34c4` |
| Kiro review + corrective spec | `docs/inter-model/KIRO-2026-09-01-security-hardening-review-and-corrective-handoff.md` |
| Writer gate (untouched — context) | `chroma_write_store.py` `fcntl.flock` |
| Landed OOM memory cap (context) | PR #245 `_scoped_index_cmd` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on `fix/2026-09-01-security-hardening`
- [ ] Branch pushed with explicit refspec
- [ ] Track A: index this Kiro session transcript

**PR Steward (picking up):**

- [ ] Confirm Ryan's PR Steward grant for this brief (role gate)
- [ ] Read this file + the Kiro review handoff before opening the PR
- [ ] Open PR with the full-branch title/body above (not the corrective-only draft)
- [ ] Shepherd required checks green; report status
- [ ] Hand to Ryan for squash-merge — do NOT merge

<!-- Kiro PR Steward brief for the 2026-09-01 security-hardening branch. Steward role is Ryan-grant only. -->
