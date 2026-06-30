# Residue archive + trash prune (2026-06-30)

**Author:** composer-2.5-fast (Cursor)  
**Chains to:** `23057a370bfdbf926fd2c34521ddc81626f02236a337a4cc54c4e52b42583bf1`, `d10535a281fd9aecc797d37d9520759aa250aa1d79a2e8460cbf421f2ac4c36b`  
**Trigger:** Ryan — archive dated coordination residue, delete obvious local clutter, and leave the live docs clean.

---

## Summary

Archived the iffy one-off coordination docs into `docs/archive/residue/`, deleted local bundle clutter and dead helper scripts, and removed a stale tarball pointer from `docs/inter-model/LATEST.md`. The goal was to preserve historical context while clearing dead-end residue from the active tree.

---

## Archived

| Item | Action |
|------|--------|
| `README-FOR-CHATGPT.md` | Moved to `docs/archive/residue/` |
| `CONVERSATION_COMPACT.md` | Moved to `docs/archive/residue/` |
| `docs/KIRO-RESPONSE-2026-06-22.md` | Moved to `docs/archive/residue/` |
| `docs/KIRO-TO-ALL-MODELS.md` | Moved to `docs/archive/residue/` |
| `docs/KIRO-STATUS-2026-06-22.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/ALL-MODELS-2026-06-22-joint-verification.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/ALL-MODELS-2026-06-22-next-moves-vote.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/CODEX-2026-06-22-claude-decision-next-path.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/CODEX-2026-06-22-multi-project-workspace.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/CURSOR-2026-06-22-chatgpt-decision-pack.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/DEEPSEEK-2026-06-22-wrap-up.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/HANDOFF-CURSOR-AUTO-COMPOSER-2026-06-25-soak.md` | Moved to `docs/archive/residue/` |
| `docs/inter-model/KIRO-2026-06-22-workspace-response.md` | Moved to `docs/archive/residue/` |
| `docs/archive/residue/README.md` | Added archive index for the moved files |

---

## Deleted

| Item | Reason |
|------|--------|
| `handoff-tar/` expanded unpack trees | Local bundle clutter with no live repo role |
| root `handoff-*.tar.gz` files | Local artifacts only |
| `review-bundles/sonnet-brief-mcp-2026-06-23/` | One-off review bundle, no live references |
| `review-bundles/sonnet-brief-mcp-2026-06-23.tar.gz` | Local artifact only |
| `scripts/ssh-askpass.sh` | Dead helper, superseded by archived miniPC kit |

---

## Live pointer fix

| File | Fix |
|------|-----|
| `docs/inter-model/LATEST.md` | Removed stale tarball reference after bundle deletion |
| `.gitignore` | Added ignore rules for `handoff-tar/*/`, `handoff-*.tar.gz`, and `review-bundles/*/` |

---

## Verification

- No live references remain to the deleted bundle paths outside the archive and cleanup logs.
- The archive folder preserves the dated coordination notes for future context.

---

## Record block

Ryan runs:

```bash
convmem record \
  --relates-to 23057a370bfdbf926fd2c34521ddc81626f02236a337a4cc54c4e52b42583bf1 \
  --summary "convmem repo: archived dated coordination residue and deleted dead local bundles" \
  --rationale "Archived one-off coordination notes into docs/archive/residue/ instead of leaving them in active paths; deleted handoff-tar unpack trees, root handoff tarballs, review-bundles/sonnet-brief-mcp-2026-06-23/, and the dead ssh-askpass helper; removed a stale tarball pointer from docs/inter-model/LATEST.md and widened .gitignore so the same clutter does not come back. Preserve intentional history, remove only dead-end residue. Log: docs/logs/2026-06-30-residue-archive-trash-prune.md." \
  --author composer-2.5-fast

convmem record --approve-last
```
