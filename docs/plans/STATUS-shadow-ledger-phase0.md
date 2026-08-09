# Arc Brief — Shadow Ledger Phase 0

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do]. The system currently: [what exists]. Missing: [what doesn't exist yet]."

---

## 1. What This Is For (product goal)

ConvMem's authority today is a Tier-1 Chroma `knowledge_units` collection. Mutations flow
through a small set of `ChromaStore` write methods, and the corpus is backed up via
Chroma-first restic snapshots. But nothing yet proves that, *after activation*, every unit
mutation is captured durably and can be replayed deterministically. The eventual goal of
the broader ledger project is a durable, replayable ledger of corpus mutations that does
not depend on Chroma as the single source of truth.

**Shadow Ledger Phase 0 is the disabled-by-default first step.** It adds an opt-in
mutation **observer** on the authoritative `ChromaStore` that, only when an explicit
activation contract is satisfied, appends a non-authoritative versioned event to a shadow
JSONL file. The goal is to *prove the mechanics*: that covered post-activation
`knowledge_units` mutations can be captured durably, replayed into a disposable Chroma
root, and compared against authoritative Chroma — **without enabling production shadowing
or changing data authority.**

**Done means:** the Phase 0 mechanism works end-to-end *but is disabled*; a read-only
inventory/readiness report runs off it; and a separate, still-missing Ryan grant (plus a
still-missing activation runbook) can later enable it. PASS here **never** means the
historic corpus is rebuildable or that cutover is authorized.

---

## 2. System Design (how the pieces connect)

```
 Existing write callers ──► Authoritative write-store factory ──► ChromaStore ──► Chroma (Tier-1)
                                  │  (only sink injection boundary;        │
                                  │   injects sink only when eligible)      │
                                  │  explicit injection only                │
                                  ▼                                         │
                              UnitMutationSink ─── confirmed mutation ──────┘
                                  │
                          best-effort health sidecar
                                  │
                                  ▼
                          Shadow ledger writer
                          (flock, 0600, one append, file+dir fsync)
                                  │
                                  ▼
                          shadow_ledger.jsonl (non-authoritative)

 Activation baseline (read-only, evidence not bootstrap ledger)
   ──► compare against authoritative Chroma (touched-ID delta only)
        ▲ from activation manifest (sequence zero)      │
   Disposable delta projector (temp Chroma, sink forced OFF,              │
     stub/live embed modes) ──► temp root ──────────────┘
```

**Key constraints (invariants from architecture lock):**
- **Disabled by default**: absent `[shadow_ledger]` ≡ `enabled = false` → no sink.
- Sink attaches only when the store root equals the canonical configured root after
  `resolve()` and a complete activation manifest validates; env vars/path conventions alone
  cannot activate it.
- Shadowing observes only confirmed `knowledge_units` mutations; `conversation_summaries`
  is excluded; summary creation/deletion never emits a unit event.
- A shadow failure is visible but never rolls back or changes a successful Chroma result.
- Read/verify/eval/restore-drill/replay stores always receive `mutation_sink=None`.
- Raw embeddings never enter the ledger; unknown embed provenance is `UNVERIFIABLE`, never
  equality PASS.
- Chroma remains Tier-1; the shadow JSONL is non-authoritative and never a backup/restore
  source. Cutover/schema freeze are out of scope.

---

## 3. What Exists Right Now (file map)

### On `main` (merged, stable)

| File | What it does | State |
|------|-------------|-------|
| `shadow_ledger.py` | Durable append-only ledger writer; validate/read ops; health reporting | Complete |
| `shadow_sink.py` | `UnitMutationSink`; observes confirmed per-entity mutations across all five unit mutators | Complete |
| `shadow_validation.py` | Single shared `validate_shadow_activation` entry (C1); deterministic refusals | Complete |
| `shadow_config.py` | Disabled-by-default `[shadow_ledger]` config parsing; canonical root compare | Complete |
| `shadow_activation.py` | Activation/manifest/baseline (T1; merge-disabled C5 transaction in corrective layer) | Complete / merge-disabled |
| `shadow_authorization.py` | One-shot authorization-token validation (C5, corrective) | Complete / merge-disabled |
| `shadow_canary.py` | C6 scratch performance canary (measurement only, merge-disabled) | Complete / merge-disabled |
| `shadow_replay.py` | Disposable delta projector into marked temp root, sink forced off; two-level comparator | Complete |
| `shadow_inventory.py` | Read-only runtime inventory + readiness report CLI (`convmem shadow-inventory`) | Complete |
| `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md` | Locked Option B architecture + 11 decisions | Complete |
| `docs/plans/EXECUTION-shadow-ledger-phase0.md` | T1–T5 execution plan | Complete |
| `docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` | C5/C6/C7 activation transaction, canary, census corrective (planning only) | Plan only; **HOLD/NOT READY** |
| `docs/plans/PHASE0-SHADOW-CONTRACT.md` | Human-readable Phase 0 contract (envelope, config, strict validation API) | Complete |
| `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md` | Writer coverage inventory (C3 gate) | Complete |
| `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` | Machine-readable inventory | Complete |
| `docs/plans/VERIFY-shadow-ledger-phase0.md` | V0–V8 checklist | V0–V7 mechanical PASS; **V8 PASS** (DeepSeek + Kiro) |
| `tests/test_shadow_ledger_phase0_t1..t5.py` + support | Focused T1–T5 contract tests | Green (61 focused) |
| `tests/test_shadow_activation.py`, `test_shadow_canary.py`, `test_shadow_secure_append_c2.py`, `test_shadow_toml_render.py`, `test_shadow_truth_c4.py`, `test_shadow_validation.py`, `test_shadow_writer_gate_c3.py` | Corrective-layer / validation / gate tests | Present |

Implemented and merged to `main` via [#122](https://github.com/alanmz-crypto/convmem/pull/122)
as `4535107`. Mechanical VERIFY V0–V7 PASS; V8 independent sign-off PASS (DeepSeek V4-Pro +
Kiro cross-check). Ryan GATE for Execute = merge. **Ryan GATE for activation = still PENDING.**

### Does NOT Exist Yet

| What | Why not | Who can create it |
|------|---------|-------------------|
| Production activation manifest | Forbidden; requires separate Ryan grant | Ryan only |
| An activation runbook (executable operator steps) | The corrective plan *defines* C5 runbook steps but is planning-only, `HOLD / NOT READY`, and unapproved | Codex/Cursor after Ryan authorizes the corrective plan |
| Live config `enabled = true` on production | Same grant requirement | Ryan only |
| A current snapshot/re-measured activation-relevant observation period | Not started; an implementation authorization was never given | Ryan-gated |
| Activation readiness re-consult / draft runbook review | Suggested as a next step, not started | DeepSeek/Kiro on Ryan request |

---

## 4. Completion State

| # | Milestone | Status | Blocking on |
|---|-----------|--------|-------------|
| Architecture HITL | Locked by Ryan (Option B) | **DONE** | — |
| Gate 1b | Audit corrections PASS (#121) | **DONE** | — |
| Execution Plan | T1–T5 authored + revised | **DONE** | — |
| Execute (T1–T5) | Implemented + merged (#122 `4535107`) | **DONE on `main`** | — |
| Mechanical VERIFY V0–V7 | PASS (Cursor) | **DONE** | — |
| Independent VERIFY V8 | PASS (DeepSeek V4-Pro + Kiro) | **DONE** | — |
| Ryan GATE (Execute) | = merge | **DONE** | — |
| Production activation grant | **NOT DONE / HOLD** | Ryan explicit grant + runbook; neither exists |
| Activation runbook | **NOT DONE / NOT READY** | Authorize corrective plan; then write executable runbook |

**Current live state:** `shadow_ledger: disabled` (doctor PASS disabled). `embed_collection_identity`
WARN (legacy collection lacks `convmem:embed_model`) is related but non-blocking for a disabled
Phase 0. Restic freshness can FAIL independently and is unrelated.

**Summary: The implementation and verification are ~100% done and on `main`. The gap is not
code or verification — it is an activation decision (Ryan) plus an operator runbook, neither
of which exists.** The current activation verdict is **HOLD / NOT READY** per the corrective
plan.

---

## 5. Your Role (read this to know what you're here to do)

**This arc is waiting for Ryan's activation grant.** You are probably here either to write
the activation runbook or to answer Ryan's questions about readiness — not to implement
new code.

**If Ryan sent you here to write (or draft-review) the activation runbook:** Read
`docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` (C5 activation transaction,
one-shot authorization token, quiesce, commit, first-event verification) plus
`PHASE0-SHADOW-CONTRACT.md`. Produce a runbook an operator can follow — but do **not**
execute it, and do **not** edit `~/.config/convmem/config.toml` or create a production
activation manifest without Ryan's explicit activation grant. The corrective plan is
planning-only at `HOLD / NOT READY`.

**If Ryan sent you here to assess readiness:** Review `VERIFY-shadow-ledger-phase0.md`
(V0–V8), `SHADOW-WRITER-COVERAGE-INVENTORY.md`, and doctor state. Key questions: is the
sink truly default-off for read/non-production stores? Does the projector refuse the
production root before opening a writable client? Are unknown-provenance and delta-only
claims truthful? `shadow_ledger: disabled` + inventory `PARTIAL` is the honest current state.

**If Ryan sent you here to implement:** Do not implement production activation. If Ryan
authorizes the corrective plan, the bounded work is C5/C6/C7 (merge-disabled activation
transaction, scratch canary, writer census) — and it must remain disabled after it lands.

**If you don't know why you're here:** Ask Ryan. The most likely next action is reviewing
readiness or drafting the runbook — not enabling the sink.

---

## 6. What Remains Before "Live" (sequential)

- [ ] Ryan approves the activation corrective plan (currently `HOLD / NOT READY`)
- [ ] Implement/lock C5 activation transaction + one-shot authorization token, C6 scratch canary, C7 writer census (merge-disabled)
- [ ] Write and verify an executable activation **runbook** (runbook does not exist yet)
- [ ] Ryan supplies the exact root, config value, and one-shot authorization for activation
- [ ] Ryan issues the explicit **activation grant**
- [ ] Run activation per runbook; observe the first real event (sequence 1, hash-valid, equals Chroma post-state)
- [ ] Validate readiness report + observation period; Ryan accepts
- [ ] **[Stop]** Cutover, canonical schema freeze, authority transfer, and historic rebuild are explicitly out of Phase 0 scope

---

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|------|-----------|----------------|
| Production activation grant | Ryan | Enabling the sink / editing live config / creating a production activation manifest |
| Activation runbook | Not written | A safe, repeatable enable path — does not exist yet |
| Merge ≠ activation | Merge semantics | Merging further code never enables the sink on its own |
| One-shot authorization | Ryan (token) | C5 activation transaction refuses without a valid `0600` token |
| Disabled-by-default | Architecture decision 1 | Read/verify/eval/restore/replay stores must never receive a sink |
| Fail-closed corruption | Architecture decision 7 | No projection/checkpoint past the first invalid record |
| Post-Chroma crash gap | Failure model | Detected by comparison but never auto-heals; no undo of Chroma success |
| `embed_collection_identity` WARN | Legacy metadata | Non-blocking for disabled Phase 0; not a correctness blocker |

---

## 8. Relationship to ConvMem (the bigger picture)

Shadow Ledger Phase 0 is the first step toward a durable mutation ledger that could one day
reduce dependency on Chroma as the only authority:

```
ConvMem data-authority landscape:
├── Chroma knowledge_units — Tier-1 authoritative today (unchanged)
├── Shadow Ledger Phase 0 (THIS ARC) — disabled-by-default delta capture machinery
├── concurrency/durability edge — synchronous shadow fsync after Chroma success (sole accepted cost)
├── Corpus backup (Track 1 restic) — Chroma-first, unchanged by this arc (SEPARATE)
├── JudgeBench — offline semantic calibration (SEPARATE arc)
└── Future (post-cutover, NEW grants): canonical schema, bootstrap/migration, authority transfer,
     restore-order flip, live ledger-first restore
```

Phase 0 deliberately changes **nothing** about production behavior while disabled. It only
creates the machinery plus read-only evidence that the eventual ledger path could work —
leaving authority, backup, and cutover decisions entirely to later, separate Ryan grants.

---

## 9. Key Design Files (for deep dives)

| Purpose | Path | Read when |
|---------|------|-----------|
| Architecture (locked, 11 decisions) | `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md` | You need invariants, decision detail, or failure model |
| Execution plan (T1–T5) | `docs/plans/EXECUTION-shadow-ledger-phase0.md` | You need scope lock or task boundaries |
| Phase 0 contract | `docs/plans/PHASE0-SHADOW-CONTRACT.md` | You need the envelope, config shape, or strict validation API (C1) |
| Activation corrective plan (C5/C6/C7) | `docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` | You're writing the runbook or assessing activation readiness |
| Writer coverage inventory | `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md` | You need the C3 writer-gate routing list |
| VERIFY checklist | `docs/plans/VERIFY-shadow-ledger-phase0.md` | You're reviewing or closing V0–V8 |
| LATEST.md entry ("Shadow Ledger Phase 0 Execute MERGED") | `docs/inter-model/LATEST.md` | Current handoff context; activation still pending |

---

## 10. How to Update This Brief (departure protocol)

**When you finish working on this arc, update this file before handoff.** The goal is that
the *next* model reads this one document and has the same quality of mental landscape you
had — updated to reflect reality after your work.

**Rules — keep this a snapshot, not a log:**

1. **Overwrite, don't append.** Update section 3 (file map) and section 4 (completion
   state) to reflect current reality. When the corrective plan is approved, or the runbook
   is written, or activation is granted, move the milestone into "Done".
2. **Keep section 5 (Your Role) generic.** Rewrite the role guidance to reflect what the
   *next* model probably needs to do — not what you just did. While activation is pending,
   keep the "waiting for Ryan's grant" framing.
3. **Update section 6 (What Remains) by removing completed items.** The list should always
   show only what's still ahead, ending at "production shadowing enabled."
4. **Touch the diagram (section 2) only if the design changed.**
5. **One line in the Update Log.** Date, your name, what changed at the milestone level.
6. **Do not add session-specific context.** Session narrative belongs in Track A ingest.
7. **The test: could a model read *only* this file and know what to do?**

---

## Update Log

| Date | Who | Change |
|------|-----|--------|
| 2026-08-09 | Crush | Initial arc brief; code + VERIFY on `main` via #122, activation HOLD/NOT READY, runbook missing |
