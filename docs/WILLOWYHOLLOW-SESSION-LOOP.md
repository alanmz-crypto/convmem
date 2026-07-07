# Willowy Hollow — session loop (Steps 1–10)

**TLDR:** [`WILLOWYHOLLOW-TLDR.md`](WILLOWYHOLLOW-TLDR.md)  
**Full guide:** [`WILLOWYHOLLOW-WEBDEV-GUIDE.md`](WILLOWYHOLLOW-WEBDEV-GUIDE.md)  
**Promotion gates:** [`site-reference/NOTES.md`](site-reference/NOTES.md)

One checklist for every sit-down in `willowyhollow-practice`. convmem handles **memory**; repo markdown and scripts handle **execution**.

---

## 1. Open the right place

- Cursor workspace: `~/WordPress/willowyhollow-practice`
- MCP **convmem** enabled in Cursor

---

## 2. Orient (~2 minutes)

```bash
convmem tldr                    # optional one-page reminder
convmem doctor                  # must exit 0
convmem brief --stdout-only
convmem unresolved --site staging2.willowyhollow.com
```

Each command may print **── Next steps ──** at the bottom — read it.

**Cursor instead of terminal:** *“Brief me for Willowy Hollow and what’s open on staging2.”*

---

## 3. Ask memory before you guess

| You need… | Run… |
|-----------|------|
| Quick source hits | `convmem "deploy VT staging2"` |
| Plain-English summary | `convmem ask "…"` |
| Staging security context | add `--site staging2.willowyhollow.com` |

**Deploy / VT / scripts** — usually **no** `--site`.  
**CSP / HSTS / monitor** — use `--site staging2.willowyhollow.com`.

If memory is thin or empty → read **`Deploy Workflow — willowyhollow.md`** and **`AGENTS.md`** in the practice repo (step-by-step commands live there).

---

## 4. Do the web work (convmem stays out of the way)

```bash
cd ~/WordPress/willowyhollow-practice
source scripts/stack.sh && stack_up          # practice :8081
# edit, wp eval-file install scripts, test in browser
scripts/sync-practice-to-preview.sh        # validate on :8080
```

**Theme-only to staging2 (git):**

```bash
cd ~/GitClones/willowyhollow-dev
git checkout staging && git pull origin staging
cp ~/WordPress/willowyhollow-practice/public_html/wp-content/themes/astra-child/functions.php \
   wp-content/themes/astra-child/
git diff wp-content/themes/astra-child/functions.php
git add wp-content/themes/astra-child/functions.php
git commit -m "VT: describe change"
git push origin staging
```

**DB / pages / full tree:** `scripts/push-practice-to-staging2.sh` — not git.

Details: **`Deploy Workflow — willowyhollow.md`**.

---

## 4b. Pre-promote gates (before staging2 or production)

Read [`site-reference/NOTES.md`](site-reference/NOTES.md) — all three gates are **blocking**:

| Gate | Slice | Quick check |
|------|-------|-------------|
| URL identity | [`site-address-consistency.md`](site-reference/site-address-consistency.md) | `stack_wp option get siteurl` / `home` |
| PHP parity | [`php-version-parity.md`](site-reference/php-version-parity.md) | `php -v` or `stack_wp eval 'echo PHP_VERSION;'` on source + target |
| Fresh backup | [`backup-before-write-gate.md`](site-reference/backup-before-write-gate.md) | `ls -lhtr ~/WordPress/willowyhollow/backups/` + `gunzip -t` |

Mismatch on any gate → do not promote; fix or flag the test as unverified.

---

## 5. Save what you learned (you approve)

Only when something should survive for future sessions:

```bash
convmem record -i
# relates_to: search for dec_prop_… or obs_… first
convmem record --approve-last
```

Use `--site staging2.willowyhollow.com` or `practice-local` when recording site-specific facts.

Agents may draft the block; **you** run `--approve-last`.

---

## 5b. Cross-model handoff (Crush → Codex → Kiro)

When switching models mid-sprint — **not** the same as `record` (that's one signed conclusion at the end).

| Ryan says | What runs |
|-----------|-----------|
| **Ingest your chat** | Track A — session transcript only |
| **Index the log** | Track B — findings/audit markdown |
| **Ingest everything** / **full handoff** | A then B |

**One command (Willowy Hollow bug sprint):**

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

That indexes Crush `.crush/crush.db`, latest Kiro `messages.jsonl`, latest Codex `rollout-*.jsonl` (full chat — not `history.jsonl`), plus synced findings + audit into `docs/inter-model/`.

**Tell the next model:** *“Search convmem for finding N”* — not *“read what you wrote”* (that skips chat).

**Team charter (full):** [`TEAM-CHARTER-2026-07-06.md`](inter-model/TEAM-CHARTER-2026-07-06.md) — lane names, not model weights. Say **Crush found it**, not "DeepSeek found it."

**Bug sprint evidence:** [`BUG-SPRINT-SUCCESS-2026-07-06.md`](inter-model/BUG-SPRINT-SUCCESS-2026-07-06.md) — five checks; score at sprint end to unlock Tier 1.5 gate.

**Tier 2 habit:** 3 consecutive clean handoffs (Track A + B, no wrong record offers) — checklist in TEAM-CHARTER doc §7.

---

## 6. Verify memory stuck

```bash
convmem "short phrase from your record"
convmem brief --stdout-only    # optional
```

---

## 7. Close

- Git commit in **practice** / **willowyhollow-dev** as usual (separate from convmem).
- No convmem “close” command — orientation ritual is read-only unless you recorded.

---

## One-card summary

```text
OPEN    → willowyhollow-practice + MCP convmem
ORIENT  → tldr / doctor / brief / unresolved --site staging2…
ASK     → convmem "…" or ask "…"
WORK    → stack_up → edit → sync-practice-to-preview → git or push script
RECORD  → record -i → you: record --approve-last
VERIFY  → convmem "…"
CLOSE   → git in WP repos
```

---

## What “good” looks like

- `doctor` passes at session start
- You know staging2 open issues **before** changing code
- Deploy commands from **repo docs**; decisions and history from **convmem**
- One approved `record` when something actually mattered — not every chat

---

## Mute footers

```bash
CONVMEM_NO_NEXT_STEPS=1 convmem doctor
```

---

**Related:** [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md) (convmem repo), [`AGENTS.md`](../../WordPress/willowyhollow-practice/AGENTS.md) (practice repo).
