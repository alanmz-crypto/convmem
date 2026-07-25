# Cursor → Codex: Shadow Ledger Phase 0 Execution Planning (authorized)

**Who:** Ryan authorized Execution Planning; Cursor packages this handoff; Codex
authors the plan.
**What:** Paste-ready Codex work order to create
`docs/plans/EXECUTION-shadow-ledger-phase0.md` only.
**When:** 2026-07-24 — after Architecture HITL APPROVED on
[#115](https://github.com/alanmz-crypto/convmem/pull/115) and Gate 1b PASS
(audit fix [#121](https://github.com/alanmz-crypto/convmem/pull/121) → `main`
`0d08310`).
**Why:** Architecture stops before task decomposition; Planning OS assigns
Execution Planning to Codex.
**How:** Codex follows the verbatim work order below. Cursor does **not** author
the Execution plan. This grant does **not** authorize Execute, hooks,
activation, cutover, Neutral, backup wiring, or restore-order flip.

## Authority chain (do not reopen)

| Gate | State |
|---|---|
| Architecture Direction | **APPROVED** — `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md` on #115 |
| Gate 1b audit corrections | **PASS** (Ryan 2026-07-24) after #121 |
| Execution Planning authorship | **AUTHORIZED** (Ryan 2026-07-24) — this handoff |
| Execution plan HITL | **Pending** — Ryan after Codex emits the plan |
| Execute / activation / cutover | **Forbidden** |

## Exact paths

| Artifact | Path |
|---|---|
| Approved Architecture | [`docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`](../plans/ARCHITECTURE-shadow-ledger-phase0.md) |
| Architecture Codex work order (provenance) | [`CURSOR-2026-07-24-shadow-ledger-phase0-codex-handoff.md`](CURSOR-2026-07-24-shadow-ledger-phase0-codex-handoff.md) |
| Audit baseline (Gate 1b PASS) | [`docs/audit-ledger-first/`](../audit-ledger-first/) on `main` |
| Planning OS Execution guide | [`docs/planning/EXECUTION-PLANNING.md`](../planning/EXECUTION-PLANNING.md) |
| Required output | `docs/plans/EXECUTION-shadow-ledger-phase0.md` |
| Arc VERIFY companion (name; stub OK) | `docs/plans/VERIFY-shadow-ledger-phase0.md` |

## Exact ChatGPT/Codex Execution Planning work order — paste to Codex

````markdown
# Codex Work Order — Execution Planning: Shadow Ledger Phase 0

You are the **planning lane**, not the implementation lane.

Ryan has authorized **Execution Planning only** (2026-07-24). Architecture HITL
is APPROVED. Gate 1b is PASS. Do **not** enter Execute. Do **not** modify
runtime Python, hooks, Restic, restore doctrine, or audit baseline bodies unless
a docs-only stub for VERIFY is required by Planning OS.

## Follow Planning OS exactly

1. Read:
   * `AGENTS.md`
   * `docs/PLANNING-PROTOCOL.md`
   * `docs/planning/EXECUTION-PLANNING.md`  ← active phase guide
   * `docs/reasoning-modes.md` (Execution Planning characters)
   * `docs/MODEL-WORKFLOW.md`
   * `docs/builder-reference.md` (if infra unclear)
   * Approved Architecture: `docs/plans/ARCHITECTURE-shadow-ledger-phase0.md`
   * Audit pack (Gate 1b PASS): `docs/audit-ledger-first/` (on `main` / this tip)
   * Provenance (optional): `docs/inter-model/CURSOR-2026-07-24-shadow-ledger-phase0-codex-handoff.md`
2. Inspect repository reality:
   * current branch / tip SHA / dirty state
   * confirm Architecture file present and marked Architecture HITL approved + Gate 1b PASS
   * confirm `docs/audit-ledger-first/LEDGER-FIRST-READINESS-VERDICT.md` no longer claims
     “No production behavior change” for Phase 0
3. Begin **Execution Planning**. Emit Planning Status. Do not implement.

## Source authority (locked — do not reopen)

* Option B: opt-in `ChromaStore` mutation observer / sink.
* Chroma remains Tier-1; shadow is non-authoritative.
* Eleven Architecture decisions (activation, envelope, vocabulary, hash,
  duplicates, lock order, corruption, failure visibility, disposable replay,
  inventory, backup doctrine) are locked — translate into tasks/gates, do not
  re-decide.
* Shadow append failure is visible and must not roll back successful Chroma writes.
* Disposable replay never targets production Chroma.
* Phase 0 proves **post-activation delta** only — not historic corpus rebuild.
* Backup/restore: Chroma-first unchanged; no shadow-as-restore-source; shadow
  backup wiring needs separate Ryan auth (docs may name intent only).
* No Neutral / Office / cutover / schema freeze / governed-decision authority change.

## Required output

Create **only**:

`docs/plans/EXECUTION-shadow-ledger-phase0.md`

Follow `docs/planning/EXECUTION-PLANNING.md` artifact template (Planning Status,
tasks table, out of scope, evidence, VERIFY companion, Execute entry).

Name (stub OK from `docs/plans/VERIFY-TEMPLATE.md`):

`docs/plans/VERIFY-shadow-ledger-phase0.md`

Do **not** create runtime code, hooks, config defaults that enable shadow in
production, or migration tools.

## Bound the plan to these five deliverables (Architecture / work-order)

Map to **one to five** tasks (Planning OS max five). Prefer one task per
deliverable unless a hard dependency forces a split:

1. **Baseline documents and Phase-0 configuration contract**
   - Provisional envelope docs / `PHASE0-SHADOW-CONTRACT` (or equivalent named
     in Architecture) as docs-only artifacts listed in the plan.
   - Exact config shape: absent/disabled = no shadow; Ryan enables explicitly.
   - Inventory counts must be runtime-derived and snapshot-stamped (never hardcode 192).
2. **Shadow writer, mutation sink, and complete writer coverage**
   - Opt-in sink on production write-store factory only.
   - Coverage of Architecture writer inventory + callers of ChromaStore mutators;
     grep alone is not proof — plan the evidence commands.
3. **Durability, corruption, concurrency, and failure tests**
   - Lock order, flush/fsync, truncated-tail quarantine vs fail-closed middle
     corruption, post-Chroma/pre-shadow gap visibility.
4. **Disposable replay and final-state comparison**
   - Temp root isolation checks; no sink on temp store; stub vs live embed modes;
     comparison categories from Architecture.
5. **Inventory tools and Phase-0 readiness report**
   - Machine-readable report; no secret payloads by default; candidate classes
     only; no auto rewrite/ingest/delete/authority transfer.

## Non-blocking clarifications Codex must pin in the plan (not new Architecture)

* Phase 0 corruption behavior: Architecture corrections say fail-closed / stop
  checkpoint; some audit body text mentions quarantine-and-continue — **Execution
  plan must pick Architecture-aligned fail-closed for Phase 0** and name the test.
* Treat Architecture + Gate 1b corrections banners as authoritative over stale
  body claims in the audit pack.
* First verification command in Execute entry should include re-measure corpus
  inventory (runtime stamp) before any migration-flavored task (none of which
  are in Phase 0 Execute scope anyway).

## Out of scope for this Execution Plan (and for later Execute of it)

* Production read-path changes
* Authority cutover / restore-order flip
* Live migration / JSONL rewrite of production
* Neutral Core / Office Team
* Enabling shadow on production without a later Ryan activation grant
* Track 1 complete-data backup / Restic Hybrid audit (`492e6e7` / PR #120)
* Re-opening Architecture Option A/B/C

## Branch / landing hygiene

* Prefer a dedicated docs/plan branch (or continue on the Architecture branch
  only if Ryan directs). Do **not** hitchhike the backup/Neutral research-pack
  branch.
* Docs/plan commits only. No Python runtime changes in this phase.
* Push with explicit refspec. Do not merge. Do not push `main`.

## Stop condition

Emit the Execution Plan artifact (+ VERIFY stub if required).

Do not:
* modify Python runtime code
* add the shadow writer or hook Chroma
* enable production shadow
* alter backup or restore behavior
* write a ledger decision / `convmem record`
* self-transition to Execute

End with:

`Active phase lane must stop here. Await HITL.`
````

## Cursor stop

Handoff packaged. Cursor must not author `EXECUTION-shadow-ledger-phase0.md`
unless Ryan reassigns the planning lane. No Execute.
