---
status: active
ledger: dec_prop_20260623_215943_5abe
---

# convmem Roadmap — Lauer

North-star: local evidence bus on **this workstation** (Arch Linux, Ollama local). Watch/refine/monitor run as user systemd units here — no separate corpus host. **Operate-and-document** — not foundation-build.

Test count is not pinned in this roadmap (it drifts with every merge). Canonical: `convmem brief --with-tests`, or `python -m unittest discover -s tests -q`.

---

## Closed — do not reopen

| Phase | What shipped |
|-------|----------------|
| P0 | Watch soak PASS (~99 MB RSS); `doctor` v0+v1; F2a store API |
| P1a | `convmem unresolved`; `recency_boost` on search + `ask --evidence`; JSONL upsert sync |
| P1b | Golden eval 10/10 |
| Protocol | Global rollout — [`config/agent-protocol.md`](../config/agent-protocol.md), verification matrix, soak closed |
| Chroma write path | `PersistentClient`-only; `record --approve-last` index regression test — commit `4c82f35` |

Daily ritual: `doctor` → `unresolved` → `ask` / `record --approve-last`.

---

## Pre-live-write gate (Restic)

Before any live Chroma upsert or write-path merge, Restic runs **fail-closed** (snapshot if stale; block on failure):

```bash
convmem record --approve-last          # gate built into CLI
convmem add --file … --upsert          # gate built into CLI
```

Equivalent external wrapper (runs the same gate, then `convmem`):

```bash
~/Projects/convmem/scripts/convmem-live-write.sh record --approve-last
~/Projects/convmem/scripts/convmem-live-write.sh add --file … --upsert
```

The wrapper calls `scripts/restic-ensure-chroma-snapshot.sh` first. **Fail-closed:** any Restic error (binary missing, bad repo, password missing, backup failure) **blocks** the live write — no warn-and-continue.

**Scope boundary (adopted, not accidental):** the gate protects *overwrite / durable-merge* writes — `record --approve-last` / `record --approve <id>` (indexed approval), `add --upsert` (replace-by-id, where a bad merge is unrecoverable) and approval recovery, `propose_decision --recover <id>` (Safe Harbor T2; T4 still owns recovery classification and retry). `convmem index`, plain `convmem add` (no `--upsert`) and `--no-index` approval are **intentionally ungated**: they are append-only or index-free and reindexable (corpus recovery = "restore or reindex"), so a snapshot is not a precondition. Gating every Chroma mutation ("gate everything") was considered and **declined** — this is the standing invariant, not a gap.

**Bound to the operation (Safe Harbor T2):** each gated command resolves its config once under the shared writer lease, then runs the preflight against that operation before Chroma opens or approval state changes. The Restic profile must be **explicit `complete-data-v2`** with an explicit data root — a legacy or v3 profile refuses these writes, so an explicit v2 profile is a rollout prerequisite. The profile's Chroma directory must equal the operation's target, and every affected path (Chroma, write-guard directory, export, approval events/queue/approved rows/locks and schema-gate files) must sit inside the data root; a symlinked export escaping it refuses. Config or profile edits after admission refuse; nested write sessions reuse the admitted config. A behavioral regression test (`tests/test_write_gate_effect.py`) plus `tests/test_safe_harbor_t2.py` assert refusals leave the corpus, approval files and export unchanged.

**Skip variable:** `CONVMEM_SKIP_RESTIC_GATE=1` is **refused** on these paths unless `CONVMEM_RESTIC_GATE_EXCEPTION` names an explicit isolated context (`isolated-test` or `isolated-lab`) and every affected path and the config are canonically outside the production data/config roots of both `$HOME` and the account's passwd home (`isolated-lab` also requires the lab data root). cwd, `convmem-lab` names, confirm variables and `CONVMEM_ROOT` do not qualify. This is a cooperative safeguard, not protection against a same-user actor.

**Freshness (B-E4.1):** the newest correct-path `convmem-data-v2` snapshot must be on the **same local calendar day** as one evaluation instant captured per resolution, and not later than it. Not last git commit, not last approved write.

| Condition | Action |
|-----------|--------|
| **Current** | Proceed |
| **Old or missing** | `restic backup` of the data root, then exact re-resolution at a fresh instant, then proceed |
| **Future-dated** (`future_snapshot_time`) | **Block** — exit 25; no backup, no dry-run pass, no fallback to an older snapshot |
| **Local day changed during admission** | One fresh resolution; still crossed → block, exit 25 (`day_boundary_crossed`) |
| **Any Restic failure** | **Block** — nonzero exit (config/profile 20, target/path 24, freshness 25, Restic codes propagate), no live write |

The check-only probe (`--check-only`, doctor reachability) reports eligibility **unchecked** and never licenses a write. Local health fails a future snapshot (25); offsite health warns (25); offsite copy refuses before copying (25).

Setup: `bash ~/Projects/convmem/scripts/setup-restic-chroma.sh` (once). Manual secret: `~/.config/convmem/restic.password` — see `config/restic.env.example`.

Corpus rollback: [`RECOVER.md`](RECOVER.md).

---

## Session workflow

```text
convmem doctor
convmem unresolved
convmem ask "…"          # source ~/.config/convmem/env.local
```

MCP (read-only): `brief`, `search_fast`, `ask`, `related`, `stats`.

---

## Optional gates (manual — do not build unless triggered)

| Gate | Trigger | Action | Builder lens |
|------|---------|--------|--------------|
| **P1c** | ≥3 `synthesis_failed` / week on `ask` | Phase 1 streaming synthesis **shipped** (partial on timeout) — [`PLAN-2026-06-29-streaming-synthesis.md`](inter-model/PLAN-2026-06-29-streaming-synthesis.md) | ouster, manning |
| **P2** | New FAIL in [`VERIFICATION-MATRIX.md`](inter-model/VERIFICATION-MATRIX.md) | MCP `unresolved` / `open`; agent-habit fixes only | hard-parts, zeller |
| **P2-stream** | After P1c + client pre-flight | Streamable HTTP + `ask_stream` — same plan doc | ouster, manning |

**rerank:** Manual spot-check only — eyeball `config.toml` vs `brief`; no automation.

---

## P3 — later

OpenClaw, dedupe approval UI, hybrid retrieval (`manning`), `export --redact`, domain backfill in brief, rerank/CUDA if latency matters.

Cross-project digest: [`scripts/cross-project-digest.sh`](../scripts/cross-project-digest.sh), pilot [`CROSS-PROJECT-DIGEST-PILOT.md`](inter-model/CROSS-PROJECT-DIGEST-PILOT.md).

**Pinned (2026-07-07):** Engineering-team design, two layers — **shipped** — Layer 1 role charters ([`role-charters.md`](role-charters.md), retrieval-triggered via `.cursor/rules/role-charter.mdc`) + Layer 2 standing-checks register ([`standing-checks-register.json`](standing-checks-register.json), evaluated by `doctor` `standing_register`, advisory warn). Live triggers and closed rows are tracked in the register JSON itself (single source of truth — not enumerated here, where the list would drift). First merge-order evaluation caught a live crush.json order violation (pre-fix insert-at-front deploy logic); remediated same day. Mapping: [`role-mapping.md`](role-mapping.md). **Design complete (2026-07-07):** register end state **12 open / 2 standing / 2 closed** (the two Tech-Writer manual-by-design rows relabeled `trigger: charter` / `status: standing` — traceable, never doctor-due); the pre-live-write gate boundary (Option 1) is documented above and behaviorally regression-tested (`tests/test_write_gate_effect.py`). See the completion addendum in [`engineering-team-retro-2026-07-07.md`](engineering-team-retro-2026-07-07.md).

**Pinned (2026-07-06):** Codex `rollout-*.jsonl` adapter — **shipped** — full assistant+user sessions under `~/.codex/sessions` (not `history.jsonl` prompts-only). Unified handoff: `scripts/sync-willowyhollow-handoff.sh`.

**Pinned (2026-07-05):** `convmem index --file --supersede` — **shipped** — tombstones prior units (`superseded` / `superseded_by`) instead of hard delete. Default remains replace-delete. Use for evolving findings docs. Sync script: `scripts/sync-willowyhollow-findings-index.sh`.

---

## Hygiene (pinned)

| Item | Rule |
|------|------|
| Pending inventory | **>20 pending** → index pass (daily ritual check) |
| Unsigned decision session files | Delete from `examples/` when never approved into ledger |

---

## Open (out of planner scope)

| Item | Lane |
|------|------|
| staging2 CSP (unresolved obs) | Client |
| `convmem ask` in shell | `source env.local` for DeepSeek key |
| Model-quality **remediation** (eval harness ships detection/classification only) | convmem — retry temp/prompt at ingest, extractive non-generative fallback, or flag-and-continue + human `--supersede`; pick per triage. Detector = `scripts/eval-*.py` + `doctor` summarization canary |

---

## Avoid

- Monolithic Chroma+protocol commits
- `_debug_log` in repo
- P2 MCP without matrix FAIL or habit evidence
- Hybrid retrieval without eval regression
- convmem infra work masquerading as client deploy

---

Supersedes [`ROADMAP-DRAFT.md`](ROADMAP-DRAFT.md) (2026-06-30). Session contract: [`AGENTS.md`](../AGENTS.md) → [`config/agent-protocol.md`](../config/agent-protocol.md).
