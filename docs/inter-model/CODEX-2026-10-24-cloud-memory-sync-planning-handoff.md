# Planning Handoff: two-way sync between workstation ConvMem and the cloud copy

**Date:** 2026-10-24
**Author:** Claude (cloud-migration coordination)
**For:** Codex (architecture and execution planning)
**Authorization:** Ryan, 2026-10-24, verbal: "make that a future project". This
authorizes recording the project only. Planning starts when Ryan says so.
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
`STATUS-<slug>.md` for keeping Ryan's cloud copy of ConvMem and his workstation
ConvMem in step, in both directions, with the workstation as the only writer.

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
| Fresh-task check prompt (local) | `/home/lauer/tmp/claude-1000/-home-lauer-Projects-convmem/d1951787-496f-4193-94a0-1387576053af/scratchpad/fresh-task-prompt.txt` |
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
