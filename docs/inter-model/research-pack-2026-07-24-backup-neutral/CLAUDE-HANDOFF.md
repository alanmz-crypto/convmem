# Handoff — Cloud Claude (max)

**Pack:** [README.md](README.md) · **Attachments:** [attachments/](attachments/)

## ROLE

You are Claude (max). Independent architecture/ops reviewer for ConvMem.
Do not implement code. Do not invent merges or ledger decisions. Return
research-grade recommendations Ryan can decide from.

## CONTEXT (2026-07-24)

ConvMem is a local evidence bus (index → Chroma/ledger → search/ask/record)
on Ryan’s Arch workstation.

Recently closed / not your problem to reopen:

- Codex planning / Cursor execution lane split: PR #109 + VERIFY close #112
  on main; Kiro PASS already recorded at tip `0096d56` (squash land tip
  `982a502`). Do **NOT** re-audit that arc.
- Crush tool-output residual closed; Stage 4 closed.
- Semantic dedupe default band closed; lower bands unauthorized.
- R2b live capture unauthorized (code on main; draft quarantined).

## Attachments in this pack

Open under `attachments/` (same directory tree on GitHub):

- `CODEX-2026-07-23-complete-data-backup-copilot-audit.md`
- Neutral plans: `PHASED-PATH.md`, `NEUTRAL-TARGET.md`,
  `NEUTRAL-CORE-CANDIDATES.md`, `EXTRACTION-PROBE.md`,
  `IMPLEMENTATION-HANDOFF-1.md`
- `observe.py.txt`, `propose_decision.py.txt`, `restic-ensure-chroma-snapshot.sh`
- `SOURCES.txt` (freeze tips)

## TRACK 1 — Complete-data backup

Implementation candidate (exact SHA):
`492e6e7eacef6cfd64dfc5bb00b25296b5e29288`

Problem: Chroma-only Restic coverage omitted canonical ledgers/sidecars under
`~/.local/share/convmem/`.

Change: snapshot data-root parent; tag `convmem-data-v1`; keep
`convmem-chroma` compatibility; update doctor/offsite/restore consumers.

Hermetic Cursor pytest at that SHA: 90 passed — **NOT** a Copilot safety PASS.

Known critique consensus:

- Expanding coverage is the right problem.
- Risks: concurrent snapshot inconsistency; daily RPO may not be mechanical;
  offsite may be tag-blind; **no** global Tier-1 write quiescence lock exists
  (only pre-write Restic gate + per-source/export locks).
- Do not smuggle Neutral path-generalization through backup work.
- Copilot owns exact-SHA PASS/FAIL before merge; Ryan owns live rollout.

### Your job (Track 1)

1. Recommend **ONE** consistency contract: crash-consistent + reconcile, OR
   real quiescence, OR service stop during snapshot. Name smallest proof.
2. Recommend **ONE** trigger policy for calendar-day RPO; state what fails
   if no durable writes for 48h.
3. Recommend offsite false-green fix or explicit accept of tag-only freshness.
4. List what Copilot MUST FAIL the PR for vs nonblocking.
5. One-page Ryan rollout checklist after Copilot PASS (no secrets).

## TRACK 2 — Neutral Core / Office Team

Direction: evidence-gated Neutral after a real independent Office Team
workflow; operational independence required.

Consensus critique:

- Pause Office coding; Gate 0 without named artifact/people = false readiness.
- Six Office record kinds ≠ Neutral schema.
- Observation ledger-first is NOT a small seam; split A/B/C (narrow defects /
  decision durability / observation migration).
- Decisive question: Will ConvMem move observation ledger-first **on its own
  merits**, independent of Office Team? Yes / No / Not yet.
- Office v0: no Chroma for policy-text workflow.
- Portable contracts: duplicate test file + hash until Neutral exists.
- Coherence bar: identity + durable append/recovery + provenance/relationships
  + ≥1 useful replayable derived view + contracts on both impls.

### Your job (Track 2)

1. Stress-test Yes / No / Not yet consequences for Neutral scope.
2. Minimal Gate 0 workflow card template (fields only; invent no office facts).
3. Is further codebase research required before Yes/No/Not yet, or is it an
   owner product decision now?
4. Flag remaining premature-abstraction traps; do not redesign Neutral.

## HARD RULES

- Prefer consequence → 5 Ws → TL;DR per track.
- Keep backup and Neutral arcs strictly separate.
- No packaging ConvMem, multi-tenant frameworks, or reopening closed arcs.
- If uncertain: state the smallest fact needed — not “defer.”

## OUTPUT FORMAT

```text
## Track 1 — Backup (decision memo)
## Track 2 — Neutral (decision memo)
## Cross-arc constraint (one paragraph)
## TL;DR
```
