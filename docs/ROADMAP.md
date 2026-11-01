---
status: active
ledger: dec_prop_20260623_215943_5abe
---

# convmem Roadmap — Lauer

North-star (Ryan, 2026-11-01): dependable professional memory for **staff-only
client history and follow-up preparation at a massage salon**, and for software
development. Accuracy and evidence preservation take priority over minimizing
model cost. Model, retrieval, and context-budget choices must earn their place
through measured quality; a cheaper configuration is acceptable only when it
meets the same release criteria.

The current deployment remains a local evidence system on one workstation
(Arch Linux, local Ollama, user systemd services). This direction does not claim
that the current software is ready for client records or shared business use.

## Professional readiness — next priorities

The first salon workflow is staff reviewing a client's recorded history and
preparing a follow-up for human approval. Software workflows include recovering
decisions, failed attempts, exact commands, and subsequent verification. These
need separate evidence sets and evaluation results. Client communication remains
human-reviewed; generating diagnoses, treatment eligibility, or medical advice
is outside this first workflow.

The sequence below is a delivery proposal, not a completed capability or a
replacement for existing execution approvals. Build on existing retrieval traces,
provenance, evaluation, and recovery machinery rather than creating parallel
frameworks.

| Order | Deliverable | Acceptance evidence before advancing |
| --- | --- | --- |
| 1 | Preserve evidence through source expansion, then ingestion and answer context. Fix expansion's reuse of clipped ingestion text first. Next, replace lossy message clipping with coverage-preserving passages and add deliberate source loading to `ask`. | Regression cases retain decisive facts in the middle/end of long messages. Every omitted span is visible as truncation or incomplete evidence. Source mismatch, missing source, and incomplete legacy hash coverage remain distinguishable. Existing provenance and ingest compatibility tests pass. |
| 2 | Establish separate frozen accuracy suites for salon staff work and software work, starting with synthetic records. | Independently phrased questions have human-reviewed answers, supporting source spans, dates/client or project identity, and expected abstentions. Measure source coverage, retrieval of **all** required evidence, delivered-context coverage, supported answers, contradictions, and abstentions separately. Keep a held-out set; report counts and uncertainty alongside percentages. |
| 3 | Enforce business/client authorization and provider-data policy before any real salon intake. | Denied clients and software/personal records cannot enter salon retrieval, source expansion, model prompts, caches, exports, or logs. Missing identity refuses access. Tests cover similarly named clients, multi-turn carryover, and attempts to broaden scope. Verify permitted model/provider routes and redacted operational logs. Existing domain/site filters are retrieval conveniences, not a proven access-control boundary. |
| 4 | Improve reasoning where the measured failures justify it. | Compare source-backed answers, multi-step retrieval, query decomposition, and hierarchical aggregation individually against the frozen baseline. Require accuracy gains or equivalent quality with an operational benefit; report latency and token/currency cost. Preserve exact quotes, dates, conflicts, and superseded records rather than silently resolving them by model preference. |
| 5 | Run a supervised staff pilot after operational readiness. | Named staff roles, access audit, record correction, retention/deletion, provider policy, and tested restore/rollback procedures exist. A restore drill meets an agreed maximum data-loss window and recovery time. Staff can inspect sources, correct records, and report failures. Review every pilot output before client communication; stop on a critical error. |

**Proposed initial pilot-entry targets — to freeze before evaluation, not results:**
at least 100 independently authored held-out questions per workflow; at least
95% fully correct and complete answers on answerable questions; at least 95%
correct abstention on insufficient-evidence questions; and no critical failure
in the release suite. Critical failures include cross-client disclosure,
wrong-client attribution, fabricated client-specific facts or commitments, and
presenting a superseded or contradicted client-care record as current without
flagging the conflict. For software work, include wrong-project attribution,
invented verification results, and presenting a failed or superseded procedure
as a verified fix. Include explicit negative cases for each class. Count
abstention on an answerable question as a failure, not a way to raise accuracy.
Report each workflow and failure class separately; these finite-sample targets
are a starting pilot gate, not a guarantee of production reliability. Confirm
targets with the salon operator before using real records.

**Current evidence boundary:** the eight-query retrieval fixture and three-case
synthesis baseline are engineering checks, not business-readiness evidence.
See [research limitations](RESEARCH.md#7-current-evidence-and-its-limits).
The [JudgeBench calibration work](plans/STATUS-judgebench.md) and
[naturalistic product-value study](plans/STATUS-naturalistic-product-value.md)
retain their existing scopes and execution status. This roadmap does not claim
that their pending experiments ran, select a judge, authorize private-data
transfer, or activate a live pilot. Real client records must remain outside
public fixtures and repository history.

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

**Scope boundary (adopted, not accidental):** the Restic gate protects indexed `record --approve-last` / `record --approve <id>`, `add --upsert`, and approval recovery through `record --recover <id>` / `propose_decision --recover <id>`. T4’s direct `recover_approval()` entry also binds the same preflight before recovery effects. These are named consumers of the existing gate, not a parallel protection mechanism. The July 7 `index` / plain `add` exemptions and existing `--no-index` approval behavior remain: these calls do not gain a Restic precondition. Retaining that scope does **not** endorse a blanket append-only/reindexable premise: replacement indexing can supersede or delete existing units. `forget` and refine gain no new gate or exemption here. Broader scope changes require Ryan’s decision and synchronized ROADMAP/RECOVER/role-mapping updates. Guarded writes still benefit from validated local segment saves; those HNSW repair sources do not replace an independently usable complete-data backup or establish an acceptable loss window.

**Merged recovery behavior (Safe Harbor T4):** fresh tombstone/authority checks and the native lock cover decision, mutation, export and completion publication. An uncertain completion may already contain APPROVED; retry reloads authoritative state rather than assuming rollback. Every automatic segment restore retains an incident and aborts the initiating write, even if validation passes. [Incident handling and rollout](RECOVER.md#safe-harbor-incident-handling-and-rollout) documents the approved operator cost and conservative release limits. Merged source does not mean it has been deployed.

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
