# ChatGPT assignment: `convmem propose_decision` spec

**To:** ChatGPT (cloud — paste or upload this tar)  
**From:** Cursor + Kiro soak plan  
**Date:** 2026-06-22  
**Lane:** Design only — **no code**. Cursor implements after 24h watch soak.

---

## Your deliverable

Write **`PROPOSE-DECISION-SPEC.md`** (markdown) that Cursor can implement in one session. Include:

1. **Purpose** — one paragraph: why this exists after `convmem brief`
2. **Workflow diagram** — Observation → Proposal → Review → Signed decision → ingest
3. **CLI UX** — `convmem propose_decision` flags, prompts, examples
4. **Pending queue format** — where proposals live on disk before sign-off
5. **Sign-off gate** — who can approve (Ryan human confirm; Kiro reviewer); what changes on approve
6. **Ingest path** — how approved proposals become ledger records (`convmem add --file` today)
7. **Inter-model bridge** — how `DECISION PROPOSED` blocks in `docs/inter-model/` relate to the queue
8. **MCP v2 (optional section)** — read-only propose → queue file only; **never** auto-write Chroma
9. **Explicit non-goals** — no agent messaging, no autonomous Chroma writes, no merge without human
10. **Acceptance criteria** — checklist for Kiro sign-off before Cursor builds

Target length: **2–4 pages**. Be specific enough that Cursor does not need a follow-up interview.

---

## Context you must respect

### Brief is shipped

`convmem brief` exists. All models start from the same ops snapshot. ChatGPT gets paste-only access via Ryan.

### Decision schema already exists

See included `ledger.py` — `Decision` dataclass fields:

- `id`, `summary`, `relates_to` (required for decisions)
- `rationale`, `alternatives_rejected`, `constraints` (Kiro extension — **must appear in Chroma document text**)
- `author_model`, `domain`, `site`, `confidence`, `timestamp`, `status`

Ingest today:

```bash
convmem add --file examples/decisions-session-2026-06-18.jsonl --upsert
```

Rationale is appended to the embedded document in `observe.py`:

```text
{summary} {keywords} Rationale: {rationale}
```

### Signed decision examples

Included JSONL files show real Kiro-signed decisions (single-writer Chroma, no auto-merge, workspace standard, CSP via nginx, etc.).

### Interim pattern (in use now)

Models write blocks like:

```text
DECISION PROPOSED:
Choice: ...
Risk: ...
Rejected: ...
Status: PENDING HUMAN CONFIRM
```

Ryan or Kiro confirms → Cursor ingests or files inter-model note. **Your spec should formalize this**, not replace brief/inter-model.

### Agent roles

| Agent | Role |
|-------|------|
| Kiro | Reviewer/signer — decisions need human/Kiro gate |
| Cursor | Implementer — builds CLI after your spec |
| ChatGPT | Strategy/design — you |
| Codex | Shell monitor during soak |

### ChatGPT's prior position (included excerpt)

From archived orchestration note: approve brief first; **do not** build autonomous MCP writes before shared understanding; future workflow is Observation → Proposal → Review → Decision with humans/Kiro signing.

### What Kiro asked for

Soak task #3: **`propose_decision` spec** — design-only, 15 min, unblocks post-soak build.

### What brief already shows

Included `brief-snapshot.md`: **Recent Decisions** section lists ingested ledger ids + rationale clips; **pending** files under `examples/decisions-*.jsonl` if not yet in Chroma.

---

## Design constraints (non-negotiable)

1. **Single Chroma writer** — proposals go to a **queue file**, not Chroma
2. **Human/Kiro sign-off** before `convmem add` ingests a decision
3. **Separate facts from interpretation** — observations can be tool-ingested; decisions are signed
4. **Soak-safe** — your output is markdown only; no machine commands
5. **Minimal v1** — prefer one CLI + one queue file over MCP + HTTP + UI

---

## Suggested v1 shape (starting point — improve or replace)

```bash
# Propose (writes pending queue, does NOT touch Chroma)
convmem propose_decision \
  --relates-to obs_staging2_willowyhollow_com_006 \
  --summary "..." \
  --rationale "..." \
  --author chatgpt-orchestration

# List pending
convmem propose_decision --list

# Ryan/Kiro approve → emits JSONL line ready for ingest
convmem propose_decision --approve dec_prop_20260622_001 --signer ryan

# Cursor ingests (existing command)
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

You may redesign this entirely if you justify why.

---

## Return format

Reply to Ryan with **`PROPOSE-DECISION-SPEC.md`** contents. Ryan will save to:

`~/Projects/convmem/docs/PROPOSE-DECISION-SPEC.md`

and notify Cursor via `docs/inter-model/CHATGPT-*-propose-decision-spec.md`.

---

## Files in this tar

| File | Why |
|------|-----|
| `README-START-HERE.md` | This assignment |
| `ledger.py` | Decision schema + normalization |
| `observe.py` | Ingest + rationale-in-document |
| `examples/*.jsonl` | Real decision records |
| `docs/AGENT-ROLES.md` | Routing |
| `docs/inter-model/KIRO-2026-06-22-soak-work-order.md` | Your task (#3) |
| `docs/inter-model/KIRO-CURSOR-BEST-PRACTICES-2026-06-22.md` | Coordination rules |
| `brief-snapshot.md` | Live corpus snapshot (2026-06-22) |
| `excerpt-chatgpt-orchestration.md` | Your prior position on decisions |

---

*Upload this tar to ChatGPT or paste README + spec ask. Do not invent corpus state — use brief-snapshot.md.*
