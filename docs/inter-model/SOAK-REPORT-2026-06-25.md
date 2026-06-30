# Soak report — 2026-06-25 (**complete**; gap-fix pre-P2 2026-06-25)

See also: [VERIFICATION-MATRIX.md](VERIFICATION-MATRIX.md) for remaining Ryan manual scenarios.

## Sessions observed

| # | Dir opened | First action | Unprompted doctor? | Notes |
|---|-----------|-------------|-------------------|-------|
| 1 | `~/Projects/convmem` | Read handoff → `doctor` → `brief` → `unresolved` | Partial | User pointed at soak handoff (not clean unprompted test) |
| 2 | `~/WordPress/willowyhollow-practice/` | Glob + Read README + git + MCP `brief()` (parallel) | **No** | Alien-workspace spot-check — see below |
| 3 | `~/Projects/convem` | Read/Glob hunt for handoff (4 turns) → `doctor` → `brief` → `unresolved` | Partial | User cited soak handoff path; correct shell order once protocol started |
| 4 | `~/Projects/convmem` | Read handoff → `doctor` + `brief` (parallel) → transcript audit | Partial | Soak analysis + record block; meta/admin, not alien test |
| 5 | `~/WordPress/pavlomassage-practice/` | List + Bash `ls` → Read README/docker → docker/curl | **No** | Continue + DeepSeek V4 Flash — **convmem not used at all** |
| 6 | `~/WordPress/pavlomassage-practice/` | `ls` → `view` scripts/README → bash/glob → `write` AGENTS.md | **No** | Crush + DeepSeek V4 Flash — **convmem not used at all** (same failure class as #5) |
| 7 | `~/WordPress/pavlomassage-practice/` | Bash ×3 (`stack_ps`, `ls`, `convmem doctor`) → MCP `brief()` | **No** (doctor 3rd) | **continue-cli** `cn --auto --config ~/.continue/config.yaml` + DeepSeek V4 Flash — **PARTIAL** |
| 8 | `~/WordPress/pavlomassage-practice/` | Bash `stack_ps` → git → docker → theme/plugins (all bash) | **No** | Crush retest post Tier B deploy — **FAIL** (zero convmem; same class as #6) |
| 9 | `~/WordPress/pavlomassage-practice/` | Bash `convmem doctor` → `brief` → `unresolved` → `stack_ps` | **Yes** | Crush post Tier A deploy — **PASS** |
| 10 | `~/WordPress/pavlomassage-practice/` | MCP `brief(willowyhollow-dev)` → answer (no repo survey) | **No** (MCP not shell doctor) | **continue-cli** `cn --auto` + **qwen3-coder:30b** — **PASS** (Ryan) |
| 11 | `/home/lauer` (home workspace) | MCP `mcp_convmem_brief()` → list_directory… | **No** (MCP entry) | **Kiro** `sess_4500caa1…` — **PASS** |
| 12 | `~/GitClones/pavlomassage-dev/` | MCP `brief(pavlomassage-dev)` ∥ Read/git | **No** | **Cursor** `4fb9b726…` — **PASS** (Ryan) |
| 13 | `~/WordPress/pavlomassage-practice/` | Bash `convmem doctor` → MCP `mcp_convmem_brief(pavlomassage-practice)` | **Yes** | **Kiro** `sess_a50e2983…` — **PASS** (steering `inclusion: always` fix); approval prompts remain |
| 14 | `~/WordPress/pavlomassage-practice/` | Bash `convmem doctor` → MCP `mcp_convmem_brief(pavlomassage-practice)` (no prompts) | **Yes** | **Kiro** `sess_740c2f91…` — **PASS** (`permissions.yaml`; ACP `effect:allow`) |
| 15 | `~/WordPress/pavlomassage-practice/` | MCP `brief(pavlomassage-dev)` first tool call | **No** (MCP entry) | **continue-cli** `c52aacbc…` + **qwen3-coder:30b** — **PASS** (Ryan) |
| 16 | `~/WordPress/willowyhollow-practice/` | Bash `convmem doctor` → MCP `brief(willowyhollow-practice)` → `unresolved \| head` | **Yes** | **Kiro** `sess_d46fb11b…` — **PASS** (head/tail rules; no convmem prompts) |
| 17 | `~/WordPress/willowyhollow-practice/` | MCP `brief(willowyhollow-practice)` first tool call | **No** (MCP entry) | **continue-cli** `0b339775…` + **qwen3-coder:30b** — **PASS** (Ryan; correct project=) |
| 18+ | alien WP repos | Full ritual per surface | varies | **Ryan retest bundle:** Cursor **PASS ×2**, Kiro **PASS**, Crush **PASS**, Continue **qwen3-coder:30b PASS** — post-permissions (incl. `echo *` fix) |
| 19 | `~/WordPress/pavlomassage-practice/` | No tool call — assistant emitted `{"name":"brief","arguments":{}}` as text | **No** | **continue-cli** `cn --auto -p` + **qwen2.5-coder:14b** — **FAIL** (Tier-A daily; headless soak 2026-06-29) |
| 20 | `~/WordPress/pavlomassage-practice/` | MCP `brief(pavlomassage-practice)` first tool call | **No** (MCP entry) | **continue-cli** `cn --auto -p` + **qwen3-coder:30b** — **PASS** (regression; headless 2026-06-29) |
| 21 | `~/WordPress/pavlomassage-practice/` | `List` → repo survey (no brief) | **No** | **continue-cli** `cn --auto -p` + **qwen3.6-27b-iq3-32k** — **FAIL** (2026-06-29) |
| 22 | `~/WordPress/pavlomassage-practice/` | `List` → repo survey (no brief) | **No** | **continue-cli** `cn --auto -p` + **qwen3.6-27b-iq3-crush** — **FAIL** (2026-06-29) |

## Alien-workspace spot-check

- **Dir:** `~/WordPress/willowyhollow-practice/`
- **User query:** "What's the current state of this project?"
- **Transcript:** `a7ad9840-29ca-492b-98ce-5b412f736e7b` (2026-06-25 ~16:52)
- **Agent first action:** Repo survey (Glob, Read README, `git status/log`) **in parallel with** MCP `brief(project=willowyhollow-practice)` — not `doctor`
- **Unprompted doctor?** **No**
- **Convmem sequence observed:**
  1. MCP `brief()` — no prior `convmem doctor`
  2. MCP `search_fast(...)` — good retrieval habit, wrong entry point
  3. Never: `convmem doctor`, `convmem unresolved`, shell `brief --stdout-only`
- **Notes:** Answer quality was good (used brief + search_fast + local audit.sh/git). Protocol order violated. Global rule loaded (convmem was used unprompted) but Tier A shell ritual skipped in favor of MCP brief.

### Continue alien-workspace spot-check (pavlomassage-practice)

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** Continue + DeepSeek V4 Flash
- **User query:** "What's the current state of this project?"
- **Session:** `74121955-68f6-42df-877d-2796482c9832` (2026-06-25 ~17:25)
- **Agent first action:** `List` + Bash `ls` — local repo only
- **Unprompted doctor?** **No**
- **Convmem used?** **No** — zero MCP calls (`brief`, `search_fast`, `doctor`, etc.)
- **Tools used:** List, Read (README, docker-compose), Bash (docker ps, curl :8082)
- **Notes:** Worse than Cursor session #2 (which at least called MCP `brief()`). Continue `config.yaml` rules still say "call MCP tool brief" at session start but agent ignored convmem entirely. No Cursor `.mdc` on this surface. README mentions convmem tag `practice-local-pavlo` but agent didn't follow up.

### Crush alien-workspace (pavlomassage-practice)

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** Crush + DeepSeek V4 Flash
- **User report:** Same query as Continue — *"What's the current state of this project?"* — same failure (no convmem)
- **Session in db:** `ba11a05f-300c-4aa3-a649-a41a1609469f` (2026-06-25 ~17:30–17:40); crush.log shows MCP clients initialized
- **Agent first action:** `ls` — local repo survey
- **Unprompted doctor?** **No**
- **Convmem used?** **No** — tools were `ls`, `view`, `bash`, `glob`, `write` only; zero MCP `brief`/`search_fast`/etc.
- **Crush log note:** `loaded_total:0` skills on turn summary — MCP wired but not invoked
- **Rules surface:** `~/.config/crush/rules/convmem.md` is **pre-protocol** (search/ask only, no doctor/brief session-start)
- **Notes:** Same failure class as Continue #5. Crush is Tier B (MCP-only per AGENT-ROLES) but has no deployed global-protocol slice. Query text not found in crush.db messages (session title is AGENTS.md generation); user confirms same alien-workspace test intent.

### Continue-cli alien-workspace retest (pavlomassage-practice) — session #7

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** **continue-cli** (`cn --auto --config ~/.continue/config.yaml`) — not IDE extension
- **Model:** DeepSeek V4 Flash
- **User query:** "What's the current state of this project?" (unprompted — no convmem hints)
- **Session:** `48ca9aaf-7234-4c91-b7ff-4a4a79049b76.json` — title "Project State Review" (2026-06-28 ~18:52 local)
- **Agent first action:** Bash `stack_ps` — repo/stack survey before convmem ritual
- **Unprompted doctor first?** **No** — `convmem doctor` was 3rd tool call (after `stack_ps`, `ls`)
- **Convmem used?** **Yes** — Bash `convmem doctor` (exit 0) then MCP `brief()` (no `project=`)
- **Not run:** `unresolved`, `search_fast`, shell `brief --stdout-only`
- **Tool sequence:** `Bash(stack_ps)` → `Bash(ls -la)` → `Bash(convmem doctor)` → `brief()` → answer
- **Answer quality:** Good — used brief JSON (stale handoff, stack status, ledger context)
- **Grader:** `grade-continue-session.sh` → **FAIL** (expected — grader only scores explicit "call brief" prompts; soak prompt did not name tools)
- **Verdict:** **PARTIAL PASS** vs #5 (zero convmem → doctor + brief). Order still wrong (repo before doctor/brief).
- **Notes:** `config.yaml` session-start stanza already present. CLI "agent mode" = `cn --auto`, not IDE Chat/Plan/Agent dropdown. Task framing ("project state") still pulls repo survey first.

### Crush alien-workspace retest (pavlomassage-practice) — session #8

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** Crush + DeepSeek V4 Flash (assumed; same as #6)
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `e5fff1e2-1d1d-4da8-932c-5c90f43edd90` — title "Project Status Inquiry" (2026-06-28 ~19:10 local)
- **Rules on disk:** Tier B deployed at `~/.config/crush/rules/convmem.md` (`brief()` first…) — verified before test
- **Agent first action:** Bash `stack_ps` — repo/stack survey
- **Unprompted doctor?** **No**
- **Convmem used?** **No** — zero MCP calls; **all tools were `bash`**
- **Tool sequence:** `bash(stack_ps)` → `bash(git log)` → `bash(docker ps/images)` → `bash(ls astra-child)` → `bash(list plugins)` → answer
- **Answer quality:** Local-only (docker stack, empty child theme, no git) — no corpus/ledger context
- **Verdict:** **FAIL** — Tier B rules deploy did **not** change behavior vs #6
- **Notes:** Agent has shell and uses it exclusively for "project state" tasks. Tier B (MCP-only) instructions appear not to compete with bash repo survey. Continue #7 only reached convmem after **shell ritual** in `config.yaml`. Crush may need **Tier A** slice (shell `doctor → brief`) not MCP-only.

### Crush alien-workspace retest (pavlomassage-practice) — session #9

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** Crush + DeepSeek V4 Flash (assumed; same as #6/#8)
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `25a040a9-63dc-4d43-b473-59fc20e91058` — title "Project Status Inquiry" (2026-06-29 ~00:14 local)
- **Rules on disk:** Tier A deployed at `~/.config/crush/rules/convmem.md` (shell ritual before repo survey)
- **Agent first action:** Bash `convmem doctor` — **correct entry point**
- **Unprompted doctor first?** **Yes**
- **Convmem used?** **Yes** — full shell ritual via bash; zero MCP in opening sequence
- **Tool sequence:** `bash(convmem doctor)` → `bash(convmem brief --stdout-only)` → `bash(convmem unresolved)` → `bash(stack_ps)` → repo survey → answer
- **Reasoning note:** Agent cited "user preferences" / convmem instructions before exploring project
- **Verdict:** **PASS** — Tier A fix confirmed (#8 FAIL → #9 PASS)
- **Notes:** First alien-workspace session with correct doctor-first order on Crush. Repo survey followed ritual, not before it.

### Continue-cli alien-workspace retest (pavlomassage-practice) — session #10

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** **continue-cli** (`cn --auto --config ~/.continue/config.yaml`)
- **Model:** **qwen3-coder:30b** (not DeepSeek V4 Flash — `cn` warns V4 Flash has limited tool calling)
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `978bca34-bec9-4f93-9acd-d59339701e6b.json` — title "Convmem Agent Workflow Development" (2026-06-29 ~00:24 local)
- **Agent first action:** MCP `brief(project=willowyhollow-dev)` — **convmem before repo survey**
- **Unprompted doctor?** **No** — MCP-only entry; no shell `convmem doctor`
- **Convmem used?** **Yes** — single MCP `brief()` then answer; **no** bash/docker/`stack_ps`
- **Not run:** `doctor`, `unresolved`, `search_fast`; wrong `project=` slug (willowyhollow-dev vs pavlomassage)
- **Answer quality:** Used brief JSON but summarized wrong project (willowyhollow-dev corpus slice)
- **Verdict:** **PASS** (Ryan) — convmem-first beats #7 partial; not full Tier A shell ritual like Crush #9
- **Notes:** Model matters — qwen3-coder:30b invoked MCP immediately; DeepSeek V4 Flash failed (#5) or partial (#7). Continue P2 stanza + capable model = protocol reachable.

### Kiro alien-workspace soak — session #11

- **Dir:** `/home/lauer` (workspace root — not a single project repo)
- **Surface:** Kiro vibe mode + MCP enabled (`~/.kiro/settings/mcp.json` post-deploy)
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `sess_4500caa1-d589-45c2-88bf-ce1169bae62e` — title "Project state overview" (2026-06-29 ~00:32–00:34 UTC)
- **Transcript:** `~/.kiro/sessions/95236b67b2db2900/sess_4500caa1-d589-45c2-88bf-ce1169bae62e/messages.jsonl`
- **Agent first action:** MCP `mcp_convmem_brief()` (no `project=`) — **before filesystem survey**
- **Tool approval:** Kiro prompted Allow/Deny for `@convmem/brief`; Ryan selected **Allow once**
- **Unprompted doctor?** **No** — MCP-first (steering Tier A shell not invoked)
- **Convmem used?** **Yes** — `brief()` first; then `list_directory` (home, Projects, GitClones, WordPress), `read_file` (TODO.md, WORKSPACE.md)
- **Not run:** `convmem doctor`, `unresolved`, `search_fast`
- **Answer quality:** Good — used brief JSON + local WORKSPACE.md; brief cited stale ledger re mcp.json (dec_prop from pre-deploy)
- **Verdict:** **PASS** — convmem before repo survey; closes Phase 2 Priority 3
- **Notes:** Home-root workspace ≠ pavlomassage alien test; still valid unprompted protocol check. MCP tool prefix: `mcp_convmem_brief`.

### Cursor alien-workspace soak — session #12

- **Dir:** `~/GitClones/pavlomassage-dev/` (git clone; has repo `AGENTS.md`)
- **Surface:** Cursor + global `convmem.mdc`
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `4fb9b726-4233-4474-af6c-9454af5245a5` (2026-06-28 ~19:42 local)
- **Agent first action:** MCP `brief(project=pavlomassage-dev)` **in parallel with** Read HANDOFF/README + `git status/log`
- **Unprompted doctor?** **No** — MCP-first; no shell `convmem doctor`
- **Convmem used?** **Yes** — `brief()` then `search_fast()` in follow-up turns
- **Verdict:** **PASS** (Ryan) — brief in opening tool batch before repo-only survey
- **Notes:** Correct `project=` slug (vs Continue #10). Still no full Tier A shell ritual (doctor → brief → unresolved). Second Cursor alien datapoint after #2 (willowyhollow).

### Kiro alien-workspace retest (pavlomassage-practice) — session #13

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** Kiro vibe mode + global steering (`inclusion: always`) + MCP
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `sess_a50e2983-9f25-45bd-ab78-89824fe8a188` — title "Project state check" (2026-06-29 ~01:17 UTC)
- **Agent first action:** `update_session_information` → Bash `convmem doctor` → MCP `mcp_convmem_brief(project=pavlomassage-practice)`
- **Unprompted doctor first?** **Yes** — doctor before repo survey (fixes #13-pre steering skip class)
- **Convmem used?** **Yes** — shell doctor + MCP brief (+ shell `brief --stdout-only`, `unresolved` after)
- **Tool approval:** Kiro prompted for **Allow** on `convmem doctor`, `@convmem/brief`, and subsequent shell convmem calls despite `autoApprove` in `~/.kiro/settings/mcp.json`; Ryan selected **Allow once** (not Always allow)
- **Policy log:** `acp.policy-eval.complete {"toolId":"mcp_convmem_brief","effect":"ask"}` — **`mcp.json` `autoApprove` ignored** in IDE 1.0+; fix is `~/.kiro/settings/permissions.yaml` with `capability: mcp` / `convmem/*` (deployed post-#13)
- **Verdict:** **PASS** — ritual order correct; friction from approval prompts is **out of band** for protocol soak
- **Notes:** Steering fix (`inclusion: auto` → `always` + preamble) confirmed. Correct `project=` slug. Redundant shell+MCP brief doubles prompts.

### Kiro permissions fix (pavlomassage-practice) — session #14

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** Kiro vibe mode + `~/.kiro/settings/permissions.yaml` (deployed from `config/kiro-permissions.yaml.example`)
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `sess_740c2f91-f38b-45a5-af09-c778de119f2c` — title "Practice stack status check" (2026-06-29 ~01:27 UTC)
- **Agent first action:** `convmem doctor` → `mcp_convmem_brief(project=pavlomassage-practice)` — **no approval prompts** on convmem shell/MCP
- **Policy log:** `effect:"allow"` for `run_command` (shell) and `mcp_convmem_brief` (was `"ask"` pre-#14)
- **Full ritual:** doctor → MCP brief → shell brief → `unresolved --site practice-local-pavlo` → then `stack_ps` (stack still prompted — expected, not in permissions rules)
- **Verdict:** **PASS** — protocol + frictionless convmem approval
- **Notes:** `mcp.json autoApprove` is dead for IDE 1.0+; **`permissions.yaml`** is the real config. Deploy script ships it.

### Continue-cli retest (pavlomassage-practice) — session #15

- **Dir:** `~/WordPress/pavlomassage-practice/`
- **Surface:** **continue-cli** (`cn --auto --config ~/.continue/config.yaml`)
- **Model:** **qwen3-coder:30b**
- **User query:** "What's the current state of this project?" (unprompted)
- **Session:** `c52aacbc-f5ea-4c15-9ffc-74ac48001c96` — title "Convmem System State Analysis" (2026-06-29 ~01:21 local)
- **Agent first action:** MCP `brief(project=pavlomassage-dev)` — **sole first-turn tool call**
- **Unprompted doctor?** **No** — MCP-only entry (same class as #10)
- **Verdict:** **PASS** (Ryan) — brief invoked before repo survey; wrong `project=` slug again (dev vs practice)
- **Notes:** Confirms #10 with qwen3-coder; V4 Flash remains unsuitable for `cn --auto` soak.

### Kiro retest (willowyhollow-practice) — session #16

- **Dir:** `~/WordPress/willowyhollow-practice/`
- **Session:** `sess_d46fb11b-dc46-4cb8-829e-3925d3ed0e08` (2026-06-29 ~01:32 UTC)
- **Ritual:** doctor → MCP brief(`willowyhollow-practice`) → `convmem unresolved --site staging2.willowyhollow.com 2>&1 | head -60` — **all auto-allowed**
- **Verdict:** **PASS** — confirms `head *` permissions fix; `stack_ps` still prompts (out of scope)
- **Notes:** Second alien WP workspace; correct `project=` slug.

### Continue-cli retest (willowyhollow-practice) — session #17

- **Dir:** `~/WordPress/willowyhollow-practice/`
- **Session:** `0b339775-1fb8-4fa1-8be9-3b4afd93986d` — qwen3-coder:30b
- **First action:** MCP `brief(project=willowyhollow-practice)` — **correct slug** (vs #10/#15)
- **Verdict:** **PASS** (Ryan) — third consecutive qwen3-coder alien pass

### Codex alien WP (willowyhollow-practice) — session #20

- **Dir:** `~/WordPress/willowyhollow-practice/`
- **Tool:** `codex exec --json --dangerously-bypass-approvals-and-sandbox` (stdin closed `</dev/null`)
- **Thread:** `019f119c-990b-7211-bacc-0669e85e2381`
- **First action:** `convmem doctor && convmem brief --stdout-only && convmem unresolved` (compound bash)
- **Then:** `git status`, `git log`, `stack_ps`, diffs
- **Verdict:** **PASS** — full shell ritual before repo/stack survey

### Codex blank dir — session #21

- **Dir:** `/tmp/test-empty` (`--skip-git-repo-check`)
- **First actions:** `convmem doctor` → `rg --files` → `convmem unresolved` → `convmem brief` → `pwd/ls/git`
- **Verdict:** **PASS** — convmem doctor first; brief/unresolved before `ls`/`git` (minor: `rg` between doctor and brief)

### Cursor blank dir — session #22 (partial)

- **Dir:** `/tmp/test-empty`
- **Wiring:** `~/.cursor/rules/convmem.mdc` has `alwaysApply: true`; dir empty (no `AGENTS.md`)
- **Runtime:** `agent -p` failed — `Authentication required` (`agent login` or `CURSOR_API_KEY`)
- **Verdict:** **WIRING PASS / RUNTIME TODO** — open `/tmp/test-empty` in Cursor and use unprompted project-state query

### convmem repo — session #23 (row 7)

- **Static:** `AGENTS.md` trimmed (10 lines); defers session-start to global rule; `convmem.mdc` has `alwaysApply: true` with Tier A steps — **no duplicate ritual text**
- **Codex:** first cmd `convmem doctor`; then `unresolved`, `brief` — single ritual pass
- **Crush V4 Pro:** first cmd `convmem doctor && brief && unresolved` (session `88d6e84d`)
- **Verdict:** **PASS** — no conflicting double ritual

### Cursor blank dir — session #24 (row 5)

- **Dir:** `/tmp/test-empty` (empty; no repo `AGENTS.md`; only empty `.cursor/`)
- **Wiring:** `~/.cursor/rules/convmem.mdc` + `convmem-protected-paths.mdc` both `alwaysApply: true`
- **Runtime:** Cursor agent root moved via `move_agent_to_root`; `convmem doctor` → `brief` → `unresolved` before `ls` dir survey
- **Note:** `agent -p` CLI blocked (needs `agent login` / API key); verified in live Cursor agent session instead
- **Verdict:** **PASS**

## Protocol violations

- **brief() before doctor** (shell available) — matches handoff failure signal; root cause **unconfirmed** (n=1)
- **No `unresolved`** — missed staging2 header context that brief would have surfaced (6 open obs)
- **Repo exploration before convmem health check** — doctor gate not treated as prerequisite
- **Continue pavlomassage-practice (#5)** — protocol not loaded into behavior at all (no MCP, no shell convmem)
- **Crush pavlomassage-practice (#6)** — same; MCP initialized but never called; stale `rules/convmem.md`
- **Continue-cli #7** — convmem reached agent (doctor + brief) but **repo survey before ritual**; no `unresolved`
- **Crush #8 (retest)** — Tier B rules deployed; **zero convmem** (bash-only); deploy fix **ineffective**
- **Crush #9 (Tier A retest)** — **no violation**; doctor → brief → unresolved before repo survey

## Convmem infra observations

- Did `doctor` exit 0 every time? #1 convmem-repo; #7 alien (3rd call); **#9 first** in alien Crush session
- Did `unresolved` count stay current? 13 open at session #7 brief (was 6 at soak start)
- Any MCP tool failures? None in #2 or #7
- Corpus health (soak end 2026-06-29): **1590** units, **343** summaries; `doctor` all PASS; watch/refine/monitor active per brief

## Trend summary (pavlomassage-practice, same query)

| Session | Surface | Convmem? | Order |
|---------|---------|----------|-------|
| #5 | Continue (unknown mode) | **No** | — |
| #6 | Crush (pre-deploy rules) | **No** | bash only |
| #7 | continue-cli `--auto` | **Yes** | Bash survey → doctor → brief |
| #8 | Crush (post-deploy Tier B) | **No** | bash only |
| #9 | Crush (post-deploy Tier A) | **Yes** | doctor → brief → unresolved → survey |
| #10, **#15** | continue-cli `--auto` + qwen3-coder:30b | **Yes** | MCP brief first (wrong project=) |

**Continue Priority 2 (config.yaml stanza):** present on disk; **#10 PASS with qwen3-coder:30b**; DeepSeek V4 Flash still weak (#5 FAIL, #7 PARTIAL). Prefer capable models for `cn --auto` convmem soak.

**Crush Tier A deploy:** **confirmed by #9** — shell ritual before repo survey. Tier B (#6/#8) and Tier A (#9) A/B on same surface/query.

**Kiro MCP deploy:** **confirmed by #11** — `brief()` first after enable + restart.

## Surface pass matrix (alien / unprompted)

| Surface | Soak | Verdict |
|---------|------|---------|
| Crush | #9, **Ryan retest** | **PASS** (shell doctor first; permissions hook) |
| continue-cli | #10, #15, **#17**, **Ryan retest** | **PASS** (MCP brief first; qwen3-coder:30b) |
| Kiro | #11, #13–**#16**, **Ryan retest** | **PASS** (permissions.yaml; head/tail/echo compounds) |
| Cursor | #2 partial, **#12**, **Ryan retest ×2** | **PASS** (MCP brief first) |

**Kiro permissions:** IDE 1.0+ uses `~/.kiro/settings/permissions.yaml` (not `mcp.json autoApprove`). Deployed + verified #14; **echo *** for semicolon compounds verified Ryan retest.

## Recommendation

**All major surfaces pass alien soak and post-permissions retest** (Cursor ×2, Kiro, Crush, Continue qwen). DeepSeek V4 Flash is a poor `cn` soak model per CLI warning.

- [x] Protocol working — **PASS** on Crush, Continue, Kiro, **Cursor (#12)**
- [x] Tweak brief docstring qualification — **shipped** (Gap 5 + project= guidance 2026-06-29)
- [x] Investigate surface not loading — resolved (Crush tier + Continue model)
- [x] **Crush: regenerate Tier A slice** — deployed; soak #9 PASS
- [x] **Kiro: permissions.yaml** — deployed; soak #14 PASS (no convmem prompts)
- [x] **Crush: permissions** — `allowed_tools` + `hooks/convmem-allow.sh` deployed via deploy script
- [x] **Kiro: echo * permissions** — deployed; Ryan retest **PASS**
- [x] **Gap-fix pre-P2** — deploy verify, Crush session-close, Continue trim template, VERIFICATION-MATRIX, grader alien check
- [x] **Ryan manual** — Continue `rules:` trim (session-close only; 2026-06-25)
- [x] Codex alien soak #19 — **PASS** 2026-06-29 (see sessions #20–#21 below)
- [x] Codex blank-dir (row 6) — **PASS** 2026-06-29
- [ ] Cursor blank-dir runtime (row 5) — wiring verified; `agent login` for CLI soak
- [ ] Ship P2 MCP tools — **hold**
- [x] Document continue-cli soak path — `CONTINUE-VERIFY.md` updated 2026-06-29
- [x] ChatGPT paste — **ignored** (out of scope for plan closure)

### Hypotheses to watch (not confirmed)

1. Deployed `convmem.mdc` concatenates Tier A + Tier B without headers — **fixed 2026-06-29** (section headers in generator)
2. Task framing ("project state") pulled agent toward repo/git/docker **before** session ritual — **supported by #5 and #7**
3. MCP tool docstring salience at tool-pick time vs `.mdc` / `instructions=` prose
4. **continue-cli:** DeepSeek V4 Flash weak (#5/#7); **qwen3-coder:30b PASS #10** — model choice matters for `cn --auto`
5. **Crush Tier B:** MCP-only rules ignored when agent has bash — **confirmed #6/#8**; **Tier A fix confirmed #9**
