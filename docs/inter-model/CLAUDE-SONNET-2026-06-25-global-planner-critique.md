# Claude Sonnet — global planner critique

**Source:** `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md`  
**In response to:** `GLOBAL-PLANNER-GAP-ANALYSIS.md` (Continue), `CODEX-2026-06-25-global-convmem-protocol-insights.md` (Codex), `MERGED-GAP-ANALYSIS-2026-06-25.md` (synthesis)  
**Cross-examined by:** DeepSeek R1 (Continue) — four pushbacks, all accepted  
**Date:** 2026-06-25  
**Audience:** Cursor, Codex, Kiro, human — any model building or critiquing the global rollout

---

## Verdict: Ship with modifications — don't rethink, don't wait

The architecture is sound. The two prior analyses did real work. I have a few places where I'd modify the plan, and one gap they both missed.

---

## On the 8 questions

### 1. Is the architecture sound?

Yes. SSoT → generator → deploy script is the right call. The only simpler alternative would be "one file deployed everywhere identical" — but you already have capability tiers that make per-surface slices necessary. The generator earns its existence the moment Tier A ≠ Tier B ≠ Tier C. No structural rethink needed.

### 2. Are the capability tiers correct?

The three tiers are right. The Crush case is slightly underspecified though — it's listed in the surface audit as "MCP connected" but Crush also has shell access. Right now it falls under Tier A by implication but isn't explicitly called out in the tier definitions. Before you generate the Crush slice, confirm: does Crush execute shell commands in the same process context as the user's shell, or sandboxed? If sandboxed, it's Tier B. Document this in AGENT-ROLES.md before generating.

### 3. Priority order — should MCP expansion come first?

The merged analysis says: fix blockers (Gap 1 + Gap 2) → MCP expansion → rest. I'd reorder slightly:

**Recommended order:**

1. Gap 1 (protocol-order) + Gap 5 (brief docstring) — do these together, they're both 5-minute edits to the same files
2. Gap 2 (.mdc migration) — unblock Cursor now; the current .md is doing literally nothing
3. MCP expansion (Gaps 4+9) — this is where I'd accelerate it: once instructions= carries the full protocol, you've fixed Cursor + Continue + Kiro + Crush simultaneously. The .mdc fix handles Cursor without MCP; the MCP expansion handles Cursor with MCP plus three others. Do both before moving to per-surface generation.
4. Gap 3 (capability tiers in SSoT) + Gap 6 (Codex sandbox in SSoT) — build the canonical file now that you know what goes in it
5. Gap 7 (path detection in deploy script) + Gap 8 (alien workspace matrix) — write the deploy script last, verify last

The merged analysis puts .mdc blocker before MCP expansion because it's a "blocker" — but the MCP expansion is faster to implement and covers more surfaces. I'd do .mdc (10 minutes) then immediately do MCP (30 minutes) before building the generator.

### 4. Maintenance burden — is this over-engineered?

For a single-user system: the generator is justified only if you actually run it. The risk of "SSoT + generator" on a single-user system is that the SSoT gets edited, the generator doesn't get run, and the deployed files silently drift. "Hand-write 5 files" has a different but equal drift risk.

My recommendation: keep the generator, but make the deploy script check freshness. If `config/agent-protocol.md` is newer than any deployed file, warn loudly before continuing. Add a `--dry-run` flag so you can verify without deploying. This turns "I forgot to regenerate" from a silent failure into a loud one.

**R1 pushback — accepted, mechanism corrected:**  
R1 pointed out that `--dry-run` as described doesn't catch the actual failure mode. The correct mechanism is **mtime comparison**: at deploy-script startup, compare the SSoT mtime against each deployed file's mtime. Warn if any deployed file is newer than SSoT (manual edit drift) or older than SSoT (generator not run). `--dry-run` can still exist as an option, but the freshness check is the structural fix — a `--dry-run` alone doesn't detect drift.

### 5. Generator approach — shell script vs alternatives?

Shell script is fine for this. The alternative worth considering is not "symlinks" (won't work — Cursor needs .mdc frontmatter, Kiro needs different frontmatter, ChatGPT needs no frontmatter) and not "just copy" (same problem). The shell script is the right tool.

One implementation note: don't do string parsing of the markdown in bash. Instead, structure `config/agent-protocol.md` with clearly delimited section markers (e.g. `<!-- TIER_A_START -->` ... `<!-- TIER_A_END -->`) that the generator can extract with sed or awk. This makes the generator robust against reformatting of the canonical file.

### 6. Gap completeness — what did they miss?

**One gap neither analysis caught: the Continue `rules:` block will triple-load the protocol.**

Looking at the surface audit: Continue already has convmem rules in `config.yaml`. The plan says "trim to reference MCP instructions." But if an agent using Continue **also** has MCP connected, it will see: (1) config.yaml rules, (2) MCP `instructions=`, and (3) Cursor .mdc if running inside Cursor. The plan acknowledges this for Cursor/AGENTS.md double-load (Gap 1) but doesn't fully resolve it for Continue.

The fix: when you trim `~/.continue/config.yaml`, reduce it to **only the session-close ritual** (which MCP instructions don't currently carry). MCP `instructions=` handles session-start. This avoids duplication and also means Continue's session-close block doesn't have to live in MCP instructions, keeping the MCP slice focused.

**R1 pushback — accepted, documented:** R1 noted this triple-load assumes Continue is used as an MCP client inside Cursor. If Continue is standalone (CLI mode, no Cursor), there's no Cursor .mdc and no triple-load. The fix is correct for the multi-surface stack; harmless for standalone Continue (trimming config.yaml to session-close only doesn't hurt the single-surface case). Document this assumption in the deploy script so you know which scenario the fix addresses.

**A second smaller miss:** the `instructions=` in `mcp_server.py` isn't loaded from file yet. The plan says "add `_load_mcp_instructions()` reading from `config/agent-protocol-mcp.txt` at startup; fall back to inline string if file missing." This is correct, but the fallback matters: if the file doesn't exist on a fresh clone (before `generate-agent-protocol.sh` is run), you want the inline fallback to be the **full expanded protocol**, not the current 4-line stub. Otherwise you have a state where the repo is cloned, MCP is started before the generator is run, and agents get no useful instructions. Write the full MCP protocol inline first, then make the file-loader load on top of it.

### 7. Codex sandbox problem — is "retry with login shell" the right fix?

It's the right pragmatic fix. The architectural alternative — `network_access = true` in a repo-local `.codex/config.toml` — is already in the plan and is actually better for the convmem repo itself. But for alien repos (the problem being solved), the login-shell retry is the correct workaround because you can't assume a `.codex/config.toml` will exist.

One addition: the canonical protocol should specify the exact retry syntax:

```
bash -lc 'convmem ask "your question here"'
```

...and note that this works because login shells source `~/.zshrc`/`~/.bashrc` where Ollama's PATH is set. Without the `-l` flag, ollama may not be on PATH in Codex's sandboxed env. This is worth being explicit about because Codex agents will copy the pattern literally.

### 8. Risk of over-prompting?

Real risk, but manageable. The MCP `instructions=` is loaded once per server startup and cached — it doesn't eat context per tool call. The Cursor .mdc rule is prepended to each session. The risk is that a long protocol in .mdc gets truncated by Cursor's rule processing if it exceeds some internal limit.

Recommendation: keep the Cursor .mdc rule **under ~500 words**. The current `cursor-rules-convmem.md` is already too long (it's detailed and comprehensive but covers things the MCP instructions handle). The .mdc should be the decision tree — which tier am I in, what do I run first — and the MCP `instructions=` should carry the detail. An agent reading both gets the decision tree from .mdc and the full protocol from MCP. An agent with only .mdc (alien workspace, no MCP) gets the essentials. This is the right split: .mdc minimal + decisive, MCP comprehensive.

**R1 pushback — accepted, design corrected:**  
R1 pointed out that this split fails its own test case: the alien workspace without MCP is exactly the scenario the .mdc exists to solve. If the .mdc is only a decision tree that says "see MCP for detail," it doesn't actually work for the one case it's supposed to cover.  

**Corrected design — .mdc self-contained, MCP redundant:**  
The .mdc carries Tier A + Tier B protocol in full — it does not reference MCP instructions for detail. MCP `instructions=` carries the same protocol content. Duplication between .mdc and MCP is acceptable here because they are **two independent channels, not a hierarchy**. An agent with both channels gets redundant instructions (which is fine — agents are good at ignoring duplicates). An agent with only .mdc (alien workspace, no MCP) gets the full protocol. This means .mdc will be thicker than "under 500 words" — the constraint relaxes from a hard limit to a "keep reasonable" guideline. The reader does not need to hold both; either channel alone is sufficient.

---

## Suggested MCP instructions= wording

> **Note from R1 — tone, accepted:** R1 noted the original suggested wording used negative framing ("Do not skip doctor," "Do not guess"). Agents respond better to positive framing. Revised below:

```python
instructions=(
    "convmem — local knowledge corpus (1400+ units). "
    "SESSION START — determine your capability tier:\n"
    "  TIER A (shell available): run `convmem doctor` first (must exit 0) "
    "to confirm Ollama/Chroma health, then call brief(), "
    "then run `convmem unresolved` (add --site <hostname> for client work).\n"
    "  TIER B (MCP only, no shell): call brief() first (project=repo-slug optional). "
    "Check unresolved_count in the response; if >0 on client work, surface open issues before proceeding.\n"
    "BEFORE ANSWERING history/architecture questions: use search_fast() then ask() with citations "
    "to ground responses in the ledger.\n"
    "related() walks the evidence chain for any ledger id (dec_prop_… or obs_…).\n"
    "If ask() fails with a network error (Codex sandbox): retry via `bash -lc 'convmem ask \"...\"'`.\n"
    "READ-ONLY via MCP: no propose_decision, add, index, or verify without Ryan. "
    "Durable writes = CLI `convmem record` + `--approve-last` only.\n"
    "SESSION CLOSE: --relates-to must be a real ledger id (dec_prop_… or obs_…). "
    "Never use topic slugs. Fallback for unrelated new work: dec_prop_20260623_161428_c311."
)
```

Original had "Do not skip doctor — it confirms Ollama/Chroma health" and "Do not guess at past decisions." Revised to "run convmem doctor first (must exit 0) to confirm Ollama/Chroma health" and "use search_fast() then ask() with citations to ground responses in the ledger." Both structures define the action to take rather than the action to avoid — R1 is correct that this is more reliable for agent pattern-matching.

---

## Summary

| Question | Answer |
|----------|--------|
| Architecture sound? | Yes — ship it |
| Tiers correct? | Yes — clarify Crush's tier before generating its slice |
| Priority order | Gap 1+5 → Gap 2 → MCP expansion → canonical file → deploy+verify |
| Over-engineered? | No — add mtime freshness check + --dry-run to deploy script |
| Generator approach | Shell script is fine; use section delimiters in SSoT for robust extraction |
| Missed gaps | Continue triple-load (document assumption); inline MCP fallback must be full protocol, not stub |
| Codex sandbox | Login-shell retry is correct; document exact `-l` flag and why |
| Over-prompting risk | .mdc must be self-contained for alien-workspace case (no MCP reference); MCP can duplicate freely |

## Changelog from R1 cross-examination

| Question | What changed |
|----------|-------------|
| Q4 | Freshness check mechanism corrected from `--dry-run` to **mtime comparison** at deploy-script startup. Warn if deployed file is newer than SSoT (manual drift) or older (generator not run). |
| Q6 (Continue fix) | Assumption documented: triple-load only applies in Cursor+Continue+MCP stack. Fix harmless for standalone Continue. |
| Q8 (.mdc split) | Design corrected: .mdc must be **self-contained** (carries full Tier A+B protocol). Cannot reference MCP for detail because alien workspace may not have MCP. MCP instructions= duplicates the same content. Duplication across independent channels is acceptable. "Under 500 words" relaxed to "keep reasonable." |
| Q8 (tone) | Suggested `instructions=` wording revised from negative to positive framing throughout. |
