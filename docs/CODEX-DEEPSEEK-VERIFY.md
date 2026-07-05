# Codex & DeepSeek — verification guide

**Purpose:** Independent checklist for Codex (shell + `AGENTS.md`) and DeepSeek (MCP read tools) to verify the synthesis + lab-reference + prod port work **without trusting prior chat claims**.

**Read first:** [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md)

**Report format:** For each section, state PASS / FAIL / SKIP and paste the one line of evidence (exit code, grep hit, or MCP field).

---

## 0. Capability tier

| Model | Tier | Can run |
|-------|------|---------|
| **Codex** | A (shell, no MCP by default) | All `bash` / `convmem` / `pytest` below |
| **DeepSeek** | B (MCP-only) | `brief()`, `search_fast()`, `ask()`, `related()`, `stats()` only |

DeepSeek: **SKIP** shell sections; use MCP + ask Ryan to paste shell output for FAIL items.

Codex: if `convmem ask` hits sandbox network error:

```bash
bash -lc 'convmem ask "test connectivity"'
```

In `~/Projects/convmem`: `cp .codex/config.toml.example .codex/config.toml` for persistent network.

---

## 1. Prod infra (both — DeepSeek via MCP)

### Codex

```bash
convmem doctor
echo "doctor exit: $?"
```

**PASS:** exit `0`, all checks `[PASS]`.

### DeepSeek

Call MCP **`brief()`** with `project=convmem` (or infer from cwd).

**PASS:** JSON/text returns; no connection error. Note `unresolved_count` (informational).

Call MCP **`stats()`** if available.

**PASS:** returns corpus stats without error.

---

## 2. Prod digest code shipped

### Codex (run from `~/Projects/convmem`)

```bash
cd ~/Projects/convmem
python -c "from cross_project_digest import load_attempts; print('load_attempts OK')"
python -m pytest tests/test_cross_project_digest.py tests/test_precheck_path.py -q
echo "pytest exit: $?"
```

**PASS:** import OK; pytest exit `0` (expect **13 passed** as of 2026-07-05).

```bash
grep -q "Do not retry" cross_project_digest.py && echo "PASS do-not-retry in digest"
grep -q "def load_attempts" cross_project_digest.py && echo "PASS load_attempts"
```

**PASS:** both greps print PASS.

### DeepSeek

MCP **`search_fast("load_attempts cross_project_digest Do not retry")`**

**PASS:** hits mention prod `cross_project_digest.py` / attempts / do-not-retry (indexed content).

MCP **`ask("Does prod cross_project_digest.py have load_attempts and a Do not retry section? Cite evidence.")`**

**PASS:** answer cites ledger or repo evidence; if corpus stale, **SKIP** and note "ask Ryan to run Codex section 2".

---

## 3. Prod smoke gate

### Codex

```bash
cd ~/Projects/convmem
bash scripts/smoke-cross-project-digest.sh
echo "smoke exit: $?"
```

**PASS:** exit `0`, final line `=== smoke-cross-project-digest: PASS ===`.

**Expected SKIP lines (OK):**

- `SKIP link queue` if `~/.local/share/convmem/link_queue.jsonl` empty
- `SKIP Do not retry` if no `attempts.jsonl` yet

### DeepSeek

Ask Ryan to run section 3 and paste tail, **or** MCP **`ask("What is the prod cross-project digest smoke script and expected PASS line?")`**

---

## 4. Prod docs & protocol

### Codex

```bash
test -f ~/Projects/convmem/docs/MODEL-WORKFLOW.md && echo "PASS MODEL-WORKFLOW"
test -f ~/Projects/convmem/docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md && echo "PASS ATTEMPTS doc"
test -f ~/Projects/convmem/config/attempts.jsonl.example && echo "PASS example"
grep -q "WORKFLOW_ROUTING_START" ~/Projects/convmem/config/agent-protocol.md && echo "PASS protocol routing"
grep -q "smoke-cross-project-digest" ~/Projects/convmem/SYNTHESIS-STATUS.md && echo "PASS SYNTHESIS-STATUS"
```

**PASS:** all five lines print PASS.

```bash
grep -q "Workflow routing" ~/.codex/AGENTS.md 2>/dev/null || \
grep -q "Workflow routing" ~/Projects/convmem/config/codex-agents-convmem.example.md
echo "codex workflow in AGENTS: $?"
```

**PASS:** grep finds "Workflow routing" (deployed `~/.codex/AGENTS.md` or repo example).

### DeepSeek

MCP **`search_fast("MODEL-WORKFLOW CROSS-PROJECT-DIGEST-ATTEMPTS")`**

**PASS:** both docs appear in hits.

---

## 5. Lab track (Codex only — DeepSeek SKIP)

```bash
cd ~/Projects/convmem-lab
bash scripts/verify-lab-reference.sh
echo "verify-lab-reference exit: $?"
python -m pytest tests/test_lab_reference.py tests/test_cross_project_digest.py tests/test_precheck_path.py -q
echo "lab pytest exit: $?"
bash lab/scripts/smoke-synthesis.sh
echo "lab smoke exit: $?"
```

**PASS:**

- `verify-lab-reference: PASS`
- lab pytest exit `0` (expect **24 passed**)
- `=== smoke-synthesis: PASS ===`

```bash
grep -q "Reference routing" ~/Projects/convmem-lab/docs/LAB.md && echo "PASS lab routing doc"
test -f ~/Projects/convmem-lab/docs/lab-reference/NOTES.md && echo "PASS lab NOTES"
```

---

## 6. Isolation (prod must not read lab data)

### Codex

```bash
# Prod digest smoke must write under prod only
ls -t ~/.local/share/convmem/digests/smoke-*.md 2>/dev/null | head -1
# Should be under convmem not convmem-lab

# Lab not in MCP (informational — may SKIP if no crush.json)
grep -l "convmem-lab" ~/.cursor/mcp.json ~/.config/crush/crush.json 2>/dev/null && echo "FAIL lab in MCP" || echo "PASS lab not in MCP"
```

**PASS:** latest smoke digest under `~/.local/share/convmem/digests/`; no `convmem-lab` in MCP configs.

---

## 7. End-to-end digest sample (Codex)

```bash
cd ~/Projects/convmem
~/Projects/convmem/scripts/cross-project-digest.sh --skip-ask -o /tmp/codex-verify-digest.md
for h in "Corpus snapshot" "Recent approved decisions" "Open coordination observations"; do
  grep -q "$h" /tmp/codex-verify-digest.md && echo "OK $h" || echo "MISSING $h"
done
grep "staging2.willowyhollow.com" /tmp/codex-verify-digest.md && echo "WARN client leak" || echo "OK default lane"
```

**PASS:** three OK lines; default lane OK (no client hostname unless `--site` used).

**Note:** `-o` is forwarded by `cross-project-digest.sh` to `cross_project_digest.py`. Fallback if wrapper is stale: `python cross_project_digest.py --skip-ask -o /tmp/codex-verify-digest.md`.

---

## 8. DeepSeek synthesis spot-check (optional)

MCP **`ask("Summarize cross-project digest Phase 0 status and whether load_attempts shipped to prod. Cite ledger ids.")`**

**PASS:** grounded answer with `dec_prop_*` or doc citations; mentions Phase 0 complete and attempts port if indexed.

**FAIL:** hallucinated features not in search hits — retry **`search_fast`** first.

---

## 9. Failure triage

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| doctor fails | Ollama/Chroma down | `convmem doctor` output; restart Ollama |
| pytest import error | wrong cwd / env | `cd ~/Projects/convmem`; use project venv |
| smoke missing link queue | empty `link_queue.jsonl` | SKIP OK; add rows if testing link section |
| smoke missing do-not-retry | no `attempts.jsonl` | `cp config/attempts.jsonl.example ~/.local/share/convmem/attempts.jsonl` |
| Codex ask network error | sandbox | `bash -lc` or `.codex/config.toml` |
| DeepSeek can't verify shell | MCP-only | Codex runs section; DeepSeek reviews pasted output |
| Workflow routing missing in Cursor | stale deploy | `bash scripts/generate-agent-protocol.sh && bash scripts/deploy-agent-protocol.sh` |

---

## 10. Sign-off template

Paste when done:

```markdown
## Verification — Codex|DeepSeek — YYYY-MM-DD

- [ ] 1 Infra: doctor/brief PASS
- [ ] 2 Prod code: load_attempts + pytest 13 passed
- [ ] 3 Prod smoke: smoke-cross-project-digest PASS
- [ ] 4 Docs: MODEL-WORKFLOW + ATTEMPTS + protocol routing
- [ ] 5 Lab (Codex): verify-lab-reference + smoke-synthesis PASS
- [ ] 6 Isolation: lab not in MCP; prod digests under prod path
- [ ] 7 Sample digest headings OK

Blockers: (none | …)
```

### Completed — 2026-07-05

**DeepSeek (MCP):** sections 0, 2, 4, 8 PASS; shell sections SKIP per tier.

**Codex (shell):** sections 1, 3, 4, 5, 6, 7 PASS.

- Prod smoke: `Do not retry` now **PASS** after `attempts.jsonl` seeded from example (edit rows for real obs_ids).
- Section 7: `cross-project-digest.sh -o` forwarded (wrapper fix 2026-07-05).

---

## Related

- [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md) — what to run when
- [`CROSS-PROJECT-DIGEST-ATTEMPTS.md`](CROSS-PROJECT-DIGEST-ATTEMPTS.md) — attempts schema
- [`../SYNTHESIS-STATUS.md`](../SYNTHESIS-STATUS.md) — phase gates
- Lab: `~/Projects/convmem-lab/docs/lab-reference/NOTES.md`
