# Role Charter Cards (Layer 1)

Shipped layout (decided 2026-07-07): this **single file** holds all seven role
cards as sections — no per-role split. Retrieval routing lives in
`.cursor/rules/role-charter.mdc` (tracked example:
`config/cursor-rules-role-charter.mdc.example`); Cursor-only for now, no
multi-surface deploy.

Each card's `register_refs` list is machine-checked: the
`charter-register-consistency` doctor probe flags dangling refs (a card citing
a nonexistent register id) and orphan tracked rows (an `open` or `standing`
register row no card cites; `closed` rows are exempt). Prose claims in the cards
are **not** probe-covered — keep them in sync by hand when rows are promoted,
relabeled, or closed.

---

## Template

```markdown
---
role: <name>
owns: <one-line scope>
read_when: <the situation that should retrieve this card>
register_refs: [<Layer 2 check IDs owned by this role>]
---

## Core Responsibilities
- ...

## Currently Mechanized
- <file/function> — <what it enforces>

## Currently Unmechanized / Charter-Only
- <sub-job> — <why it stays a judgment call, not a check>

## Layer 2 Cross-References
- <check-id> — see standing-checks-register.md
```

---

## 1. Retrieval / ML Engineer

```yaml
owns: embeddings, reranking, search_fast/ask split
read_when: "tuning retrieval quality, adding a new ranking signal, investigating a slow or stale-feeling answer"
register_refs: [recency-boost-retune, latency-budget]
```
- Mechanized: none identified (2026-07-07 audit).
- Charter-only: regression fixture curation — deciding what counts as a new failure shape is judgment, not a check.
- Register: `recency-boost-retune` (live corpus_size trigger, 2026-07-07 — nags when the unit count doubles from the 5714 baseline), `latency-budget` (live cadence trigger, 90d).

## 2. Data / Knowledge Engineer

```yaml
owns: ingest adapters, truth lifecycle, tombstoning
read_when: "adding an adapter, deciding whether a fact is stale, before any bulk neutralize/delete"
register_refs: [adapter-parity-scan, neutralize-provenance-confirm]
```
- Mechanized: `supersede_units_for_source` tombstones by `source_path` and keeps history (no hard delete), and since 2026-07-07 every supersede run prints an unconditional `[neutralize]` provenance echo first (`preview_supersede_for_source` + `ingest.py`): source file, active-unit count, timestamp range, tombstone tag. Reading the echo before letting a run proceed is the remaining human step.
- Charter-only: fact expiration policy — someone has to own the actual invalidation trigger definition.
- Register: `adapter-parity-scan` (live cadence trigger, 60d, 2026-07-07), `neutralize-provenance-confirm` (closed 2026-07-07 — mechanized as the unconditional pre-supersede provenance echo).

## 3. Platform / Backend Engineer

```yaml
owns: CLI, deploy pipeline, config, global_context_paths merge order
read_when: "touching deploy scripts, changing merge order, adding a stopgap rule with an expiry condition"
register_refs: [ksweep-sunset, deploy-script-interaction, merge-order-position, pr-steward-reminder]
```
- Mechanized: `merge-order-position` — `verify-builder-reference.sh` asserts ritual-first at deploy, `deploy-builder-reference.sh` is the designated last writer (ritual-first / CRUSH-last), and the `merge-order-position` doctor probe nags between deploys (2026-07-07). Probe scope: Crush `global_context_paths` only (ritual-first + CRUSH-last); other surfaces have no merge order to check.
- Charter-only: none pure; everything here converts to a register row once it has a concrete trigger.
- Register: `ksweep-sunset` (confirmed gap), `deploy-script-interaction` (closed 2026-07-07 — mechanized as `tests/test_deploy_interaction.py`, combined-effect order + idempotence in a sandbox `$HOME`), `merge-order-position` (live probe), `pr-steward-reminder` (manual 30-day prompt to consider PR Steward for bounded PR lifecycle tasks).

## 4. QA / Eval Engineer

```yaml
owns: eval harness, judge independence, baseline provenance
read_when: "adding a new eval, interpreting a regression, changing the judge model"
register_refs: [eval-provenance-wiring]
```
- Mechanized: judge independence (`eval_judge.py`), baseline provenance + regression/rebaseline split (`eval_provenance.py`).
- Charter-only: none — this role is the most code-covered.
- Register: `eval-provenance-wiring` — the one confirmed residual gap (new evals aren't checked for correct wiring).

## 5. SRE / Reliability Engineer

```yaml
owns: doctor.py checks, canaries, escalation policy
read_when: "closing a P0, adding a new canary, revisiting alert thresholds"
register_refs: [exposure-window-tracking, escalation-threshold-retune]
```
- Mechanized: silent-degradation detection (`_check_synthesis_gate`, `_check_index_gate`); pre-live-write snapshot gate — `restic_gate.ensure_chroma_snapshot_for_live_write()` (`restic_gate.py`) is called inline and fail-closed before the two durable/overwrite Chroma paths (`add --upsert`, `record --approve-last`; see ROADMAP "Pre-live-write gate"). Boundary is **Option 1** (overwrite/durable gated; `index` and non-`upsert` `add` intentionally ungated as append-only/reindexable; Option 2 "gate every mutation" declined). Behavioral test `tests/test_write_gate_effect.py` asserts the effect, not just the call's presence. Silent provider fallback (Bug 5, 2026-07-08) — a `deepseek-v4*` model with no `DEEPSEEK_API_KEY` no longer swaps to a local model silently: `llm._resolve_fallback_model()` is the one swap site (warns once per process; `CONVMEM_FAIL_ON_FALLBACK=1` raises `ModelFallbackError` instead), with `distill.distill` and `scripts/eval-synthesis.py` delegating; behavioral test `tests/test_llm_fallback.py`.
- Charter-only: none pure.
- Register: `exposure-window-tracking` (live probe, 2026-07-07 — fires when a critical/high observation closes after `last_verified`; bump = clean-scan done), `escalation-threshold-retune` (live corpus_size trigger, 2026-07-07 — corpus growth as an event-volume proxy). The write gate is `(a)` mechanized (no register row — a resolved decision, not tracked backlog); its boundary decision is logged to the ledger.

## 6. Technical Writer / Documentation Lead

```yaml
owns: canon slices, ROADMAP, terminology
read_when: "renaming or renumbering something, writing a new canon slice, closing a decision discussion"
register_refs: [cross-doc-consistency-handwritten, deferred-decision-closure, charter-register-consistency, mechanized-claims-audit, unverified-resting-state, retro-loop-closure]
```
- Mechanized: cross-doc consistency for *generated* docs (`generate-agent-protocol.sh` / `generate-site-reference.sh`); `charter-register-consistency` probe (`doctor.py`) asserts these charters and the register stay in sync; `unverified-resting-state` probe asserts no live uppercase owner-tagged unverified marker is left sitting in this file or `role-mapping.md`.
- Charter-only: vocabulary enforcement — a review habit more than a check. Prose-drift discipline (2026-07-07 retro): do **not** restate derived counts/lists a source of truth already holds — point at the source; where a restatement is genuinely useful, date-stamp it as a snapshot. The mechanical half is `charter-register-consistency`; the judgment half (which prose is safe to restate) stays here.
- Register: `cross-doc-consistency-handwritten` and `deferred-decision-closure` — both `trigger: charter` + `status: standing` (2026-07-07): charter-owned review-habits fired by this card's `read_when` hook (a rename/renumber, or closing a decision), **not** doctor-due and excluded from the open count; kept as register rows so this citation is audited by the consistency probe (which requires standing rows to stay cited). `charter-register-consistency` (probe — dangling/orphan detection between this file and the register), `mechanized-claims-audit` (live cadence trigger, 90d, added by the 2026-07-07 retro — re-verify mechanized claims against current code; template: `docs/engineering-team-retro-2026-07-07.md`), `unverified-resting-state` (live probe — no live uppercase owner-tagged unverified marker left in the design docs; the literal marker form is defined in the register row's notes and `docs/retro-template.md`, both out of the probe's scope), `retro-loop-closure` (live manual trigger, 90d — the previous retro's action items got audited; remediation runs step 0 of `docs/retro-template.md`).

## 7. Tech Lead / Engineering Manager

```yaml
owns: sequencing, tier gating, charter/policy, go/no-go calls
read_when: "n/a for retrieval — this role isn't delegated to an agent"
register_refs: []
```
- Mechanized: none, and shouldn't be.
- Charter-only: all three sub-jobs (scope creep refusal, reclassify-vs-drop, evidence-gate discipline) — kept here for reference only, not as something an agent checks or enforces. Evidence-gate discipline includes the **citation gate** (2026-07-07 retro, leak 1): a claim of the form "X is mechanized/handled" is not written as confident prose until a file/function citation backs it — absent a citation it is marked unverified with a named owner (the uppercase marker the `unverified-resting-state` probe greps for), never stated as fact. This is the judgment half; its mechanical backstop is `mechanized-claims-audit` (Role 6) re-verifying citations against current code.
- Register: none. This is the one role that stays entirely with you.
