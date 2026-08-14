# Cursor Handoff: CG-1 Literature Verification (with ChatGPT)

**Date:** 2026-08-10
**Author:** Kiro (review lane)
**For:** Cursor (Composer 2.5)
**Collaborator:** ChatGPT (has repo access + literature PDFs on desktop)

---

## Task

Verify that the CG-1 committed-generation implementation correctly applies the
principles from the reference literature Ryan has provided to ChatGPT. ChatGPT
has the papers; you have the code. Together you confirm the implementation isn't
just "working" but is grounded in the right engineering foundations.

## Your role (Cursor)

You are the **implementation verifier**. You:

- Read the CG-1 source code in `/tmp/convmem-cg1`
- Trace specific claims about durability, atomicity, and correctness back to
  code paths
- Identify where the implementation makes assumptions about storage behavior
- Report what you find to Ryan, who relays to ChatGPT for literature validation

You do NOT:
- Modify the CG-1 code (Luna wrote it; review only)
- Make claims about what the literature says (that's GPT's job)
- Commit, push, or open PRs from this task

## ChatGPT's role

ChatGPT has:
- The full CG-1 source (via the onboard bundle or GitHub)
- Reference literature PDFs (on Ryan's desktop, uploaded to GPT)
- The locked architecture and review-round amendments

GPT validates whether:
- The durability assumptions match what the literature establishes
- The recovery model (fail-closed, no "most complete") is consistent with
  established correctness proofs
- The fsync/journal/WAL observations match published SQLite/ext4 behavior
- The copy-on-write + atomic-pointer pattern is a sound application of the
  referenced techniques

## What literature is involved

Ryan has provided papers/references to ChatGPT covering topics like:
- SQLite durability guarantees (journal modes, synchronous pragmas, fsync semantics)
- ext4 filesystem behavior (write ordering, metadata journaling, rename atomicity)
- Copy-on-write and generation-based approaches to safe data replacement
- Atomic file operations on POSIX systems

You don't need to read the papers yourself. Your job is to surface the specific
implementation details that need to be checked against them.

## CG-1 implementation location

All code is uncommitted in the `/tmp/convmem-cg1` worktree:

```
Branch: feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate
Base:   0be0a05 (current main)
```

### Key files to examine

| File | What it does | Literature-relevant aspects |
|------|-------------|---------------------------|
| `file_generation_contract.py` | Deterministic identities, canonical hashing | Hash stability, canonical JSON serialization |
| `file_generation_pointer.py` | Durable manifests, per-owner active pointers | Atomic publication, crash recovery, fsync assumptions |
| `file_generation_store.py` | Copy-on-write Chroma facade | Generation isolation, read mediation, backpressure |
| `file_generation_validate.py` | Fresh-process cold validation | Process-crash recovery proof, SQLite sequence positions |
| `file_generation_builder.py` | Candidate construction | Build/commit separation, overlay dedupe |
| `ingest_dedupe.py` (diff) | Logical-identity-aware deduplication | Identity comparison semantics |

### The modified tracked file

`ingest_dedupe.py` has a 62-line diff adding `generation_identity_fields` support.
This is the bridge between the existing dedupe system and CG-1's logical/physical
identity distinction.

## Specific verification questions

These are the claims that need literature grounding. For each one, trace the
code path in the implementation and report what you find:

### 1. Pointer atomicity

**Claim:** Active pointer promotion is atomic because it uses `atomic_write_json()`
which writes to a temp file, fsyncs, then renames.

**Trace:** `file_generation_pointer.py` → `publish_active_pointer()` → calls
`atomic_write_json(path, pointer)`.

**Literature question for GPT:** Does POSIX rename guarantee that a crash during
rename cannot leave the target in a partial state on ext4 with `data=ordered`?

### 2. Manifest immutability

**Claim:** Once a manifest is published, re-reading it and comparing bytes proves
it was durably written.

**Trace:** `publish_manifest()` writes via `atomic_write_json`, then re-reads and
compares. If mismatch → `GenerationQualificationError`.

**Literature question for GPT:** Is read-after-write sufficient proof of durability
when the write used fsync + rename? Or could the read succeed from page cache
before the rename is durable?

### 3. Chroma row durability (Bar P)

**Claim:** After Chroma's upsert returns, rows survive process crash (but NOT
necessarily power loss) because SQLite uses `synchronous=FULL` with
`journal_mode=DELETE`.

**Trace:** `file_generation_validate.py` → `BAR_P_DURABILITY` dict documents the
claim. `cold_validate()` opens Chroma in a new process and checks exact rows.

**Literature question for GPT:** With `synchronous=FULL` + `journal_mode=DELETE`,
what exactly survives process crash vs. power loss? Is the "no post-unlink
directory fsync" gap material for data that was committed before the crash?

### 4. Recovery semantics

**Claim:** Recovery never chooses "most complete" — it accepts only the generation
named by the structurally valid visible pointer.

**Trace:** `recover_active_pointer()` reads the existing pointer, validates it
against the referenced manifest, requires exact Chroma match, then republishes.

**Literature question for GPT:** Is this consistent with established crash-recovery
principles (e.g., write-ahead log recovery always replays the committed log, never
infers intent from partial state)?

### 5. Generation isolation

**Claim:** Inactive generation rows cannot appear in query results because the
active predicate is passed to Chroma's `where` clause.

**Trace:** `FileGenerationStore._active_where()` constructs `$or` predicates;
`_query()` passes this to `col.query(where=...)`.

**Literature question for GPT:** Is there a TOCTOU risk where the active map
changes between predicate construction and Chroma execution? Does it matter for
correctness given CG-1's scope (hermetic, not production)?

## How to collaborate

Ryan is the relay between you and GPT. Your workflow:

1. **Read the CG-1 code** and trace the claims above
2. **Report findings** to Ryan (what the code actually does at each point)
3. Ryan shares your findings with GPT alongside the literature
4. GPT confirms or flags mismatches between implementation and published guarantees
5. Any issues come back to you for precise code-level characterization

## Boundaries

- **Do not modify CG-1 code.** This is review/verification only.
- **Do not expand scope** to production activation, CG-2, or Shadow Ledger.
- **Do not run the CG-1 tests** unless Ryan asks (they passed in Luna's session;
  re-running is a separate grant since the worktree has write restrictions).
- **Do not confuse CG-1 with JudgeBench.** The live-driver branch
  (`feat/2026-08-10-judgebench-live-driver`) is parked, separate work.

## Protocol reminders

- You are on `main` in `~/Projects/convmem`. CG-1 code is in `/tmp/convmem-cg1`.
- `convmem doctor` → `brief` → `unresolved` at session start.
- Do not edit tracked files on `main` without `convmem work start`.
- This is a read-only verification task — no branch needed unless findings require
  a document commit.

## Success criteria

The task is done when:
- All 5 verification questions above have traced code paths
- Ryan has relayed findings to GPT
- GPT has confirmed or flagged each claim against the literature
- Any discrepancies are documented (not fixed — that's a separate task)
