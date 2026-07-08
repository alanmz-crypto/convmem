# Model workflow — convmem cheat sheet

**For Ryan and all agents.** When lost, start here — not a second canon.

| Doc | Role |
|-----|------|
| **This file** | Which repo, which script, which reference |
| [`docs/PLANNING-PROTOCOL.md`](PLANNING-PROTOCOL.md) | Planning OS workflow — where am I in architecture / execution / revise? |
| [`docs/planning/EXECUTION-CLOSURE-2026-07-08.md`](planning/EXECUTION-CLOSURE-2026-07-08.md) | Planning OS arc closure — frozen summary, findings, interim routes |
| [`config/agent-protocol.md`](../config/agent-protocol.md) | Session start/close (deployed to Cursor, MCP, Codex, Kiro) |
| [`SYNTHESIS-STATUS.md`](../SYNTHESIS-STATUS.md) | Cross-project digest phase status |
| [`docs/inter-model/SESSION-CLOSE-RECORD.md`](inter-model/SESSION-CLOSE-RECORD.md) | Record block format |
| [`docs/inter-model/TEAM-CHARTER-2026-07-06.md`](inter-model/TEAM-CHARTER-2026-07-06.md) | HITL team roles — lost on who does what? |

---

## Step 0 — Every session (all repos)

```bash
convmem doctor          # must exit 0
convmem brief --stdout-only
convmem unresolved      # add --site <host> for client work
```

MCP-only: `brief()` → check `unresolved_count` → `search_fast` / `ask` before history questions.

**`ask` degraded states (P1c):** `synthesis_interrupted` = partial answer before timeout;
`synthesis_failed` = citation-only fallback.

**Search recency (P1a):** `search` / `search_fast` apply `recency_boost` when
`query.recency_weight` > 0 in config — inspect `rank_score` in MCP JSON.
See [`builder-reference/notes/suggested-application-of-builder-material.md`](builder-reference/notes/suggested-application-of-builder-material.md).

**Session tracking — two tracks (do not confuse):**

- **A — Session chat** (`crush.db`, Kiro `messages.jsonl`, Codex `rollout-*.jsonl`, Cursor `agent-transcripts`): **required** at handoff — `convmem index --file <session-path>`
- **B — Log artifact** (`logs/*.md` → inter-model): only if a log was written; **does not replace A**

Ryan: **"ingest your chat"** = A · **"index the log"** = B · **"ingest everything"** = A then B. Avoid **"index what you wrote"** (models skip chat).

**Do not** `convmem record` for session-start alone. Record only when Ryan closes or substantive work finished (one conclusion, not per-finding).

---

## Step 1 — Which repo am I in?

| Workspace | Data dir | CLI |
|-----------|----------|-----|
| `~/Projects/convmem` | `~/.local/share/convmem` | `convmem` / MCP **convmem** (prod) |
| `~/Projects/convmem-lab` | `~/.local/share/convmem-lab` | `scripts/convmem-lab.sh` only — **no lab MCP** |

**Never** mix paths. Lab writes are disposable. Prod Tier 1 is backed up.

### Write boundary (enforced in CLI)

| Situation | What happens |
|-----------|----------------|
| `convmem-lab` cwd + prod config (default `convmem`) | **Blocked** — prod index/record/add/watch/refine |
| Prod repo cwd + lab config via `convmem-lab.sh` | **Allowed** (`CONVMEM_CONFIRM_LAB=1` set by wrapper) |
| Prod repo cwd + prod config | **Allowed** — normal prod work |
| Bulk prod inter-model index | **`CONVMEM_CONFIRM_PROD=1`** required by `scripts/index-inter-model-docs.sh` |

**Intentional prod write from lab cwd:** `CONVMEM_CONFIRM_PROD=1 convmem index …` (use sparingly).

**Ryan habit — you will forget the flag:** from **any** cwd, index prod session chat with:

```bash
bash ~/Projects/convmem/scripts/convmem-index-prod.sh ~/.kiro/sessions/.../messages.jsonl --force
bash ~/Projects/convmem/scripts/convmem-index-prod.sh ~/.cursor/projects/.../agent-transcripts/.../....jsonl --force
```

Same wrapper for Codex rollout, Crush `.crush/crush.db`, etc. — always prod Chroma, no lab/prod mix-up.

**Check before writes:** `convmem doctor` includes `write_lane` — shows `lane=`, `workspace=`, `write_guard=OK|BLOCKED`.

---

## Step 2 — What kind of work?

### A. Normal feature / bug / client site

1. Session ritual (Step 0)
2. Architecture or boundaries? → [`docs/builder-reference/README.md`](builder-reference/README.md) (prod only)
3. Willowy Hollow promote/deploy? → [`docs/site-reference/NOTES.md`](site-reference/NOTES.md) (pre-promote gates)
4. Implement, test, record block at close

### B. Cross-project “big picture” digest (prod)

**Read:** [`docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md`](CROSS-PROJECT-DIGEST-ATTEMPTS.md)

```bash
# Deterministic brief (no LLM) — weekly habit / smoke
~/Projects/convmem/scripts/cross-project-digest.sh --skip-ask

# Full synthesis + recency check
~/Projects/convmem/scripts/cross-project-digest.sh

# Smoke gate
bash ~/Projects/convmem/scripts/smoke-cross-project-digest.sh
```

Optional: `~/.local/share/convmem/attempts.jsonl` → digest renders **Do not retry**  
Setup: `cp config/attempts.jsonl.example ~/.local/share/convmem/attempts.jsonl`

Before editing a file with prior failures: `bash scripts/precheck-path.sh <path>` (advisory, exit 0)

**`--propose`:** queues draft in `pending_decisions.jsonl` — **Ryan reviews before approve**. Still Ryan-gated for prod habit.

### C. Lab coordination / synthesis experiments

**Read first:** [`~/Projects/convmem-lab/docs/lab-reference/NOTES.md`](../../convmem-lab/docs/lab-reference/NOTES.md)

```bash
cd ~/Projects/convmem-lab
bash lab/scripts/seed-fixtures.sh
scripts/convmem-lab.sh doctor
bash lab/scripts/compile-synthesis-brief.sh    # deterministic big picture
bash lab/scripts/smoke-synthesis.sh           # full lab gate
bash scripts/verify-lab-reference.sh
```

**Reference:** `docs/lab-reference/` in lab repo — **not** `builder-reference` unless architectural.

### D. Session close / record block

1. Read [`docs/inter-model/SESSION-CLOSE-RECORD.md`](inter-model/SESSION-CLOSE-RECORD.md)
2. `convmem search` for real `--relates-to` ledger id
3. Output copy-paste block; **Ryan runs** `convmem record --approve-last`

---

## Reference routing (avoid reading the wrong canon)

| Question | Read |
|----------|------|
| Lab gates, smoke, fail-open/closed | `convmem-lab/docs/lab-reference/` |
| Prod architecture, ledger, retrieval | `convmem/docs/builder-reference/` |
| Willowy Hollow promote / prod write gates | `convmem/docs/site-reference/` |
| Digest attempts schema | `convmem/docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md` |
| Synthesis phase / propose gate | `convmem/SYNTHESIS-STATUS.md` |

**If both apply:** builder-reference for system shape → lab-reference for lab-specific policy. Site-reference for client WP promotion only.

---

## Smoke / verify quick reference

| Gate | Command | Repo |
|------|---------|------|
| Prod digest | `bash scripts/smoke-cross-project-digest.sh` | convmem |
| Lab synthesis | `bash lab/scripts/smoke-synthesis.sh` | convmem-lab |
| Lab reference docs | `bash scripts/verify-lab-reference.sh` | convmem-lab |
| Builder reference deploy | `bash scripts/verify-builder-reference.sh` | convmem |
| Site reference docs | `bash scripts/verify-site-reference.sh` | convmem |
| Site reference surfaces | `bash scripts/smoke-site-reference-surfaces.sh` | convmem |
| Infra | `convmem doctor` | prod (lab: `convmem-lab.sh doctor`) |

---

## What agents must NOT do

- Register **convmem-lab** in MCP configs
- Run `convmem record --approve-last` without Ryan (except Kiro `--signer kiro-review` when signing)
- Run full `convmem index` / wipe Tier 1 without Ryan
- Use `builder-reference` for routine lab fixture work
- Use `lab-reference` for prod retrieval tuning (Manning eval is prod-only)

---

## Ryan one-time setup (prod do-not-retry)

```bash
cp ~/Projects/convmem/config/attempts.jsonl.example ~/.local/share/convmem/attempts.jsonl
# edit with real obs_id rows, then:
bash ~/Projects/convmem/scripts/smoke-cross-project-digest.sh
```

After protocol edits: `bash scripts/generate-agent-protocol.sh && bash scripts/deploy-agent-protocol.sh`

**Codex / DeepSeek verify this work:** [`docs/CODEX-DEEPSEEK-VERIFY.md`](CODEX-DEEPSEEK-VERIFY.md)
