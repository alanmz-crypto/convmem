# Architecture — Claude Watch Parity

**Arc:** Claude Watch Parity

**State:** `KIRO_PASS_WITH_CONDITIONS` at `290294d`; C1–C4 incorporated for carry-forward check

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

The launcher creates a host-only control root containing sibling `scratch` and
`snapshot-vault` directories, opens both with no-follow flags, and performs host
Gate 0. It publishes an immutable snapshot through the held vault descriptor
before bubblewrap starts. It then opens that published snapshot and passes only
the scratch and snapshot descriptors to bubblewrap; the vault and control root
are never bound. Bubblewrap mounts the scratch root at `/canary-root` and the
snapshot read-only at
`/canary-root/home/.claude/projects/granted/<alias>.jsonl`. The worker uses
`HOME=/canary-root/home`, so normal `detect_format()` dispatch recognizes the
source as Claude input. It sees no traversable host pathname alias and no
production home or data directories. Linux mount metadata can disclose host
mount-source names; section 8 bounds that non-authoritative exposure.

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
3. Create a mode-0700 host control root outside all configured watch roots.
   Create sibling `scratch` and `snapshot-vault` directories through its held
   dirfd and open both with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`. Run host Gate 0
   against both. Host capture publishes through the held vault descriptor with
   `O_TMPFILE` plus capability-relative `linkat`. The worker never republishes
   the live source, and the vault/control descriptors never cross the namespace
   boundary.
4. Open the published snapshot read-only with `O_NOFOLLOW|O_CLOEXEC`; bind the
   root fd read-write to `/canary-root` and expose the snapshot read-only at
   `/canary-root/home/.claude/projects/granted/<alias>.jsonl`. The alias is the
   validated `SourceAlias`. Routed fixtures must carry `sessionId`, as required
   by the existing detector. A separate metadata-contract test must prove that
   the helper fallback uses this alias rather than the generic name `session`;
   missing-id input must remain unroutable through normal detection.
5. Pre-create the final validated config at
   `/canary-root/home/.config/convmem/config.toml`, record its host digest, and
   supply the same bytes as read-only data at that path. Every path in it uses
   the stable `/canary-root/...` prefix. The overlay must expose the supplied
   bytes in the namespace and leave the pre-existing host file byte-identical.
   It must not create or replace the host config with a zero-byte placeholder.
6. Pre-create the source mountpoint at
   `/canary-root/home/.claude/projects/granted/<alias>.jsonl`. This declared
   zero-length host placeholder is distinct from the immutable snapshot bound
   over it inside the namespace. Record its existence and size, keep it outside
   host source discovery, and assert it is unchanged after the worker exits.
7. Bind only the interpreter/runtime, repository code, required shared
   libraries, and certificate-independent resources needed by the offline
   worker. Do not bind the host home, `/run/user`, production ConvMem data,
   agent transcript roots, sockets, D-Bus, or provider credentials.
8. Use `--unshare-all`, explicit `--unshare-user`, `--disable-userns`,
   `--die-with-parent`, and `--new-session`. Never use
   `--not-a-security-boundary` or `--share-net`.
9. Start from `--clearenv`, set `HOME=/canary-root/home`, and add only the fixed
   canary environment.
10. Run the worker at a stable read-only application path and use
   `/canary-root` for every mutable output.

### 5.1 Control-root create and reopen contract

The launcher never accepts an arbitrary absolute control-root path. A new root
is created with `mkdirat(..., 0o700)` under one trusted canary parent dirfd and
opened with `O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC`. Replay may reopen only the
previously issued opaque root id beneath that same parent, using dirfd-relative
operations and the same no-follow flags.

Before reading markers or source bytes, `fstat` must prove that the control,
scratch, and vault descriptors:

- are directories rather than symlinks or other file types;
- are owned by the current effective uid;
- have exact mode `0700`, rejecting any group or other permission bits;
- share one `st_dev`, so the control/vault publication and lifecycle assumptions
  do not cross filesystems.

Any mismatch refuses before capture. The launcher then acquires the lifecycle
lock described in section 7.

### 5.2 Snapshot lifecycle

Every worker invocation performs a new host capture. The host publishes the
snapshot under the unbound vault as `<capture-id>.jsonl`, where
`capture-id` is a fresh 128-bit lowercase hexadecimal value generated by the
launcher. The filename contains no alias, host path, transcript text, or file
descriptor number. `O_TMPFILE` plus capability-relative `linkat` publishes the
new name once; `EEXIST` fails closed and generates no replacement attempt.

The host filename is never coordinator identity. Each fresh snapshot fd is
mounted at the same Claude-compatible path
`/canary-root/home/.claude/projects/granted/<alias>.jsonl`. Therefore first run,
unchanged replay, append, repair, and injected worker/coordinator crash recovery
preserve the coordinator's source path and `path_key` while the host launcher
remains alive, even though their host snapshot inodes and names are different.
An append run captures the new complete source bytes; it does not mutate a prior
snapshot. Launcher crash is not same-root recovery: `.active` causes durable
quarantine on the next lock holder.

The launcher owns snapshot retention:

- an anonymous inode that was never linked disappears when its fd closes;
- a published snapshot remains immutable until that worker exits;
- after an ordinary exit, the launcher removes that run's snapshot by held
  vault dirfd only after the worker fd closes and host revalidation succeeds;
- after a worker crash, the host launcher performs the same cleanup in
  `finally`; if the launcher itself crashes, the prior snapshot remains as a
  stale declared artifact but is never reused;
- a later invocation always creates a new capture id, inventories stale names
  through the held directory descriptor, and may remove only allowlisted
  regular files after identity checks;
- cleanup uncertainty or an unexpected entry quarantines the control root.
  Replay then requires a new clean root and cannot use outputs from the failed
  evidence run.

Before cleanup, the launcher reopens the published name through the held vault
dirfd, requires the original device/inode/size, hashes the full bytes, and
requires the original capture digest. These are the snapshot "identity checks."
A missing name or mismatch fails evidence and durably quarantines the entire
control root before any cleanup attempt. Evidence records the capture-id format,
source digest, digest-recheck outcome, and cleanup outcome in closed fields, but
never records the host snapshot path.

The namespace has no writable alias to the snapshot inode: the vault is absent,
the old `/canary-root/sources/claude-capture/runs` path is absent, and only the
read-only Claude mount is visible. The worker must fail to write, truncate, or
unlink the source through every reachable namespace path. Host-side device,
inode, size, bytes, and digest must remain unchanged after those attempts.

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
host O_TMPFILE/linkat capture -> immutable unbound-vault snapshot
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

The real watcher, credential, and configured-watch-root probes run in the host
launcher immediately before capture and again immediately after the worker
exits, because the isolated PID and service view cannot observe the host watcher
reliably. The launcher does not accept a caller report, digest, hook object, or
environment override. A post-run active or indeterminate watcher makes the
canary evidence fail; it does not attempt to roll back scratch-only output.

Gate 0 canonicalizes every configured watch root plus the host control,
scratch, and vault roots before opening transcript content. Their trees must be
disjoint in both directions: no canary root can be inside a watched root, and no
watched root can be inside a canary root. Evidence records only a closed
`watch_roots_disjoint=true` result. A control root from a failed post-run watcher
check is quarantined and must not be reused for replay or later evidence.

Quarantine is durable, not launcher memory. Immediately after opening the
control root, the launcher acquires a nonblocking exclusive `flock` on the held
control dirfd and retains it through snapshot cleanup, post-run checks, and
marker removal. Lock contention refuses without inspecting or modifying
markers; it never quarantines the active owner. Kernel lock release on process
exit makes a found `.active` marker unambiguously stale after the new launcher
has acquired the lock.

Under that lock, the launcher creates an unbound `.active` marker through the
held control-root dirfd and fsyncs that directory before opening transcript
content. Failure to create or fsync `.active` refuses before capture. After
verified snapshot cleanup and passing post-run checks, it removes `.active` and
fsyncs again. Finding `.active` at startup means the prior launcher did not
close cleanly: atomically rename `.active` to `.quarantined` through the held
dirfd, fsync the directory, and refuse the root. Every post-run failure uses the
same transition. Its terminal marker invariant is exactly
`.quarantined=present` and `.active=absent`; never both and never neither. Tests
assert the marker set after each failure. A root with `.quarantined` is never
reused; removal is a separate host cleanup action outside evidence production.

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
`/proc/self/mountinfo` can reveal the literal host control-root prefix and the
capture-id filename used as mount sources. Those strings are disclosure-only,
not authority: the corresponding host paths are absent and cannot be traversed
inside the namespace. The worker, evidence assembler, and persistence surfaces
must not copy either string into output or state.

## 9. Fitness gates

Implementation is acceptable only if adversarial tests prove:

- binary/version/setuid validation and a real namespace probe fail closed;
- the descriptor-bound root survives host rename and same-path replacement;
- a source descriptor remains read-only and bound to the granted identity;
- host production paths and sockets are absent;
- network access is unavailable;
- config is immutable at the coordinator's expected pathname;
- the snapshot vault and control paths are absent from the namespace, and the
  deprecated scratch capture path is absent;
- write, truncate, and unlink attempts against every reachable source alias
  fail while the host snapshot identity and digest remain unchanged;
- control-lock contention refuses without changing markers; marker creation or
  directory-fsync failure refuses before capture;
- normal `detect_format()` returns `jsonl_claude_session` for the mounted path;
- first-run evidence asserts the explicit expected session id and sanitized unit
  content; missing-id input is refused by normal detection, and a separate
  metadata-contract test asserts its fallback id equals the validated alias
  rather than the generic name `session`;
- first run, replay, append, repair, and worker/coordinator crash recovery with
  a surviving host launcher use the same stable `/canary-root` paths;
- only the designated injected `CRASH_EXIT` sentinel counts as recoverable
  worker/coordinator crash evidence; a signal, another exit code, or an
  unexpected process termination fails evidence and receives exactly one
  diagnostic rerun in a fresh clean process and root, with both outcomes
  recorded and neither counted as recovery;
- checkpoints and evidence contain no host path, fd number, transcript text,
  environment content, or credential material;
- stdout, stderr, evidence, checkpoints, exports, and processed state contain
  neither the literal control-root prefix nor the capture id observed in
  `/proc/self/mountinfo`;
- worker stdout and stderr are launcher-created pipes, never host files;
  `close_fds=True` and the fixed setup `pass_fds` set are verified before
  execution, and the worker confirms fd 1 and fd 2 are pipes;
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

The intended execution host is explicit rather than inferred. Closed evidence
uses the `primary_convmem_host` enum plus
`HMAC-SHA256(key=machine-id, message="convmem-gate2")`. This follows the
application-specific machine-identity pattern: raw hostname and machine-id are
never serialized. The VERIFY document names the human-readable host role,
kernel, and bubblewrap version.

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
