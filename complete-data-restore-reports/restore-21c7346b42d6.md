# Complete-data restore preflight report

- status: **BLOCKED**
- started: 2026-07-27T21:47:21Z
- finished: 2026-07-27T21:47:23Z
- exit_code: 31
- restic_version: restic 0.19.0 compiled with go1.26.4 on linux/amd64
- snapshot.id: `21c7346b42d6e2ded51e78665dcacd12de902e2b08dab6b1542e5a50bfd9e67e`
- snapshot.tree: `3719e5d8e42418bccfd944816d62b185e71f1a2099a3ce3f70fc37f42207ea1f`
- snapshot.original: `None`
- snapshot.tags: `['convmem-chroma', 'convmem-data-v2']`
- snapshot.paths: `['/tmp/convmem-restic-t1-wlxb1nk4/data-root']`
- snapshot.repository: `/tmp/convmem-restic-t1-wlxb1nk4/local-repo`
- detail: classifications=34

## Classifications

- `chroma` — BLOCKED (tier1_authoritative): Chroma validation failed: chroma.sqlite3 missing
- `decisions-approved.jsonl` — BLOCKED (canonical_decisions): missing
- `pending_decision_events.jsonl` — ADVISORY (canonical_control): file missing (empty lifecycle)
- `pending_decisions.jsonl` — VALID (compatibility_projection): absent (normal when no projection)
- `knowledge_units.jsonl` — REPAIRABLE (derived_export): missing — regeneratable from Chroma
- `processed.json` — REPAIRABLE (mixed_incremental_sidecar): missing — rebuild via source rescan
- `dedupe_queue.jsonl` — VALID (conditional_operational_control): absent
- `link_queue.jsonl` — VALID (conditional_operational_control): absent
- `ingest_duplicate_suppressions.jsonl` — VALID (conditional_operational_control): absent
- `inventory.jsonl` — REPAIRABLE (source_inventory_cache): missing
- `imports` — VALID (import_artifacts): absent
- `authorizations` — VALID (conditional_authorization_control): absent
- `shadow/` — VALID (non_authoritative_phase0): absent/disabled (normal Phase 0 default)
- `shadow_activation.json` — VALID (non_authoritative_phase0): absent
- `shadow_activation_manifest.json` — VALID (non_authoritative_phase0): absent
- `shadow_health.json` — VALID (non_authoritative_phase0): absent
- `hash_schema_deploy.json` — VALID (canonical_when_referenced): absent
- `hash_schema_migration_report.json` — VALID (canonical_when_referenced): absent
- `attempts.jsonl` — VALID (operational_evidence): absent
- `index_failures.jsonl` — VALID (operational_evidence): absent
- `synthesis_failures.jsonl` — VALID (operational_evidence): absent
- `refine_undo` — VALID (operational_evidence): absent
- `refine_stats.json` — VALID (operational_evidence): absent
- `brief.md` — VALID (operational_evidence): absent
- `digests` — VALID (operational_evidence): absent
- `logs` — VALID (operational_evidence): absent
- `eval` — VALID (operational_evidence): absent
- `integrity-check` — VALID (operational_evidence): absent
- `locks` — VALID (ephemeral): absent
- `governed-ledger.lock` — VALID (ephemeral): absent
- `worktrees/` — VALID (forbidden_scratch): absent (required)
- `restore-drill/` — VALID (forbidden_scratch): absent (required)
- `.convmem-backup-evidence.json` — ADVISORY (capture_evidence_non_authority): absent
- `seed.txt` — BLOCKED (unknown): not in restore matrix — must be reviewed before replacement

## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=21c7346b42d6e2ded51e78665dcacd12de902e2b08dab6b1542e5a50bfd9e67e |
| 2 | resolve_and_restore | PASS | restored snapshot 21c7346b42d6e2ded51e78665dcacd12de902e2b08dab6b1542e5a50bfd9e67e → /tmp/convmem-restic-t1-wlxb1nk4/preflight-s |
| 3 | locate_restored_root | PASS | /tmp/convmem-restic-t1-wlxb1nk4/preflight-s/tmp/convmem-restic-t1-wlxb1nk4/data-root |
| 4 | classify:chroma | BLOCKED | Chroma validation failed: chroma.sqlite3 missing |
| 5 | classify:decisions-approved.jsonl | BLOCKED | missing |
| 6 | classify:pending_decision_events.jsonl | ADVISORY | file missing (empty lifecycle) |
| 7 | classify:pending_decisions.jsonl | VALID | absent (normal when no projection) |
| 8 | classify:knowledge_units.jsonl | REPAIRABLE | missing — regeneratable from Chroma |
| 9 | classify:processed.json | REPAIRABLE | missing — rebuild via source rescan |
| 10 | classify:dedupe_queue.jsonl | VALID | absent |
| 11 | classify:link_queue.jsonl | VALID | absent |
| 12 | classify:ingest_duplicate_suppressions.jsonl | VALID | absent |
| 13 | classify:inventory.jsonl | REPAIRABLE | missing |
| 14 | classify:imports | VALID | absent |
| 15 | classify:authorizations | VALID | absent |
| 16 | classify:shadow/ | VALID | absent/disabled (normal Phase 0 default) |
| 17 | classify:shadow_activation.json | VALID | absent |
| 18 | classify:shadow_activation_manifest.json | VALID | absent |
| 19 | classify:shadow_health.json | VALID | absent |
| 20 | classify:hash_schema_deploy.json | VALID | absent |
| 21 | classify:hash_schema_migration_report.json | VALID | absent |
| 22 | classify:attempts.jsonl | VALID | absent |
| 23 | classify:index_failures.jsonl | VALID | absent |
| 24 | classify:synthesis_failures.jsonl | VALID | absent |
| 25 | classify:refine_undo | VALID | absent |
| 26 | classify:refine_stats.json | VALID | absent |
| 27 | classify:brief.md | VALID | absent |
| 28 | classify:digests | VALID | absent |
| 29 | classify:logs | VALID | absent |
| 30 | classify:eval | VALID | absent |
| 31 | classify:integrity-check | VALID | absent |
| 32 | classify:locks | VALID | absent |
| 33 | classify:governed-ledger.lock | VALID | absent |
| 34 | classify:worktrees/ | VALID | absent (required) |
| 35 | classify:restore-drill/ | VALID | absent (required) |
| 36 | classify:.convmem-backup-evidence.json | ADVISORY | absent |
| 37 | classify:seed.txt | BLOCKED | not in restore matrix — must be reviewed before replacement |

