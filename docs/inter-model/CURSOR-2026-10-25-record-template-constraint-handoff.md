# Implementation Handoff: add the required constraint flag to every record template

**Date:** 2026-10-25
**Author:** Claude (ad-hoc cloud migration follow-up)
**For:** Cursor (Composer)
**Authorization:** Ryan, 2026-10-25, verbal: "I trust your judgment on all
standard choices" while reviewing the loose ends that included this fix.
Implementation starts when Ryan pastes the prompt into Cursor.
**Arc:** none (ad-hoc)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | handoff: `docs/2026-10-25-record-template-constraint-handoff`; implementation: `fix/2026-10-25-record-template-constraint` from `origin/main` |
| **Tip SHA** | see `git log -1 origin/docs/2026-10-25-record-template-constraint-handoff` |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Ryan pastes the Cursor prompt; Ryan merges; Ryan approves the live-surface deploy after merge |
| **Track A ingest** | `~/.claude/projects/-home-lauer-Projects-convmem/d1951787-496f-4193-94a0-1387576053af.jsonl` |

---

## What to build

Every session-close template that tells a model how to write a ledger record
must produce a command that `convmem record` accepts.

**Why this exists:** `convmem record` rejects a proposal without at least one
`--constraint` (or the exact sentinel `none-identified`):

```
--constraint is required; use the exact sentinel 'none-identified' when none are identified
```

The template in the protocol source, every generated agent surface,
`brief.py` and `SESSION-CLOSE-RECORD.md` still shows the older form with only
`--relates-to`, `--summary`, `--rationale` and `--author`. On 2026-10-25 Ryan
ran a record block built from that template, it failed, and approval then
reported "No pending drafts to approve". Every model following the template
hands Ryan a block that fails the same way.

---

## Integration point

- `propose_decision.py:1102` `_normalize_constraints` — the rule (do not
  change it).
- `convmem.py:1388` — the `--constraint` option (repeatable; also `--alternative`).
- `config/agent-protocol.md:229-236` — canonical template inside
  `SESSION_CLOSE_START`/`SESSION_CLOSE_END`.
- `brief.py:927` — the one-line session-close hint printed by `convmem brief`.

Current template:

```bash
convmem record \
  --relates-to <ledger_id> \
  --summary "<one sentence>" \
  --rationale "<why this decision>" \
  --author <model-name>
convmem record --approve-last
```

---

## Specification

### Inputs

Files on `origin/main` (4b4796b) that carry a live template or flag list
without `--constraint`:

| File | How to change it |
|------|------------------|
| `config/agent-protocol.md` | edit (canonical source) |
| `config/agent-protocol-mcp.txt`, `config/cursor-rules-convmem.mdc.example`, `config/kiro-steering-convmem.example.md`, `config/copilot-agents-convmem.example.md`, `config/copilot-instructions-convmem.example.md`, `config/claude-memory-convmem.example.md`, `config/crush-rules-convmem.example.md`, `config/opencode-instructions-convmem.example.md`, plus any other output | regenerate with `scripts/generate-agent-protocol.sh`; never hand-edit |
| `config/continue-rules-session-close.example.yaml` | edit by hand if the generator does not write it (check the script first) |
| `brief.py` (line 927) | edit; then update `tests/golden/watch-oom-stream-brief/c0-render.md` line 51 to match |
| `docs/inter-model/SESSION-CLOSE-RECORD.md` | edit the main template (line ~70), the bare example (line 49) and the checklist (line ~229) |
| `docs/CHATGPT-PROPOSE-DECISION-BRIEF.md` (line ~115), `docs/chatgpt-pack/README-START-HERE.md` (line ~113) | edit; regenerate `docs/chatgpt-pack/custom-instructions.txt` if it carries the template |
| `docs/builder-reference/ousterhout-builder-digest.md` (line ~311) | add `--constraint` to the listed public flags |

### Behavior

New template shape:

```bash
convmem record \
  --relates-to <ledger_id> \
  --summary "<one sentence>" \
  --rationale "<why this decision>" \
  --constraint "<hard constraint this decision must respect>" \
  --author <model-name>
convmem record --approve-last
```

Add one sentence next to it: repeat `--constraint` for each constraint; use
exactly `--constraint none-identified` when there are none (it cannot be
combined with other constraints); `--alternative "<rejected option>"` is
optional and repeatable. Add a checklist line in `SESSION-CLOSE-RECORD.md`:
"Includes at least one `--constraint` (or exactly `none-identified`)".

Keep the `brief.py` hint on one line, for example:
`convmem record --relates-to … --summary … --rationale … --constraint … --author …`.

### Output / contract

- Only text changes. The record CLI and its validation stay as they are.

---

## What NOT to build

- Do not change `_normalize_constraints`, the CLI options or the ledger format.
- Do not edit historical documents: `docs/archive/**`, `docs/logs/**`,
  dated handoffs and `handoff-tar-*` bundles, `BUILT-PLANS-*`, research packs,
  and the dated example record in `TEAM-CHARTER-2026-07-06.md`. They record
  what was true then.
- **Do not run `scripts/deploy-agent-protocol.sh`.** It copies over
  `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`, which hold hand-written
  sections Ryan wants kept. Deploying is a separate step after merge (below).
- No changes to the live watcher, runtime or config.

---

## Test expectations

1. **Template is accepted (new test, for example
   `tests/test_record_template_constraint.py`):** extract the template block
   between `SESSION_CLOSE_START` and `SESSION_CLOSE_END` in
   `config/agent-protocol.md`, fill the placeholders with fixture values, and
   run it through the record CLI's argument parsing and `propose` validation
   against a `tmp_path` config. Expect the draft to be created. At `origin/main`
   this test must fail with the `--constraint is required` error.
2. **Every live surface carries the flag:** for each generated slice, `brief.py`,
   `SESSION-CLOSE-RECORD.md` and the two ChatGPT docs, any line that starts a
   `convmem record` template with `--relates-to` is followed by a
   `--constraint` line in the same block. Must fail at `origin/main`.
3. **Generated files are current:** run the generator and assert `git diff
   --exit-code` on its outputs (or reuse an existing freshness check if one
   exists).
4. The existing golden test for the brief render passes with the updated
   golden file.

Use `tmp_path`; no live corpus, ledger or home-directory config.

---

## Acceptance criteria

- [ ] Tests 1 and 2 fail at `origin/main` and pass on the branch
- [ ] Generator output committed and unchanged on a rerun
- [ ] No historical document changed (check with
      `git diff --stat origin/main -- docs/archive docs/logs`)
- [ ] Deploy script not run; `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` untouched
- [ ] No regression in the existing suite (use main's Safe Harbor `run-ci`
      launcher when comparing branch tip with main)
- [ ] Ruff / pylint clean per repo gates
- [ ] PR body includes the post-merge deploy note below

---

## After merge (Ryan-gated deploy)

Patch the live surfaces from the merged diff instead of copying: back up
each target, then apply `git diff <old>..<new> -- config/<file>` to
`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` and the other deployed copies.
A plain copy is fine only where the live file has no lines of its own.

---

## Branch convention

```
fix/2026-10-25-record-template-constraint   (implementation, from origin/main)
```

Push immediately after each commit with an explicit refspec
(`git push -u origin "${branch}:refs/heads/${branch}"`; brace the variable
under zsh). Ryan squash-merges unless the PR says **Do not squash**.

---

## Related files

| What | Path |
|------|------|
| Validation rule | `propose_decision.py` (`_normalize_constraints`) |
| Record CLI options | `convmem.py` (`record` command) |
| Canonical protocol | `config/agent-protocol.md` |
| Generator | `scripts/generate-agent-protocol.sh` |
| Session-close guide | `docs/inter-model/SESSION-CLOSE-RECORD.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet with link and resume state
- [x] `STATUS-*.md` Update Log line: not applicable (no arc)
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Confirm you are Cursor; if not, stop
- [ ] Read this file before the first edit
- [ ] Work on `fix/2026-10-25-record-template-constraint` in your own worktree

<!-- src: ../../propose_decision.py — constraint rule and error text -->
<!-- ref: ./SESSION-CLOSE-RECORD.md — template to update -->
