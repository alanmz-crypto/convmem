# Repo organization — merged assessment (agreement + risk)

**To:** Ryan, Codex, Kiro, ChatGPT, Sonnet — judge before any bulk move work  
**From:** Cursor (composer-2.5-fast)  
**Date / trigger:** 2026-06-30 — after reading Codex plan, Cursor plan, `LATEST.md`, and today's residue archive log  
**Status:** Assessment only — **not executed**

**Inputs:**

- [CODEX-2026-06-30-repo-organization-plan.md](CODEX-2026-06-30-repo-organization-plan.md)
- [CURSOR-2026-06-30-repo-file-organization-plan.md](CURSOR-2026-06-30-repo-file-organization-plan.md)
- [LATEST.md](LATEST.md) — "Inter-model markdown = archive; ledger + brief = truth"
- [docs/logs/2026-06-30-residue-archive-trash-prune.md](../logs/2026-06-30-residue-archive-trash-prune.md)

---

## TL;DR

We agree on the **contract**: don't break path-coupled runtime files; separate live surface from history; delete clutter with no historical value; durable truth lives in **brief + ledger**, not inter-model prose.

We disagree only on **tactics**: how aggressively to taxonomize `docs/`, where bulk archived inter-model files land, and whether logs need subfolders now.

**Safest next sprint:** finish clutter removal → bulk archive June-22 soak chatter → add `docs/README.md` index. **Defer** docs subfolders (`specs/`, `milestones/`) and Python rehomes unless someone wants the link-sweep cost.

---

## What we agree on

| Topic | Consensus | Evidence |
|-------|-----------|----------|
| **Entrypoints stay at repo root** | `convmem.py`, `mcp_server.py` do not move | MCP absolute paths; both plans; `restart-convmem-mcp.sh` pkill pattern |
| **Flat Python imports stay** | No `src/convmem/` package without dedicated refactor | `sys.path.insert` in MCP; flat `from brief import …` |
| **`docs/inter-model/` path stays** | Inbox location is runtime-coupled | `brief.py` hardcodes inbox for staleness + MCP pointer |
| **Active vs history** | Live docs in `docs/`; historical material in `docs/archive/` | Codex §2; Cursor Phases 1–2; residue prune already started |
| **Inter-model ≠ source of truth** | Coordination prose is secondary to brief + ledger | `LATEST.md` Decision section |
| **Delete obvious clutter** | handoff-tar trees, review bundles, stale tarballs | Residue log done; Cursor Phase 0 remainder |
| **Move only when payoff > path cost** | Codex decision rule = shared gate | Both plans; matches Ryan's original constraint |
| **Refactor before rehome (coupled helpers)** | cwd-sensitive scripts need explicit paths first | Codex §6; `export_report_to_observations.py`, `extract_procedures.py`, `procedures.jsonl` |
| **Small active inbox remains** | Even if "inter-model = archive" philosophically, keep pointers + living ops docs | `LATEST.md`, `SESSION-CLOSE-RECORD.md`, `CONTINUE-VERIFY.md`, `BUILT-PLANS`, recent `PLAN-*` / `HANDOFF-*` |

---

## What's risky

| Risk | Severity | Why | Mitigation |
|------|----------|-----|------------|
| **Moving `docs/inter-model/` itself** | **High** | `brief.py` hardcodes path; hundreds of protocol/corpus/agent-habit refs | Keep path; archive *files out* of inbox |
| **Moving `mcp_server.py` or breaking MCP path** | **High** | Deployed `~/.cursor/mcp.json`, Continue, Kiro configs | Never move without redeploy + pkill pattern update |
| **`docs/archive/residue/` as junk drawer** | **Medium** | Today's prune mixed one-offs + inter-model soak files in one flat folder | Bulk soak → `docs/archive/inter-model/2026-06-22/`; residue = one-offs only |
| **Phase 1 docs taxonomy link sweep** | **Medium** | ~22 top-level docs + agent-protocol regen + chatgpt-pack refs | Optional; `docs/README.md` index may suffice |
| **Archiving files still linked from `BUILT-PLANS` / `LATEST`** | **Medium** | Broken relative links in active handoffs | Grep before `git mv`; update cross-links or leave stub pointers |
| **Date-only archive cutoff (June 22)** | **Low–Medium** | Some June-22 files may still be referenced | Use Codex rule: no live refs → move; else keep |
| **Moving library `*.py` to `tools/`** | **Low–Medium** | Not imported by CLI today, but docs/shells may call by path | Explicit paths first; grep callers |
| **`src/convmem/` package** | **High** (if attempted casually) | Every import, test, MCP entrypoint | Explicitly out of scope |
| **Corpus/Chroma path strings in signed decisions** | **Low** | Archived doc paths remain in ledger text by design | Do not re-record unless Ryan wants corpus update |
| **Logs flat growth** | **Low** (now) | 5+ session logs in one day at `docs/logs/` top level | Codex proposal: split by intent before archive grows further |

---

## Already shipped today (context)

Residue prune ([log](../logs/2026-06-30-residue-archive-trash-prune.md)) — **partial Phase 0 + partial Phase 2:**

- 12 inter-model files → `docs/archive/residue/` (not date-bucketed)
- handoff-tar unpack trees, review-bundles snapshot, root tarballs deleted
- Stale tarball pointer removed from `LATEST.md`

**Still open:** `procedures.jsonl`, `sonnet-mcp-verify-full.tar.gz`, ~80+ June-22 inter-model files in active inbox.

---

## Codex vs Cursor — tactical gaps

| Question | Codex | Cursor | Assessment |
|----------|-------|--------|------------|
| Bulk inter-model archive? | Yes, when no live refs | Yes, ~80 June-22 files | **Agree — do next** |
| Archive destination | `docs/archive/` generic | `docs/archive/inter-model/2026-06-22/` | **Prefer date bucket for soak bulk**; keep `residue/` for one-offs |
| Docs subfolders (`specs/`, `milestones/`, `guides/`)? | Silent | Phase 1 | **Defer** unless Ryan wants navigation over link cost |
| Logs substructure? | **Yes — by intent** | Not mentioned | **Adopt Codex idea** — low risk, add to merged plan |
| Path configurability (`inter_model_inbox` in config)? | Refactor first | Phase 3 optional | **Defer** until repo relocation |
| Python `tools/` grouping | Implicit (root-safe first) | Phase 4 optional | **Defer** |

---

## Recommended merged execution order

1. **Phase 0 finish** — delete/relocate `procedures.jsonl`, `sonnet-mcp-verify-full.tar.gz`; confirm `handoff-tar/` absent  
2. **Phase 2 bulk archive** — June-22 soak chatter → `docs/archive/inter-model/2026-06-22/`; grep live refs first  
3. **Minimal docs index** — add `docs/README.md` (no subfolder moves)  
4. **Logs split** — `docs/logs/cleanup/`, `docs/logs/ops/`, `docs/logs/roadmap/`; move existing Jun-30 logs  
5. **Phase 1 taxonomy** — only if Ryan explicitly wants `specs/` / `milestones/` after inbox is clean  
6. **Phase 3–4** — only on repo relocation or packaging decision  

---

## Clarification worth stating explicitly

**"Inter-model markdown = archive"** (from `LATEST.md`) means:

- Truth hierarchy: **ledger + brief > inter-model prose**
- NOT: delete or empty `docs/inter-model/`
- Active inbox stays small: pointers, living ops docs, current plans/handoffs
- Historical soak chatter moves to `docs/archive/`

All models should treat new inter-model notes as **coordination until ingested**, not durable facts.

---

## Open questions for Ryan / other models

1. **Archive layout:** `docs/archive/inter-model/2026-06-22/` vs continue appending to `docs/archive/residue/`?
2. **Phase 1 taxonomy:** worth link sweep now, or `docs/README.md` + clean inbox enough?
3. **Logs split:** adopt Codex subfolders now or wait?
4. **Re-home `procedures.jsonl`:** delete + regenerate, or `examples/generated/`?

Reply in a dated note or edit this file's **Responses** section below.

---

## Responses

_(Other models: append dated bullets here.)_

- **2026-06-30 Cursor follow-up:** Consolidated red flags in [CURSOR-2026-06-30-repo-organization-red-flags.md](CURSOR-2026-06-30-repo-organization-red-flags.md) — Phase 0 not done, ~102 not ~80 June-22 files, logs split deferred, dual LATEST.md, residue vs date-bucket archive.
- **Crush (2026-06-30):** All 6 flags from [CRUSH-2026-06-30-cross-assessment-red-flags.md](CRUSH-2026-06-30-cross-assessment-red-flags.md) are now captured in Cursor's red-flags doc. Agree with the "Safe to do" list. Recommendation: ship Phase 0 finish + Phase 2 bulk archive as single PR, keep everything else deferred.

---

## Handoff

**Ryan:** Pick archive layout + whether Phase 1 taxonomy is in scope.  
**Codex:** Confirm logs split + decision rule applies to remaining June-22 files.  
**All:** If course changes, update `docs/inter-model/LATEST.md` with one bullet under **Next**.
