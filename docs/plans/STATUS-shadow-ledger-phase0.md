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
| `shadow_activation.py` | C5 activation state machine, baseline, commit, first-event gate (#131) | Complete on `main`; **not live-run** |
| `shadow_authorization.py` | One-shot authorization-token validation (C5) | Complete on `main` |
| `shadow_canary.py` | C6 scratch performance canary — measurement only, never enables (#131 path) | Complete on `main`; **no PASS artifact** |
| `writer_census.py` | C7 payload-free writer-session census (#134) | Complete on `main`; **no valid report** |
| `shadow_replay.py` | Disposable delta projector into marked temp root, sink forced off; two-level comparator | Complete |
| `shadow_inventory.py` | Read-only runtime inventory + readiness report CLI (`convmem shadow-inventory`) | Complete |
| `convmem.py` | `shadow-inventory`, `shadow-activate`, `shadow-rollback`, `shadow-canary`, `writer-census-start`, `writer-census-report` | Complete; activate/canary/census require Ryan grants |
| `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md` | Locked Option B architecture + 11 decisions | Complete |
| `docs/plans/EXECUTION-shadow-ledger-phase0.md` | T1–T5 execution plan | Complete |
| `docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` | C5/C6/C7 activation transaction, canary, census corrective | Plan doc; **C1–C7 code merged** (#126, #131, #134); **live activation ops HOLD** until evidence + Ryan grant |
| `docs/inter-model/CODEX-2026-07-30-C7-OPERATIONAL-RUNBOOK.md` | C7 7-day census operator runbook | Runbook READY; **not armed** |
| `docs/inter-model/DEEPSEEK-2026-07-30-C6-PAYLOAD-FREE-EVENT-SIZE-EVIDENCE-HANDOFF.md` | C6 event-size evidence design gap | **Open** — blocks C6 canary |
| `docs/plans/SHADOW-WRITER-CENSUS.json` | Static writer/service census for activation quiesce | **Stale** — regenerate at deployed SHA before `shadow-activate` |
| `docs/plans/PHASE0-SHADOW-CONTRACT.md` | Human-readable Phase 0 contract (envelope, config, strict validation API) | Complete |
| `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md` | Writer coverage inventory (C3 gate) | Complete |
| `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` | Machine-readable inventory | Complete |
| `docs/plans/VERIFY-shadow-ledger-phase0.md` | V0–V8 checklist | V0–V7 mechanical PASS; **V8 PASS** (DeepSeek + Kiro) |
| `tests/test_shadow_ledger_phase0_t1..t5.py` + support | Focused T1–T5 contract tests | Green (61 focused) |
| `tests/test_shadow_activation.py`, `test_shadow_canary.py`, `test_shadow_secure_append_c2.py`, `test_shadow_toml_render.py`, `test_shadow_truth_c4.py`, `test_shadow_validation.py`, `test_shadow_writer_gate_c3.py` | Corrective-layer / validation / gate tests | Present |

Phase 0 Execute merged [#122](https://github.com/alanmz-crypto/convmem/pull/122) (`4535107`).
Corrective C1–C7 code merged [#126](https://github.com/alanmz-crypto/convmem/pull/126),
[#131](https://github.com/alanmz-crypto/convmem/pull/131), [#134](https://github.com/alanmz-crypto/convmem/pull/134).
Mechanical VERIFY V0–V7 PASS; V8 PASS (DeepSeek + Kiro). Ryan GATE for Execute = merge.
**Ryan GATE for activation = still PENDING.** Chroma R4 GREEN ([#161](https://github.com/alanmz-crypto/convmem/pull/161))
removes the rebuild blocker for arming C7 or capturing an activation baseline.

### Does NOT Exist Yet (operational / evidence)

| What | Why not | Who can create it |
|------|---------|-------------------|
| Production activation manifest | Forbidden until activation transaction succeeds | Created only by `shadow-activate` under grant |
| `docs/plans/ACTIVATION-shadow-ledger-phase0-runbook.md` | Executable operator doc not written | Codex/Cursor after Ryan authorizes |
| C7 `census-report.json` | Prior armed census removed 2026-08-06; no replacement | Ryan grant → `writer-census-start` → 7 UTC days → report |
| C6 event-size evidence artifact | Design handoff still open; no payload-free source locked | DeepSeek/Kiro design; optional small Execute slice |
| C6 canary PASS report | Requires C7 report + event-size evidence + Ryan C6 grant | Cursor under grant |
| Fresh live `SHADOW-WRITER-CENSUS.json` | On-disk file is static binding at old SHA | Regenerate at deployed SHA immediately before activation |
| Live config `enabled = true` | Requires successful `shadow-activate`, not hand-edits | Ryan grant + token |

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
| C1 strict validation | Merged disabled (#126) | **DONE on `main`** | — |
| C5 activation transaction code | Merged disabled (#131) | **DONE on `main`** | — |
| C7 writer census code | Merged (#134) | **DONE on `main`** | — |
| C7 operational evidence | 7-day census + report | **NOT DONE** | Prior census removed 2026-08-06; re-arm after Ryan grant |
| C6 event-size evidence | Payload-free design | **NOT DONE** | Open handoff; blocks canary |
| C6 canary PASS | Performance matrix | **NOT DONE** | Requires C7 report + C6 evidence + Ryan grant |
| Activation runbook | Executable operator doc | **NOT DONE** | Draft from corrective plan §10 |
| Production activation grant | Live `shadow-activate` | **NOT DONE / HOLD** | Ryan grant + token after activation-ready |

**Current live state:** `shadow_ledger: disabled` (doctor PASS). `convmem shadow-inventory` → **PARTIAL**
(expected while disabled). `embed_collection_identity` WARN (legacy missing `convmem:embed_model`)
is non-blocking for disabled Phase 0.

**Summary: Phase 0 + corrective **code** are on `main`. The gap is **activation-ready evidence**
(C7 census, C6 canary, fresh writer census, runbook) plus Ryan's explicit activation grant.
Merge ≠ activate. `shadow-activate` refuses without token, fresh census, quiescence, and backups.

---

## 5. Your Role (read this to know what you're here to do)

**This arc is waiting for activation-ready evidence and Ryan's activation grant.** You are
probably here to assess readiness, advance C6/C7 ops gates, or draft the runbook — not to
hand-enable config or implement new Phase 0 capture code.

**If Ryan sent you here to assess activation readiness:** Read this brief section 6, run
`convmem doctor` and `convmem shadow-inventory`, and compare against
`EXECUTION-shadow-phase0-activation-corrective.md` §10–12. Key gates: C7 7-day census report,
C6 event-size evidence, C6 canary PASS, fresh `SHADOW-WRITER-CENSUS.json` at deployed SHA.
`shadow_ledger: disabled` + inventory `PARTIAL` is honest pre-activation state.

**If Ryan sent you here to advance C7 (writer census):** Follow
`docs/inter-model/CODEX-2026-07-30-C7-OPERATIONAL-RUNBOOK.md`. Requires deployment proof,
no legacy writers, Ryan grant for `writer-census-start`, then **7 complete UTC days** frozen
revision. Does **not** authorize activation.

**If Ryan sent you here to advance C6 (canary):** Close the event-size evidence handoff first.
Then Ryan-grant `shadow-canary` with C7 report + evidence. Does **not** authorize activation.

**If Ryan sent you here to write the activation runbook:** Derive from corrective plan §10 and
`PHASE0-SHADOW-CONTRACT.md` §C5–C7. Do **not** execute `shadow-activate` without Ryan's
live-activation grant and one-shot token.

**If Ryan sent you here to implement:** Phase 0 + corrective code are merged. Only implement
if Ryan authorizes a **new** slice (e.g. C6 event-size evidence tooling). Never enable production
shadowing without the full activation-ready path.

**If you don't know why you're here:** Ask Ryan. Default: readiness assessment or runbook draft.

---

## 6. What Remains Before "Live" (sequential)

**Activation-ready** (evidence + runbook; still no live enable):

- [ ] Close C6 payload-free event-size evidence design ([handoff](../inter-model/DEEPSEEK-2026-07-30-C6-PAYLOAD-FREE-EVENT-SIZE-EVIDENCE-HANDOFF.md))
- [ ] Ryan grant → C7 `writer-census-start` → 7 complete UTC days → `writer-census-report` + independent SHA review
- [ ] Ryan grant → `shadow-canary` PASS (requires C7 report + event-size evidence)
- [ ] Regenerate `SHADOW-WRITER-CENSUS.json` at deployed SHA (live process/service scan)
- [ ] Write `docs/plans/ACTIVATION-shadow-ledger-phase0-runbook.md`
- [ ] Dense consult (DeepSeek + Kiro) on activation appetite; Ryan **readiness sign-off**

**Live activation** (separate maintenance window — only after activation-ready):

- [ ] Ryan **activation grant** + one-shot `0600` authorization token
- [ ] Re-check `convmem doctor` + complete-data-v2 backup (local + offsite)
- [ ] Stop writer services; verify quiescence + attestations
- [ ] `convmem shadow-activate --authorization-token …`
- [ ] First ledger event within 300s (or separate synthetic-event grant)
- [ ] Post-commit doctor + `shadow-inventory`; Ryan accepts observation period
- [ ] **[Stop]** Cutover, schema freeze, authority transfer, historic rebuild — out of Phase 0 scope

---

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|------|-----------|----------------|
| Production activation grant | Ryan | Enabling the sink / editing live config / creating a production activation manifest |
| Activation runbook | Not written | Executable operator steps for `shadow-activate` |
| C7 census report | Not on disk | C6 and activation preflight require valid 7-day report |
| C6 canary PASS | Never run | Performance evidence gate before activation |
| Stale writer census file | `SHADOW-WRITER-CENSUS.json` at old SHA | `shadow-activate` refuses with `census_stale` |
| Merge ≠ activation | Merge semantics | Merging code never enables the sink |
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
| Activation corrective plan (C5/C6/C7) | `docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` | Runbook source + readiness gates |
| C7 operational runbook | `docs/inter-model/CODEX-2026-07-30-C7-OPERATIONAL-RUNBOOK.md` | Arming/running writer census |
| C6 event-size handoff | `docs/inter-model/DEEPSEEK-2026-07-30-C6-PAYLOAD-FREE-EVENT-SIZE-EVIDENCE-HANDOFF.md` | Open blocker for canary |
| Cross-arc landscape | `docs/inter-model/STATUS.md` | Active vs closed arcs; next authorized actions |
| Arc brief (this file) | `docs/plans/STATUS-shadow-ledger-phase0.md` | Session-start orientation |
| Writer coverage inventory | `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.md` | C3 writer-gate routing list |
| VERIFY checklist | `docs/plans/VERIFY-shadow-ledger-phase0.md` | V0–V8 review |
| LATEST.md Shadow entry | `docs/inter-model/LATEST.md` | Historical soft-close context |

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
| 2026-08-09 | Cursor | Landscape hygiene: C1–C7 code on `main`; activation-ready ops gates (C7/C6 evidence, fresh census, runbook) |
