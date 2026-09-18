# Planning Handoff: generalize the append-cursor beyond `jsonl_kiro_session`

**Date:** 2026-09-17
**Author:** Claude (measurement + problem statement; no design authority here)
**For:** OpenAI Codex (architecture + execution planning) → Kiro (review) → Cursor (implement, after Ryan)
**Authorization:** Ryan, 2026-09-17 (verbal: "if the next job is yours do it, or create a handoff")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | none yet — `plan/2026-09-18-generalize-append-cursor` by convention |
| **Tip SHA** | n/a |
| **Push status** | n/a |
| **PR** | `not opened` |
| **Ryan GATE** | **Yes, before implementation — not before planning.** Planning is gate-independent and may start now. Any change to `incremental_jsonl.py` or to activation is an Arc Codex gate Ryan holds. |
| **Deliverable** | `ARCHITECTURE-*.md` + `EXECUTION-*.md` + a matching `STATUS-*.md`, per the arc-authoring convention. **Not code.** |

---

## The problem, measured

convmem re-summarizes an **entire** transcript whenever it changes. `processed.json`
is keyed by whole-file content hash (`ingest.py:1219`), so a one-message append
re-indexes the whole file. Each chunk costs two paid provider calls
(summarize + distill), and `chunk_size=60 / chunk_overlap=10` slides a 50-message
step.

Measured on 2026-09-17:

| Measure | Value |
|---|---|
| `~/.codex/history.jsonl` | 3,281 lines → 66 chunks → **132 paid calls per touch** |
| Units it accumulated | **44,770 of 79,566 active — 56% of the serving corpus** |
| Share of provider traffic (since 09-15) | **~94%** (1,434 of 1,519 failures) |
| Index timeouts attributable to it | **100%** of the retained window |

That specific file has been excluded, which stopped the bleed. **The mechanism
is untouched.** It still applies to every append-heavy source: Codex rollouts,
Copilot sessions, Cursor transcripts, and any future Claude adapter.

The fix already exists and is deliberately narrow: `incremental_jsonl.py:42`
sets `ELIGIBLE_FORMAT = "jsonl_kiro_session"`, and `:526` raises
`IsolationViolation` for anything else.

---

## The question for Codex

**Can the append-cursor be generalized to the other append-only JSONL adapters,
and if so at what cost in risk and work?** A defensible "no, and here is why"
is an acceptable answer.

### The crux

The coordinator depends on a capability only one adapter has:

```
adapters/kiro_session_jsonl.py:151  def parse_complete_prefix(...) -> CompletePrefixView
```

No other adapter can parse a complete prefix or report byte ranges. Candidate
formats, all currently whole-file:

| Format | Adapter | Append-only? |
|---|---|---|
| `jsonl_codex_rollout` | `codex_rollout_jsonl.py` | believed yes — needs confirming |
| `jsonl_copilot_session` | `copilot_session_jsonl.py` | believed yes — needs confirming |
| `jsonl_cursor` | `jsonl_chat.py` | unknown |
| `jsonl_codex_history` | `codex_history_jsonl.py` | **rolling, not append-only** — entries age out |
| `jsonl_claude_session` | does not exist | see the adapter handoff |

SQLite sources (crush, kiro, openwebui, cursor store) are a different problem
and are **out of scope** here.

### Questions a plan must answer

1. Which of those formats are genuinely append-only under their writers'
   behaviour, established by evidence rather than assumption? `history.jsonl`
   is the cautionary case: it looks like an append log and is not one.
2. Does `parse_complete_prefix` generalize, or does each adapter need its own?
   Is there a shared `jsonl_io` primitive that makes this cheap?
3. How is truncation, rewrite or rotation detected and failed closed? The
   existing invariant — a selected complete prefix may be followed by a pure
   append but never replaced, truncated or mutated before commit — must hold
   per adapter, not just for Kiro.
4. What does adoption cost for already-indexed sources? Arc Codex's STATUS
   lists "Bootstrap required" as a separate Ryan grant covering rebuild and its
   model cost. Generalizing multiplies that.
5. Is per-adapter opt-in the right shape (config lists eligible formats), or
   does eligibility belong to an adapter capability check?
6. What is the smallest slice that delivers real savings? Probably one
   additional format, chosen for the best evidence-to-risk ratio.

---

## What NOT to do

- **No implementation.** This handoff produces plans. Cursor implements after
  Kiro review and a Ryan grant.
- **Do not modify `incremental_jsonl.py`**, its canary, or its isolation
  harness. Arc Codex owns them and its P2 canary is unauthorized.
- **Do not enable anything.** `[index.incremental_jsonl]` stays absent/false;
  watcher activation is a separate Ryan gate. No model may infer one gate from
  another.
- **Do not change** `chunk_size`, `chunk_overlap`, retrieval, scoring, or the
  writer/provenance path.
- **Do not fold in the Claude adapter.** It has its own handoff and its own
  gates; this plan should say what it would *inherit*, not build it.
- **Do not touch** `fix/2026-09-17-watch-skip-hash-parity` — it is mid-review
  with an R2b rebind pending.

---

## Acceptance criteria for the plan

- [ ] Names each candidate format with **evidence** for append-only behaviour,
      or excludes it
- [ ] States whether `parse_complete_prefix` generalizes, with the seam
- [ ] Carries the fail-closed invariants per adapter, not just for Kiro
- [ ] Quantifies expected savings against the measured baseline above, and
      states bootstrap cost separately
- [ ] Proposes the smallest first slice, with an explicit non-goal list
- [ ] Ends at a Ryan decision point; grants nothing itself
- [ ] `STATUS-<slug>.md` created from the 10-section template and added to the
      Active STATUS list in `CLAUDE.md` and `AGENTS.md`

---

## Why this is Codex's lane

Per the team charter: architecture and execution planning is Codex; Kiro
reviews; Cursor implements after Ryan authorizes. This work is also
Arc-Codex-adjacent, so it needs an author who holds that arc's design context.

The author of this handoff measured the problem and deliberately did not design
the solution — the measurement is offered as input, not as a proposed shape.

---

## Related

| What | Path |
|---|---|
| Measurements and full diagnosis | `CLAUDE-2026-09-17-ingest-cost-diagnosis.md` |
| Arc Codex brief | `../plans/STATUS-codex-jsonl-production-integration.md` |
| Existing coordinator | `incremental_jsonl.py` |
| Claude adapter (would inherit this) | `CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` |
| Correctives branch (do not touch) | `fix/2026-09-17-watch-skip-hash-parity` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet — added with this commit
- [ ] `STATUS-*.md` — none exists yet; creating it is part of the deliverable
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file and the diagnosis record before designing
- [ ] Confirm with Ryan whether the arc is authorized to start
- [ ] State arc codename, goal, role, system state and next action
