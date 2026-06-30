# Cursor Auto Composer — convmem global protocol soak test

**Date:** 2026-06-25
**From:** DeepSeek R1 (Continue) — final session before soak
**To:** Cursor Auto Composer (Tier A: shell + MCP, alwaysApply `convmem.mdc` loaded)
**Duration:** ~1 week of normal use
**Goal:** Observe whether agents actually follow the protocol now that it's deployed globally

---

## What just happened

The convmem session-start protocol (`doctor → brief → unresolved → search before guessing`) used to live only in repo-level `AGENTS.md` files. Agents entering a random directory got nothing.

**Shipped and deployed today:**

| Surface | What | Path |
|---------|------|------|
| **Cursor** (you) | Global alwaysApply rule with full protocol | `~/.cursor/rules/convmem.mdc` |
| **MCP** | Expanded `instructions=` — every MCP client sees it before first tool call | `mcp_server.py` (loaded from generated `config/agent-protocol-mcp.txt`) |
| **Codex** | Global `AGENTS.md` synced | `~/.codex/AGENTS.md` |
| **Kiro** | Steering file synced | `~/.kiro/steering/convmem.md` |
| **ChatGPT** | Paste-only pack generated | `docs/chatgpt-pack/custom-instructions.txt` |

**Architecture:** one canonical source-of-truth (`config/agent-protocol.md`) → generator (`scripts/generate-agent-protocol.sh`) emits per-surface slices → deploy script (`scripts/deploy-agent-protocol.sh`) pushes them. Three capability tiers: shell / MCP-only / paste-only.

**You (Cursor Auto Composer) have both shell and MCP.** The `convmem.mdc` rule is prepended to every session regardless of working directory. The MCP `instructions=` also carries the protocol. You may see it from both channels — that's intentional (redundancy across independent channels is harmless).

---

## The soak test

**Question:** Now that the protocol follows the human (not the directory), do agents actually use it?

**Test setup:** Use convmem normally for ~1 week. No special behavior. Work on convmem, WordPress, random repos — whatever you'd normally do. The test runs itself.

**What to observe:**
- Does Cursor Auto Composer run `convmem doctor → brief --stdout-only → unresolved` at session start, unprompted?
- When asked history/architecture questions, does it search_fast/ask before guessing?
- Does it check `unresolved_count` when working on client sites?
- At session close, does it output a correct `convmem record` block?

**The primary metric:** *Does the agent start with `doctor` before any search/ask operation, without being told?* If yes, the deployment works. If not, the protocol is deployed but not loaded into agent behavior.

### Alien-workspace spot-check

One explicit test you should run once early in the soak:

1. Open Cursor in **`~/WordPress/willowyhollow-practice/`** (or any directory without an `AGENTS.md`)
2. Ask: *"What's the current state of this project?"*
3. Observe: does the agent run `convmem doctor` first, unprompted?

If yes → "instructions follow the human" works. If no → the global rule isn't reaching the agent.

### Success signals

| Observation | Meaning |
|-------------|---------|
| Agent runs `doctor` before first ask/search in **any** directory | ✅ Global rule working |
| Agent runs `unresolved --site staging2...` on client work | ✅ Tier A protocol followed |
| Agent uses `search_fast` before answering history questions | ✅ Retrieval habit formed |
| Agent does NOT duplicate ritual from convmem repo `AGENTS.md` when already following global rule | ✅ No double-load confusion |
| Agent correctly outputs session-close record block at end | ✅ Close ritual intact |

### Failure signals

| Observation | Diagnosis |
|-------------|-----------|
| Agent calls `brief()` before `doctor` (when shell is available) | brief docstring override winning over server instructions |
| Agent ignores protocol entirely in non-convmem repo | Global `.mdc` not loaded or wrong path |
| Agent asks "what is convmem" or suggests alternatives | Identity statement not reaching agent |
| Agent runs `ask` without `search_fast` on history questions | Retrieval-before-synthesis not ingrained |
| Agent uses topic slug as `--relates-to` on session close | Close ritual not followed |
| Agent calls MCP `ask` in Codex sandbox without retry via `bash -lc` | Sandbox workaround missing from surface |

### How to report back

Create a file: `docs/inter-model/SOAK-REPORT-<date>.md`

Template:

```markdown
# Soak report — <date range>

## Sessions observed

| # | Dir opened | First action | Unprompted doctor? | Notes |
|---|-----------|-------------|-------------------|-------|
| 1 | | | | |
| 2 | | | | |

## Alien-workspace spot-check

- Dir: `~/WordPress/willowyhollow-practice/`
- Agent first action: 
- Unprompted doctor? [yes/no]
- Notes:

## Protocol violations

- [list any failure signals observed]

## Convmem infra observations

- Did `doctor` exit 0 every time?
- Did `unresolved` count stay current?
- Any MCP tool failures?
- Corpus health (run `convmem stats` at soak end)

## Recommendation

- [ ] Protocol working — no changes needed
- [ ] Tweak brief docstring qualification (if agents skip doctor)
- [ ] Investigate surface not loading (if agents miss protocol in specific dirs)
- [ ] Ship P2 MCP tools (if agents still bypass CLI despite protocol)
```

---

## What NOT to conflate

| This is protocol soak | This is NOT protocol soak |
|-----------------------|--------------------------|
| "Did the agent run doctor/brief/unresolved?" | "Did we deploy CSP on staging2?" |
| "Did the agent search before guessing?" | "Did indexing finish?" |
| "Did the session-close block use a real ledger_id?" | "Was the agent's answer correct?" |

The soak is about **agent habit** — whether the protocol reaches the agent's first action. Retrieval quality (10/10 golden eval) and client work (staging2 security headers) are separate lanes.

---

## Files to know about

| File | Purpose |
|------|---------|
| `config/agent-protocol.md` | Canonical SSoT — three tiers, edit this to change protocol |
| `scripts/generate-agent-protocol.sh` | Run after editing canonical to regenerate surfaces |
| `scripts/deploy-agent-protocol.sh` | Run to push generated surfaces to user configs |
| `docs/ROADMAP-DRAFT.md` | Convmem project roadmap (P2 gated on soak outcome) |
| `docs/AGENT-ROLES.md` | Per-model capability tiers |
| `docs/RECOVER.md` | Machine rebuild recovery (step 7 now includes deploy script) |
| `LATEST.md` | Cross-model handoff (read by next agent entering convmem repo) |
| `docs/inter-model/SESSION-CLOSE-RECORD.md` | Session close ritual (referenced by protocol) |

---

## Remaining manual items (not for you)

| Item | Owner | Status |
|------|-------|--------|
| Continue `~/.continue/config.yaml` trim to session-close only | Ryan | Optional unless graded sessions show duplication problems |
| ChatGPT paste `custom-instructions.txt` | Ryan | One-time, low urgency |
| Crush shell access confirmation | Ryan | Determines Tier A vs B for Crush |

---

## Your session start

You're Cursor Auto Composer — Tier A (shell + MCP). The `convmem.mdc` rule and MCP `instructions=` both carry this, but to be explicit:

```
convmem doctor            # exit 0 required
convmem brief --stdout-only
convmem unresolved        # add --site <hostname> for client work
search_fast / ask before guessing on history questions
```

**Do not duplicate session-start steps from repo `AGENTS.md`** — it's a pointer now. The global rule is the authority.
