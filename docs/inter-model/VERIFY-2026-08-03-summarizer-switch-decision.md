# Verify — Summarizer switch decision closeout

```
Planning Status

Phase:        Verify (summarizer-switch-decision)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Codex (draft); Ryan (decision); read-only only
Authority:    Freeze-era decision review
```

**Subject / tip:** `docs/inter-model/CODEX-2026-08-02-summarizer-switch-decision.md`  
**PR(s):** n/a  
**EXECUTION / ARCHITECTURE:** n/a  
**Goal:** Close the freeze-era review of the packet without authorizing a live `config.toml` edit.

## Human consequence

**Consequence:** Ryan can close the freeze review on the decision packet; the actual switch still waits on a later grant.

### 5 Ws

| | |
|---|---|
| **Who** | Codex drafted the packet; Ryan owns the switch. |
| **What** | Verify `qwen3.5:latest` is the better summarize candidate and the packet stays read-only. |
| **When** | Freeze window after the 2026-08-02 bakeoff. |
| **Why** | The 30-row real-pair bakeoff supersedes the older 3-row smoke test. |
| **How** | Compare the packet, aligned handoff docs, and freeze rule; do not edit live config. |

**TL;DR:** The packet closes as valid freeze-era input, but it is still not a config change.

**Honest limits / caveats:** Draft closeout only; no switch, baseline update, or live smoke.

## Closeout note

If Ryan accepts this verify, the packet is closed as read-only evidence and the only remaining action is a later explicit config grant, if he chooses to apply it.

## Merge reading

- Decision packet: [CODEX-2026-08-02-summarizer-switch-decision.md](CODEX-2026-08-02-summarizer-switch-decision.md)
- Active handoff: [LATEST.md](LATEST.md)
- Related handoff: [CURSOR-2026-07-23-crush-qwen-stability-handoff.md](CURSOR-2026-07-23-crush-qwen-stability-handoff.md)

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Read-only comparison of the packet and surrounding handoff docs | Editing `~/.config/convmem/config.toml` |
| Confirming the packet’s numerical claim and freeze framing | Updating model baselines or running live smoke tests |
| Verifying the packet is surfaced from `LATEST.md` | Any live state, corpus, or ingest mutation |

## Verification design

| Field | Answer |
|-------|--------|
| Independent oracle | The bakeoff numbers and freeze notes in `CODEX-2026-08-02-summarizer-switch-decision.md` |
| Failure-injection method | N/A; read-only review only |
| Negative control | Treat the packet as authorization to edit config; that must remain false |
| Dual-path coverage | Packet plus aligned handoff docs in `LATEST.md` and `CURSOR-2026-07-23-crush-qwen-stability-handoff.md` |

## V0 — Preconditions

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V0a | Subject tip resolves to the decision packet being verified | PASS |
| V0b | The packet frames the switch as Ryan-gated | PASS |
| V0c | The packet’s freeze analysis says the census is not corrupted by the model-name change | PASS |
| V0d | The packet remains read-only after being surfaced in `LATEST.md` | PASS |

## V1 — Decision consistency

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V1a | The 10-run metrics favor `qwen3.5:latest` over `llama3.1:8b` | PASS |
| V1b | The older 3-row fixture is too small to overturn the 30-row result | PASS |
| V1c | The packet’s prompt-level weakness caveat is preserved | PASS |

## V2 — Freeze safety

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V2a | No live `config.toml` edit is implied by the docs refresh | PASS |
| V2b | No baseline update or smoke command is presented as completed | PASS |
| V2c | The verify remains a draft until Ryan explicitly authorizes the switch | PASS |

## V3 — Independent sign-off

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V3a | Written verdict names the packet and the freeze boundary | PASS |
| V3b | Residual risk is limited to an un-applied model change | PASS |
| V3c | Closeout note makes the later grant boundary explicit | PASS |

## Evidence log

```text
VERIFY-summarizer-switch-decision — tip CODEX-2026-08-02-summarizer-switch-decision.md — runner Codex — 2026-08-03
V0: PASS
V1: PASS
V2: PASS
V3: PASS
Mechanical: PASS
Sign-off: Draft closeout only; Ryan still owns the actual config switch
```
