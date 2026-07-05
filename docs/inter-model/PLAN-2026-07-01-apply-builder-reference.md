# Plan: Apply builder-reference to past work and future planning

---
builder_lens:
  primary: ousterhout
  verify: scripts/verify-builder-reference.sh + scripts/validate-builder-reference-surfaces.sh
---

**Status:** enriched — **execution shipped** (2026-07-01)  
**Original author:** Cursor Auto  
**Reviewer:** Claude Cloud  
**Verdict:** Enrich as planned, with two scope corrections  
**Operational guide:** [`docs/builder-reference/notes/suggested-application-of-builder-material.md`](../builder-reference/notes/suggested-application-of-builder-material.md)

**Handoffs (shipped):**

| To | File | Tarball |
|----|------|---------|
| Claude Cloud (plan enrichment) | [`HANDOFF-CLAUDE-CLOUD-2026-07-01-builder-reference.md`](HANDOFF-CLAUDE-CLOUD-2026-07-01-builder-reference.md) | `handoff-builder-reference-2026-07-01.tar.gz` |
| ChatGPT (literature review) | [`HANDOFF-CHATGPT-2026-07-01-builder-reference-literature.md`](HANDOFF-CHATGPT-2026-07-01-builder-reference-literature.md) | `handoff-chatgpt-literature-2026-07-01.tar.gz` |
| Kiro / Crush / Codex | [`HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md`](HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md) | repo access (no tar) |

**Execution gate:** todos below **paused** until ChatGPT returns `LITERATURE-RECOMMENDATIONS.md` and Ryan accepts/rejects titles.

**Local agents:** Kiro, Crush (DeepSeek/Charm), Codex — read [`HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md`](HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md) after this plan.

---

## Execution todos

| # | Id | Task | Status |
|---|-----|------|--------|
| 1 | `fix-readme-drift` | Fix README pragmatic dead link — archive-only; delete main-table row | **done** |
| 2 | `reconcile-verify-thresholds` | Align verify scripts: PASS ≥1500 ship gate; ≥2500 aspirational WARN | **done** |
| 3 | `annotate-built-plans` | `Builder lens` column on BUILT-PLANS + optional-gate rows in ROADMAP | **done** |
| 4a | `ddia-changelog` | Dated log for DDIA 1,230→2,055 undocumented growth | **done** |
| 4b | `expand-arch-patterns` | Expand arch-patterns-python (989→1,500+) — F1 queue, tombstone, UoW rollback | **done** |
| 5 | `promote-ddia-surfaces` | DDIA → Cursor/Kiro/Codex + deploy `required[]`; Crush tier-A unchanged | **done** |
| 6 | `plan-frontmatter` | `builder_lens` YAML in PLAN-*.md | **done** |
| — | `claude-handoff-tar` | Handoff + tarball for Claude Cloud review | **done** |
| — | `chatgpt-literature-tar` | Handoff + tarball for ChatGPT literature review | **done** |
| — | `kiro-crush-codex-handoff` | LATEST + unified handoff for local shell agents | **done** |

---

## 0. Corrections to Cursor's original plan (read first)

Word counts re-measured from archive (not trusting initial estimates):

| Digest | Original claim | Actual | Verdict |
|--------|----------------|--------|---------|
| `ddia-builder-digest.md` | "~900–1200 words… expand first" | **2,055 words** | Wrong. Above 1,500 target. Expanded after add-log (1,230) with no changelog — needs paperwork, not more words. |
| `arch-patterns-python-builder-digest.md` | grouped with DDIA as thin | **989 words** | Correct. Actual expansion priority. |
| `archive/pragmatic-programmer-builder-digest.md` | not scored | 299 words | Archive-only; exempt from expansion target. |

**Script threshold mismatch (new gap):**

| Script | Gate |
|--------|------|
| `verify-builder-reference.sh` | WARN &lt;800, WARN &lt;1500, **PASS ≥1500** |
| `validate-builder-reference-surfaces.sh` | FAIL &lt;1500, WARN 1500–2499, **PASS ≥2500** |

Under the stricter script: Zeller (2,352), Hard Parts (2,499), DDIA (2,055) sit in WARN, not PASS. Reconcile before agents chase false FAILs.

**Standing Crush context today:** four tier-A digests ≈ 10,380 words (~13.5–14.5k tokens). DDIA adds ~2,700–2,900 (~20% increase).

---

## 1. Verdict

**Enrich as planned.** Shape: fix drift → reconcile thresholds → annotate retro docs → DDIA changelog + expand arch-patterns → surface promotion → front-matter ritual → operational use. Tuning pass, not redesign.

---

## 2. Core workflow (unchanged)

From `suggested-application-of-builder-material.md`:

1. Pick digest by change shape
2. State change in one sentence (no implementation names)
3. Classify win: deeper module / better retrieval / less coupling / easier repro
4. Smallest change that satisfies goal
5. Verify with existing fitness checks
6. `convmem record` so next session does not rediscover it

**Tie-breaker:** surface → Manning → Zeller → DDIA → Hard Parts (user-visible complexity removal).

---

## 3. Revised retroactive table

| Shipped work | Digest(s) | Principle |
|--------------|-----------|-----------|
| Global protocol rollout | **Ousterhout** + Pragmatic (archive) | Deep SSoT (`agent-protocol.md`) → thin per-surface slices |
| `convmem doctor` + alien soak | **Zeller** | Systematic repro before PASS |
| F2a store API, `ledger_id` dedupe | **Manning** + **DDIA** | Ranking/citation + derived index follows ledger |
| `watch` / `refine` (Milestone F) | **DDIA** + **Arch Patterns** | Stream consumer + F1 job queue as event-handler/message-bus pattern |
| Tombstone / `chroma_dedupe` (F1) | **Arch Patterns** + **DDIA** | Repository filter point (`include_superseded=False`) — strongest mapping |
| Golden eval 10/10 (P1b) | **Manning** | Fixed query set; Ch.8 eval methodology |
| `recency_weight` on `ask --evidence` | **Manning** | Ranking ≠ generation |
| Restic fail-closed gate | **unmapped** *(weak DDIA)* | Fail-closed backup-before-write ≠ replication lag |
| P2 held (no MCP `unresolved`) | **Hard Parts** + **Ousterhout** | No surface until matrix FAIL |
| Cross-project digest Phase 0–1 | **Hard Parts** + Second Brain (archive) | Script + brief, not query service |
| Builder-reference system | **Ousterhout** | Book knowledge in digests; rules lean |
| Interactive soak (2026-07-01) | **Manning** | All four surfaces cited Manning |

**Retro doc action:** Add `Builder lens` as 5th column on BUILT-PLANS index (`ouster`, `manning`, `zeller`, `hard-parts`, `ddia`, `arch-pat`). Optional-gate rows in ROADMAP.

---

## 4. Revised forward-mapping table

| Item | Read first | Anti-pattern |
|------|------------|--------------|
| **P1c** streaming synthesis | Ousterhout + Manning | Prompt expansion vs `llm.py`/`ask.py` depth; cite in P1c plan when work starts |
| **P2** MCP `unresolved` (held) | Hard Parts + Zeller | New MCP when CLI + brief suffice |
| **F1** refine job queue | DDIA + Arch Patterns | Ledger/Chroma blur; per-query filter duplication |
| **P3** hybrid retrieval | Manning | Ship without golden regression |
| **Change feed** (2026-07-07) | Ousterhout | Surface layer documenting drift |
| **Crush deploy of new digests** | Ousterhout (token budget) | See §6 |
| **Restic gate — future iterations** | *unmapped* | Hard Parts if multi-repo ownership; don't force-fit now |

**Planning ritual:** new `docs/inter-model/PLAN-*.md` files carry:

```yaml
builder_lens:
  primary: manning   # ousterhout | zeller | ddia | hard-parts | arch-patterns
  verify: golden queries + convmem ask
```

---

## 5. Prioritized execution order

1. **Fix README pragmatic link** — dead link to root `pragmatic-programmer-builder-digest.md`; archive-only lane; delete main-table row, keep archive row.
2. **Reconcile verify-script thresholds** — ≥1500 as ship gate in both; ≥2500 aspirational WARN in `validate-builder-reference-surfaces.sh`; document in script headers.
3. **Add `builder_lens` column** to BUILT-PLANS + optional-gate rows in ROADMAP.
4. **DDIA changelog entry** (1,230→2,055) + **expand arch-patterns-python** (989→1,500+) with F1/tombstone hooks — DDIA needs paperwork, not words.
5. **Promote DDIA** to Cursor + Kiro + Codex pointers + deploy `required[]`; **defer Crush** `global_context_paths` until Ryan token-budget call.
6. **6-step operational pattern** in next real session (P1c or F1); record with `--relates-to` from `search_fast`.

No corpus reindex for doc-only steps. Ryan runs `convmem record` when closing a substantive decision.

---

## 6. Surface-wiring — DDIA

| Surface | Mechanism | Add DDIA now? |
|---------|-----------|---------------|
| **Cursor** | `.mdc`, glob-scoped, on-demand | **Yes** — free |
| **Kiro** | Steering, `inclusion: manual` | **Yes** — free |
| **Codex** | `AGENTS.md` pointer list only | **Yes** — ~15 tokens/line |
| **Crush** | `global_context_paths` full text every session | **Defer** — ~20% floor increase |

Crush has no glob-scoped conditional load (per F2c note) — state plainly in README so tier-A bias doesn't silently default to "no."

---

## 7. Digest expansion brief

**arch-patterns-python** (989 → 1,500+ — real priority)

- Command/Event vocabulary on F1 job queue (`chroma_dedupe` = command, `superseded: true` = event)
- Aggregate + `refine_undo/<job>/<timestamp>.jsonl` rollback (Unit of Work)
- Message Bus: formalize `watch → index` / `record → index` before P2 or stay implicit?

**ddia** (2,055 — changelog only)

- Dated log entry for 1,230→2,055 growth (match Manning/Ousterhout pattern); note if unreconstructable

**hard-parts** (2,499) — 1 word under strict 2,500 PASS; confirm rounding before treating as gap.

**zeller** (2,352) — no content gap; threshold reconciliation only.

---

## 8. Risks (canon → second canon)

1. **Undocumented digest growth** — DDIA pattern; repeat → `convmem record`
2. **Two scripts, two thresholds** — latent agent trap; fix in step 2
3. **Crush no conditional load** — biases tier-A toward "no"; state in README
4. **`builder_lens` honor-system** — needs verify hook or dies after 2–3 sessions
5. **Force-fitting digests** — use explicit **unmapped** category (Restic row)

---

## 9. What not to do

- Copy digest content into protocol rules or inter-model plans
- Use archive digests for infra unless capture-workflow change
- Treat builder-reference verify as substitute for `convmem doctor`
- Expand DDIA for word count (already sufficient)
- Load all 9 digests into Crush without trade-off table

---

## Ledger anchors

| Id | Topic |
|----|-------|
| `dec_prop_20260701_122838_13dc` | 5 new book digests |
| `dec_prop_20260701_022733_b844` | builder-reference SSoT + wiring |
| `dec_prop_20260629_212545_8aae` | roadmap gap audit + P1c slot |
| `dec_prop_20260623_161428_c311` | protocol root (fallback) |
