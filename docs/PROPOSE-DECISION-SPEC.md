# `convmem propose_decision` — Canonical Spec (v1)

**Status:** Implemented (2026-06-22)  
**Merged from:** Claude + ChatGPT specs, Kiro review simplifications  
**Implementer:** Cursor  

---

## Purpose

`convmem brief` shares ops state. `convmem propose_decision` closes the gap between inter-model `DECISION PROPOSED` prose and signed ledger records — **without writing to Chroma**.

---

## Workflow

```
propose → pending_decisions.jsonl (PENDING)
    → --list / --approve / --reject (Ryan or Kiro)
    → decisions-approved.jsonl (ledger-shaped)
    → convmem add --file decisions-approved.jsonl --upsert  (existing path)
```

---

## CLI

### Propose

```bash
convmem propose_decision \
  --relates-to dec_convmem_no_auto_merge \
  --summary "One sentence choice" \
  --rationale "Why this choice" \
  --author cursor-implementer \
  --alternative "rejected path" \
  --constraint "hard limit" \
  --domain coding.tooling \
  --site "" \
  --confidence 0.8 \
  --id dec_prop_custom  # optional
```

Required: `--relates-to`, `--summary`, `--rationale`, `--author`.

### List

```bash
convmem propose_decision --list          # PENDING only (default)
convmem propose_decision --list --all    # include APPROVED/REJECTED
convmem propose_decision --list --json   # raw records
```

### Approve

```bash
convmem propose_decision --approve dec_prop_20260622_143201_a3f2 \
  --signer ryan \
  --ledger-id dec_my_canonical_id   # optional; default proposal id
```

Signers: `ryan`, `kiro-review` (exact match only). **Agents cannot approve.**

### Reject

```bash
convmem propose_decision --reject dec_prop_... --signer ryan --reason "duplicate of dec_x"
```

`--reason` required.

### Ingest (unchanged)

```bash
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

No `--ingest-approved` wrapper in v1 (Kiro simplification).

---

## Queue format

**Pending:** `~/.local/share/convmem/pending_decisions.jsonl`

```json
{
  "id": "dec_prop_20260622_143201_a3f2",
  "kind": "decision_proposal",
  "status": "PENDING",
  "relates_to": "dec_convmem_no_auto_merge",
  "summary": "...",
  "rationale": "...",
  "alternatives_rejected": [],
  "constraints": [],
  "domain": "coding.tooling",
  "site": "",
  "confidence": 0.8,
  "proposed_by": "cursor-implementer",
  "proposed_at": "2026-06-22T21:00:00Z",
  "source": "cli",
  "signer": null,
  "signed_at": null,
  "rejection_reason": null
}
```

`kind: decision_proposal` is **not** in `LEDGER_KINDS` — queue lines cannot be ingested by mistake.

**Approved:** `~/.local/share/convmem/decisions-approved.jsonl` — same shape as `examples/decision-csp-nginx.jsonl` (`kind: decision`, `status: accepted`, `author_model` = signer).

Queue updates use atomic temp-file + rename (same pattern as `processed.json`).

---

## Kiro v1 simplifications (applied)

- No `--ingest-approved` wrapper
- No `--edit-rationale` on approve
- `--list` default = PENDING only; `--all` for history
- No MCP approve/reject in v1
- `--parse-doc` reserved (exits "not yet implemented")

---

## Inter-model bridge

Agents without shell write `DECISION PROPOSED:` blocks in `docs/inter-model/`. Cursor (or Ryan) transcribes to `convmem propose_decision` flags. Add `Queue id: dec_prop_...` to the doc after transcribing.

---

## Non-goals

- No autonomous Chroma writes on propose/approve
- No agent self-signing
- No notification system
- No queue deduplication

---

## Acceptance (verified by Cursor)

- [x] Propose writes one queue line; no Chroma access
- [x] `--list` PENDING default; `--all` for history
- [x] Signer allow-list enforced on approve/reject
- [x] Approve appends ledger-shaped line to `decisions-approved.jsonl`
- [x] Reject preserves record with reason
- [x] Approved output passes `normalize_ledger_record`
- [x] `--parse-doc` stub reserved
- [x] Tests in `tests/test_propose_decision.py`

---

*Canonical spec — superseded Claude-only and ChatGPT-only drafts.*
