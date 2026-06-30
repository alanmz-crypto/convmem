# DeepSeek R1 handoff — Continue CLI workspace-local smoke verification

**Date:** 2026-06-29  
**From:** Cursor Auto (post-Codex gauge)  
**To:** DeepSeek R1 (`deepseek-reasoner` in Continue)  
**Surface:** **continue-cli only** (`cn`) — Ryan does **not** use VS Code/Cursor Continue extension for these smokes  
**Goal:** Run and grade folder-state smokes on **workspace_local** cwds; report PASS / PARTIAL / FAIL with session UUID or transcript path

---

## Problem (what you're verifying)

Ryan prompts from an alien cwd:

> What is the current state of this folder?

**PASS:** turn 1 = MCP `folder_state()` or `brief()` before `List` / `Read` / generic `Bash`.  
**PARTIAL:** convmem on turn 2+ after `Bash` or `List` first.  
**FAIL:** no convmem; shallow answer from directory names only.

**Do not** treat a correct answer via `Read`/`Bash` as pass — named MCP tool discipline is the test.

---

## Root cause (already proven — do not re-litigate)

| Finding | Evidence |
|---------|----------|
| `cn --auto` **ignores** `--exclude` | Continue docs; `725e9e78` List-first on `/home/linuxbrew` |
| Strict script enforces turn-1 convmem | `77a57494` PASS — `folder_state()` turn 1 via `cn-convmem-smoke.sh` |
| `cn --auto` on workspace_local = best-effort PARTIAL | `e46bb58d` (`~/Documents`), `5a5e6f0e` (`~/WordPress/scripts`) |
| MCP `workspace_local` brief trims global noise | `mcp_server.py` — empty `projects[]`, `workspace_hint`, strip global `recent_decisions` |

**Enforceable path:** `cn-convmem-smoke.sh` (no `--auto`).

---

## Session evidence (baseline before your run)

| Session | cwd | Mode | Turn 1 | Verdict |
|---------|-----|------|--------|---------|
| `77a57494` | `/home/linuxbrew` | strict script | `folder_state` | **PASS** |
| `e46bb58d` | `~/Documents` | `cn --auto` | `Bash` → turn 2 `folder_state` | **PARTIAL** |
| `5a5e6f0e` | `~/WordPress/scripts` | `cn --auto` | `Bash` → turn 2 `folder_state` | **PARTIAL** |
| `725e9e78` | `/home/linuxbrew` | `cn --auto` | `List` | **FAIL** |
| `62c9a903` | `~/Projects/convem` | `cn --auto` | `brief` | **PASS** |
| `cbf6e0b3` | `~/Projects/ponytail` | `cn --auto` | `brief` | **PASS** |

No new Continue session JSON was written after **16:18** on 2026-06-29 (Codex session did not complete interactive smokes).

---

## What shipped (test against this)

### MCP (`mcp_server.py`)

- `workspace_local` brief mode for alien cwds (not `~/Projects|WordPress|GitClones`, not system runbook)
- `folder_state()` — prompt-matched alias for `brief()`
- Ignore `project=<basename>` on workspace_local (prevents fake `focus_project: linuxbrew`)
- Cwd-aware MCP `instructions=` at spawn
- `search_fast` / `ask` / `stats` blocked until `brief()` on workspace_local + system runbook

### Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/cn-convmem-smoke.sh`](../../scripts/cn-convmem-smoke.sh) | Canonical entry — any cwd |
| [`scripts/cn-workspace-convmem.sh`](../../scripts/cn-workspace-convmem.sh) | Excludes List/Read/Bash; optional `CONVMEM_CONTINUE_TIMEOUT` + transcript |
| [`scripts/grade-continue-session.sh`](../../scripts/grade-continue-session.sh) | Grades `~/.continue/sessions/<uuid>.json` |
| [`scripts/verify-continue.sh`](../../scripts/verify-continue.sh) | Wiring check (run first) |
| [`scripts/restart-convmem-mcp.sh`](../../scripts/restart-convmem-mcp.sh) | Kill stale MCP; `cn` spawns fresh |

### Config

- **`~/.continue/config.yaml`** — select **DeepSeek R1** (`provider: deepseek`, `model: deepseek-reasoner`) via `/model` in `cn`
- **qwen3-coder:30b** is the reference PASS model for regression; R1 is the test subject here

### Codex follow-up (harness only)

Codex added bounded transcript capture to `cn-workspace-convmem.sh`:

```bash
CONVMEM_CONTINUE_TIMEOUT=120 scripts/cn-convmem-smoke.sh /home/linuxbrew
```

- Prints transcript path to stderr (e.g. `/tmp/convmem-continue.*.log`)
- Exit code `124` = timeout (expected if CLI stays interactive)
- **8s is too short** for qwen3-coder:30b; use **120–180s** minimum
- Codex's 8s linuxbrew transcript captured **no tool calls** — only startup rules

---

## What DeepSeek R1 should do

### 0. Tier A ritual (this repo)

```bash
convmem doctor
convmem brief --stdout-only
bash ~/Projects/convmem/scripts/restart-convmem-mcp.sh
bash ~/Projects/convmem/scripts/verify-continue.sh
```

All must pass before smokes.

### 1. Primary test — interactive strict smokes

**Do not use `cn --auto`.** Use the strict wrapper:

```bash
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents
~/Projects/convmem/scripts/cn-convmem-smoke.sh /home/linuxbrew
~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/WordPress/scripts
```

In each `cn` session:

1. `/model` → select **DeepSeek R1**
2. Accept default prompt: *What is the current state of this folder?*
3. Let the session run until you have a useful answer or clear failure
4. Exit the CLI (`Ctrl+C` or quit) so session JSON is flushed

### 2. Grade each run

```bash
ls -t ~/.continue/sessions/*.json | grep -v sessions.json | head -3
~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<uuid>.json
```

Look for `alien_ritual PASS` / `PARTIAL` / `FAIL` in grader output.

### 3. Optional — bounded transcript path (automation-friendly)

If interactive exit is awkward, use timeout + transcript (grade manually from log):

```bash
CONVMEM_CONTINUE_TIMEOUT=180 \
  ~/Projects/convmem/scripts/cn-convmem-smoke.sh ~/Documents

# Then inspect printed transcript path:
rg -n 'folder_state|search_fast|brief|List|Read|Bash' /tmp/convmem-continue.*.log | head -40
```

PASS in transcript = `folder_state` or `brief` appears **before** any `List`/`Read`/generic `Bash`.

### 4. Regression (optional)

Repeat one cwd with **qwen3-coder:30b** under strict script — expect PASS turn 1 (`77a57494` baseline).

### 5. Report back

For each cwd tested, report:

| cwd | Model | Turn 1 tool | Grader verdict | Session UUID or transcript |
|-----|-------|-------------|----------------|----------------------------|
| `~/Documents` | DeepSeek R1 | ? | ? | ? |
| `/home/linuxbrew` | DeepSeek R1 | ? | ? | ? |
| `~/WordPress/scripts` | DeepSeek R1 | ? | ? | ? |

---

## DeepSeek R1–specific caveats

1. **Cloud reasoner** — may emit tool JSON as chat text instead of native tool calls (same class of failure as qwen2.5-coder:14b). If you see `<function=…>` or raw JSON with no MCP execution, that's **FAIL** (tool leak).
2. **Do not rescue weak `ask`** with `Read`/`Bash` — that fails named-tool verify even if the answer is correct.
3. **Do not pass `project=linuxbrew`** on workspace_local — use unscoped `folder_state()`.
4. **Do not cite global `inventory.total`** as “files in this folder” — use `workspace_hint` + scoped `search_fast`.
5. **`cn --auto` on workspace_local** — document as PARTIAL at best; not the primary test path.

---

## Open problems (report if you hit them; fixing optional)

1. Remove `_debug_log` from `mcp_server.py` after strict smokes PASS on Documents + linuxbrew
2. Transcript auto-grader (parse log → PASS/PARTIAL/FAIL) — not shipped yet
3. XML tool leak / Read `path` vs `filepath` param mismatch (Continue/qwen quirk)
4. CORE 8 system runbook smokes under `cn --auto`: `/etc`, `/boot/loader/entries`
5. Codex left uncommitted diffs in `chroma_store.py` (debug JSONL), `query.py`, `requirements.txt` — orthogonal to this smoke; do not expand scope unless Chroma breaks

---

## Protected paths

- **Tier 1:** `~/.local/share/convmem/` — no delete via agent shell
- **Tier 2:** `~/.config/convmem/`
- **Tier 3:** `~/Projects/convmem/` — edit freely
- **`~/.continue/config.yaml`** — Ryan manual merge unless smoke fix requires documented edit

---

## Related files

- [`HANDOFF-CODEX-2026-06-29-continue-workspace-smoke.md`](HANDOFF-CODEX-2026-06-29-continue-workspace-smoke.md) — prior handoff + code map
- [`CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md) — full verify matrix
- [`SESSION-CLOSE-RECORD.md`](SESSION-CLOSE-RECORD.md) — record block rules

---

## Record block (Ryan runs — after your test report)

```bash
convmem record \
  --relates-to dec_prop_20260629_213127_1f62 \
  --summary "DeepSeek R1 Continue workspace_local smokes: strict script graded on Documents/linuxbrew/scripts; harness timeout+transcript documented." \
  --rationale "Handoff HANDOFF-DEEPSEEK-R1-2026-06-29-continue-workspace-smoke.md for R1 verification. Baseline: 77a57494 PASS strict linuxbrew; cn --auto PARTIAL on Documents/scripts. Codex added CONVMEM_CONTINUE_TIMEOUT transcript path (120s+ required). R1 results: <fill PASS/PARTIAL/FAIL per cwd + session UUIDs>." \
  --author deepseek-r1
convmem record --approve-last
```

Replace the `<fill …>` line in `--rationale` with your actual results before Ryan approves.
