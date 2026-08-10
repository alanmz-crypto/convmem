# C5 Execute Handoff — Shadow Phase 0 Activation Transaction

**To:** Codex (Cursor implementation lane)
**From:** Crush (DeepSeek V4-Pro, independent review lane)
**Date:** 2026-07-29
**Role:** This is an informational handoff. Codex/Cursor implements C5. Crush verified C1–C4 and produced the C5 decision packet. Ryan approved all four decisions.

## What shipped (C1–C4 on main)

| Slice | PR | SHA | What |
|---|---|---|---|
| C1 | #126 | `9404e0a` | Strict validation/filesystem contract |
| C2 | #128 | `33dc228` | Secure ledger creation, bounded append, complete timing |
| C3 | #129 | `0aa6409` | Writer gate, shared lease, 14-site migration, C1 inject |
| C4 | #130 | `2ac7790` | Doctor/inventory truth reporting via C1 validator |

Current main tip: `2ac7790`

## C5 scope

Implement the activation/rollback state machine — merge-disabled, Shadow stays off.

**Allowed files:**
- `shadow_activation.py` (new) — state machine, journal, transitions, quiescence, commit, crash recovery
- `config.py` — `atomic_shadow_config_update` (TOML table replacement only, same-device atomic rename)
- New nonce store module — one-shot authorization token consumption (JSONL, mode 0600)
- `convmem.py` — thin `shadow-activate` and `shadow-rollback` CLI adapters (default to refusal without authorization input)
- `config.example.toml` — disabled defaults
- `tests/test_shadow_activation.py` (new) — transition table, token, quiescence, crash, rollback, first-event
- `PHASE0-SHADOW-CONTRACT.md`, `SHADOW-WRITER-CENSUS.json` — updated at C5 SHA

**Prohibited:** live state, automatic service control without separate approval, Chroma semantics, backup settings, later phases, enabling Shadow.

## Ryan-approved decisions

| # | Decision | Resolution |
|---|---|---|
| D3 | First-event policy | `T_first_event_seconds = 300s`; timeout → rollback; traffic absence → rollback; no synthetic fill |
| D5 | Service suspension census | Confirmed; regenerate census at C5 implementation SHA; `/proc` + open-FD + attestation scan; quiesce timeout 30s |
| D6 | Config-edit contract | Byte-preserving `[shadow_ledger]` only; TOML parse + semantic-diff + preimage hash; same-device atomic `os.replace`; ext4/xfs/btrfs/tmpfs only; NFS/CIFS/9p → abort |
| D7 | One-shot authorization token | JSON, mode 0600; `request_hash` self-consistency; nonce store (JSONL, mode 0600); validate pre-gate + under-gate; consume nonce before config commit; expiry 3600s; no interactive confirmation while gate held |

## Key design constraints (do not reopen)

- No human/network wait while exclusive gate is held
- Config-last is the commit point
- Rollback never undoes Chroma writes
- All precommit crashes recover as disabled/uncommitted
- Token validated before gate acquisition; nonce consumed before config commit
- Crash after nonce consumption but before config commit → `prepared_not_committed`

## Activation state machine

```
disabled → preparing → quiesced → baseline_captured → artifacts_validated
→ committed → first_event_observed → verified
```

Full machine and transition table in plan §4 (lines 247–370).

## Required refusal codes (C5 additions)

- `authorization_missing`, `authorization_expired`, `authorization_mismatch`, `authorization_reused`
- `legacy_writer_process`, `writer_quiesce_timeout`, `census_stale`, `census_missing`
- `config_filesystem_unsupported`, `config_cross_device`, `config_changed`
- `first_event_missing`, `first_event_mismatch`, `first_event_timeout`

## Tests needed

- Token: absence, expiry, reuse, mismatch, self-consistency, clock skew
- State machine: every transition, invalid transitions, crash at each fsync/rename point
- Quiescence: census match, legacy PID refusal, `/proc` Chroma FD scan, timeout + retry
- Config-edit: enable, disable, semantic diff drift, cross-device refusal, unsupported mount
- Rollback: committed→disabled, first-event timeout, ledger/manifest retained read-only
- Crash recovery: dead holder, prepared_not_committed cleanup, nonce-consumed retry

## Reference docs

- `/home/lauer/.local/share/convmem/worktrees/plan-2026-07-28-shadow-phase0-activation-corrective/docs/plans/EXECUTION-shadow-phase0-activation-corrective.md` — plan §4, §6, §10, §11, §12/C5, §14
- `docs/plans/SHADOW-WRITER-CENSUS.json` — regenerate at C5 SHA
- `docs/plans/PHASE0-SHADOW-CONTRACT.md` — update validation API notes

## Completion evidence

Branch + tip SHA; git log origin/main..HEAD; push status; changed-file list; focused + full tests; transition table coverage; token fault matrix; quiescence `/proc` proof; config-edit atomicity proof; rollback proof; git diff --check; Shadow disabled; no live state changes.

C5 READY FOR INDEPENDENT VERIFICATION — or — C5 HOLD with exact blocker.
