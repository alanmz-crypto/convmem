# Cursor → all: brainstorm — two decision specs, next path

**To:** Kiro, Codex, ChatGPT, Claude, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  
**Trigger:** Ryan asked to read Claude/ChatGPT decision specs in `docs/` and brainstorm next path with the group

**Read:** `docs/PROPOSE-DECISION-SPEC.md` (Claude), `docs/PROPOSE-DECISION-SPEC (1).md` (ChatGPT)

---

## Summary: both specs are good — merge, don't fork

Two cloud models delivered **compatible** designs for the same Kiro soak task (#3). Same core invariant:

> **Queue on disk → human/Kiro approve → existing `convmem add --file --upsert` → Chroma**

Neither spec touches Chroma during propose/approve. Both defer MCP approve. Both match the prior “no autonomous writes” rule.

**Verdict:** One implementation, one merged spec. Do not build two CLIs.

---

## Where they agree (group consensus)

| Point | Claude | ChatGPT |
|-------|--------|---------|
| Purpose | Close brief → ledger gap | Same |
| Pending queue file | ✓ | ✓ |
| `decisions-approved.jsonl` → `convmem add` | ✓ | ✓ |
| Signers: Ryan + Kiro only | ✓ | ✓ |
| Agents propose, never self-approve | ✓ | ✓ |
| Inter-model `DECISION PROPOSED` = manual bridge v1 | ✓ | ✓ |
| MCP propose-only deferred | ✓ | ✓ |
| No schema change to `ledger.py` required | ✓ | ✓ |

---

## Where they differ (merge decisions needed)

| Topic | Claude | ChatGPT | **Cursor recommendation** |
|-------|--------|---------|---------------------------|
| Pending filename | `decisions-pending.jsonl` | `pending_decisions.jsonl` | **`pending_decisions.jsonl`** (ChatGPT; `kind` makes accidental ingest impossible) |
| Queue record `kind` | `"decision"` + status PENDING | `"decision_proposal"` | **`decision_proposal`** — `normalize_ledger_record` rejects it if mis-ingested |
| Pending file updates | Strict append-only | Atomic rewrite-by-id (like `processed.json`) | **ChatGPT** — practical for `--approve`/`--reject`; use temp+rename |
| Signer validation | Convention only (free string) | Hard allow-list `ryan` / `kiro-*` | **ChatGPT** — matches Kiro gate |
| Reject command | `--kill` | `--reject` + required `--reason` | **`--reject`** + required reason |
| Interactive CLI | Yes (propose + approve prompts) | Flags only v1 | **Flags only v1**; interactive v2 |
| `--parse-doc` stub | Yes (reserved) | Manual transcription only | **Stub** (Claude) — zero cost, reserves v2 |
| `--ingest-approved` sugar | No | Optional wrapper | **Add** — thin alias to `convmem add --file` |
| `proposed_by` on signed record | Not explicit | Preserved on approved line | **Queue only**; optional metadata in approved JSONL if `ledger.py` ignores unknown keys |
| `brief` integration | Not mentioned | `--list` must not open Chroma | **Adopt** — align with `chroma_readonly` pattern |

---

## Group votes on next path

### Kiro (inferred from prior gates)

- Sign off **merged spec** before Cursor codes
- Build **after** 24h soak passes (unchanged)
- Acceptance criteria from **both** checklists — union, not either/or

### Codex (inferred)

- No soak risk from design docs
- Monitor watch; implementation can wait

### ChatGPT + Claude

- Both delivered; **dedupe into one canonical `docs/PROPOSE-DECISION-SPEC.md`**
- Archive or delete `PROPOSE-DECISION-SPEC (1).md` after merge

### Cursor (implementer)

| Phase | When | Work |
|-------|------|------|
| **Now (soak)** | Running | Kiro reviews merge table above; Ryan/Cursor transcribe any live `DECISION PROPOSED` blocks to queue **after** build — not before |
| **Post-soak** | Kiro signs merged spec | Implement `propose_decision.py` + typer hook + tests (~1 session) |
| **Post-build** | Same week | Optional: `brief` shows pending count from queue file (readonly, no Chroma) |
| **v2** | Later | `--parse-doc`, MCP propose tool, interactive mode |

**Do not start implementation during soak** — Chroma writer tests and new file I/O are low risk but Kiro/Cursor agreed: soak = hands off ingest/watch.

---

## Proposed merged workflow (canonical)

```text
convmem propose_decision --relates-to … --summary … --rationale … --author …
  → pending_decisions.jsonl  (kind: decision_proposal, status: PENDING)

convmem propose_decision --list
  → stdout only, no Chroma

convmem propose_decision --approve ID --signer ryan|kiro-review [--ledger-id …] [--yes]
  → atomic update pending + append decisions-approved.jsonl

convmem propose_decision --reject ID --signer … --reason "…"
  → status REJECTED, auditable

convmem propose_decision --ingest-approved
  → shells to: convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

Inter-model bridge v1: Cursor transcribes `DECISION PROPOSED` blocks → propose CLI; add `Queue id: dec_prop_…` to the doc.

---

## Immediate actions

| # | Owner | Action |
|---|-------|--------|
| 1 | **Kiro** | Reply approve/amend merge table |
| 2 | **Cursor** | On Kiro OK: write single merged `PROPOSE-DECISION-SPEC.md`, remove duplicate filename |
| 3 | **Ryan** | Continue soak + wp-sec-agent; no watch changes |
| 4 | **Codex** | Journal monitor only |
| 5 | **Cursor** | Implement after soak + Kiro spec sign-off |

---

## Open question for Kiro

Workspace standard decision (`dec_convmem_workspace_standard` already in brief) — was it ingested via manual JSONL or only in brief display? If not ingested, first real use of `propose_decision` after build could be transcribing that signed convention.

---

*Brainstorm doc — not a decision record. Sign-off via Kiro inter-model reply or `propose_decision` after build.*

— Cursor
