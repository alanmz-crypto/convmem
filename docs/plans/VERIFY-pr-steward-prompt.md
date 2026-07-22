# Verify Plan — PR Steward Prompt

```
Planning Status

Phase:        Verify (pr-steward-prompt)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Crush (mechanical); Kiro or Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust chat claims alone
```

**Subject / tip (immutable):** branch `docs/2026-07-22-2026-07-22-pr-steward-prompt`  
**PR(s):** [#92](https://github.com/alanmz-crypto/convmem/pull/92) — MERGED (squash) as `0e2b396` on `main` (2026-07-22)  
**EXECUTION:** Crush session 2026-07-22 — two-commit change adding prompt mechanisms for PR Steward  
**Goal:** Prove the PR Steward prompt changes are correct, complete, and cause no regressions.

**Deferred residual (Docs / Tech Writer — not blocking):** V0b and the EXECUTION blurb still say “2 commits” / “two-commit.” Pre-squash tip reality was **3** commits (product pair + this VERIFY doc). Correct metadata to `3` in a later tiny docs PR. Parked in [`../inter-model/LATEST.md`](../inter-model/LATEST.md) Active handoff (2026-07-22).

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** Complete **V0–V4** → Mechanical PASS|FAIL → independent sign-off → Ryan GATE.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| `config/agent-protocol.md` TEAM_CHARTER Steward line | Live deploy via `deploy-agent-protocol.sh` |
| `docs/standing-checks-register.json` new check entry | Changing Steward role boundaries or mutation allowlist |
| `docs/role-charters.md` Platform register_refs | Other charter cards or standing checks |
| Six generated `.example` surfaces consistency with canonical | Editing generated surfaces by hand |
| `convmem doctor` no regressions | PR Steward activation/assignment mechanics |
| Charter-register-consistency probe passes | Live corpus mutation |

---

## V0 — Preconditions and immutable subject

```bash
cd /home/lauer/Projects/convmem
git fetch origin
git checkout docs/2026-07-22-2026-07-22-pr-steward-prompt
git rev-parse HEAD
git log --oneline origin/main..HEAD
convmem doctor
```

| ID | Check | PASS |
|----|-------|------|
| V0a | Branch exists and is fetchable | … |
| V0b | Exactly 2 commits diverged from main | … |
| V0c | `convmem doctor` exit 0 (1 non-fatal embed warning expected) | … |
| V0d | `standing_register` shows `12 open checks, 0 due` (no orphan rows) | … |
| V0e | No dirty tracked files | … |

---

## V1 — Agent protocol prompt line

```bash
git show HEAD:config/agent-protocol.md | head -220 | tail -10
```

| ID | Check | PASS |
|----|-------|------|
| V1a | Line 213 contains the full Steward prompt line: "If Ryan describes a bounded, well-defined task that fits the PR lifecycle, suggest assigning PR Steward — it activates only through explicit Ryan assignment and never self-assigns." | … |
| V1b | The Steward routing table row (`Bound brief → GitHub PR lifecycle \| PR Steward \| Not involved`) is unchanged | … |
| V1c | The `<!-- TEAM_CHARTER_END -->` marker still immediately follows the Sol-High non-example block (no content injected into the structural boundary) | … |

---

## V2 — Standing check registration

```bash
python3 -c "
import json
with open('docs/standing-checks-register.json') as f:
    data = json.load(f)
check = [c for c in data['checks'] if c['id'] == 'pr-steward-reminder']
assert len(check) == 1, f'Expected 1, found {len(check)}'
c = check[0]
for field, expected in [
    ('check', 'consider PR Steward for bounded PR lifecycle tasks'),
    ('role', 'Platform'),
    ('status', 'open'),
    ('last_verified', '2026-07-22'),
]:
    assert c[field] == expected, f'{field}: expected {expected!r}, got {c[field]!r}'
assert c['trigger']['type'] == 'manual', f'trigger type: {c[\"trigger\"][\"type\"]}'
assert c['trigger']['max_age_days'] == 30, f'max_age_days: {c[\"trigger\"][\"max_age_days\"]}'
assert 'TEAM-CHARTER-2026-07-06.md' in c['notes'], 'notes missing charter ref'
print('PASS — all fields match')
"
```

| ID | Check | PASS |
|----|-------|------|
| V2a | `pr-steward-reminder` entry exists exactly once | … |
| V2b | `role: Platform`, `status: open`, `trigger.type: manual`, `max_age_days: 30` | … |
| V2c | `last_verified: 2026-07-22` | … |
| V2d | Notes reference `TEAM-CHARTER-2026-07-06.md § PR Steward` | … |

---

## V3 — Charter-register consistency

```bash
# Verify Platform register_refs includes pr-steward-reminder
git show HEAD:docs/role-charters.md | grep 'register_refs:.*Platform\|pr-steward-reminder'
# Verify Platform "Register:" line includes pr-steward-reminder
git show HEAD:docs/role-charters.md | grep -A1 'Register:.*ksweep-sunset\|pr-steward-reminder' | head -5
```

| ID | Check | PASS |
|----|-------|------|
| V3a | Platform `register_refs` includes `pr-steward-reminder` | … |
| V3b | Platform "Register:" prose line lists `pr-steward-reminder` with description | … |
| V3c | `standing_register` doctor check is PASS (0 due, no orphans) | … |

---

## V4 — Generated surfaces consistency

```bash
for f in \
  config/agent-protocol-mcp.txt \
  config/codex-agents-convmem.example.md \
  config/crush-rules-convmem.example.md \
  config/cursor-rules-convmem.mdc.example \
  config/kiro-steering-convmem.example.md
do
  echo "=== $f ==="
  git show HEAD:"$f" | grep -c "suggest assigning PR Steward"
done
```

| ID | Check | PASS |
|----|-------|------|
| V4a | `config/agent-protocol-mcp.txt` contains the prompt line | … |
| V4b | `config/codex-agents-convmem.example.md` contains the prompt line | … |
| V4c | `config/cursor-rules-convmem.mdc.example` contains the prompt line | … |
| V4d | `config/kiro-steering-convmem.example.md` contains the prompt line | … |
| V4e | `config/crush-rules-convmem.example.md` contains the prompt line | … |
| V4f | `config/agent-protocol-mcp-shell.txt` does NOT contain the prompt line (MCP-shell surface only carries `MCP_AFTER_TIER_A`, not TEAM_CHARTER) | … |
| V4g | No generated surface edited by hand — all carry identical Steward text | … |

---

## V5 — Independent sign-off and Ryan GATE

| ID | Check | PASS |
|----|-------|------|
| V5a | Same-tip independent PASS/FAIL written (see slot below) | … |
| V5b | Independent verifier performs no cleanup or correction | … |
| V5c | Crush does not self-sign / merge / record | … |

### Independent sign-off slot

```text
Lane: <signing lane>
Tip: <git rev-parse HEAD on docs/2026-07-22-2026-07-22-pr-steward-prompt>
Verdict: <PASS|FAIL>
Rationale: <one-line summary of what was checked and why it passes>
Residuals: <any non-blocking issues noted>
Date (ISO-8601): <YYYY-MM-DD>
```

---

## Evidence log

```text
VERIFY-pr-steward-prompt — tip <sha> — runner <lane> — <ISO-8601>
V0: …
V1: …
V2: …
V3: …
V4: …
Mechanical: PASS|FAIL
Sign-off: …
```
