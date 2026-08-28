# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-08-27 (R2b v2 writer-gate normative plan prepared; live capture remains unauthorized)

- **[Arc Recovery Authority] T2 LANDED (2026-08-23):** Who/What: T2 (authority recovery and projection agreement state machine) implemented, independently verified (exact-tip BugBot clean + Kiro PASS), and squash-merged via PR #236. When: reviewed tip `c91a218015caadb82ce6294358777234d90754e5`; landing SHA `62f0f2355543f1daefa237bfc0811f94d8982989` on `main`. Why: complete the second executable Recovery Authority task (projection agreement). How: T2 landed; recovered authority, projection validity, and serving readiness remain separate — T2 is non-serving. **Next: scratch-only bulk recovery (V4j, plan task T3) is next but NOT AUTHORIZED.** T4 remains unstarted/unauthorized; D1/V4k remains BLOCKED pending CG-2 Design A ratification; no live recovery, migration, activation, serving, or CG-2 authority is open. Evidence: [`STATUS-recovery-authority.md`](../plans/STATUS-recovery-authority.md) · [`ARCHITECTURE-recovery-authority.md`](../plans/ARCHITECTURE-recovery-authority.md) · [`EXECUTION-recovery-authority.md`](../plans/EXECUTION-recovery-authority.md).

- **[Arc Recovery Authority] T1 LANDED (2026-08-23, superseded by T2 landing):** Who/What: T1 (complete-data-v3 profile and registry validation substrate) implemented, independently Kiro-verified (PASS, off-GitHub), and squash-merged via PR #234. When: architecture locked `22852a07e66920874045e0e85c4572ab6c0b29b8`; Execution Plan accepted `b0c1dd226fa4e1f7cee5c74ae99a13191d7742ab`; landing squash SHA `cac3cc35b8a74d43f9d353554cb7c80cb2f13801` on `main`. Why: complete the first executable Recovery Authority task (v3 substrate/registry validation). How: T1 landed; the complete-data-v3 substrate and registry validation now exist on non-live surfaces. **Superseded:** T2 has since landed via PR #236; the next authorized task is T3 (V4j), which remains NOT AUTHORIZED. Evidence: [`STATUS-recovery-authority.md`](../plans/STATUS-recovery-authority.md) · [`ARCHITECTURE-recovery-authority.md`](../plans/ARCHITECTURE-recovery-authority.md) · [`EXECUTION-recovery-authority.md`](../plans/EXECUTION-recovery-authority.md).

- **[Arc Recovery Authority] Execution Plan consented + T1 executed (2026-08-22, superseded by T1 landing):** Who/What: Codex converted the locked Recovery Authority direction into four bounded serial Cursor tasks plus one genuinely **BLOCKED** V4k task. When: after Ryan locked architecture bytes `22852a07e66920874045e0e85c4572ab6c0b29b8` on branch `plan/2026-08-22-recovery-authority` (carrier tip `a133629f96cc34c4df2fda2730b5bcb272d743da`); execution-planning content commit is `8add9a7586adf5bd2da2d8cc1ceba91323c61ff9`. Why: V4g–V4j and V4l need separate executable boundaries and evidence, while V4k must wait for CG-2 Design A ratification and stable generation/pointer semantics. **Superseded:** the plan was Kiro-reviewed (PASS) and accepted, and T1 landed via PR #234; T2 onward remain NOT AUTHORIZED. Evidence: [`EXECUTION-recovery-authority.md`](../plans/EXECUTION-recovery-authority.md) · [`VERIFY-recovery-authority.md`](../plans/VERIFY-recovery-authority.md) · [`CODEX-2026-08-22-recovery-authority-execution-planning-handoff.md`](CODEX-2026-08-22-recovery-authority-execution-planning-handoff.md).

- **Arc Recovery Authority — architecture package LOCKED (2026-08-22):** Who/What: Codex authored the new V4g–V4l Recovery Authority direction and evidence/reconciliation handoff from exact `origin/main` `c1fac4c2c40662d9d1f88a1a020835feecce682b`. When: architecture bytes `22852a07e66920874045e0e85c4572ab6c0b29b8` were locked on branch `plan/2026-08-22-recovery-authority`; carrier tip `a133629f96cc34c4df2fda2730b5bcb272d743da` binds the package. Why: deferred complete-data recovery, provenance-registry integration, selected-generation rollback continuity, and recovery-side crash closure needed one bounded direction before separate execution gates. How: choose new `complete-data-v3` provenance-complete recovery profile, immutable registry-generation authority, exact snapshot/tree/projection bindings, explicit pending/blocked states, and bounded CG-1/CG-2 interface. **V4k execution remains BLOCKED pending CG-2 Design A ratification; dedicated DeepSeek R1 direct/API critique was not authorized; Copilot audit was skipped because no allow-listed unresolved code-grounded question remained.** No implementation, restore, activation, migration, T3 reopening, or T5 campaign. Next: Kiro Execution Plan review → Ryan. Evidence: [`ARCHITECTURE-recovery-authority.md`](../plans/ARCHITECTURE-recovery-authority.md) · [`CODEX-2026-08-22-recovery-authority-architecture-handoff.md`](CODEX-2026-08-22-recovery-authority-architecture-handoff.md).

- **[Arc CG-2] Design A first-cutover rollback-bootstrap architecture LOCKED + papered (2026-08-21, AUTHORIZED docs — not yet merged):** Who/What: HITL #2 papering of Ryan-locked Design A onto restored architecture text from `e680ce837653698a5be8b78ba02db2f880c40c63`, base `origin/main` `cd9554e4c3006f7e0695d5d17a69696cc913c566`. When: branch `docs/2026-08-21-cg2-design-a-arch-lock`. Why: close the first-canary `previous_generation_id=None` gap with convert-v1 `G_rb` + exact pre-grant `G_canary`. How: amend ARCHITECTURE §§6.2–6.3, §7.0, §10.1, §11, A6, §13; RUNBOOK pre-GATE order / rollback≠recovery / pause conditions; VERIFY papers V8c **definition only** (still PENDING — not PASS). HITL #3 correction bound: exact `G_canary` before grant; one-shot self-invalidating grant. **No implementation / no activation.** Next: Design A **execution plan** (Ryan/Codex lane). Evidence: [`ARCHITECTURE-cg2-production-activation.md`](../plans/ARCHITECTURE-cg2-production-activation.md) · [`RUNBOOK-cg2-production-activation.md`](../plans/RUNBOOK-cg2-production-activation.md) · [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md).

- **Arc Trapdoor Hunt — T3 CLOSED; PR #221 squash-merged (2026-08-21):** Who/What: PR #221 integrated the frozen T3 result plus bounded writer-boundary and provenance-supersession corrections with current-main Runway Ledger/CI/protocol changes. When: squash-merged at `722141d31e586151f361ef7006ad74c71cdff534` from final reviewed head `bfe79f728cde60ec5e8f7021c87dcebf23ee1eca`. Why: complete the main integration without reopening T3 or changing Runway semantics. How: current-main integration is complete; Bootstrap, migration/backfill, CG-2 activation, Shadow/R2b, GC, T4, and T5 remain separately governed and unauthorized. [`STATUS-dependability-provenance.md`](../plans/STATUS-dependability-provenance.md)
- **[Arc CG-2] V8a independent sign-off PASS (2026-08-21, Kiro):** Who/What: Independent review of CG-2 implementation tip `2f427fcfb8818dd665310bae7e8cd5ffa066bdcc` with preservation check on `main` `451f523b48c9fd998a050edfe6766d14249dcc6b` (CG-2 surfaces unchanged). When: papered 2026-08-21. Why: close V8a. How: focused CG-2 **43/43 PASS**; CG-2 + generation-core **76/76 PASS**; query/doctor/rerank **84/84 PASS**; full suite timed out at 180s (**not** claimed PASS/FAIL); no material defects. Non-blocking V8c/canary note: `FrozenGenerationStable` and `RetryBudgetTerminates` share one test; structural immutability supplements coverage. **V8a PASS.** **V8b PASS** (grant only). Soak completion **ACCEPTED**. **V8c PENDING** — next governed step is first-owner **packet preparation** only; **not** authorized. Evidence: [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md).

- **[Arc CG-2] legacy-only gateway soak COMPLETED + Ryan-accepted (2026-08-21):** Who/What: Soak-completion closeout for CG-2 authority migration after #186. When: Ryan accepted 2026-08-21. Why: close the unresolved soak-completion question without granting owner/activation/GC. How: continuous watch PID **955623** since **2026-08-18 02:12:54 CDT** (`NRestarts=0`); `owners=0`; `logical_projection` PASS; fresh reconciliation; no demonstrated RUNBOOK pause; six midnight `RESET_REQUIRED` samples adjudicated non-blocking; final `eval-retrieval.py` at **2026-08-21T08:17Z** — 8/8 PASS, P@1 87.5%, P@k 100%, MRR 0.9375, Recall@k 100%, **no regression vs baseline**, exit 0. **V8b** remains **PASS** (soak **grant** only). Soak completion **ACCEPTED**. First generational owner / activation / activation manifest / GC / Shadow / R2b **not** authorized. Evidence: [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md) soak-completion section · [`RUNBOOK-cg2-production-activation.md`](../plans/RUNBOOK-cg2-production-activation.md).
- **Arc Runway Ledger — CLOSED (merged #215/#216, 2026-08-20):** Who/What: Deterministic agent run identity tracking — append-only JSONL event ledger correlating client sessions to work (Kiro first capture client). When: core merged via PR #215; hook-enable soak passed + PR #216 merged 2026-08-20. Why: native session IDs were lost after agents finish; this provides a unified correlation layer. How: `agent_run_ledger.py`, Kiro SessionStart/Stop hooks, additive forward-only ingest association (unique-match-only), CLI query surface. **State:** Runway Ledger is **CLOSED** — no remaining Runway execution. Other clients (Codex, Cursor, Crush, Copilot) are optional future slices, not unfinished Runway work. [`STATUS-agent-run-ledger.md`](../plans/STATUS-agent-run-ledger.md)

**Live counts:** run `convmem brief` — do not trust stale numbers here.

- **CodeQL Complex Therapy — CLOSED/PASS (2026-08-17, `plan/2026-08-16-codeql-complex-therapy`):** Who/What: `Protect Main` `19156572` now requires Pylint, Pytest, `Analyze (actions)`, `Analyze (python)`, and `CodeQL` with integration IDs `15368`, `15368`, `15368`, `15368`, and `57789`. When: Grant A positive control passed on PR #198; B1 attempt #2 proved 1-red/4-green blocking on PR #200; B2 proved producer binding on PR #201; Kiro PASSed exact implementation SHA `d3d0bdd9986c7f77e60f956c6018493f22b784f2` and exact planning tip `cd653d95fd3dd7b3e46565c59d44134d84fae44e`. Why: the arc makes existing CodeQL completion and GHAS result semantics part of ordinary merge protection without changing thresholds or native code-scanning rules. How: all disposable PRs were closed without merge, all disposable branches were removed, and no bypass was used. Evidence: [PR #198](https://github.com/alanmz-crypto/convmem/pull/198), [PR #199](https://github.com/alanmz-crypto/convmem/pull/199), [PR #200](https://github.com/alanmz-crypto/convmem/pull/200), [PR #201](https://github.com/alanmz-crypto/convmem/pull/201), [B2 status](https://api.github.com/repos/alanmz-crypto/convmem/statuses/d3d0bdd9986c7f77e60f956c6018493f22b784f2), and [live ruleset](https://api.github.com/repos/alanmz-crypto/convmem/rulesets/19156572). **Resume state:** `CLOSED/PASS — no further execution; Ryan owns quarterly plus configuration-drift attestation.` [`EXECUTION-codeql-complex-therapy.md`](../plans/EXECUTION-codeql-complex-therapy.md) · [`VERIFY-codeql-complex-therapy.md`](../plans/VERIFY-codeql-complex-therapy.md) · [`STATUS-codeql-complex-therapy.md`](../plans/STATUS-codeql-complex-therapy.md).

## Recently merged / settled (2026-08-08 through 2026-08-16)

- **Pinwheel Pytest CI — CLOSED (2026-08-16, [#191](https://github.com/alanmz-crypto/convmem/pull/191) + disposable [#192](https://github.com/alanmz-crypto/convmem/pull/192)–[#194](https://github.com/alanmz-crypto/convmem/pull/194)):** Who/What: pinned `pytest==9.1.1`, 16-module checker, 21 contract tests. When: impl merged `857a3a2`; disposable + VERIFY [#195](https://github.com/alanmz-crypto/convmem/pull/195); Kiro V7a PASS; Ryan arc-close. Why: reproducible pytest CI after Kryptonite. How: gate live on `main` `d495e4b`. [`VERIFY-pinwheel-pytest-ci.md`](../plans/VERIFY-pinwheel-pytest-ci.md). **Resume state:** `CLOSED` — no further Pinwheel work.

## Recently merged / settled (2026-08-08 through 2026-08-15)

- **CI Behavioral Merge Gate — MERGED; enforcement NEGATIVE CONTROL PASS (2026-08-16, [#187](https://github.com/alanmz-crypto/convmem/pull/187) + disposable [#188](https://github.com/alanmz-crypto/convmem/pull/188)):** Who/What: hermetic pytest job in GitHub Actions; `Protect Main` requires `pytest (3.12)` alongside `pylint (3.12)`. When: #187 merged as `c2c6429` on 2026-08-15; #188 tested and closed on 2026-08-16. Why: prove a known-bad candidate cannot enter `main` through the ordinary path. How: #188 head `02ee739` produced a red required `pytest (3.12)` check and `mergeStateStatus=BLOCKED`; admin bypass was observed as available but not exercised. **Arc CI Kryptonite is CLOSED** — the behavioral merge gate and negative-control evidence were completed, and the closeout documentation merged via #189. No CI Kryptonite execution or docs-merge gate remains. See [`VERIFY-ci-behavioral-merge-gate.md`](../plans/VERIFY-ci-behavioral-merge-gate.md) and [`CODEX-2026-08-15-ci-behavioral-merge-gate-closeout-handoff.md`](CODEX-2026-08-15-ci-behavioral-merge-gate-closeout-handoff.md).

- **Crush index freeze + refine memory — MERGED + DEPLOYED (2026-08-15, [#184](https://github.com/alanmz-crypto/convmem/pull/184)):** Who/What: hard-deny `convmem index/add/verify` inside Crush hook (exit 2) plus `refine.py` `gc.collect()` + `malloc_trim(0)` between daemon cycles. When: squash-merged to `main` as `e82cbd0`; Kiro PASS @ `2179b08`; live hook deployed via `deploy-agent-protocol.sh`. Why: long-running index inside Crush hit ~60s bash timeout; refine daemon grew ~9.4G over 32h. How: no further action — hook live after Crush restart.

- **Forward-announcement norm + stuck-branch cleanup — COMPLETE (2026-08-14):** Who/What: Kiro triage handoff → Cursor implemented and Ryan merged three PRs. When: #176–#178 squash-merged 2026-08-14. Why: completing models did not announce next lane or review path, leaving unique commits stranded on feature branches. How: Tier A **Forward announcement** norm in `config/agent-protocol.md` (phase name, next step, next lane, lowest-effort “see my work”); rebased and merged judge injection hardening ([#177](https://github.com/alanmz-crypto/convmem/pull/177)) and synthesis operational-detail prompt ([#178](https://github.com/alanmz-crypto/convmem/pull/178)); `fix/2026-08-06-ask-eval-trace` was already on `main` (rebase dropped commits as upstream). **Parked (not authorized):** intake-classification infrastructure on `plan/2026-08-14-arc-classification-verify-gate` (local stash) — behavioral norm is the chosen fix unless Ryan re-opens.

- **Arc-staleness doctor check — COMPLETE (merged to `main`, live):** Who/What: advisory `arc_staleness` check in `convmem doctor` that warns when STATUS-tracked arcs have incomplete milestones but no Update Log progress in >14 days. When: merged as `f4a42d0` (within the #174-180 window, on `main`). Why: catches the "authorized but forgotten" pattern (P1.3 source-trust was 22 days stale with no execution). How: `_check_arc_staleness()` in `doctor.py:1011`, registered in `run_doctor()` (`doctor.py:1389`); register entry `docs/standing-checks-register.json`; 6 tests in `tests/test_doctor_arc_staleness.py` all pass. Verified live: `convmem doctor` reports `[PASS] arc_staleness: 5 arcs tracked, 0 stale`. Implementation handoff originally for Cursor/Codex - no longer needed (work merged). [`KIRO-2026-08-13-arc-staleness-check-handoff.md`](KIRO-2026-08-13-arc-staleness-check-handoff.md). **Forward announcement:** I finished: arc-staleness doctor check implementation+merge. Next step: none - it is on `main` and live; verify with `convmem doctor` / `pytest tests/test_doctor_arc_staleness.py`. Next lane: Kiro (optional review) or Ryan (no action). See my work: `git show f4a42d0`.
- **LATEST stale-handoff autonomy — APPROVED (2026-08-14, Kiro):** Crush may autonomously update+commit+push `LATEST.md` on feature branches when the brief flags it stale (pointer housekeeping for already-authorized work only; non-`main`; no merge/force-push). `HANDOFF-TEMPLATE.md` moved into `_INTER_MODEL_SKIP` so it no longer trips the stale-handoff P0. [`KIRO-2026-08-14-latest-stale-handoff-autonomy.md`](KIRO-2026-08-14-latest-stale-handoff-autonomy.md)

- **JudgeBench fail-closed calibration runs (#171, 2026-08-09):** Architecture-locked offline calibration with G3 corpus. [`ARCHITECTURE-judgebench.md`](../plans/ARCHITECTURE-judgebench.md) · [`STATUS-judgebench.md`](../plans/STATUS-judgebench.md)
- **JudgeBench G3 calibration corpus (#170, 2026-08-09):** Locked corpus for semantic calibration. [`EXECUTION-judgebench-flash-slices.md`](../plans/EXECUTION-judgebench-flash-slices.md)
- **Projection completeness gate (#169, 2026-08-09):** Truthful accounting — stops treating successful-looking Chroma state as proof that every expected projection exists.
- **Preserve projections until reindex succeeds (#168, 2026-08-09):** Predecessor to CG-1; prevents destructive one-file reindex but does not yet prove atomic generation replacement.
- **DeepSeek timeout fix (#167, 2026-08-08):** Raise reasoning model timeout from 15s to 60s.
- **CG-1 dependability handoff (2026-08-10, MERGED):** Full architecture/implementation handoff that underpinned the CG-1 review. [`HANDOFF-CG1-DEPENDABILITY-2026-08-10.md`](HANDOFF-CG1-DEPENDABILITY-2026-08-10.md) · [`CURSOR-2026-08-10-cg1-literature-verification-handoff.md`](CURSOR-2026-08-10-cg1-literature-verification-handoff.md)
- **CG-1 G4b independent review — PASS → MERGED (2026-08-14):** The G4a material GAP (cold-validation binding to promotion) is structurally closed and independently reviewed PASS at stabilization SHA `2ed229244ea1d7cdf9a83630ad56d5a194426826`. Crush verified the exact bytes; then Codex fixed the pylint gate (`7f7c226`) and **PR #172 merged to `main` 2026-08-14** along with the handoff docs (#173) and this closure package (#174). Verified: full suite 1,284 + 230 subtests (0 fail), focused CG-1 58 pass, dedupe 7 pass. Closure equation `tested = reviewed = accepted = pushed` is satisfied; only CG-2 activation (separate grant) remains open. [`CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md`](CRUSH-2026-08-13-cg1-g4b-review-pass-closure.md)
- **Cross-model export tooling — MERGED (2026-08-14, [#173](https://github.com/alanmz-crypto/convmem/pull/173)):** Who/What: `scripts/export-chatgpt-snapshot.sh` and `scripts/export-claude-bundle.sh` for giving ChatGPT/Claude full project context without changing push conventions. When: squash-merged 2026-08-14 with CG-1 dependability handoff docs. Why: cloud models need repo-grounded bundles without altering push/ref conventions. How: run scripts from repo root; outputs are local artifacts only.

## Active handoff

- **[Arc R2b Capture Authorization] v2 mutable-source correction planned (2026-08-27):** Who/What: Luna High prepared a versioned architecture amendment, bounded execution/state-machine plan, VERIFY matrix, and current STATUS snapshot from D4 `origin/main` `89a7e045b130f005f57539478d9a180cbea905df`. When: docs-only branch `docs/2026-08-27-r2b-v2-writer-gate-normative`; no runtime action occurred. Why: v1 timing-only behavior is incompatible with a continuously mutating live source. How: future R2b must hold one live exclusive writer-gate lease across trusted snapshot → packet draft/ACCEPT → materialization → ACCEPT AND GRANT → one capture → final source recomputation → close evidence → release. Zero-bypass coverage, concrete durations, implementation, activation, and all live authority remain pending Ryan. **900 seconds is not ratified.** Old v1 manifests and quarantined runs `2026-07-21-r2b-capture-01` / `2026-08-27-r2b-capture-02` are not upgraded or reused. Merge reading: [`STATUS-r2b-capture-auth.md`](../plans/STATUS-r2b-capture-auth.md) · [`ARCHITECTURE-r2b-mutable-source-quiescence-v2.md`](../plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md) · [`EXECUTION-2026-08-27-r2b-v2-quiescence.md`](../plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md) · [`VERIFY-r2b-v2-quiescence.md`](../plans/VERIFY-r2b-v2-quiescence.md).

- **CG-2 authority migration — MERGED (#186); V8a PASS; V8b grant PASS; soak ACCEPTED; Design A architecture papered (docs branch); V8c PENDING:** Who/What: T1–T5 on `main` (`2f427fc`); Kiro V8a independent sign-off PASS (subject `2f427fc`, preservation on `451f523`); soak completion Ryan-accepted 2026-08-21; Design A first-cutover rollback-bootstrap architecture papered on `docs/2026-08-21-cg2-design-a-arch-lock`. Why: gateway proven; independent review closed; Design A closes `previous_generation_id=None` before any first-owner grant. How: see VERIFY V8a/V8c rows + Design A ARCHITECTURE/RUNBOOK. **Resume state:** next governed step is **Design A execution plan** only — **not** implementation/activation yet. **V8c** first-owner packet remains **PENDING** and comes **after** Design A implementation/evidence. Not authorized for first owner, fence/pointer publication, activation manifest, GC, Shadow, or R2b. Desktop checklist: `~/Desktop/CG2-after-soak-checklist.md` (not in repo).

- **JudgeBench semantic calibration v1 — G3 locked; Phase A merged (2026-08-21 reconcile):** Who/What: S1–S9 (#144) + T2–T5 (#155) merged; **G3 corpus merged and locked** (#170); **Phase A fail-closed calibration prep merged** (#171); VERIFY CHK-001..006 and CHK-008 PASSED, CHK-007 PARTIAL (no calibration run). When: #155 merged 2026-08-09, #170/#171 merged 2026-08-10. Why: offline judge calibration before live quality claims. How: read arc brief; `cases.jsonl`/`gold.jsonl` are already Ryan-locked; the corpus is populated.

  **Merge reading:** [`docs/plans/STATUS-judgebench.md`](../plans/STATUS-judgebench.md) · [`VERIFY-judgebench.md`](../plans/VERIFY-judgebench.md) · [`ARCHITECTURE-judgebench.md`](../plans/ARCHITECTURE-judgebench.md)

  **Suggested next:** Ryan's separate 60-call calibration-experiment grant, then G4 judge selection; standing checks `eval-provenance-wiring` / `eval-negative-control-coverage` when assigned.

- **Shadow Ledger Phase 0 — activation-ready path (2026-08-09):** Who/What: Phase 0 + corrective C1–C7 **code on `main`** (#122, #126, #131, #134); shadow **still disabled**. When: Execute + VERIFY done; ops evidence not started. Why: merge ≠ activate. How: read [`STATUS-shadow-ledger-phase0.md`](../plans/STATUS-shadow-ledger-phase0.md) section 6 — C6 event-size evidence → C7 7-day census → C6 canary PASS → fresh writer census → runbook → Ryan grant → `shadow-activate`. Prior C7 census removed 2026-08-06.

  **Merge reading:** [`STATUS-shadow-ledger-phase0.md`](../plans/STATUS-shadow-ledger-phase0.md) · [`EXECUTION-shadow-phase0-activation-corrective.md`](../plans/EXECUTION-shadow-phase0-activation-corrective.md) · [`CODEX-2026-07-30-C7-OPERATIONAL-RUNBOOK.md`](CODEX-2026-07-30-C7-OPERATIONAL-RUNBOOK.md)

- **Track 1 backup — Hybrid consistency bar LOCKED (2026-07-24):** Who/What: Ryan locked Hybrid after DeepSeek V4-Pro + Kiro dense consult; Copilot must audit exact SHA `492e6e7` with A-checklist + Five-part report card. When: still open track. Why: full-root backup merge blocked on safety bar. How: paste [`COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md`](COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md). **Separate from Shadow.**

- **R2b v1 implementation is historical; live capture remains unauthorized (2026-07-22):** Implementation landed [#67](https://github.com/alanmz-crypto/convmem/pull/67) as [`c0f06f5`](https://github.com/alanmz-crypto/convmem/commit/c0f06f57ac1cf82df205fe0c5bd3d60422012b1b). Disk draft `~/.local/share/convmem/authorizations/r2b/2026-07-21-r2b-capture-01/` is **QUARANTINED / abandoned** (stale T4; no sidecar; do not ACCEPT AND GRANT from it). The v2 correction is now the active planning path; see the 2026-08-27 R2b v2 entry above. Do not merge #64 or reuse/upgrade a v1 packet.

- **R2b capture authorization (2026-07-20, wording updated 2026-07-22):** Option A settled in [`../plans/ARCHITECTURE-r2b-capture-auth.md`](../plans/ARCHITECTURE-r2b-capture-auth.md); execution/VERIFY as linked from Active handoff **R2b capture** bullet. **Implementation is on `main` via [#67](https://github.com/alanmz-crypto/convmem/pull/67)** — do not re-assert “no implementation authorized.” **Live capture** and draft `2026-07-21-r2b-capture-01` remain unauthorized / quarantined (see Active handoff). Supersedes #64; do not merge #64.

## Completed / settled (historical archive)

_Closed/completed/settled items previously listed under Active handoff, moved here so Active handoff reflects only genuinely active or gated work. Historical records, preserved verbatim._

- **Chroma reconcile Tier L — R4 GREEN, arc closed (2026-08-09):** Who/What: Crush index rebuild + DeepSeek Flash V1–V6 post-rebuild verify; Cursor landscape sync. When: rebuild completed 2026-08-08; R4 GREEN 2026-08-09; docs on `main` via [#161](https://github.com/alanmz-crypto/convmem/pull/161). Why: 646 HNSW orphans blocked calibration and contaminated retrieval. How: full re-index, orphan inventory **0**, calibration 100% with `eval-synthesis.py --judge --legacy`, and `convmem doctor` PASS with two non-fatal warnings (legacy embed metadata and external-restic freshness).

  **Merge reading:** [`docs/plans/STATUS-chroma-reconcile-tier-l.md`](../plans/STATUS-chroma-reconcile-tier-l.md) · [`FLASH-2026-08-08-post-rebuild-verify-handoff.md`](FLASH-2026-08-08-post-rebuild-verify-handoff.md) · [`CRUSH-2026-08-08-index-complete-judgebench-unblock.md`](CRUSH-2026-08-08-index-complete-judgebench-unblock.md) · [`EXECUTION-chroma-reconcile-tier-l.md`](../plans/EXECUTION-chroma-reconcile-tier-l.md)

  **What this packages:** Corpus is trustworthy for retrieval-dependent eval again. Arc closed except optional R5 anomaly disposition and Ryan-gated ops (watch/refine).

  **Suggested next:** JudgeBench calibration-experiment grant + G4 — see STATUS-judgebench (G3 already locked).

- **STATUS arc-brief pattern — on `main` (#160–#161):** Four arc briefs + cross-arc rollup [`docs/inter-model/STATUS.md`](STATUS.md). New arcs require `STATUS-<slug>.md` at plan start.

- **DeepSeek V4 Flash timeout fix — COMPLETE (2026-08-09):** Who/What: Kiro diagnosed and fixed continuous `ReadTimeout` failures in watch service distill/summarize path. When: 2026-08-09, committed to `fix/2026-08-09-deepseek-v4-flash-timeout`. Why: V4 Flash is a reasoning model that spends 10-20s on internal chain-of-thought before producing output; the 15s timeout (set when the summarizer switched to DeepSeek cloud) was too tight. How: raised timeout from 15s → 60s in both `distill.py` and `llm.py` `summarize()` path. Verified: 19 tests pass, live distill succeeds in 5.7s, watch restarted with 0 failures.

  **Merged:** [#167](https://github.com/alanmz-crypto/convmem/pull/167) to `main` (2026-08-09).

  **What this packages:** Watch/ingest pipeline no longer fails on every DeepSeek call; ingest-degraded count dropped after merge.

- **Summarizer GPU contention fix — COMPLETE (2026-08-07):** Who/What: Crush (investigation) + Claude cloud (advisory) + Kiro (design review) fixed four issues from the qwen3.5 summarizer saturating the RTX 3060 at 95% GPU util, causing ollama embed calls to blow 120 s timeouts and silently drop ingested chunks. When: 2026-08-06 evening, committed to `fix/2026-08-06-summarizer-switch-baseline-and-docs`; PR #140 filed. Why: every chunk's summarize→embed→distill pipeline queued behind a single `-np 1` 6.6 GB model; `ingest.py:638` caught exceptions and `continue`d with zero visibility. How: `summarize_model = "deepseek-v4-flash"` (cloud, key present), `ollama_embed` timeout 120→300 s, `OLLAMA_MAX_LOADED_MODELS=2` (was 1), chunk failure logging to `synthesis_failures.jsonl` + 3-attempt retry with 5s/30s backoff in `ingest.py`. Verified: zero watch journal timeouts after fix, both models resident in `ollama ps`, all doctor PASS.

  **Merge reading:** [`CRUSH-2026-08-06-summarizer-gpu-timeout-handoff.md`](CRUSH-2026-08-06-summarizer-gpu-timeout-handoff.md) · [PR #140](https://github.com/alanmz-crypto/convmem/pull/140) · [`CODEX-2026-08-02-summarizer-switch-decision.md`](CODEX-2026-08-02-summarizer-switch-decision.md)

  **What this packages:** Summarizer moved off local GPU to DeepSeek cloud for automated watch/ingest path (qwen3.5 retained for batch runs via CONVMEM_CONFIG override). Embed timeout raised. Ollama model coexistence enabled. Silent chunk drops now logged and retried.

  **Ledger record:** pending -- see session close.

- **Summarizer model switch to qwen3.5 — CLEANUP COMPLETE (2026-08-06):** Who/What: Crush finished the half-applied summarizer switch from llama3.1:8b to qwen3.5:latest. When: config edit applied 2026-08-03 (during C7 freeze, no recorded grant); baseline re-run + soak + LATEST reconciliation on 2026-08-06 after freeze lift. Why: live config was already on qwen3.5 but baseline was stale (llama-era 3-row fixture), VERIFY doc was lost from disk, and no ledger record existed. How: re-ran `eval-summaries.py --update-baseline` (structural 100%, keyword recall 86.67% on 3-row set); soak-tested with real Crush session ingest (192 units, 25 chunks -- 3 distill warnings but summaries healthy); removed expired C7 writer-census to unblock writes. **Note (2026-08-07):** qwen3.5 summarizer subsequently moved off the automated ingest path due to GPU saturation (see entry above); retained for batch runs only.

  **Merge reading:** [`CODEX-2026-08-02-summarizer-switch-decision.md`](CODEX-2026-08-02-summarizer-switch-decision.md) · [`CRUSH-2026-08-02-summarizer-bakeoff-chroma-assessment.md`](CRUSH-2026-08-02-summarizer-bakeoff-chroma-assessment.md)

  **What this packages:** Live config `summarize_model = "qwen3.5:latest"` now has matching baseline fixture, verified soak, and consistent LATEST.md. VERIFY-2026-08-03-summarizer-switch-decision.md lost from disk (indexed in Chroma only); not reconstructed -- search corpus retains the evidence.

  **Ledger record:** pending -- see session close.

- **Complete-data backup correction v2 — ROLLOUT COMPLETE (2026-07-28):** Who/What: PR #125 squash-merged to `main` as [`83b8c11`](https://github.com/alanmz-crypto/convmem/commit/83b8c11683c1295579c4fad9c8316f9f8fc3d10f); Crush (DeepSeek V4 Pro) executed four post-merge live grants on `archlinux` with Ryan approval. When: all grants complete 2026-07-28. Why: legacy-chroma profile never proved complete-data protection; v2 corrects this with explicit profile, fallback-free workflows, and hermetic proof. How: grant 1 (profile + data root in restic.env), grant 2 (first v2 snapshot), grant 3 (offsite copy + lineage), grant 4 (v2 local + external timers). Legacy `convmem-restic-ensure.timer` disabled; old external timer contained before v2 snapshot.

  **Merge reading:** [`ARCHITECTURE-complete-data-backup-correction-v2.md`](../plans/ARCHITECTURE-complete-data-backup-correction-v2.md) · [`EXECUTION-complete-data-backup-correction-v2.md`](../plans/EXECUTION-complete-data-backup-correction-v2.md) · [`VERIFY-complete-data-backup-correction-v2.md`](../plans/VERIFY-complete-data-backup-correction-v2.md) · census [`COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.md`](../plans/COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.md) · Hybrid bar [`COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md`](COPILOT-2026-07-24-complete-data-backup-hybrid-bar.md)

  **What this packages (product terms):** One validated `BackupContext`; explicit `complete-data-v2` activation profile (`WARN_LEGACY_ONLY` until live grants); fallback-free `backup_workflows.py`; reusable atomic publication; capture evidence + closed restore matrix.

  **Immutable FAIL evidence:** `b6284ad9ac42e0bb554cd2d44d512b01bad748f2` (Codex FAIL). Earlier PR #120 `492e6e7…` remains Ryan `A-FAIL / FAIL`.

  **Suggested next:** None — rollout complete. Standing checks (`recency-boost-retune`, `escalation-threshold-retune`) are DUE and independent of backup.

- **Shadow Ledger Phase 0 Execute MERGED — soft close (2026-07-25):** Who/What: Ryan squash-merged [#122](https://github.com/alanmz-crypto/convmem/pull/122) to `main` as [`4535107`](https://github.com/alanmz-crypto/convmem/commit/4535107143279c87e8b34c1eab7e4dee88bffc68) (*Implement Shadow Ledger Phase 0 (disabled by default)*). Cursor soft-closing the Execute chat for DeepSeek / Kiro / Codex. When: now. Why: code + VERIFY mechanical + V8 sign-off + pylint green are on `main`; live enable is a **different** grant. How: read Merge reading below; **do not** edit `~/.config/convmem/config.toml` or write a production activation manifest without Ryan’s explicit activation grant.

  **Merge reading:** [`ARCHITECTURE-shadow-ledger-phase0.md`](../plans/ARCHITECTURE-shadow-ledger-phase0.md) · [`EXECUTION-shadow-ledger-phase0.md`](../plans/EXECUTION-shadow-ledger-phase0.md) · [`VERIFY-shadow-ledger-phase0.md`](../plans/VERIFY-shadow-ledger-phase0.md) · [`SHADOW-WRITER-COVERAGE-INVENTORY.md`](../plans/SHADOW-WRITER-COVERAGE-INVENTORY.md) · [`PHASE0-SHADOW-CONTRACT.md`](../plans/PHASE0-SHADOW-CONTRACT.md)

  **What landed (product terms):** Disabled-by-default shadow delta capture: write-store factory injects sink only when eligible; durability/health; disposable temp-Chroma replay; `convmem shadow-inventory` readiness CLI; doctor `shadow_ledger: disabled` check.

  **VERIFY posture at merge:** V0–V7 mechanical PASS; V8 PASS (DeepSeek V4-Pro + Kiro cross-check). Ryan GATE for Execute = merge. **Ryan GATE for activation = still PENDING.**

  **Lessons for next lane (do not re-learn the hard way):**
  1. **Factory coverage first** — tip `5c0ddb8` proved 0 prod `open_chroma_for_write` callers / 14 bypasses; V3 could not PASS until writers migrated.
  2. **Task order** — after T2, prefer T4 projector then T3/V4 durability before T5 readiness (plan + dense consult); T5 alone cannot honestly PASS isolation.
  3. **Activation ≠ merge** — dense consult DeepSeek+Kiro: **NOT-YET** until V8 + merge + separate grant + runbook; merge alone never enables the sink.
  4. **Pylint regression gate** — CI compares to `origin/main` baseline; do not only sprinkle disables. The sticky #122 fail was a real bug: factory migration dropped `from chroma_store import ChromaStore` while nine `store: ChromaStore` annotations remained (`refine.py`) → +9 E0602. Fix = restore import; then clean remaining new-file fingerprints. Local proof: `python -m pylint $(git ls-files '*.py') --output-format=json > /tmp/pylint-report.json` then `python scripts/pylint_regression_gate.py ci --report /tmp/pylint-report.json --pylint-status $? --branch-baseline ci/pylint-baseline.json --base-ref origin/main`.
  5. **Live residuals (non-blocking for disabled Phase 0):** `embed_collection_identity` WARN (legacy missing `convmem:embed_model`); restic freshness can FAIL independently of shadow.

  **Suggested next (Ryan-gated, pick one):**
  - **DeepSeek / Kiro:** activation readiness re-consult or review a draft runbook — still no live enable.
  - **Codex:** only if Ryan wants a new Architecture/Execution slice (activation ops plan, embed metadata, or Track 1 backup #120) — do not reopen Phase 0 Execute.
  - **Cursor:** idle on Shadow until activation grant or a new Execute brief.

- **Shadow Ledger Phase 0 Architecture HITL LOCKED (2026-07-24):** Who/What: Ryan approved Direction on the Architecture path (now superseded for Execute by merged #122). When: Architecture closed. Why: Option B boundary. How: Execute complete on `main` @ `4535107`; activation still separate.

- **Shadow Ledger Gate 1b PASS (Ryan 2026-07-24):** Audit corrections accepted (#121 `0d08310`). Historical precondition for Execution Planning; Execute itself is now merged (#122 / `4535107`).

- **Workspace-coord salvage to GitHub (2026-07-24):** Who/What: WS-main-cursor lands previously LOCAL_ONLY audit dir, ChatGPT handoff, Track-1/2 decision memos, coord board snapshot. When: Round 3 after ONE_PRIMARY → WS-main-cursor. Why: close sibling chats without losing takeover data. How: dedicated docs branch (not research-pack, not #115 edits). See [`CURSOR-2026-07-24-backup-neutral-decision-memos.md`](CURSOR-2026-07-24-backup-neutral-decision-memos.md), [`COORD-2026-07-24-shadow-ledger-workspaces-BOARD.md`](COORD-2026-07-24-shadow-ledger-workspaces-BOARD.md).

- **Research pack for cloud Claude/ChatGPT (2026-07-24):** Branch [`docs/2026-07-24-research-pack-backup-neutral`](https://github.com/alanmz-crypto/convmem/tree/docs/2026-07-24-research-pack-backup-neutral/docs/inter-model/research-pack-2026-07-24-backup-neutral). Who/What: Cursor frozen attachments + handoffs so max models can research (1) complete-data backup close decisions and (2) Neutral/Office Gate-0 + ledger-first appetite. When: pack PR. Why: those two tracks are the remaining forward blockers; Codex↔Cursor lane (#109/#112) stays closed. How: open [README](research-pack-2026-07-24-backup-neutral/README.md); paste `CLAUDE-HANDOFF.md` / `CHATGPT-HANDOFF.md`; browse `attachments/`. **Does not authorize** Office coding, Neutral extraction, or live Restic rollout.

- **Codex planning / Cursor execution LANDED + DEPLOYED (2026-07-24):** Squash-merged [#109](https://github.com/alanmz-crypto/convmem/pull/109) to `main` as [`982a502`](https://github.com/alanmz-crypto/convmem/commit/982a5028400cd9d5c45201e1cd127ea1d5b663ef).  
  **Consequence:** Live overlays name **Codex** for architecture/execution planning and **Cursor** for implementation; Planning Guide Contract **v2** (actor-neutral HITL stop).  
  **Who:** Codex Architecture + Execution/VERIFY; Kiro plan PASS @ `0096d56`; Cursor Execute; BugBot clean @ `a77dbc0`; Ryan merge + deploy.  
  **What/When/Why/How:** Plans [`../plans/ARCHITECTURE-codex-planning-cursor-execution.md`](../plans/ARCHITECTURE-codex-planning-cursor-execution.md), [`../plans/EXECUTION-2026-07-24-codex-planning-cursor-execution.md`](../plans/EXECUTION-2026-07-24-codex-planning-cursor-execution.md), [`../plans/VERIFY-codex-planning-cursor-execution.md`](../plans/VERIFY-codex-planning-cursor-execution.md). Deploy: `scripts/deploy-agent-protocol.sh` from `origin/main`. Copilot targeted audit not invoked. PR Steward not granted.  
  **TL;DR:** Lane split is on `main` and live; VERIFY GATE accepted.

- **Crush freezes + Qwen/DeepSeek billing routing LANDED (2026-07-23):** Squash-merged [#106](https://github.com/alanmz-crypto/convmem/pull/106) to `main` as [`67b020f`](https://github.com/alanmz-crypto/convmem/commit/67b020fd7fd545cd583496f2bb6a1808bfc53f7b).  
  **Consequence:** Crush uses shell `convmem` (MCP disabled) to avoid tool hangs; Cursor-dry work goes to Crush **Qwen3.7-Max**, with **DeepSeek V4 Pro/Flash** as second cloud seat.  
  **Who:** Cursor + Crush soak; Ryan squash-merged.  
  **What/When/Why/How:** Handoff [`CURSOR-2026-07-23-crush-qwen-stability-handoff.md`](CURSOR-2026-07-23-crush-qwen-stability-handoff.md); paste [`../CRUSH-QWEN-BOOTSTRAP.md`](../CRUSH-QWEN-BOOTSTRAP.md) / [`../CRUSH-DEEPSEEK-BOOTSTRAP.md`](../CRUSH-DEEPSEEK-BOOTSTRAP.md); routing in [`../MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md).  
  **Follow-up ([#107](https://github.com/alanmz-crypto/convmem/pull/107) MERGED):** squash-merge default note + soaks.  
  **Crush MCP hang FIXED + RE-ENABLED (2026-07-24):** Squash-merged [#108](https://github.com/alanmz-crypto/convmem/pull/108) as [`1d80a26`](https://github.com/alanmz-crypto/convmem/commit/1d80a26). Shell-profile sync tools had deadlocked `tools/call` ↔ `roots/list`; cwd fallback + explicit hook `allow`. Post-merge probe **PASS** ~13 s; live `mcp.convmem.disabled=false`. **Restart Crush** so hooks/MCP load.

- **Crush tool-output residual GATE ACCEPTED (2026-07-23):**  
  **Consequence:** Crush routine digs in the Task 2 soak sat ~**30k** prompt tokens instead of the old ~**100k** residual — cheaper if agents keep tool dumps thin; we did **not** start an MCP-clipping follow-on. Ryan accepted the close paperwork after [#103](https://github.com/alanmz-crypto/convmem/pull/103) / [#104](https://github.com/alanmz-crypto/convmem/pull/104).  
  **Who:** Cursor Execute + VERIFY; Crush/`deepseek-v4-flash` soak; Ryan GATE accepted.  
  **What:** Always-loaded `tool-output-hygiene` (ranged bash/view/grep; failures still show exit + last lines).  
  **When:** Execute [#102](https://github.com/alanmz-crypto/convmem/pull/102) → `main` [`482637b`](https://github.com/alanmz-crypto/convmem/commit/482637b7bf3bfe82eba6007ad8fdf09eeae4ce43); soak + VERIFY [#103](https://github.com/alanmz-crypto/convmem/pull/103) `e324d2f`; merge-reading guidance [#104](https://github.com/alanmz-crypto/convmem/pull/104) `ca1178b`.  
  **Why:** Stage 4 fixed standing ~6k; tool-history rebill was still the bill.  
  **How:** Live rule `~/.config/crush/rules/tool-output-hygiene.md`; three soaks mean ~30.5k vs ~98–107k; Task 3 SKIP.  
  **Caveat / TL;DR:** Short guided soaks — not equal-weight proof vs old mega-audits; Stage 4 stays CLOSED. Plans: [`../plans/ARCHITECTURE-residual-tool-output.md`](../plans/ARCHITECTURE-residual-tool-output.md), [`../plans/EXECUTION-2026-07-22-residual-tool-output.md`](../plans/EXECUTION-2026-07-22-residual-tool-output.md), [`../plans/VERIFY-residual-tool-output.md`](../plans/VERIFY-residual-tool-output.md).  
  **Known residual (no arc):** Crush UI can hang on “waiting for a tool response” (seen ×3 on 2026-07-23 soak). Reopen only if it keeps biting.

- **PR / VERIFY human layer + merge reading (2026-07-23):** [#103](https://github.com/alanmz-crypto/convmem/pull/103) + [#104](https://github.com/alanmz-crypto/convmem/pull/104) on `main`. Arc-close and Execute PRs lead with consequence → 5 Ws → TL;DR **and** a **Merge reading** link list (ARCHITECTURE / EXECUTION / VERIFY / LATEST); mechanical tables stay. Canonical: `AGENTS.md` PR summary guidance; template: [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md).

- **Copilot CLI Tier A surface LANDED + DEPLOYED (2026-07-22; key hygiene 2026-07-23):** Squash-merged [#97](https://github.com/alanmz-crypto/convmem/pull/97) to `main` as [`8b0f53f`](https://github.com/alanmz-crypto/convmem/commit/8b0f53f). Who/What: Cursor land of GitHub Copilot **CLI** session adapter + watch/doctor/open_source + always-on instructions (filename A: `config/copilot-instructions-convmem.example.md`) + key-omitted MCP example; not GitHub.com Copilot billing/PR settings. When: merge + `deploy-agent-protocol.sh` same day (always-on + optional `--agent convmem` synced; `mcp_copilot` PASS). **Follow-up:** live `~/.copilot/mcp-config.json` had retained a real `DEEPSEEK_API_KEY`; scrubbed and deploy now strips that key always (mcp_server loads `env.local`). Why: end COMBINE residue from cross-arc consolidation so plain `copilot` is ingestible and ritual-capable on `main`. How: Track A via `~/.copilot/session-state/<uuid>/events.jsonl`; docs [`../COPILOT-SESSION-ADAPTER.md`](../COPILOT-SESSION-ADAPTER.md). Parallel Kiro generate/deploy tip folded under filename A — do not revive `copilot-instructions.example.md`. **Does not authorize** expanding the scarce GitHub Copilot audit lane or GitHub-hosted spend.

- **BugBot PR-level external review gate LANDED (2026-07-22):** Squash-merged [#91](https://github.com/alanmz-crypto/convmem/pull/91) to `main` as [`db3e5e0`](https://github.com/alanmz-crypto/convmem/commit/db3e5e0aeff29b6666441200e3cbb5db7b30559e). SHA-bound BugBot evidence in Execute/Verify; tracked `.cursor/BUGBOT.md` review context only. Independent of Copilot audit lane and PR Steward — do not collapse “someone looked” into BugBot PASS. Org branch-protection / non-Cursor fallback reviewer remain optional follow-ons (not authorized by the merge).

- **MCP Roots brief boundary LANDED (2026-07-22):** Squash-merged [#87](https://github.com/alanmz-crypto/convmem/pull/87) to `main` as [`eb84472`](https://github.com/alanmz-crypto/convmem/commit/eb84472f7ae6fedd75f9ace4359c913b15ee9136). Cursor shell MCP may omit `brief` when Roots report a project workspace — closes the old “global MCP starts in `$HOME` so every chat re-briefs” product gap from Stage 3 / [#19](https://github.com/alanmz-crypto/convmem/pull/19). Residual panel/`stats` live proof and bridge “Connection closed” debug are optional, not a reopen of the land.

- **PR Steward prompt LANDED + DEPLOYED (2026-07-22):** Squash-merged [#92](https://github.com/alanmz-crypto/convmem/pull/92) to `main` as [`0e2b396`](https://github.com/alanmz-crypto/convmem/commit/0e2b396c6a04b32a373deb0480d84efd64f10209). Canonical TEAM_CHARTER Steward suggest-line + standing check `pr-steward-reminder` (Platform, manual, 30-day) + Platform charter `register_refs`. Kiro independent VERIFY V0–V4 PASS (pre-rebase tip `6145c1b`; land tip later rebased). Live overlays updated via `deploy-agent-protocol.sh` (Cursor/Codex/Kiro/Crush Steward line present; mcp-shell excluded). **Docs residual closed:** VERIFY V0b + EXECUTION blurb corrected `2`→`3` (pre-squash tip was product pair + VERIFY doc). Not a merge/deploy reopen.

- **Semantic dedupe / queue hygiene GATE ACCEPTED (2026-07-22):** VERIFY PASS at tip [`dba9795`](https://github.com/alanmz-crypto/convmem/commit/dba9795785b4dffdbb21f9cad82d93332b8b1554) ([#86](https://github.com/alanmz-crypto/convmem/pull/86)). Phase A shipped (ingest total-line `queue_max_depth` pause; live refine jobs omit `semantic_dedupe`; example config documents optional job). Phase C default band closed: exact-title @ similarity ≥0.999 drained (pending exact=0); banded applies with undo under `refine_undo/semantic_dedupe/`; no `--approve-dedupe all`. Cursor mechanical PASS + Kiro independent PASS; **Ryan GATE accepted**. Remaining ~1055 pending are lower bands (0.98/0.95/0.92) or non-exact 1.000 — **not authorized**. Phase D (snapshot steering) still deferred / separate GATE. Plans: [`../plans/ARCHITECTURE-semantic-dedupe-hygiene.md`](../plans/ARCHITECTURE-semantic-dedupe-hygiene.md), [`../plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md`](../plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md), [`../plans/VERIFY-semantic-dedupe-hygiene.md`](../plans/VERIFY-semantic-dedupe-hygiene.md). Handoff: [`CURSOR-2026-07-22-semantic-dedupe-hygiene.md`](CURSOR-2026-07-22-semantic-dedupe-hygiene.md).

- **P1.3 live soak CLOSED (2026-07-22):** Day-0 A/B + Crush + Cursor behavioral PASS; Day+1 A/B PASS. Steering preferred for `ksweep-deploy` / `#ksweep-deploy` with `source_trust_weight = 1.0` and Crush stopgap retired. Residual: Kiro session-snapshot steering copies crowd top-N (deferred to dedupe hygiene Phase D).

- **CI Wait Workflow MERGED (2026-07-22):** [#81](https://github.com/alanmz-crypto/convmem/pull/81) squash-merged to `main` as `c5f17b6`. Optional playbook for productive work while CI/review runs; docs-only six-file scope. Cursor mechanical PASS (V0–V7); Kiro independent sign-off PASS at `0baab46d` (pre update-from-main). VERIFY: [`../plans/VERIFY-ci-wait-workflow.md`](../plans/VERIFY-ci-wait-workflow.md). Architecture: [`../plans/ARCHITECTURE-ci-wait-workflow.md`](../plans/ARCHITECTURE-ci-wait-workflow.md). Playbook on main: [`../CI-WAIT-WORKFLOW.md`](../CI-WAIT-WORKFLOW.md).

- **P1.3 ops complete (2026-07-22):** Live `source_trust_weight = 1.0` in `~/.config/convmem/config.toml`. Crush `ksweep-routing` stopgap retired (rules → `rules-retired/`; deploy no longer redeploys it). Standing check `ksweep-sunset` closed. Smoke: steering still preferred for `ksweep-deploy`.

- **P1.3 source-trust LANDED (2026-07-22):** Merged [#78](https://github.com/alanmz-crypto/convmem/pull/78) (`af31c6e`) + [#77](https://github.com/alanmz-crypto/convmem/pull/77) (`99f8717`). Cursor mechanical PASS with residual; Kiro PASS. Smoke: `ksweep-deploy` steering at rank 1. Follow-ups done via ops complete above (#36 already closed). VERIFY: [`../plans/VERIFY-source-trust-ranking.md`](../plans/VERIFY-source-trust-ranking.md).

- **who-fixes-retrieval CLOSED (2026-07-22):** Debate board Rounds 1–4 coordination closed; round code already on `main`. Inherit/dismiss + cargo: [`CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md`](CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md). VERIFY: [`../plans/VERIFY-who-fixes-retrieval.md`](../plans/VERIFY-who-fixes-retrieval.md). Keep shipped tools (ask trace, diversification, retrieve_for_ask, nested inter-model); corpus job follow-up **closed for default band** — see Active handoff GATE ACCEPTED (lower bands not authorized).

- **P1.3 source-trust ranking (2026-07-21, superseded):** Historical Codex execution brief — superseded by **P1.3 source-trust LANDED** + **P1.3 ops complete** above. Keep packets only as provenance: [`../plans/EXECUTION-2026-07-21-source-trust-ranking.md`](../plans/EXECUTION-2026-07-21-source-trust-ranking.md), [`CURSOR-2026-07-21-p13-codex-packet.md`](CURSOR-2026-07-21-p13-codex-packet.md).

- **Context brief rule (2026-07-21):** Always-loaded companion to RESPONSE_TLDR — when citing PRs, SHAs, ledger ids, or paths, keep the id **and** give Who/What/When/Why/How so Ryan knows what the item is doing. Canonical slice `CONTEXT_BRIEF` in `config/agent-protocol.md`.

- **DeepSeek V4-Pro audit substitute (2026-07-21):** Canonical protocol + hermetic runner for Ryan-authorized Copilot-lane substitutes (not Crush, not `convmem ask`). [`../plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md`](../plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md); `scripts/deepseek_audit_substitute.py`. Merged PR #66 used an earlier ad-hoc PASS — do not treat superseded Cursor plan packets as provenance. **No live substitute audit authorized by this docs change.**

- **PR Steward Delivery role v0.1 (2026-07-21):** Nonblocking governance/protocol PR adding a lasting **PR Steward** Delivery role under Ryan HITL (default actor OpenAI Codex when assigned); v0.1 is the temporary training period. Canonical: [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md); roles: [`../AGENT-ROLES.md`](../AGENT-ROLES.md); successor: [`CODEX-2026-07-21-pr-steward-role.md`](CODEX-2026-07-21-pr-steward-role.md). Compact `TEAM_CHARTER` + fitness test + five regenerated TEAM_CHARTER surfaces. **Deploy not run** — merge ≠ live overlay authority. **PR #65 architecture is merged; R2b implementation remains separate and unauthorized.**

- **VERIFY every arc (2026-07-20):** Binding Planning OS rule — after Execute, every **arc** needs `docs/plans/VERIFY-<slug>.md` before close. Phase guide: [`../planning/VERIFY-PLANNING.md`](../planning/VERIFY-PLANNING.md); copy starter: [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md). Kernel: [`../PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md). Example: [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md).

- **HITL charter — Copilot lifecycle (#54, 2026-07-20):** **Merged and charter active** (`3ee9f28` on `main`). Same-SHA GitHub Copilot audit lane + Kiro PASSes recorded before merge. Canonical: [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md); successor: [`CURSOR-2026-07-20-hitl-charter-copilot-lifecycle.md`](CURSOR-2026-07-20-hitl-charter-copilot-lifecycle.md); original handoff: [`CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md`](CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md). **Deploy qualification:** Cursor and Kiro live surfaces match tip examples. **CLI session plumbing** later closed by [#97](https://github.com/alanmz-crypto/convmem/pull/97) (see Active handoff Copilot Tier A) — do not confuse #54 lifecycle/audit scarcity with CLI ingest wiring. Do not treat #54 as deploy-blocked or awaiting review.

- **Post-#54 backlog / R2a one-job (2026-07-20):** [#52](https://github.com/alanmz-crypto/convmem/pull/52) auth + [#59](https://github.com/alanmz-crypto/convmem/pull/59) Phase D docs merged; nomic/mxbai `shadow.toml` written; Kiro PASS. Binding verify (V0–V7, Restic absolute, per-arm STOP): [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md). Handoff: [`CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md). **Still not authorized:** further R2a without new grant; R2b+, Gate 2, promotion, cleanup. Gate 1 harness SHA remains `3b2790f50414f0445c35748e52f849c6276839f7`.

- **Response TL;DR (2026-07-19):** Canonical rule in `config/agent-protocol.md` (`RESPONSE_TLDR` slice) — every agent response ends with a scaled TL;DR. Regenerated into Cursor/Codex/Kiro/Crush/MCP/ChatGPT surfaces via `scripts/generate-agent-protocol.sh` (deploy with `scripts/deploy-agent-protocol.sh` when Ryan wants live surfaces updated).

- **Stage 3 bounded-autonomy accepted (2026-07-13):** Behaviorally verified and accepted by Ryan on 2026-07-13. Stage 2 soak 3/3 passed ([PR #13](https://github.com/alanmz-crypto/convmem/pull/13)–[PR #15](https://github.com/alanmz-crypto/convmem/pull/15)); doctor-first policy landed in [PR #16](https://github.com/alanmz-crypto/convmem/pull/16); the convmem-only default landed in [PR #17](https://github.com/alanmz-crypto/convmem/pull/17); prompt-level MCP brief deduplication shipped in [PR #18](https://github.com/alanmz-crypto/convmem/pull/18); [PR #19](https://github.com/alanmz-crypto/convmem/pull/19) added a cwd-gated shell profile; [PR #22](https://github.com/alanmz-crypto/convmem/pull/22) closed the doctor-first gate; [PR #24](https://github.com/alanmz-crypto/convmem/pull/24) shipped the human-readable pending-decision review (JSONL remains canonical). Ryan manually verified: `record --list` is readable; `record --approve-last` shows the full card; default-No cancellation leaves the draft unchanged. **MCP `$HOME` re-brief product gap:** closed later by Roots omit on [#87](https://github.com/alanmz-crypto/convmem/pull/87) (see Active handoff) — do not treat the Jul 13 “global MCP starts from `/home/lauer`” line as still-open product work. WordPress, other repositories, architecture, security, and external configuration remain excluded. Plans: [`EXECUTION-token-efficient-bounded-autonomy.md`](../plans/EXECUTION-token-efficient-bounded-autonomy.md), [`ARCHITECTURE-token-efficient-bounded-autonomy.md`](../plans/ARCHITECTURE-token-efficient-bounded-autonomy.md).

- **Always-Available GitHub Fallback (2026-07-12):** shipped; Kiro V6c signed (`Kiro reviewed: 2026-07-12`). V6a remains SKIP because GitHub branch protection requires Pro; do not claim `main` is protected. VERIFY: [`../plans/VERIFY-always-github-fallback.md`](../plans/VERIFY-always-github-fallback.md).

- **Bug sprint scored (2026-07-08):** 5/5 PASS. `tier_1_5_gate: UNLOCKED`. Bug 5 (provider fallback) fixed same day — `_resolve_fallback_model` + warn-once + `CONVMEM_FAIL_ON_FALLBACK=1`. Scored in [`BUG-SPRINT-SUCCESS-2026-07-06.md`](BUG-SPRINT-SUCCESS-2026-07-06.md). Convmem now clear for willowyhollow-practice bug work.

- **Orchestration approach (2026-07-06, merged):** Claude Cloud **Option B** — Tier 1 = **shared memory bus** (not orchestration); bug sprint proves value via [BUG-SPRINT-SUCCESS-2026-07-06.md](BUG-SPRINT-SUCCESS-2026-07-06.md); Tier 1.5 deferred until `tier_1_5_gate: UNLOCKED`; Tier 3 design in convmem-lab. Canonical: [ORCHESTRATION-APPROACH-2026-07-06.md](ORCHESTRATION-APPROACH-2026-07-06.md). Framing: [ORCHESTRATION-FRAMING.md](ORCHESTRATION-FRAMING.md). Prior handoff closed: [HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md).

- **HITL team charter (2026-07-06):** **shipped** — Claude Cloud review integrated; compact `TEAM_CHARTER` in [`config/agent-protocol.md`](../config/agent-protocol.md) (always-loaded via generate/deploy); full doc [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md). Key fix: **Crush lane ≠ DeepSeek API** — say Crush found it, not DeepSeek. Phrasebook + lane table on all Tier A surfaces. Prior handoff: [`HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md`](HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md). Deploy: `bash scripts/deploy-agent-protocol.sh`.

- **Retrieval + synthesis hardening (2026-07-05):** **shipped** — P1c partial synthesis on timeout (`generate_stream`, `synthesis_interrupted`); Manning P1a recency on plain search; protocol anchor `c311` lookup fix; DDIA `ledger_unit_document()` at ingest + `scripts/repair-ledger-documents.sh`; inter-model doc adapter (`docs/inter-model/*.md` → section units, `scripts/index-inter-model-docs.sh` requires `CONVMEM_CONFIRM_PROD=1`); prod/lab **write guard** (`runtime_guard.py`, `write_lane` in doctor). Builder notes: [`suggested-application-of-builder-material.md`](../builder-reference/notes/suggested-application-of-builder-material.md). Streaming plan: [`PLAN-2026-06-29-streaming-synthesis.md`](PLAN-2026-06-29-streaming-synthesis.md) Phase 1 closed.

- **Ops closure (2026-07-05):** weekly digest timer **active** (`convmem-cross-project-digest.timer` Mon 09:00); `attempts.jsonl` real obs ids; `[watch].extra_paths` → `docs/inter-model`; doctor `ledger_documents` + `digest_timer` (v1). Install: `scripts/install-cross-project-digest-timer.sh`.

- **Synthesis + lab-reference (2026-07-05):** **shipped** — lab S1–S5 (`load_attempts`, recency, propose smoke), `lab-reference/` gates, prod port of `load_attempts` + `## Do not retry`, `MODEL-WORKFLOW.md`, `CODEX-DEEPSEEK-VERIFY.md`. Codex + DeepSeek verify PASS (shell + MCP). Cheat sheet: [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md). Verify: [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md). Status: [`SYNTHESIS-STATUS.md`](../../SYNTHESIS-STATUS.md). `--propose` prod trial still Ryan-gated.

- **Builder-reference plan (2026-07-01):** **execution shipped** — README tier A/B/archive, script thresholds reconciled, `Builder lens` on BUILT-PLANS + ROADMAP, DDIA changelog, arch-patterns expanded (1510w), DDIA tier-B on Cursor/Kiro/Codex (Crush unchanged). Plan: [`PLAN-2026-07-01-apply-builder-reference.md`](PLAN-2026-07-01-apply-builder-reference.md). Log: [`docs/logs/2026-07-01-builder-reference-plan-handoffs.md`](../logs/2026-07-01-builder-reference-plan-handoffs.md). ChatGPT literature lane still optional if recommendations return.

- **Repo organization (2026-06-30):** **shipped** (Option A — root `LATEST.md` renamed to [`SYNTHESIS-STATUS.md`](../../SYNTHESIS-STATUS.md)). Runbook + trail: [`docs/archive/inter-model/2026-06-30-org-planning/`](../archive/inter-model/2026-06-30-org-planning/). Log: [`docs/logs/2026-06-30-v4-execution.md`](../logs/2026-06-30-v4-execution.md).

- **Digest Phase 0 (2026-07-01):** **closed** (Run 6). Run 8 (2026-07-05): full digest + first `--propose` trial — auto-draft `dec_prop_20260705_152603_2c96` **rejected** (stale prod-gap line); pipeline validated; Ryan filing habit OK. Log: [`CROSS-PROJECT-DIGEST-PILOT.md`](CROSS-PROJECT-DIGEST-PILOT.md). Output: `~/.local/share/convmem/digests/2026-07-05.md`.

- **Background-synthesis status reconciliation (2026-07-14):** [`BUILT-PLANS-2026-06-24-to-2026-06-29.md`](BUILT-PLANS-2026-06-24-to-2026-06-29.md) now reflects Run 8, shipped P1c/inter-model indexing, and the active read-only weekly timer. Phase 2 remains held on agent-habit/value evidence and a recorded manual `link_queue.jsonl` review; timer-driven `--propose` remains Ryan-gated.

- **F1 semantic dedupe (2026-07-01):** **queue drained** — 10/10 pairs reviewed (`dec_prop_20260701_211650_5a62`); 9 Chroma tombstones applied via `convmem refine --approve-dedupe all`; 1 `rejected_keep_both`. CLI `--approve-dedupe` shipped in `refine.py`. Undo snapshots under `refine_undo/semantic_dedupe/`.

- **F1 backfill_domain acceptance (2026-07-01):** `convmem refine --once --job backfill_domain --limit 10` → **0 untagged** (corpus fully domain-tagged on visible units). MILESTONE-F manual gate **closed**.

- **Digest recency tighten (2026-07-02):** Run 7 — explicit recent-id ask injection + `## Recency check` in digest output. Log: [`CROSS-PROJECT-DIGEST-PILOT.md`](CROSS-PROJECT-DIGEST-PILOT.md) Run 7.

**Phase 1 gate:** **CLOSED.** Documents `13bf8547` PASS, linuxbrew `77a57494` PASS. Strict script + `--exclude Search` is the enforceable path for graded workspace_local smokes.

**Phase 2 gate — CLOSED (2026-06-29):** `f358d4f0` — `cn --auto` on Documents, PARTIAL ritual, v5 payload PASS (`inventory.total: 0`). **Qwen Continue verify lane complete.**

**Phase 2 (optional):** superseded — see Phase 2 section in [`CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md).

**Archive:** [`HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md`](HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md). Tarball removed during residue cleanup.

## State

- **Global protocol:** **Closed.** All active surfaces **PASS** alien soak + post-permissions retest (Ryan). See `SOAK-REPORT-2026-06-25.md`.
- **Gap-fix (pre-P2):** Deploy permissions verify, Crush session-close slice, Continue trim template, verification matrix, grader alien check — **shipped**. Ryan manual: Continue trim + Codex/blank-dir soaks.
- **Deployed:** Cursor `.mdc`, Kiro steering + `permissions.yaml` (incl. `echo *`), Crush Tier A + `crush.json` permissions + bash hook, Continue MCP `instructions=`.
- **Post-permissions retest (Ryan):** **Cursor PASS ×2**, **Kiro PASS**, **Crush PASS**, **Continue qwen3-coder:30b PASS** — no convmem permission prompts.
- **ChatGPT Tier C:** out of scope (ignored).
- **Corpus:** see `convmem brief` — do not trust counts here; run `doctor` before ask/search.
- **P2 gate:** still **hold** (MCP `unresolved` tool optional next).
- **Tests:** run `convmem brief --with-tests` or pytest when needed.

## Architecture diagram

```
flowchart TD
  canonical["config/agent-protocol.md\n(canonical SSoT)"]
  mcp["mcp_server.py\nloads MCP slice"]
  cursor["~/.cursor/rules/convmem.mdc"]
  codex["~/.codex/AGENTS.md"]
  kiro["~/.kiro/steering/convmem.md"]
  crush["~/.config/crush/rules/convmem.md"]
  continue["~/.continue/config.yaml rules"]
  chatgpt["docs/chatgpt-pack/\ncustom-instructions.txt"]
  recover["docs/RECOVER.md +\ndeploy script"]

  canonical --> mcp
  canonical --> cursor
  canonical --> codex
  canonical --> kiro
  canonical --> crush
  canonical --> continue
  canonical --> chatgpt
  canonical --> recover
```

## Decision

- Inter-model markdown = archive; **ledger + brief** = truth.
- **Change feed** (Codex): deferred until payoff review **2026-07-07**.
- **Crush tier:** Tier A (shell + MCP) — soak #8 showed MCP-only rules ignored; redeployed with shell ritual.
- **P2 gate held:** Do not accelerate. Fix surface coverage first, then re-evaluate MCP tools.

## Record a fact (two commands)

```bash
convmem record -i                  # draft (interactive)
convmem record --approve-last      # finish — indexes automatically
```

Kiro: add `--signer kiro-review`. Legacy CLI name: `propose_decision`.

## Session close (all models)

Read `docs/inter-model/SESSION-CLOSE-RECORD.md`. Output:

```bash
convmem record --relates-to <id> --summary "..." --rationale "..." --author ...
convmem record --approve-last
```

Search for `--relates-to` (never topic slugs). Fallback root: `dec_prop_20260623_161428_c311`.

### Close chain (newest first)

| Layer | Ledger id |
|-------|-----------|
| **Lab synthesis S1–S5 + prod port + dual verify** | `dec_prop_20260705_151004_1e00` (after Ryan record) |
| **F1 dedupe queue review + tombstone apply** | `dec_prop_20260701_211650_5a62` (review); apply record → see session close below |
| **Builder-reference plan execution** | `dec_prop_20260701_182803_987b` |
| **Phase 2 deployment (Crush slice + soak report)** | `dec_prop_20260625_233830_b9af` |
| **Continue+Crush alien-workspace fail: zero convmem** | `dec_prop_20260625_225404_11cf` |
| **Continue alien-workspace fail: pavlomassage-practice** | `dec_prop_20260625_223006_528c` |
| **Soak: alien-workspace spot-check logged** | `dec_prop_20260625_220647_47d9` |
| **Global protocol post-deploy soak** | `dec_prop_20260625_203408_f9b3` |
| **Thai Massage image darkening fix** | `dec_prop_20260623_215943_5abe` |
| **Docker/Podman stack fix** | `dec_prop_20260624_025115_862b` |
| **Protocol root (fallback)** | `dec_prop_20260623_161428_c311` |

**Rule:** chain under the **newest relevant** id from `search_fast`, not a ledger you only cited during a test.

## Next

- **Builder-reference:** execution **shipped** (2026-07-01). Use digests per `docs/builder-reference/notes/suggested-application-of-builder-material.md` before architecture edits.
- **F1 refine:** semantic dedupe queue **drained** (0 pending; 9 tombstoned). `semantic_dedupe` **out of daemon jobs** until corpus growth warrants re-queueing — review via `dedupe_queue.jsonl` + `--approve-dedupe`. Live config: `dedupe_similarity=0.92`, `queue_max_depth=200` (no change needed).
- **Digest:** Phase 1 automation + recency self-check (Run 7). Run 8 `--propose` trial **closed** — `2c96` rejected; prose/record filing habit OK (Ryan). Weekly timer install = host ops; linker product **held** on agent-habit gate.
- **Default:** `convmem doctor` → `brief` → `unresolved` (shell) or MCP `brief()` + `unresolved()` (MCP-only); `search_fast` before guessing.
- **Ryan manual:** See [VERIFICATION-MATRIX.md](VERIFICATION-MATRIX.md) — Continue `rules:` trim, Codex alien soak, blank-dir checks.
- **Change feed:** hold until **2026-07-07**.
- **P2:** MCP `unresolved()` tool **shipped** (Run 5) — parity with shell `convmem unresolved`. Gate **still held** on agent-habit / Phase 2 linker (`obs_806985bc5697`); not blocked on unresolved tool anymore.

### Optional close (Ryan — search for newer `--relates-to` first)

```bash
convmem record \
  --relates-to dec_prop_20260625_233830_b9af \
  --summary "Global convmem protocol: all surfaces PASS + gap-fix deploy" \
  --rationale "Cursor/Kiro/Crush/Continue qwen verified; permissions echo*; deploy verify shipped; P2 deferred." \
  --author ryan
convmem record --approve-last
```
