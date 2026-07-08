# Role Sub-Job Mapping

Classification key:
- **(a)** Already mechanized in code — cite the file/function.
- **(b)** Belongs in a Layer 1 Role Charter card — judgment/context, retrieval-triggered.
- **(c)** Belongs in the Layer 2 Standing Checks register — state-dependent, needs a trigger doctor.py can evaluate.
- **(b) / standing hybrid** — primarily a charter review-habit (b), but kept as a
  register row with `trigger: charter` + `status: standing` so the Layer 1 ↔
  Layer 2 link stays auditable (the consistency probe requires standing rows to
  be cited). Excluded from the open backlog count and never doctor-due.

Process rule (2026-07-07 retro): every (a) claim carries a file/function
citation, or it is marked unverified **with a named owner** — never a bare
resting state; no pass concludes while one remains. A *live* unverified mark
uses the uppercase owner-tagged marker defined in the `unverified-resting-state`
register row, which the doctor probe of the same name greps for in this file and
`role-charters.md`. Lowercase "unverified" in historical narrative (e.g. the
Summary line below) is case-sensitively invisible to that probe by design.

Confirmed against: `doctor.py`, `eval_provenance.py`, `eval_judge.py`,
`crush-rules-ksweep-routing.example.md`, `generate-agent-protocol.sh` /
`generate-site-reference.sh`, `.cursor/rules/builder-reference.mdc`,
`restic_gate.py` / `convmem.py` (inline write gate).

---

## 1. Retrieval / ML Engineer

| Sub-job | Class | Notes |
|---|---|---|
| Recency-vs-relevance tuning as ongoing job | (c) — **live trigger (2026-07-07)** | Register row `recency-boost-retune` now carries a `corpus_size` trigger: baseline 5714 units recorded at promotion (via `collection_count`), nags when the count doubles. Caveat: baseline is from promotion date, not the original tune date (unknown), so the first nag is conservative. |
| Regression fixture curation (keep adding cases) | (b) | Judgment call on what counts as a new failure shape — charter responsibility, not a mechanical check. |
| Latency budget ownership (ask vs search_fast) | (c) — **live trigger (2026-07-07)** | Register row `latency-budget` now carries a 90-day cadence trigger; nags when the ask vs search_fast delta hasn't been re-measured. Threshold-drift detection is still manual — the trigger only enforces that a measurement happens. |

## 2. Data / Knowledge Engineer

| Sub-job | Class | Notes |
|---|---|---|
| Fact expiration policy ownership | (b) | Genuinely a judgment call ("what triggers invalidation") — charter card documents the policy once someone sets it; not mechanizable itself. |
| Adapter parity auditing | (c) — **live trigger (2026-07-07)** | Register row `adapter-parity-scan` now carries a 60-day cadence trigger: nags when 60d pass without a parity scan across all 5 surfaces. The "after any single-surface incident closes" half stays manual (no incident feed for doctor to read). |
| Per-unit provenance tracing before neutralize | (a) — **mechanized (2026-07-07)** | `preview_supersede_for_source` (`chroma_store.py`, read-only) + an unconditional `[neutralize]` echo in `ingest.py` before both supersede call sites: source file, active-unit count, timestamp range, and tombstone tag print before any tombstoning; the path/path_key variants merge into one echo per logical file. Register row `neutralize-provenance-confirm` closed. Residual: reading the echo is human judgment (charter). |

## 3. Platform / Backend Engineer

| Sub-job | Class | Notes |
|---|---|---|
| Verifying position, not presence (merge-order bug) | (a) | **Verified fixed in code, residual closed.** `verify-builder-reference.sh` asserts `CONVMEM-RITUAL.md` is `paths[0]` (FAILs on wrong order, lines 194/205–207); `deploy-builder-reference.sh` is the designated last writer enforcing ritual-first / CRUSH-last (lines 146–162). The between-deploys residual is now covered by the `merge-order-position` doctor probe (2026-07-07), which nags via `standing_register` whenever `paths[0]` is not the ritual. |
| Deploy-script interaction effects | (a) — **mechanized (2026-07-07)** | `tests/test_deploy_interaction.py`: sandbox `$HOME`, crush.json seeded scrambled, runs `deploy-builder-reference.sh` (the designated last writer), asserts ritual-first / CRUSH-last / no duplicates / idempotence on re-run. Register row `deploy-script-interaction` closed — the check runs continuously in the pytest suite instead of nagging. Variant note: the full `deploy-agent-protocol.sh` chain is not run (it regenerates repo artifacts); its crush stanza effect is reproduced in the seed. |
| Sunset-clause enforcement (ksweep rule) | (c) — **confirmed gap** | Lives only as an HTML comment in `crush-rules-ksweep-routing.example.md` (lines 24–27). Nothing reads or evaluates it. Poster-child register row. |

## 4. QA / Eval Engineer

| Sub-job | Class | Notes |
|---|---|---|
| Judge-model independence auditing | (a) | `eval_judge.py`: `judge_model != under_test_model` check; non-independent scores demoted to informational; `aggregate()` flags the whole batch. |
| Baseline provenance hygiene | (a) | `eval_provenance.py`: records model/digest/quant/ollama_version/fixture_hash; `classify()` separates `EXIT_REGRESSION` from `EXIT_NEEDS_REBASELINE`. |
| Negative controls as standard practice | (c) — **confirmed gap** | The discipline is encoded *inside* each eval that calls `judge()`/`model_context()`, but nothing checks that a *newly added* eval actually calls them. Register row. |

## 5. SRE / Reliability Engineer

| Sub-job | Class | Notes |
|---|---|---|
| Silent-degradation detection between runs | (a) | `doctor.py` `_check_synthesis_gate` / `_check_index_gate` — reads persistent JSONL logs, evaluates trigger, returns pass/fail/warn/skip via `DoctorCheck`. |
| Escalation-threshold maintenance | (c) — **live trigger (2026-07-07)** | Register row `escalation-threshold-retune` carries a corpus_size trigger (baseline 5708 x 2.0) as an event-volume **proxy** — the gate logs count failures only (no attempt denominator), so true volume is unmeasurable; retarget if attempt logging ships. Clusters intentionally with `recency-boost-retune` at corpus doubling. |
| Exposure-window tracking ("P0 done ≠ corpus clean") | (c) — **live trigger (2026-07-07)** | The flagship example the whole register exists for, now a live probe: due when a critical/high observation closes (pass-verification child in the ledger) after the row's `last_verified`. Bumping `last_verified` = "corpus-clean scan done" — the reset for this row. Vacuous until the first real P0 closes. |
| Pre-live-write snapshot gate (fail-closed) | (a) — **mechanized + boundary locked (2026-07-07)** | `restic_gate.ensure_chroma_snapshot_for_live_write()` is called inline before the two durable/overwrite Chroma paths — `add --upsert` (`convmem.py:355–358`) and `record --approve-last` (`convmem.py:919–924`) — and fail-closes on any Restic error (`restic_gate.py:13–33`). **Scope boundary (Option 1, adopted; Option 2 "gate every mutation" declined):** `convmem index` and plain `add` (no `--upsert`) are append-only + reindexable, so intentionally ungated; `CONVMEM_SKIP_RESTIC_GATE=1` is the deliberate test/lab hatch. Behavioral regression test `tests/test_write_gate_effect.py` forces the gate to fail and asserts each path aborts and leaves the corpus unchanged (effect, not reference — closes the position-vs-presence wiring hole). Boundary documented in ROADMAP + RECOVER and logged to the ledger. |
| Silent provider fallback (deepseek→local) | (a) — **mechanized (2026-07-08)** | Bug 5 (`dec_prop_20260707_182231_874d`): a configured `deepseek-v4*` model with no `DEEPSEEK_API_KEY` used to swap to a local Ollama model with zero signal, in three places. Now single-sourced through `llm._resolve_fallback_model()` — warns **once per process** to stderr (default: warn-and-continue), and fails closed via `CONVMEM_FAIL_ON_FALLBACK=1` (raises `ModelFallbackError`, never runs the local model). Wired into `llm.generate` / `generate_stream` / `summarize`; `distill.distill` and `scripts/eval-synthesis.py:_synth_model` delegate (the first draft's llm-only fix missed the distill hot path). Behavioral coverage in `tests/test_llm_fallback.py` (warn-once, no-warn-with-key, fail-closed does-not-call-local — effect, not presence). Env-var control mirrors the write gate; no new register row. |

## 6. Technical Writer / Documentation Lead

| Sub-job | Class | Notes |
|---|---|---|
| Vocabulary enforcement | (b) | Charter card + `.mdc` routing rule can state canonical terms; catching drift in prose is a review habit, not a mechanical check. |
| Closing the loop on deferred decisions | (b) / standing | Not doctor-evaluable ("was this discussed decision actually written down" has no pollable state). Charter review-habit — the Role 6 `read_when` hook fires when a decision discussion closes. Kept as register row `deferred-decision-closure` (`trigger: charter`, `status: standing`) for traceability, not counted open. Relabeled from `(c)`/`trigger: none` 2026-07-07 — an honest naming, not a reversal. |
| Cross-doc consistency on renumbering | split: (a) + (b)/standing | **(a)** for generated docs — `generate-agent-protocol.sh`/`generate-site-reference.sh` propagate from one SSoT automatically. **(b) / standing** for hand-written docs (ROADMAP, canon slices) — nothing re-greps these when a term or number changes, and no pollable condition exists; it is a charter review-habit fired by the Role 6 `read_when` hook on a rename/renumber. Kept as register row `cross-doc-consistency-handwritten` (`trigger: charter`, `status: standing`) for traceability. Relabeled from `(c)`/`trigger: none` 2026-07-07. |

## 7. Tech Lead / Engineering Manager

| Sub-job | Class | Notes |
|---|---|---|
| Refusing scope creep mid-experiment | none | Judgment call, in-the-moment. Doesn't belong in either layer. |
| Distinguishing "reclassified" from "dropped" | none | Same — this is exactly the P0.2/P0.3 near-miss. No mechanism substitutes for noticing it live. |
| Evidence-gate discipline (tier advances on scores, not calendar time) | none | Same. Worth a charter card for reference, but enforcement is inherently you. |

---

## Summary

- **Already mechanized (a):** all of Role 4 except negative-control wiring; Role 5's degradation detection; Role 6's generated-doc consistency; **merge-order position verification** — deploy-time (`verify-builder-reference.sh` order assertion + `deploy-builder-reference.sh` last-writer ordering) *and* between deploys (the `merge-order-position` doctor probe, 2026-07-07: ritual-first + CRUSH-last on Crush); **deploy-script interaction** (2026-07-07 — combined-effect test `tests/test_deploy_interaction.py`, register row closed); **Role 5 pre-live-write snapshot gate** (2026-07-07 — inline fail-closed `restic_gate` on `add --upsert` / `record --approve-last`, boundary locked to overwrite/durable paths, behavioral test `tests/test_write_gate_effect.py`); **Role 5 silent provider fallback** (2026-07-08 — Bug 5 closed: `deepseek→local` swap centralized in `llm._resolve_fallback_model`, warn-once + `CONVMEM_FAIL_ON_FALLBACK` fail-closed, `tests/test_llm_fallback.py`).
- **Confirmed real gaps → Layer 2 (c):** ksweep sunset clause, eval-provenance wiring for new evals, exposure-window tracking, adapter parity, escalation-threshold retuning, recency-boost retuning, latency budget. **Twelve open rows carry live triggers** (2026-07-07 triage + same-day retro): ksweep-sunset (manual 90d), eval-provenance-wiring / charter-register-consistency / merge-order-position / exposure-window-tracking (probes), adapter-parity-scan (cadence 60d), latency-budget (cadence 90d), recency-boost-retune (corpus_size, baseline 5714 x 2.0), escalation-threshold-retune (corpus_size, baseline 5708 x 2.0, event-volume proxy). Three further live triggers were added by the 2026-07-07 retrospective as **process checks** (not mapped gaps — they cover the design process itself): mechanized-claims-audit (cadence 90d — re-verifies the (a) claims in this file against current code), unverified-resting-state (probe — no live owner-tagged unverified marker left in this file or role-charters.md), retro-loop-closure (manual 90d — the previous retro's action items got audited). Seven of the twelve are promoted gaps from the list above (hand-written-doc consistency and deferred-decision-closure are **not** among the open twelve — they are now **(b)/standing** charter review-habits, `trigger: charter`, kept for traceability but excluded from the open count); merge-order-position is residual coverage of an already-mechanized item (see Role 3) and charter-register-consistency is the register's own self-check (never a gap); the three retro rows are process checks. Four rows sit outside the open backlog: two graduated via the tracked → mechanized → closed lifecycle (both 2026-07-07 — deploy-script interaction via combined-effect test, per-unit neutralize-provenance confirmation via unconditional pre-supersede echo), and two are `status: standing` charter-owned review-habits (`cross-doc-consistency-handwritten`, `deferred-decision-closure`) — manual-by-design, never doctor-due. **Register end state: 12 open / 2 standing / 2 closed (16 total).**
- **Layer 1 charter only (b):** fact expiration policy, regression fixture curation, vocabulary enforcement.
- **Neither layer, by design:** all of Role 7.
- **Previously unverified, now classified:** per-unit provenance tracing (Role 2) → confirmed gap `neutralize-provenance-confirm` (`chroma_store.py:261`), then mechanized and closed 2026-07-07 (pre-supersede provenance echo).
