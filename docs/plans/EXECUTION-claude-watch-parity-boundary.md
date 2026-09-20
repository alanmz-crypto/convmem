# Execution Plan — Claude Watch Parity Boundary

**Arc:** Claude Watch Parity

**Depends on:** Kiro PASS on `ARCHITECTURE-claude-watch-parity.md`

**Implementation base:** Cursor local-safety tip `e007a22b24754a93d9cbd15d02269d422d371c4a` after exact ref verification

**Live-source canary:** `NOT_RUN`

## E0 — Reconcile the implementation base

Before editing, fetch and verify that
`origin/fix/2026-09-20-claude-gate2-local-safety-corrective` resolves to the
reviewed local-safety tip. Confirm its diff leaves `incremental_jsonl.py`,
`incremental_jsonl_isolation.py`, `chroma_write_store.py`, production config,
watcher surfaces, and routing untouched.

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

Open and retain the scratch root and exact source. Pass them with
`subprocess.run(..., pass_fds=...)` to bubblewrap:

- scratch root fd -> `--bind-fd ... /canary-root`;
- source fd -> `--ro-bind-fd ... /source/session.jsonl`;
- final configuration fd -> `--ro-bind-data ...
  /canary-root/home/.config/convmem/config.toml`.

Mount the runtime and application code read-only. Start with an empty root,
clear environment, isolated network/PID/IPC/UTS/cgroup/user namespaces, new
session, parent-death handling, and nested-user-namespace disablement.

No host home, production ConvMem path, D-Bus socket, provider socket, or
credential path may appear in the command.

## E3 — Run the unchanged coordinator inside the namespace

Inside the worker:

- require `/canary-root` and `/source/session.jsonl` exactly;
- build `IsolationBoundary` normally from those fixed paths;
- validate the read-only config and all mutable targets;
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
8. stable paths across first run, unchanged replay, append, repair, and crash;
9. namespace setup failure before coordinator mutation;
10. descriptor closure after success, ordinary exception, timeout, and
    `BaseException` fault injection;
11. no forbidden host paths, fd numbers, content, environment, or credentials
    in evidence and persisted state.

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

Static assertions must show empty diffs for:

- `incremental_jsonl.py`;
- `incremental_jsonl_isolation.py`;
- `chroma_write_store.py`;
- watcher/source/service configuration;
- `KIRO_ROUTE_FORMATS` and production activation.

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
