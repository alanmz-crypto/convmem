# Collision-Check Handoff: enable #286 incremental JSONL indexing

**Date:** 2026-10-05
**Author:** Kiro (review/design lane — non-implementing)
**For:** Any agent currently working on convmem (esp. Switchboard Arc, Trapdoor Hunt / #286 owners, OpenClaw Watch Coverage)
**Authorization:** Ryan, 2026-10-05 (verbal — asked me to circulate this before enabling, to catch conflicts)

> **Purpose:** collision check, NOT an implementation brief. We want to **turn
> on the merged incremental-indexing engine (#286)** by adding its config
> table, to stop full-file DeepSeek reprocessing on every transcript change.
> Before changing live config, confirm it won't disturb in-flight work.
> **If any planned action touches your work, say STOP.**

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED` — scope check shows config enable is a cost no-op; do NOT proceed as a burn fix (see SCOPE CHECK RESULT below) |
| **Target of action** | live config `~/.config/convmem/config.toml` (add one table) + watch restart to reload |
| **Branch** | n/a for the config change (operational); any code work would be a separate branch |
| **PR** | not opened |
| **Ryan GATE** | Ryan must authorize the config enable + the watch reload |

---

## ⚠ SCOPE CHECK RESULT (2026-10-05) — config enable will NOT reduce burn

Read-only verification of the live runtime code (`incremental_jsonl.py`,
`incremental_jsonl_formats.py`) and the watch service env found that enabling
the config flag is a **no-op for DeepSeek cost**. Do not enable it expecting
cost relief.

**Finding 1 — live-production route is fused off.** `maybe_route_incremental`
runs the real incremental coordinator **only when `CONVMEM_INCREMENTAL_ROOT`
(a hermetic isolation root) is set**. Otherwise it returns `"skipped"` and the
file falls back to the legacy full-reprocess path. The code comment:
*"Live activation is unauthorized for this Execute; refuse rather than
constructing production-state machinery outside a hermetic root."*
The live `convmem-watch.service` env does **not** set
`CONVMEM_INCREMENTAL_ROOT` (checked unit + drop-ins). So with `enabled = true`,
watch hits the refuse branch and keeps full-reprocessing via DeepSeek.

**Finding 2 — scope is Kiro-only (non-isolated).** `routed_formats()` returns
only `{jsonl_kiro_session}` outside isolation; Codex formats require the same
`CONVMEM_INCREMENTAL_ROOT` gate. **Crush and Cursor transcripts have no
incremental format spec** and would full-reprocess regardless.

**Conclusion:** the safe config-only enable does nothing for cost. Actually
cutting the burn requires the live-activation path — i.e. the Ryan-gated
`feat/2026-09-17-issue-286-main-integration` work (Copilot FAIL outstanding),
which is explicitly OUT OF SCOPE here. **Recommendation: do NOT proceed with
the config enable as a burn fix.** Pursue instead (safest first): local
summarizer (`qwen3.5`), narrowing watched sources, then the gated #286
live-activation review, with watch-pause as a fallback if a spike hits.

---

## Why (the problem this fixes)

- Indexing/summarization runs through the **paid DeepSeek API**
  (`summarize_model = distill_model = "deepseek-v4-flash"` in config).
- The incremental fix (#286) is **absent from config**, so on every *changed*
  watched transcript, watch **re-summarizes the whole file** rather than only
  the appended delta — the documented burn (config comment cites a past
  "132 paid calls" full re-summarize of one file). Active sessions append to
  `messages.jsonl` frequently, so the restarted watcher (brought up earlier
  today) now carries live cost-spike risk. Nothing has burned yet; Ryan is
  watching.

---

## Key finding: this is a CONFIG toggle, NOT a code merge

Verified 2026-10-05 against `main` and the live runtime worktree:

- The incremental **engine is already merged to `main`** and present in the
  runtime worktree `.worktrees/runtime-main` (HEAD `a92a74e`, what watch runs):
  - PR **#293** `881133d` — default-off incremental indexing for Kiro JSONL
  - PR **#301** `8983a6f` — live-safe exact-resource JSONL production canary
  - PR **#307** `d657767` — safe incremental indexing for isolated Codex JSONL
- The engine reads `[index.incremental_jsonl]` via
  `config.py::incremental_jsonl_settings()`; **default-off, fails closed** on
  malformed input. Keys: `enabled` (bool), `allow_full_rebuild` (bool),
  `state_dir` (str, default `~/.local/share/convmem/incremental-jsonl`).
- Routing: `ingest.py:1313 maybe_route_incremental(...)` → honors
  `settings.enabled`; off today because the table is absent.

**Therefore enabling #286 does NOT require merging the gated
`feat/2026-09-17-issue-286-main-integration` branch (`19d34a5`, no PR, Copilot
FAIL outstanding).** That branch is a *separate, further* integration and is
explicitly OUT OF SCOPE here. We are only switching on already-merged,
default-off, fail-closed engine code via config.

---

## Planned action (what I intend to do)

```toml
# add to ~/.config/convmem/config.toml under [index]
[index.incremental_jsonl]
enabled = true
allow_full_rebuild = false
# state_dir defaults to ~/.local/share/convmem/incremental-jsonl
```

```bash
# reload watch so the new setting takes effect
systemctl --user restart convmem-watch.service
systemctl --user status convmem-watch.service --no-pager
journalctl --user -u convmem-watch -n 20 --no-pager
convmem doctor
```

**Rollback:** remove the table (or set `enabled = false`) and restart watch —
fail-closed means absence = prior full-reprocess behavior. The archived
pre-change config can be kept if desired.

---

## WILL / WILL NOT touch

**WILL:** `~/.config/convmem/config.toml` (`[index.incremental_jsonl]` table);
restart `convmem-watch.service`; create the incremental state dir
(`~/.local/share/convmem/incremental-jsonl`) on first run.

**Will NOT:**
- merge or touch `feat/2026-09-17-issue-286-main-integration` (`19d34a5`) or any
  #286 review branch — out of scope, still Ryan-gated with Copilot FAIL
- change `summarize_model`/`distill_model` (still DeepSeek; this reduces call
  *volume*, not the provider)
- touch the `a92a74e` runtime pin, OpenClaw manifest, monitor timer, or
  shadow-ledger (all left as-is)
- set `allow_full_rebuild = true` (kept false so it can't trigger a full replay)

---

## Risks / open questions

- **First-run behavior:** on enable, each watched JSONL may do one
  `initial_full` pass to establish its cursor (engine distinguishes
  `initial_full` from later deltas; `allow_full_rebuild=false` blocks
  non-initial full rebuilds). So expect a *one-time* normal-cost pass per file,
  then delta-only. This is the opposite of a runaway — but watch spend on the
  first churn after enable.
- **Scope:** merged PRs name **Kiro and Codex JSONL** explicitly. Confirm the
  routing covers the sources actually driving burn (Crush/Cursor transcripts
  too?) — if a hot source isn't routed, it still full-reprocesses. (Open
  verification item before claiming the burn is fully solved.)
- **Fail-closed:** malformed table raises `IncrementalJsonlConfigError` — a
  typo disables indexing rather than corrupting. Low blast radius.

---

## Collision questions for active agents (answer CLEAR or STOP)

1. **Switchboard Arc:** Does enabling incremental JSONL indexing / restarting
   watch again disturb your (now-finishing) transcript indexing or any live
   state? You cleared the earlier restart — does this second restart matter?
2. **#286 owners (Trapdoor Hunt):** Any objection to enabling the *merged*
   engine via config while your `main-integration` branch review is still open?
   Does switching it on live interfere with a measurement or review you depend
   on being able to run against the default-off state?
3. **OpenClaw Watch Coverage:** Does an incremental state dir + watch restart
   affect the pinned runtime worktree / admitted-file manifest? (Plan leaves the
   pin and manifest untouched.)
4. **Anyone:** Is anything depending on full-reprocess behavior (e.g. a
   re-summarization pass you expect watch to perform)?

---

## Related files

| What | Path |
|------|------|
| Config to edit | `~/.config/convmem/config.toml` ([index] section) |
| Engine config loader | `.worktrees/runtime-main/config.py` (`incremental_jsonl_settings`) |
| Routing call-site | `.worktrees/runtime-main/ingest.py:1313` (`maybe_route_incremental`) |
| Engine | `.worktrees/runtime-main/incremental_jsonl.py` |
| Prior watch-restart handoff | `KIRO-2026-10-05-watch-restart-collision-check-handoff.md` |
| Gated (OUT OF SCOPE) integration branch | `feat/2026-09-17-issue-286-main-integration` (`19d34a5`) |

---

## Leaving / picking up checklist

**Author (Kiro):**

- [x] This file written under `docs/inter-model/`
- [ ] `LATEST.md` bullet (add on Ryan's say-so after clearances)
- [ ] Not pushed yet (local)

**Reviewer (active agent):**

- [ ] Read "Planned action" + "WILL / WILL NOT touch" + "Risks"
- [ ] Answer collision questions for your lane (CLEAR / STOP)
- [ ] Flag STOP if it disturbs in-flight work

<!-- Collision-check handoff. Enables already-merged default-off engine via config; does NOT merge the gated #286 integration branch. Kiro review-required; action is operational + Ryan-gated. -->
