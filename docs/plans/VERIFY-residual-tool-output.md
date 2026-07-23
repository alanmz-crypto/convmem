# Verify Plan — residual-tool-output

```
Planning Status

Phase:        Verify (residual-tool-output)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off optional); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `feat/2026-07-22-residual-tool-output-execute` (update SHA at PR open)  
**PR(s):** (pending)  
**EXECUTION / ARCHITECTURE:** [EXECUTION-2026-07-22-residual-tool-output.md](EXECUTION-2026-07-22-residual-tool-output.md), [ARCHITECTURE-residual-tool-output.md](ARCHITECTURE-residual-tool-output.md)  
**Goal:** Prove Task 0–1 landed; Task 2 measurement either recorded or explicitly pending Crush sessions after deploy/restart.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
BugBot-only V0 rows may use **N/A (exempt)** when Execute recorded a valid
exemption and reason. An applicable SHA mismatch is always **FAIL**, never SKIP.

**GATE** = Ryan process step; not a mechanical agent PASS.

---

## Scope lock

| In scope | Out of scope |
|---|---|
| Crush tool-hygiene rule + deploy wiring | Stage 4 digest reopen |
| Task 0 baseline honesty | Next semantic-dedupe bands |
| Task 2 measure vs ~98–107k Post 1–3 | R2b live capture; MCP clips unless Task 2 fails |

---

## External Review (Execute record)

| Field | Value |
|---|---|
| `gate_applicability` | `required` (deploy script + runtime-affecting Crush rule path) |
| `reason` | Changes `scripts/deploy-agent-protocol.sh` and always-loaded Crush rules behavior |
| `subject_tip_sha` | (fill at PR tip) |
| `bugbot_reviewed_sha` | (fill after BugBot run) |
| Steward | `offer` — bounded PR lifecycle; Ryan may self-drive Cursor |

---

## V0 — Planning / tip identity

| ID | Check | Result |
|---|---|---|
| V0a | ARCHITECTURE accepted on main (#100 / #101) before Execute | PASS — `9f89cd0` on main |
| V0b | Subject tip is this Execute branch / PR tip | (fill) |
| V0c | BugBot-reviewed SHA equals subject tip when required | (fill after BugBot) |

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
| V2c | After deploy: file present under `~/.config/crush/rules/`; Crush restart noted | PASS file live (`~/.config/crush/rules/tool-output-hygiene.md`); **Crush restart still required** for process load |

---

## V3 — Task 2 measure

| ID | Check | Result |
|---|---|---|
| V3a | ≥3 comparable Crush / deepseek-v4-flash sessions after rule deploy + Crush restart | PENDING — needs post-deploy sessions |
| V3b | Mean `prompt_tokens` compared to ~98–107k band | PENDING |
| V3c | Task 3 MCP clips opened only if mean still ≳90k and MCP dumps implicated | SKIP unless V3b fails |

**Pre-deploy snapshot (not Task 2 PASS):** recent `convmem/.crush/crush.db` sessions still show ~50k–120k prompt (e.g. 103137, 119653) — confirms residual still live before hygiene.

---

## Mechanical summary

| Area | PASS/FAIL/PENDING |
|---|---|
| Task 0 | PASS |
| Task 1 | (fill at tip) |
| Task 2 | PENDING Crush sessions |
| BugBot | (fill) |

**Ryan GATE:** after Task 2 numbers, or accept Task 1 land with Task 2 as follow-up soak.
