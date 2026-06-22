# `convmem propose_decision` — Design Spec

**Author:** ChatGPT (orchestration/strategy lane)
**Date:** 2026-06-22
**Status:** Design only — no implementation. For Cursor to build after soak passes and Kiro signs off below.
**Builds on:** `convmem brief`, existing `Decision` ledger schema (`ledger.py`), `convmem add --file --upsert` (`observe.py`).

---

## 1. Purpose

`convmem brief` solved *shared understanding* — every agent now starts a session from the same snapshot instead of re-deriving corpus state from scattered handoffs. It did not solve *shared decision-making*. Right now, a model that reaches a decision worth recording has exactly two paths: hand-write a JSONL line and hope someone runs `convmem add`, or drop a `DECISION PROPOSED:` text block into a chat or an inter-model doc and hope a human notices it. Both are informal, neither is queryable until a human manually transcribes it into the ledger, and neither leaves a trail of *what was proposed but not yet accepted*.

`propose_decision` closes that gap with the smallest possible mechanism: a CLI command that writes a structured proposal to a **plain pending-queue file** (never Chroma), a `--list`/`--approve` pair that lets Ryan or Kiro turn a pending line into a signed one, and a thin adapter that feeds approved lines into the ingest path that already exists. It does not introduce a new storage engine, a new transport, or a new authority. It formalizes the `DECISION PROPOSED` convention that's already in informal use across `docs/inter-model/` so that proposing a decision and recording one converge on the same schema, instead of diverging into "decisions some human remembered to type up" versus "decisions a script can read."

This is explicitly the next step in the trajectory ChatGPT proposed earlier this session ("re-evaluate decision workflows after brief adoption") — not a new direction.

---

## 2. Workflow

```
Observation                Proposal                  Review                 Signed Decision           Ingest
(tool or agent finds       (any agent writes a        (Ryan or Kiro reads    (status flips to          (existing
 something, already         pending_decisions.jsonl    --list, accepts or     "accepted", author_model  convmem add
 ingestible today via       line via                   rejects)               becomes the signer,       --file
 convmem add)               propose_decision)                                  not the proposer)         --upsert)
     │                           │                          │                       │                       │
     ▼                           ▼                          ▼                       ▼                       ▼
 obs_staging2_...   →   dec_prop_20260622_001   →   convmem propose_decision   →   appended to        →   convmem add
 (already in Chroma)    {status: PENDING}            --approve / --reject          decisions-approved      --file decisions-
                         (queue file only)            --signer ryan|kiro            .jsonl (queue file)     approved.jsonl
                                                                                                              --upsert
                                                                                          │
                                                                                          ▼
                                                                                  Same `Decision` shape
                                                                                  as existing signed
                                                                                  examples — no schema
                                                                                  change required.
```

Nothing in this pipeline touches Chroma until the last arrow, and that last arrow is the **existing, unmodified** `convmem add --file --upsert` command. The queue is the only new storage surface.

---

## 3. CLI UX

Four subcommands under one verb. No new top-level command needed beyond what `README-START-HERE.md` already sketched; this section makes the sketch concrete and complete.

### 3.1 Propose

```bash
convmem propose_decision \
  --relates-to obs_staging2_willowyhollow_com_006 \
  --summary "Add Content-Security-Policy header via nginx, not WordPress plugin layer" \
  --rationale "WPCode caused TBT regressions on staging. CF transform rules don't apply — staging2 doesn't route through CF." \
  --alternative "WPCode header snippet" \
  --alternative "Cloudflare transform rule" \
  --constraint "Must not touch PHP/plugin layer" \
  --domain web_stack.security \
  --site staging2.willowyhollow.com \
  --author chatgpt-orchestration
```

- `--relates-to` is **required** — mirrors the existing schema rule (`normalize_ledger_record` rejects any decision without it). If the observation doesn't exist yet, the proposer should `convmem add` it first, or pass `--relates-to none` to mark it a freestanding policy decision (rare; see §9).
- `--summary` and `--rationale` are required text. Rationale is what eventually lands in the embedded document text per the existing `observe.py` convention (`summary + keywords + " Rationale: " + rationale`) — nothing new here, just inherited.
- `--alternative` and `--constraint` repeat (zero or more times each) and map directly to `alternatives_rejected` / `constraints`.
- `--author` is the **proposing** model's identity (e.g. `chatgpt-orchestration`, `crush-session`, `cursor-implementer`). This is distinct from the signer (§5) — see the attribution note below.
- `--domain` defaults to `web_stack.security` to match the existing `Decision` dataclass default; `--site` defaults to empty.
- On success, prints the generated proposal id and a one-line confirmation:
  ```
  Proposed: dec_prop_20260622_001  (status: PENDING)
  Relates to: obs_staging2_willowyhollow_com_006
  Run `convmem propose_decision --list` to review, or
  `convmem propose_decision --approve dec_prop_20260622_001 --signer ryan` to accept.
  ```
- No interactive prompt mode in v1 — flags only, so it's scriptable from any agent's shell tool without TTY assumptions. (`convmem ask -i` already covers the interactive case for a different command; no need to duplicate that pattern here.)

### 3.2 List pending

```bash
convmem propose_decision --list
```

```
PENDING (2)
  dec_prop_20260622_001  staging2.willowyhollow.com  web_stack.security
    "Add CSP header via nginx, not WordPress plugin layer"
    proposed by chatgpt-orchestration · relates_to obs_staging2_willowyhollow_com_006 · 2026-06-22T20:10:00Z

  dec_prop_20260622_002  (no site)  coding.tooling
    "Cache embeddings for repeated propose_decision dry-runs"
    proposed by cursor-implementer · relates_to dec_convmem_single_writer_chroma · 2026-06-22T20:14:00Z

REJECTED (1, last 7 days)
  dec_prop_20260621_004  rejected by ryan · "duplicate of dec_convmem_no_auto_merge"
```

- Default view shows PENDING only; `--all` includes REJECTED and APPROVED history; `--json` emits the raw queue lines for scripting.
- Rejected entries stay in the queue file (status flips, not deleted) so the rationale for *not* deciding something is preserved — this matches the existing philosophy in the corpus (the no-auto-merge decision explicitly argues for queue-and-review over silent disposal).

### 3.3 Approve

```bash
convmem propose_decision --approve dec_prop_20260622_001 --signer ryan
convmem propose_decision --approve dec_prop_20260622_001 --signer kiro-review --edit-rationale "..."
```

- `--signer` is **required** and restricted to `ryan` or a Kiro identity string (`kiro-review`, matching the `author_model` value used in every existing signed example). The CLI should validate against this small allow-list, not accept arbitrary strings — this is the actual sign-off gate, not just a label.
- Optional `--edit-summary` / `--edit-rationale` / `--edit-constraint` let the signer adjust wording at approval time without a separate edit-then-approve round trip. If omitted, the proposal ships as written.
- On approve, the CLI:
  1. Rewrites the queue line's `status` from `PENDING` to `APPROVED`.
  2. Emits a **new** JSONL line, shaped exactly like the existing signed examples (`decision-csp-nginx.jsonl`, `decisions-session-2026-06-18.jsonl`), into `decisions-approved.jsonl`. `author_model` on this emitted line is the **signer** (`ryan` or `kiro-review`), matching the existing corpus convention where every signed decision's `author_model` is `kiro-review`, never the original proposer.
  3. Preserves the proposer's identity as `proposed_by` inside the emitted record — a new, additive field, not a schema change to the required fields (see §9 on schema impact).

### 3.4 Reject

```bash
convmem propose_decision --reject dec_prop_20260622_004 --signer ryan --reason "duplicate of dec_convmem_no_auto_merge"
```

- Same signer restriction as approve. `--reason` is required for rejects (optional for approves, since approval is self-explanatory but rejection reasoning is exactly the kind of thing that prevents the same proposal from being re-litigated by a future agent that didn't see the first attempt).
- Rejected entries are never deleted, only marked — append-only queue, same pattern as the existing `dedupe_queue.jsonl` convention referenced in the no-auto-merge decision's constraints.

---

## 4. Pending queue format (on disk, not Chroma)

**Location:** `~/.local/share/convmem/pending_decisions.jsonl`

One JSONL line per proposal, append-only (status changes are new fields written via rewrite-in-place by id, following the same atomic-write pattern — temp file + rename — already used for `processed.json` per the best-practices doc). Shape:

```json
{
  "id": "dec_prop_20260622_001",
  "kind": "decision_proposal",
  "status": "PENDING",
  "relates_to": "obs_staging2_willowyhollow_com_006",
  "summary": "Add Content-Security-Policy header via nginx, not WordPress plugin layer",
  "rationale": "WPCode caused TBT regressions on staging. CF transform rules don't apply.",
  "alternatives_rejected": ["WPCode header snippet", "Cloudflare transform rule"],
  "constraints": ["Must not touch PHP/plugin layer"],
  "domain": "web_stack.security",
  "site": "staging2.willowyhollow.com",
  "proposed_by": "chatgpt-orchestration",
  "proposed_at": "2026-06-22T20:10:00Z",
  "signer": null,
  "signed_at": null,
  "rejection_reason": null
}
```

This is deliberately **not** the `Decision` dataclass — it's a superset wrapper (`kind: decision_proposal`, `proposed_by`, `proposed_at`, `signer`, `status` values of `PENDING`/`APPROVED`/`REJECTED`) that the approve step *transforms into* a proper `Decision`-shaped record. Keeping the queue schema distinct from the ledger schema means:

- The queue file is never accidentally ingestible by `convmem add` (wrong `kind` value, `normalize_ledger_record` will reject it outright since `decision_proposal` isn't in `LEDGER_KINDS`).
- The two concerns — "what's been proposed" and "what's been signed" — stay structurally separate, which is the whole point of the human/Kiro gate.

**Approved output location:** `~/.local/share/convmem/decisions-approved.jsonl` — a real ledger-shaped JSONL file, append-only, in the exact format of the existing `examples/*.jsonl` files. This file is what gets passed to `convmem add --file ... --upsert`.

---

## 5. Sign-off gate

**Who can approve:** Ryan (human, `--signer ryan`) or Kiro (`--signer kiro-review`). No other value is accepted by the CLI. This mirrors the existing corpus reality — every single signed `Decision` example in this tar has `author_model: kiro-review`; there is no precedent for any other model self-signing a decision, and this spec doesn't introduce one.

**What changes on approve, precisely:**
1. Queue line status: `PENDING` → `APPROVED`.
2. A new line is appended to `decisions-approved.jsonl`, with `author_model` set to the signer (not the proposer).
3. Nothing touches Chroma. Approval produces a file on disk that is *ready* to ingest, not an ingested record. This is intentional — it keeps the single-Chroma-writer constraint absolute: ingestion is still a deliberate, separate, human-or-Cursor-run command.

**What changes on reject:** Queue line status → `REJECTED`, `rejection_reason` populated, `signer` recorded. No further action; the proposal is closed but auditable.

**No silent auto-approval, ever** — there is no flag, config value, or "trusted model" allowlist that bypasses `--signer`. This is the one hard line in the whole spec.

---

## 6. Ingest path — approved proposals become ledger records

No new ingest mechanism. The bridge is exactly the command already documented in `README-START-HERE.md` and demonstrated by every example file in this tar:

```bash
convmem add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

Because the approve step (§3.3) already emits lines in the precise shape `normalize_ledger_record` expects — `kind: "decision"`, required `relates_to`, optional `rationale`/`alternatives_rejected`/`constraints` — this command needs zero changes to `ledger.py` or `observe.py`. The `--upsert` flag is important here specifically because a signer may use `--edit-rationale` at approval time after a proposal already round-tripped once; upsert-by-`ledger_id` (already implemented in `ingest_observation_file`) makes re-running ingest after an edit safe rather than duplicative.

Suggested cadence: Cursor (or whichever agent has shell access) runs the ingest command at natural checkpoints — end of session, after a batch of approvals, or on demand via `convmem propose_decision --ingest-approved` as a convenience wrapper that simply shells out to the `add --file --upsert` call above. That wrapper is optional sugar, not a new code path.

---

## 7. Inter-model bridge — `DECISION PROPOSED` blocks

The informal pattern already in use:

```text
DECISION PROPOSED:
Choice: ...
Risk: ...
Rejected: ...
Status: PENDING HUMAN CONFIRM
```

becomes a **convention for writing inter-model doc messages that mirror a queue entry**, not a replacement for the queue. Concretely:

- When an agent without shell access (ChatGPT, or any model in a paste-only session) reaches a decision worth proposing, it writes the `DECISION PROPOSED` block into `docs/inter-model/<MODEL>-<date>-<topic>.md` exactly as today.
- Whichever agent next has shell access (typically Cursor) transcribes that block into a `convmem propose_decision` call — `Choice` → `--summary`, `Risk`/constraints → `--constraint`, `Rejected` → `--alternative`. This is a one-line, low-judgment transcription step, not a redesign of the proposal.
- Once transcribed, the inter-model doc block should be edited to add `Queue id: dec_prop_...` so anyone reading the doc later can jump straight to `--list` / `--approve` instead of re-deriving status from prose.

This keeps the inter-model docs as the *narrative* record (why a model thought this was worth proposing, in context) while the queue file becomes the *structured* record (what's pending, who proposed it, what its current status is). Neither replaces the other; the queue id is the seam between them.

---

## 8. MCP v2 (optional, read-only propose)

Not required for v1. If/when MCP agents (Crush, Cursor via MCP) should be able to propose without shell access, the only safe addition is a **sixth MCP tool**, `propose_decision`, with these hard constraints:

- Writes **only** to `pending_decisions.jsonl` — identical effect to the CLI's propose path, same validation, same required `relates_to`.
- **No** MCP tool may call `--approve` or `--reject`. Sign-off stays human/Kiro, off the MCP surface entirely, regardless of which agent is asking.
- **No** MCP tool ever writes to Chroma. This is consistent with the existing MCP server design (already read-only; `mcp_server.py` exposes no ingest tool today) and should stay that way — adding a write-capable MCP tool here would be the first crack in that boundary, and it isn't necessary, since `propose` is by definition not a write to the system of record.

This section is explicitly optional and should not block v1 shipping with CLI-only proposal.

---

## 9. Non-goals

- **No agent-to-agent messaging system.** Proposals are written to a file; nothing pushes notifications. An agent finds out about pending proposals by running `--list`, same as it finds out about anything else in this project — by checking, not by being pinged. Consistent with ChatGPT's prior stated position: "do not build agent messaging."
- **No autonomous Chroma writes**, under any signer, any confidence threshold, any flag. The two-step approve-then-ingest structure (§5, §6) is intentionally not collapsible into one command that both signs and ingests — keeping them separate means a human/Kiro mistake in `--approve` doesn't simultaneously corrupt the index; it just produces a wrong line in a file that can be edited before the separate `convmem add` step runs.
- **No semantic merge or dedup logic in this command.** If a proposal duplicates an existing signed decision, that's caught the same way duplicates are caught today — human/Kiro judgment at review time (§3.2's rejection example), not a similarity-threshold auto-reject. This mirrors the existing `dec_convmem_no_auto_merge` decision's reasoning almost exactly, just applied one layer earlier in the pipeline.
- **No new schema fields on the `Decision` dataclass itself.** `proposed_by` and `proposed_at` live in the *queue* record, not the ledger record. Once ingested, a decision looks exactly like every other decision in the corpus today — `ledger.py` needs zero changes for this to work, which is by design: this is a workflow spec, not a schema spec.
- **No MCP write tool in v1** (see §8 — explicitly deferred, not abandoned).
- **No interactive/TTY prompt mode in v1** — flags only, for scriptability across agents that may not have a real terminal.

---

## 10. Acceptance criteria (for Kiro sign-off before Cursor builds)

- [ ] `propose_decision` (no flags beyond `--relates-to`/`--summary`/`--rationale`/etc.) writes one line to `pending_decisions.jsonl` and **does not** touch Chroma, `processed.json`, or any existing ledger file.
- [ ] A proposal missing `--relates-to` is rejected by the CLI with a clear error, mirroring the existing `normalize_ledger_record` rule (no decision without `relates_to`) — checked client-side before the queue write, not just at eventual ingest time.
- [ ] `--list` reads only the queue file; never opens a Chroma connection (consistent with `brief`/`stats` using `chroma_readonly.py` rather than `PersistentClient`, per the agreed Chroma access pattern).
- [ ] `--approve` requires `--signer` and only accepts `ryan` or a `kiro-*` identity string; any other value is a hard CLI error, not a warning.
- [ ] `--approve` output, when fed into `convmem add --file decisions-approved.jsonl --upsert`, ingests without modification to `ledger.py`/`observe.py` — i.e. Cursor's implementation must produce output that already matches `normalize_ledger_record`'s expectations, verified against at least one of the three example JSONL files in this tar as a shape reference.
- [ ] `--reject` requires `--reason` and leaves the original proposal line intact (status flips, content doesn't disappear).
- [ ] Queue file writes use the same atomic temp-file-then-rename pattern as `processed.json`, per the agreed ingest memory pattern — no partial-write corruption risk.
- [ ] No code path in this feature opens a long-lived Chroma writer outside the existing, already-reviewed `convmem add` command.
- [ ] Inter-model `DECISION PROPOSED` doc blocks are unaffected — this feature adds a queue id reference convention to them, it does not require rewriting the existing doc format.
- [ ] Kiro confirms this spec requires no changes to `Decision`/`Observation`/`Verification` dataclasses in `ledger.py`.

---

*End of spec. Questions or disagreements go to `docs/inter-model/CHATGPT-2026-06-22-propose-decision-spec.md` per the existing inter-model convention — not back into this file.*
