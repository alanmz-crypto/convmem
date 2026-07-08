# Engineering-Team Design — Retrospective (2026-07-07)

Owner: Tech Lead (Ryan). Next review: the `mechanized-claims-audit` register row
(cadence 90d) re-runs section 2's sweep; everything else here is a one-time
closing record.

Scope: the two-layer engineering-team design shipped 2026-07-07 (role charters +
standing checks register). This retro covers the **process**, not the artifacts —
where the working method itself leaked, whether the ledger still matches code,
whether every UNVERIFIED got resolved, and whether the explicit non-goals still
hold.

---

## 1. Process leaks — root causes and countermeasures

### Leak 1: confident classification before code review

`merge-order-position` was classified and described in prose **before** anyone
read `verify-builder-reference.sh` or `deploy-builder-reference.sh`. Code review
then forced a reclassification (it was largely mechanized already; the real gap
was a narrow between-deploys residual).

- **Root cause:** the initial mapping pass had no gate requiring a file:line
  citation before a claim earned confident prose. Nothing structurally
  distinguished "I checked this" from "this sounds right." Missing verification
  step, not pace — the check took five minutes once someone did it.
- **Countermeasure (in effect):** the classification key in
  `docs/role-mapping.md` requires "cite the file/function" for every (a); a
  claim without a citation must be marked unverified instead. The
  `mechanized-claims-audit` register row (added by this retro) re-verifies all
  citations on a 90-day cadence so a claim can't stay confidently wrong for
  long even if the gate is skipped once.

### Leak 2: UNVERIFIED as a resting place

Per-unit provenance tracing sat marked "unverified" in the mapping table for a
full working turn before anyone circled back (it then turned out to be a real
gap — no dry-run, no provenance echo — and got mechanized).

- **Root cause:** UNVERIFIED was written as a table cell, not a todo. It had no
  owner and no deadline, so the conversation's forward pace carried past it.
  Both factors, but the fixable one is structural: a state with no owner
  doesn't get revisited.
- **Countermeasure (rule, recorded here and in the mapping doc):** UNVERIFIED
  is a todo, not a fifth category. Any new UNVERIFIED entry must name who
  checks it, and a pass does not conclude while one remains. The closure
  checklist includes `grep -i unverified` over the role docs.

### Additional leaks found (transcript scan, same class)

Both are instances of one shared root cause — **derived state duplicated into
prose drifts silently**:

- A probe promotion updated the role-mapping table row but left the Summary
  bullet stale; caught by human retrospective, not by any probe (recorded as a
  known limitation in `standing-checks-register.md`).
- `ROADMAP.md` originally enumerated the live trigger list; it went stale
  within the same day and was fixed by de-enumerating — it now points at the
  register JSON instead of copying from it.

**Countermeasure:** don't restate counts/lists that a source of truth already
holds; point at the source. Where a restatement is genuinely useful (the
register narrative's end-state paragraph), date-stamp it as a snapshot.

### What worked

Worth recording so it isn't accidental next time: the "check for bugs" /
debug-with-runtime-evidence passes caught real defects before ship (the
`endswith("CRUSH.md")` suffix-match bug, the consistency probe flagging its own
documentation prose, template placeholders parsed as refs). Adversarial passes
after each increment were the single most effective step in the process.

---

## 2. Ledger-vs-reality sweep (full, 2026-07-07)

Every (a)-classified claim and both closed-row mechanizations re-verified
against **current** code today (after all of today's edits to `doctor.py`,
`ingest.py`, `chroma_store.py`, `convmem.py`). This table is the template for
future `mechanized-claims-audit` runs.

| Claim | Where verified | Result |
|---|---|---|
| Ritual-first asserted at deploy | `scripts/verify-builder-reference.sh:194` (`paths[0].endswith("CONVMEM-RITUAL.md")`), FAIL path `:206` | holds |
| Deploy script is designated last writer, ritual-first / CRUSH-last | `scripts/deploy-builder-reference.sh:146-165` (canonical order comment + `ordered = head + middle + digests + tail`) | holds |
| Combined-effect deploy test (closed row `deploy-script-interaction`) | `tests/test_deploy_interaction.py:86-116` — order, no-dup, middle-preserved, idempotence asserts | holds |
| Pre-supersede provenance echo (closed row `neutralize-provenance-confirm`) | `chroma_store.py:280` `preview_supersede_for_source`; `ingest.py:233` `_echo_neutralize_preview`, wired at both call sites `ingest.py:358-360` and `:393-394` before `supersede_units_for_source` (`chroma_store.py:306`) | holds |
| Judge independence, structural | `eval_judge.py` — `judge()` `:138`, `aggregate()` `:194`, independence = `judge_model != under_test_model` (module contract lines 10-12) | holds |
| Baseline provenance + regression/rebaseline split | `eval_provenance.py` — `model_context()` `:66`, `classify()` `:94`, `EXIT_REGRESSION`/`EXIT_NEEDS_REBASELINE` `:19-20`, `ollama_version()` `:29`, `fixture_hash()` `:59` | holds |
| Silent-degradation gates | `doctor.py:431` `_check_synthesis_gate`, `:547` `_check_index_gate`, reading `synthesis_failures.jsonl` / `index_failures.jsonl` (`:436`, `:552`) | holds |
| Generated-doc consistency from SSoT | `scripts/generate-agent-protocol.sh:17` (`SSoT="config/agent-protocol.md"`); `scripts/generate-site-reference.sh` present | holds |
| The four register probes exist and dispatch | `doctor.py` — `_eval_provenance_probe` `:587`, `_charter_register_consistency_probe` `:618`, `_merge_order_probe` `:657`, `_exposure_window_probe` `:704`, dispatched via `_standing_row_due` `:788` / `_check_standing_register` `:835` | holds |

**Drift found: none.** All mechanized claims match current code as of this
sweep. This seeds the new register row's `last_verified: 2026-07-07`
legitimately (the bump follows an actually-run check, per the register's
dual-use hazard rule).

---

## 3. UNVERIFIED sweep — conclusion

Exactly **one** item was ever formally marked unverified: per-unit provenance
tracing (Role 2). It resolved fully: unverified → confirmed gap
(`neutralize-provenance-confirm`) → mechanized (pre-supersede echo) → closed.
No item quietly stayed UNVERIFIED.

Grep over the design docs today finds two remaining "unverified" strings, both
historical narrative ("was unverified") describing the resolved item — zero
live resting states.

Note the two leaks are opposite failures of the same discipline:
`merge-order-position` should have been marked unverified and wasn't (confident
prose without a citation); per-unit provenance was marked correctly but the
mark had no owner. The rule covering both: **every claim is either cited or
UNVERIFIED-with-an-owner, and neither state survives the end of a pass.**

---

## 4. Explicit non-goals — re-checked

| Exclusion | Decided because | Conditions changed? | Verdict |
|---|---|---|---|
| Role 7's three sub-jobs (scope-creep refusal, reclassify-vs-drop, evidence-gate discipline) out of both layers | judgment calls with no trigger condition a script could evaluate | No — nothing shipped today produces an event feed for these decisions | **Stands** |
| `scripts/eval-retrieval.py` exempt from the provenance probe | deterministic retrieval metrics, no LLM output under test | Re-verified today: zero `judge(`/`model_context(` calls; imports only argparse/json/`query_units` | **Stands** |
| `cross-doc-consistency-handwritten` stays `trigger: none` | "did the prose stay consistent" has no evaluable condition | No — and section 1's prose-drift leaks are direct evidence the manual prompt is still earning its place | **Stands** |
| `deferred-decision-closure` stays `trigger: none` | "was the discussed decision written down" has no evaluable condition | No | **Stands** |
| Adapter-parity's incident-close trigger half stays manual | no incident feed for doctor to read | Nuance: `attempts.jsonl` exists (written by `cross_project_digest.py`, per-observation remediation outcomes) — but it records digest remediation attempts, not surface incidents | **Stands** — revisit if `attempts.jsonl` scope ever broadens to incident closes |
| Latency-budget's threshold-drift detection stays manual | only the re-measure cadence is machine-checkable | No | **Stands** |
| Escalation-threshold trigger stays a corpus-growth proxy | gate logs record failures only, no attempt denominator | Re-verified: `doctor.py:436`/`:552` still read failure-only logs; `attempts.jsonl` is not a gate-attempt denominator | **Stands** — retarget if gate-attempt logging ever ships |

No exclusion needed reversal; one gained a documented revisit condition
(`attempts.jsonl` scope).

---

## 5. Register change made by this retro

Added `mechanized-claims-audit` (Role 6 / Technical Writer, cadence 90d,
`last_verified: 2026-07-07` seeded by section 2's sweep) to
`docs/standing-checks-register.json`, cited in Role 6's `register_refs`. End
state after this retro: **14 rows — 12 open (10 with live triggers: 1 manual,
4 probes, 3 cadence, 2 corpus_size; 2 manual-by-design), 2 closed.**

### Addendum (2026-07-07, later same day): findings fed back into the ledger

The retro above initially left most of its own countermeasures as prose — which
is the very failure mode it documents. Applying the register's discipline to the
process, each finding was converted to a real bucket. This table is the target
for the next retro's step-0 audit.

| Finding | Destination | Bucket |
|---|---|---|
| Leak 1 — citation gate (claims cited before written as fact) | Role 7 charter card, evidence-gate line (judgment); backstop `mechanized-claims-audit` (code) | CHARTERED + REGISTERED |
| Leak 2 — UNVERIFIED is a todo-with-an-owner, not a resting state | `unverified-resting-state` probe (`doctor.py`) + register row | MECHANIZED |
| Prose-drift — don't restate derived state; date-stamp snapshots | Role 6 charter card, Charter-only (judgment half; mechanical half is `charter-register-consistency`) | CHARTERED |
| "What worked" — adversarial debug pass per increment | `docs/retro-template.md` standing agenda | PRACTICE (template) |
| Retro-loop closure — the next retro audits this one | `retro-loop-closure` register row (manual 90d) + template step 0 | REGISTERED |

Post-addendum end state: **16 rows — 14 open (12 with live triggers: 2 manual,
5 probes, 3 cadence, 2 corpus_size; 2 manual-by-design), 2 closed.** The three
new rows (`mechanized-claims-audit`, `unverified-resting-state`,
`retro-loop-closure`) are process checks, not mapped gaps. Verified: `convmem
doctor` reports 14 open / 0 due, the `charter-register-consistency` and
`unverified-resting-state` probes pass, and `tests/test_doctor.py` is green.

### Completion addendum (2026-07-07, design close)

Two loose ends from the state above were closed to reach design completion. The
snapshots above are left intact as dated history; this addendum records the
deltas.

**(A) The two manual-by-design rows relabeled — a naming fix, not a reversal.**
The section-4 verdict ([L127–128](#)) that `cross-doc-consistency-handwritten`
and `deferred-decision-closure` **Stand** is unchanged: both are still
manual-by-design and still earn their place. What changed is only their *label* —
`trigger: none` / `status: open` was ambiguous (it inflated the open backlog
with rows that can never fire and can never close). They are now
`trigger: charter` / `status: standing`: the real trigger is this role's Role 6
charter `read_when` hook (in-situ human evaluation), so they are never doctor-due
and are excluded from the open count, while remaining cited so the
`charter-register-consistency` probe still audits the link (the probe now covers
`open` **and** `standing` rows). Register end state moves from **14 open / 0
standing / 2 closed** to **12 open / 2 standing / 2 closed** (still 16 total). No
row was dropped; no verdict reversed.

**(B) Write-gate boundary made explicit + behaviorally tested.** The
pre-live-write Restic gate was already inline and fail-closed on the two durable
paths (`add --upsert` at `convmem.py:355–358`, `record --approve-last` at
`:919–924`; gate `restic_gate.py:13–33`), but its *scope boundary* was never
written down: `convmem index` and non-`upsert` `add` appear nowhere in the
2026-06-30 gate-close log — neither gated nor declared out-of-scope. Resolved as
**Option 1** (overwrite/durable paths gated; append/index intentionally ungated
because they are reindexable; Option 2 "gate every mutation" explicitly
declined), documented in ROADMAP + RECOVER, and cited in Role 5. The wiring hole
(a tested gate function with untested call sites — the same position-vs-presence
shape as the day-one merge-order bug) is closed by `tests/test_write_gate_effect.py`,
a behavioral test that forces the gate to fail and asserts each path aborts and
leaves the corpus unchanged. The boundary decision itself is queued as a
`convmem record` block for Ryan (Role 6 "closing the loop on deferred decisions"
applied to this very decision — docs describe it, the ledger locks it).

Verified at close: `convmem doctor` reports **12 open / 0 due (2
charter-standing)**, the `charter-register-consistency` / `unverified-resting-state`
/ `restic_gate` checks pass, and `pytest` + `ruff` are green including the new
behavioral write-gate test.
