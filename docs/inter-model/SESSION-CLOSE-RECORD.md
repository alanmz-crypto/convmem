# Session close — record handoff (all models)

This doc covers **two** distinct close types. Know which one you're in.

---

## Stopping point (soft close)

**Trigger phrases:** "find a stopping point", "good stopping point", "let's wrap up", "let's pause here", "wind down", "park it"

**This is NOT a record block.** Do not output `convmem record`. Do:

1. **Finish or checkpoint current work** — leave the system stable. No half-applied DB mutations, no broken containers, no uncommitted branch changes that will confuse the next agent.
2. **Push any commits** on the working branch (remote = backup).
3. **Verbal handoff summary** — state clearly in chat:
   - What was done (bullet list, concrete).
   - What's pending / blocked (e.g. "needs reboot", "waiting on Ryan to merge").
   - What the next agent (or Ryan) should do first on resume.
4. **Index session chat (Track A):**
   ```bash
   convmem index --file <session-transcript-path>
   ```
   Use the path for your surface (Kiro: `~/.kiro/sessions/…/messages.jsonl`, Crush: `.crush/crush.db`, Cursor: agent transcript `.jsonl`, Codex: rollout `.jsonl`).
5. **If you wrote a `logs/*.md` file** (only if Ryan asked), also run Track B sync script.
6. **Do NOT** output a `convmem record` block, create new markdown files, or propose decisions.

**The stopping-point close preserves work via chat ingest (Track A). Watch auto-indexes after debounce. The next agent sees it via `brief()` + `search`.**

---

## Record block (hard close)

**Trigger phrases:** "closing", "reboot", "end session", "record block", "record this"

When Ryan says one of these: output a **terminal-ready** `convmem record` command. Ryan copy-pastes and runs it.

---

## WRONG (never output this)

```bash
# ❌ not a command
record -i session=closing summary="..." detail="..." tier1_cleaned=...

# ❌ not convmem flags
convmem record summary="..." detail="..."

# ❌ missing --relates-to (required)
convmem record --summary "..." --rationale "..." --author ryan

# ❌ human topic tag — NOT a ledger id
convmem record --relates-to "system-maintenance" --summary "..." ...
convmem record --relates-to "closing" --relates-to "backup" ...
```

`--relates-to` must be an **existing ledger id** from search (usually `dec_prop_YYYYMMDD_HHMMSS_xxxx`). **Never** invent labels like `system-maintenance`, `closing`, or `backup`.

`record` alone is **not** on PATH unless Ryan adds `alias record='convmem record'`. Always write **`convmem record`**.

---

## RIGHT (always output this shape)

**Preferred — one copy-paste command block** (Ryan runs as-is, then approve):

```bash
convmem record \
  --relates-to <ledger-id-you-looked-up> \
  --summary "<one sentence — lead with primary lane, e.g. convmem repo / system ops>" \
  --rationale "<Done / Open / Not my lane — plain English, details here>" \
  --author <model-session or ryan>

convmem record --approve-last
```

Add `--signer kiro-review` on approve **only** when Kiro signs.

**Alternate — interactive** (only if Ryan prefers prompts):

```bash
convmem record -i
# Paste when prompted: relates_to, summary, rationale, author
convmem record --approve-last
```

---

## `--relates-to` is mandatory (real ledger id only)

**Format:** `dec_prop_20260623_161428_c311` (or `dec_*`, `obs_*` from search results).  
**Not valid:** `system-maintenance`, `closing`, `convmem`, topic slugs, or quoted English phrases.

### How to pick the id

1. Run **`convmem search "<your topic> handoff"`** or MCP **`search_fast`**.
2. Copy the line **`ledger: dec_prop_…`** (or `obs_…`) from the hit — paste **exactly** into `--relates-to`.
3. If the work is **new and unrelated** (e.g. system cache cleanup, no closer parent): use protocol root  
   **`dec_prop_20260623_161428_c311`**  
   and say in rationale that this is a new maintenance thread under coordination protocol.

**Never skip step 3 with a made-up slug.** If you didn't search, say so in rationale and use `c311`.

### Chain (2026-06-23 arc — search for newer before defaulting)

| Layer | Use as `--relates-to` for next close |
|-------|--------------------------------------|
| Protocol root (fallback only) | `dec_prop_20260623_161428_c311` |
| Kiro+Cursor arc | `dec_prop_20260623_212248_fec0` |
| Codex late join | `dec_prop_20260623_212548_ed29` |
| DeepSeek late join | `dec_prop_20260623_212906_4a5a` |
| Cursor close | `dec_prop_20260623_213448_a602` |
| Cursor correction (convmem-primary) | search `Correction Cursor session convmem` |

**Rule:** chain under the **newest relevant** ledger id from search. Use **`c311`** only when no closer parent exists — and say why in rationale.

---

## Summary vs rationale

| Field | What goes here |
|-------|----------------|
| **`--summary`** | One sentence; **primary lane first** (e.g. “convmem repo work”, “system cache cleanup”, “client staging2 probe”) |
| **`--rationale`** | Details, numbers, paths, open items, what you did *not* own |

Do not hide the main topic in rationale only.

---

## Per-model defaults

| Model | `--author` | Approve signer | Lead summary with |
|-------|------------|----------------|-------------------|
| **Kiro** | `kiro-session` | `kiro-review` | design / protocol / watch direction |
| **Cursor** | `cursor-session` | `ryan` | **`convmem repo`** if that was the session |
| **Codex** | `codex-session` | `ryan` | change-feed / shell lane |
| **DeepSeek** | `deepseek-session` | `ryan` | synthesis / OOM needles |
| **Continue** | `continue-session` | `ryan` | MCP read / verify |
| **Crush** | `crush-session` | `ryan` | runtime MCP / automation |
| **ChatGPT** | `chatgpt-session` | `ryan` | strategy (Ryan runs commands) |
| **Ryan (terminal)** | `ryan` | `ryan` | whatever Ryan did |

---

## Examples (copy-paste correct)

### System ops — Crush (corrected from wrong `system-maintenance`)

**Wrong (Crush emitted this — do not copy):**
```bash
convmem record --relates-to "system-maintenance" ...   # ❌ not a ledger id
```

**Right:**
```bash
convmem record \
  --relates-to dec_prop_20260623_161428_c311 \
  --summary "Tier 1 system cache cleanup before backup: 8.5G cleared without sudo" \
  --rationale "Cleaned build/package/browser caches (~8.5G): pip, go-build, Chrome, npm, uv, Trash, thumbnails, borg. Pending (sudo): paru ~5.7G, pacman ~8.1G, journalctl vacuum ~1G. New maintenance thread — no closer ledger parent; chained to coordination protocol c311." \
  --author crush-session

convmem record --approve-last
```

### System ops — Ryan terminal (same id rule)

```bash
convmem record \
  --relates-to dec_prop_20260623_161428_c311 \
  --summary "System cache cleanup before backup: 8.5G cleared without sudo" \
  --rationale "Audited ~/.cache (~21G). Cleaned without sudo: pip ~3.9G, go-build ~1.7G, Chrome cache ~1.8G, npm ~251M, uv ~614M, Trash ~141M, thumbnails ~37M, borg ~152M. Pending (sudo): pacman -Sc ~8.1G, paru -Sc ~5.7G, journalctl --vacuum-time=30d ~1G." \
  --author ryan

convmem record --approve-last
```

### Codex late join (convmem coordination)

```bash
convmem record \
  --relates-to dec_prop_20260623_212248_fec0 \
  --summary "Codex late join: change-feed lane deferred; shell CLI to convmem" \
  --rationale "Joined after Kiro+Cursor. Change feed deferred to 2026-07-07. AGENTS.md shell. Did not drive record UX, practice :8081, Continue verify, watch lazy-import (Kiro)." \
  --author ryan

convmem record --approve-last
```

### Continue — MCP verify session (corrected from wrong author / wrong parent id)

**Wrong (Continue emitted — do not copy):**
```bash
convmem record --relates-to dec_prop_20260623_203527_c4dd ... --author "DeepSeek"
# ❌ c4dd = practice stack fact (test subject), not the coordination thread
# ❌ author must be continue-session, not model vendor name
# ❌ broken line wraps inside quotes; missing approve-last on its own line
```

**Right:**
```bash
convmem record \
  --relates-to dec_prop_20260623_215943_5abe \
  --summary "Continue MCP verify passed: brief, search_fast, ask; DeepSeek V4 in config.yaml" \
  --rationale "Agent-mode MCP tools exercised (brief willowyhollow-dev, search_fast practice-local, ask reset). Grader PASS. Added reset ledger 1403. Config: schema v1 + mcpServers; V4 Flash/Pro replaces legacy deepseek-chat/reasoner. Not client deploy or staging2." \
  --author continue-session

convmem record --approve-last
```

---

```bash
convmem record \
  --relates-to dec_prop_20260623_213448_a602 \
  --summary "Correction: Cursor session was almost exclusively ~/Projects/convmem product work" \
  --rationale "Primary lane: convmem repo — record --approve-last, brief/MCP/AGENTS/LATEST, Continue verify, SESSION-CLOSE-RECORD, practice-local lab. Not client deploy or willowyhollow-dev git audit. Touch-only: staging2 CSP probe." \
  --author cursor-session

convmem record --approve-last
```

---

## Checklist before you send the block

- [ ] Starts with **`convmem record`** (not `record`)
- [ ] Includes **`--relates-to dec_prop_…`** (or `obs_…` from search — **not** a topic label)
- [ ] Id **starts with** `dec_` or `obs_` — if it looks like English (`system-maintenance`), stop and fix
- [ ] Uses **`--summary`** and **`--rationale`** (not `detail=`, `session=`, custom keys)
- [ ] Ends with **`convmem record --approve-last`**
- [ ] Summary states **primary lane** in the first clause

Chat transcripts are indexed by watch eventually; **`record` is the curated handoff** agents should trust.
