# Recover convmem + MCP after data loss

Ryan backs up **`~/Projects/convmem`** (source, docs, examples). This guide assumes that
backup exists. It separates what the **hook hard-protects**, what is **easy to recreate
from the repo**, and what needs a **separate data backup**.

---

## Three tiers

| Tier | Location | If wiped | Agent hook |
|------|----------|----------|------------|
| **1 — Corpus** | `~/.local/share/convmem/` | Restore from your **data backup** or full reindex (slow) | **Blocks** shell delete/move/truncate |
| **2 — Runtime config** | `~/.config/convmem/` | Copy examples below; re-enter API key | **Blocks** shell delete/move/truncate |
| **3 — Wiring + source** | `~/Projects/convmem`, `~/.cursor/mcp.json`, `~/.kiro/settings/mcp.json`, `~/.kiro/settings/permissions.yaml`, `~/.config/crush/crush.json`, `~/.copilot/mcp-config.json`, `~/.copilot/agents/`, Continue YAML | Restore project backup or git; copy MCP/permissions examples | **Not blocked** — edits encouraged |

**Not in the Git repo:** Tier 1 (`chroma/`, `processed.json`, `knowledge_units.jsonl`,
`decisions-approved.jsonl`, `attempts.jsonl` (optional), etc.). Include `~/.local/share/convmem/` in backups if you want
fast recovery without reindexing.

---

## Restic snapshot gate (live Chroma writes)

**Policy:** fail-closed. If Restic cannot verify or create a current snapshot, **do not**
run live indexed approval, `add --upsert` or approval recovery (`record --recover` /
`propose_decision --recover`) on the
production corpus. Since Safe Harbor T2 the CLI gate is bound to the operation: it needs an
explicit `complete-data-v2` profile whose Chroma directory matches the write target and
whose data root contains every affected path; `CONVMEM_SKIP_RESTIC_GATE=1` is refused
outside an explicit, canonically isolated test/lab context (ROADMAP "Pre-live-write gate").

**Freshness (pinned):** the newest correct-path snapshot must be from the **current local
calendar day** and not later than the evaluation instant. A future-dated snapshot fails with
exit 25 and reason `future_snapshot_time` — no backup, no fallback to an older snapshot.
Investigate the clock or snapshot rather than retrying.

### One-time setup

```bash
# Install restic (pick one)
sudo pacman -S restic
# or: conda install -n convmem -c conda-forge restic && ln -sf ~/miniforge3/envs/convmem/bin/restic ~/.local/bin/restic

bash ~/Projects/convmem/scripts/setup-restic-chroma.sh
```

**Manual secret (Ryan):** `~/.config/convmem/restic.password` — created by setup if missing.
Back up this file offline; without it you cannot restore from the Restic repo.

**Config:** `~/.config/convmem/restic.env` (from `config/restic.env.example`).

### Live writes

Indexed `convmem record --approve-last` / `--approve <id>`, `convmem add --file … --upsert`, and `convmem record --recover <id>` / `convmem propose_decision --recover <id>` run the bound Restic gate **fail-closed** before opening Chroma or changing approval state. T4 also binds direct `recover_approval()` calls; this does not claim every direct Python approval helper or arbitrary writer is gated.

**Scope retained:** the July 7 `index` and plain `add` (no `--upsert`) exemptions and existing `--no-index` approval behavior are unchanged. They do not gain per-invocation recovery qualification. This is a retained owner boundary, not proof that all indexing is append-only or harmless: replacement indexing can supersede/delete existing units. `forget` and refine gain no new gate or exemption here. Any broader change needs Ryan’s decision and synchronized policy docs.

Optional wrapper (same gate, then `convmem`):

```bash
~/Projects/convmem/scripts/convmem-live-write.sh record --approve-last
~/Projects/convmem/scripts/convmem-live-write.sh add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

### What gate diagnostics establish

The configured profile/tag/path and local-day checks establish snapshot eligibility, not demonstrated recovery or a consistent live-file capture method. Under complete-data-v2 the tag is `convmem-data-v2`; `convmem-chroma` is legacy and cannot substitute for that profile. Use the existing explicit BackupContext resolver; do not select `--latest` or silently fall back across profiles.

The ensure `--check-only` probe deliberately leaves eligibility **unchecked** and can return PASS after caught resolver errors. It is a reachability/toolchain probe, not permission to write. The live gate, local health, offsite health and copy retain their distinct reviewed outcomes (ROADMAP). Doctor aggregates those observations; a healthy report does not qualify a recovery artifact. Running these diagnostics on production is an operational action requiring the applicable grant.

### Complete-data restore classifications (v2)

When validating a **complete-data-v2** snapshot (tag `convmem-data-v2`), restore
preflight classifies every durable path through a closed matrix. Validators
**never repair**. Outcome precedence:

`BLOCKED > REPAIRABLE > ADVISORY > VALID`

| Classification | Meaning | Live replacement? |
|---|---|---|
| **VALID** | Structurally sound for the path's authority class | Eligible only after Ryan live-replacement grant |
| **ADVISORY** | Residue / evidence / inactive Shadow — review, not a hard stop | Still requires Ryan live-replacement grant |
| **REPAIRABLE** | Derived drift with a **named repair source** (e.g. Chroma → export, Pending event log → projection, Source rescan → processed/inventory) | **Not** replacement-ready until repaired or accepted |
| **BLOCKED** / `BLOCKED_UNCLASSIFIED_STATE` / `BLOCKED_SNAPSHOT_SCOPE_LEAK` | Canonical/control corruption, unknown top-level state, or scratch (`worktrees/**`, `restore-drill/**`) leaked into the snapshot | Do **not** replace live data |

Capture file `.convmem-backup-evidence.json` is **evidence only** — not authority
and never a repair source. Mid-capture skew becomes a visible classification.

**Named repair sources (examples):**

- Derived `knowledge_units.jsonl` ↔ Chroma (only when the compare is deterministic)
- Pending projection ↔ Pending event log (lifecycle reducer)
- `processed.json` / `inventory.jsonl` ↔ Source rescan / reimport

### Authoritative-first replacement + rollback (Ryan grant only)

Live replacement of `~/.local/share/convmem/` is **out of band** from code merge.
It requires a **separate Ryan live-replacement authorization** (distinct from
configuring `complete-data-v2`, taking the first live v2 snapshot, or enabling
timers).

Authoritative-first order when Ryan authorizes replacement:

1. Stop writers (watch/refine) deliberately.
2. Keep a rollback copy of the current live root (or confirm a prior good snapshot).
3. Replace from a preflight result that is not `BLOCKED` / not merely repairable
   unless Ryan explicitly accepts repairable derived drift.
4. Verify with `convmem doctor` and restore-preflight reports (JSON authoritative;
   Markdown derived).
5. On failure, roll back to the retained live copy before restarting writers.

Do **not** treat capture evidence as the thing to restore from.

### Complete-data-v2 vs complete-data-v3 (coexistence)

Two closed restore contracts coexist. They are **not** interchangeable and there
is **no** automatic v2→v3 migration, upgrade, or reinterpretation.

| Profile | Restic tag | Provenance authority | Missing registry |
|---|---|---|---|
| **complete-data-v2** (legacy) | `convmem-data-v2` | Not required | Normal v2 preflight; `provenance/` is not part of the v2 contract |
| **complete-data-v3** (provenance-aware) | `convmem-data-v3` | Required immutable registry under `provenance/` | **BLOCKED** / quarantined — authority cannot be inferred from JSONL, Chroma, or backup evidence |

**v3 requirements:** a valid v3 candidate must include `provenance/` with an
immutable generation `P_g`, manifest commitment `M_g`, and tree commitment
`T_g`, plus required history/graph/profile bindings. Preflight runs **two
independent validators**:

1. **Registry manifest/graph/history validation** — durable provenance authority
2. **`.convmem-backup-evidence.json` validation** — capture evidence only

A valid sidecar **cannot** repair or satisfy an invalid or missing registry.
Missing or partial provenance authority fails closed (blocked/quarantined).

Exact Restic snapshot/tree selection is preserved as evidence
`(restic_snapshot_id, restic_root_tree_id, T_g, P_g, M_g)`; preflight rejects
“most complete” or automatic snapshot election heuristics.

**Recovery Authority T3 (scratch-only bulk recovery):** use
`scripts/complete_data_restore_preflight.py --bulk-scratch --grant-id <id>`
with an isolated `--target` directory and explicit `--snapshot-id` (full 64-char
hex). This prepares a v3 recovery **candidate** in scratch only; it does not
replace live authority and is not a live-replacement grant.

Live replacement, provenance-authority activation, projection rebuild, and
serving publication remain separately Ryan-gated — preflight classifies only.

### Restore chroma from Restic

```bash
source ~/.config/convmem/restic.env
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
restic restore latest --tag convmem-chroma --target /tmp/convmem-chroma-restore
# Inspect, then stop watch/refine and replace ~/.local/share/convmem/chroma/ deliberately
```

---

## Fast path (project backup only)

Use when Tier 1 corpus still exists or you accept reindexing later.

```bash
# 1. Restore source tree (your normal backup restore)
cd ~/Projects
# … restore convmem directory …

# 2. Runtime config
mkdir -p ~/.config/convmem
cp ~/Projects/convmem/config.example.toml ~/.config/convmem/config.toml
cp ~/Projects/convmem/config/env.local.shell.example ~/.config/convmem/env.local
cp ~/Projects/convmem/config/env.systemd.example ~/.config/convmem/env.systemd
# Edit env.local + env.systemd: set DEEPSEEK_API_KEY

# 3. Shell alias
source ~/.config/convmem/env.local

# 4. Cursor MCP
cp ~/Projects/convmem/config/cursor-mcp.json.example ~/.cursor/mcp.json
# Edit API key in mcp.json or rely on env.local

# 5. Continue MCP
mkdir -p ~/.continue/mcpServers
cp ~/Projects/convmem/config/continue-mcp.json.example ~/.continue/mcpServers/convmem.json
# Add mcpServers block from config/continue-mcp-servers.yaml.example to ~/.continue/config.yaml
# Tier-A agent models: merge config/continue-models-tier-a.example.yaml under models:

# 5b. Copilot CLI MCP (if installed)
mkdir -p ~/.copilot/agents
cp ~/Projects/convmem/config/copilot-mcp-config.json.example ~/.copilot/mcp-config.json
# Agent protocol also deploys ~/.copilot/agents/convmem.md

# 6. Systemd (optional always-on)
cp ~/Projects/convmem/systemd/convmem-watch.service.example ~/.config/systemd/user/convmem-watch.service
cp ~/Projects/convmem/systemd/convmem-refine.service.example ~/.config/systemd/user/convmem-refine.service
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch.service convmem-refine.service

# 7. Deploy agent protocol surfaces (Cursor .mdc, Codex AGENTS.md, Kiro steering + MCP + permissions.yaml, Crush, Copilot)
bash ~/Projects/convmem/scripts/deploy-agent-protocol.sh
# Kiro: enable MCP in Settings after deploy (see script manual steps)

# 8. Verify
convmem stats
~/Projects/convmem/scripts/verify-continue.sh
# Restart Cursor / Continue / Kiro / Copilot after MCP config changes
# After mcp_server.py updates: bash scripts/restart-convmem-mcp.sh (kills stale stdio subprocesses)
```

---

## Corpus lost (Tier 1)

If `~/.local/share/convmem/chroma/` is gone:

1. Complete **Fast path** above.
2. Restore `~/.local/share/convmem/` from a **data backup** if you have one, **or**
3. Rebuild corpus (hours, GPU/LLM cost):

```bash
mkdir -p ~/.local/share/convmem
convmem inventory          # refresh inventory.jsonl
convmem index              # full index from inventory
convmem refine --once      # optional cleanup pass
convmem stats
```

Approved decisions in `decisions-approved.jsonl` can be re-ingested with
`convmem add` if you still have that file from backup.

### Index drift (doctor `index_drift` check)

`convmem doctor` compares Chroma `knowledge_units` count to
`knowledge_units.jsonl` (config `index.units_export`). Compares Chroma count to
**unique unit ids** in the export (append-only JSONL may have duplicate lines).
WARN below ~30% indexed; FAIL below ~15% or empty Chroma with non-empty export.

**One-command rebuild** (Ryan terminal — clears incremental index state):

```bash
rm ~/.local/share/convmem/processed.json
convmem index
convmem doctor   # index_drift should pass
```

If Chroma itself is corrupt, restore from Restic (above) before reindexing.

---

## What agents may change freely

- Any file under `~/Projects/convmem/` (code, tests, docs)
- `mcp_server.py`, `watch.py`, `brief.py`, etc.
- `~/.cursor/mcp.json`, `~/.kiro/settings/mcp.json`, `~/.copilot/mcp-config.json`, and Continue `mcpServers` (MCP wiring)
- `~/.config/convmem/config.toml` (paths, models)

## What needs Ryan (hook blocks shell destruction)

- `rm` / `mv` / `truncate` on `~/.local/share/convmem/` or `~/.config/convmem/`
- Bulk wipe of Chroma or `processed.json` (use deliberate terminal, not agent)

---

## Related

- `config.example.toml` — index paths and models
- `scripts/verify-continue.sh` — CLI MCP smoke test
- `docs/SYSTEMD-DEPLOY.md` — systemd + env details
- `docs/archive/minipc-deploy/` — archived miniPC deploy (historical; do not run)
- `docs/inter-model/CONTINUE-VERIFY.md` — Continue UI checklist


## Safe Harbor incident handling and rollout

**Status:** T1–T5 / V1–V6 are accepted and merged through
`c6f07241ccf1a71d9d874fee963a37b04091b3ce`. [VERIFY closeout](plans/VERIFY-safe-harbor.md#t5-hosted-ci-owner-exception-and-squash-mapping)
records the resolved correction, hosted CI, owner exception and identical-tree squash.
These instructions describe the implemented contract, not live authority.
[The rollout/rollback draft](plans/ROLLOUT-safe-harbor.md) records the subsequent
read-only preflight, subsequent focused interpreter/legacy evidence, and remaining
recovery/initialization prerequisites. Its readiness section is the current pointer.

### Stop, inspect and preserve

1. An automatic segment restore ends the initiating mutation and leaves an incident, even when structural validation and census pass. Ryan accepted the availability/operator cost: every restore needs a current owner disposition before release. Do not reinterpret “restored” as successful ingestion or enable an automatic clear/retry loop.
2. The sole guarded-write authority is `QUARANTINE.json` beside the **canonical** Chroma directory in `<chroma_dir>.write-guard/`. Current publications use `convmem.safe_harbor.incident_set`, version 2. Recognized version 1/legacy state, unknown/malformed/unreadable state and persisted-empty incident sets are not implicit release. A competing lexical alias guard location refuses; do not delete either location or create a fresh empty authority to bypass it.
3. Preserve the marker, `preservation/` originals/manifests, pinned `snapshots/<segment>/<generation>/SNAPSHOT.json` and segment files, `events.jsonl`, plus relevant approval/export authority. Local segment saves are HNSW repair sources, not complete-data or independent disaster-recovery backups. No automatic cleanup is part of Safe Harbor. `audit.json` is latest-observation telemetry; a later pass/skipped/error cannot erase an unresolved incident.
4. Within a separately authorized diagnostic scope, `scripts/chroma_guard.py status --chroma-dir <canonical-path>` reports incident IDs, finding revisions and the current authority digest. `validate` checks structure; `census` detects missing IDs. Zero missing IDs does not establish fresh vectors/content. These script paths open no Chroma client and use read-only SQLite; generic ConvMem/Chroma reads can still write bookkeeping. `audit` also writes telemetry/events and may publish quarantine under the lock; it is not a physically read-only command.
5. **Containment unavailable** or a release-removal durability error means a marker file’s visible presence/absence is insufficient. Stop the affected operation, retain evidence and request Ryan’s bounded process-level containment/investigation. Do not claim a durable stop or durable release. The native guard does not stop incidental read-client writes, older clients, arbitrary same-user operations or other publishers.

### Bounded repair and validated release

The existing `reconcile` command can mutate segments and snapshot state; it is not a health probe. With existing authority, only the guard’s incident-bound resume is available: `--incident-id <current-id> --authority-digest <current-digest>` names a previously bound repair and pinned source. It does not authorize a general repair or invent a source for an unsupported/legacy incident. Originals must have a durable write-once completion manifest before replacement. Failed space/IO/hash/source checks retain containment; stop and route unavailable evidence to a separate repair decision.

Ordinary `clear-quarantine` refuses. Its validated path requires **both** `--disposition <owner-reference>` and `--authority-digest <current-digest>`, for the explicitly selected canonical store. The owner reference records authorization, not authentication against a same-user actor. Ryan’s disposition must bind the actual findings authorized; additional findings or a new occurrence invalidate an older digest and require a fresh disposition.

Under the native lock, release checks **every** unresolved incident: supported finding/occurrence, completed preservation and repair, immutable originals, pinned generation identities/digests, supported backend/schema, structure/census and the strict watermark oracle. Metadata must match the saved vector watermark with no newer relevant queued work. Census-only success cannot release stale same-ID vectors. Missing/legacy evidence, unknown semantics or pending/newer work keep containment, even where another recovery strategy could work. There is no force clear or automatic re-embedding fallback.

Only after all checks pass does release durably append the disposition to existing `events.jsonl`, then remove the marker and durably publish its removal. A crash/error can leave a recorded disposition with containment still present, or uncertain marker removal. Do not infer rollback or replay a disposition over changed findings; inspect current authority/history and obtain the bounded follow-up decision. Evidence and pinned generations are not automatically deleted after release. A confirmed release permits guarded admission; resuming services or retrying a corpus mutation still requires its own applicable authorization.

### Uncertain approval completion

`record --recover <proposal-id>` and `propose_decision --recover <proposal-id>` share the admitted recovery path with direct `recover_approval()`. Recovery resolves the protected target/config first, reads authoritative intent/events under the governed lock, then performs fresh state checks and effects in the native critical section. It refuses unavailable/tombstoned/conflicting state rather than treating it as absence.

An error reported as **completion outcome unknown** may occur after Chroma, export or APPROVED publication took effect. Keep all three; do not truncate the event tail, manually append approval, re-upsert blindly or assume APPROVAL_STARTED remains. A separately authorized retry reloads/reduces authoritative events, checks present Chroma and export effects, completes permitted missing effects/durability, and cannot duplicate a terminal approval. A malformed/truncated log or contradictory effects stops for review. A terminal event by itself is not proof that export and native validation completed. This is recovery of the existing approved intent, not permission to resurrect a tombstone or change intent.

### Prepared rollout checklist — not executed

- **Candidate and interpreter:** merged candidate `c6f07241ccf1a71d9d874fee963a37b04091b3ce` (runtime is unchanged from T4 `fdc8da7`); local integrated evidence uses `/home/lauer/miniforge3/bin/python` 3.13.12 and hosted evidence Python 3.12.15, with Chroma 1.5.9. These are test identities. Choose and review the actual deployment interpreter/native binding; the strict release backend allowlist currently supports Chroma 1.5.9 only. A newer main must receive its own delta assessment.
- **Recovery material:** Ryan must set the lost-work interval and name a qualified artifact, completion time, scope, exclusions and retrieval instructions. Confirm key access independently of the workstation and actual physical custody. Preserve the reported pre-incident Rescuezilla image. A fresh offline image can support planned maintenance; neither its frequency nor a mounted USB proves usable/offsite recovery. The added `/run/media/lauer/ext-ex4-1T-NVMe/` is unallocated capacity until separately authorized; T5 made no drive inspection or write. The subsequent read-only preflight is recorded in the rollout draft; no drive write or allocation was made.
- **Processes and code roots:** under a later operational scope, inventory exact CLI/watch/MCP/reconcile/audit/backup-unit roots, interpreters and running versions. Name how every old writer or clear command is stopped/restarted/held; lazy-import caches require process replacement. Preserve currently stopped services as stopped. Include unguarded and incidental writers; the flock is not a global freeze. T5 performed no live process census. The later preflight observed 29 MCP servers and a manual index process; refresh that census and coordinate owners before a separately granted maintenance window.
- **Existing state and coverage:** inspect actual canonical and lexical guard locations, markers, supported schemas, incident sources and backup profile coverage before first adoption. Record an explicit preservation/adoption procedure for any live legacy state. There is no migration grant here and no permission to rely on a first ordinary write as migration. Ensure explicit complete-data-v2 covers every actual affected path; Rescuezilla qualification alone does not bypass an unhealthy Restic gate on named consumers.
- **Activation and rollback:** a separate reviewed grant must name the exact commit, interpreter, targets, permitted commands, service transitions and stop conditions. Inspect the actual intervening runtime-to-candidate delta; this handoff is not permission for an unreviewed main catch-up. A rollback to old code that can overwrite/ignore/clear incidents is blocked until compatibility is proven with containment retained. Unexpected schema/target/clock/IO or validation results stop the affected action for investigation.
- **Acceptance after a permitted rollout:** record observed code/process identities, guard state and granted diagnostics; do not infer deployment health from CI. Any restore drill, backup creation, corpus operation, incident repair/release or watch start must remain within its separately named scope. Complete-data Backup v2’s Hybrid consistency audit and Recovery Authority T4/V4k remain open under their existing owners.

**TL;DR:** [Arc Safe Harbor] Merged code retains incidents and original evidence, binds approval recovery to its protected target and refuses uncertain release. Operational qualification, deployment and live repair remain separate owner decisions.

<!-- ref: plans/ROLLOUT-safe-harbor.md — observed rollout prerequisites and conditional rollback -->
<!-- src: plans/VERIFY-safe-harbor.md — merged Safe Harbor acceptance -->
