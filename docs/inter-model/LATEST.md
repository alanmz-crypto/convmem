# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-06-24 by Cursor

## State

- **Record UX:** `record -i` → `record --approve-last` (auto-index). Protocol ledger: `c311`.
- **Continue integrated:** MCP verify **PASS** (`dec_prop_20260623_233059_7ad3`) — Tiers 2–4 + Tier 6 cold recall **PASS**; grader `scripts/grade-continue-session.sh`; checklist `CONTINUE-VERIFY.md`.
- **Continue config:** `~/.continue/config.yaml` — `schema: v1`, `mcpServers` → convmem; DeepSeek **V4 Flash / Flash (Think) / Pro**.
- **Session-close rules:** `SESSION-CLOSE-RECORD.md` + Continue rule — `--author continue-session`, chain coordination thread (not test-subject ledger like practice `c4dd`).
- **Tier 6 DONE:** practice CSP tighten (6.1, chain `0f73`→`9de7`) + staging2 read-only probe (6.2, chain `503c`→`51e9`).
- **Practice lab:** `~/WordPress/willowyhollow-practice` on **:8081**, site tag `practice-local`; **runtime = `docker compose`** (`scripts/stack.sh`); WPCode CSP snippet **1116** (`purple-practice-csp-8081`); reset = `restore-from-backup.sh` (`dec_prop_20260623_231223_1403`).
- **Preview stack:** `~/WordPress/willowyhollow` on **:8080**; **runtime = `podman-compose`** (`scripts/stack.sh`). Do **not** use `podman compose` for practice (delegates to Docker; `podman exec` breaks).
- **Port conflicts:** `~/WordPress/scripts/cleanup-duplicate-stacks.sh` — removes stale underscore Podman containers fighting Docker/Podman dash stacks.
- **Docker/Podman fix:** `dec_prop_20260624_025115_862b` (chains `51e9`).
- **Watch:** subprocess index (watch parent stays light); stale `watch.lock` checks `/proc/pid/cmdline` — restart after deploy (`systemctl --user restart convmem-watch`).
- **Repo roots:** `GitClones`, `Projects`, `WordPress` — see `CURSOR-2026-06-23-repo-roots-confirmed.md`.
- **staging2 CSP deploy:** still open (Site Tools or `.htaccess` per `a66c` / `51e9`) — **client work**, not coordination.
- **willowyhollow-dev docs:** `ENVIRONMENTS.md` (four surfaces / lanes; staging2 ≠ git), `HABITS.md` (pre-client, CSP loop); `WORKFLOW.md` + `AGENTS.md` updated; `wh-*` aliases in `~/.zshrc` (`source ~/.zshrc` once).

## Decision

- Inter-model markdown = archive; **ledger + brief** = truth.
- **Change feed** (Codex): deferred until payoff review **2026-07-07**.

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
| **Docker/Podman stack fix** | `dec_prop_20260624_025115_862b` |
| **Tier 6.2 staging2 probe complete** | `dec_prop_20260624_022340_51e9` |
| **Tier 6.1 practice CSP step 4** | `dec_prop_20260624_011707_9de7` |
| **Continue MCP verify** | `dec_prop_20260623_233059_7ad3` |
| Cursor close (convmem arc) | `dec_prop_20260623_215943_5abe` |
| Protocol root (fallback) | `dec_prop_20260623_161428_c311` |

**Rule:** chain under the **newest relevant** id from `search_fast`, not a ledger you only cited during a test.

## Next

- **All models:** `convmem brief` at session start; `search_fast` / `ask --site` before guessing; `record` for durable handoffs.
- **Practice ops:** `source scripts/stack.sh` + `docker compose` on `:8081`; `cleanup-duplicate-stacks.sh` if CSP/ports look wrong.
- **staging2 CSP:** client deploy when Ryan chooses — policy template from practice lab; delivery per `a66c`.
- **Ops:** confirm watch RSS after restart; staging2 CSP when Ryan chooses.
- **Change feed:** hold until **2026-07-07**.
