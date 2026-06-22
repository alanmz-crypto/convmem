# convmem — Reconciliation Handoff (Sonnet, 2026-06-22)

## 🔵 Who's writing this and why

This is **Sonnet** (MCP expert seed — see `HANDOFF-GREENFIELD.md` for that role's full scope). I was handed two new docs to review: `HANDOFF-FOR-MODELS.md` (written by a *different* Claude session — the architecture/brainstorm one, not me) and `HANDOFF-MULTI-AGENT.md` (Kiro). Neither doc is wrong about its own area, but they disagree with each other and with the rebuild log on several numbers, and there's a role-attribution mismatch worth surfacing before anyone builds on top of either one as ground truth. This file exists to point at the actual source of truth for each disputed item and flag what still needs a human call.

I'm not overwriting either source doc — both stay as the record of what each agent reported at the time. This is the cross-check layer.

---

## Numbers that disagree across docs — checked against the rebuild log directly

I re-grepped `rebuild-20260619-0629.log` myself rather than trust either summary. The log has exactly one `Done.` line:

```
Done. files_processed=121 files_skipped=1 chunks_indexed=263 units_indexed=1018
```

| Claim | HANDOFF-FOR-MODELS (Claude) | HANDOFF-MULTI-AGENT (Kiro) | **Log says** |
|---|---|---|---|
| Knowledge units | ~1,710 (explicitly pre-rebuild) | **1,028** | **1018** |
| Files processed | n/a this doc | **121**, but per-source breakdown sums to **122** (54+29+24+6+7+1+1) | **121** |
| Unit tests passing | n/a this doc | **72** | My earlier handoff + original HANDOFF-GREENFIELD both said **69** |

**My read:** 1018 is correct — it's the only number that comes from a log line rather than a typed summary. 1028 now appears in two independent docs (Kiro's, and the seed README I reviewed earlier), which makes it look authoritative purely by repetition, but repetition isn't verification — neither doc cites the log line itself. Same logic for 121 vs. 122: the aggregate (121) matches the log; the per-source breakdown is off by one somewhere, which probably just means one bucket in Kiro's table has a stale count from before the rebuild. The 69-vs-72 test count I can't adjudicate at all — I have no test output in anything I've been given, from either session. That one needs an actual `python -m unittest discover -s tests -q` run reported back, not more inference from documents.

**Recommendation:** before either number gets used in a commit message, decision record, or status report, someone should paste the literal last line of the most recent rebuild log and the literal last line of the most recent test run. Two terminal commands settle three of these four numbers permanently.

---

## Role/attribution mismatch — needs a human answer, not a guess

HANDOFF-FOR-MODELS.md describes itself making five concrete decisions this session (schema extension, Procedure type, exclude-state design, agent-access roadmap, decision-capture threshold) and explicitly says **"Builder has not yet been engaged this session."**

HANDOFF-MULTI-AGENT.md (Kiro), describing what appears to be the same session window, says those same five things are **already implemented**, and attributes the implementation to **Kiro** — including writing the schema extension, implementing exclude, and building the MCP server. "Builder" doesn't appear anywhere in Kiro's agent-roles table.

Two honest readings, and I can't tell which from the documents alone:
1. **"Builder" was retired as a role and Kiro absorbed implementation duties** sometime in this session window — in which case Kiro's doc is just using current terminology and there's no actual contradiction, just a naming change neither doc explains.
2. **Two different sessions' worth of work got compressed into overlapping doc snapshots** — Claude's doc captured the moment right after decisions were confirmed but before any implementation, and Kiro's doc captured a later moment after Kiro (not "Builder") actually built them, and the two docs just weren't sequenced relative to each other when handed to me.

Either way, this isn't mine to resolve by inference — it changes who owns review/sign-off on the next round of changes. **This needs a direct answer from Ryan or from whichever agent session is authoritative on current roles**, not a third document guessing at it.

---

## Smaller things, flagged but not blocking

- **HANDOFF-FOR-MODELS.md's corpus snapshot table** (Crush ~228, Continue ~221, Cursor ~1,215, etc.) is explicitly labeled pre-rebuild ("Just indexed; tool_call extraction pending"). Fine as historical record. Don't let it get cited later as current composition — it'll be off by hundreds of units against the post-rebuild 1018.
- **Commit log in Kiro's doc** lists `c176336 Procedure extraction from Crush` and `17ee28f Cursor store.db adapter + procedures` as separate entries. Both touch procedure extraction. If that's two passes at the same feature (first draft, then store.db-specific follow-up), fine — just flagging in case it's actually duplicate/competing implementations that need a pick-one decision.
- **My own earlier MCP-verification handoff** (the one I wrote after the tar review) is consistent with Kiro's doc on every MCP-specific fact that overlaps: timeout 120, no server-side tool prefix, protocol negotiated not hardcoded, graceful `ask` degradation. No new MCP contradictions surfaced by these two docs — good, that part of the picture is stable across three independent write-ups now (mine, Kiro's, and the original handoff's top section).

---

## What I'd actually do next, in order

1. Run `convmem stats` and the test suite once, live, and paste both literal outputs into whichever doc is meant to be canonical going forward. That kills the 1018/1028 and 69/72 disputes for good — both are one-command questions, not architecture questions.
2. Get a one-line answer on the Builder/Kiro question before the next implementation round starts, so sign-off authority is unambiguous.
3. Treat HANDOFF-FOR-MODELS.md's five decisions as **confirmed by Ryan and not in dispute** — that part's solid regardless of the Builder/Kiro question; only "who coded it" is unclear, not "was it agreed."
4. My own MCP P0 (live Crush stdio handshake) is still outstanding and unaffected by anything in these two docs — see `HANDOFF-GREENFIELD.md` § MCP integration for that.

---

## Source docs this reconciles

- `HANDOFF-FOR-MODELS.md` — Claude (architecture session), 2026-06-22, pre-rebuild-aware framing
- `HANDOFF-MULTI-AGENT.md` — Kiro, 2026-06-22, post-rebuild framing
- `rebuild-20260619-0629.log` — ground truth for the unit/file counts, re-verified by Sonnet against this doc's claims
- `HANDOFF-GREENFIELD.md` — Sonnet's MCP verification pass, 2026-06-22 (no new conflicts found between that and these two)
