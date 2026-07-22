# Standing Checks Register (Layer 2)

Generalizes the pattern already in `doctor.py`'s `_check_synthesis_gate` /
`_check_index_gate`: read persistent state, evaluate a trigger condition,
return a status. `DoctorCheck`'s four-value status (pass/fail/skip/warn) gives a
register check room to "nag" (warn) without hard-failing.

**End state (2026-07-07, design complete):** the two-layer engineering-team
design closed out at 16 rows — **12 open** rows, all with live triggers
(2 manual, 5 probes, 3 cadence, 2 corpus_size); **2 charter-standing** rows
(`cross-doc-consistency-handwritten`, `deferred-decision-closure`, both Tech
Writer / Role 6) — charter-owned review habits kept in the register for
traceability but excluded from the open backlog and never doctor-due; and
**2 mechanized-and-closed** rows (`deploy-script-interaction`,
`neutralize-provenance-confirm`). Every machine-evaluable row was promoted; the
two that resist a doctor-evaluable condition were relabeled `trigger: charter` /
`status: standing` (an honest naming of their by-design-manual nature, not a new
mechanism — see "Standing (charter-owned) rows" below). The exposure-window
severity recording path (`convmem add --severity`) shipped and was verified end
to end the same day. The same-day retrospective
([engineering-team-retro-2026-07-07.md](engineering-team-retro-2026-07-07.md))
root-caused the process leaks, re-verified every mechanized claim against
current code, and — applying the register's own discipline to the process —
converted its findings back into the ledger rather than filing them as a
standalone lesson doc: `mechanized-claims-audit` (recurring claim sweep),
`unverified-resting-state` (probe), and `retro-loop-closure` (the next retro
audits this one), plus charter rules on Roles 6 and 7. This paragraph is a dated
snapshot — the JSON is the source of truth for current state.

## Source of truth

Rows live in **[`standing-checks-register.json`](standing-checks-register.json)**
(same directory), read by `_check_standing_register()` in `doctor.py`. This
markdown file is narrative only — it deliberately does **not** duplicate the row
table, because an unsynced second copy is exactly the
`cross-doc-consistency-handwritten` failure mode this register exists to catch.

To see current rows and their live status: open the JSON, or run
`convmem doctor` — the `standing_register` check reports how many open checks are
due.

## Trigger types

- `manual` — due when `max_age_days` elapses since `last_verified`; bump
  `last_verified` in the JSON when the check is re-verified.
- `cadence` — due every `interval_days` since `last_verified`.
- `corpus_size` — due when the Chroma knowledge-unit count exceeds
  `baseline * multiple`.
- `probe` — a mechanical assertion evaluated in code; may list `exempt` paths
  with a stated `reason`.
- `charter` — the real trigger is a Role 6 charter `read_when` retrieval hook
  (a human evaluates it in-situ, e.g. "when renaming something" or "when closing
  a decision"), not a doctor-polled condition. Paired with `status: standing`;
  **never** doctor-due, and excluded from the open-count. This is the honest
  home for jobs that are genuinely manual-by-design rather than
  awaiting-a-trigger.
- `none` — historical: "tracked, no evaluable trigger yet". No open row uses it
  anymore (the two that did were relabeled `charter`); retained only as a
  documented status a closed/legacy row may carry. Never counted as due.

## Live triggers

- `ksweep-sunset` (**closed** 2026-07-22) — P1.3 source-trust (#78) landed;
  live Crush `ksweep-routing.md` retired; deploy no longer copies the example.
  Example file retained as a RETIRED stub only.
- `eval-provenance-wiring` (probe) — scans `scripts/eval-*.py` for
  `model_context(` / `judge(`; `scripts/eval-retrieval.py` is exempt
  (deterministic retrieval metrics, no LLM output under test — verified:
  `eval-summaries.py` and `eval-synthesis.py` are wired, `eval-retrieval.py` is
  not, by design).
- `charter-register-consistency` (probe) — parses `register_refs:[...]` blocks
  from `docs/role-charters.md` and flags dangling refs (charter cites a
  nonexistent register id) or orphan rows (an open register row no charter
  cites). This is the register checking itself against the Layer 1 charters.
  **Known limitation:** it checks the refs lists only — prose claims in these
  docs can still drift (proved 2026-07-07: a probe promotion updated a table
  row but left a stale Summary bullet; caught by human retrospective, not by
  the probe). Renames/reclassifications still require the manual grep pass.
- `merge-order-position` (probe, promoted from `trigger: none` 2026-07-07) —
  asserts `CONVMEM-RITUAL.md` is `paths[0]` and `CRUSH.md` (when present) is
  last in crush.json `global_context_paths` on every doctor pass. Closes the
  residual below: the deploy-time verify ran non-fatally and nothing nagged
  between deploys. Scope: Crush surface only. Remediation when due:
  `bash scripts/deploy-builder-reference.sh`. First evaluation (2026-07-07)
  caught a live violation left by the pre-fix deploy script (which inserted
  digests at the front); remediated same day.
- `adapter-parity-scan` (cadence, 60d — promoted from `trigger: none`
  2026-07-07) — nags when 60 days pass without a stale-fact scan across all 5
  surfaces equally (Cursor was the heaviest contributor, 16/49, last scan;
  attention drifts to the surface that last broke). Remediation: run the parity
  scan, then bump `last_verified`. The "after any single-surface incident
  closes" half of the intended trigger stays manual — doctor has no incident
  feed to read.
- `latency-budget` (cadence, 90d — promoted 2026-07-07) — nags when 90 days
  pass without re-measuring the ask vs search_fast latency delta (the +8s
  finding was a one-time measurement). Remediation: re-measure, then bump
  `last_verified`.
- `recency-boost-retune` (corpus_size — promoted 2026-07-07) — nags when the
  Chroma `knowledge_units` count exceeds `baseline * multiple` (5714 x 2.0).
  Baseline recorded at promotion via the same `collection_count()` call the
  trigger uses — not at the original tune date, whose count is unknown, so the
  first nag is conservative. Remediation: re-run the recency eval, re-tune
  weight/half-life, re-record the baseline. Bumping `last_verified` does
  **not** reset this trigger — only re-recording the baseline does.
- `escalation-threshold-retune` (corpus_size — promoted 2026-07-07, baseline
  5708 x 2.0) — corpus growth as a **proxy** for event volume: the gate logs
  (`synthesis_failures.jsonl`, `index_failures.jsonl`) record failures only,
  with no attempt denominator, so true volume is unmeasurable today; retarget
  this trigger if attempt logging ever ships. Intentionally clusters with
  `recency-boost-retune` — both fire at corpus doubling because both re-tune
  values calibrated at the old corpus size. Remediation: review the `>=3/week`
  thresholds on both gates against current activity, adjust, re-record the
  baseline (bumping `last_verified` does not reset it).
- `mechanized-claims-audit` (cadence, 90d — added by the 2026-07-07
  retrospective) — nags when 90 days pass without re-verifying every
  (a)-classified claim and closed-row mechanization against current code.
  Everything marked mechanized was true when someone checked; code moves, and
  without this the ledger silently becomes fiction (the ksweep-comment failure
  mode). Remediation: run the sweep using the citation table in
  [engineering-team-retro-2026-07-07.md](engineering-team-retro-2026-07-07.md)
  as the template, fix drifted claims, then bump `last_verified`.
- `unverified-resting-state` (probe — added by the 2026-07-07 retro) —
  mechanizes the rule that UNVERIFIED is a todo-with-an-owner, not a fifth
  resting category. Case-sensitive whole-word `UNVERIFIED` grep over exactly two
  files, `docs/role-mapping.md` and `docs/role-charters.md`. Convention: a live
  mark is written uppercase, owner-tagged; historical lowercase prose ("was
  unverified") is invisible. Scope deliberately excludes this file, the retro
  artifact (has an "UNVERIFIED sweep" heading), and the retro template (instructs
  in uppercase) — any of those in scope would false-fire on day one. Remediation:
  assign an owner to each flagged marker and resolve it to a real bucket.
- `retro-loop-closure` (manual, 90d — added by the 2026-07-07 retro) — closes
  the loop on retros themselves: due when 90 days pass without auditing the
  previous retro's action items (a retro whose items are never re-checked is as
  dead as the ksweep comment). Aligned with `mechanized-claims-audit` so both
  nag at the same quarterly checkpoint. Remediation: run step 0 of
  [retro-template.md](retro-template.md) against the latest
  `engineering-team-retro-*.md`, then bump `last_verified` (bump only after the
  audit actually ran — the dual-use hazard below).
- `exposure-window-tracking` (probe — promoted 2026-07-07) — the flagship
  "P0 done != corpus clean" row, now live: the close-event feed was already in
  the ledger. Due when any **critical/high** observation has a closed status
  (per `evidence_boost`, the same machinery as `convmem unresolved`) whose
  close date is after this row's `last_verified`. Close date comes from
  pass-verification children, **not** `last_touched` — a note attached to a
  closed P0 later must not re-fire the row. Severity gate: medium/info closes
  never fire it; open P0s are `unresolved`'s business, not this probe's.
  Remediation: run the corpus-clean scan (adapter parity / stale-unit sweep),
  then bump `last_verified` — for this row the bump **is** the reset (the
  opposite of the corpus_size rows), because it records "scan done after that
  close". Currently vacuous: zero critical/high observations exist, so it
  cannot fire until the first real P0 closes. **Feed requirement** (runtime
  survey 2026-07-07: 21 of 26 live observations carry no severity field,
  which defaults to medium): a P0 only enters the feed if recorded with
  `severity: critical|high` — record P0 observations with explicit severity
  or this probe stays blind to them. `convmem add --severity critical|high`
  (single-record path, shipped 2026-07-07) makes this possible without a
  JSONL file; batch `--file` records carry a `severity` field directly.

**`last_verified` dual-use hazard:** for `manual` and `cadence` rows, the
trigger reads the same `last_verified` field humans bump when editing rows.
Bumping it during a doc-sync pass without actually performing the check
silently resets the nag. Bump `last_verified` **only after actually running
the check** the row describes.

## Standing (charter-owned) rows

Two rows — `cross-doc-consistency-handwritten` and `deferred-decision-closure`
(both Tech Writer / Role 6) — are `trigger: charter` + `status: standing`. They
are review habits, **by design** not doctor-evaluable: "did the prose stay
consistent after a rename" and "was the discussed decision actually written
down" have no state a script can poll. Their real trigger is the Role 6 charter
`read_when` hook — a human evaluates them at the moment of the triggering edit,
not on a doctor cadence.

They stay in the register (not dropped) so the Layer 1 charter ↔ Layer 2
register link is traceable and audited: the `charter-register-consistency` probe
requires **standing** rows to remain cited from `role-charters.md`, so a dropped
citation is still caught. But `status: standing` keeps them **out of the open
backlog count** (`doctor` reports "12 open, 0 due (2 charter-standing)") and
`_standing_row_due` never marks a `charter` row due. This resolves the earlier
ambiguous `trigger: none` state — an honest relabel, not a reversal of the
"stands as manual" verdict.

## Corrected rows (2026-07-07 verification pass)

- `merge-order-position` — largely mechanized after all:
  `verify-builder-reference.sh` asserts `CONVMEM-RITUAL.md` is `paths[0]`
  (lines 194 / 205–207) and `deploy-builder-reference.sh` is the designated last
  writer enforcing ritual-first / CRUSH-last order (lines 146–162). The former
  residual (verify ran non-fatally at deploy end only) is now **closed** by the
  `merge-order-position` doctor probe above (2026-07-07).
- `deploy-script-interaction` — the two deploy scripts are coordinated by design
  (`deploy-agent-protocol.sh` prepends the ritual then calls
  `deploy-builder-reference.sh` last, lines 443–447). Now **closed** — see
  "Closed rows" below.
- `neutralize-provenance-confirm` — new row (was "unverified"); originally
  `supersede_units_for_source` neutralized by `source_path` with no dry-run and
  no provenance echo. Now **closed** — see "Closed rows" below.

## Closed rows

A row closes when its check gets mechanized somewhere that runs continuously —
at that point a register nag is redundant. Closed rows stay in the JSON
(`status: closed`) so their history and charter references remain valid; the
consistency probe requires *open* and *standing* rows to be cited (closed rows
are exempt).

- `deploy-script-interaction` (closed 2026-07-07) — first row to complete the
  full lifecycle: tracked (`trigger: none`) → mechanized → closed. The
  combined-effect test `tests/test_deploy_interaction.py` seeds a sandbox
  `$HOME` crush.json in scrambled order, runs `deploy-builder-reference.sh`
  (the designated last writer), and asserts ritual-first / CRUSH-last / no
  duplicates plus idempotence on a second run — the exact regression class
  behind the 2026-07-07 merge-order incident. The full
  `deploy-agent-protocol.sh` chain is not run in-test (it regenerates repo
  artifacts); its crush stanza effect is reproduced in the seed.
- `neutralize-provenance-confirm` (closed 2026-07-07) — every supersede run now
  prints an unconditional `[neutralize]` provenance echo before tombstoning:
  source file, active-unit count, timestamp range, and tombstone tag
  (`preview_supersede_for_source` in `chroma_store.py`, wired into both
  supersede call sites in `ingest.py`; the path/path_key variants merge into
  one echo per logical file). A neutralize run cannot execute silently.
  Residual: reading the echo is Role 2 charter judgment. Kept to one line
  (plus a verbose sample) because `--supersede` runs at every handoff sync.

## Explicitly excluded

Role 7 (Tech Lead) sub-jobs — scope creep, reclassify-vs-drop, evidence-gate
discipline — do not belong here. They're judgment calls with no trigger
condition a script could evaluate.
