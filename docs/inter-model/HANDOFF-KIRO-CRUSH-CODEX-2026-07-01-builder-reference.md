# Handoff: Builder-reference plan — Kiro, Crush (DeepSeek), Codex

**Date:** 2026-07-01  
**From:** Cursor Auto  
**To:** **Kiro** (reviewer), **Crush / Charm** (DeepSeek V4), **Codex** (shell monitor)  
**Purpose:** Persist the builder-reference application plan and external review lane so local-shell agents do not rediscover or contradict work already done in Cursor + cloud handoffs.

**Status:** active — execution **paused** pending ChatGPT literature review  
**Owner:** Ryan (merge literature) → Cursor (execute plan todos)  
**Read first:** [`docs/inter-model/LATEST.md`](LATEST.md) (always) → this file → canonical plan below

---

## One-screen summary

| What | Where |
|------|-------|
| **Canonical plan** (Claude-enriched) | [`docs/inter-model/PLAN-2026-07-01-apply-builder-reference.md`](PLAN-2026-07-01-apply-builder-reference.md) |
| **Builder digests** (9 books) | [`docs/builder-reference/README.md`](../builder-reference/README.md) |
| **How to use digests** | [`docs/builder-reference/notes/suggested-application-of-builder-material.md`](../builder-reference/notes/suggested-application-of-builder-material.md) |
| **Claude Cloud review** | [`HANDOFF-CLAUDE-CLOUD-2026-07-01-builder-reference.md`](HANDOFF-CLAUDE-CLOUD-2026-07-01-builder-reference.md) |
| **ChatGPT literature lane** (in flight) | [`HANDOFF-CHATGPT-2026-07-01-builder-reference-literature.md`](HANDOFF-CHATGPT-2026-07-01-builder-reference-literature.md) |
| **Session log** | [`docs/logs/2026-07-01-builder-reference-plan-handoffs.md`](../logs/2026-07-01-builder-reference-plan-handoffs.md) |

**Tarballs (repo root, gitignored):** `handoff-builder-reference-2026-07-01.tar.gz` (Claude), `handoff-chatgpt-literature-2026-07-01.tar.gz` (ChatGPT)

---

## What shipped this session (do not redo)

1. **Nine book digests** in `docs/builder-reference/` — four tier-A deployed to surfaces via `scripts/deploy-builder-reference.sh`
2. **Application plan** — map digests to past work + optional roadmap gates; Claude corrected word counts (DDIA 2,055 words — not thin; expand **arch-patterns-python** only)
3. **Claude Cloud enrichment** — merged into canonical plan; new step: reconcile `verify-builder-reference.sh` vs `validate-builder-reference-surfaces.sh` thresholds
4. **ChatGPT literature handoff** — paused execution until `LITERATURE-RECOMMENDATIONS.md` returns

---

## Execution gate (all implementers)

**Do not start plan todos 1–7** until Ryan pastes ChatGPT `LITERATURE-RECOMMENDATIONS.md` and accepts/rejects titles.

Pending todos (see plan file): README pragmatic link, script thresholds, `builder_lens` column, DDIA changelog, arch-patterns expansion, DDIA surface promotion (Cursor/Kiro/Codex — **Crush deferred**), front-matter ritual.

---

## Your role by surface

### Kiro (reviewer / signer)

- **Read** canonical plan §5–§8 before signing any builder-reference doc or digest expansion PR
- **Sign-off gate:** arch-patterns-python expansion (todo 4b) and DDIA surface promotion (todo 5) need Kiro review per Milestone F convention
- **Do not** reopen global protocol or P2 MCP — still **held** per [`ROADMAP.md`](../ROADMAP.md)
- **Record blocks:** use `--signer kiro-review` on `--approve-last`

### Crush / Charm (DeepSeek V4 — Tier A shell + MCP)

- **Before architecture edits:** read matching digest per [`suggested-application-of-builder-material.md`](../builder-reference/notes/suggested-application-of-builder-material.md)
- **Crush token note:** four tier-A digests already in `global_context_paths` (~13.5k tokens standing). **DDIA promotion to Crush is explicitly deferred** — do not add to `crush.json` without Ryan decision
- **Shell ritual unchanged:** `convmem doctor` → `brief` → `unresolved` before repo survey
- **Do not** run `convmem record` unless Ryan requests a record block

### Codex (shell monitor)

- **Alien-workspace soaks:** unchanged — see [`VERIFICATION-MATRIX.md`](VERIFICATION-MATRIX.md)
- **Builder-reference verify** is separate from `doctor`: `bash scripts/verify-builder-reference.sh`
- **Change feed review:** still **2026-07-07** per LATEST — do not accelerate
- **If implementing plan todos:** follow enriched execution order in canonical plan; smallest diff

---

## Key decisions already made (do not relitigate)

| Decision | Source |
|----------|--------|
| DDIA not thin — changelog only, not expansion | Claude Cloud review |
| arch-patterns-python is expansion target (989 words) | Claude Cloud review |
| DDIA → Cursor/Kiro/Codex pointers now; Crush defer | Claude Cloud review |
| Restic gate = **unmapped** digest (don't force-fit DDIA) | Claude Cloud review |
| `watch`/`refine` → DDIA + Arch Patterns co-digest | Claude Cloud review |
| Execution paused for ChatGPT literature | Cursor 2026-07-01 |

---

## Search before guessing

```bash
convmem search "builder-reference digest plan"
convmem search "dec_prop_20260701_022733_b844"
```

Ledger anchors: `dec_prop_20260701_122838_13dc`, `dec_prop_20260701_022733_b844`, `dec_prop_20260629_212545_8aae`, `dec_prop_20260623_161428_c311`

---

## Done-writing ping

**Kiro / Crush / Codex:** open [`PLAN-2026-07-01-apply-builder-reference.md`](PLAN-2026-07-01-apply-builder-reference.md) before any builder-reference implementation. **Assess only** until literature gate clears. Reply via `docs/inter-model/KIRO-*` / `CRUSH-*` / `CODEX-*` if you find plan gaps.

**Ryan:** when ChatGPT returns literature, save to `docs/inter-model/CHATGPT-2026-07-01-literature-recommendations.md` and notify Cursor to merge + resume execution.
