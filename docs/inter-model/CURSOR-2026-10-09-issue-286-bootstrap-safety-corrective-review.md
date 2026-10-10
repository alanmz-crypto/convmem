# Implementation Handoff: issue #286 bootstrap safety corrective

**Arc:** Codex  
**Date:** 2026-10-09  
**Author:** Cursor implementation lane  
**For:** Kiro design review and Copilot safety audit  
**Authorization:** Ryan, 2026-10-09, via the Sol corrective Execute handoff

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `READY_FOR_PR` after required same-revision reviews; no PR is authorized yet |
| **Branch** | `fix/2026-10-09-issue-286-bootstrap-budget-safety` |
| **Tip SHA** | Review the exact pushed branch tip reported in Cursor's completion response; implementation checkpoint before routing docs: `cf8f654` |
| **Push status** | pushed to origin after every commit |
| **PR** | not opened |
| **Ryan GATE** | Same-revision Kiro/Copilot review, then Ryan separately decides PR/live progression |
| **Track A ingest** | `/home/lauer/.cursor/projects/home-lauer-local-share-convmem-worktrees-fix-2026-10-09-issue-286-bootstrap-budget-safety/agent-transcripts/d78bb8ed-6ef2-4540-beb3-c2797dea257a/d78bb8ed-6ef2-4540-beb3-c2797dea257a.jsonl` |

---

## What was built

The disabled-by-default Kiro existing-source bootstrap now consumes a durable
HTTP-attempt permit before provider transport, binds every invocation and
transaction to one immutable runtime/config/provider/transform grant, records
success and failure durably, and reuses paid prepared work during bounded
recovery. Transaction-aware dedupe and non-source isolation evidence close the
review packet's ambiguity, while export snapshot/reconcile/rollback now streams
within a bounded memory envelope.

**Why this exists:** The corrected review packet at `4aecb96` was an accurate
`NO-GO`: the merged command could exceed its paid-work budget after failures,
did not durably account for all outcomes, and did not bind enough execution
identity to make recovery safe.

---

## Integration points

- `bootstrap_safety.py` — canonical grant, operation identity, fsynced journals,
  pre-call permit consumption, cumulative cap, and one recovery allowance.
- `scripts/bootstrap-incremental-jsonl.py` — exact grant construction and
  bootstrap invocation/recovery orchestration.
- `llm.py` — optional context-local bootstrap HTTP permit and usage hooks;
  legacy callers remain unchanged when no hook is installed.
- `incremental_jsonl.py` / `ingest.py` — transaction/grant binding, prepared
  reuse, restart recovery, and streaming export restoration.
- `ingest_dedupe.py` / `chroma_store.py` — deterministic transaction-bound
  dedupe evidence and canonical non-source collection evidence.

---

## Specification

### Inputs

- Canonical reviewed grant fields only: runtime SHA, config hash, source and
  transform identity, chunking, provider/model/base URLs, embedding identity,
  and explicit attempt/recovery limits.
- Existing hermetic bootstrap isolation token and temporary roots.
- No live corpus, source transcript, config, credential, provider, or service.

### Algorithm / behavior

1. Canonicalize and hash the exact grant; reject omitted, changed, or fallback
   execution identity before paid work.
2. Append and fsync an invocation record, then append and fsync an HTTP-attempt
   permit before each provider transport.
3. Append and fsync each success/failure usage outcome; derive remaining budget
   from durable journals on every restart.
4. Permit at most one same-grant recovery invocation and reuse the fsynced
   prepared transform for PREPARING, `transform_failed`, or APPLYING recovery.
5. Bind transaction and dedupe evidence to the same operation/grant; verify
   prefix/source and non-source collection evidence before reuse or rollback.
6. Snapshot, reconcile, and restore source-scoped export rows as streams rather
   than materializing the complete export.

### Output / contract

- Paid attempts cannot exceed the grant cap across failures or restarts.
- Recovery under any changed grant fails closed before provider transport.
- Durable journals distinguish permit, success, and failure accounting.
- Recovery does not duplicate completed paid transform work.
- Default-off and non-bootstrap legacy behavior remain unchanged.

### Constants

The canonical grant schema and journal event versions are defined in
`bootstrap_safety.py`; reviewers should treat field removal or fallback as an
authority change.

---

## What NOT to build

- No live bootstrap, provider call, source read, corpus/config/runtime mutation,
  watcher/service/timer operation, backup action, runtime pin, issue, PR, merge,
  or activation.
- No Crush SQLite or Cursor JSONL coverage; the guarded route remains Kiro-only.
- No claim that Chroma provides an atomic two-collection transaction.

---

## Test expectations

Focused tests in `tests/test_incremental_jsonl_bootstrap_safety.py`,
`tests/test_incremental_jsonl_bootstrap_command.py`, and
`tests/test_incremental_jsonl_live_boundary.py` cover:

1. **Grant closure:** omitted/changed provider, config, runtime, transform, or
   embedding identity fails before transport.
2. **Durable cap:** permits are consumed before fake transport and survive
   failure/restart without exceeding the cumulative budget.
3. **Paid-work recovery:** PREPARING, `transform_failed`, and APPLYING reuse the
   same-grant prepared transform; a second recovery or changed grant is denied.
4. **Isolation evidence:** dedupe and non-source Chroma evidence are canonical,
   transaction-bound, prefix-verified, and idempotent.
5. **Bounded rollback:** large synthetic exports restore source-scoped rows
   without full-export materialization; lock files are private (`0600`).
6. **Legacy compatibility:** flag-off and non-bootstrap routes retain existing
   behavior and do not install bootstrap accounting hooks.

All tests use temporary fixtures and fake or denied providers.

---

## Acceptance criteria

- [x] Durable pre-call provider HTTP-attempt budget and outcome accounting
- [x] Immutable runtime/config/provider/transform grant binding
- [x] PREPARING/`transform_failed`/APPLYING recovery without duplicate paid work
- [x] Transaction-aware dedupe and collection-isolation evidence
- [x] Bounded-memory, source-scoped export rollback
- [x] Default-off and legacy behavior preserved
- [x] Focused tests and repository suite pass hermetically
- [x] Pylint regression, secret-scan, and critical-invariant gates pass
- [x] No live or external operation performed

---

## Branch convention

```text
fix/2026-10-09-issue-286-bootstrap-budget-safety
```

The branch was pushed after each coherent commit. Do not open a PR until Ryan
authorizes delivery after same-revision Kiro and Copilot review. Ryan's normal
squash-merge default is compatible with this branch.

---

## Related files

| What | Path |
|------|------|
| Authorized implementation scope | `docs/inter-model/SOL-2026-10-09-issue-286-bootstrap-safety-corrective-execute.md` |
| Current Arc Codex state | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Durable bootstrap safety primitives | `bootstrap_safety.py` |
| Bootstrap command | `scripts/bootstrap-incremental-jsonl.py` |
| Recovery coordinator | `incremental_jsonl.py` |
| Focused safety tests | `tests/test_incremental_jsonl_bootstrap_safety.py` |
| Command boundary tests | `tests/test_incremental_jsonl_bootstrap_command.py` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on the pushed branch
- [x] `LATEST.md` routes to this review packet
- [x] Arc `STATUS` snapshot and Update Log updated
- [x] Branch pushed

**Reviewers (picking up):**

- [ ] Resolve and record the exact pushed branch tip from the completion response
- [ ] Kiro reviews design conformance at that exact revision
- [ ] Copilot audits safety at that same exact revision
- [ ] Return any material opposing `PASS`/`FAIL` to Sol-High
- [ ] Do not infer PR, live-use, config, runtime, or watcher authorization
