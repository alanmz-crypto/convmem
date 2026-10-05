# Implementation Handoff: #286 live-activation (stop the DeepSeek burn)

**Date:** 2026-10-05
**Author:** Kiro (review/design lane — non-implementing)
**For:** Codex (architecture + implementation planning lane); **Copilot** in the
conditional safety/audit lane for the live-activation safety review
**Authorization:** Ryan, 2026-10-05 (verbal — "give me a handoff so Codex can
try to fix the issue; Codex needs Copilot to help")

> **This is an implementation handoff, not a collision check.** It asks Codex to
> finish the one thing that actually reduces the burn: wiring the *merged,
> default-off* incremental engine so it runs on the live watcher. Copilot audits
> the safety of live activation. Kiro reviews the design/outcome. **Ryan owns the
> merge.** No production activation ships without Ryan's explicit grant.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` → ready for Codex to pick up planning/implementation on a branch |
| **Reviewed impl (PASS)** | `506afc1` on `feat/2026-09-17-issue-286-incremental-index` — Copilot PASS, Kiro PASS, no PR |
| **Integration successor** | `19d34a5` on `feat/2026-09-17-issue-286-main-integration` — READY_FOR_RECHECK; pushed; **Copilot FAIL (documentation acceptance) outstanding at earlier tip `e99856e`**; needs fresh exact-tip Copilot + Kiro rechecks |
| **main at integration grant** | `18f63db` (re-fetch actual `origin/main` at start) |
| **Copilot corrective branch** | `fix/2026-09-17-...-issue-286-copilot-corrective` `d14f8a6` — 0 commits ahead of origin/main (stale/folded; verify, do not assume) |
| **PR** | none opened for any #286 branch |
| **Ryan GATE** | (1) authorize which branch Codex works from; (2) authorize live activation + any `convmem-watch.service` env/config change; (3) merge |

---

## The issue to fix (why this exists)

Watch indexing summarizes transcripts through the **paid DeepSeek API**
(`summarize_model = distill_model = "deepseek-v4-flash"`). On every *changed*
watched JSONL, the legacy path **re-summarizes the whole file**, not the
appended delta — the DeepSeek "burn." #286 built incremental (delta-only)
indexing to fix this.

**Kiro scope check (2026-10-05) — why the easy toggle does NOT work:**
- The engine is already merged to `main` / runtime worktree `a92a74e`
  (PRs #293, #301, #307) and reads `[index.incremental_jsonl]` (default-off,
  fail-closed).
- BUT `maybe_route_incremental` (`incremental_jsonl.py` ~line 1721) runs the real
  coordinator **only when `CONVMEM_INCREMENTAL_ROOT` (hermetic isolation root)
  is set**; otherwise it returns `"skipped"` and falls back to full reprocess.
  Code comment: *"Live activation is unauthorized for this Execute; refuse
  rather than constructing production-state machinery outside a hermetic root."*
  The live `convmem-watch.service` env does **not** set that var.
- Scope is also narrow: `routed_formats()` → only `{jsonl_kiro_session}` outside
  isolation; Codex formats need the isolation gate; **Crush/Cursor transcripts
  are not routed at all.**

So setting the config flag alone is a **cost no-op**. The real fix is the
live-activation path — the deliberately-fused production wiring plus source
coverage — which is the gated `main-integration` work with the open Copilot
FAIL. **That is what this handoff authorizes Codex to pursue.**

---

## What to build (goal)

Make the merged incremental engine **safely run on the live watcher** so changed
transcripts index delta-only instead of full-reprocessing, eliminating the
per-change DeepSeek burn — **without weakening the isolation/safety guarantees
the current refuse-branch protects.**

Deliverables Codex should produce (plan first, then implement on a branch):

1. **A design** for live activation that replaces the hard refuse branch with a
   production-safe route: how production state (`state_dir`, cursors) is created
   outside a hermetic root without the corruption/coverage risks the refuse
   comment guards against. Resolve: do we set `CONVMEM_INCREMENTAL_ROOT` for the
   service, introduce a distinct production-activation flag, or something else?
2. **Resolution of the outstanding Copilot FAIL** (documentation acceptance) on
   the integration branch — fresh exact-tip Copilot audit + Kiro review.
3. **Source-coverage decision:** burn is driven by Kiro + Crush + Cursor
   transcripts. Non-isolated routing today covers only Kiro JSONL. Decide and
   document whether Crush/Cursor get incremental format specs now or stay on the
   legacy path (and therefore keep burning). State the realistic cost impact.

---

## Integration point

- `.worktrees/runtime-main/incremental_jsonl.py` ~1721 — `maybe_route_incremental`
  (the refuse branch to redesign).
- `.worktrees/runtime-main/incremental_jsonl_formats.py` — `routed_formats`,
  `KIRO_ROUTE_FORMATS`, `ISOLATED_CODEX_FORMATS` (source-coverage gating).
- `.worktrees/runtime-main/ingest.py:1313` — call-site.
- `~/.config/convmem/config.toml` `[index]` — `[index.incremental_jsonl]` table.
- `~/.config/systemd/user/convmem-watch.service` (+ drop-ins) — env/activation.

---

## What NOT to build

- **Do not activate on the live watcher without Ryan's explicit grant.** Planning
  + branch implementation + reviews first; activation is a separate gated step.
- **Do not change `summarize_model`/`distill_model`** here (that's a different,
  parallel mitigation — local `qwen3.5` — not this arc).
- **Do not weaken the fail-closed / isolation guarantees** to make activation
  easier. If the refuse branch exists for a corruption-safety reason, the design
  must preserve that property, not bypass it.
- **Do not merge or self-approve.** Ryan merges.
- **Do not touch** the runtime pin `a92a74e`, OpenClaw manifest, monitor timer,
  or shadow-ledger.

---

## Test expectations

- Incremental route produces the **same units/summaries** for a given transcript
  prefix as the legacy full path (contract parity — the S0–S3 contract Copilot
  and Kiro already PASSed at `506afc1`).
- A changed/appended JSONL triggers **delta-only** DeepSeek calls, measurably
  fewer than full reprocess (capture a before/after paid-call count).
- Fail-closed preserved: malformed `[index.incremental_jsonl]` → indexing
  disabled, not corrupted.
- No regression in existing suite; ruff/pylint clean per repo gates.

---

## Acceptance criteria

- [ ] Design doc for live activation that preserves isolation/fail-closed safety
- [ ] Outstanding Copilot FAIL (doc acceptance) resolved; fresh exact-tip Copilot
      audit = PASS; Kiro review = PASS on the same tip
- [ ] Source-coverage decision documented with cost impact (esp. Crush/Cursor)
- [ ] Contract parity + delta-only burn reduction demonstrated with evidence
- [ ] Branch pushed; PR drafted (not merged); Ryan GATE for activation stated

---

## Lane roles (per team charter)

- **Codex:** author the activation design + execution plan; implement on a
  branch after Ryan authorizes which branch to work from.
- **Copilot (conditional audit lane):** independent **safety/isolation audit of
  live activation** + the exact-tip documentation-acceptance recheck that
  previously FAILed. Targeted scope only — not implementation.
- **Kiro:** design review / sign-off on the same exact tip.
- **Sol-High:** only if Copilot and Kiro issue materially conflicting PASS/FAIL
  verdicts on the same tip (five-field prompt). A single FAIL or a deferral is
  not a conflict.
- **Ryan:** sole merge + sole live-activation grant.

---

## Branch convention

```
feat/2026-10-NN-issue-286-live-activation   (or resume the integration branch if Ryan directs)
```

Push immediately after each commit. PR when acceptance criteria pass. Ryan
squash-merges unless the PR says **Do not squash**.

---

## Related files

| What | Path |
|------|------|
| Scope-check + no-op finding | `KIRO-2026-10-05-enable-286-incremental-collision-check-handoff.md` |
| Prior Cursor integration handoff | `CURSOR-2026-09-17-issue-286-main-integration-handoff.md` |
| Watch-restart recovery (today) | `KIRO-2026-10-05-watch-restart-collision-check-handoff.md` |
| Engine | `.worktrees/runtime-main/incremental_jsonl.py` |
| Format/scope gating | `.worktrees/runtime-main/incremental_jsonl_formats.py` |
| Arc brief | `docs/plans/STATUS-codex-jsonl-production-integration.md` |

---

## Leaving / picking up checklist

**Author (Kiro):**

- [x] This file written under `docs/inter-model/`
- [ ] `LATEST.md` bullet (add on Ryan's say-so)
- [ ] Push branch so Codex/Copilot off-`origin` can read it (Ryan authorizes push)

**Implementer (Codex, picking up):**

- [ ] Read this file + the scope-check handoff before first edit
- [ ] `git fetch origin`; record actual `origin/main`; confirm the integration
      branch tip `19d34a5` and whether the corrective branch is truly stale
- [ ] State Goal / role / system state / next action (STATUS-codex-jsonl arc)
- [ ] Plan first; implementation + activation await Ryan grants

<!-- Implementation handoff. Codex implements on a branch; Copilot audits live-activation safety + the doc-acceptance recheck; Kiro reviews; Ryan merges and grants activation. The config-only toggle is a cost no-op (see scope-check handoff) — the real fix is the gated live-activation path. -->
