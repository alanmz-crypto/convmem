# Execution Plan — Post-#54 Backlog Clear

```text
Planning Status

Phase:        EXECUTION plan ready (strategy approved after blocking amendments)
Characters:   Cursor → GitHub Copilot audit lane → Kiro → Ryan → Copilot CLI operator (later, pending one-job R2a exception)
Lanes:        Cursor implements Phases A–D prep; Ryan merges and owns force-push; audit lane + Kiro exact-tip #52; Copilot CLI operator under pending one-job R2a exception (does not establish an execution lane or alter charter default routing)
Authority:    Binding strategy in this plan; charter TEAM-CHARTER-2026-07-06; R2a constraints CURSOR-2026-07-19-r2a-codex-pass-token-constraints.md; runbook EXECUTION-embedding-model-eval.md
Repo path when landed: docs/plans/EXECUTION-2026-07-20-post-54-backlog-clear.md
```

**Intended commit path:** land this EXECUTION text on the Phase A docs hygiene branch so operators have a repo-canonical copy. Until then, this plan file is the working SSoT.

## Accepted gates

- R2a is not Gate 2; handoff is Authorization R2a `config_generation` only
- Two arm-specific Ryan authorization packets (baseline + challenger)
- One-job Copilot CLI exception stays **pending** until Ryan records packets that grant exception + execution together
- Phase D is a separate merged docs PR from post-#52 `main` after tree-identity proof
- Agents never force-push; preserve untracked `.kilo/` and `login` (no stash)
- Restic waiver only if doctor FAIL (current premise: PASS)
- #54: merge verified; Cursor/Kiro surfaces match; Copilot CLI/Codex `AGENTS.md` retains three trailing digest lines
- #42 remains Ryan decision (not auto-closed)

## Locked defaults (no mid-flight choice)

- **Git update path: B (non-rewriting)** for #56, #57, and #52: `gh pr update-branch` or merge `origin/main` into the PR branch (merge commit). If Path B fails or GitHub refuses, **stop** and hand to Ryan for Path A (rebase + force-push with lease) or Path C (replacement branch). Cursor does not force-push.
- **No live R2a / eval-root / R2b+ / Gate 2** in Phases A–D Cursor work
- **Hermetic (for restic waiver scope, if needed):** unit/integration tests under `.venv`, docs/markdown edits, branch maintenance (fetch, switch, Path B update-branch/merge-main, conflict resolution, push of non-rewritten tips). Includes Phase C’s authorization implementation code edits and test runs. Excludes: live data writes, eval-root mutations, corpus ingest, deploy-agent-protocol, recovery-sensitive writes, `record --approve-last`, `add --upsert`.

## Stage 0 — prerequisites

1. Ryan accepts this EXECUTION plan.
2. Leave stale #54 docs branch; `git fetch origin`; `git switch main`; `git pull --ff-only`.
3. Ritual: `convmem doctor` → `brief` → `unresolved`.
   - If `restic_gate` PASS: proceed with no waiver.
   - If `restic_gate` FAIL: stop for refresh, or record explicit narrow waiver using the hermetic definition above.
4. Confirm untracked `.kilo/` and `login` remain; do not stash.
5. Single active writer: use `--worktree` if contested.

## Phase A — restore LATEST truth

**Owner:** Cursor. **Merge:** Ryan.

1. `convmem work start docs 2026-07-20-post-54-latest-hygiene`.
2. Edit [`docs/inter-model/LATEST.md`](docs/inter-model/LATEST.md):
   - #54 merge verified; charter active
   - Deploy qualification: Cursor/Kiro match tip; Copilot CLI/Codex three trailing digest lines (not a blocker)
   - Remove deploy-blocked / awaiting-review language for #54
   - #52 open/conflicted; authorization implementation; awaiting exact-tip reviews
   - R2a not authorized; Copilot CLI one-job exception **pending**
3. Land repo copy: [`docs/plans/EXECUTION-2026-07-20-post-54-backlog-clear.md`](docs/plans/EXECUTION-2026-07-20-post-54-backlog-clear.md) (content match to this plan).
4. Push explicit refspec; open PR; CI; **Ryan merges**.

**Evidence:** hygiene PR URL; merge SHA; LATEST no longer claims #54 blocked.

## Phase B — retrieval leftovers

**Owner:** Cursor (Path B). **Merge:** Ryan.

1. On [PR #56](https://github.com/alanmz-crypto/convmem/pull/56): Path B update onto current `main`; wait CI on **new** head; Ryan merges.
2. On [PR #57](https://github.com/alanmz-crypto/convmem/pull/57): same. No ranking-logic changes.

**Evidence:** For each PR, record the updated head SHA and CI result; after Ryan merges it, record the merge SHA.

## Phase C — land R2a authorization implementation (#52)

**Owner:** Cursor integrates (Path B); **GitHub Copilot audit lane** + **Kiro** exact-tip review; **Ryan** squash-merges.

### C1 — integrate

1. Resume `feat/2026-07-19-r2a-auth-schema` (worktree if needed).
2. Path B: merge `origin/main` (post-#56/#57) into the PR branch. No force-push. If Path B fails, stop for Ryan Path A or C.
3. Resolve conflicts from **current main** inspection:
   - `LATEST.md`: post–Phase A main wins
   - `EXECUTION-embedding-model-eval.md`: **Judge: Ryan or Kiro.** Cursor does not decide “still-valid” R2a amendments alone. Cursor stages both sides of the conflict and stops for Ryan/Kiro to pick which #52 amendments remain. Criteria Ryan/Kiro use: keep amendments that implement the post-FAIL security properties listed in C1 step 4; drop amendments that reintroduce stale status language, Gate 2 conflation, or weaken global `REQUIRED_REAL_FIELDS`.
4. Preserve post-FAIL security properties (verify in files, not from memory):
   - Binder-only immutable capability
   - Bindings re-derived from approved manifest
   - Original sidecar revalidated at write time
   - Exact path match
   - Caller-supplied live config rejected
   - Approved `live_config` from manifest
   - Gate 1 pin `3b2790f50414f0445c35748e52f849c6276839f7`
   - Codex PASS constraints in `CURSOR-2026-07-19-r2a-codex-pass-token-constraints.md`

### C2 — exact-tip gate (same literal head SHA)

Pre-update reviews do not carry forward. On final published tip:

- `pytest tests/test_eval_r2a_auth_schema.py`
- Related manifest/sidecar/shadow-config tests
- Full pytest suite
- Pylint regression gate PASS
- `git diff --check` clean
- GitHub CI green on that head
- **GitHub Copilot audit lane** written PASS quoting **literal head SHA**
- **Kiro** written PASS quoting **same literal head SHA**
- No unresolved review threads

Record: `main` base SHA; reviewed #52 head SHA.

### C3 — merge and tree identity

1. Ryan squash-merges #52.
2. Record squash-merge SHA on `main`.
3. Prove `reviewed_head^{tree} == merge_commit^{tree}`. Tree identity proves **content** identity, not commit identity. If trees differ, stop — do not bind Phase D.
4. Close #51 as superseded by #52 only after merge.

**Evidence:** review quotes with SHAs; CI URL; tree identity command output; #51 closed.

## Phase D — Copilot CLI handoff (separate docs PR)

**Owner:** Cursor authors; Ryan merges; **execution later** by Copilot CLI operator under a pending one-job R2a exception. This does not establish an execution lane or alter the charter's default routing.

1. FF `main` to #52 squash-merge SHA.
2. `convmem work start docs 2026-07-20-r2a-config-generation-handoff`.
3. Create `docs/inter-model/CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md` containing:
   - Role split: GitHub Copilot audit lane (Phase C) vs Copilot CLI operator under a pending one-job R2a exception (Phase D). This does not establish an execution lane or alter the charter's default routing.
   - Exception **pending** until Ryan packets (template text for Ryan to grant; Cursor does not assert approval)
   - Executable scope: Create each approved `out_dir`, write its `shadow.toml`, and bind the approved future `chroma_dir` path. Creation of the Chroma storage directories is not part of this authorization.
   - Exclusions: R2b, B-Accept, C0, R3–R7, Gate 2, promotion, cleanup
   - **Two packet templates** (baseline + challenger), each requiring:

```text
manifest_path:
manifest_file_sha256:
approved_manifest_body_sha256:
approval_sidecar_path:
approval_sidecar_expected_contents:
authorization_phase: r2a
execution_mode: real
status: approved
operations: [config_generation]
merged_harness_sha256: 3b2790f50414f0445c35748e52f849c6276839f7
service_policy:
prohibited_actions:
live_config:
out_dir:
chroma_dir:          # path binding only — existence not required by R2a
embed_model:
embed_host:
allowed_directories:
exact_command_tuple:
authorized_revision:   # #52 squash-merge SHA after tree identity
```

   - Partial-failure: no retry/cleanup/overwrite without new auth; preserve inventories/artifacts; stop for Ryan/Kiro
   - Procedural controls: approved command path only; pre/post read-only inventory of `out_dir/` and `out_dir/shadow.toml` for both arms (do **not** require `chroma_dir` to exist); diff; stop on unexpected paths; note procedural if shell unrestricted
   - Independent post-run verify: **Kiro** (not Copilot CLI self-audit)
4. Point `LATEST.md` at this handoff; exception still pending.
5. Open PR from post-#52 `main`; Ryan merges.

**Continuity rule:** Do not soft-close or hand back between the #52 merge and the Phase D status/handoff PR. If Phase D cannot proceed immediately, open a minimal status-only PR so `LATEST.md` does not continue reporting #52 as open/conflicted.

**Hard stop:** zero eval-root mutations in Phases A–D.

## Partial-failure rules (binding for later Copilot CLI)

- Fail mid-arm → stop; preserve inventories/artifacts
- No retry, cleanup, or overwrite without **new** Ryan authorization
- Sibling arm: if shared state contaminated, do not start; if fully isolated, still require Ryan confirmation after sibling failure

## Nonbinding ops checklist (not in R2a handoff)

- Restic: action only on doctor FAIL
- staging2 CSP/HSTS/Referrer: WP/SiteGround
- Stale PRs #37 #36 #34 #33 #32 #6: later disposition
- #42 mcp bump: **Ryan decision required**

## Verification card (Cursor handback)

- Doctor recorded; restic PASS or conditional FAIL handling
- #54 qualified correctly in LATEST (merge verified; Cursor/Kiro match; Copilot CLI/Codex three trailing digest lines)
- #56/#57 merged via Path B (or Ryan Path A/C noted)
- #52: reviewed head SHA; GitHub Copilot audit lane + Kiro PASS quote that SHA; CI green
- Squash-merge SHA + tree identity proof (content identity, not commit identity)
- #51 closed after #52
- Phase D docs PR merged; exception pending; two packet templates; partial-fail rules
- Zero eval-root mutations; `.kilo/`/`login` undisturbed
- Track A at soft close; no `record` unless Ryan asks

## Out of scope (separate future authorizations)

R2b capture; B-Accept; C0; R3–R7; Gate 2 evidence review; promotion; cleanup; live eval-root writes before Ryan packets.

## Soft close

Track A index of this Cursor transcript. No durable record block unless Ryan requests.

**Do not soft-close or hand back between the #52 merge and the Phase D status/handoff PR.** If Phase D cannot proceed immediately, open a minimal status-only PR so `LATEST.md` does not continue reporting #52 as open/conflicted.
