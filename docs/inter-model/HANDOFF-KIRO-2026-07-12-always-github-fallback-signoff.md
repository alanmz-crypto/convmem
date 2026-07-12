# Handoff: Kiro sign-off — Always-Available GitHub Fallback

**Date:** 2026-07-12  
**From:** Cursor  
**To:** **Kiro** (design / milestone sign-off)  
**Status:** Mechanical PASS — awaiting **V6c**  
**Branch tip:** `feat/2026-07-12-always-github-fallback` @ `f4b4993`

**Read first:** [`LATEST.md`](LATEST.md) → this file → VERIFY → EXECUTION → ARCHITECTURE (spot-check only).

---

## Your job (V6c)

Independent **design / policy sign-off** after Mechanical PASS. Confirm the shipped arc matches the executive gates and is safe to merge (Ryan merges).

**When satisfied**, add exactly one line (today’s date) to [`docs/plans/EXECUTION-always-github-fallback.md`](../plans/EXECUTION-always-github-fallback.md) under **Sign-off**:

```text
Kiro reviewed: 2026-07-12
```

Also tick the evidence line in [`docs/plans/VERIFY-always-github-fallback.md`](../plans/VERIFY-always-github-fallback.md) (`V6c Kiro reviewed: …`).

Commit on the **same feature branch** (`docs`/`plan` only — your prefixes). Push with explicit refspec. **Do not merge to `main`.**

---

## Do not

| Must not | Why |
|----------|-----|
| Merge / push `main` | Ryan-only (V6d) |
| Claim “main is GitHub-protected” | `gh api …/protection` → **HTTP 403** (needs Pro) — V6a SKIP |
| Re-implement hooks / `work_git` / protocol | Cursor shipped; your lane is review |
| Create `feat/` / `fix/` branches | Kiro = **plan/docs only** |
| Volunteer a `convmem record` block | Only if Ryan says record / closing |
| Clean or switch away shared dirty allowlist | WH triage / TODO-WH / `s2_hotfix` stay |

---

## What Cursor already proved (do not re-derive)

```text
tip f4b4993 — Mechanical PASS
V0–V5 from unique /tmp worktree; hermetic tests/test_work_git.py (5 passed)
Installer checked in independent temp clone (not linked VERIFY_WT)
Doctor via $VERIFY_WT/convmem.py (not convmem wrapper); restic_gate-only nonzero OK
V6a SKIP (403 Pro)
```

Full checklist: [`VERIFY-always-github-fallback.md`](../plans/VERIFY-always-github-fallback.md)  
Raised-bar plan: `~/.cursor/plans/verify_github_fallback_5f18ba72.plan.md`

---

## Review checklist (sign-off questions)

1. **Gates** — EXECUTION defaults still correct? (fail-closed push; local ownership MVP; convmem-only; env = hook-skip not authz; PR-only *intent* until Pro)
2. **Safety** — No typo-on-main exception; no bare `git push -u origin HEAD`; taxonomy before mutate; explicit `"$branch:refs/heads/$branch"`
3. **Doctor** — `dirty_main` / `unpushed_commits` present; `direct_commits_on_main` not live enforcement
4. **Tests** — Hermetic `work_git` is mandatory for Mechanical PASS (greps alone insufficient) — agree?
5. **GitHub** — Agree V6a stays GATE until Ryan enables Pro + real protection API success?

Spot-check sources (no need to re-run full V0–V5 unless you distrust evidence):

| Doc / code | Path |
|------------|------|
| Architecture | [`ARCHITECTURE-always-github-fallback.md`](../plans/ARCHITECTURE-always-github-fallback.md) |
| Execution + gates | [`EXECUTION-always-github-fallback.md`](../plans/EXECUTION-always-github-fallback.md) |
| Verify | [`VERIFY-always-github-fallback.md`](../plans/VERIFY-always-github-fallback.md) |
| Strategy | [`branching-strategy.md`](../plans/branching-strategy.md) |
| Work CLI | `work_git.py` |
| Hooks | `git_hooks.py`, `scripts/git-hooks/` |
| Hermetic tests | `tests/test_work_git.py` |

Session start on this repo: `convmem doctor` → `brief(project=convmem)` → `unresolved` → read this handoff.

---

## After you sign

Ryan: merge GATE (V6d); enable GitHub Pro when ready for real branch protection (V6a).
