# 2026-07-01 — Builder-reference plan + cross-model handoffs

## Summary

Cursor session produced an enriched plan to apply `docs/builder-reference/` to past convmem work and future roadmap gates. External review lanes opened for Claude Cloud (plan enrichment — **merged**) and ChatGPT (literature recommendations — **in flight**). Local agents (Kiro, Crush, Codex) wired via LATEST + unified handoff.

## Artifacts

| Artifact | Path |
|----------|------|
| Canonical plan | `docs/inter-model/PLAN-2026-07-01-apply-builder-reference.md` |
| Local-agent handoff | `docs/inter-model/HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md` |
| Claude handoff | `docs/inter-model/HANDOFF-CLAUDE-CLOUD-2026-07-01-builder-reference.md` |
| ChatGPT handoff | `docs/inter-model/HANDOFF-CHATGPT-2026-07-01-builder-reference-literature.md` |
| Claude tar | `handoff-builder-reference-2026-07-01.tar.gz` |
| ChatGPT tar | `handoff-chatgpt-literature-2026-07-01.tar.gz` |

## Gate

Plan execution todos **paused** until `CHATGPT-2026-07-01-literature-recommendations.md` lands and Ryan accepts/rejects.

## Claude corrections merged

- DDIA 2,055 words — changelog not expansion
- arch-patterns-python 989 words — expansion target
- Reconcile verify-script thresholds (new step 2)
- DDIA promote Cursor/Kiro/Codex; Crush defer (~20% token increase)

## Next

Ryan uploads ChatGPT tar → literature recommendations → Cursor resumes plan steps 1–7.

## Execution (2026-07-01)

Plan todos 1–6 **shipped**: README tiers, verify thresholds, BUILT-PLANS/ROADMAP lenses, DDIA changelog, arch-patterns 1510w, DDIA tier-B deploy. `deploy-builder-reference.sh` + `verify` PASS; `validate-surfaces` WARN (aspirational 2500+ on 3 digests).
