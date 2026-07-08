# convmem documentation index

Flat navigation for active docs. **No subfolder taxonomy** — historical material lives under [`archive/`](archive/).

**Option A (2026-06-30):** synthesis / cross-project digest lane → [`../SYNTHESIS-STATUS.md`](../SYNTHESIS-STATUS.md) at repo root. Protocol handoff → [`inter-model/LATEST.md`](inter-model/LATEST.md) only (runtime SPOF for `brief`, MCP, agent rules).

---

## Start here

| Doc | Role |
|-----|------|
| [`STATUS.md`](STATUS.md) | Where to read for live ops |
| [`ROADMAP.md`](ROADMAP.md) | Product roadmap |
| [`RECOVER.md`](RECOVER.md) | Disaster recovery |
| [`inter-model/LATEST.md`](inter-model/LATEST.md) | Single cross-model handoff pointer |
| [`../SYNTHESIS-STATUS.md`](../SYNTHESIS-STATUS.md) | Background synthesis / digest status (Phase 0–3) |
| [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md) | **Agent cheat sheet** — prod vs lab, digest, references, smoke |
| [`WILLOWYHOLLOW-WEBDEV-GUIDE.md`](WILLOWYHOLLOW-WEBDEV-GUIDE.md) | **Willowy Hollow** — convmem for web dev (beginner) |
| [`WILLOWYHOLLOW-TLDR.md`](WILLOWYHOLLOW-TLDR.md) | **Willowy Hollow** — one-page cheat sheet |
| [`WILLOWYHOLLOW-SESSION-LOOP.md`](WILLOWYHOLLOW-SESSION-LOOP.md) | **Willowy Hollow** — full session loop (Steps 1–10) |
| [`CODEX-DEEPSEEK-VERIFY.md`](CODEX-DEEPSEEK-VERIFY.md) | **Verification checklist** for Codex (shell) and DeepSeek (MCP) |

---

## Site reference (Willowy Hollow)

Curated promotion-gate slices for client-site work (PHP parity, URL identity, backup-before-write).
Deploy: `bash scripts/deploy-site-reference.sh` · Verify: `bash scripts/verify-site-reference.sh` · Surfaces: `bash scripts/validate-site-reference-surfaces.sh` · Smoke: `bash scripts/smoke-site-reference-surfaces.sh`

| Doc | Role |
|-----|------|
| [`site-reference/README.md`](site-reference/README.md) | Index — when to read which slice |
| [`site-reference/NOTES.md`](site-reference/NOTES.md) | Pre-promote gate sequence + registry |

---

## Builder reference

Curated tier-A book digests for agent surfaces (Ousterhout, Manning IR, Zeller).
Deploy: `bash scripts/deploy-builder-reference.sh` · Verify: `bash scripts/verify-builder-reference.sh` · Surfaces: `bash scripts/validate-builder-reference-surfaces.sh`

| Doc | Role |
|-----|------|
| [`builder-reference/README.md`](builder-reference/README.md) | Index — when to read which digest |
| [`builder-reference/SOURCES.md`](builder-reference/SOURCES.md) | PDF paths + page ranges (local) |
| [`inter-model/PLAN-2026-07-01-apply-builder-reference.md`](inter-model/PLAN-2026-07-01-apply-builder-reference.md) | **Active plan** — apply digests to past/future work (paused for literature review) |
| [`inter-model/HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md`](inter-model/HANDOFF-KIRO-CRUSH-CODEX-2026-07-01-builder-reference.md) | Kiro / Crush / Codex — read before builder-reference implementation |

---

## Operations

| Doc | Role |
|-----|------|
| [`SYSTEMD-DEPLOY.md`](SYSTEMD-DEPLOY.md) | Always-on user systemd deploy |
| [`AGENT-ROLES.md`](AGENT-ROLES.md) | Model routing |
| [`inter-model/SESSION-CLOSE-RECORD.md`](inter-model/SESSION-CLOSE-RECORD.md) | `convmem record` handoff format |
| [`inter-model/CONTINUE-VERIFY.md`](inter-model/CONTINUE-VERIFY.md) | Continue IDE verify lane |
| [`inter-model/SOAK-REPORT-2026-06-25.md`](inter-model/SOAK-REPORT-2026-06-25.md) | Surface soak matrix |
| [`inter-model/VERIFICATION-MATRIX.md`](inter-model/VERIFICATION-MATRIX.md) | Graded verify matrix |

---

## Plans and milestones

| Doc | Role |
|-----|------|
| [`inter-model/PLAN-2026-07-01-apply-builder-reference.md`](inter-model/PLAN-2026-07-01-apply-builder-reference.md) | **Active** — builder-reference application plan (enriched; execution paused) |
| [`MILESTONE-F.md`](MILESTONE-F.md) | Milestone F scope |
| [`ROADMAP-DRAFT.md`](ROADMAP-DRAFT.md) | Draft roadmap (archival banner; live link from ROADMAP) |
| [`inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`](inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md) | Filed plans + synthesis gates |
| [`inter-model/CROSS-PROJECT-DIGEST-PILOT.md`](inter-model/CROSS-PROJECT-DIGEST-PILOT.md) | Manual digest pilot log |
| [`CROSS-PROJECT-DIGEST-ATTEMPTS.md`](CROSS-PROJECT-DIGEST-ATTEMPTS.md) | `attempts.jsonl` schema, precheck, prod smoke |

---

## Inter-model inbox

Active coordination: [`inter-model/`](inter-model/) — read [`inter-model/README.md`](inter-model/README.md) for conventions.

**Archived soak (2026-06-22):** [`archive/inter-model/2026-06-22/`](archive/inter-model/2026-06-22/)  
**Archived org planning (2026-06-30):** [`archive/inter-model/2026-06-30-org-planning/`](archive/inter-model/2026-06-30-org-planning/) (after Commit 5)

---

## Logs

Session logs: [`logs/`](logs/) — dated operational notes (not inter-model handoffs).

---

## Archive

| Path | Contents |
|------|----------|
| [`archive/inter-model/`](archive/inter-model/) | Retired inter-model coordination |
| [`archive/handoffs/`](archive/handoffs/) | Historical handoff milestones |
| [`archive/minipc-deploy/`](archive/minipc-deploy/) | Retired miniPC deploy kit (do not run) |
| [`archive/residue/`](archive/residue/) | Residue index + non–June-22 one-offs |

Truth for ops state: **`convmem brief`** + ledger — not folder mtime.
