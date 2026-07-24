# Handoff — Cloud ChatGPT (max)

**Pack:** [README.md](README.md) · **Attachments:** [attachments/](attachments/)

## ROLE

You are ChatGPT (max). Adversarial research reviewer. Challenge soft
assumptions. Prefer repository-grounded reasoning from the attachments.
No implementation. No merges.

## MISSION

Ryan needs research-grade answers before moving forward on two remaining
tracks after the Codex↔Cursor lane split closed (#109/#112). Prior
Cursor/Claude/ChatGPT consensus exists; find holes, false dichotomies, and
missing measurements—not restart closed work.

## NON-GOALS

- Re-verify Codex planning package / Kiro PASS at `0096d56` / PR #109/#112.
- Reopen Stage 4, residual tool-output, default semantic dedupe band, R2b live.
- Design Neutral package system or Office product UI.

## Attachments (read these)

Under `attachments/`:

| File | Use for |
|---|---|
| `CODEX-2026-07-23-complete-data-backup-copilot-audit.md` | Backup audit contract; SHA `492e6e7` |
| `restic-ensure-chroma-snapshot.sh` | Gate / tag / path behavior |
| `observe.py` | Observation authority / write order |
| `propose_decision.py` | Decision durability / recovery |
| `PHASED-PATH.md`, `NEUTRAL-TARGET.md`, `NEUTRAL-CORE-CANDIDATES.md` | Neutral direction |
| `EXTRACTION-PROBE.md`, `IMPLEMENTATION-HANDOFF-1.md` | Gate 0 / Office handoff |
| `SOURCES.txt` | Freeze provenance |

## TRACK 1 — Complete-data backup

Assume unless attachments disprove:

- Restic gate runs before selected overwrite paths, not every mutation.
- Offsite timer copies latest tagged snapshot; may not verify destination
  path/time/ID.
- No global Tier-1 quiescence lock; writers can run during backup.
- Expanding to full data root fixes coverage but can change failure mode from
  “missing ledgers” to “complete-looking inconsistent restore.”

### Deliverables

1. Decision matrix with **exactly one** recommended cell for trigger policy,
   consistency contract, and offsite verification bar — plus evidence that
   would overturn each choice.
2. Silent-inconsistency threat model for file pairs under the data root:
   reindex-repairable vs restore-blocking.
3. Should Copilot **FAIL** without quiescence, or **PASS** with documented
   limits? Argue one side hard.
4. Minimal live drill protocol for Ryan after merge (conceptual; no secrets).

## TRACK 2 — Neutral / ledger-first appetite

Decisive question:

> Will ConvMem Engineering adopt observation ledger-first architecture on its
> own merits, independent of Office Team?

Answers: **Yes** / **No** / **Not yet**  
Scopes: **A** narrow defects | **B** decision durability | **C** observation migration

### Deliverables

1. For each Yes / No / Not yet: honest Neutral v0 scope (what must drop).
2. Concrete seams that MUST be audited before calling observation↔decision
   “small consistency” — cite attachment files/lines where possible.
3. Gate 0 incompleteness test: minimum fields without which “execution-ready”
   is false advertising.
4. Non-semantic “active policy index” for Office v0: legitimate or theater?
   Pick one.
5. Coherence bar: improve or accept
   (identity + durable append/recovery + provenance/relationships + ≥1 useful
   replayable derived view + duplicated contracts until extraction).

## METHOD

- Separate facts / inferences / recommendations.
- Prefer blocking vs nonblocking.
- Call out where prior Claude advice was wrong if you disagree (especially:
  existing write-lock for backup; “small” observe/decision consistency).
- Keep backup and Neutral recommendations non-entangled.

## OUTPUT FORMAT

```text
## Executive answer (what Ryan should research/decide next, ordered)
## Track 1 findings
## Track 2 findings
## Disagreements with prior Cursor/Claude notes
## TL;DR (≤5 bullets)
```
