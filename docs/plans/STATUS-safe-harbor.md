# Arc Brief — Safe Harbor

> **Arc: Safe Harbor. T1 MERGED; T2 TARGET-BINDING CORRECTION GRANTED.** Draft PR #389 was reviewed at `0cff1578b881d890234adad6b9cb93a110ec1d48`. Codex found a post-preflight alias-retarget gap (90%, static); Ryan authorized its bounded correction and isolated evidence. CodeQL alert #6 is dismissed as a false positive. The correction is NOT_STARTED; Cursor's current handoff is in execution section 9. No further paid reviewer request, T2 acceptance, merge, T3–T5 or live operation is granted.

## 1. What This Is For (product goal)

Make ConvMem's recovery and incident handling remain dependable across agents, processes and time. Durability is first; convenience is second. The requirements are: no verified recovery point before risky change means no change; unexpected results stop the affected operation for investigation; production is never repaired blindly.

The accepted direction uses existing Rescuezilla/Restic backups and the existing guarded Chroma quarantine, with stronger target binding, unknown-state handling, evidence preservation and validated release. It does not promise universal write prevention.

## 2. System Design (how the pieces connect)

```text
exact recovery artifact + scoped qualification + Ryan operation grant
                         |
              resolved operation target/profile
                         |
              existing recovery/write preflight
                         |
         existing native lock + quarantine admission
               /                         \
     admitted bounded operation       unresolved incident
                                          |
                              preserve before replacement
                                          |
                          validate/dispose under same lock
                                          |
                            explicit authorized release

doctor / audit result / events = observations and history
QUARANTINE.json = all unresolved incidents for guarded Chroma writes
```

The scope is application cooperation, not same-user security. Read clients can perform incidental writes; direct clients, other durable-state publishers and shell/service tools do not all pass this guard.

## 3. What Exists Right Now (file map)

- **Current T2 delivery:** draft [PR #389](https://github.com/alanmz-crypto/convmem/pull/389), reviewed source `0cff1578b881d890234adad6b9cb93a110ec1d48` (runtime/tests `964c1de`), on the existing T2 branch/worktree below. Its pytest/pylint/secret-scan/CodeQL checks passed after the authorized dismissal of alert #6. These checks belong to that source, not to the unimplemented correction.
- **Active correction:** [Target-binding correction — owner authorized](EXECUTION-safe-harbor.md#target-binding-correction--owner-authorized). Preflight canonicalizes targets, but the retained config still contains alias spellings and the writer resolves them again. Config/env byte-edit refusal does not detect alias retargeting; initial path containment does not establish immutable target binding. Codex's static finding is recorded in VERIFY; reproduction and correction evidence are not yet run.
- **External review:** the single authorized BugBot request on #389 hit a usage limit and reviewed no SHA. No PR-native Copilot review was requested; Ryan subsequently asked to avoid Copilot for budget reasons. Earlier full/delta reviews remain historical evidence. No T2 tip-specific outage acceptance is recorded.
- `ARCHITECTURE-safe-harbor.md`: direction approved by Ryan at `5ea16a6c7af7900b981d19eb03b168d77f611718`, following Opus delta PASS at `505a4224b5c078a2379ebe16444ca757cc69b7db` (85%) and Kiro governing PASS at the approved revision (88%). Approval includes owner disposition after every automatic segment restore. Subsequent edits record approval, naming and review routing; the approved contracts are unchanged.
- E4 review: Kiro's PASS (85%) at `20283bdc536f9f2d9ccf7c44a75a17f5a26e1d61` is confirmed for the full intended scope by its coverage addendum at `1268a500d7ac8f4a94f816d90817e21ad8e2c342`. Ownership is unchanged. Architecture section 10 preserves B-E4.1/O-E4.a–e and Codex's two qualifications: the probe disables current-day checking, and the approved contract adds approval recovery to the existing preflight rather than selecting a separate check.
- `STATUS-safe-harbor.md`: this current-state brief; required arc lists and routing point here.
- `EXECUTION-safe-harbor.md`: five-task plan reviewed PASS at `00c69d2` (85%), followed by Kiro delta PASS at `dca13a5` (88%), and accepted by Ryan at that successor. Section 7 records B-E4.1/all five consumer outcomes. Section 8 preserves the completed T1 grants; section 9 records the separate T2 grant and pinned Cursor handoff. T2 is implemented on its task branch; T3–T5 are not implemented.
- T2 implementation: **on branch** `fix/2026-10-12-safe-harbor-t2` (worktree `/home/lauer/Projects/convmem/.worktrees/fix-2026-10-12-safe-harbor-t2`), start `9664878`, initial source `44e29f6d943c98a2425c21901c310c52ca5c5b1a`, corrected runtime/tests `964c1decb1a8366226ad45345ae26ed909542569`. `add --upsert`, indexed `record --approve-last`/`--approve` and `propose_decision --recover` now pass one operation-bound preflight (`chroma_write_store.admitted_write_operation` → `restic_gate.preflight_operation`): explicit v2 profile, target/affected-path containment, post-admission edit refusal, refused production skip, and B-E4.1 future-time 25 across all five consumers. ROADMAP/RECOVER/role-mapping and the v2 exit-25 row are updated. Shadow inventory unchanged; R2b inventory regenerated (derived only). Not merged, not deployed.
- T2 review: original Copilot static **FAIL, narrow (75%)** remains pinned to `05c7706e54b77f9ef5b41a1c206b29bec012e405`. The only blocker, B1 (recovery label rejected by an armed census), is **closed by Copilot delta PASS (88%) at `82f25efb4696325afa83298fae0e1ca698f1d7fe`**. No new blocker; no tests rerun by the reviewer. Non-blocking advisories and the evidence exclusion remain in VERIFY V2. This is not BugBot evidence or overall V2 acceptance.
- T2 B1 correction: **implemented at `964c1decb1a8366226ad45345ae26ed909542569`** (code/tests; reviewed in the docs-only successor `82f25ef`).
  - Change: recovery admission reuses `propose_decision.write`. The only production edit is `convmem.py`; the census allowlist, routes and hashing are unchanged.
  - Derived R2b identity: `05362dba…`; the shadow inventory is byte-unchanged.
  - Tests: armed-census positive (new unit plus matching APPROVED, census open/close recorded), future snapshot (25; census telemetry recorded, logical state unchanged), and a test-only old-label control (actual census refusal; the positive assertions fail).
  - Uid-1000 isolated runs: 153 affected cases passed (including the 3 new cases) with pytest exit 0; lint gate exit 0 (466 findings, none new).
- T2 evidence (VERIFY V2):
  - Codex's captured uid-1000 runs at runtime `44e29f6`: 236 distinct cases (focused `133 passed` + regression `103 passed`), pytest exit 0 for both; lint gate exit 0 (pylint raw 30).
  - Refresh at tests `2459acd`: the 64 affected T2/caller cases passed again (pytest exit 0; overlapping, not additional); lint gate exit 0 (465 findings, none new).
  - Fixture `2459acd` (tests only) builds the event-only recovery state by interrupting a real indexed approval. It proves future refusal with state unchanged and the existing human-review outcome after admission.
  - Also recorded: AST equality `262573e`→`44e29f6`, inventory proofs, and earlier failed or uncaptured runs as history.
- Event-only evidence gap: no event-only completion success control. The current ingestion hash view (summary-derived `title`, empty `notes`/`result`) disagrees with the proposal hash view (those fields absent), so the `approve` recovery branch is not reachable on this path. Copilot classifies this as a pre-existing T4 prerequisite, not its T2 runtime blocker. Ryan accepted that V2 evidence excludes successful event-only completion; this is not overall V2 acceptance. T4 must align the views and prove that success under its later grant. Sources are cited in VERIFY V2. Direct helper callers also remain ungated (T4 seam).
- T1 implementation: **on `main` via PR #387**, squash commit `05aa2c86e2d01c9a9f5259b1f505833d7f28563d`. Its tree is identical to the reviewed candidate `0c7b4e263dff12f8e1a6b2d485616153ed096b66`. The former implementation branch/worktree is historical; do not resume its completed grant or switch the shared checkout/runtime-main.
- `VERIFY-safe-harbor.md`: records the T1 evidence chain, final-tip CI/review, Ryan's exact-tip outage acceptance and squash mapping (GitHub pytest at the T1 candidate: 2970 passed, 75 skipped). V2 holds T2 source identity, captured final evidence and the open event-only limitation; V3–V6 remain NOT RUN.
- Deployed runtime: `.worktrees/runtime-main` at `a92a74eb326b3eaa59087b707de10153c7cc0c63` when checked on resume. Installed launcher still points there.
- Planning base: `6a23aa93184460ed853996608bb28190c61f8d89`. It contains the detector; it is not the deployed release.
- Existing code: `restic_gate.py`, `backup_workflows.py`, `restic_snapshot.py`, `chroma_write_guard.py`, `propose_decision.py` and `doctor.py`. Known contract gaps and pinned source evidence are in architecture section 3.
- Detector candidate: CPU/vector-loss PR #341, exact `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`. Deployment is a separate Ryan decision; no watch start or broad catch-up is implied.
- Backup access during execution-plan drafting on 2026-10-11: required doctor exited 0; local snapshot, external lineage copy and matching offline password copy passed. This is access/freshness evidence, not demonstrated restoration; CLI read paths may perform bookkeeping writes.
- Fresh Rescuezilla image: completion, identifier, scope and destination not yet confirmed. The reported September 16 pre-incident image should be preserved.
- Additional backup destination: Ryan supplied `/run/media/lauer/ext-ex4-1T-NVMe/`; read-only mount/capacity inspection confirmed ext4 and available space. Execution section 6 records UUID/capacity and proposes a fresh-image destination. No drive write, backup allocation or qualification was performed.
- Safe Harbor T1 retains unresolved incidents, aligns canonical client/cache identity and refuses persisted-empty authority. Ordinary clear cannot release incidents; the validated-release workflow is still T3. Old writers can overwrite or clear the marker, so the T1 merge does not make it independently deployable. No deployment was performed by this work.

## 4. Completion State

- Review synthesis and pre-reboot checkpoint: preserved at `bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1` on the separate checkpoint branch.
- Architecture direction: **APPROVED at `5ea16a6`**, existing backups and strengthened admission/incident contracts; seven planning obligations remain in architecture section 8.
- Arc name: **CONFIRMED — Safe Harbor** by Ryan.
- Opus review/delta: **COMPLETE — DELTA PASS at `505a422` (85%)**. Both blockers resolved; E1–E7 accepted as planning obligations. Opus explicitly required no further round for its exact E7 clarification, now included.
- Kiro governing design sign-off: **PASS at `5ea16a6` (88%)**, no direction blockers; relayed by Ryan in this conversation.
- E4 backup-interface review: **COMPLETE — FULL-SCOPE PASS (85%)**, confirmed by Kiro's addendum at `1268a50`. No ownership transfer. Its B-E4.1/O-E4.a–e obligations were carried into the now-accepted execution plan; source/contract qualifications remain in architecture section 10. E4 compatibility alone did not approve the detailed change; Ryan's later owner approval is recorded separately below.
- Ryan direction approval: **APPROVED at `5ea16a6`**, explicitly including disposition after every automatic segment restore.
- Execution Planning: **COMPLETE — RYAN ACCEPTED `dca13a59a2edf649ac6a19777f572645bea8674e`** after Kiro delta PASS (88%); initial PASS remains pinned to `00c69d2` (85%). A1/A2 and O-E4.e are satisfied plan-side. No required review correction remains.
- **B-E4.1 owner disposition: APPROVED**, by Ryan explicitly as owner, exactly T2 at the accepted revision including all five consumer outcomes. Ownership is unchanged; this is contract approval, not implementation or live activation.
- **T1: MERGED** by Ryan in PR #387 at `05aa2c8`. The final candidate `0c7b4e2` passed fresh CI; the initial full Copilot audit and successive correction/integration reviews cover the delivered candidate. Final integration delta: PASS 82%, static.
- **External review gate: SATISFIED BY RYAN'S EXACT-TIP OUTAGE ACCEPTANCE** for `0c7b4e263dff12f8e1a6b2d485616153ed096b66`. BugBot reviewed no SHA; this is not a BugBot PASS. Exact owner wording and evidence are in VERIFY V0/final acceptance.
- **PR #387: MERGED**, 2026-10-12 05:13:16 UTC. No open T1 correction or review action remains from this delivery.
- **T2: B1 CLOSED; ALIAS TARGET-BINDING CORRECTION GRANTED / NOT_STARTED; V2 NOT ACCEPTED.**
  - Runtime/tests `964c1de` have captured isolated evidence: 153 affected cases passed, including 3 new census controls; lint regression gate PASS.
  - Copilot delta **PASS (88%)** at final candidate `82f25ef` closes B1. Original FAIL remains pinned to `05c7706`; the review is static and supplies no new runtime or CI evidence. This documentation record does not transfer exact-tip review to a later successor.
  - Ryan accepted the event-only success evidence exclusion only; T4 hash normalization/success and direct-caller proof remain unperformed.
  - No T2 PR-native BugBot evidence or exact-tip outage acceptance exists; T1's exception does not transfer.
- **PR #389: OPEN / DRAFT.** The authorized one-shot BugBot trigger returned a usage-limit reply, with no reviewed SHA. CodeQL alert #6 was owner-authorized and dismissed as false positive at `2026-10-12T10:34:24Z`; GitHub then reported CodeQL SUCCESS at `0cff157`. No paid retry/reviewer is requested.
- **Current grant:** Cursor may implement only the bounded target-binding correction and isolated evidence in execution section 9, updating the existing draft via normal branch pushes. Fresh CI and a Codex delta follow; neither substitutes automatically for final-tip external-review acceptance.
- T3–T5 implementation, new review triggers/comments, merge and live operations/deployment: **NOT AUTHORIZED**. No phase auto-advance.

## 5. Your Role (read this to know what you're here to do)

**Codex:** The alias-retarget finding and Ryan's correction grant are recorded; CodeQL alert #6 is dispositioned. Hand Cursor the pushed grant successor, then review only the delivered correction and regressions. No paid reviewer request and no automatic external-gate waiver.

**Cursor:** Resume the existing T2 worktree at Codex's pushed grant successor. Reproduce and correct post-preflight alias target drift, capture isolated regression/control evidence, update the existing records and push. Keep #389 draft. No hash/classifier repair, census policy expansion, unrelated advisories, T3/T4 or production work.

**Ryan:** The correction and CodeQL disposition are authorized. After correction evidence and the bounded Codex delta, decide final-tip external-review disposition and overall V2 acceptance. The existing event-only evidence exclusion is already accepted; T1's outage acceptance does not carry over.

**Kiro / Opus / Copilot:** Existing approvals remain pinned. Copilot closed B1 at `82f25ef` (88%, static delta), following its full review at `05c7706`. No new paid round is authorized or requested, including after this correction.

**Ops:** No live grant from this arc; T1 is not independently deployable.

## 6. What Remains Before "Live" (sequential)

1. Complete the granted T2 alias target-binding correction and its isolated effect/control evidence on draft #389. Then obtain fresh CI, the bounded Codex delta, final-tip external-review disposition and owner acceptance/merge decision. B1 is closed historically; the event-only evidence exclusion stays accepted. CodeQL alert #6 is dispositioned, not evidence that the runtime correction is complete.
2. Complete T3–T5 only under their task grants, including:
   - T3's backend-proof ordering gate and preservation/validated release;
   - T4 approval recovery: gating or binding direct helper callers, aligning the proposal and ingestion hash views so an event-only completion can be proven, and unknown/tombstone/race/uncertain-completion handling;
   - integrated evidence.

   V3–V6 remain NOT RUN.
3. Rollout prerequisite added by T2: production `restic.env` must declare an explicit `complete-data-v2` profile and data root covering every affected path, or gated writes refuse with 20/24.
4. Before live rollout, resolve the loss window and exact recovery-artifact qualification, old-process/guard-state adoption and rollback compatibility in execution section 6. The additional drive is a candidate resource, not completed protection.
5. Any deployment or corpus-affecting operation requires its own scope, recovery evidence and Ryan grant. T1 alone is not a release workflow; the standalone detector remains a separate decision.

## 7. Hard Stops (models cannot cross)

- The active T2 grant permits only its scoped implementation source and isolated fixtures/evidence in its worktree. No installed runtime, production data, service, backup-repository, key, retention or installed-permission changes.
- No restore drills, production experiments, indexing, ledger record or merge from this brief.
- No Recovery Authority T4/V4k, v3 authority/serving activation, migration or generalized repair. Read that arc's current STATUS hard stops.
- No generic HOLD, identity registry, freeze, broad constructor change or automatic cleanup subsystem under this direction.
- No claim that gate PASS proves recovery, that zero missing vector IDs proves semantic integrity, or that quarantine covers arbitrary same-user writers.
- No automatic phase transition. A published or merged architecture is not execution or deployment authorization.

## 8. Relationship to ConvMem (the bigger picture)

Safe Harbor proposes stricter contracts around existing local guard and approval-recovery paths. Complete-data Backup v2 still owns its resolver, eligibility/gate interfaces, snapshot/restore profile and open Hybrid consistency audit; Recovery Authority still owns provenance-aware recovery and its T4/V4k dependencies. Other run-ledger, generation and permission surfaces retain their own owners.

The architecture records these interfaces and refuses to claim a global freeze. It does not change those other arcs' statuses or silently finish their deferred work.

## 9. Key Design Files (for deep dives)

- [Safe Harbor architecture](ARCHITECTURE-safe-harbor.md): proposed direction, evidence, risks and reviewer assignment.
- [Execution plan](EXECUTION-safe-harbor.md): five bounded tasks, interface proposal, proof requirements and new-drive operational limits.
- [VERIFY companion](VERIFY-safe-harbor.md): T1 acceptance, T2 captured evidence/review findings and pending V3–V6.
- [Reboot checkpoint](https://github.com/alanmz-crypto/convmem/blob/bc3a6fd34bc594024d53fb86c9ca6b312cb64bd1/docs/inter-model/CODEX-2026-10-11-durability-reboot-checkpoint.md): review provenance and saved pre-reboot state.
- [Recovery Authority STATUS](STATUS-recovery-authority.md): ownership and hard stops.
- [Complete-data Backup v2 STATUS](STATUS-complete-data-backup-correction-v2.md): existing profile/restore contract and open consistency audit.
- [Team charter](../inter-model/TEAM-CHARTER-2026-07-06.md) and [decision/review guardrails](../inter-model/DECISION-REVIEW-GUARDRAILS.md): authority and review discipline.
- [Execution Planning guide](../planning/EXECUTION-PLANNING.md): active phase and stop condition.

## 10. How to Update This Brief (departure protocol)

Overwrite sections 3–6 when the actual state changes. Keep runtime observations dated and scoped; do not turn them into permanent green guarantees. Other orientation surfaces should point here instead of duplicating mutable milestones. Add one milestone-level update line; keep detailed review discussion in the architecture or review artifact. If Ryan renames the arc, rename the matching files and their pointers together.

## Update Log

- 2026-10-12 — Codex: recorded the owner-granted alias target-binding correction and Cursor handoff; reconciled draft #389/BugBot quota status and dismissed CodeQL #6 as an authorized false positive. Correction evidence and T2 acceptance remain pending.

- 2026-10-12 — Codex: recorded Copilot B1 delta PASS at exact candidate `82f25ef` (88%), corrected runtime/review SHA shorthand and retained the accepted event-only exclusion; V2 acceptance and the separate PR-native gate remain pending.

- 2026-10-12 — Cursor: implemented B1 at `964c1de` (recovery reuses the allowlisted writer label; R2b identity derived-only) and recorded armed-census uid-1000 evidence (3 new and 153 affected passed, lint gate PASS). Narrow Copilot delta is next; V2 not accepted.
- 2026-10-12 — Codex: recorded Ryan's bounded B1 correction grant and event-only evidence exclusion; prepared Cursor's scoped continuation with isolated census-present positive/refusal/control evidence.

- 2026-10-12 — Codex: recorded Copilot's exact-tip T2 narrow FAIL at `05c7706`, confirmed B1 and routed the bounded correction plus explicit event-only evidence-limit decision; runtime unchanged.

- 2026-10-12 — Codex: reconciled execution-plan current-state pointers with the delivered T2 candidate; isolated evidence is recorded, with the event-only completion limitation and review/acceptance still open.
- 2026-10-12 — Cursor: recorded Codex's refresh at tests `2459acd` (64 affected cases re-passed, exit 0; lint gate PASS). T2 implementation and evidence are delivered; event-only completion stays an open T4 limitation. Review and acceptance are next.
- 2026-10-12 — Cursor: recorded Codex's captured final runs at `44e29f6` (133/103 passed, exit 0; lint gate PASS). The event-only fixture now uses a real interrupted approval (`2459acd`), exposing the hash-view mismatch as a T4 prerequisite. Fixture refresh, V2 acceptance and review are pending.
- 2026-10-12 — Cursor: implemented T2 (final source `44e29f6`), updated policy docs and recorded isolated V2 evidence; final uid-1000 pytest/pylint status pending Codex, then external review/Ryan acceptance. T4 direct-caller proof outstanding.
- 2026-10-12 — Codex: recorded Ryan's separate T2 grant and prepared the pinned Cursor handoff/worktree; implementation and V2 not started, T3–T5/live work ungranted.

- 2026-10-12 — Codex: recorded final-tip CI/Copilot evidence, Ryan's exact-tip BugBot outage acceptance and T1 squash merge #387 at `05aa2c8`; T2 grant and all live work remain pending.

- 2026-10-11 — Codex: recorded Copilot delta PASS at `2977c45` and Ryan's bounded main-integration/inventory-refresh grant; fresh CI and final-tip review follow, with no PR merge or live grant.
- 2026-10-11 — Cursor: merged main `5550def` into the T1 branch at `c624e2f`, regenerated the inventory (`87b8144d…`) and recorded isolated integration evidence (63/45 passed); fresh CI, final-tip review, BugBot gate and T1 acceptance remain pending.

- 2026-10-11 — Codex: resumed from the GitHub checkpoint and authored the provisional Safe Harbor direction/brief; independent review and Ryan approval remain pending.
- 2026-10-11 — Codex: corrected Opus's two first-review blockers and recorded E1–E7; exact-revision delta review is next, with Kiro sign-off and Ryan approval still pending.
- 2026-10-11 — Codex: recorded Opus delta PASS at `505a422` and added its exact E7 disposition clause; Kiro governing review is next, with Ryan approval pending.
- 2026-10-11 — Codex: recorded Kiro governing PASS at `5ea16a6` (88%); Ryan's direction decision and E4 remain open, with no execution-planning or live-action grant.
- 2026-10-11 — Codex: recorded Ryan's approval at `5ea16a6` and confirmed Safe Harbor; targeted Kiro E4 prompt prepared, with execution planning explicitly pending.
- 2026-10-11 — Codex: recorded Kiro E4 PASS at `20283bd` (85%) and carried its obligations; truncated-prompt coverage clarification requested, execution planning still pending.
- 2026-10-11 — Codex: recorded Kiro's full-scope E4 PASS addendum at `1268a50` (85%), O-E4.d/e and two source/contract qualifications; Ryan's execution-planning decision is next.
- 2026-10-11 — Codex: recorded Ryan's drafting grant, authored five-task EXECUTION and unrun VERIFY stub, and inspected the added ext4 destination; plan/v2 review and acceptance are next, implementation/live operations pending.
- 2026-10-11 — Codex: at Ryan's request, clarified uncertain approval-event completion and its unrun evidence cases; saved Kiro's focused execution-review prompt. Review/acceptance and all execution remain pending.
- 2026-10-11 — Codex: recorded Kiro's execution PASS at `00c69d2` (85%) and O-E4.e satisfaction; incorporated A1/A2, qualified the audit source claim, and retained the v2-owner/acceptance gates with no execution grant.
- 2026-10-11 — Codex: recorded Kiro delta PASS at `dca13a5` (88%), closed the review cadence without contract changes, and routed B-E4.1 to owner disposition before Ryan's plan acceptance; execution remains pending.
- 2026-10-11 — Codex: recorded Ryan's explicit B-E4.1 owner approval and acceptance of the plan at `dca13a5`, including all five consumer outcomes; ownership unchanged, implementation/live operations pending.
- 2026-10-11 — Codex: recorded Ryan's T1-only grant and prepared the bounded Cursor Execute handoff/isolated branch; implementation not started, evidence unrun, later tasks/live operations pending.
- 2026-10-11 — Cursor: implemented T1 on `fix/2026-10-11-safe-harbor-t1` at runtime `fa82028` and recorded isolated V1; exact-tip review, T2–T5, and live operations remain pending.

- 2026-10-11 — Codex: recorded Ryan's bounded T1 correction grant; store-file scope addition, persisted-empty refusal and actual overwrite control are authorized, with correction evidence/review pending.
- 2026-10-11 — Cursor: corrected T1 on `fix/2026-10-11-safe-harbor-t1` at runtime `496792f` and recorded isolated V1 (43 passed); exact-tip review, T2–T5, and live operations remain pending.
- 2026-10-11 — Cursor: merged main `db8aebb`, made T1 tests self-isolating under standard pytest, and regenerated the writer-coverage inventory to `43a3944d`; BugBot was not re-triggered.
- 2026-10-11 — Codex: recorded green CI and Copilot static PASS at `677c8a0`, both quota-blocked BugBot attempts, and Ryan's two-test correction grant; Cursor correction and successor evidence/review are next.
- 2026-10-11 — Cursor: implemented the isolation-cleanup and audit/writer-contention test corrections at `8b41044` (runtime unchanged) and recorded isolated evidence with failing controls; successor CI/delta review, BugBot gate and T1 acceptance remain pending.

## TL;DR

[Arc Safe Harbor] T1 is merged; T2 is on draft #389. B1 is closed by historical Copilot delta PASS. Ryan authorized Cursor's new alias target-binding correction and isolated evidence; resume from the pushed handoff successor. CodeQL #6 is dismissed as a false positive. No further paid reviewer request. Correction evidence/CI, final-tip review disposition and V2 acceptance are pending; T3–T5, merge and live operations remain ungranted.
