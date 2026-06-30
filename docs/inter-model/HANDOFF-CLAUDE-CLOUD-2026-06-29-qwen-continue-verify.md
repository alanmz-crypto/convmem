# Claude Cloud handoff — Qwen Continue CLI verification

**Date:** 2026-06-29  
**From:** Cursor Auto (synthesis of Cursor + Codex + DeepSeek R1 work)  
**To:** Claude Cloud (Opus or Sonnet)  
**Surface under test:** **Continue CLI (`cn`)** + **qwen3-coder:30b** (primary) + qwen2.5-coder:14b (daily tier)  
**Ryan's machine:** miniPC, Arch Linux, Ollama local, convmem MCP on localhost

---

## Your role (Claude Cloud)

You **cannot** run `cn`, Ollama, or convmem on Ryan's miniPC from the cloud. You are the **verification architect**:

1. **Review** the test matrix, shipped fixes, and session evidence in this archive.
2. **Produce a ordered test plan** Ryan runs locally (copy-paste commands).
3. **Grade** results Ryan pastes back (grader output, session UUIDs, transcript snippets).
4. **Recommend policy:** strict script vs `cn --auto` on alien cwds; whether qwen30b matrix is “good enough.”
5. **Flag gaps** the three prior agents missed (if any).

Do **not** propose more MCP instruction wording unless you identify a specific untested failure mode.

---

## What we're testing

Ryan uses **`cn --auto`** daily. The verification bar has two layers:

| Layer | Meaning |
|-------|---------|
| **Alien-workspace ritual** | Turn 1 = MCP `folder_state()` or `brief()` (or shell `convmem doctor`/`brief`) before List/Read/Bash |
| **Named-tool verify** | Model must use the **named MCP tool**; correct answers via Read/Bash = **FAIL** |

**Primary model:** **qwen3-coder:30b** — `provider: openai`, `apiBase: http://localhost:11434/v1`, `apiKey: ollama` (native Ollama tool API; avoids XML tool leak).

**Prompt (folder-state smokes):**

> What is the current state of this folder?

---

## Architecture (what convmem + Continue do)

```
Ryan: cn [--auto] --config ~/.continue/config.yaml
  → Continue spawns MCP subprocess (mcp_server.py) with cwd = workspace
  → MCP instructions= include ACTIVE SESSION block for workspace_local / system_runbook
  → Model may call: folder_state, brief, search_fast, ask, related, stats (+ Continue built-ins)
```

**workspace_local** cwds: `~/Documents`, `/home/linuxbrew`, `~/Pictures`, etc. — not `~/Projects/*`, not system runbook.

**Key MCP behaviors (v5, 2026-06-29):**

- `folder_state()` = alias for `brief()` on folder/cataloging prompts
- `workspace_local` brief: strips global noise, **zeros** `units`/`summaries`/`inventory`/`services`/`coordination` so model cannot cite corpus size as folder stats
- `search_fast`/`ask`/`stats` blocked until `brief()` on workspace_local + system runbook
- MCP spawn warns: `filepath=` not `path=` for Read; no `<function=...>` XML as chat text

---

## Session evidence (baseline — before your test run)

### qwen3-coder:30b

| Session | cwd | Mode | Turn 1 | Verdict |
|---------|-----|------|--------|---------|
| `77a57494` | `/home/linuxbrew` | **strict script** | `folder_state` | **PASS** |
| `62c9a903` | `~/Projects/convem` | `cn --auto` | `brief` | **PASS** |
| `cbf6e0b3` | `~/Projects/ponytail` | `cn --auto` | `brief` | **PASS** |
| `5a5e6f0e` | `~/WordPress/scripts` | `cn --auto` | Bash → turn 2 `folder_state` | **PARTIAL** |
| `e46bb58d` | `~/Documents` | `cn --auto` | Bash → turn 2+ convmem | **PARTIAL/FAIL** |
| `725e9e78` | `/home/linuxbrew` | `cn --auto` | `List` | **FAIL** |

### DeepSeek R1 (contrast — not your test subject)

| Session | cwd | Turn 1 | Verdict |
|---------|-----|--------|---------|
| `03b3b6e8` | `~/Documents` | `Search` → turn 2 `folder_state` | **PARTIAL** |
| `3848ff46` | `/home/linuxbrew` | `Search` → turn 2 `folder_state` | **PARTIAL** |

---

## What three agents already tried (don't repeat)

| Agent | Delivered | Conclusion |
|-------|-----------|------------|
| **Cursor** | `workspace_local` brief, `folder_state()`, strict scripts, grader, MCP gates | qwen30b **PASS** under strict script; **FAIL/PARTIAL** under `cn --auto` on alien cwds |
| **Codex** | Chroma debug (orthogonal), `CONVMEM_CONTINUE_TIMEOUT` + transcript capture | Harness improvement; 8s timeout too short; no new PASS sessions |
| **DeepSeek R1** | v5 fixes: remove debug log, zero global stats on workspace_local, MCP quirk warnings, docs | Fixes answer quality; **cannot** fix `cn --auto` turn-1 discipline |

**Structural limit (proven):** `cn --auto` **ignores** `--exclude`. Continue docs confirm. No config/MCP fix found.

**Enforceable path:** `cn-convmem-smoke.sh` → `cn-workspace-convmem.sh` (no `--auto`; excludes List/Read/Bash).

---

## Test plan for Ryan (you should refine/order this)

### Phase 0 — wiring

```bash
convmem doctor
bash ~/Projects/convmem/scripts/verify-continue.sh
bash ~/Projects/convmem/scripts/restart-convmem-mcp.sh
```

All must pass.

### Phase 1 — post-v5 strict smokes (qwen3-coder:30b) — **highest priority**

Unverified after v5 stats-zeroing. Run **interactive** (not headless `-p`):

```bash
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents
~/Projects/convmem/scripts/cn-convmem-smoke.sh /home/linuxbrew
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/WordPress/scripts
```

In each session: `/model` → **qwen3-coder:30b**.

Grade:

```bash
ls -t ~/.continue/sessions/*.json | grep -v sessions.json | head -3
~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<uuid>.json
```

**PASS criteria:**

- `alien_ritual PASS` (turn 1 `folder_state` or `brief`)
- Answer cites `workspace_hint`, `search_fast` hits, local README — **not** global corpus counts

### Phase 2 — Ryan's daily mode (`cn --auto`) — policy test

Document outcome; do not expect strict PASS on alien cwds:

```bash
cd ~/Documents && cn --auto --config ~/.continue/config.yaml
# prompt: What is the current state of this folder?
```

Repeat for `/home/linuxbrew`. Grade sessions. Expect **PARTIAL** or **FAIL** on turn-1 ritual; check whether **v5** improved answer quality on turn 2+.

### Phase 3 — CORE 8 system runbook (optional)

```bash
cd /etc && cn --auto --config ~/.continue/config.yaml
# What is the state of my pacman configuration?

cd /boot/loader/entries && cn --auto --config ~/.continue/config.yaml
# What is the state of boot entries?
```

**PASS:** turn 1 `brief()` with `brief_mode: system_runbook` in JSON.

### Phase 4 — named-tool matrix (optional)

From `CONTINUE-VERIFY.md`:

- Brief one-sentence `coordination.durable_writes` quote
- `search_fast` only — practice-local ledger cite
- `ask` only — stack reset; no Read rescue

### Phase 5 — qwen2.5-coder:14b alien soak (optional)

One `cn --auto` run in alien WP dir with 14b after `openai`/v1 config. Prior FAIL: tool JSON as text.

### Phase 6 — bounded transcript (automation path)

```bash
CONVMEM_CONTINUE_TIMEOUT=180 \
  ~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents
# grep transcript for tool order (path printed to stderr)
```

Use **120–180s** minimum; 8s captures only startup rules.

---

## Grader interpretation

```bash
~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<uuid>.json
```

| Output | Meaning |
|--------|---------|
| `alien_ritual PASS (first tool: folder_state)` | **Phase 1 pass** |
| `alien_ritual PARTIAL (turn 2+ folder_state after Bash)` | Convmem used, wrong order |
| `alien_ritual PARTIAL (turn 2+ folder_state after CheckBackgroundJob)` | **Invalid** — grader now emits `SKIP (CheckBackgroundJob — agent shell artifact)`; rerun from real terminal |
| `alien_ritual FAIL (first tool: List)` | No convmem ritual |
| `GRADE: FAIL — … brief_answer` | **Phase 4 only** — ignore for Phase 1 if `alien_ritual PASS` |

**Phase 1 gate:** read `alien_ritual` line only. Top-level `GRADE: FAIL` often reflects unused Phase 4 checks in the same grader run.

### CheckBackgroundJob (agent shell — do not grade)

Running `cn-convmem-smoke.sh` from Cursor/Codex agent subprocesses can inject `CheckBackgroundJob` into session JSON before the model's first tool. **Not qwen30b behavior.** Smokes for Phase 1 must run from Ryan's **real terminal**.

### Phase 1 status — **CLOSED** (2026-06-29)

| cwd | Verdict | Session |
|-----|---------|---------|
| `~/Documents` | **PASS** | `13bf8547` |
| `/home/linuxbrew` | **PASS** | `77a57494` |
| `~/WordPress/scripts` | Optional | — |

**Policy:** strict script for graded workspace_local; `cn --auto` PARTIAL-acceptable on alien cwds (Phase 2 doc optional).

---

## Open items (your judgment)

1. **Accept `cn --auto` PARTIAL** on workspace_local as documented policy vs push Ryan to strict script?
2. **Re-smoke Documents post-v5** — sufficient to close the Qwen30b lane?
3. **Exclude Continue `Search`** in strict script (`cn-workspace-convmem.sh`) — harness gap found during R1 smokes?
4. **qwen2.5-coder:14b** — retest worth promoting to daily default?
5. **Transcript auto-grader** — ship or defer?

---

## Protected paths (Ryan's machine)

- **Do not delete:** `~/.local/share/convmem/` (corpus)
- **Do not delete:** `~/.config/convmem/`
- **Edit freely:** `~/Projects/convmem/`
- **`~/.continue/config.yaml`** — Ryan manual merge for model blocks

---

## Record block (Ryan runs after your review + smokes)

```bash
convmem record \
  --relates-to dec_prop_20260629_213127_1f62 \
  --summary "Claude Cloud reviewed Qwen Continue verify matrix; post-v5 strict smokes graded on Documents/linuxbrew/scripts." \
  --rationale "Claude handoff 2026-06-29: test plan + policy on cn --auto vs strict script. Results: <PASS/PARTIAL/FAIL per phase>. Open: <remaining gaps>." \
  --author claude-cloud
convmem record --approve-last
```

---

## Files in this archive

See `MANIFEST.txt` in the tarball root.

Key paths:

| File | Why |
|------|-----|
| `scripts/cn-convmem-smoke.sh` | Canonical strict smoke entry |
| `scripts/cn-workspace-convmem.sh` | Excludes + optional timeout/transcript |
| `scripts/grade-continue-session.sh` | Session grader |
| `scripts/verify-continue.sh` | Wiring check |
| `mcp_server.py` | workspace_local, folder_state, v5 stats zeroing |
| `tests/test_mcp_site.py` | 15 MCP unit tests (expected all pass) |
| `docs/inter-model/CONTINUE-VERIFY.md` | Full matrix + v5 fix table |
| `config/continue-models-tier-a.example.yaml` | Qwen model blocks (sanitized) |

---

## Related ledger chain

| Layer | Ledger id |
|-------|-----------|
| Continue workspace smoke (Ryan) | `dec_prop_20260629_213127_1f62` |
| Continue verify / coordination | `dec_prop_20260625_233437_8907` |
| Protocol root (fallback) | `dec_prop_20260623_161428_c311` |
