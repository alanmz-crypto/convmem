# CURSOR opinion — retrieval / corpus fix insight

**Date:** 2026-07-15  
**From:** Cursor  
**To:** Ryan + ChatGPT + Claude + Codex + DeepSeek + others

## Best insight lane (and why)

**DeepSeek** for the *current* defect: facts are captured but default `ask` ranks stale, heavily duplicated Jun-30 coordination mass above today’s Arc/PR material. That is IR/corpus-quality, which matches DeepSeek’s wide-lens and Arc 2 finding.

- **GPT** best for freezing sequence and refusing new arcs.
- **Claude** already won Arc 0 (capture/handoff distinctions).
- **Codex** best as implementation auditor, not IR strategist.
- **Cursor** best for local repro and a small patch once the class of fix is chosen.

## Smallest recommended fix

1. Ryan: merge #33; close #31; park #32; leave #6 separate; Codex watch config later.
2. DeepSeek: pick **one** countermeasure class (prefer neutralize the Jun-30 duplicate attractor; else a tiny coordinate-state ranking bias — not a retrieval rewrite).
3. Cursor implements that one class on a bounded branch.
4. Codex re-audits with the same failed `ask` question.
5. Log Arc 2 outcome; stop.

## Acceptance check

Default:

```bash
convmem ask "What is the current status of Arc 0, Arc 1, and GitHub PR #33 for convmem documentation consolidation? Cite source_path."
```

Must cite current Arc/PR or correction-trail material; must not frame the answer from Jun-30 “inbox 33” / v4 org runbook alone.

## Explicitly out of scope

Hybrid retrieval, graph DB, full taxonomy cleanup, timestamp backfill of the corpus, reopening Arc 0, shipping #32 without the recovery-drill trigger.

## Asks

- Other lanes: drop `<LANE>-opinion.md` in this folder.
- Ryan: choose whether DeepSeek writes the countermeasure pick next, or you pick class A/B/C directly.
