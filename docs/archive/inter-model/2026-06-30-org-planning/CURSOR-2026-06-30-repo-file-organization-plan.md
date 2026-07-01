# Repo file organization plan

**To:** Ryan, Codex, Kiro, ChatGPT, Sonnet — anyone comparing reorganization approaches  
**From:** Cursor (composer-2.5-fast)  
**Date / trigger:** 2026-06-30 — Ryan asked for a whole-repo organization audit; plan drafted for comparison before execution  
**Status:** Plan only — **not executed**

Also stored at: `.cursor/plans/repo_file_organization_cd9dba45.plan.md`

Chains to: `dec_prop_20260630_220459_1e3f` (residue archive), Jun 30 miniPC doc cleanup log

---

## Problem

Three layers are mixed at the repo root:

| Layer | Examples | Scale |
|-------|----------|-------|
| Runtime Python | `convmem.py`, `mcp_server.py`, ~33 library modules | 35 `.py` at root |
| Ops / deploy | `scripts/`, `systemd/`, `config/` | ~25 shell scripts |
| Knowledge / coordination | `docs/inter-model/`, root `LATEST.md`, `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` | 135 tracked inter-model `.md` |

Recent cleanup ([docs/logs/2026-06-30-minipc-doc-cleanup-and-pointer-fixes.md](../logs/2026-06-30-minipc-doc-cleanup-and-pointer-fixes.md)) fixed miniPC deploy pointers. **Still open:** bulk inter-model archive, local clutter (`procedures.jsonl`, `sonnet-mcp-verify-full.tar.gz`), empty `review-bundles/`.

---

## Principles (path dependencies)

1. **Do not move runtime entrypoints** — `convmem.py` and `mcp_server.py` stay at repo root. MCP configs and `scripts/restart-convmem-mcp.sh` use absolute paths to `mcp_server.py`.
2. **Do not flatten→package Python without a dedicated refactor** — flat imports (`from brief import …`); `mcp_server.py` uses `sys.path.insert(0, Path(__file__).parent)`.
3. **Treat `docs/inter-model/` as a runtime anchor** — `brief.py` hardcodes inbox path for staleness, recent titles, MCP `inter_model_pointer`. Moving the inbox requires code + config (Phase 3), not a simple `git mv`.
4. **Archive out of the inbox** — `brief.py` only scans top-level `*.md` in the inbox. Use `docs/archive/inter-model/` (matches existing archive patterns), not subfolders inside the active inbox.
5. **Prefer `CONVMEM_ROOT` / `git rev-parse` in scripts** — most scripts already resolve repo relative; systemd defaults bake in `~/Projects/convmem` until re-deploy.

---

## Phase 0 — Zero-risk cleanup (no code changes)

| Action | From | Disposition |
|--------|------|-------------|
| Delete | `sonnet-mcp-verify-full.tar.gz` | Superseded by live repo |
| Delete empty dir | `review-bundles/` | Gitignore pattern stays for future bundles |
| Relocate or delete | `procedures.jsonl` (320K) | `examples/generated/` or regenerate via `extract_procedures.py` |
| Confirm absent | `handoff-tar/` | Already gone on disk |

**Verify:** `convmem doctor`, `pytest`, grep active docs for dead tarball refs.

---

## Phase 1 — Docs taxonomy (link updates only)

Proposed layout:

```
docs/
  README.md              # NEW — index
  ROADMAP.md, STATUS.md, RECOVER.md, SYSTEMD-DEPLOY.md  # keep
  WORKSPACE-STANDARD.md, AGENT-ROLES.md                  # keep
  specs/                 # PROPOSE-DECISION, CHROMA-ACCESS, KIRO-SESSION-ADAPTER
  milestones/            # MILESTONE-F, F2a/b/c
  guides/                # CRUSH-DEEPSEEK, DEEPSEEK-SESSION-CONTEXT, orchestration note
  archive/plans/         # GLOBAL-CONVMEM-PROTOCOL-PLANNER, ROADMAP-DRAFT
  inter-model/           # UNCHANGED PATH (runtime)
  logs/
```

**Root pointers:**

- `LATEST.md` — **keep at root** (synthesis lane); protocol → `docs/inter-model/LATEST.md`
- `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` — move to `docs/archive/plans/`; 3-line stub at root
- `AGENTS.md` — keep at root

**Link sweep:** README, STATUS, agent-protocol (regenerate), chatgpt-pack if archived.

---

## Phase 2 — Inter-model archive (highest doc ROI)

~80+ June-22 soak files hide active handoffs from `ls -lt docs/inter-model/`.

**Keep in active inbox:**

- Pointers: `README.md`, `LATEST.md`, `SESSION-CLOSE-RECORD.md`
- Living ops: `CONTINUE-VERIFY.md`, `VERIFICATION-MATRIX.md`, `CRUSH-VERIFY.md`, `SOAK-REPORT-2026-06-25.md`
- Plans: `BUILT-PLANS-2026-06-24-to-2026-06-29.md`, `PLAN-2026-06-25-*`, `PLAN-2026-06-29-*`, recent `HANDOFF-*`
- Pilot: `CROSS-PROJECT-DIGEST-PILOT.md`
- Anything after **2026-06-24** or referenced from `LATEST.md` / `BUILT-PLANS`

**Move to `docs/archive/inter-model/2026-06-22/`:**

- Bulk `CURSOR/KIRO/CODEX/DEEPSEEK/ALL-MODELS-2026-06-22-*`
- Superseded gap-analysis duplicates summarized in `BUILT-PLANS`
- Step-by-step soak transcripts

Add `docs/archive/inter-model/README.md`. Update `docs/inter-model/README.md` reading order.

**No `brief.py` change required.**

---

## Phase 3 — Path configurability (optional)

Only if relocating repo or renaming inbox:

- `[paths] inter_model_inbox` in `config.example.toml` + `brief.py` / `config.py`
- Central `repo_root()` helper
- MCP examples via `CONVMEM_ROOT`
- Re-run `scripts/deploy-always-on.sh`

**Not recommended now:** moving `docs/inter-model/` itself.

---

## Phase 4 — Python layout (optional, defer)

**Keep at root:** all modules imported by `convmem.py` / `mcp_server.py`.

**Optional:** group `export_*`, `extract_*`, `inventory.py`, `cross_project_digest.py` into `tools/` or `scripts/py/`. Dedupe stale `examples/export_report_to_observations.py`.

**Do not do without dedicated project:** `src/convmem/` package, `pyproject.toml`.

---

## What stays exactly where it is

| Path | Why |
|------|-----|
| `convmem.py`, `mcp_server.py` | CLI/MCP entrypoints |
| Flat library `*.py` | Import graph |
| `adapters/` | Existing subpackage |
| `config/` | Agent-protocol generation |
| `scripts/`, `systemd/`, `tests/`, `examples/` | Deploy/test conventions |
| `docs/inter-model/` path | `brief.py` runtime inbox |

---

## Execution order

1. Phase 0 (~30 min) — zero regression  
2. Phase 1 (1–2 hr) — link grep + docs README  
3. Phase 2 (1–2 hr) — bulk `git mv` + cross-link updates  
4. Phases 3–4 — only if relocating repo or publishing package  

---

## Verification (each phase)

- `convmem doctor` exits 0
- `pytest` (163 tests)
- `convmem brief --stdout-only` — inter-model staleness sane
- MCP `brief()` — `inter_model_inbox` correct
- Grep active docs for broken links
- `scripts/verify-continue.sh` if protocol docs moved

---

## Out of scope

- Corpus re-record for archived doc paths in Chroma
- Watch-indexing `docs/inter-model/*.md`
- `pyproject.toml` / pip-installable package
- Changing default `~/Projects/convmem` (document `CONVMEM_ROOT` instead)

---

## Comparison hooks (for other plans)

1. **Inter-model aggressiveness** — this plan archives ~80 June-22 files; inbox path unchanged.
2. **Docs taxonomy vs minimal** — Phase 1 is optional if a flat `docs/` + README index suffices.
3. **Code changes** — Phases 0–2 need no Python; Phase 3+ only for relocation or fewer root files.
4. **Builds on Jun 30** — residue archive + miniPC cleanup; does not repeat those moves.

---

## Handoff

**Ryan:** Compare this plan to other model proposals; pick phases to ship.  
**Other models:** Reply here or add a dated note if you disagree on inbox archive cutoffs, docs taxonomy, or Python layout.

If course changes, update `docs/inter-model/LATEST.md`.

**See also:** [CURSOR-2026-06-30-repo-organization-assessment.md](CURSOR-2026-06-30-repo-organization-assessment.md) — merged agreement + risk matrix vs Codex plan.
