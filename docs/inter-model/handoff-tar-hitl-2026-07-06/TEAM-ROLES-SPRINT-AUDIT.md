# Willowy Hollow bug sprint — team roles audit (as-run)

**Sprint:** 2026-07-05 — present  
**Client:** `willowyhollow-practice` (Docker `:8081`)  
**Artifact:** `logs/2026-07-05-code-review-findings.md` (~82 findings)  
**Indexed copies:** `docs/inter-model/WILLOWYHOLLOW-CODE-REVIEW-FINDINGS.md` + `…-AUDIT.md`

---

## Intended vs actual roles

| Canon role | Agent / surface | Sprint assignment | As-run behavior | Grade |
|------------|-----------------|-------------------|-----------------|-------|
| Finder / breadth review | **Crush** (often DeepSeek V4 inside Crush) | Code review → findings log | Produced large findings markdown; indexed via `crush.db` + log sync | **Correct lane** — model brand ≠ agent role |
| Independent verifier | **Codex** | Confirm/deny findings vs live stack | Audit session in `rollout-*.jsonl`; wrote `…-findings-audit.md` when tasked | **Correct** |
| Design review / sign-off | **Kiro** | Review findings 69/73; no unsolicited record | Read audit; discussed; indexed `messages.jsonl` | **Mostly correct** — early tendency to offer `record` at task end (protocol fixed) |
| Implementer (infra) | **Cursor** | convmem ingest, `--supersede`, handoff scripts, protocol | Shipped Track A/B split, Codex rollout adapter, handoff shell | **Correct** |
| Implementer (client WP) | **Cursor / Ryan** | Theme, stack, deploy scripts | Ongoing in practice repo (separate from convmem) | **Correct split** |
| Synthesis | **DeepSeek API** | `convmem ask` / search summaries only | Used for retrieval synthesis, not primary bug author | **Correct when API-only** |
| Strategy / external review | **Claude Cloud** | Plan enrichment (builder-reference); **this handoff** | Prior tar review 2026-07-01; new charter review requested | **Correct** |
| Human gate | **Ryan** | Approve records; phrasebook; run handoff script | Approved many Crush verification records; agreed umbrella record at end | **Correct** — watch per-finding record creep |

---

## Role confusion to flag for Claude

### 1. "DeepSeek is looking for bugs"

**Operator language:** "DeepSeek is hunting bugs."  
**Correct framing:** **Crush** is hunting bugs **using** DeepSeek V4 as runtime model.  
**Risk:** Assigning bug discovery to "DeepSeek agent" blurs Tier B synthesis API with Tier A shell agent. Future supervisor may route tasks to wrong surface.

### 2. Handoff vs record

Models conflated **session ingest** (`convmem index --file`) with **durable ledger** (`record --approve-last`).  
**Fixed in protocol:** handoff ≠ record; Kiro must not volunteer record at task end.

### 3. Track A vs Track B

"Index what you wrote" caused models to index **only** `logs/*.md` and **skip** chat (`crush.db`, Kiro jsonl, Codex rollout).  
**Fixed:** phrasebook — ingest your chat / index the log / ingest everything.

### 4. Per-finding records

Early impulse: one `dec_prop_*` per Crush finding.  
**Ryan decision:** index for inventory; **one umbrella record** at sprint end. Correct HITL pattern.

### 5. Codex improvising markdown

Codex created audit file when asked to verify — **valid**. Protocol now says: no new `logs/*.md` unless Ryan asked.

---

## Recommended sprint team (for Claude to validate)

```text
Crush (DeepSeek V4)  →  discover / log findings (Track B source + Track A chat)
Codex                →  independent audit (Track A rollout + audit md Track B)
Kiro                 →  design review, signing (--signer kiro-review on close only)
Cursor               →  tooling + convmem infra; WP implementation when scoped
Ryan                 →  handoff script, approve-last, orchestration phrases
DeepSeek API         →  ask/search synthesis only — never primary bug author
Claude Cloud         →  strategy, role charter, external review (this tar)
```

**Not yet assigned (deferred):** event-driven supervisor, linker Phase 2, auto `--propose` approval.
