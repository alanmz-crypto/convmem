# Lab errors, near-misses, and guardrails (2026-07-06)

## convmem-lab health (automated)

**Last smoke:** `bash lab/scripts/smoke-synthesis.sh` — **PASS** (2026-07-06)

Includes: synthesis mechanics, lab-reference verify, cross-lane write guard, pytest subset.

**Verdict:** Lab **did not corrupt prod Chroma** when guards used. Lab fixtures are disposable by design.

---

## Confirmed mistakes (protocol / ops — not lab data corruption)

| Issue | Impact | Mitigation shipped |
|-------|--------|-------------------|
| Track A skipped when only log indexed | Next model lost chat context | Track A/B table + phrasebook in `agent-protocol.md` |
| Kiro offered `record` at task end | False "session close" signal | Kiro-specific: handoff ≠ record |
| Codex `history.jsonl` indexed instead of full chat | Prompts only, no assistant turns | `codex_rollout_jsonl` adapter + handoff script |
| Per-finding `record` impulse | Ledger noise | Ryan: umbrella record at end |
| "Index what you wrote" phrasing | Models skipped Crush/Codex chat | Ryan phrasebook |
| Uncommitted prod work (`--supersede`, handoff scripts) | Git drift, not corpus corruption | Commit pending; ops not memory error |

---

## Near-misses (not errors if protocol followed)

| Item | Status |
|------|--------|
| `--propose` draft `dec_prop_20260705_152603_2c96` rejected | **Correct** — pipeline worked; draft wrong on merit |
| Lab `LATEST.md` ≠ prod `LATEST.md` | **Intentional** — lab disposable |
| Index drift ~37% JSONL ids in Chroma | **Coverage gap**, not wrong data — search works for indexed paths |
| `write_lane` FAIL when cwd=lab + prod config | **Guard working** — use `convmem-lab.sh` or `CONVMEM_CONFIRM_PROD=1` deliberately |
| Restic gate stale on doctor | **Backup ops** — blocks live write until snapshot fresh |
| Linker Phase 2 held on agent-habit gate | **Deferred by design** — not a lab failure |

---

## Lab spikes — graduation status (not errors)

| Spike | Lab exit | Prod graduation |
|-------|----------|-----------------|
| S1 LATEST pointer | Done | **Not graduated** |
| S2 defer queue | Done | **Not graduated** |
| S3 trend report | Script exists | Open |
| S4 handoff-warn | Script exists | Open |
| Synthesis S1–S5 | Done | Partial port to prod (`load_attempts`, digest) |

**Not an error:** spikes validated in lab first; prod promotion requires Ryan `record`.

---

## Prod/lab isolation rules (must hold in experiment)

| Rule | Enforced by |
|------|-------------|
| No lab MCP in Cursor/Crush/Codex/Kiro | `LAB.md` anti-leak |
| Lab data under `~/.local/share/convmem-lab` | `convmem-lab.sh` wrapper |
| Prod index from lab cwd blocked | `runtime_guard.py` / `write_lane` doctor check |
| Bulk inter-model index needs `CONVMEM_CONFIRM_PROD=1` | `index-inter-model-docs.sh` |

---

## What Claude should check

1. Are any **confirmed mistakes** above still unaddressed in protocol?
2. Does **DeepSeek-in-Crush** bug hunting require a **fourth reviewer** before fixes?
3. Is **37% index coverage** a blocker for orchestration experiment?
4. Should **Crush verification records** (many `dec_prop_*` from Ryan) be collapsed before next phase?
