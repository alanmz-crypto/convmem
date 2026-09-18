# Implementation Handoff: Review-gate enforcement — willowyhollow vs. convmem vs. proposed target

**Date:** 2026-09-18
**Author:** Claude (ad-hoc review, no named arc)
**For:** Codex (architecture / execution planning)
**Authorization:** Ryan, 2026-09-18 (verbal in-session: "create a handoff for codex to compare your ideal system with our convmem setup and the willowyhollow setuppp")

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `NOT_STARTED` |
| **Branch** | `docs/2026-09-18-willowyhollow-review-gate-comparison` |
| **Tip SHA** | (this commit — see `git log -1`) |
| **Push status** | pushed to origin (via `convmem work start docs ... --worktree`) |
| **PR** | not opened |
| **Ryan GATE** | Codex's output is a *plan*, not a change — no ruleset, branch-protection, or CI file may be edited without a separate Ryan authorization naming the exact repo, ruleset field, and new value |
| **Track A ingest** | No adapter exists for native Claude Code `.jsonl` transcripts yet (confirmed this session — `convmem index --file` on `~/.claude/projects/-home-lauer-WordPress/*.jsonl` fails with "No adapter recognizes"). This handoff doc is the durable record of the session's findings; nothing else was indexed. |

---

## What to build

Not code — a **written comparison and target-state recommendation**: how AI-lane review responsibility (Cursor/Crush/Codex/Kiro/Copilot-audit, per the HITL team charter) *should* map onto GitHub's actual enforcement primitives (rulesets, required status checks, required reviewers/CODEOWNERS), compared against what two real repos currently do. Output is a markdown doc (plan-type, not implementation) with a recommended target ruleset shape per repo, plus an execution-plan brief Cursor could later implement from — but implementation is explicitly out of scope for this slice.

**Why this exists:** A session today (2026-09-18, ad-hoc, no arc) investigating willowyhollow's staging2 security-header gaps ended up reading `.github/workflows/deploy.yml` and both repos' live GitHub rulesets via `gh api`. It found that "review required" is a documented policy in both this repo's own charter and the WordPress project's norms, but **GitHub enforces zero required approving reviews on both repos' protected branches**. That gap — a real PR-gate that lets any single write-access holder self-merge — is bigger than the willowyhollow-specific staging2 finding that started the investigation, and it recurs identically in convmem's own `main`. Ryan asked for Codex to reconcile a proposed ideal against both real systems rather than have Claude design it unilaterally.

---

## Integration point

No code integration point — this is a planning artifact. The **subject matter** lives at:

- `~/GitClones/willowyhollow-dev/.github/workflows/deploy.yml` (two jobs: `deploy-production` on push to `main` → `~/www/willowyhollow.com`, `deploy-staging` on push to `staging` → `~/www/staging2.willowyhollow.com`; independent/parallel, not sequential)
- GitHub ruleset `alanmz-crypto/willowyhollow-dev` id `19155375` (`main-integrity-gates`) and id `19155380` (`staging-integrity-gates`)
- GitHub ruleset `alanmz-crypto/convmem` id `19156572` (`Protect Main`)
- `docs/inter-model/TEAM-CHARTER-2026-07-06.md` (this repo) — the HITL lane table Ryan's policy assumes is enforced
- `~/WordPress/AGENTS.md` and `~/WordPress/willowyhollow/AGENTS.md` — project docs that describe deploy mechanics now stale relative to the ruleset (see below)

---

## Specification

### Inputs — the three systems to reconcile

**A. Data point 1 — willowyhollow-dev, `main-integrity-gates` (created 2026-07-18, active, non-bypassable):**
```json
{
  "pull_request": {"required_approving_review_count": 0, "required_reviewers": [], "require_code_owner_review": false},
  "required_status_checks": {"strict_required_status_checks_policy": false, "required_status_checks": ["theme-engine", "plugin-lock"]},
  "non_fast_forward": true,
  "bypass_actors": [], "current_user_can_bypass": "never"
}
```
`staging-integrity-gates` (id 19155380) is byte-for-byte identical except `ref_name` targets `staging`. Neither ruleset's required status checks include anything related to CSP/HSTS/Referrer-Policy — the six open staging2 security observations (confirmed live via `convmem unresolved --site staging2.willowyhollow.com`: 3 `failed_check` + 3 `failed_verification`, all medium severity, dated 2026-09-08) are caught only by convmem's out-of-band monitor, never by CI, and never block a merge.

**B. Data point 2 — convmem, `Protect Main` (created 2026-07-18, active):**
```json
{
  "pull_request": {"required_approving_review_count": 0, "required_reviewers": [], "required_review_thread_resolution": true},
  "required_status_checks": {"strict_required_status_checks_policy": true, "required_status_checks": ["pylint (3.12)", "pytest (3.12)", "Analyze (actions)", "Analyze (python)", "CodeQL"]},
  "non_fast_forward": true, "deletion": true,
  "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}],
  "current_user_can_bypass": "always"
}
```
Same **zero required approvals** gap as willowyhollow, but: 5 required status checks (incl. CodeQL) vs. 2; `strict_required_status_checks_policy: true` (branch must be up to date with base) vs. `false`; and — asymmetrically — convmem allows a `RepositoryRole` to *always* bypass the ruleset, while willowyhollow allows **no** bypass at all. That inconsistency (unbypassable-but-toothless vs. bypassable-and-richer) looks accidental, not designed, across the two repos.

**C. Proposed direction (Claude's starting position, not a decision):**
1. Raise `required_approving_review_count` to at least 1 on any branch that deploys to a live or production-adjacent host (both `main` and `staging` on willowyhollow; `main` on convmem) — the single biggest gap, since it's the one place "review required" as stated policy and "review required" as GitHub mechanism currently diverge.
2. Decide `required_approving_review_count` deliberately per risk tier rather than uniformly — e.g. convmem's own non-production-facing `main` may reasonably stay lighter than willowyhollow's SiteGround-facing branches once question 1 is settled; this needs an explicit call, not a default.
3. Promote the staging2 CSP/HSTS/Referrer-Policy checks from convmem-monitor-only into an actual required status check on `staging-integrity-gates` (and eventually `main-integrity-gates`), so a security-header regression blocks merge instead of surfacing as an unresolved ledger item after the fact.
4. Match `strict_required_status_checks_policy: true` on willowyhollow's rulesets to convmem's existing posture, or explicitly decide why willowyhollow should stay looser.
5. Resolve the bypass-actor asymmetry between the two repos on purpose (pick one policy, document why) instead of leaving it as an artifact of whoever configured which repo first.
6. Map the charter's Kiro (design/sign-off) vs. Copilot-audit-lane (safety/isolation) split onto whatever GitHub reviewer mechanism actually exists for these lanes today (human Ryan approval standing in for both, a bot/service-account reviewer, or CODEOWNERS by path) — this repo's charter assumes the split is enforced; right now nothing enforces it.

This is a starting position for Codex to stress-test, not a spec to implement as-is.

### Algorithm / behavior

Not applicable (planning artifact, not code) — Codex's output should instead walk: current state (A, B) → gaps against stated policy → proposed target (evaluate/revise C) → a phased execution-plan brief (what Cursor would implement first, what needs a Ryan authorization for which exact repo/ruleset/field/value per the bounded-autonomy rule: *"External auth requires exact resource, operation, and final value... never infer from outcome"*).

### Output / contract

A markdown document at `docs/plans/` or `docs/inter-model/` (Codex's call, following existing repo convention) containing:
- A comparison table: willowyhollow vs. convmem vs. proposed target, per ruleset field.
- A named verdict on each of the 6 proposed-direction points above (adopt / adopt-with-changes / reject, with reasoning).
- A phased execution-plan brief suitable for a follow-on Cursor implementation handoff, **explicitly listing which steps require a new Ryan authorization** (per repo, ruleset field, exact new value) before Cursor can act.

### Constants

None.

---

## What NOT to build

- No ruleset, branch-protection, or `deploy.yml` change — this is analysis and planning only.
- No new required status check implementation (e.g., actually wiring a CSP/HSTS/Referrer-Policy CI check) — that's a Cursor implementation slice that would follow *after* Codex's plan and a Ryan grant.
- No change to `willowyhollow/AGENTS.md` or `~/WordPress/AGENTS.md` — flagging staleness is in scope, editing them is not (this session was explicitly told "do not edit files" for the underlying review, and no broader authorization has been given since).
- No assumption that Kiro/Copilot/Cursor/Crush have literal GitHub reviewer identities today — verify this before proposing CODEOWNERS or required-reviewer wiring that assumes accounts exist.

---

## Test expectations

Not applicable in the pytest sense. Acceptance is a document review: Ryan (and optionally Kiro, per the charter's design/sign-off lane) reads Codex's comparison and either authorizes a next Cursor slice or sends it back with corrections.

---

## Acceptance criteria

- [ ] Comparison table covers both real repos' actual ruleset JSON (not paraphrased) plus the proposed target
- [ ] Each of the 6 proposed-direction points gets an explicit verdict, not a blanket endorsement
- [ ] Execution-plan brief separates "needs Ryan authorization" steps from anything a lane could safely draft unauthorized (e.g., a draft CODEOWNERS file for review, vs. actually enabling `require_code_owner_review`)
- [ ] Bypass-actor asymmetry between the two repos is addressed explicitly, not silently dropped
- [ ] Staging2's six open security observations are referenced with their real ledger ids (`obs_staging2_monitor_csp-missing`, `obs_staging2_monitor_header-hsts`, `obs_staging2_monitor_header-referrer-policy`, and their `ver_staging2_mon_*` verification counterparts) rather than restated as a bare count

---

## Branch convention

```
docs/2026-09-18-willowyhollow-review-gate-comparison
```
Push immediately after each commit. This is a docs-type branch — Codex's comparison doc can land as a commit on this same branch, or Codex may open a fresh `plan/` branch if its output is substantial enough to warrant its own — either is fine, note the choice in the resume-state table when picking this up.

---

## Related files

| What | Path |
|------|------|
| WordPress workspace overview | `~/WordPress/AGENTS.md` |
| willowyhollow site guide (stale deploy section) | `~/WordPress/willowyhollow/AGENTS.md` |
| Deploy workflow (ground truth for what actually runs) | `~/GitClones/willowyhollow-dev/.github/workflows/deploy.yml` |
| HITL team charter (the policy being checked against enforcement) | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` |
| Session-close / record protocol | `docs/inter-model/SESSION-CLOSE-RECORD.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line — not applicable, no arc claims this work (ad-hoc)
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] `convmem work resume docs/2026-09-18-willowyhollow-review-gate-comparison` (or `--worktree` equivalent)
- [ ] No STATUS arc applies — state `Arc: none (ad-hoc)` per the arc-identity rule, not a Goal/Role/System/Next block
