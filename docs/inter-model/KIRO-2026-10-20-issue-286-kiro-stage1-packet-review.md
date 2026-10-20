# [Arc Codex #286] Kiro review — incremental Stage 1 packet (exact revision 0b00e6a)

**Author:** Kiro (design review / sign-off lane). **Date:** 2026-10-20 UTC.
**Reviewed artifact:** `docs/inter-model/ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md`
and `ASTRA-2026-10-20-issue-286-kiro-stage1-evidence.json` at commit
`0b00e6a9c05a7e457f7b2436f6e266ffef753693` on
`docs/2026-10-20-issue-286-kiro-stage1-packet`.
**Deployed baseline reviewed against:** `686d50e` (`origin/main` tip; the packet's
parent commit).
**Review branch (mine):** `review/2026-10-20-kiro-stage1-packet-review` from
`origin/main` in worktree `/tmp/convmem-kiro-review-stage1`. Review-only; no PR;
no code/config/runtime/guard/index/recovery action; `.worktrees/runtime-main`
and the live config untouched.

---

## Verdicts

| Scope | Verdict |
|---|---|
| **Packet accuracy / completeness** | **PASS with conditions** |
| **Stage 1 spending readiness** | **FAIL (NO-GO) — confirmed** |

The packet's own `NO-GO` is correct and I confirm it. Packet accuracy is PASS
with conditions because every technical and arithmetic claim I could check holds
against the call chain and on-disk state, but the global pending-transaction
census is now stale: a third pending transaction exists that the packet does not
enumerate (see C1). That does not change the spending verdict — it strengthens it.

---

## What I confirmed from the call chain and disk

### 1. Callback finding (CONFIRMED) — per-source bootstrap cap is shadowed

The packet's finding #1 is correct at the source level. The relevant call chain
at `686d50e`:

- `llm.provider_http_accounting` (`llm.py:65`) installs the permit / usage /
  finished callbacks with `ContextVar.set()` and restores them with the returned
  token on exit. It **replaces**, it does not compose or chain.
- `scripts/bootstrap-incremental-jsonl.py` (~line 545) wraps `coordinator.run()`
  in `provider_http_accounting(journal.consume_provider_http_attempt, ...)` — the
  **outer / bootstrap** installation (the per-source 18/12/12/24/18 journal cap).
- Inside the run, both transform call sites (`incremental_jsonl.py:2816` and
  `:3220`) go through `_build_frontier_with_accounting` (`:737`), which, when
  `kiro_admitted_live`, opens its **own** `provider_http_accounting(
  self._consume_cohort_paid_attempt, ...)` — the **inner / cohort** installation
  (`:753`).
- All paid summarize/distill work happens inside `_build_frontier` (`:1146`),
  i.e. inside the inner cohort context. Because the inner `.set()` replaces the
  permit ContextVar, every paid attempt during the frontier build reaches only
  the cohort callback; the bootstrap journal's `consume_provider_http_attempt`
  sees **zero**. On inner-context exit the bootstrap callback is restored, but
  the paid work has already completed under the cohort callback.

The packet's "outer=0, inner=1" in-memory probe is the correct real-world
behavior, and its decision to treat it as a static call-chain corroboration
(not an end-to-end test) is the right level of claim. The per-source bootstrap
hard limits therefore **cannot be treated as enforced on today's runtime**;
only the aggregate 120 cohort cap fires.

I separately confirmed the aggregate cohort cap **is** genuinely enforced
pre-dispatch: `CohortBudgetLedger.reserve_paid_http_attempt`
(`incremental_jsonl_cohort_budget.py`) takes an exclusive flock, re-reads the
ledger, and raises `ProviderAttemptBudgetExceeded` when
`consumed + reserved >= ceiling` **before** transport, counting failed attempts
against the cap (crash-conservative). So the packet's precise framing — cohort
cap holds, per-source cap does not — is accurate, as is its instruction not to
"fix" this by dropping the Kiro policy, resetting counters, or raising a cap.

### 2. Cohort selection and arithmetic (CONFIRMED)

- Ranking `priority = (2 × processed_chunks) × watch_spawns_24h × reach`
  reproduces exactly for every cohort row: 42, 28, 12, 8, 6. The top five by
  `burn_priority_proxy` in the evidence array are exactly K1–K5; the 6th/7th
  score 2, the remaining 21 score 0 — matching the packet text.
- Nominal = 2 × chunks: [6,4,4,8,6]; total chunks 14; total nominal **28**.
- Per-source proposed caps = 3 × nominal: [18,12,12,24,18]; total **84**.
- Ranking total **96**. Original Stage 1 (K1=6 + N1=2) = **8** nominal.
  Five + N1 = **30** nominal; proposed allocations 84 + 6(N1) = **90**, leaving
  **30** of the 120 cohort cap — all consistent with §3/§4.
- K2's `file_sha256` (`25871092…`) ≠ its `processed_key` (`7a11f5c9…`): confirmed
  unindexed drift; the packet correctly says to grant the current complete
  prefix, never the stale processed hash. K1/K3/K4/K5 `prefix_sha256 ==
  processed_key` at capture.
- All five show `state_exists/checkpoint_exists/transaction_exists = false`,
  consistent with "none had an incremental state directory at capture."

The selection and arithmetic hold.

### 3. Guard accounting in §5 (CONFIRMED sufficient as a specification)

Scratch files match the packet hashes exactly: `measure.py`
`ab52257a…`, `guard24.sh` `45854c34…`. Reading `measure.py`:

- `family()` returns `"kiro"` for `/.kiro/` paths — Kiro is recognized.
- `new_runs[family] += 1` fires for any finished, non-failed run whose stdout
  lacked the legacy `[index] … (N msgs, M chunks)` marker. Absence of a legacy
  marker is **not** proof of incremental admission.
- Paid estimate is `2 × done_chunks` where `done_chunks` is parsed from
  `chunks_indexed=` — coverage including reused chunks, not transform work
  (finding #2, confirmed).
- The ceiling is a 3,000-call estimate with Kiro still legacy; there is no
  exact-path / operation-id / ledger-based Kiro accounting.
- The coordinator's structured `incremental_codex_admitted_run` event
  (`incremental_jsonl.py:1444`) is Codex-only; there is no Kiro equivalent, so
  the packet is right to forbid requiring a nonexistent Kiro event or
  classifying by the shared `messages.jsonl` basename.

§5's required-behavior contract — select by exact canonical path + operation id
+ expected config + checkpoint/receipt outcome; enforce on absolute ledger
`consumed+reserved`; count completed/unchanged/refused/failed/in-progress
separately; treat missing/corrupt/decreasing ledger as STOP/UNKNOWN; never
double-count the selected Kiro component into the old `2×done_chunks` estimate;
keep the durable cap as pre-dispatch enforcement with no auto-extension — is a
sufficient and correct specification for a **separately authorized** guard
update. It does not claim the current guard is adequate; it documents every gap.
Sufficient.

### 4. Wedge correctly tied to Stage 1 (CONFIRMED)

On-disk state of source-state
`0d50863041f0fcd9…` matches the packet exactly:

- `transaction.json` SHA-256 `a0530661…`; `transaction_id`
  `46313d437ae4446282a752270770c614`; version **1**; phase **APPLYING**;
  `rollback_authority_sha256` `33ab1c3b…`; `complete_boundary` 6,079,972.
- `rollback.json` **absent**; `snapshots/46313d43…` **absent** (snapshots dir
  empty); two prepared JSON artifacts present.
- `retry_state.json` SHA-256 `101fc9ce…`-class content: `recovery_unproven`,
  `attempts_on_prefix=3`, `source_consecutive=2`.
- `checkpoint.json` version 1, `record_count` 13, `complete_boundary`
  1,995,036, SHA-256 `bab59aa6…`.

The recovery logic matches the packet: `_roll_forward` (`incremental_jsonl.py:
2672`) raises `recovery_unproven: "v1 transaction requires original runtime"`
for a v1 transaction under the v2 (`transform_v2`) coordinator, and separately
requires a present, bound rollback file for an APPLYING transaction — which is
absent here. `watch --clear-quarantine` clears only the retry/circuit hold, not
this. The source is a **Codex** rollout (`/.codex/sessions/…`); tying it to
Stage 1 because both adapters share Chroma collections, processed projection,
export, and dedupe surfaces under shared writer gates is a correct, conservative
cross-adapter hazard argument, not a scope error. **Wedge gate FAIL/UNRESOLVED
is correct.** The second excluded-Kiro transaction `18d83bf3…`
(`transform_failed`, v1) is also present and correctly held out of cohort.

### 5. Config observations (CONFIRMED)

Live config shows `enabled=true`, `live_sources=[]`, `allow_full_rebuild=true`,
`mutation_proof_observer="shadow"`, **no `kiro_session` table**, and a present
`codex_rollout_admission` (`admitted_after=2026-10-12T04:04:00Z`,
`root=/home/lauer/.codex/sessions`). This matches §2 exactly, including the
packet's correction that shadow is **already on** and must not be described as
off. The current config SHA-256 (`9d4be9e4…`) differs from the packet's captured
`config_sha256` (`f83aeec2…`); the packet already labels its captured digest
"pre-change … not a valid digest for a later bootstrap configuration," so the
difference is expected and the packet's refusal to bind a config digest into a
grant is the right call. The §4 two-phase bootstrap configuration requirement
(disabled-bootstrap entry with the Codex admission table temporarily omitted to
avoid `codex_admission_requires_enabled`, then restored post-bootstrap) is
consistent with the parser behavior and is a correct, non-obvious precondition.

---

## Conditions on the accuracy PASS

**C1 — Pending-transaction census is stale (completeness gap, not an error).**
At review time there are **three** pending transactions on disk, not two:

| txid | source-state | phase | ver | source | mtime (CDT) |
|---|---|---|---|---|---|
| `46313d43…` | `0d508630…` | APPLYING | 1 | Codex Oct 13 wedge | Oct 17 00:24 |
| `18d83bf3…` | `13c4c30c…` | transform_failed | 1 | excluded Kiro `sess_2628159e` | (held out) |
| `f844aba4…` | `f28bf974…` | **PREPARING** | **2** | **Codex Oct 16 rollout** | **Oct 19 23:04** |

The third (`f844aba4…`) is a **v2 PREPARING** Codex transaction whose
`transaction.json` mtime (2026-10-19 23:04:03 CDT) is ~53 minutes **after** the
packet's capture instant (2026-10-20T03:11:07Z). It uses `distill_model=
gpt-6-luna`, `distill_reasoning_effort=xhigh`, `complete_boundary≈203 MB`. It is
live Codex incremental activity contemporaneous with the packet. The packet's
"current two retained transactions" census was accurate **at its capture
instant**, and the packet explicitly states its watcher/writer observations are
"an inventory input, not proof that all other writers are fenced." So this is a
freshness/completeness gap, not a false claim. **It reinforces the NO-GO:** the
shared store has an active Codex writer producing new pending transactions right
now, so §7's no-other-writer window is demonstrably not satisfiable at present,
and the pre-execution global transaction census (§7 precondition #5) must be
re-run immediately before any grant and must dispose of all three (now) pending
transactions, not two. **Condition:** the refreshed packet must re-census pending
transactions at execution time and give an explicit disposition for every one
then present, including any v2 Codex PREPARING transaction.

**C2 — Rebind every digest at execution time.** The captured `config_sha256`,
and by extension any grant binding, is already stale (config changed to
`9d4be9e4…`). The packet says this; I am making it an explicit accuracy
condition: no digest in this packet (config, runtime SHA, backup snapshot ids
`18cb57f1…`/`79b21ce2…`) may be copied into a grant. All must be re-observed and
re-bound against the corrected runtime after the §1 code fix lands.

These conditions do not require packet edits to be *useful for review*; they are
binding instructions for the refreshed execution packet.

---

## Spending readiness (FAIL / NO-GO) — reasons, confirmed

Spending is not ready, independent of packet quality, for these reasons, all of
which the packet itself raises and I confirm:

1. **Per-source paid cap unenforced on the live runtime** (§1 / confirmation 1).
   Requires separate implementation authority, hermetic proof that *both* the
   per-source journal cap and the cohort cap veto before dispatch, and
   exact-tip review — none authorized by this packet.
2. **Oct 13 wedge is UNRESOLVED** with missing rollback authority and snapshot
   under a shared-store APPLYING transaction (§6 / confirmation 4). No safe
   irrelevance proof exists; `clear-quarantine` does not repair it.
3. **No no-other-writer window exists**, and C1 shows an active Codex writer is
   currently generating new pending transactions.
4. **Live cohort ledger is not materialized**; final source/N1 bindings, fresh
   verified backups, and the supplemental ledger mutation inventory remain
   open (§4 / §7).
5. **Guard accounting is a specification, not a deployed meter** (§5 /
   confirmation 3); an operational Kiro canary needs the separately authorized
   guard update first.

A review PASS on packet accuracy does **not** grant any spend, and must not be
read as one.

---

## Route forward

Kiro packet review (this document) → Ryan decisions on the §1 code correction,
original two-source (K1 + bound N1) vs five-source expansion scope, wedge
disposition, and the §5 guard update → separately authorized correction /
recovery work → refreshed exact packet re-binding all digests and re-censusing
pending transactions (C1/C2) → Ryan's explicit "go Stage 1". No PR requested; I
created none.

I finished: Kiro exact-revision review of the issue #286 Stage 1 packet.
Next step: Ryan decides the §1 fix, cohort scope, wedge disposition, and guard update.
Next lane: Ryan (grants), then Cursor (any authorized code correction) / Codex (refreshed packet).
See my work: `docs/inter-model/KIRO-2026-10-20-issue-286-kiro-stage1-packet-review.md` on `review/2026-10-20-kiro-stage1-packet-review`.

## TL;DR

- **Packet accuracy: PASS with conditions.** Every call-chain, arithmetic,
  wedge, guard, and config claim I checked holds exactly at `0b00e6a` against
  deployed `686d50e`. The callback-shadowing finding (per-source bootstrap cap
  bypassed by the cohort context; only the 120 cohort cap enforced) is confirmed
  from `llm.py` + `incremental_jsonl.py` + `bootstrap-incremental-jsonl.py`.
- **Condition C1:** the pending-transaction census is now stale — a **third**
  (v2 PREPARING Codex) transaction `f844aba4…` appeared ~53 min after capture;
  the refreshed packet must re-census and dispose of all pending transactions at
  execution time. **Condition C2:** rebind every digest at execution time.
- **Stage 1 spending readiness: FAIL / NO-GO, confirmed** — unenforced
  per-source cap, unresolved Oct 13 wedge, no writer window (active Codex writer
  observed), unmaterialized cohort ledger, and a guard that is spec-only.
- Review-only; new branch from `origin/main` in my own worktree; no PR;
  `.worktrees/runtime-main` and live config untouched.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Arc Codex | The Kiro/Codex JSONL incremental production-integration arc (issue #286); see `docs/plans/STATUS-codex-jsonl-production-integration.md`. |
| Stage 1 | First granted live Kiro incremental pilot (manual, watcher stopped); enrolls K1 plus a newly bound N1 by default. |
| Stage 2 | Later 24-hour watcher canary grant, separate from Stage 1. |
| K1–K5 | The five ranked existing Kiro session transcripts proposed as the Stage 1 priority cohort. |
| N1 | A dedicated new native Kiro session enrolled before its first index; its identity does not yet exist. |
| bootstrap | Adopting an already-indexed source into the incremental scheme via `scripts/bootstrap-incremental-jsonl.py`; incurs paid transforms. |
| nominal call | Planning unit = 2 × chunks transformed; an estimate, not a measured paid HTTP attempt. |
| cohort cap | Durable aggregate ceiling (proposed 120) on paid DeepSeek HTTP attempts across the whole operation, enforced by `CohortBudgetLedger`. |
| per-source cap | Proposed per-source bootstrap HTTP-attempt limit (18/12/12/24/18); confirmed NOT enforced on the live runtime. |
| provider_http_accounting | `llm.py` context manager that installs paid-attempt callbacks via ContextVar `.set()` (replaces, does not compose). |
| wedge | The Oct 13 Codex transaction `46313d43…` stuck in APPLYING with no rollback/snapshot authority. |
| APPLYING / PREPARING | Incremental transaction phases; APPLYING is mid-commit, PREPARING is pre-commit. |
| transform_v2 / v1 transaction | Semantic-v2 coordinator runtime; a v1 pending transaction must recover under its original runtime. |
| shadow (mutation_proof_observer) | Shadow mutation-observation mode, currently enabled in live config. |
| guard24.sh / measure.py | Scratch canary burn-measurement guard the packet §5 critiques; not a deployed Kiro meter. |
| reach | Ranking factor (1 if under configured watch root, non-excluded, with observed dispatch). |

<!-- src: ./ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md, ./ASTRA-2026-10-20-issue-286-kiro-stage1-evidence.json — reviewed artifact at 0b00e6a -->
<!-- src: ../../llm.py, ../../incremental_jsonl.py, ../../scripts/bootstrap-incremental-jsonl.py, ../../incremental_jsonl_cohort_budget.py — call chain confirmed at 686d50e -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief -->
