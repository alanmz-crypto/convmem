# Gate 1 Decision Brief: Should Claude Code transcripts enter the corpus?

**Date:** 2026-09-18
**Author:** Kiro (review lane — decision brief, non-implementing)
**For:** Ryan (Gate 1 decision)
**Decision requested:** Yes / No / Conditional — do Claude Code CLI session
transcripts belong in the convmem corpus, and if so, by what capture path?
**Companion docs:** implementation spec in
[`CURSOR-2026-09-17-claude-transcript-adapter-handoff.md`](CURSOR-2026-09-17-claude-transcript-adapter-handoff.md);
cost precedent in
[`CLAUDE-2026-09-18-deepseek-indexing-burn-handoff.md`](CLAUDE-2026-09-18-deepseek-indexing-burn-handoff.md).

---

## Consequence first (what changes for you)

Today, every Claude Code session that follows its `CLAUDE.md` Track A instruction
runs `convmem index --file ~/.claude/projects/<slug>/<uuid>.jsonl` and indexes
**nothing** — the format is unrecognized. Claude is the one wired MCP surface
whose own conversations never reach the corpus. Your decision here determines
whether that gap gets closed, and how much recurring DeepSeek/embedding spend you
accept to close it.

There are **three** distinct choices bundled under "add Claude to convmem," and
they have very different cost profiles. This brief separates them so you can say
yes to the cheap one without implicitly buying the expensive one.

| Option | What it enables | Recurring cost | Reversible? |
|--------|-----------------|----------------|-------------|
| **1. Do nothing** | Claude sessions stay unindexed | none | n/a |
| **2. Adapter only** (handoff scope) | `convmem index --file` works on demand; no auto-capture | **per explicit invocation only** | trivially — delete adapter |
| **3. Adapter + watch/source wiring** | `~/.claude/projects` auto-indexed like Cursor | **high, continuous** (see Cost) | config revert, but corpus pollution persists |

The handoff proposes **Option 2** and explicitly walls off Option 3 behind a
second gate. My recommendation (below) agrees, with one refinement.

---

## The 5 Ws

- **Who** — Claude Code CLI is a wired convmem surface (`convmem doctor` reports
  `mcp_claude` PASS; `~/.claude.json` has the convmem server). Its sessions are
  authored by the Claude lane doing real convmem work.
- **What** — Claude CLI writes one JSONL transcript per session at
  `~/.claude/projects/<project-slug>/<session-uuid>.jsonl`. There is no adapter
  that recognizes this format. **Verified:** `adapters/detect.py` has no Claude
  branch — such a file falls through the `.jsonl` block and `detect_format()`
  returns `None`.
- **When** — the gap has existed since Claude was wired. Until a recent fix
  (`fix/2026-09-17-watch-skip-hash-parity`) `index --file` returned **exit 0 with
  `files_processed=0`**, so sessions falsely believed their handoff was recorded.
  The silent-success half is fixed; the missing adapter is what remains.
- **Why now** — this very session cannot complete Track A. The bug is no longer
  silent, so it now surfaces as a hard wall instead of a false success — which is
  why it's in front of you.
- **How (if yes)** — build `adapters/claude_session_jsonl.py` modelled on the
  existing `adapters/copilot_session_jsonl.py` (**verified**: that file is exactly
  the `is_* / read_session_meta / parse` shape over `adapters/jsonl_io` helpers the
  handoff cites), register three lines in `detect.py`, add focused tests. Do
  **not** touch `[sources].paths`.

---

## The case FOR (why Claude chat has corpus value)

1. **Parity.** Cursor, Codex, Kiro, Copilot, Crush transcripts are all indexable.
   Claude is the lone wired surface that is not. Cross-model handoff quality
   degrades when one lane's reasoning is invisible to search/ask.
2. **The instruction already exists and is dead.** `CLAUDE.md` tells every session
   to run the Track A command. Either make it work or remove the instruction —
   the current state (a documented ritual that silently no-ops) is the worst of
   both.
3. **Bounded, on-demand cost under Option 2.** Explicit `index --file` is paid
   only when a human/agent chooses to run it, once per session at handoff. That
   is the same shape as Kiro/Copilot Track A today.

## The case AGAINST (why to be cautious)

1. **The cost precedent is severe and recent.** Per
   `CLAUDE-2026-09-18-deepseek-indexing-burn-handoff.md`: a single prompts-only
   transcript (`~/.codex/history.jsonl`) generated **44,770 of 79,566 active
   units — 56% of the serving corpus** — because convmem re-summarizes the whole
   transcript on every append, at ~132 paid DeepSeek calls per touch. It caused
   94% of DeepSeek traffic and 100% of the 900s index timeouts. Claude sessions
   are append-heavy and long — Option 3 would reproduce this on a larger source.
2. **The incremental-append fix does not cover Claude.** `incremental_jsonl.py` is
   hard-scoped to `jsonl_kiro_session` and gated behind Arc Codex, so it cannot
   absorb Claude appends today. This is *the* reason Option 3 is dangerous now and
   Option 2 is safe: on-demand `index --file` pays once; watch-driven re-index
   pays per append.
3. **Content bloat if hygiene is skipped.** Claude injects the entire `CLAUDE.md`
   (~10 KB) into the first user turn of every session via `<system-reminder>`,
   plus slash-command plumbing. Indexed raw, the same boilerplate re-embeds in
   every session. The handoff's content-hygiene stripping is not optional polish —
   it is a cost control.

---

## Recommendation

**Approve Option 2 (adapter only). Keep Gate 2 (watch/source wiring) firmly
closed until the incremental-append fix covers Claude.**

Rationale: Option 2 closes the parity gap and revives a dead instruction at
on-demand cost that matches the existing Kiro/Copilot Track A pattern, while the
documented 56%-corpus blowup is entirely a property of *auto-capture on append*
(Option 3), which Option 2 does not enable. The two gates in the handoff are the
right partition; this brief only asks you to clear the first.

**One refinement I'd add to the handoff before implementation:** make the
adapter's registration order in `detect_format()` explicit and tested. The
handoff says the Claude checker "must run BEFORE the generic agent-transcripts
shortcut." **Verified against `detect.py`:** the `"agent-transcripts" in
path.parts → jsonl_cursor` shortcut is the *first* thing tested in the `.jsonl`
branch, before the checker tuple. A Claude file is not under `agent-transcripts`,
so there is no real collision — but the test suite should assert that a Cursor
`agent-transcripts` file and a Claude file each still classify to their own
format, exactly as the handoff's test #2 already specifies. So this is confirmation,
not a new requirement: the handoff spec is sound as written.

---

## Design-review verdict on the existing spec (the "B" question)

I read `CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` critically as the
review lane. **Verdict: implementable as written, no blocking gaps.** Checked:

- Integration point (`detect.py` TOOL_BY_FORMAT / _PARSERS / checker tuple) matches
  the live file structure. ✔
- Model file (`copilot_session_jsonl.py`) exists and has the claimed shape. ✔
- Shared helpers (`iter_jsonl_dicts`, `nonempty_stripped`, `session_parse_context`)
  exist in `jsonl_io.py` and match the described contract. ✔
- Content-hygiene, sidechain-exclusion, and thinking/tool_use exclusion rules are
  specific and testable. ✔
- Acceptance criteria include "not in `[sources].paths`/`[watch].extra_paths`" —
  **verified** those are absent today (only `~/.cursor/projects` is wired). ✔

This is a Kiro review sign-off on the **spec**, not on code — no code exists yet.
Implementation remains Cursor's lane per the team charter.

---

## What clearing this gate unblocks (and what it does NOT)

- **Unblocks:** Cursor to build the adapter on
  `feat/2026-09-18-claude-transcript-adapter`, then Claude sessions can run Track A
  on demand.
- **Still blocked underneath:** the base branch `fix/2026-09-17-watch-skip-hash-parity`
  is **red (53 failed / 2483 passed)** due to an R2b inventory-digest rebind, tracked
  in `CURSOR-2026-09-17-r2b-inventory-rebind-handoff.md`. That is an R2b-lane /
  Ryan remediation and is independent of this decision — but the adapter branch
  should base off a clean tree, so sequencing matters.
- **Does NOT authorize:** adding `~/.claude/projects` to any auto-capture path
  (Gate 2), sidechain/subagent ingestion, or any `incremental_jsonl.py` change.

---

── Next steps ──
  • Ryan: record the Gate 1 decision (Yes → Option 2 / No / Conditional).
  • If Yes: Cursor picks up `CURSOR-2026-09-17-claude-transcript-adapter-handoff.md`
    once the R2b rebind lands and the base branch is green.
  • This session's own Track A remains impossible until the adapter exists — that
    is the bug, not a process miss.

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Track A | Indexing a session's chat transcript into convmem (vs Track B = indexing a `logs/*.md` artifact). |
| Gate 1 / Gate 2 | The two Ryan decisions on this work: (1) do Claude transcripts belong in the corpus; (2) may `~/.claude/projects` be auto-captured via watch/sources. |
| Adapter | A convmem parser that turns a tool's transcript format into canonical messages; registered in `adapters/detect.py`. |
| `detect_format()` | The router in `adapters/detect.py` that classifies a file by format or returns `None` if unrecognized. |
| Watch / `[sources].paths` / `[watch].extra_paths` | convmem config that auto-indexes files on change; the expensive, append-driven capture path. |
| `incremental_jsonl.py` | The append-cursor optimization that avoids re-summarizing a whole transcript per append; currently scoped only to Kiro sessions. |
| DeepSeek burn | The recurring paid-LLM cost of re-summarizing transcripts; the 56%-of-corpus blowup documented in the companion handoff. |
| sidechain | A Claude subagent's separate conversation tree (`isSidechain: True`); excluded from v1 ingestion. |
| R2b inventory rebind | An R2b-lane maintenance step re-binding an authority-content digest after governed modules move; the reason the base branch is currently red. |
| Lane (Kiro / Cursor / Codex / Crush) | The role a given model plays per `TEAM-CHARTER-2026-07-06.md`; Kiro reviews and plans (non-implementing), Cursor implements. |
| Arc | A named unit of tracked work with a STATUS brief; this decision brief is ad-hoc (not arc-tracked). |
