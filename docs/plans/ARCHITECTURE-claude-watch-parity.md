# Architecture — Claude Watch Parity

**Arc:** Claude Watch Parity

**State:** `READY_FOR_KIRO_REVIEW` (conditional-FAIL corrections applied)

**Decision scope:** Gate 2 isolation-boundary blocker only

**Live access:** not authorized

## 1. Decision

Run the Claude Gate 2 canary inside a narrowly constructed, unprivileged
bubblewrap mount namespace. Pass the already-open scratch-root capability to
bubblewrap with `--bind-fd` and expose it at the stable internal path
`/canary-root`. Do not change the shared incremental coordinator, isolation
module, Chroma writer, production routing, watcher configuration, or activation
surfaces.

This closes the remaining pathname-authority problem at the process boundary:
the unchanged coordinator sees ordinary stable paths, while the namespace pins
those paths to the descriptor-selected scratch inode. Host replacement of the
original pathname does not retarget the namespace mount.

If the namespace fitness gate cannot be satisfied on the execution host, stop
with `NO_GATE2_ROUTE`. Gate 1 on-demand Claude indexing remains the supported
product path.

## 2. Why this decision is needed

OpenAI Security Review failed Gate 2 tip
`10322a6bc23a9ca38da310520f28395eaddda219` on six findings. Cursor's local
corrective at `e007a22b24754a93d9cbd15d02269d422d371c4a` addresses findings #1
and #3–#6. Finding #2 remains:
the coordinator and Chroma writer resolve scratch paths and configuration by
pathname after the canary's preflight.

The original Gate 2 plan explicitly prohibited changes to
`incremental_jsonl.py`. Attempting to repair finding #2 solely inside the
canary led to unstable `/proc/self/fd/<n>` configuration paths, private loader
patching, and incomplete authority transfer. The remaining choice is either a
process-level namespace or a shared runtime authority redesign.

## 3. Options considered

### Option A — descriptor-bound bubblewrap namespace (chosen)

The launcher opens the scratch root and granted source with no-follow flags,
performs host Gate 0, and publishes an immutable snapshot through the held root
descriptor before bubblewrap starts. It then opens that published snapshot and
passes the root and snapshot descriptors to bubblewrap. Bubblewrap mounts the
root at `/canary-root` and the snapshot read-only at
`/canary-root/home/.claude/projects/granted/<alias>.jsonl`. The worker uses
`HOME=/canary-root/home`, so normal `detect_format()` dispatch recognizes the
source as Claude input. It sees no host pathname alias and no production home or
data directories.

Advantages:

- confines the safety mechanism to the Claude canary and its worker;
- preserves stable paths across replay runs;
- keeps checkpoint and configuration values independent of file-descriptor
  numbers;
- leaves Kiro and Codex runtime behavior untouched;
- turns host pathname replacement into an irrelevant operation after binding;
- removes network access through a separate network namespace.

Costs:

- Linux-only;
- depends on bubblewrap 0.12.0 or newer and enabled unprivileged user
  namespaces;
- the launcher owns a concrete sandbox policy and must test every bind;
- crash/replay tests must consistently enter the same internal layout.

### Option B — shared configuration and filesystem authority (rejected now)

Add capability-aware path resolution to `incremental_jsonl_isolation.py`, pass
an immutable configuration authority through `incremental_jsonl.py`, and teach
`chroma_write_store.py` to consume that authority rather than reopening a
pathname.

This is architecturally coherent but has a materially larger regression
surface. `production_chroma_write_session` also protects the production
`convmem.py add` path. The change would require one shared-code owner plus
regressions across Kiro, Codex, isolation workers, canary grants, and production
ledger writes. Gate 2 does not justify that blast radius while a canary-only
boundary is viable.

### Option C — stop Gate 2 (fallback)

Retain the merged Gate 1 adapter and explicit `convmem index --file` workflow.
Do not build an automatic incremental Claude route. This is the mandatory
outcome if Option A's fitness gates fail.

## 4. Verified feasibility

The planning host reported:

- `/usr/bin/bwrap`, version 0.12.0;
- Linux `7.2.6-arch2-1`;
- unprivileged user namespaces enabled;
- `user.max_user_namespaces = 2147483647`;
- non-setuid bubblewrap binary;
- successful `--unshare-all` execution with production ConvMem paths absent;
- successful descriptor-based `--bind-fd` root mount;
- writes remained attached to the mounted inode after the host root pathname
  was renamed and replaced.

These observations establish feasibility on this host. A follow-up experiment
also reproduced empty effective and bounding capability sets, read-only source
and configuration mounts, and no inherited host descriptors beyond standard
stdio plus bubblewrap's child status channel. A synthetic adapter probe confirmed
that the Claude-compatible path dispatches normally when `sessionId` is present,
that missing-id input remains unroutable, and that `read_session_meta()` falls
back to the validated filename alias. They are not a runtime grant or a
substitute for implementation review.

Bubblewrap is a sandbox construction tool rather than a complete policy. The
launcher therefore owns the allowlist. Version 0.12.0 is the minimum because
the upstream release and advisory identify 0.12.0 as the fix for
GHSA-pxhw-h44j-8pfx, the setup-time absolute-symlink traversal defect. The
launcher still runs a real descriptor-bind fitness probe; version alone is not
acceptance evidence and a distribution backport does not waive the probe.

## 5. Namespace contract

The launcher must build one fixed command shape:

1. Resolve `/usr/bin/bwrap`; reject another binary, a setuid binary, or a
   version below 0.12.0.
2. Run an actual disposable namespace probe before opening transcript content.
3. Open the scratch root with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`, run host Gate
   0, and capture the exact granted source through the held root descriptor.
   Host capture owns the existing `O_TMPFILE` plus capability-relative `linkat`
   publication. The worker never republishes the live source.
4. Open the published snapshot read-only with `O_NOFOLLOW|O_CLOEXEC`; bind the
   root fd read-write to `/canary-root` and expose the snapshot read-only at
   `/canary-root/home/.claude/projects/granted/<alias>.jsonl`. The alias is the
   validated `SourceAlias`. Routed fixtures must carry `sessionId`, as required
   by the existing detector. A separate metadata-contract test must prove that
   the helper fallback uses this alias rather than the generic name `session`;
   missing-id input must remain unroutable through normal detection.
5. Pre-create the final validated config at
   `/canary-root/home/.config/convmem/config.toml`, record its host digest, and
   supply the same bytes as read-only data at
   `/canary-root/home/.config/convmem/config.toml`. Every path in it uses the
   stable `/canary-root/...` prefix. The destination already exists, so the
   overlay must not leave a zero-byte configuration placeholder. The declared
   source mountpoint placeholder is zero-length on the host and must be recorded
   and ignored outside the namespace.
6. Bind only the interpreter/runtime, repository code, required shared
   libraries, and certificate-independent resources needed by the offline
   worker. Do not bind the host home, `/run/user`, production ConvMem data,
   agent transcript roots, sockets, D-Bus, or provider credentials.
7. Use `--unshare-all`, explicit `--unshare-user`, `--disable-userns`,
   `--die-with-parent`, and `--new-session`. Never use
   `--not-a-security-boundary` or `--share-net`.
8. Start from `--clearenv`, set `HOME=/canary-root/home`, and add only the fixed
   canary environment.
9. Run the worker at a stable read-only application path and use
   `/canary-root` for every mutable output.

The worker must reject any boundary, source, or configuration path that does
not equal the fixed namespace paths. It must also prove network denial and
absence of known production paths before coordinator construction.

## 6. Authority and data flow

```text
host exact-source grant
        |
        v
host Gate 0 + O_NOFOLLOW source/root descriptors
        |
        v
host O_TMPFILE/linkat capture -> immutable scratch snapshot
        |
        v
bwrap --ro-bind-fd snapshot
      -> /canary-root/home/.claude/projects/granted/<alias>.jsonl
      --bind-fd scratch   -> /canary-root
        |
        v
unchanged IsolationBoundary('/canary-root')
        |
        v
unchanged IncrementalJsonlCoordinator + Chroma writer
        |
        v
/canary-root state, Chroma, export, processed log
```

The open descriptors are host-side selection authority. The namespace mounts
are worker-side path authority. Device and inode numbers are evidence and
wiring checks; they do not replace the descriptors.

All persisted paths are root-relative or use the stable `/canary-root` prefix.
No persisted artifact or digest may contain a host scratch pathname, a file
descriptor number, or `/proc/self/fd`.

## 7. Gate 0 placement

The real watcher and credential probes run in the host launcher immediately
before capture and again immediately after the worker exits, because the
isolated PID and service view cannot observe the host watcher reliably. The
launcher does not accept a caller report, digest, hook object, or environment
override. A post-run active or indeterminate watcher makes the canary evidence
fail; it does not attempt to roll back scratch-only output.

The worker independently verifies namespace properties, fixed paths, config,
source identity, network denial, and production-path absence. It does not
claim to re-run the host watcher probe.

Live execution still requires Ryan to arrange an inactive watcher window. The
pre/post checks are boundary evidence, not proof that a watcher could not start
and stop entirely during the run. The namespace does not grant permission to
stop or start services.

## 8. Threat model and limits

The design protects against:

- same-path replacement of the host scratch root after descriptor binding;
- aliases and symlinks in the selected root or source;
- accidental access to production home, data, locks, sockets, and credentials;
- network/provider access;
- unstable per-process fd paths in persisted state;
- canary code escaping through ordinary absolute paths.

It does not protect against a privileged host administrator, kernel compromise,
or malicious modification of the bubblewrap executable. It also does not make
the production watcher safe or authorize watching Claude transcripts.

## 9. Fitness gates

Implementation is acceptable only if adversarial tests prove:

- binary/version/setuid validation and a real namespace probe fail closed;
- the descriptor-bound root survives host rename and same-path replacement;
- a source descriptor remains read-only and bound to the granted identity;
- host production paths and sockets are absent;
- network access is unavailable;
- config is immutable at the coordinator's expected pathname;
- normal `detect_format()` returns `jsonl_claude_session` for the mounted path;
- first-run evidence asserts the explicit expected session id and sanitized unit
  content; missing-id input is refused by normal detection, and a separate
  metadata-contract test asserts its fallback id equals the validated alias
  rather than the generic name `session`;
- first run, replay, append, repair, and crash recovery use the same stable
  `/canary-root` paths;
- checkpoints and evidence contain no host path, fd number, transcript text,
  environment content, or credential material;
- bubblewrap setup failure leaves no snapshot or coordinator mutation;
- Kiro-only default routing and isolated Codex behavior remain unchanged.

The implementation must rerun the existing Claude, Kiro, and Codex focused
route suites plus the Gate 1 containment suite. Namespace integration tests may
use one explicit prerequisite skip reason on incompatible hosted runners, but
any skip means finding #2 remains unproved. Exact-tip acceptance on the intended
host requires every finding-#2 namespace test to run and pass.

The baseline has three layers and must not be summarized as merely "shared code
unchanged":

1. merged base `e6a0634c214cf07c89b551d13410bb276a93b38d`;
2. expected Gate 2 adapter and registry additions, including
   `incremental_jsonl_formats.py` (byte-identical at `a95cef3` and `e007a22`,
   and previously included in Kiro's implementation PASS; later safety FAILs
   concerned the canary);
3. protected runtime files `incremental_jsonl.py`,
   `incremental_jsonl_isolation.py`, and `chroma_write_store.py`, whose diffs
   must be empty from the merged base through the final implementation.

## 10. Exit condition

Return `NO_GATE2_ROUTE` if any of these is true:

- bubblewrap 0.12.0+ or unprivileged user namespaces are unavailable on the
  intended host;
- the minimal filesystem allowlist cannot run the coordinator without exposing
  production paths;
- descriptor mounts do not preserve the fixed path across replay/crash runs;
- security review finds an escape that requires modifying shared runtime code;
- the maintenance burden exceeds the value of automatic Claude capture, as
  decided by Ryan after the Kiro design verdict and namespace fitness evidence.

`NO_GATE2_ROUTE` is a valid completion. Gate 1 remains available on demand. The
five local corrections at `e007a22` remain branch-only evidence and are not
proposed for a standalone PR unless Ryan separately authorizes that disposition.

## 11. Shared-code fallback boundary

If Ryan later rejects the namespace dependency and still wants Gate 2, start a
new architecture decision. It must name one owner and cover:

- `incremental_jsonl_isolation.py` and its isolation/grant workers;
- `incremental_jsonl.py` and all Kiro/Codex/Claude route regressions;
- `chroma_write_store.py`, including `convmem.py add` production-ledger tests;
- stable logical paths versus runtime capability resolution;
- immutable config consumption and any checkpoint schema migration.

That fallback is not authorized by this architecture.

## 12. Scope locks

This architecture grants no implementation, PR, live transcript access, live
canary, production routing, watcher/source change, issue #314 work, merge, or
activation. Issue #313 remains tracking context until a reviewed successor tip
exists.

## 13. References

- [Bubblewrap upstream README and sandbox-policy responsibility](https://github.com/containers/bubblewrap/blob/main/README.md)
- [Bubblewrap 0.12.0 release notes, including descriptor binds and setup hardening](https://github.com/containers/bubblewrap/releases/tag/v0.12.0)
- [GHSA-pxhw-h44j-8pfx setup-time symlink traversal advisory](https://github.com/containers/bubblewrap/security/advisories/GHSA-pxhw-h44j-8pfx)
