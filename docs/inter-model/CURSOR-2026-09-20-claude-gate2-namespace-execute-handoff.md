# [Arc Claude Watch Parity] Gate 2 Namespace Execute Handoff

**Date:** 2026-09-20  
**Author:** Codex architecture  
**For:** Cursor Composer  
**Authorization:** Ryan, 2026-09-20, explicit bounded Execute grant in session

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` |
| **Branch** | create `fix/2026-09-20-claude-gate2-namespace-execute` from exact base `e007a22b24754a93d9cbd15d02269d422d371c4a` |
| **Tip SHA** | base `e007a22b24754a93d9cbd15d02269d422d371c4a`; no implementation tip yet |
| **Push status** | branch not created; push each commit with an explicit refspec |
| **PR** | not authorized; do not open |
| **Ryan GATE** | bounded implementation granted; live source, canary, PR, routing, watcher, and activation remain closed |
| **Review target** | stop at one exact pushed tip for OpenAI Security Review; Kiro follows only after Security Review PASS |

---

## What to build

Implement the descriptor-bound bubblewrap namespace in the Claude Gate 2
canary. Host capture publishes each source snapshot into an unbound sibling
vault; the worker sees a fixed read-only Claude path and a writable isolated
scratch root. The existing incremental coordinator and Chroma writer remain
unchanged.

**Why this exists:** Gate 2 finding #2 showed that preflight pathname checks did
not bind the coordinator's later configuration and filesystem reads. Kiro
PASSed the namespace architecture at `290294d` and carried that PASS to exact
normative plan `2f09469a76f0654230c56fef18d720ccc771a15e` with C1–C4 incorporated.

## Authority and starting point

1. Fetch origin and require
   `origin/fix/2026-09-20-claude-gate2-local-safety-corrective` to resolve to
   `e007a22b24754a93d9cbd15d02269d422d371c4a`.
2. Create a clean worktree outside the repository root at exact `e007a22`.
3. Run `bash scripts/install-repo-config.sh` inside it.
4. Create `fix/2026-09-20-claude-gate2-namespace-execute`.
5. Treat plan `2f09469a76f0654230c56fef18d720ccc771a15e` as normative. Do not redesign it.

Stop if the base moved or protected runtime files differ from merged base
`e6a0634c214cf07c89b551d13410bb276a93b38d`.

## Allowed implementation surfaces

- `claude_incremental_canary.py`
- `tests/claude_incremental_canary_worker.py`
- `tests/test_claude_incremental_canary.py`
- `docs/inter-model/VERIFY-claude-watch-parity-gate2.md`
- one Cursor completion handoff and its `docs/inter-model/LATEST.md` pointer

Do not edit:

- `incremental_jsonl.py`
- `incremental_jsonl_isolation.py`
- `chroma_write_store.py`
- watcher, source, service, or production configuration
- routing or activation surfaces
- issues #313, #314, or #315

## Required mechanism

Implement the reviewed architecture exactly:

1. Validate `/usr/bin/bwrap` 0.12.0+, non-setuid, and run a real disposable
   descriptor-bind/user-namespace fitness probe.
2. Create or reopen a trusted-parent, opaque-id control root with sibling
   `scratch` and `snapshot-vault` directories.
3. Acquire the exclusive lifecycle lock and establish durable marker state
   before transcript access.
4. Run real host Gate 0, including watcher, credentials, and two-way watch-root
   disjointness for control/scratch/vault.
5. Capture each synthetic source into a fresh immutable vault snapshot, then
   bind only the scratch root and read-only snapshot into bubblewrap.
6. Mount the source at
   `/canary-root/home/.claude/projects/granted/<alias>.jsonl`, set
   `HOME=/canary-root/home`, and use normal Claude detection.
7. Run the unchanged coordinator with fake providers and closed evidence.
8. Revalidate host snapshot identity and digest before descriptor-relative
   cleanup. Quarantine on any uncertainty.
9. Run post-worker watcher/watch-root checks before declaring evidence valid.

## Mandatory C1–C4 acceptance conditions

### C1 — Control-root create/reopen

- trusted parent dirfd and opaque issued root id only;
- `mkdirat(..., 0o700)` for creation;
- directory/no-follow/cloexec opens;
- current effective uid, exact permission mode `0700`, and common `st_dev`
  across control, scratch, and vault;
- reassert every property on reopen before lock, markers, or capture.

### C2 — Recoverable crash evidence

- only injected `CRASH_EXIT` counts as recoverable worker/coordinator crash;
- signals, unexpected exit codes, or other termination fail evidence;
- run exactly one diagnostic rerun in a fresh clean process and root;
- record both outcomes and count neither as recovery evidence.

### C3 — Terminal marker invariant

- post-run failure atomically renames `.active` to `.quarantined` through the
  held dirfd and fsyncs the directory;
- terminal set is exactly `.quarantined` present and `.active` absent;
- tests reject both-present and neither-present states.

### C4 — Worker output pipes

- stdout and stderr are launcher-created `subprocess.PIPE` streams;
- never redirect either stream to a host file;
- use `close_fds=True` and the fixed setup `pass_fds` set;
- worker proves fd 1 and fd 2 are pipes;
- captured streams must not contain the literal control-root prefix or capture
  id obtained from the worker's `/proc/self/mountinfo`.

## Adversarial acceptance

Tests must cover the full E4/E5 matrix in the normative plan, including:

- vault/control/capture paths absent from the namespace;
- no snapshot, vault, or control descriptor reachable through worker or PID 1;
- write, truncate, and unlink refusal through every reachable source alias;
- unchanged host device, inode, size, bytes, and digest after tamper attempts;
- unique per-run capture ids with a fixed worker source path and `path_key`;
- ordinary/worker-crash cleanup, launcher-crash quarantine, and stale snapshot
  non-reuse;
- concurrent launcher refusal without false quarantine;
- create/reopen rejection for symlinks, ownership, mode, type, opaque-id, and
  filesystem violations;
- literal mountinfo control prefix and capture id absent from every output and
  persisted artifact;
- Claude explicit-session-id routing, missing-id refusal, and alias fallback;
- first run, unchanged replay, append, repair, prepared replay, and isolated
  Kiro/Codex regressions;
- intended-host namespace suite runs with zero skips. Any skip leaves finding
  #2 unproved.

If the mechanism requires a shared runtime edit or undeclared host bind, stop
with `NO_GATE2_ROUTE`; do not widen scope.

## Verification and handoff

- Run the focused and regression suites named in plan E5.
- Run compileall, pylint on touched Python, and full branch `git diff --check`.
- Prove protected runtime files have empty diffs from merged base `e6a0634`.
- Update VERIFY with exact implementation/review SHAs, host role, kernel,
  bubblewrap version, mount manifest, test counts, and `Live canary: NOT_RUN`.
- Commit and push every change using an explicit branch refspec.
- Stop for OpenAI Security Review on the full exact pushed SHA.

No real Claude transcript, provider, production corpus, live canary, PR,
watcher action, routing change, issue action, or activation is authorized.

## Leaving / picking up checklist

**Author:**

- [x] Exact reviewed plan and implementation base named
- [x] C1–C4 copied into the implementation handoff
- [x] STATUS and LATEST routed to Cursor Execute
- [ ] Cursor branch created and pushed

**Implementer:**

- [ ] Verify exact refs before editing
- [ ] Use a clean external worktree and install repository config
- [ ] State Goal / role / system / next action and Arc codename
- [ ] Push with an explicit refspec after every commit
- [ ] Stop at the exact pushed tip for OpenAI Security Review

**TL;DR [Arc Claude Watch Parity]:** Implement the Kiro-PASSed namespace from
`e007a22` under C1–C4, touch only the allowed canary/test/evidence surfaces, and
stop at a pushed exact SHA for Security Review. No live or production authority.
