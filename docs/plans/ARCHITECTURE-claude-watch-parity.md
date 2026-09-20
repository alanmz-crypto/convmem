# Architecture — Claude Watch Parity

**Arc:** Claude Watch Parity

**State:** `READY_FOR_KIRO_REVIEW`

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
performs host Gate 0, then passes those descriptors to bubblewrap. Bubblewrap
mounts the root at `/canary-root` and the source read-only at a fixed internal
path. The worker sees no host pathname alias and no production home or data
directories.

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

These observations establish feasibility on this host. They are not a runtime
grant or a substitute for implementation review.

Bubblewrap is a sandbox construction tool rather than a complete policy. The
launcher therefore owns the allowlist. Version 0.12.0 is the minimum because it
contains the upstream fix for the 2026 setup-time symlink traversal advisory.

## 5. Namespace contract

The launcher must build one fixed command shape:

1. Resolve `/usr/bin/bwrap`; reject another binary, a setuid binary, or a
   version below 0.12.0.
2. Run an actual disposable namespace probe before opening transcript content.
3. Open the scratch root with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`; bind that fd
   read-write to `/canary-root` with `--bind-fd`.
4. Open the exact granted source read-only with `O_NOFOLLOW|O_CLOEXEC`; expose
   it read-only at `/source/session.jsonl` with `--ro-bind-fd`.
5. Supply the final validated config as read-only data at
   `/canary-root/home/.config/convmem/config.toml`. Every path in it uses the
   stable `/canary-root/...` prefix.
6. Bind only the interpreter/runtime, repository code, required shared
   libraries, and certificate-independent resources needed by the offline
   worker. Do not bind the host home, `/run/user`, production ConvMem data,
   agent transcript roots, sockets, D-Bus, or provider credentials.
7. Use `--unshare-all`, explicit `--unshare-user`, `--disable-userns`,
   `--die-with-parent`, and `--new-session`. Never use
   `--not-a-security-boundary` or `--share-net`.
8. Start from `--clearenv` and add only the fixed canary environment.
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
bwrap --ro-bind-fd source -> /source/session.jsonl
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
before bubblewrap starts, because the isolated PID and service view cannot
observe the host watcher reliably. The launcher does not accept a caller
report, digest, hook object, or environment override.

The worker independently verifies namespace properties, fixed paths, config,
source identity, network denial, and production-path absence. It does not
claim to re-run the host watcher probe.

Live execution still requires Ryan to arrange an inactive watcher window. The
namespace does not grant permission to stop or start services.

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
- first run, replay, append, repair, and crash recovery use the same stable
  `/canary-root` paths;
- checkpoints and evidence contain no host path, fd number, transcript text,
  environment content, or credential material;
- bubblewrap setup failure leaves no snapshot or coordinator mutation;
- Kiro-only default routing and isolated Codex behavior remain unchanged.

The implementation must rerun the existing Claude, Kiro, and Codex focused
route suites plus the Gate 1 containment suite. Shared runtime files must have
an empty diff against the execution base.

## 10. Exit condition

Return `NO_GATE2_ROUTE` if any of these is true:

- bubblewrap 0.12.0+ or unprivileged user namespaces are unavailable on the
  intended host;
- the minimal filesystem allowlist cannot run the coordinator without exposing
  production paths;
- descriptor mounts do not preserve the fixed path across replay/crash runs;
- security review finds an escape that requires modifying shared runtime code;
- the maintenance burden exceeds the value of automatic Claude capture.

`NO_GATE2_ROUTE` is a valid completion. Gate 1 remains available on demand.

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
