# Implementation Handoff: Claude Code transcript adapter

**Date:** 2026-09-17
**Author:** Claude (discovery + diagnosis, this session)
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-09-17 (verbal, this session: "Fix anything else you can. If it's no longer your route create a handoff.")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `feat/2026-09-18-claude-transcript-adapter` (not yet created) |
| **Tip SHA** | n/a |
| **Push status** | n/a |
| **PR** | `not opened` |
| **Ryan GATE** | **Yes — two.** (1) Ryan decides whether Claude transcripts belong in the corpus at all. (2) Even after the adapter lands, `~/.claude/projects` must NOT be added to `[sources].paths` without a separate Ryan decision. See **Cost gate**. |
| **Track A ingest** | Not possible for the authoring session — that is the bug this handoff describes. |

---

## What to build

An adapter that parses Claude Code CLI session transcripts
(`~/.claude/projects/<project-slug>/<session-uuid>.jsonl`) into canonical
messages, registered as format `jsonl_claude_session` with tool name `claude`.

**Why this exists:** there is no Claude adapter today. `detect_format()` returns
`None` for these files, so the Track A handoff step that `CLAUDE.md` instructs
every Claude session to run —
`convmem index --file ~/.claude/projects/<project>/<id>.jsonl` — has been
indexing **nothing**. Until today it also reported `files_processed=0` with
**exit 0**, so every Claude session that ran it believed its handoff was
recorded. The corpus contains 2 incidental lines mentioning `/.claude/projects/`
and no Claude session content.

The silent-success half is already fixed (see **Related work**); the missing
adapter is what remains.

---

## Integration point

`adapters/detect.py:31` (TOOL_BY_FORMAT), `:50` (_PARSERS), `:83` (checker tuple):

```python
# TOOL_BY_FORMAT
"jsonl_claude_session": "claude",

# _PARSERS
"jsonl_claude_session": claude_session_jsonl.parse,

# detect_format(), inside the `path.suffix == ".jsonl"` branch.
# Order matters: this checker must run BEFORE the generic
# "agent-transcripts in parts -> jsonl_cursor" shortcut is reached, and
# alongside the existing kiro/copilot/codex checkers.
("jsonl_claude_session", claude_session_jsonl.is_claude_session_jsonl),
```

New file: `adapters/claude_session_jsonl.py`, modelled on
`adapters/copilot_session_jsonl.py` (same `is_*` + `read_session_meta` + `parse`
shape, same `adapters/jsonl_io` helpers).

---

## Specification

### Inputs

- `~/.claude/projects/<project-slug>/<session-uuid>.jsonl`, one JSON object per line.
- No sibling metadata file. Session id and cwd are carried on the records.

### Observed record shape

Measured on a real 514-line session:

| `type` | count | carries a message? |
|---|---|---|
| `assistant` | 176 | **yes** — `message.content` is a **list of blocks** |
| `user` | 104 | **yes** — `message.content` is a **str** |
| `attachment` | 99 | no |
| `mode`, `permission-mode`, `atis-latch` | 25 each | no |
| `last-prompt`, `ai-title` | 24 each | no |
| `file-history-snapshot` | 7 | no |
| `system` | 5 | no |

Top-level fields: `type`, `sessionId` (also `session_id` on some records),
`uuid`, `parentUuid`, `isSidechain`, `timestamp` (ISO-8601 `...Z`), `cwd`,
`gitBranch`, `version`, `message`.

Assistant block types seen: `thinking`, `text`, `tool_use`.

### Algorithm / behavior

```
1. is_claude_session_jsonl(path):
     - suffix == ".jsonl"
     - path resolves under ~/.claude/projects/
     - first N non-blank lines parse as dicts carrying "sessionId" and a
       "type" in {user, assistant, system}
2. parse(filepath):
     for each record:
       - skip unless type in {user, assistant}
       - skip when isSidechain is True            (see What NOT to build)
       - content:
           str          -> use as-is
           list[block]  -> join the text of blocks whose type == "text"
                           SKIP blocks of type thinking / tool_use / tool_result
       - STRIP injected-context wrappers before emitting (see Content hygiene)
       - drop the message when the surviving text is empty
       - emit {role, content, timestamp, session_id, workspace_directory: cwd,
               source_type: "claude_session"}
```

### Content hygiene (do not skip this — it is the cost/quality trap)

Claude Code injects large blocks into `user` messages that are **not** user
speech. Indexing them raw would re-embed the same boilerplate in every chunk of
every session:

- `<system-reminder>…</system-reminder>` — contains the **entire CLAUDE.md**
  (currently ~10 KB) on the first user turn of every session, plus git status
  and memory blocks.
- `<local-command-caveat>…</local-command-caveat>`, `<command-name>`,
  `<command-message>`, `<command-args>`, `<local-command-stdout>` — slash-command
  plumbing.

Strip these wrappers **and their contents** before emitting. A session whose
user text is empty after stripping emits no message.

### Output / contract

`parse()` returns `list[dict]` matching the existing canonical shape:

```python
{"role": "user" | "assistant",
 "content": str,                  # non-empty, stripped
 "timestamp": str | None,         # ISO-8601 as found
 "session_id": str | None,
 "workspace_directory": str | None,
 "source_type": "claude_session"}
```

---

## Cost gate (read before wiring anything to watch)

This session's diagnosis: one prompts-only transcript
(`~/.codex/history.jsonl`) generated **44,770 of 79,566 active units — 56% of
the serving corpus** — because convmem re-summarizes a whole transcript on every
append, at 132 paid calls per touch. It accounted for 94% of DeepSeek traffic
and 100% of the 900-second index timeouts.

Claude sessions are append-heavy and long. Adding `~/.claude/projects` to
`[sources].paths` would reproduce that pattern on a new, larger source, and the
append-cursor fix (`incremental_jsonl.py`) is hard-scoped to
`jsonl_kiro_session` (`incremental_jsonl.py:42`, `:526`) and gated behind Arc
Codex, so it cannot absorb it.

**Therefore:** build and register the adapter so explicit
`convmem index --file` works. Do **not** add the directory to `[sources].paths`
or `[watch].extra_paths`. That is a separate Ryan decision with its own cost
argument.

---

## What NOT to build

- **No watch/source wiring.** See **Cost gate**.
- **No `thinking`-block ingestion.** Internal reasoning is high-volume and not
  durable knowledge; it would dominate distilled units.
- **No `tool_use` / `tool_result` ingestion.** These carry whole file contents
  and command output; they are the single largest content class in a transcript.
- **No sidechain (subagent) transcripts** in v1. `isSidechain: True` records are
  a separate conversation tree; folding them into the parent inline would
  interleave two dialogues. Defer to a later slice.
- **No `--supersede` / re-index policy change**, no chunking change, no
  retrieval or scoring change.
- **No Arc Codex work.** This adapter must not touch `incremental_jsonl.py`.

---

## Test expectations

Focused tests in `tests/test_claude_session_jsonl.py`, using `tmp_path`
fixtures only — no live corpus, no `~/.claude` reads:

1. **detects a well-formed transcript:** a `.jsonl` under a fake
   `~/.claude/projects/<slug>/` with `sessionId` + `type` → `is_*` True.
2. **rejects neighbours:** a Cursor `agent-transcripts` file, a Codex rollout,
   and a bare `.jsonl` elsewhere → `is_*` False, and `detect_format` still
   returns their own formats (no misclassification).
3. **string user content passes through**, assistant **block list flattens to
   `text` blocks only** — `thinking` and `tool_use` absent from output.
4. **`<system-reminder>` and `<local-command-*>` wrappers are stripped**,
   including multi-line and multiple occurrences in one message.
5. **a message that is empty after stripping is dropped**, and does not emit a
   blank-content dict.
6. **`isSidechain: True` records are excluded.**
7. **non-message types** (`attachment`, `mode`, `ai-title`, …) produce nothing.
8. **timestamps and session_id survive**; a record missing `timestamp` yields
   `None` rather than raising.
9. **malformed line tolerance:** an unparseable line is skipped, not fatal
   (match `iter_jsonl_dicts` behaviour).

---

## Acceptance criteria

- [ ] `convmem index --file <a real Claude transcript>` reports
      `files_processed=1` with a non-zero `units_indexed`.
- [ ] `detect_format()` returns `jsonl_claude_session`; `TOOL_BY_FORMAT` maps it
      to `claude`.
- [ ] No existing adapter changes classification (run
      `tests/test_naturalistic_v2_adapters.py` and the kiro/copilot/codex
      adapter tests).
- [ ] `~/.claude/projects` appears in **neither** `[sources].paths` nor
      `[watch].extra_paths`.
- [ ] No regression in existing suite.
- [ ] Ruff / pylint clean per repo gates.

---

## Branch convention

```
feat/2026-09-18-claude-transcript-adapter
```

Push immediately after each commit. Open PR when acceptance criteria pass.

---

## Related work (this session, already landed on branches)

| What | Where |
|------|-------|
| Watch re-spawn loop fix (9 files stuck re-indexing forever) | `fix/2026-09-17-watch-skip-hash-parity` → `d4056e4` |
| `index --file` silent-success fix + provider fail-fast | same branch, follow-up commit |
| `~/.codex/history.jsonl` exclusion + `[sources]` narrowing | live config (not in git) |

---

## Related files

| What | Path |
|------|------|
| Model to copy | `adapters/copilot_session_jsonl.py` |
| Registration | `adapters/detect.py:31,50,83` |
| Shared JSONL helpers | `adapters/jsonl_io.py` |
| Canonical message consumer | `ingest.py` (`chunk_messages`, `_index_one_file`) |
| Track A instruction this unblocks | `~/.claude/CLAUDE.md` § "Claude — handoff vs record" |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [ ] `STATUS-*.md` Update Log line — n/a, this is not arc-tracked work
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] Confirm the Ryan GATE is cleared before writing code
- [ ] `convmem work start feat claude-transcript-adapter`
