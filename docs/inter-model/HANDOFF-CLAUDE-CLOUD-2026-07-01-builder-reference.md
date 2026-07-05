# Handoff: Apply builder-reference — for Claude Cloud enrichment

**Date:** 2026-07-01  
**From:** Cursor Auto (plan author)  
**To:** Claude Cloud (Opus or Sonnet)  
**Purpose:** Review Cursor's application plan for `docs/builder-reference/`; enrich retroactive mappings, surface-wiring decisions, and digest expansion priorities. **No code edits** — return enriched plan markdown Ryan can paste back.

**Status:** open  
**Owner:** Claude Cloud (review) → Ryan (merge)  
**Sunset:** after enriched plan merged or superseded

---

## Context (30 seconds)

convmem now has **9 curated book digests** under `docs/builder-reference/` plus an operational note at `notes/suggested-application-of-builder-material.md`. Four digests (Ousterhout, Manning, Zeller, Hard Parts) deploy to agent surfaces; five newer ones (DDIA, Arch Patterns, + 3 archive) are repo-only. Cursor produced a plan mapping this canon to **past shipped work** (BUILT-PLANS, Milestone F, protocol rollout) and **future optional gates** (P1c streaming, P2 MCP, F1 refine).

---

## Read order in this archive

1. `HANDOFF.md` (this file)
2. `PLAN-apply-builder-reference.md` — Cursor's plan under review
3. `builder-reference/notes/suggested-application-of-builder-material.md` — operational workflow
4. `builder-reference/README.md` — digest index
5. `context/BUILT-PLANS-2026-06-24-to-2026-06-29.md` — shipped work index
6. `context/ROADMAP.md` — optional gates
7. Digests as needed (do not read all 9 cover-to-cover unless judging a specific mapping)

---

## What Claude Cloud should judge

1. **Retroactive mapping** — Are digest assignments for shipped work correct? Missing links?
2. **Tier-A vs tier-B** — Should DDIA and Arch Patterns join the 4 deployed digests on Cursor/Codex/Kiro? Crush token budget trade-off?
3. **Expansion order** — Which thin digests (~900–1200 words) deserve 1500+ expansion first given F1 / P1c / P2?
4. **Planning ritual** — Is `builder_lens` YAML in PLAN front-matter the right weight?
5. **Anti-patterns** — Gaps in `suggested-application-of-builder-material.md`?
6. **Archive lane** — Smart Notes / Second Brain / Pragmatic: stay archive-only?
7. **README drift** — Pragmatic listed at repo root but file is under `archive/` only

---

## Expected output

1. **Verdict:** enrich as planned / modify scope / defer items
2. **Revised retroactive table** (shipped work → digest → principle)
3. **Revised forward-mapping table** (optional gates → digest → verify)
4. **Prioritized execution order** (may reorder Cursor's 5 steps)
5. **Surface-wiring recommendation** — explicit yes/no on DDIA in deploy + Crush token estimate
6. **Digest expansion brief** — 3–5 bullet targets per digest (hooks only, not full text)
7. **Risks missed** — anything that turns builder-reference into a second canon

Return **markdown only** — Ryan will paste back to Cursor for merge.

---

## Constraints

- Single user, single machine; local-first corpus
- MCP read-only; durable writes = `convmem record` + `--approve-last` (Ryan only)
- Do **not** quote copyrighted book text
- Do **not** propose full corpus reindex or bulk ingest
- `verify-builder-reference.sh` ≠ `convmem doctor`
- P2 MCP `unresolved` still **held**; change feed review **2026-07-07**

---

## Ledger anchors (`ledger-ids.txt`)

Use for any record-block suggestions:

| Ledger id | Topic |
|-----------|-------|
| `dec_prop_20260701_122838_13dc` | 5 new book digests added |
| `dec_prop_20260701_022733_b844` | builder-reference SSoT + surface wiring |
| `dec_prop_20260629_212545_8aae` | roadmap gap audit + P1c slot |
| `dec_prop_20260623_161428_c311` | protocol root (fallback `--relates-to`) |

---

## Files in this archive

```
handoff-builder-reference-2026-07-01/
├── HANDOFF.md
├── PLAN-apply-builder-reference.md
├── builder-reference/
│   ├── README.md
│   ├── SOURCES.md
│   ├── notes/suggested-application-of-builder-material.md
│   ├── ousterhout-builder-digest.md
│   ├── manning-builder-digest.md
│   ├── zeller-builder-digest.md
│   ├── hard-parts-builder-digest.md
│   ├── ddia-builder-digest.md
│   ├── arch-patterns-python-builder-digest.md
│   └── archive/
│       ├── smart-notes-builder-digest.md
│       ├── second-brain-builder-digest.md
│       └── pragmatic-programmer-builder-digest.md
├── context/
│   ├── ROADMAP.md
│   ├── MILESTONE-F.md
│   ├── LATEST.md
│   ├── BUILT-PLANS-2026-06-24-to-2026-06-29.md
│   ├── PLAN-2026-06-29-streaming-synthesis.md
│   └── logs/
│       ├── 2026-07-01-remaining-books-added.md
│       ├── 2026-07-01-manning-evaluation-expansion.md
│       └── 2026-07-01-ousterhout-errors-consistency-expansion.md
├── wiring/
│   ├── cursor-rules-builder-reference.mdc.example
│   ├── kiro-steering-builder-reference.example.md
│   ├── deploy-builder-reference.sh
│   ├── verify-builder-reference.sh
│   └── validate-builder-reference-surfaces.sh
└── ledger-ids.txt
```

**Excluded:** PDFs, `staging/builder-reference/` raw extractions, full source code.

---

## Ryan → Claude Cloud prompt

> Read `HANDOFF.md` and `PLAN-apply-builder-reference.md` first. Enrich the plan per **Expected output** in the handoff. Return markdown only — no code changes.
