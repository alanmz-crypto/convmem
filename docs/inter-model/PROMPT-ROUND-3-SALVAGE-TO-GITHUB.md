# Workspace coordination — Round 3 (SALVAGE → GitHub)

Paste into **every** open Cursor chat that filed Round 1/2 on this arc.

## Goal

Leave **all work data needed for takeover** on GitHub so Ryan can keep **one**
live workspace and close the rest. No Architecture rewrite. No runtime/hooks.
No Execute.

## Outcome Ryan wants

| Keep open (one) | Close after salvage |
|---|---|
| **WS-main-cursor** on `/home/lauer/Projects/convmem` (unless Ryan names another) | This recon chat, shadow-handoff chat, any other sibling on the same root |

Architecture stays reviewable via draft PR #115 — no Codex workspace required.

## Hard rules

1. Read `/tmp/convmem-coord-2026-07-24-workspaces/BOARD.md` first.
2. **Do not** edit PR #115 Architecture content unless you are fixing a
   factual push mistake you just made (unlikely).
3. **Do not** commit onto `docs/2026-07-24-research-pack-backup-neutral` any
   Shadow Ledger audit/handoff residue — that stream is research-pack #114.
4. **Do not** stage secrets. **Do not** implement shadow hooks.
5. Prefer **new dedicated `docs/…` branches** + draft or ready PRs for salvage.
6. Push with explicit refspec:  
   `git push -u origin "$branch:refs/heads/$branch"`
7. After your salvage PR(s) exist, append a **Round 3 salvage receipt** to
   `BOARD.md` (your section only) listing GitHub URLs + “safe to close this chat: yes/no”.
8. If you have **nothing local-only**, still file a receipt: “Nothing to salvage; already on GitHub: …”

## Shared-root collision lock

Three chats share `/home/lauer/Projects/convmem`. To avoid toe-stepping:

1. **Only WS-main-cursor** may create branches / commit / push from that
   checkout for salvage **unless** Ryan names a different single writer.
2. Other chats on the same root: inventory + propose exact file→PR mapping in
   your BOARD receipt; **do not** `git add` / commit / switch branch.
3. If you are WS-main-cursor: you own the git mutations below.

(If Ryan pastes this into a chat that is not WS-main-cursor, that chat still
inventories and files a receipt, but does not commit.)

## Inventory checklist (every chat)

Mark each item: `ON_GITHUB` / `LOCAL_ONLY` / `N/A`

| Artifact | Expected home if salvaged |
|---|---|
| Research pack | PR #114 (merged) — already done |
| Architecture Direction | Draft PR #115 — already done |
| `docs/audit-ledger-first/` (8 files) | New dedicated docs PR; apply corrections named in #115 Architecture if touching them |
| `CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md` | Same salvage PR or tiny docs PR; mark superseded-by-#115 in the PR body if true |
| Local `LATEST.md` edits | Either include in salvage PR **or** leave for primary to reconcile to “#115 awaiting HITL” |
| `~/.cursor/plans/shadow_ledger_phase_0_*.plan.md` | Optional: paste path + one-paragraph status into salvage PR body (plans need not be committed) |
| `~/.cursor/plans/codex_phase_0_work_order_*.plan.md` | Same — note “Codex handoff file never written; #115 superseded packaging execute” |
| In-chat Track-1/Track-2 memos (backup/Neutral) | Only if not already in #114 / GitHub; else N/A |
| `/tmp/convmem-coord-2026-07-24-workspaces/` | Optional: do **not** require on GitHub; board is ephemeral |

## WS-main-cursor — execute salvage (git)

Unless Ryan redirects:

```text
1. Stay on or create a NEW branch off origin/main, e.g.
   convmem work start docs shadow-ledger-phase0-salvage
   (do NOT put salvage on the research-pack branch)

2. Copy/add only the LOCAL_ONLY files Ryan still wants:
   - docs/audit-ledger-first/*.md  (optionally with #115-required corrections)
   - docs/inter-model/CURSOR-2026-07-24-shadow-ledger-phase0-chatgpt-handoff.md
   - LATEST.md Active handoff bullet: Architecture #115 authored, awaiting HITL;
     Cursor Execute prohibited; note salvage PR URL

3. Commit with a human-readable message (why: one workspace can take over).

4. Push explicit refspec. Open a PR (draft OK) with consequence → 5 Ws → TL;DR
   and Merge reading links to #115 + salvage paths. Squash OK.

5. File Round 3 receipt on BOARD.md with PR URL(s).

6. Stop. Do not merge. Do not implement.
```

If Ryan wants audit left uncommitted: say so in the receipt and only land the
handoff + LATEST, or land nothing and list discard.

## Non-writer chats — inventory only

```text
1. List LOCAL_ONLY artifacts you authored or care about (paths).
2. Confirm you will not commit from the shared root.
3. Append Round 3 receipt: “Salvage delegated to WS-main-cursor; my unique bits: …”
4. After salvage PR exists (or Ryan says discard), reply: safe to close this chat: yes.
```

## Round 3 receipt template (append under `## Round 3 — Salvage receipts`)

```markdown
### Salvage receipt — WS-<slug>

| Artifact | Status | GitHub home |
|---|---|---|
| … | ON_GITHUB / LOCAL_ONLY / delegated / discard | <PR/URL or path> |

**Commits/PRs I opened:** <none | URLs>  
**Safe to close this chat:** yes / no — <why>  
**Primary takeover workspace:** WS-main-cursor (or Ryan override)  
**TL;DR:** …
```

## Done when

- #114 and #115 remain the landed Architecture/research artifacts
- Every LOCAL_ONLY item is either on a GitHub PR/branch, explicitly discarded
  by Ryan, or delegated with a BOARD receipt
- Only one chat claims write on the shared checkout
- Other chats say `Safe to close this chat: yes`
