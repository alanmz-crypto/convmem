# Verify Plan — residual-tool-output

```
Planning Status

Phase:        Verify complete — Ryan GATE (docs review)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** Execute land [#102](https://github.com/alanmz-crypto/convmem/pull/102) squash-merged to `main` as [`482637b`](https://github.com/alanmz-crypto/convmem/commit/482637b7bf3bfe82eba6007ad8fdf09eeae4ce43) (2026-07-23). This PR is Task 2 soak paperwork only.  
**PR(s):** [#102](https://github.com/alanmz-crypto/convmem/pull/102) (Execute); this docs PR (Task 2 close)  
**EXECUTION / ARCHITECTURE:** [EXECUTION-2026-07-22-residual-tool-output.md](EXECUTION-2026-07-22-residual-tool-output.md), [ARCHITECTURE-residual-tool-output.md](ARCHITECTURE-residual-tool-output.md)  
**Goal:** Record Task 0–2 results after Crush soak; Task 3 skipped.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
BugBot-only V0 rows may use **N/A (exempt)** when Execute recorded a valid
exemption and reason. An applicable SHA mismatch is always **FAIL**, never SKIP.

**GATE** = Ryan process step; not a mechanical agent PASS.

---

## Human consequence (read this first)

Crush was still billing you ~100k prompt tokens per heavy session after Stage 4
made standing rules small. Most of that was tool dumps re-charged every later turn.
We shipped a thin always-on Crush rule that keeps bash/view/grep output short
(without hiding failures), then ran three real post-restart soaks.

**Consequence for you:** routine Crush digs in this soak landed around **~30k**
prompt tokens instead of the old **~100k** band — cheaper sessions if agents
follow the rule. We did **not** open a second MCP-clipping project (Task 3),
because the mean was already well under ~90k.

**Honest limit:** the three soaks were short guided work, not 150-message audits.
Do not treat “~70% cheaper” as proven on equal-weight Crush days. Treat it as:
post-land, this class of work is no longer stuck in the residual ~100k band.

### 5 Ws

| | |
|---|---|
| **Who** | Cursor Execute + VERIFY; Crush/`deepseek-v4-flash` soak; Ryan GATE on this paperwork |
| **What** | Close the Crush tool-output residual arc with measured soak numbers |
| **When** | Rule landed [#102](https://github.com/alanmz-crypto/convmem/pull/102) 2026-07-23; soak same afternoon |
| **Why** | Standing-context cuts were not enough — your Crush bill was still tool-history rebill |
| **How** | Always-loaded `tool-output-hygiene` + three measured sessions; MCP clips skipped |

**TL;DR:** Rule shipped; three soaks mean ~30.5k vs ~100k residual; Task 3 skipped; equal-weight caveat stands; Stage 4 stays closed.

### Merge reading

- [ARCHITECTURE-residual-tool-output.md](ARCHITECTURE-residual-tool-output.md)
- [EXECUTION-2026-07-22-residual-tool-output.md](EXECUTION-2026-07-22-residual-tool-output.md)
- This VERIFY (human block above + V3 soak table)
- [LATEST Active handoff — Crush tool-output residual](../inter-model/LATEST.md)
- Execute land: [#102](https://github.com/alanmz-crypto/convmem/pull/102) (`482637b`)

---

## Scope lock

| In scope | Out of scope |
|---|---|
| Crush tool-hygiene rule + deploy wiring | Stage 4 digest reopen |
| Task 0 baseline honesty | Next semantic-dedupe bands |
| Task 2 measure vs ~98–107k Post 1–3 | R2b live capture; MCP clips (Task 3 skipped) |

---

## External Review (Execute record)

| Field | Value |
|---|---|
| `gate_applicability` | `required` on Execute [#102](https://github.com/alanmz-crypto/convmem/pull/102); **`exempt`** on this Task 2 docs PR |
| `reason` (Execute) | Changed `scripts/deploy-agent-protocol.sh` and always-loaded Crush rules |
| `reason` (this PR) | Plans / LATEST status only — no runtime or deploy script change |
| `subject_tip_sha` | Execute product tip at BugBot: `edb96ba7fda16476da7e3b35f0467449c7ae7caf` |
| `bugbot_reviewed_sha` | `edb96ba7fda16476da7e3b35f0467449c7ae7caf` (GitHub `Cursor Bugbot` SUCCESS) |
| Steward | `skip` for this docs PR — Ryan will review after merge |

---

## V0 — Planning / tip identity

| ID | Check | Result |
|---|---|---|
| V0a | ARCHITECTURE accepted on main (#100 / #101) before Execute | PASS — `9f89cd0` on main |
| V0b | Execute landed on main | PASS — [#102](https://github.com/alanmz-crypto/convmem/pull/102) → `482637b` |
| V0c | BugBot-reviewed SHA equals subject tip when required | PASS — both `edb96ba` on Execute tip |

---

## V1 — Task 0 baseline

| ID | Check | Result |
|---|---|---|
| V1a | `disable_auto_summarize` not set in `~/.config/crush/crush.json` | PASS — key absent in options (2026-07-22) |
| V1b | Standing context ~6k token class (~23KB) | PASS — 22085 bytes rules+globals ≈ 5521 tokens (bytes/4) |
| V1c | Comparison baseline frozen | PASS — Stage 4 Post 1–3 mean ~103.5k prompt (band ~98–107k) |

---

## V2 — Task 1 rule + deploy

| ID | Check | Result |
|---|---|---|
| V2a | Example `config/crush-rules-tool-output-hygiene.example.md` exists with failure exception | PASS — failure exception + ranged-read guidance in example |
| V2b | `deploy-agent-protocol.sh` copies it to `tool-output-hygiene.md` | PASS — wired beside commit-pr-quality |
| V2c | After deploy: file present under `~/.config/crush/rules/`; Crush restart noted | PASS — live file present; Crush restarted 2026-07-23 ~13:14 before soak |

---

## V3 — Task 2 measure

Post-restart soak sessions in `~/Projects/convmem/.crush/crush.db` (model `deepseek-v4-flash`):

| Session id (prefix) | Title | `prompt_tokens` | Messages |
|---|---|---:|---:|
| `d457a7fb` | Convmem project deployment steps and checks | 27,497 | 14 |
| `aa8132b0` | Verify Task 2 residual tool-output | 37,587 | 37 |
| `7d523238` | Deploy-agent-protocol Crush rule installation analysis | 26,561 | 12 |

**Mean `prompt_tokens`:** ~30,548  
**Baseline:** Stage 4 Post 1–3 ~103.5k (band ~98–107k); pre-hygiene heavy trio mean ~115,926

| ID | Check | Result |
|---|---|---|
| V3a | ≥3 Crush / deepseek-v4-flash sessions after rule deploy + Crush restart | PASS — three finished soaks above (2026-07-23) |
| V3b | Mean `prompt_tokens` compared to ~98–107k band | PASS *for this soak class* — mean ~30.5k ≪ band |
| V3c | Task 3 MCP clips opened only if mean still ≳90k and MCP dumps implicated | SKIP — mean not ≳90k; no MCP-clip open |

**Caveat (do not over-claim):** soak sessions were short guided digs, not 150-message audits. This does **not** prove hygiene alone cut ~70% on equal-weight work. It does show post-land routine tool-using sessions are no longer sitting in the ~100k residual band.

**Pre-deploy snapshot (unchanged):** heavy pre-hygiene sessions still showed ~50k–120k (e.g. 103137, 119653).

---

## Mechanical summary

| Area | PASS/FAIL/SKIP |
|---|---|
| Task 0 | PASS |
| Task 1 | PASS (rule + deploy; live on Crush) |
| Task 2 | PASS (soak class; equal-weight caveat above) |
| Task 3 | SKIP |
| BugBot (Execute #102) | PASS at `edb96ba` |
| BugBot (this docs PR) | N/A (exempt) |

**Ryan GATE:** review this paperwork after merge; Stage 4 stays CLOSED.
