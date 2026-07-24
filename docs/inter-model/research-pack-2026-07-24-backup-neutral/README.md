# Research pack — backup ops + Neutral owner decisions (2026-07-24)

**Consequence:** Cloud Claude / ChatGPT (max) can open one GitHub tree and get the handoffs plus every attachment named for the research pass—without hunting branch tips.

| Field | Value |
|---|---|
| Branch | `docs/2026-07-24-research-pack-backup-neutral` |
| Who | Cursor assembled pack; Ryan sends handoffs to Claude/ChatGPT |
| What | Decision research for (1) complete-data backup close, (2) Neutral/Office Gate-0 + ledger-first appetite |
| When | After Codex↔Cursor lane split closed (#109/#112) |
| Why | Remaining forward motion needs ops + owner decisions, not more closed-arc re-audit |
| How | Paste `CLAUDE-HANDOFF.md` / `CHATGPT-HANDOFF.md`; attach or browse `attachments/` |

## Do not reopen

- Codex planning / Cursor execution (#109 / #112) — closed  
- Stage 4 / residual tool-output / default semantic dedupe band  
- R2b live capture (unauthorized)

## Handoffs

| Model | File |
|---|---|
| Cloud Claude (max) | [CLAUDE-HANDOFF.md](CLAUDE-HANDOFF.md) |
| Cloud ChatGPT (max) | [CHATGPT-HANDOFF.md](CHATGPT-HANDOFF.md) |

## Attachments (this pack)

See [attachments/SOURCES.txt](attachments/SOURCES.txt) for freeze tips.

| File | Role |
|---|---|
| [CODEX-2026-07-23-complete-data-backup-copilot-audit.md](attachments/CODEX-2026-07-23-complete-data-backup-copilot-audit.md) | Copilot safety audit contract; artifact `492e6e7` |
| [PHASED-PATH.md](attachments/PHASED-PATH.md) | Neutral gated path |
| [NEUTRAL-TARGET.md](attachments/NEUTRAL-TARGET.md) | Neutral v0 target |
| [NEUTRAL-CORE-CANDIDATES.md](attachments/NEUTRAL-CORE-CANDIDATES.md) | Candidate / independence notes |
| [EXTRACTION-PROBE.md](attachments/EXTRACTION-PROBE.md) | Office probe / Gate 0 |
| [IMPLEMENTATION-HANDOFF-1.md](attachments/IMPLEMENTATION-HANDOFF-1.md) | Office implementation handoff (unauthorized until Gate 0) |
| [observe.py](attachments/observe.py) | Observation write path (Chroma-first today) |
| [propose_decision.py](attachments/propose_decision.py) | Decision JSONL / approval path |
| [restic-ensure-chroma-snapshot.sh](attachments/restic-ensure-chroma-snapshot.sh) | Local Restic ensure / gate script |

## GitHub browse (after push)

Repo: `https://github.com/alanmz-crypto/convmem`

Pack root on this branch:

`https://github.com/alanmz-crypto/convmem/tree/docs/2026-07-24-research-pack-backup-neutral/docs/inter-model/research-pack-2026-07-24-backup-neutral`

Raw attachment example:

`https://raw.githubusercontent.com/alanmz-crypto/convmem/docs/2026-07-24-research-pack-backup-neutral/docs/inter-model/research-pack-2026-07-24-backup-neutral/attachments/observe.py`

## Also on origin (source tips)

| Tip | Contents |
|---|---|
| `fix/2026-07-23-complete-data-backup` @ `b8114fe` | Backup implementation + Copilot handoff |
| `plan/2026-07-23-neutral-core-path` @ `74b68aa` | Neutral planning docs (live sources of the copies) |
| `main` | Current `observe.py` / `propose_decision.py` / restic script |

## TL;DR

One branch pack: Claude + ChatGPT handoffs and frozen attachments for backup + Neutral research; lane-split arc stays closed.
