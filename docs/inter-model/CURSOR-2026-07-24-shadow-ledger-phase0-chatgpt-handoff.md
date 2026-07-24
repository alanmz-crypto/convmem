# Cursor → ChatGPT: advise Codex on final Shadow Ledger Phase 0 plan

> **Superseded for Architecture authorship (2026-07-24):** Draft PR
> [#115](https://github.com/alanmz-crypto/convmem/pull/115) already contains
> Codex-authored [`ARCHITECTURE-shadow-ledger-phase0.md`](../plans/ARCHITECTURE-shadow-ledger-phase0.md)
> (tip `c9a5c70`), awaiting Ryan HITL. This handoff remains useful as intake
> provenance for ChatGPT→Codex advice, but **do not** treat it as an open
> “write Architecture” work order. Cursor Execute remains prohibited until
> Architecture + Execution HITL. Local Cursor plan
> `codex_phase_0_work_order_940805a0` never wrote a separate Codex handoff file
> on disk — packaging execute was superseded by #115.

**Updated:** 2026-07-24  
**From:** Cursor (local; revised plan after Codex YELLOW review)  
**To:** ChatGPT Cloud (strategy / synthesis — no code, no prod writes)  
**Next actor after you:** Codex local (architecture / execution planning)  
**Why:** Ryan needs a **final** Phase 0 plan. Cursor absorbed Qwen’s audit and
Codex’s corrections into a revised draft, but Codex owns the planning lane.
Your job is to give Codex **sharp advice** so its final plan is approvable
without another rewrite cycle.

## Lane map

| Lane | Role here |
|------|-----------|
| **ChatGPT Cloud** | Adversarial advice → Codex: what the final plan must contain, what to drop, what to gate |
| **Codex** | Author the final Phase 0 plan + `PHASE0-SHADOW-CONTRACT.md` (docs only until Ryan authorizes hooks) |
| **Cursor** | Later Execute only after Ryan accepts Codex’s final plan |
| **Qwen audit** | Already produced eight-file baseline under `docs/audit-ledger-first/` (untracked / needs factual corrections) |
| **Kiro / Neutral / Office** | Out of scope |

## Status (do not re-litigate)

| Item | State |
|------|--------|
| Authority today | **Chroma** is Tier-1 for observations; JSONL export is incomplete |
| Doctor (2026-07-24 session) | ~10,966 active units; **192** Chroma-active / JSONL-missing still current; embed collection metadata lacks `convmem:embed_model` |
| Qwen audit verdict | **YELLOW** — ledger-first sound; prerequisites before cutover |
| Claude review | Accept YELLOW; approve **shadow only**; no cutover / Neutral / migration yet |
| ChatGPT §10 (backup) | Ledger→Chroma restore order is **end-state**; do not execute in Phase 0 |
| Codex review of Cursor plan | **YELLOW** — direction OK; **do not authorize production hooks** until contracts tighten |
| Cursor revised plan | Incorporates Codex’s 8 corrections; lives at `~/.cursor/plans/shadow_ledger_phase_0_cadca832.plan.md` — **draft input for Codex, not final** |
| Branch note | Audit docs currently untracked; repo on `docs/2026-07-24-research-pack-backup-neutral` for research-pack work — **final plan should land on a dedicated feat/docs branch**, not hitchhike unrelated PRs |

## What Codex already required (preserve these)

ChatGPT must treat these as **accepted constraints**, not open debate, unless
you find a concrete contradiction with the repo:

1. **Delta proof only** — Phase 0 validates post-activation mutations via
   timestamped baseline / touched-ID compare. Full empty-corpus rebuild is
   bootstrap/migration, not Phase 0.
2. **Write inventory** — Scope `knowledge_units`: create, full update,
   metadata update, supersede (incl. per-unit partial success), hard delete,
   undo/restore. **Exclude** `conversation_summaries` (independent Tier-1).
   Prefer storage-boundary hooks in `chroma_store.py` with activation controls.
3. **Event envelope** — Shadow records need sequence/event_id/operation/
   stable_entity_id/post_state-or-tombstone/state_hash/embed provenance —
   not bare `ledger_id` + content_hash. Fix audit claim that Chroma IDs are
   “random backend UUIDs”; caller-supplied unit IDs are stable.
4. **Two equality levels** — state equality vs projection equality; document
   text must match for projection equality; embed model may be `unknown`.
5. **Latency contract** — Chroma commits first; bounded shadow wait; failure
   never rolls Chroma back; visible health/lag telemetry. Replace “never
   block Chroma” / “zero production behavior change.”
6. **Crash window honesty** — Chroma-success / shadow-miss is a detectable
   gap, not auto-healed.
7. **Corruption = non-PASS** — no checkpoint past bad records; 0600; file +
   parent-dir fsync on create.
8. **Activation / recursion** — hooks only on authoritative Chroma root;
   disposable replay must force-disable shadow recording.

Also preserve: shadow backup **wiring** needs separate Ryan auth; docs may
name path/retention intent only. Inventory counts must be **runtime-derived
and snapshot-stamped**. Legacy-decision candidate classification uses
**deterministic local heuristics** unless Ryan authorizes external model cost.

## Your job (ChatGPT)

Produce a **paste-ready brief for Codex** (not for Cursor Execute yet) that:

1. States the single recommended Phase 0 definition in one paragraph.
2. Lists **must-include** sections of the final plan (and of
   `PHASE0-SHADOW-CONTRACT.md`) with acceptance criteria Codex can make
   checkable.
3. Lists **must-not** claims (full rebuild, summaries in scope, auto-heal,
   authority transfer, restore-order flip, Neutral extraction).
4. Advises the **doc correction pass** on `docs/audit-ledger-first/` before
   commit — which factual errors to fix, which files own which fix.
5. Advises **stop points / approval sequence** Ryan should use:
   - Approve final plan → docs-only PR (contract + corrected audit) →
     separate approve hooks → later cutover gates.
6. Calls out any remaining ambiguity Cursor’s revised plan still leaves
   (e.g. exact wait-bound default, baseline manifest format, how bulk
   supersede emits per-unit events) and **picks a default** for Codex to
   write down rather than leaving TBDs.
7. Separates backup Track advice: Phase 0 must not entangle complete-data
   backup rollout; cite that restore doctrine stays Chroma-first.

### Method

- Prefer repository-grounded constraints over abstract ledger theory.
- Separate facts / inferences / recommendations.
- Do not reopen “is ledger-first a good idea?” — that is YELLOW-accepted.
- Do not write implementation code or authorize hooks.
- If you disagree with Codex’s eight corrections, say so explicitly with
  evidence; otherwise harden them into final-plan requirements.

## Inputs Ryan can paste / point you at

| Artifact | Role |
|----------|------|
| `docs/audit-ledger-first/*.md` (8 files) | Qwen audit baseline — needs factual corrections before commit |
| Cursor revised plan | `~/.cursor/plans/shadow_ledger_phase_0_cadca832.plan.md` (or paste) |
| Codex YELLOW review | In Ryan’s chat (8 required corrections + stop-point assessment) |
| This handoff | Your instructions |
| Optional research pack | `docs/inter-model/research-pack-2026-07-24-backup-neutral/` — backup/Neutral context only; do not merge scopes |

## Hard stops

- No code edits, no production hooks, no migration, no Neutral Core
- No changing Restic restore doctrine
- No freezing the long-term canonical observation schema as production law
- No authorizing Cursor Execute

## Done when

Paste to Ryan:

```text
## Advice for Codex (final Phase 0 plan)

### One-paragraph Phase 0 definition
### Must-include plan sections (checkable)
### Must-include PHASE0-SHADOW-CONTRACT fields / behaviors
### Must-not claims
### Audit-doc factual fixes (file → fix)
### Defaults for remaining ambiguities (pick one each)
### Ryan approval sequence (ordered stop points)
### Backup entanglement warning (one paragraph)
### TL;DR for Codex (≤5 bullets)
```

Ryan then pastes that block to **Codex** as the planning brief.

## Ryan note

After ChatGPT returns the advice block: give it to Codex and ask for the
final plan + contract. Do **not** ask Cursor to implement until you accept
Codex’s final docs.
