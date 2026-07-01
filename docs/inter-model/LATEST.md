# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-07-01  
**Live counts:** run `convmem brief` — do not trust stale numbers here.

## Active handoff

- **Repo organization (2026-06-30):** **shipped** (Option A — root `LATEST.md` renamed to [`SYNTHESIS-STATUS.md`](../../SYNTHESIS-STATUS.md)). Runbook + trail: [`docs/archive/inter-model/2026-06-30-org-planning/`](../archive/inter-model/2026-06-30-org-planning/). Log: [`docs/logs/2026-06-30-v4-execution.md`](../logs/2026-06-30-v4-execution.md).

**Phase 1 gate:** **CLOSED.** Documents `13bf8547` PASS, linuxbrew `77a57494` PASS. Strict script + `--exclude Search` is the enforceable path for graded workspace_local smokes.

**Phase 2 gate — CLOSED (2026-06-29):** `f358d4f0` — `cn --auto` on Documents, PARTIAL ritual, v5 payload PASS (`inventory.total: 0`). **Qwen Continue verify lane complete.**

**Phase 2 (optional):** superseded — see Phase 2 section in [`CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md).

**Archive:** [`HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md`](HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md). Tarball removed during residue cleanup.

## State

- **Global protocol:** **Closed.** All active surfaces **PASS** alien soak + post-permissions retest (Ryan). See `SOAK-REPORT-2026-06-25.md`.
- **Gap-fix (pre-P2):** Deploy permissions verify, Crush session-close slice, Continue trim template, verification matrix, grader alien check — **shipped**. Ryan manual: Continue trim + Codex/blank-dir soaks.
- **Deployed:** Cursor `.mdc`, Kiro steering + `permissions.yaml` (incl. `echo *`), Crush Tier A + `crush.json` permissions + bash hook, Continue MCP `instructions=`.
- **Post-permissions retest (Ryan):** **Cursor PASS ×2**, **Kiro PASS**, **Crush PASS**, **Continue qwen3-coder:30b PASS** — no convmem permission prompts.
- **ChatGPT Tier C:** out of scope (ignored).
- **Corpus:** see `convmem brief` (snapshot 2026-06-30: **3575** units, **635** summaries); `doctor` all PASS.
- **P2 gate:** still **hold** (MCP `unresolved` tool optional next).
- **Tests:** run `convmem brief --with-tests` or pytest when needed.

## Architecture diagram

```
flowchart TD
  canonical["config/agent-protocol.md\n(canonical SSoT)"]
  mcp["mcp_server.py\nloads MCP slice"]
  cursor["~/.cursor/rules/convmem.mdc"]
  codex["~/.codex/AGENTS.md"]
  kiro["~/.kiro/steering/convmem.md"]
  crush["~/.config/crush/rules/convmem.md"]
  continue["~/.continue/config.yaml rules"]
  chatgpt["docs/chatgpt-pack/\ncustom-instructions.txt"]
  recover["docs/RECOVER.md +\ndeploy script"]

  canonical --> mcp
  canonical --> cursor
  canonical --> codex
  canonical --> kiro
  canonical --> crush
  canonical --> continue
  canonical --> chatgpt
  canonical --> recover
```

## Decision

- Inter-model markdown = archive; **ledger + brief** = truth.
- **Change feed** (Codex): deferred until payoff review **2026-07-07**.
- **Crush tier:** Tier A (shell + MCP) — soak #8 showed MCP-only rules ignored; redeployed with shell ritual.
- **P2 gate held:** Do not accelerate. Fix surface coverage first, then re-evaluate MCP tools.

## Record a fact (two commands)

```bash
convmem record -i                  # draft (interactive)
convmem record --approve-last      # finish — indexes automatically
```

Kiro: add `--signer kiro-review`. Legacy CLI name: `propose_decision`.

## Session close (all models)

Read `docs/inter-model/SESSION-CLOSE-RECORD.md`. Output:

```bash
convmem record --relates-to <id> --summary "..." --rationale "..." --author ...
convmem record --approve-last
```

Search for `--relates-to` (never topic slugs). Fallback root: `dec_prop_20260623_161428_c311`.

### Close chain (newest first)

| Layer | Ledger id |
|-------|-----------|
| **Phase 2 deployment (Crush slice + soak report)** | `dec_prop_20260625_233830_b9af` |
| **Continue+Crush alien-workspace fail: zero convmem** | `dec_prop_20260625_225404_11cf` |
| **Continue alien-workspace fail: pavlomassage-practice** | `dec_prop_20260625_223006_528c` |
| **Soak: alien-workspace spot-check logged** | `dec_prop_20260625_220647_47d9` |
| **Global protocol post-deploy soak** | `dec_prop_20260625_203408_f9b3` |
| **Thai Massage image darkening fix** | `dec_prop_20260623_215943_5abe` |
| **Docker/Podman stack fix** | `dec_prop_20260624_025115_862b` |
| **Protocol root (fallback)** | `dec_prop_20260623_161428_c311` |

**Rule:** chain under the **newest relevant** id from `search_fast`, not a ledger you only cited during a test.

## Next

- **Default:** `convmem doctor` → `brief` → `unresolved` (shell) or MCP `brief()` first (MCP-only); `search_fast` before guessing.
- **Ryan manual:** See [VERIFICATION-MATRIX.md](VERIFICATION-MATRIX.md) — Continue `rules:` trim, Codex alien soak, blank-dir checks.
- **Change feed:** hold until **2026-07-07**.
- **P2:** MCP `unresolved` tool — **hold** until post-fix matrix green.

### Optional close (Ryan — search for newer `--relates-to` first)

```bash
convmem record \
  --relates-to dec_prop_20260625_233830_b9af \
  --summary "Global convmem protocol: all surfaces PASS + gap-fix deploy" \
  --rationale "Cursor/Kiro/Crush/Continue qwen verified; permissions echo*; deploy verify shipped; P2 deferred." \
  --author ryan
convmem record --approve-last
```
