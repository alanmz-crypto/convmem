# Execution Plan — Claude Watch Parity Boundary

**Arc:** Claude Watch Parity

**Depends on:** Kiro PASS on `ARCHITECTURE-claude-watch-parity.md`

**Implementation base:** Cursor local-safety tip `e007a22b24754a93d9cbd15d02269d422d371c4a` after exact ref verification

**Live-source canary:** `NOT_RUN`

## E0 — Reconcile the implementation base

Before editing, fetch and verify that
`origin/fix/2026-09-20-claude-gate2-local-safety-corrective` resolves to the
reviewed local-safety tip. Use merged base
`e6a0634c214cf07c89b551d13410bb276a93b38d`. Confirm:

- empty diffs from the merged base through `e007a22` for
  `incremental_jsonl.py`, `incremental_jsonl_isolation.py`, and
  `chroma_write_store.py`;
- the expected `incremental_jsonl_formats.py` Gate 2 registry addition is
  byte-identical to the Kiro-reviewed `a95cef3` blob;
- no production config, watcher, source, service, or activation change.

Do not claim that the whole Gate 2 stack is unchanged from main: the adapter,
format registry, route tests, and canary are expected branch additions.

Create a new clean worktree outside the repository root. Install repository
configuration with `bash scripts/install-repo-config.sh`.

Stop if the base moved or the shared-file diff is not empty.

## E1 — Build a single namespace launcher

Add one private launcher in the Claude Gate 2 canary surface. It owns:

- exact `/usr/bin/bwrap` validation;
- minimum version 0.12.0;
- non-setuid verification;
- unprivileged-user-namespace and descriptor-bind probe;
- the complete fixed argument allowlist;
- descriptor ownership and closure;
- exit-code and stderr normalization into closed evidence.

Do not expose free-form bwrap arguments, optional host binds, caller-supplied
environment, or a generic sandbox helper.

## E2 — Descriptor-bind the fixed filesystem

Create one mode-0700 host control root with sibling `scratch` and
`snapshot-vault` directories through a held control dirfd. Open and retain both
directory descriptors plus the exact source. Host capture runs before the
namespace: publish the snapshot through the held vault descriptor, then open the
published snapshot read-only. Pass only the scratch and snapshot with
`subprocess.run(..., pass_fds=...)` to bubblewrap:

- scratch root fd -> `--bind-fd ... /canary-root`;
- snapshot fd -> `--ro-bind-fd ...
  /canary-root/home/.claude/projects/granted/<alias>.jsonl`;
- final configuration fd -> `--ro-bind-data ...
  /canary-root/home/.config/convmem/config.toml`.

Create new roots only with `mkdirat(..., 0o700)` beneath one trusted parent
dirfd. Reopen only a previously issued opaque root id beneath that parent. Use
dirfd-relative no-follow opens and reject unless control, scratch, and vault are
directories owned by the effective uid, have exact mode `0700`, and share one
`st_dev`. Complete these checks before the lifecycle lock, markers, or capture.

Set `HOME=/canary-root/home`. Pre-create the final config with the validated
bytes before the overlay and assert its host digest remains unchanged. Treat
the zero-length source mountpoint as a declared scratch-only artifact; assert it
is unchanged and never selected as a host source.

For every worker invocation, generate a fresh 128-bit lowercase hexadecimal
capture id and publish as `<capture-id>.jsonl` in the unbound vault. Re-capture
even for unchanged replay. Append tests capture the new complete fixture rather
than modifying an old snapshot. Mount each new snapshot fd at the same internal
alias path so the coordinator `path_key` remains stable. Do not bind the vault,
control root, or their descriptors into the namespace.

After the worker fd closes, reopen the snapshot through the vault dirfd and
require its original device, inode, size, full bytes, and digest. Only then
remove it through the same dirfd, including worker-crash paths. If the launcher
crashes, treat the
remaining allowlisted regular snapshot as stale: never reuse it, inventory it
on the next invocation, and remove it only after descriptor-relative identity
checks. Unexpected entries or cleanup uncertainty quarantine the control root;
start replay from a new clean root instead of accepting prior evidence.

Acquire a nonblocking exclusive `flock` on the held control dirfd before reading
or changing markers, and retain it for the full invocation. Lock contention
refuses without quarantining the active owner. Under the lock, create and fsync
an unbound `.active` control marker before capture. Creation or fsync failure
refuses before transcript access. Remove and fsync it only after snapshot digest
verification, cleanup, and passing post-run checks. A pre-existing `.active`
marker after lock acquisition or any post-run quarantine condition is atomically
renamed through the held dirfd to `.quarantined`, then the directory is fsynced.
The required terminal set is `.quarantined` present and `.active` absent. Tests
must reject both-present and neither-present outcomes. A marked control root is
refused on all later starts. Its deletion is not part of a canary run.

Mount the runtime and application code read-only. Start with an empty root,
clear environment, isolated network/PID/IPC/UTS/cgroup/user namespaces, new
session, parent-death handling, and nested-user-namespace disablement.

No host home, production ConvMem path, D-Bus socket, provider socket, or
credential path may appear in the command.

## E3 — Run the unchanged coordinator inside the namespace

Inside the worker:

- require `/canary-root` and the Claude-compatible source path exactly;
- build `IsolationBoundary` normally from those fixed paths;
- validate the read-only config and all mutable targets;
- require normal `detect_format()` dispatch to `jsonl_claude_session`;
- prove network denial and production-path absence;
- run the existing coordinator and fake providers;
- emit only the closed evidence schema from the local-safety corrective.

Do not patch config loaders or shared modules. Do not persist host paths,
descriptor numbers, or `/proc/self/fd` paths.

## E4 — Adversarial verification

Add hermetic tests for:

1. missing/old/setuid/wrong bubblewrap;
2. disabled user namespaces and failed real probe;
3. root rename and replacement after the fd is opened;
4. source pathname replacement after the fd is opened;
5. absent production home/data/lock/socket paths;
6. network denial;
7. immutable configuration at the expected path;
8. normal Claude detection plus first-run explicit session-id and
   sanitized-unit-content assertions; missing-id detection refusal and a
   separate metadata-helper alias-fallback assertion;
9. stable paths across first run, unchanged replay, append, repair, and an
   injected `CRASH_EXIT` worker/coordinator crash while the host launcher
   remains alive;
10. namespace setup failure before coordinator mutation;
11. descriptor closure after success, ordinary exception, timeout, and
    `BaseException` fault injection;
12. no forbidden host paths, fd numbers, content, environment, or credentials
    in evidence and persisted state.

Host-side tests must also prove that snapshot capture and O_TMPFILE/linkat
publication finish before bubblewrap starts, root identity checks remain
descriptor-anchored, the config overlay leaves no zero-byte replacement, and
the real watcher probe passes both immediately before capture and immediately
after worker exit.

Add lifecycle tests proving unique host snapshot names across first run,
unchanged replay, append, repair, and crash; fresh capture on every run; fixed
internal source path and `path_key`; ordinary and worker-crash cleanup; stale
snapshot non-reuse after launcher crash; and control-root quarantine on unknown
entries or cleanup uncertainty.

Define crash evidence precisely: same-root checkpoint recovery covers injected
`CRASH_EXIT` worker/coordinator crashes for which the host launcher survives and
completes snapshot verification and cleanup. Any signal, unexpected exit code,
or other termination fails evidence and triggers exactly one diagnostic rerun
in a fresh process and clean root. Record both outcomes; neither is recovery
evidence. A launcher crash leaves `.active`, durably quarantines the control
root on the next lock holder, and never claims same-root recovery.

Add namespace tamper tests that try to write, truncate, and unlink the mounted
source and every discoverable alias. Assert the vault, control root, and former
scratch-capture path are absent; no snapshot, vault, or control descriptor is
inherited by the worker; the host snapshot's device, inode, size, bytes, and
digest remain unchanged; and the post-run digest recheck gates cleanup.

Add lock/marker tests for two concurrent launchers, kernel lock release after a
launcher crash, stale `.active` handling, and create/fsync failure before
capture. Read `/proc/self/mountinfo` in the worker to obtain the literal control
prefix and capture id, then assert those exact strings are absent from stdout,
stderr, evidence, checkpoints, exports, processed state, and every other
persisted artifact.

Add create/reopen tests for symlink leaves and parents, wrong uid, group/other
mode bits, non-directory entries, unknown opaque root ids, and mismatched
filesystems. Add termination tests distinguishing `CRASH_EXIT`, signals,
unexpected exit codes, and the single clean diagnostic rerun. Assert every
post-run failure ends with exactly `.quarantined` and no `.active`.

Launch the worker with launcher-created `subprocess.PIPE` stdout and stderr,
`close_fds=True`, and only the fixed bubblewrap setup descriptors in
`pass_fds`. Never redirect either stream to a host file. Assert fd 1 and fd 2
are pipes inside the worker and apply the literal mountinfo-string exclusion to
both captured streams.

Gate 0 must prove the canonical control, scratch, and vault roots are disjoint
in both directions from every configured watch root. Recheck after worker exit.
A failed post-run watcher or watch-root result marks the evidence failed and
durably quarantines the control root from replay.

Use synthetic fixtures only.

## E5 — Regression matrix

Run:

- Gate 1 Claude adapter and containment tests;
- Claude prefix, route, canary, and worker tests;
- Kiro prefix and route tests;
- Codex history/rollout prefix, route, isolation, replay, and physical keep-set
  tests;
- R2b static coverage tests if the changed canary remains governed;
- `compileall`, pylint on touched Python, and full branch `git diff --check`.

Split the namespace tests into always-runnable command/policy unit tests and
real bubblewrap integration tests. On a runner without the prerequisite, the
integration suite may skip only with the explicit reason
`namespace prerequisite unavailable`. Report the count. A skip is never PASS
evidence for finding #2; the intended execution host must run the complete
namespace suite with zero skips before exact-tip review. Evidence must bind that
host as closed enum `primary_convmem_host` plus
`HMAC-SHA256(key=machine-id, message="convmem-gate2")`; VERIFY names the host
role, kernel, and bubblewrap version without serializing the raw hostname or
machine-id.

Static assertions must show empty diffs for:

- `incremental_jsonl.py`;
- `incremental_jsonl_isolation.py`;
- `chroma_write_store.py`;
- watcher/source/service configuration;
- `KIRO_ROUTE_FORMATS` and production activation.

Separately report the expected adapter and `incremental_jsonl_formats.py`
branch additions against merged base `e6a0634`; do not hide them behind the
protected-runtime assertion.

## E6 — Evidence and review

Update `VERIFY-claude-watch-parity-gate2.md` with:

- exact implementation and review SHAs;
- bubblewrap binary, version, ownership/mode, and probe result;
- fixed namespace mount manifest without host-sensitive values;
- focused and regression test results;
- the live canary marked `NOT_RUN`;
- known Linux/bubblewrap dependency and `NO_GATE2_ROUTE` fallback.

Push every commit with an explicit branch refspec. Stop for OpenAI Security
Review under a fresh Ryan exception while Copilot is unavailable. After a
Security Review PASS, Kiro reviews the same exact SHA. A same-revision material
PASS/FAIL conflict routes to Sol-High.

## E7 — Stop conditions

Stop and recommend `NO_GATE2_ROUTE` rather than widening scope when:

- the namespace requires a host bind outside the declared allowlist;
- a test requires modifying shared coordinator/isolation/Chroma code;
- a stable internal path cannot be preserved through replay;
- the minimum bubblewrap/user-namespace requirement cannot be guaranteed;
- an escape cannot be closed inside the Claude canary and worker files.

No Execute, PR, live source, live canary, routing, watcher, issue #314, or
activation authority is granted by this plan.
