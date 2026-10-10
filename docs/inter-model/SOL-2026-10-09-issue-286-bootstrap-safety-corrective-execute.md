# Implementation Handoff: Issue #286 Bootstrap Safety Corrective

**Arc:** Codex  
**Date:** 2026-10-09  
**Author:** Sol conflict-adjudication lane  
**For:** Cursor implementation lane  
**Authorization:** Ryan, 2026-10-09, explicit chat authorization of the exact
bounded scope below

---

## Resume state

| Field | Value |
|---|---|
| **State** | `IMPLEMENTED_REVIEW_PENDING` — corrected implementation and focused evidence complete |
| **Baseline** | `956d74e8bab4a6c397a80a14a5709043b8b205ef` on `origin/main` after Switchboard PR #370 |
| **Implementation branch** | `fix/2026-10-09-issue-286-bootstrap-replay-authority-corrective` |
| **Corrected implementation** | `b108ab6` on the current-main branch; `a23eb22` preserves the first implementation for comparison |
| **Push status** | corrected implementation pushed to the explicit branch ref |
| **PR** | not opened; PR creation remains separately Ryan-granted |
| **Ryan GATE** | none for this bounded hermetic implementation; live resources and PR creation remain ungranted |
| **Required review** | after correction, Kiro design review and GitHub Copilot safety audit on the same exact implementation revision |

---

## Product goal and current system

Arc Codex should transform only the overlap frontier and appended messages for
one governed Kiro transcript, reuse completed transformations after a crash,
and make paid work measurable and bounded. PR #365 placed the exact-source,
default-off bootstrap route on `main`, but the corrected Sol packet showed that
the command cannot yet enforce the requested paid-processing cap, preserve
failure accounting, or bind all effective transform inputs.

The reviewed decision packet is
`docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-review-packet.md` at commit
`4aecb960c7354c130cbb67d84cfa87bfa5b0c2a6`, SHA-256
`23553b71830e43e90ec3a9b3387a4380ca71e9985414a74ed57c323fbb531e06`.
Kiro and Copilot both passed that exact revision as an accurate `NO-GO` packet.

## What to build

Strengthen the existing one-shot bootstrap path so a future exact-resource
grant can enforce a durable provider HTTP-attempt ceiling, bind the effective
transform configuration, emit durable accounting for success and handled
failure, and recover deterministically without resetting budget authority.
Keep the normal default-off and legacy ingest paths behaviorally unchanged.

**Why this exists:** a chunk cap limits intended work but does not cap nested
provider retries. The current receipt exists only after success, the grant does
not bind live config/provider values, and current evidence cannot fully explain
every failure or append-only follower change.

---

## Integration points

- `scripts/bootstrap-incremental-jsonl.py` — grant validation, fail-closed
  preflight, invocation/recovery allowance, and final receipt.
- `incremental_jsonl.py` — durable operation/budget state, transaction recovery,
  prepared-cache reuse, follower evidence, and streaming export rollback.
- `ingest.py` and `llm.py` — optional bootstrap-only provider-attempt permit and
  usage reporting without changing ordinary ingest behavior.
- `ingest_dedupe.py` — deterministic transaction-bound evidence for append-only
  dedupe events if the current result surface cannot express it.
- focused tests under `tests/test_incremental_jsonl_*`, plus fallback/provider
  tests only where the shared provider hook requires them.

Keep policy in the coordinator/bootstrap boundary. Do not turn the CLI script
into a second ingestion engine or fork prompt/transformation behavior.

---

## Specification

### 1. Exact grant and transform binding

Extend the one-shot grant with one canonical operation identity and immutable
values sufficient to prove the intended transform:

- exact source path, prefix digest, complete boundary, chunk cap, embedding
  dimension, and verified backup snapshot;
- exact runtime revision and config-file SHA-256;
- transform fingerprint and chunk size/overlap/minimum confidence;
- summarize/distill provider, model, and base URL;
- embedding provider/model;
- `max_provider_http_attempts`; and
- `max_recovery_invocations`, fixed to `1` for this route.

Reject missing, extra, mistyped, noncanonical, or mismatched fields before any
provider call or corpus mutation. Prove the credential exists in the exact
invoking process without writing or printing it. Require fail-closed fallback
behavior and reject any resolved generation binding with `fallback=true`.

### 2. Durable paid-attempt budget

Use `max_provider_http_attempts` as the enforceable paid limit. Token and dollar
usage remain measured evidence, not a pre-call enforcement claim.

- Create operation state under the source's incremental state directory,
  keyed by a stable fingerprint of the exact grant.
- Persist and fsync a permit consumption record **before** each outbound paid
  HTTP attempt.
- Refuse the attempt that would exceed the cap.
- Carry the consumed count across outer retries, internal HTTP retries,
  handled failure, process interruption, and the one same-grant recovery.
- Never reset or replace the ledger because a transaction file was cleaned up.
- Prepared-cache reuse and `replay_forward` must issue zero new provider calls.
- A changed grant creates no authority to recover the old operation.

The optional permit hook must be inactive for every existing non-bootstrap
ingest path.

### 3. Durable receipts and failure taxonomy

Persist append-only, fsynced invocation records tied to the grant fingerprint.
The terminal record for each handled invocation must include:

- invocation ordinal and operation identity;
- outcome, mode, transaction phase, and stable refusal/failure code;
- logical summarize/distill attempts and successes;
- permitted outbound HTTP attempts and the durable cumulative count;
- provider-reported token/usage fields when supplied;
- chunks, summaries, units, active generation, exact suppressions, and semantic
  candidates queued when applicable;
- effective runtime/config/transform/provider/embedding fingerprints; and
- whether recovery remains available.

Cover at least these states explicitly: preflight refusal, `PREPARING`, clean
`transform_failed`, fatal provider authentication/payment refusal, `APPLYING`,
`replay_forward`, rollback, committed bootstrap, and recovery exhaustion.
Abrupt termination may prevent a terminal receipt, but the pre-call budget
ledger and transaction state must still make the consumed authority observable.

### 4. Recovery contract

- A normal successful first run returns mode `bootstrap_existing`.
- An existing compatible `APPLYING` transaction may use the one same-grant
  recovery allowance and return `replay_forward` or a documented rollback
  result without provider work.
- `PREPARING` and clean `transform_failed` recovery must reuse every valid
  prepared artifact and the same durable budget ledger.
- A mismatched source prefix, config/transform binding, runtime, grant
  fingerprint, or exhausted recovery allowance fails closed.
- A second failure after consuming the recovery allowance returns control to
  Ryan; it creates no implicit third invocation.

### 5. Isolation and follower evidence

- Treat dedupe files as append-only: prove their old bytes are an exact prefix
  and every new row is deterministic and bound to the current transaction.
- Derive `exact_suppressed` and `semantic_queued` from that transaction-bound
  diff and carry them into the durable receipt.
- Define the exact non-source collection metadata fields under comparison and
  include document and embedding digests, rather than relying on counts or
  vague "selected metadata."
- Include `synthesis_failures.jsonl`, writer-attestation/census state, prepared
  cache, operation ledger, receipts, and every incremental state file in the
  mutation/evidence inventory.
- Keep the watcher and corpus-writing reconcile paths outside this hermetic
  Execute. Production preflight support may report/refuse competing writers;
  do not start, stop, or modify services here.

### 6. Export and rollback scale

Do not embed all unrelated export lines in `rollback.json` or load/rewrite the
multi-gigabyte export as one in-memory string. Preserve unrelated bytes through
a streaming, lock-held temp-file replacement or another bounded-memory design.
Rollback material should contain only source-owned before-images and the
minimum file authority needed to detect an unsafe restore. Preserve atomic
replace, fsync, source scoping, and exact rollback behavior.

If a bounded-memory correction cannot preserve those properties without a
larger architecture change, stop and return the design fork to Ryan. Do not
ship a second whole-file copy under another name.

---

## What not to build or run

- No live bootstrap or indexing of the named Kiro source.
- No DeepSeek, Ollama, network, or other real provider call.
- No production Chroma, processed log, export, dedupe, checkpoint, backup, or
  source mutation.
- No live config, credential, systemd, timer, watcher, or runtime-pin change.
- No Cursor/Crush/Codex route expansion and no public API redesign.
- No PR creation, merge, issue mutation, force-push, or push to `main`.
- No claim that bootstrap alone demonstrates incremental cost reduction.

---

## Implementation checkpoint

Cursor implemented and pushed the first corrective as `273c27a` on the
post-PR-#369 branch. That exact code is carried as `a23eb22` onto the current
branch based on post-PR-#370 `main` `956d74e`. The four Arc ConvMem Switchboard
planning files are inherited unchanged from `origin/main` and remain outside
this branch's changed path set.

Evidence currently available:

- focused incremental/provider safety set: `140 passed`;
- narrower final safety set: `40 passed`;
- changed-file syntax and whitespace checks: PASS;
- secret scan and critical-invariant manifest: PASS;
- Pylint regression gate: PASS with no new/increased findings; and
- full suite: **not claimed**. The local sandbox makes unrelated CLI tests fail
  when they attempt the hard-coded production writer-lock path under the CI
  config. The first such test passes under Python 3.12 without that sandboxed
  path collision. GitHub CI or an equivalently isolated writable home remains
  required before PR disposition.

The two prior bootstrap-safety branches are preserved as remote backups and
must not be proposed for merge because they predate the current-main baseline.
Only `fix/2026-10-09-issue-286-bootstrap-replay-authority-corrective` is a
candidate for correction and later review.

### Sol-High adjudication and required correction

Kiro issued `PASS` and Copilot issued `FAIL` on exact revision `b68daea`. The
verdicts materially conflicted over whether APPLYING replay preserves the
original rollback and isolation authority. Sol-High adjudicated in Copilot's
favor after tracing the source sequence: `_roll_forward()` reads the original
rollback, then `_commit_generation()` takes a fresh snapshot of partially
applied state and overwrites `rollback.json`. Isolation comparison can therefore
use the mutation as its new baseline, and a later unexpected replay crash can
leave no durable original before-image.

Cursor must correct and prove all three Copilot blockers:

1. APPLYING replay reuses the immutable original rollback and original
   non-source isolation digest. It must not snapshot or overwrite either before
   a terminal commit or exact restoration.
2. Any exception during replay leaves the original rollback authority durable
   on disk. Add hermetic faults that mutate a foreign row and crash after a
   partial apply; recovery must detect/restore the violation and must not spend
   its allowance into an unrecoverable re-baselined state.
3. Embedding dimension must be checked against an independent effective
   authority before any paid provider attempt. Comparing a grant value with a
   settings value injected from that same grant is not evidence. If no
   independent preflight authority is available, refuse before paid work.

The correction must also disable automatic HTTP redirects or account durably
for every redirected request before transport. Normal routes remain default
off and unchanged. All evidence remains hermetic; no live provider or corpus
resource is authorized.

### Corrected implementation checkpoint

Cursor's preserved diff was completed and verified as `b108ab6`:

- APPLYING replay hashes and reuses the original rollback journal, checks the
  original non-source digest before and after apply, and never rewrites that
  journal during replay;
- replay rollback restores source-owned state while preserving the durable
  transaction and rollback authority for a fail-stopped second attempt;
- existing summary and unit rows independently prove the effective embedding
  dimension before provider accounting is entered; absence or disagreement
  refuses before paid work; and
- DeepSeek transport sets `allow_redirects=False`.

Verification evidence:

- new adjudication regressions: `5 passed`;
- selected incremental/provider suite: `270 passed`, with three environment
  failures (temporary lock modes and the managed read-only writer-lock path)
  rerun under isolated `HOME` and restrictive `umask`: `3 passed`;
- governed R2b/Shadow inventory tests: `25 passed`;
- secret scan: PASS;
- critical-invariant manifest: PASS (`16 modules`);
- Pylint regression gate: PASS (`461 findings`, `240 fingerprints`, no
  new/increased findings against `956d74e`); and
- full repository suite: not claimed; CI-equivalent execution remains pending.

---

## Test expectations

All tests must use temporary roots, fake providers, denied network, and
sentinels proving production paths were untouched.

1. **Grant closure:** missing/extra/mismatched binding or fallback rejects
   before calls/writes.
2. **Hard cap:** the attempt beyond the durable HTTP ceiling is refused before
   the fake transport runs.
3. **Crash/restart cap:** consumed permits survive process restart and the
   authorized recovery cannot reset them.
4. **Prepared reuse:** `PREPARING`, `transform_failed`, and `APPLYING` recovery
   reuses durable work and performs no duplicate provider call.
5. **Receipts:** success and every handled failure class produce the required
   durable accounting; abrupt termination leaves enough ledger/transaction
   evidence to reconcile consumed attempts.
6. **Recovery allowance:** exactly one same-grant recovery is available; a
   changed grant or second recovery fails closed.
7. **Dedupe evidence:** previous bytes remain an exact prefix and new events are
   transaction-bound, deterministic, and counted in the receipt.
8. **Non-source isolation:** ids, exact metadata fields, document digests,
   embedding digests, export bytes, processed entries, and unrelated dedupe
   bytes remain unchanged.
9. **Bounded export memory:** the implementation streams the export and does not
   call whole-file `read_text`, `read_bytes`, or equivalent on the export path.
10. **Parity:** absent/default-off configuration and non-bootstrap ingest retain
    their current behavior and signatures.

Run the focused affected tests first, then the repository's required lint and
test gates named by current CI. Do not weaken thresholds or update governed
hashes mechanically without showing why the changed authority bytes require it.

---

## Acceptance criteria

- [ ] A durable permit is consumed before every fake paid HTTP attempt and the
      cap survives every supported restart/recovery path.
- [ ] Exact transform/provider/config/runtime binding fails closed before work.
- [ ] Durable records explain successful, refused, failed, interrupted, and
      recovered invocations without claiming unobservable cost.
- [ ] Recovery performs no duplicate provider work and consumes at most the one
      explicitly granted recovery invocation.
- [ ] Dedupe and non-source isolation evidence is exact and transaction-aware.
- [ ] Export reconciliation and rollback use bounded memory and source-scoped
      before-images.
- [ ] Existing default-off and legacy routes remain behaviorally unchanged.
- [ ] Focused tests, required lint, and the repository suite pass hermetically.
- [ ] Kiro and Copilot receive the same exact final commit and file set.
- [ ] Branch commits are pushed immediately; no PR is opened without a new
      Ryan grant.

---

## Related files

| What | Path |
|---|---|
| Corrected decision packet | `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-review-packet.md` |
| Arc status | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Production architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md` |
| Existing execution plan | `docs/plans/EXECUTION-codex-jsonl-production-integration.md` |
| Bootstrap command | `scripts/bootstrap-incremental-jsonl.py` |
| Coordinator | `incremental_jsonl.py` |
| Transform/provider path | `ingest.py`, `llm.py` |

---

## Leaving / picking up checklist

**Sol (leaving):**

- [x] Ryan's exact Execute authorization recorded.
- [x] Corrected same-revision Kiro/Copilot packet verdicts linked.
- [x] This handoff, `LATEST.md`, and STATUS authorization state committed.
- [x] Authorization branch pushed; implementation branch is created and pushed
      before Cursor starts.

**Cursor (corrective result):**

- [x] Read this file and the Arc Codex STATUS brief before the first edit.
- [x] Worked only on
      `fix/2026-10-09-issue-286-bootstrap-replay-authority-corrective`.
- [x] Preserved the live-resource and provider prohibition.
- [x] Preserved immutable rollback/isolation authority across APPLYING replay.
- [x] Added an independent pre-paid-work embedding-dimension check.
- [x] Disabled redirected paid HTTP transports.
- [x] Cursor Track A transcripts:
      `~/.cursor/projects/home-lauer-local-share-convmem-worktrees-fix-2026-10-09-issue-286-bootstrap-replay-authority-corrective/agent-transcripts/9a735eba-1111-4cf2-ae12-428b483f47ac/9a735eba-1111-4cf2-ae12-428b483f47ac.jsonl`
      and
      `~/.cursor/projects/home-lauer-local-share-convmem-worktrees-fix-2026-10-09-issue-286-bootstrap-replay-authority-corrective/agent-transcripts/f707d20e-a38d-44e6-9e8e-7f81998ccf1a/f707d20e-a38d-44e6-9e8e-7f81998ccf1a.jsonl`.
- [x] Exact code tip, focused evidence, and unresolved full-suite gap recorded.
- [ ] Kiro/Copilot same-revision review and CI-equivalent full-suite evidence.

## TL;DR

Sol-High accepted Copilot's FAIL on the first implementation. Cursor's corrected
implementation at `b108ab6` now preserves original replay authority, proves
dimension before provider work, and disables redirects. Same-revision review
and CI-equivalent full-suite evidence remain. Live bootstrap,
providers, runtime/config, watcher operations, PR creation, and merge remain
separately gated.
