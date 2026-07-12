# Execution Plan — Always-Available GitHub Fallback

```
Planning Status

Phase:        Execute
Characters:   Cursor
Lanes:        Cursor → Ryan (GitHub Pro / merge)
Authority:    Executive plan authorized; gates accepted as defaults 2026-07-12
```

**Sources:** [`github_fallback_executive_e9bc86df.plan.md`](/home/lauer/.cursor/plans/github_fallback_executive_e9bc86df.plan.md), [`always_github_fallback_124717a3.plan.md`](/home/lauer/.cursor/plans/always_github_fallback_124717a3.plan.md)  
**Architecture SSoT:** [`ARCHITECTURE-always-github-fallback.md`](ARCHITECTURE-always-github-fallback.md)  
**Branch:** `feat/2026-07-12-always-github-fallback`

---

## Gate decisions (accepted defaults)

| # | Choice |
|---|--------|
| 1 | Local env = hook skip + audit only (`CONVMEM_SKIP_MAIN_HOOK`); never in agent protocol; not identity |
| 2 | **Intent (a)** PR-only / no emergency direct-push bypass. **Blocked on this private repo:** GitHub Branch Protection / Rulesets API returns HTTP 403 (requires GitHub Pro or public repo). Ryan must enable Pro or apply equivalent protection when available. Until then: **do not claim “main is protected” on GitHub** — local hooks only. |
| 3 | **A** — fail closed; block tracked edits until explicit push succeeds |
| 4 | **MVP local-only** — this gitdir / `git worktree list`; cross-host protocol-only |
| 5 | **A** — convmem only |
| 6 | Forced by 2(a) intent: **PR required** for every `main` update once GitHub allows PR-only rules |

**Supersession:** Builds `work start`/`resume` now; overrides Foundation 2-week habit gate.

---

## `_check_direct_commits_on_main` decision

**Repurpose → retire heuristic WARN.** Replace with:

- `dirty_main` — tracked modifications while on `main` (WARN)
- `unpushed_commits` — current branch has commits not on `@{u}` (WARN)
- Historical reflog feat/fix heuristic removed from default doctor path (hard hooks supersede)

---

## Deliverables (this branch)

1. Protocol + branching-strategy: no typo-on-main; before first tracked edit; explicit refspec; push every commit; Always-GitHub-Fallback block
2. `git_hooks.py` + `pre-commit` + `pre-push`: reject commit/push on `main`; bypass env audit-only
3. Doctor: dirty_main, unpushed_commits; retire direct_commits heuristic
4. `convmem work start|resume` (+ optional `--worktree`); fail closed; taxonomy-first
5. VERIFY plan + GitHub Pro checklist for Ryan
6. Tests

---

## Out of scope this PR

- Same-host claim registry (deferred)
- Remote-backed claims
- Making the GitHub private-repo protection API work without Pro
- Expanding policy to non-convmem repos

---

## Sign-off

**Mechanical PASS:** 2026-07-12 — tip `f4b4993` (see VERIFY evidence).  
**V6a:** SKIP (GitHub protection API HTTP 403 — Pro required). Do not claim main protected.

**Kiro (V6c):** review per [`../inter-model/HANDOFF-KIRO-2026-07-12-always-github-fallback-signoff.md`](../inter-model/HANDOFF-KIRO-2026-07-12-always-github-fallback-signoff.md), then replace this line:

```text
Kiro reviewed: PENDING
```

**Ryan (V6d):** merge GATE after V6c. Enable Pro + branch protection when ready for V6a PASS.
