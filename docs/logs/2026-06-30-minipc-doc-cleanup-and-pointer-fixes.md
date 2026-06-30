# miniPC doc cleanup + live pointer fixes (2026-06-30)

**Author:** composer-2.5-fast (Cursor)  
**Chains to:** `dec_convmem_dev_machine_canonical`, `dec_prop_20260630_140725_39d2`  
**Trigger:** Ryan — remove abandoned miniPC deploy plan from active docs; preserve intentional history; fix stale/broken live pointers.

---

## Problem

Active docs still described a two-host miniPC deploy topology (canonical host vs dev machine, remote deploy, corpus rsync). First pass only renamed terminology. Historical ledger copies and archive handoffs were also edited, then partially reverted. A follow-up audit found broken `LATEST.md` links, stale `propose_decision` workflow text, and duplicate/unreferenced pack examples.

---

## Done — active ops (single workstation)

| Change | Detail |
|--------|--------|
| **Removed from live paths** | `docs/MINIPC-DEPLOY.md`, `scripts/deploy-minipc.sh`, `scripts/remote-deploy-minipc.sh` |
| **Current deploy** | `docs/SYSTEMD-DEPLOY.md`, `scripts/deploy-always-on.sh` |
| **North-star** | `README.md`, `docs/ROADMAP.md`, `docs/MILESTONE-F.md` — one workstation, user systemd units |
| **Archived miniPC kit** | `docs/archive/minipc-deploy/` — restored `MINIPC-DEPLOY.md`, both deploy scripts, `ssh-askpass.sh` with do-not-run README |
| **Code** | `doctor.py` / `convmem.py` docstrings only (no behavior change) |

---

## Done — history preserved

| Item | Action |
|------|--------|
| `CONVERSATION_COMPACT.md`, archive handoffs, inter-model handoffs, `BUILT-PLANS` embedded plan | Restored miniPC wording from git where edited |
| `docs/chatgpt-pack/examples/decisions-session-2026-06-18.jsonl` | Left matching signed Chroma corpus (not rewritten) |
| `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md`, `docs/ROADMAP-DRAFT.md` | Archival banners — body kept as frozen record; explicit do-not-execute labels |
| `docs/KIRO-STATUS-2026-06-22.md` | Archival banner |

---

## Done — live pointer fixes (reassessment)

| File | Fix |
|------|-----|
| `LATEST.md` (root) | `docs/inter-model/` links; P1c → `docs/ROADMAP.md`; synthesis vs protocol lane note |
| `docs/inter-model/README.md` | `convmem record` + `--approve-last` (not `propose_decision`) |
| `docs/inter-model/LATEST.md` | Refreshed date; corpus snapshot; defer live counts to `brief` |
| `docs/CHATGPT-PROPOSE-DECISION-BRIEF.md` | Superseded banner; fixed example JSONL path |
| `docs/chatgpt-pack/examples/` | Deleted duplicate `decision.jsonl`, `decision-csp-nginx.jsonl` (root `examples/` kept) |

---

## Not done (deferred)

- Bulk archive of June-22 `docs/inter-model/` chatter
- `handoff-tar/` expanded trees and root `handoff-*.tar.gz` local clutter
- Delete `docs/chatgpt-pack/examples/decisions-session-2026-06-18.jsonl` (still referenced by pack README)
- Corpus re-record to update `dec_convmem_*` rationale text in Chroma (ledger still mentions miniPC by design)

---

## Verification

- `convmem doctor` PASS
- 163 tests PASS
- No tracked references to deleted `deploy-minipc` / `MINIPC-DEPLOY` paths

---

## Record block

Ryan runs:

```bash
convmem record \
  --relates-to dec_convmem_dev_machine_canonical \
  --summary "convmem repo: retired miniPC deploy from active docs; archived kit; fixed LATEST and workflow pointers" \
  --rationale "Abandoned separate always-on host plan: active ops now SYSTEMD-DEPLOY + deploy-always-on on one workstation. Restored deleted miniPC deploy artifacts to docs/archive/minipc-deploy/ (do not run). Reverted miniPC edits in intentional history (handoffs, BUILT-PLANS excerpt, session JSONL left matching corpus). Reassessment fixes: root LATEST broken links + ROADMAP pointer; inter-model README record workflow; refreshed inter-model/LATEST counts; archival labels on ROADMAP-DRAFT and GLOBAL-CONVMEM-PROTOCOL-PLANNER; removed duplicate chatgpt-pack decision examples. Log: docs/logs/2026-06-30-minipc-doc-cleanup-and-pointer-fixes.md. Open: handoff-tar clutter, bulk inter-model archive, corpus still has miniPC in signed dec_convmem_* text." \
  --author composer-2.5-fast

convmem record --approve-last
```
