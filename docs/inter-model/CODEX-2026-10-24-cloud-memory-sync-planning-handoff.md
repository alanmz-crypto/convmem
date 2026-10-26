# Planning Handoff: cloud memory sync and Claude app access

**Date:** 2026-10-24
**Author:** Claude (cloud-migration coordination)
**For:** planning lane: Codex, or Claude CLI if Ryan picks it (Codex budget
was nearly spent on 2026-10-24)
**Authorization:** Ryan, 2026-10-24, verbal: "make that a future project", then
"yes" to adding the Claude cloud route. This authorizes recording the project
only. Planning starts when Ryan says so.
**Arc:** not yet named. Ryan assigns the codename when planning starts.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` (future project; not started) |
| **Branch** | `plan/2026-10-24-cloud-memory-sync` |
| **Tip SHA** | see `git log -1 origin/plan/2026-10-24-cloud-memory-sync` |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Ryan starts the project and names the arc |
| **Track A ingest** | `~/.claude/projects/-home-lauer-Projects-convmem/d1951787-496f-4193-94a0-1387576053af.jsonl` |

---

## What to build

A plan, not code: `ARCHITECTURE-<slug>.md`, `EXECUTION-<slug>.md` and
`STATUS-<slug>.md` for two linked goals, with the workstation as the only
writer throughout:

1. Keep the cloud copy of ConvMem and the workstation ConvMem in step, in both
   directions.
2. Let Ryan use ConvMem from Claude apps (phone, web, desktop) with his
   computer off. Today only the ChatGPT environment can do that.

**Why this exists:** the cloud migration finished on 2026-10-25 (UTC). Ryan can
now ask ConvMem questions from his phone with his computer off. But the cloud
copy is read-only and frozen:

1. **Cloud to workstation is missing.** Phone conversations are never
   captured. The cloud runtime has no capture or ingestion, and the
   workstation cannot see cloud chats (`codex cloud list` returns nothing for
   this account; no transcript lands on disk).
2. **Workstation to cloud is missing.** The cloud copy holds the backup
   snapshot taken 2026-10-23 at 00:19 CDT. Nothing indexed since then
   reaches the phone.
3. **Claude apps have no cloud route.** Remote Control works today, but only
   while the computer is on.

---

## Integration point

### Workstation side (authority)

- The watcher (`convmem watch`, deployed from `.worktrees/runtime-main`)
  indexes configured transcript roots. The ledger and
  `~/.local/share/convmem/knowledge_units.jsonl` stay the single source of
  truth; Ryan is the only ledger writer.
- `convmem index --file <path>` is the existing on-demand ingest path.

### Cloud side (replica)

- A ChatGPT cloud environment named `convmem` (Codex > Cloud > convmem),
  attached to this repository, published with visibility Only me.
- Runtime `/workspace/convmem-runtime`; database `data/chroma`; activation
  `activate.sh`; lifecycle `environment-install.sh` and
  `environment-start.sh`; guide `/workspace/.convmem-cloud/start.md`.
- Generation is DeepSeek `deepseek-v4-flash` with
  `CONVMEM_FAIL_ON_FALLBACK=1`. Embeddings come from a CPU Ollama on
  `127.0.0.1:11435` (`nomic-embed-text`) with the pinned BGE reranker.
- Each new chat copies the published files into its own layer when it first
  opens the database (about 6.5 GB). A chat's writes never reach the published
  environment or other chats.

---

## Specification

### Verified facts to design against (fresh-task check, 2026-10-25 02:18 UTC)

- After Republish, a brand-new chat found the full runtime: config and doctor
  hashes matched, 112,837 serving units (113,342 physical rows), and nothing
  was restored or downloaded.
- A cited answer used only DeepSeek and the local embedder (4 provider calls),
  and memory tables were unchanged. A phone follow-up in the same chat also
  answered with citations, and those ledger ids match the workstation's
  `knowledge_units.jsonl`.
- Disk: 31.45 GiB filesystem; active memory 13.22 GiB allocated; 23.3 GiB free
  in a fresh chat after first use.
- `OPENAI_CLUSTER` is a platform variable. Check key variables by name, not
  with `grep OPENAI`.
- An unscripted phone question in a new chat found the runtime without help,
  but answered from the runtime's setup files (migration manifest, setup
  status), not from ConvMem retrieval. The question's answer postdated the
  snapshot, so retrieval could not have answered it. Whether a plain question
  uses retrieval is still unproven.
- **Known stale state:** the published environment's setup notes and manifest
  steps still say Edit/Publish and the fresh-task check are pending. Both
  passed on 2026-10-25. The start guide also sends new chats to Drive first
  (unreachable from cloud chats) and never says to answer memory questions
  with `convmem ask`, which likely explains the plain-question miss.
  **Pending Ryan GUI step (2026-10-25):** one Edit chat with the prepared
  prompt (local path in Related files), Republish, then one new chat asking
  only "Why was my ConvMem watcher stuck at a 4G memory cap when I'd set
  8G?" Pass: a cited answer naming a late-sorting systemd drop-in and #308.
  The cloud `downloads/` folder stays (install recovers from it); the Drive
  handoff is deliberately not refreshed.

### Claude app access: facts as of 2026-10-24

Claude Code docs, "Configure cloud environments"
(https://code.claude.com/docs/en/cloud-environments), checked 2026-10-24:

- Anthropic-hosted cloud sessions get about 4 vCPUs, 16 GB RAM and 30 GB of
  disk. The ConvMem runtime needs about 18 GB (13.2 GiB memory, 2.4 GB models,
  1.7 GB Python).
- A setup script runs as root on Ubuntu 24.04. If it finishes within about
  5 minutes, its filesystem is snapshotted and reused by later sessions.
  Running processes are not kept, so Ollama must start per session (for
  example from a SessionStart hook).
- The snapshot is rebuilt when the script or allowed hosts change, and after
  about 7 days. That weekly rebuild could also serve as the workstation-to-
  cloud refresh, if the setup script pulls a copy the workstation keeps fresh.
- Network secrets are per-host bearer tokens added by the proxy (Anthropic-
  hosted environments only). The DeepSeek key fits this model. The setup
  script runs before the environment's variables are set.
- Cloud sessions clone the repository, so its `CLAUDE.md` loads there. It can
  hold non-sensitive usage instructions; this repository is public.

Candidate routes:

| Route | Works in | Computer off | Main cost |
|---|---|---|---|
| Remote Control | Claude app driving the workstation's Claude Code | No | none |
| Claude Code cloud environment | Claude Code in any Claude app | Yes | private download source; 5-minute setup budget; porting `/workspace` scripts |
| Custom connector (remote MCP) | plain Claude chats in any Claude app | Yes | always-on server (about $10-25/month), HTTP transport and auth for the MCP server, security review |
| DeepSeek agent on an always-on server | a private web page in any phone browser | Yes | same always-on server; private network only; security review; developer-preview software |

### DeepSeek route: facts as of 2026-10-25

Added by Ryan's "yes" on 2026-10-25. Sources: a third-party article about
DeepSeek Harness (Composio), not yet checked against DeepSeek's own docs.

- DeepSeek has no hosted, Codex-style environment, and its consumer app has
  no known custom tool connector. The route is self-hosted.
- DeepSeek Harness (`dsh`) is an open-source Node.js agent in developer
  preview with a web interface (`pnpm dsh web`). Its MCP client plugin
  supports stdio and streamable HTTP with static headers only (no OAuth).
- The harness can run shell commands, so it must never face the internet: a
  private network the phone joins (for example Tailscale) plus a Copilot
  security review.
- **Why it matters for sync:** chats would live on Ryan's own server, so the
  workstation could pull and index them. That makes it the only candidate
  route that also closes the cloud-to-workstation capture gap. The log format
  is unverified and would need a new ConvMem parser.
- A lighter variant: a private page on the same server that runs
  `convmem ask` directly. Cited answers only, no multi-step agent work.
- DeepSeek `deepseek-v4-flash` costs pennies per question and uses no Codex
  budget.

### ChatGPT cloud environment: facts as of 2026-10-25

OpenAI's "Cloud environments" guide (learn.chatgpt.com), read 2026-10-25:

- Environments can join a private network over Tailscale (reusable,
  ephemeral auth key, set under Advanced > VPN). The ChatGPT environment
  could therefore fetch refreshes from the same always-on private server
  that other routes need. This is a candidate answer to question 7.
- Network secrets: programs see a placeholder; the proxy substitutes the real
  value only for allowed HTTPS destinations.
- Computer and browser use are not supported in cloud environments yet.
  Skills stored in the repository are available; personal skills from the
  workstation are not synced.

### Constraints the architecture must respect

- **One writer.** The cloud copy is a replica. It never writes the ledger,
  and the design must not create two diverging corpora.
- **This repository is PUBLIC.** No memory content, conversation notes, Drive
  ids, environment ids, account identifiers or secrets may be committed or
  pushed here. A Git-based route needs a separate private repository.
- **Transfer limits seen in practice.** Edit chats could not reach private
  Drive. Chat attachments are capped at 32 MiB per file, so the first
  transfer took 54 chunks. Publishing an environment is a manual GUI step.
- **Network policy is an allowlist.** Any new host is a deliberate Ryan
  change. Do not add speculative hosts.
- **No OpenAI provider.** OpenAI authentication was removed from the
  environment; generation stays on DeepSeek.

### Questions the architecture must answer

1. **Capture route (cloud to workstation).** Candidates: a private channel
   the workstation can read (a private repo or private Drive folder, if
   reachable), a ChatGPT data export, or the current manual workaround (paste
   the chat's summary into a Codex session, which the watcher indexes). How is
   provenance recorded so a cloud note is distinguishable from a local
   transcript?
2. **Refresh route (workstation to cloud).** Full re-transfer (about 1.7 GB
   compressed active memory plus republish) versus an incremental delta
   (new units plus embeddings, or units only with re-embedding on cloud CPU).
   What does each cost in time, disk and Ryan GUI steps?
3. **Freshness target.** How stale may the phone copy be (daily, weekly, on
   demand)? Ryan decides; the plan proposes options.
4. **Who triggers each direction,** given the workstation is off when the
   phone is used.
5. **Verification per cycle.** Reuse the fresh-task check: hashes, serving
   count, one cited answer with fallback forbidden, and unchanged memory
   fingerprints.
6. **Client route.** Which of the four routes above, or a staged mix (for
   example the cloud environment first, the connector later)? Does the
   ChatGPT environment stay, or does Claude replace it? Can one private
   always-on server back the connector, the DeepSeek route and the refresh
   source at once?
7. **Private download source.** The Claude cloud route needs a place the
   setup script can fetch the memory package from with a fixed bearer token.
   Drive does not fit (its access tokens expire hourly). Candidates include a
   private object store behind a token check or a private dataset host. Ryan
   decides where his memory may live.
8. **Setup time.** Can install plus fetch plus extract finish inside about
   5 minutes? If not, what moves to a per-session step, and how slow is a
   session start then?

### Output / contract

- An ARCHITECTURE and an EXECUTION plan with slices small enough for Cursor,
  each with hermetic tests, plus a STATUS brief from the JudgeBench 10-section
  template.
- A target of at most one Ryan GUI step per sync cycle, or an explicit reason
  why more are needed.

---

## What NOT to build

- No code, scripts, config or runtime changes in this planning phase.
- No ingestion into the cloud copy, and no second ledger writer.
- No change to the live watcher, its config, or the published cloud
  environment.
- No OpenAI troubleshooting or OpenAI provider path.
- Do not make the manual 54-chunk transfer the design. It was a one-time
  bootstrap.
- Nothing private in this public repository (see Constraints).
- No internet-facing ConvMem server or custom connector without a security
  review (Copilot audit lane) of its authentication and exposure.

---

## Test expectations

The plan must name, per slice: hermetic tests (`tmp_path`, no live corpus),
a privacy check that nothing private is staged for a public remote, and the
live acceptance check (a fresh cloud chat after publish, using the same
fields as the 2026-10-25 check).

---

## Acceptance criteria

- [ ] Ryan has named the arc; ARCHITECTURE, EXECUTION and STATUS use one slug
- [ ] STATUS is listed in `AGENTS.md` and `config/agent-protocol.md`
- [ ] Both directions are covered, or one is deferred with a stated reason
- [ ] A client route (Claude or DeepSeek) is chosen, or deferred with a stated reason
- [ ] Privacy constraint enforced: no route publishes memory to a public place
- [ ] Ryan GUI steps per cycle stated and minimized
- [ ] Kiro review requested on the exact plan revision

---

## Branch convention

```
plan/2026-10-24-cloud-memory-sync   (this brief)
plan/YYYY-MM-DD-<arc-slug>           (Codex planning, from origin/main)
```

Push immediately after each commit with an explicit refspec. Ryan
squash-merges unless a PR says **Do not squash**.

---

## Related files

| What | Path |
|------|------|
| Transfer materials, evidence, prior cloud guides (local only, not in Git) | `/home/lauer/tmp/convmem-cloud-20261023/` |
| Latest cloud setup guide snapshot (local) | `/home/lauer/tmp/convmem-cloud-20261023/reports/cloud-startup-correction-20261024/convmem-runtime/CLOUD-ENVIRONMENT-SETUP.md` |
| Fresh-task check prompt (local) | `/home/lauer/tmp/convmem-cloud-20261023/reports/fresh-task-prompt-20261025.txt` |
| Edit prompt for the stale notes (local) | `/home/lauer/tmp/convmem-cloud-20261023/reports/cloud-edit-prompt-20261025.txt` |
| Record-template fix (Cursor, separate) | `docs/inter-model/CURSOR-2026-10-25-record-template-constraint-handoff.md` on `docs/2026-10-25-record-template-constraint-handoff` |
| Private Drive migration manifest | id recorded in the local transfer materials; never commit it here |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet with link and resume state
- [ ] `STATUS-*.md` Update Log line (no STATUS yet; Codex creates it)
- [x] Branch pushed

**Planner (picking up):**

- [ ] Confirm Ryan started the project and named the arc
- [ ] Read this file, then the local setup guide above
- [ ] State Goal / role / system state / next action once STATUS exists

<!-- ref: ./LATEST.md — routing bullet for this future project -->
<!-- src: /home/lauer/tmp/convmem-cloud-20261023/reports/cloud-startup-correction-20261024/convmem-runtime/CLOUD-ENVIRONMENT-SETUP.md — cloud runtime layout and limits -->
