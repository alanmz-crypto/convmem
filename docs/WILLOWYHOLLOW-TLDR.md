# Willowy Hollow + convmem — TLDR

**Full guide:** [`WILLOWYHOLLOW-WEBDEV-GUIDE.md`](WILLOWYHOLLOW-WEBDEV-GUIDE.md)

---

## Every session (4 commands)

```bash
convmem doctor
convmem tldr                   # one-page cheat sheet (auto lane)
convmem brief --stdout-only
convmem unresolved --site staging2.willowyhollow.com
convmem "your question"
```

Cursor: *“Brief me for Willowy Hollow and what’s open on staging2.”*

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

## Save a win

```bash
convmem record -i
convmem record --approve-last   # you approve
```

---

## After each command

Look for **── Next steps ──** at the bottom.  
Mute: `CONVMEM_NO_NEXT_STEPS=1`

---

## Git deploy (theme only)

Preview first → copy `public_html/.../functions.php` → `willowyhollow-dev` staging branch → `git add` that file only → push.  
DB/pages: use `push-practice-to-staging2.sh`, not git.
