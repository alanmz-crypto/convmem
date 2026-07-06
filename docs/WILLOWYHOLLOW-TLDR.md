# Willowy Hollow + convmem — TLDR

**Session loop (full):** [`WILLOWYHOLLOW-SESSION-LOOP.md`](WILLOWYHOLLOW-SESSION-LOOP.md)  
**Guide:** [`WILLOWYHOLLOW-WEBDEV-GUIDE.md`](WILLOWYHOLLOW-WEBDEV-GUIDE.md)

---

## Every session (4 commands)

```bash
convmem doctor
convmem tldr
convmem brief --stdout-only
convmem unresolved --site staging2.willowyhollow.com
convmem "your question"
```

Cursor: *“Brief me for Willowy Hollow and what’s open on staging2.”*

---

## Full session loop (7 beats)

```text
OPEN practice  →  ORIENT (doctor/brief/unresolved)  →  ASK memory
WORK (repo scripts)  →  RECORD (you approve)  →  VERIFY  →  git close
```

Details: [`WILLOWYHOLLOW-SESSION-LOOP.md`](WILLOWYHOLLOW-SESSION-LOOP.md)

---

## Three places (don’t mix them)

| Where | For what |
|-------|----------|
| **convmem** | Memory — past decisions, open bugs, search |
| **Repo markdown** | Exact commands — `Deploy Workflow — willowyhollow.md`, `AGENTS.md` |
| **Terminal scripts** | Do the work — `stack_up`, `sync-practice-to-preview.sh`, git push |

---

## Environments

`practice :8081` → `preview :8080` → `git push staging` → **staging2**

---

## Search tips

| Topic | Command |
|-------|---------|
| Deploy / VT / scripts | `convmem "…"` **no** `--site` |
| Staging security | `convmem "…" --site staging2.willowyhollow.com` |
| Plain summary | `convmem ask "…"` |

---

## Cross-model handoff

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh   # Crush + Kiro + Codex + logs
```

Phrasebook: **ingest your chat** = session only · **index the log** = markdown · **ingest everything** = both. Handoff ≠ `record`.

---

```bash
convmem record -i
convmem record --approve-last   # you approve
```

---

## Footers

**── Next steps ──** after most commands. Mute: `CONVMEM_NO_NEXT_STEPS=1`

---

## Git deploy (theme only)

Preview first → copy `public_html/.../functions.php` → `willowyhollow-dev` staging → `git add` that file only → push.  
DB/pages: `push-practice-to-staging2.sh`, not git.
