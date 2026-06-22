# PROPOSE-DECISION-SPEC.md
**Status:** Design only — no implementation code  
**Author:** Claude (architecture/strategy role)  
**Date:** 2026-06-22  
**Target implementer:** Cursor (after 24h watch soak)  
**Kiro sign-off required before build starts**

---

## Purpose

`convmem brief` gives every agent a shared ops snapshot. `convmem propose_decision` closes the gap between a model writing a `DECISION PROPOSED` block in an inter-model doc and that decision actually entering the signed ledger.

Without this command, the path from proposal to ingest requires Ryan or Kiro to manually construct a JSONL record, save it to disk, and run `convmem add --file`. That friction means proposals accumulate in inter-model docs as unstructured text, rationale decays, and future agents can't query them. `propose_decision` makes the proposal-to-ledger path as low-friction as the confirm step: one command drafts, one command signs, one existing command ingests.

**This command never writes to Chroma.** It manages a pending queue on disk only. The existing `convmem add --file` handles ingest after sign-off, unchanged.

---

## Workflow

```
Agent / human writes proposal
          │
          ▼
convmem propose_decision --relates-to <id> --summary "..." --rationale "..." [flags]
          │
          │  Writes one JSONL line to:
          │  ~/.local/share/convmem/decisions-pending.jsonl
          │  Status: PENDING
          ▼
convmem propose_decision --list
          │  Shows pending proposals with id, summary, author, age
          ▼
Ryan or Kiro reviews (10 seconds — three-line format)
          │
    ┌─────┴─────┐
  APPROVE      KILL
    │            │
    ▼            ▼
--approve      --kill
Moves record   Marks record
to             status: REJECTED
decisions-     (stays in queue
approved.jsonl  for audit, never
                ingested)
    │
    ▼
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
          │
          ▼
  Record enters Chroma as signed decision (existing path, unchanged)
```

---

## CLI UX

### Propose (agent or human)

```bash
convmem propose_decision \
  --relates-to obs_staging2_willowyhollow_com_006 \
  --summary "Add CSP via nginx server block, not plugin layer" \
  --rationale "WPCode snippet caused TBT regressions on staging. nginx config survives plugin updates." \
  --alternatives-rejected "WPCode snippet" "Cloudflare transform rule" \
  --constraints "Must not touch PHP layer" "Staging-only until Kiro verifies" \
  --author kiro-review \
  --domain web_stack.security \
  --site staging2.willowyhollow.com
```

**Required flags:**
- `--relates-to` — ledger ID of the parent observation or decision (validated: must be non-empty string; existence check is optional in v1 to allow proposals before the observation is ingested)
- `--summary` — one sentence, the choice made
- `--rationale` — why this choice; the load-bearing reason
- `--author` — model or human identifier (`kiro-review`, `claude`, `ryan`, etc.)

**Optional flags:**
- `--alternatives-rejected` — repeatable; each value is one rejected path
- `--constraints` — repeatable; hard limits that shaped the choice
- `--domain` — defaults to `coding.tooling` if not provided
- `--site` — site tag (blank for infrastructure decisions)
- `--confidence` — float 0.0–1.0; defaults to 0.8
- `--id` — explicit ledger ID (e.g. `dec_staging2_csp_nginx`); auto-generated if omitted

**Output on success:**
```
Proposed: dec_prop_20260622_143201_a3f2
  Summary: Add CSP via nginx server block, not plugin layer
  Relates-to: obs_staging2_willowyhollow_com_006
  Status: PENDING
  Queue: ~/.local/share/convmem/decisions-pending.jsonl
```

**Interactive mode** (no flags beyond `--relates-to`):
```bash
convmem propose_decision --relates-to obs_staging2_willowyhollow_com_006
```
Prompts for `summary`, `rationale`, `alternatives-rejected` (comma-separated), `constraints` (comma-separated), `author`. Displays the three-line confirm preview before writing.

---

### List pending

```bash
convmem propose_decision --list
```

Output (tabular, Rich or plain):
```
ID                              Summary                                    Author         Age     Status
dec_prop_20260622_143201_a3f2   Add CSP via nginx server block             kiro-review    2h      PENDING
dec_prop_20260622_091044_b7c1   Use upsert not add in ingest path          cursor         8h      PENDING
dec_prop_20260621_174532_d9e0   Exclude Kiro sqlite from watch             claude         1d      PENDING
```

`--list --all` includes REJECTED and APPROVED records for audit.

---

### Approve

```bash
convmem propose_decision --approve dec_prop_20260622_143201_a3f2 --signer ryan
```

- Sets `status: APPROVED`, `signer: ryan`, `approved_at: <ISO timestamp>`
- Appends the final record (with `kind: decision`, `status: accepted`) to `decisions-approved.jsonl`
- Does **not** remove from `decisions-pending.jsonl` (append-only; audit trail)
- Does **not** touch Chroma

Output:
```
Approved: dec_prop_20260622_143201_a3f2
  Signer: ryan
  Written to: ~/.local/share/convmem/decisions-approved.jsonl
  Next step: convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

**Kiro shell shorthand** (sugar for common case):
```bash
convmem propose_decision --approve dec_prop_20260622_143201_a3f2 --signer kiro-review
```
Identical behavior; `--signer` accepts any string.

---

### Kill (reject)

```bash
convmem propose_decision --kill dec_prop_20260622_091044_b7c1 --reason "relates-to ID was wrong"
```

- Sets `status: REJECTED`, `kill_reason: "..."`, `killed_at: <ISO timestamp>` in `decisions-pending.jsonl`
- Record stays in queue (audit); never moves to `decisions-approved.jsonl`
- Never ingested

---

### Ingest approved (existing command, unchanged)

```bash
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

This is the existing path. No changes to `convmem add`. The approved JSONL file is already in valid ledger format (see Queue Format below).

---

## Pending queue format

**File:** `~/.local/share/convmem/decisions-pending.jsonl`  
**Format:** One JSON object per line, append-only. Never truncated, never sorted. Status field tracks lifecycle.

### PENDING record (written by `propose_decision`)

```json
{
  "id": "dec_prop_20260622_143201_a3f2",
  "kind": "decision",
  "status": "PENDING",
  "relates_to": "obs_staging2_willowyhollow_com_006",
  "summary": "Add CSP via nginx server block, not plugin layer",
  "rationale": "WPCode snippet caused TBT regressions on staging. nginx config survives plugin updates.",
  "alternatives_rejected": ["WPCode snippet", "Cloudflare transform rule"],
  "constraints": ["Must not touch PHP layer", "Staging-only until Kiro verifies"],
  "author_model": "kiro-review",
  "domain": "web_stack.security",
  "site": "staging2.willowyhollow.com",
  "confidence": 0.8,
  "proposed_at": "2026-06-22T14:32:01Z",
  "source": "cli"
}
```

`"source"` is `"cli"` for direct proposals, `"inter-model"` for proposals parsed from `DECISION PROPOSED` blocks (see Bridge section).

### APPROVED record (written by `--approve`)

Same fields, plus:
```json
{
  "status": "APPROVED",
  "signer": "ryan",
  "approved_at": "2026-06-22T16:45:00Z"
}
```

### decisions-approved.jsonl

Written by `--approve`. Contains only the ledger-ready subset of fields — stripped of `proposed_at`, `source`, `signer`, `approved_at` — so `convmem add --file` can pass it directly to `normalize_ledger_record` without changes.

```json
{
  "id": "dec_staging2_csp_nginx",
  "kind": "decision",
  "status": "accepted",
  "relates_to": "obs_staging2_willowyhollow_com_006",
  "summary": "Add CSP via nginx server block, not plugin layer",
  "rationale": "WPCode snippet caused TBT regressions on staging. nginx config survives plugin updates.",
  "alternatives_rejected": ["WPCode snippet", "Cloudflare transform rule"],
  "constraints": ["Must not touch PHP layer", "Staging-only until Kiro verifies"],
  "author_model": "kiro-review",
  "domain": "web_stack.security",
  "site": "staging2.willowyhollow.com",
  "confidence": 0.9,
  "timestamp": "2026-06-22T16:45:00Z"
}
```

Note: `id` in `decisions-approved.jsonl` is the final ledger ID. If the proposal used an auto-generated `dec_prop_*` ID, `--approve` prompts Ryan/Kiro for a canonical ID or accepts `--ledger-id dec_staging2_csp_nginx` as a flag. This is the only moment ID normalization happens.

---

## Sign-off gate

### Who can approve

| Signer | When appropriate |
|--------|-----------------|
| `ryan` | Always valid; human authority supersedes all |
| `kiro-review` | Standard for architectural and infrastructure decisions |
| Any agent | **Not valid** — agents propose only, never approve |

The `--signer` flag is a free string in v1 (no cryptographic signature). Convention enforces authority, not the tool. This is consistent with how `author_model: kiro-review` works in existing ledger records.

### What review looks like (10-second confirm)

`--approve` and `--kill` always display the three-line summary before acting:

```
Review required:
  Choice:   Add CSP via nginx server block, not plugin layer
  Risk:     WPCode snippet caused TBT regressions; Cloudflare not available on staging DNS
  Rejected: WPCode snippet, Cloudflare transform rule

Approve as dec_staging2_csp_nginx? [y/N/kill]:
```

`y` → approves and prompts for canonical ledger ID if not supplied  
`N` → exits, record stays PENDING  
`kill` → prompts for reason, marks REJECTED

Non-interactive (Kiro shell use):
```bash
convmem propose_decision --approve dec_prop_20260622_143201_a3f2 \
  --signer kiro-review --ledger-id dec_staging2_csp_nginx --yes
```
`--yes` skips the interactive prompt.

---

## Bridge: DECISION PROPOSED blocks in inter-model docs

Models currently write blocks like this in `docs/inter-model/` files:

```
DECISION PROPOSED:
Choice: Queue semantic duplicate candidates for Kiro review; never auto-merge
Risk: Auto-merge is irreversible; false positives delete real knowledge
Rejected: Auto-merge above similarity threshold
Status: PENDING HUMAN CONFIRM
```

### v1 bridge (manual, no parser)

`convmem propose_decision --list --source inter-model` shows nothing in v1 — the bridge is manual. When an inter-model doc contains a `DECISION PROPOSED` block, the agent or Ryan runs `convmem propose_decision` with the block's fields as CLI flags. The `--source inter-model` flag tags the record for audit. This is the correct v1 behavior: inter-model docs are human-readable communication; the queue is machine-readable state.

### v2 bridge (optional, post-soak)

`convmem propose_decision --parse-doc docs/inter-model/KIRO-CURSOR-2026-06-22.md` scans the file for `DECISION PROPOSED:` blocks, presents each one interactively for confirm/skip, and writes accepted proposals to the pending queue with `"source": "inter-model"`. Implementation: regex extraction of `Choice:`, `Risk:`, `Rejected:`, `Status:` lines. Kiro signs off on parser output before merge.

The v2 parser is out of scope for the initial build. Cursor should stub a `--parse-doc` flag that exits with `"not yet implemented"` so the interface is reserved.

---

## MCP write tool (optional, post-soak)

`mcp_server.py` currently exposes four read-only tools. A future `propose_decision` MCP tool would allow agents in Cursor, Crush, or Continue to write to the pending queue without a terminal session.

**Constraints (non-negotiable):**
- MCP tool writes to `decisions-pending.jsonl` only — never to Chroma
- `--approve` / `--signer` are not exposed via MCP; sign-off is terminal-only (Ryan or Kiro)
- Tool name: `propose_decision`; input schema mirrors the CLI flags
- Returns the `dec_prop_*` ID on success

This section is informational. Cursor does not implement the MCP tool in the initial build.

---

## Non-goals

- **No autonomous Chroma writes.** The tool never calls `store.add_unit` or `store.update_unit`. Ingest is always a separate explicit `convmem add --file` step.
- **No agent approval.** Only `ryan` and `kiro-review` are valid signers. The tool does not validate this in v1 (convention only), but Kiro's acceptance criteria do.
- **No merge of pending records.** Two proposals for the same `relates_to` are not automatically deduplicated. Ryan/Kiro review both and kill the weaker one.
- **No replacement of `convmem brief`.** Brief is the ops snapshot. The pending queue is decision-specific. These are separate concerns.
- **No HTTP API, no web UI, no database beyond JSONL.** The queue file is the single source of truth.
- **No notification system.** Agents check `--list` or read inter-model docs. No push.

---

## Acceptance criteria (Kiro sign-off checklist)

Before Cursor begins implementation, Kiro confirms all of the following:

- [ ] `convmem propose_decision --relates-to X --summary Y --rationale Z --author A` writes exactly one valid JSONL line to `decisions-pending.jsonl` and does not touch Chroma
- [ ] Auto-generated IDs use format `dec_prop_YYYYMMDD_HHMMSS_<4hex>` (no collision risk at human interaction speed)
- [ ] `--list` shows only PENDING by default; `--list --all` shows all statuses
- [ ] `--approve` always displays the three-line review block before acting (no `--yes` bypass of the display, only of the prompt)
- [ ] `--approve` writes to `decisions-approved.jsonl` in ledger-ready format that passes `normalize_ledger_record` without modification
- [ ] `--approve` strips queue-internal fields (`proposed_at`, `source`, `signer`, `approved_at`) from the ingested record
- [ ] `--kill` marks the record REJECTED in `decisions-pending.jsonl` and never writes to `decisions-approved.jsonl`
- [ ] `decisions-pending.jsonl` is append-only — no line is ever deleted or modified in place
- [ ] `convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert` ingests approved records correctly using the existing path (Cursor verifies with one real record before considering this done)
- [ ] `--parse-doc` flag exists and exits with `"not yet implemented"` (interface reserved for v2)
- [ ] No new dependencies beyond what convmem already uses
- [ ] 69 existing tests still pass after implementation

---

*This spec is design only. Cursor implements after Kiro signs off. No code in this document should be copied directly — it is illustrative of intent, not implementation.*
