# Arc Brief — R2b Capture Authorization

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do]. The system currently: [what exists]. Missing: [what doesn't exist yet]."

---

## 1. What This Is For (product goal)

ConvMem answers questions by retrieving evidence from a local corpus. The corpus is
built by *capture* — turning exported/processed data plus a Chroma collection into a
package of `knowledge_units` and evaluation artifacts. Today that capture pipeline can
be run, but nothing proves a capture was **authorized**: which exact sources were
approved, under what fixed controls, and that the output is the immutable, complete
result of one approved run.

**R2b replaces this** with an honest, phase-scoped authorization boundary: by default a
real capture refuses to run unless it is bound to one explicitly approved
`authorization_phase: "r2b"` manifest. An approval authorizes **one exact capture**, not
a directory or a reusable retry loop. When complete, a capture is structurally complete
only when a last-atomic completion marker validates every required prior artifact and
the exact inventory.

**Done means:** Ryan ACCEPT AND GRANTs a filled, timestamp-valid R2b packet; a single
deterministic capture runs into an absent `capture_dir`; the completion marker proves the
exact approved sources/controls were used; and a post-capture VERIFY closes the arc.

---

## 2. System Design (how the pieces connect)

```
              ┌───────────────────────────────────────────────────────────┐
              │                    AUTHORIZATION CHAIN                    │
              │                                                           │
 Approved     │  manifest + sidecar ──► bind_r2b_capture ──► _R2bCapability│
 manifest     │        (AUTH_ROOT/<run_id>/capture.json      (opaque,     │
 (real/r2b)   │         + .approved.sha256)                   HMAC-sealed) │
              └──────────────────────┬────────────────────────────────────┘
                                     ▼
                    run_capture(..., r2b_capability=capability)
                                     │
                                     ▼
                 materialize_r2b_write_authorization
                 (recheck age/approval/bindings/source/symlinks/target)
                                     │
                                     ▼
                 first capture_dir creation/write  (EVAL_ROOT/<run_id>/capture)

 Trusted source snapshot (recomputed pre-capability, at materialization, post-extract):
   export sha256 + processed state + canonical Chroma collection/ID/doc/superseded digest

 Write order (last marker wins):
   materialize auth → capture_dir → export/processed copies → canonical Chroma extract
   → corpus_package.jsonl → overlap_validation.json → historical_spot_check.json
   → capture_report.json → final live-source drift check
   → corpus_package_manifest.json  (completion marker — LAST atomic write)
```

**Key constraints (invariants from architecture lock):**
- Approval authorizes one exact capture, not a directory or retry loop (invariant 1).
- The approved manifest and sidecar are the source of truth; capability/grant fields are
  never independent sources of authorization (invariant 3).
- Source identity is recomputed by trusted code before capability minting and at execution
  (invariant 4); stable Chroma IDs are insufficient.
- A capture is structurally complete only when the last atomic marker validates every
  required prior artifact and the exact inventory (invariant 5).
- Failure, drift, or interruption never produces a completion marker; partial directories
  are quarantined; retry requires a fresh directory and grant (invariant 6).
- The one-hour staleness rule applies at ACCEPT, binder execution, and materialization.

---

## 3. What Exists Right Now (file map)

### On `main` (merged, stable)

| File | What it does | State |
|------|-------------|-------|
| `eval_corpus/r2b_capture_auth.py` | R2b schema/precedence, safe `run_id`/path rules, `bind_r2b_capture`, `_R2bCapability`, materializer; plain binder refuses R2b | Complete |
| `eval_corpus/r2b_capture_run.py` | `run_capture(..., r2b_capability=capability)`; capability required before eval-root write; canonical Chroma helper; last expanded marker | Complete |
| `eval_corpus/capture.py` | Shared canonical Chroma source-identity helper; capture extraction | Complete |
| `scripts/eval_corpus_capture.py` | CLI; preserves/passes capability; fixed controls (`capture_id=run_id`, canonical overlap, spot `n=20`, one attempt); exact exit mapping | Complete |
| `tests/r2b_hermetic.py` | Hermetic tests, including failure classes | Complete |
| `tests/test_eval_r2b_auth_schema.py` | R2b schema and capability forgery/staleness tests | Complete |
| `tests/test_eval_r2b_capture_marker.py` | Marker order/inventory/hashes tests | Complete |
| `docs/plans/ARCHITECTURE-r2b-capture-auth.md` | Locked architecture (Option A, phase-scoped `r2b`) | Complete |
| `docs/plans/EXECUTION-2026-07-20-r2b-capture.md` | T1–T8 task/gate sequence | Complete |
| `docs/plans/VERIFY-r2b-capture.md` | V0–V6 filled against architecture; **NOT RUN** | Stub/filled, not executed |

Implementation was merged to `main` via [#67](https://github.com/alanmz-crypto/convmem/pull/67)
with tree proof at `c0f06f5`.

### Does NOT Exist Yet

| What | Why not | Who can create it |
|------|---------|-------------------|
| A current, timestamp-valid T4 packet draft | Old draft `~/.local/share/convmem/authorizations/r2b/2026-07-21-r2b-capture-01/` is **QUARANTINED/abandoned** (stale T4, no sidecar) | Cursor, after `restic_gate: PASS` + fresh trusted snapshot |
| Ryan packet **ACCEPT** | Requires a valid <=1h timezone-aware snapshot/digest | Ryan (T5) |
| Sidecar `capture.json.approved.sha256` + materialized manifest | Requires ACCEPT on the new packet | Ryan + operator (T5) |
| Ryan **ACCEPT AND GRANT** | A filled, approved packet is the only execution authority | Ryan only (T5) |
| One executed live capture into absent `capture_dir` | Requires the grant; never before it | Named operator (T6) |
| Mechanical VERIFY + Kiro sign-off + Ryan GATE | Requires the executed capture (T7) | Kiro + Ryan |

---

## 4. Completion State

| # | Milestone | Status | Blocking on |
|---|-----------|--------|-------------|
| T1 | Architecture docs replacement | **DONE on `main`** | — |
| T2 | Implementation (schema, snapshot, capability chain, marker, tests) | **DONE on `main`** (#67) | — |
| T3 | Copilot + Kiro same-tip review; Ryan merge + tree proof | **DONE** (merged as `c0f06f5`) | — |
| T4 | `restic_gate: PASS`, trusted fresh snapshot, filled packet draft | **BLOCKED** | Fresh snapshot + new draft packet; old draft quarantined |
| T5 | Ryan ACCEPT + materialize + **ACCEPT AND GRANT** | **NOT STARTED** | Ryan two-stage HITL on a current packet |
| T6 | Execute one capture into absent `capture_dir` | **NOT STARTED** | Requires T5 grant |
| T7 | Mechanical VERIFY + Kiro sign-off + Ryan GATE | **NOT STARTED** | Requires T6 |

**Summary: Code is on `main` and complete. The gap is not code. It is authorization —
a fresh T4 packet, Ryan ACCEPT, and **ACCEPT AND GRANT**.** No model can advance past
T5 without Ryan's explicit grant.

---

## 5. Your Role (read this to know what you're here to do)

**If Ryan sent you here to run T4 (the packet step):** Before editing anything, run
`convmem doctor` and confirm `restic_gate: PASS`. Produce a *fresh* trusted source
snapshot and a *new* draft packet under `AUTH_ROOT/<new_run_id>/` in the same operator
session. Do **not** reuse or repair `2026-07-21-r2b-capture-01/` — it is quarantined and
must not be **ACCEPT AND GRANT**-ed from. The old draft has no sidecar and its snapshot
is stale.

**If Ryan sent you here to review or verify:** Read the applied branch against the
architecture. Key questions: does the binder refuse R2b on the plain path? Does the
materializer re-derive every binding from the approved body? Does the marker validate the
exact inventory with no write after it? Is `capture_id=run_id`, spot `n=20`, one attempt?

**If Ryan sent you here for the grant/execution gate:** You are assisting Ryan. The
packet must be filled and timestamp-valid, ACCEPT within the one-hour bound, then
**ACCEPT AND GRANT**. Only then may one capture run. Do not let a verbal
`GRANT: yes` substitute for a filled, approved packet.

**If you don't know why you're here:** Ask Ryan. The most likely next action is producing
a fresh T4 packet and awaiting ACCEPT AND GRANT. The capture cannot be advanced by any
model without that grant.

---

## 6. What Remains Before "Live" (sequential)

- [ ] `convmem doctor` confirms `restic_gate: PASS` (absolute precondition)
- [ ] Produce fresh trusted source snapshot + new R2b packet draft (do **not** use quarantined `2026-07-21-r2b-capture-01/`)
- [ ] Ryan packet **ACCEPT** (snapshot timezone-aware, not future, <=1h; no source drift)
- [ ] Materialize manifest, sidecar, hashes, exact argv; Ryan **ACCEPT AND GRANT**
- [ ] Execute exactly one capture into absent `EVAL_ROOT/<run_id>/capture` (`--max-retries 1`)
- [ ] Mechanical VERIFY (V0–V5) then Kiro sign-off (V6)
- [ ] Ryan GATE closes the capture arc
- [ ] **[Stop]** B-Accept is explicitly out of scope — new architecture/grant required

---

## 7. Hard Stops (models cannot cross)

| Stop | Gate owner | What it blocks |
|------|-----------|----------------|
| T5 — Ryan ACCEPT + **ACCEPT AND GRANT** | Ryan | Any live capture; the gap is not code, it is authority |
| Restic precondition | `restic_gate: PASS` | Snapshot computation and eval-root capture write — no waiver |
| One-hour staleness | ACCEPT/binder/materialization | Every path where the approved timestamp must remain fresh |
| Quarantined draft `2026-07-21-r2b-capture-01/` | Operator protocol | **ACCEPT AND GRANT** from it — never reuse/repair; it has no sidecar |
| Marker authority | Architecture invariant 5 | Live capture never completes without the last atomic marker |
| Failure/quarantine semantics | Architecture invariant 6 | No same-directory retry; retry = new `run_id`, fresh packet, new grant |
| Cleanup | Separate prohibited operation | No reuse/resume/overwrite without separate authorization |

---

## 8. Relationship to ConvMem (the bigger picture)

R2b is one gate in ConvMem's capture → package → evaluate pipeline:

```
ConvMem capture/eval landscape:
├── R2b capture (THIS ARC) — authorize + run one content-bound capture
├── R2a config generation — earlier, now-superseded R2 family step (done)
├── corpus package / knowledge_units — output of the R2b capture write path
├── Chroma eval / embedding-model eval — downstream consumers of the captured corpus
├── JudgeBench — offline semantic calibration on retrieved evidence (SEPARATE arc)
└── Gate 2 / B-Accept / promotion — explicitly out of R2b scope (FUTURE, new grants)
```

R2b is upstream of corpus quality: until a capture is authorized and completed with a
valid marker, the packaged data feeding downstream eval has no proven provenance. But
R2b itself is narrowly scoped — it authorizes exactly one capture and stops before
B-Accept.

---

## 9. Key Design Files (for deep dives)

| Purpose | Path | Read when |
|---------|------|-----------|
| Architecture (locked, canonical) | `docs/plans/ARCHITECTURE-r2b-capture-auth.md` | You need invariants, schema, marker, or capability-chain detail |
| Execution plan (tasks/gates) | `docs/plans/EXECUTION-2026-07-20-r2b-capture.md` | You need T1–T8 sequencing or authority sequence |
| VERIFY checklist | `docs/plans/VERIFY-r2b-capture.md` | You're reviewing or closing V0–V6 |
| LATEST.md entry ("R2b capture: code on main") | `docs/inter-model/LATEST.md` | Current handoff context; draft packet quarantined |

---

## 10. How to Update This Brief (departure protocol)

**When you finish working on this arc, update this file before handoff.** The goal is that
the *next* model reads this one document and has the same quality of mental landscape you
had — updated to reflect reality after your work.

**Rules — keep this a snapshot, not a log:**

1. **Overwrite, don't append.** Update section 3 (file map) and section 4 (completion
   state) to reflect current reality. When a milestone lands (e.g. packet ACCEPT, grant,
   capture run), move it from "What Remains"/"NOT STARTED" to "Done".
2. **Keep section 5 (Your Role) generic.** Rewrite the role guidance to reflect what the
   *next* model probably needs to do — not what you just did.
3. **Update section 6 (What Remains) by removing completed items.** The list should always
   show only what's still ahead, ending at "live capture enabled."
4. **Touch the diagram (section 2) only if the design changed.**
5. **One line in the Update Log.** Date, your name, what changed at the milestone level.
6. **Do not add session-specific context.** Session narrative belongs in Track A ingest.
7. **The test: could a model read *only* this file and know what to do?**

---

## Update Log

| Date | Who | Change |
|------|-----|--------|
| 2026-08-09 | Crush | Initial arc brief; code on `main` via #67, draft packet QUARANTINED, T5 grant pending Ryan |
