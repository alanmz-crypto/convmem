# convmem for Willowy Hollow web development

**TLDR:** [`WILLOWYHOLLOW-TLDR.md`](WILLOWYHOLLOW-TLDR.md)  
**Full guide:** this file

---

## What convmem is (one paragraph)

convmem is your **local memory for AI-assisted work**. It indexes past chat sessions and records **decisions you approve** (CSP must use SiteGround Site Tools, page IDs differ per environment, etc.). When you open Cursor and ask “how did we deploy VT to staging2?”, it searches that memory instead of guessing.

It does **not** replace git, backups, or WordPress. It helps **you and agents remember** what already happened.

---

## Your four commands (bookmark these)

Run from any terminal when working on Willowy Hollow:

```bash
convmem doctor                    # infra OK? must exit 0
convmem brief --stdout-only       # what's open, recent decisions
convmem unresolved --site staging2.willowyhollow.com   # staging security queue
convmem "your question"           # search past work (add --site when filtering)
```

In Cursor with MCP: call **`brief()`** first, then **`search_fast()`** / **`ask()`** before history questions.

---

## Site tags (important)

| When you mean… | Use `--site` |
|----------------|--------------|
| Staging server issues (CSP, HSTS, monitor) | `staging2.willowyhollow.com` |
| Production (when recorded) | `willowyhollow.com` |
| Local Docker practice stack facts | tag records with `site: practice-local` on **`convmem record`** — search may need **no** `--site` or plain query |

**Gotcha:** `--site` filters strictly. Deploy / VT / “how do I run sync script” questions often work **better without** `--site` because those facts live in general chat memory, not under the staging hostname tag.

---

## What convmem already knows about Willowy Hollow

From indexed sessions and approved decisions:

- **CSP / security headers on staging2** — must use SiteGround Site Tools or `.htaccess` `mod_headers`; no user nginx on shared hosting ([decision `dec_prop_20260623_153615_a66c`])
- **Root `.htaccess` in deploy repo** had no CSP rules at audit time
- **View Transitions** — practice stack on `:8081`, install scripts, `functions.php` sync pattern (from Continue/Cursor sessions)
- **6 open monitor observations** on staging2 (CSP, HSTS, Referrer-Policy) — run `convmem unresolved --site staging2.willowyhollow.com`

---

## What convmem does *not* know yet (gaps)

These files are in **`~/WordPress/willowyhollow-practice/`** but are **not** in the search index unless you add them:

| File | Contents |
|------|----------|
| `Deploy Workflow — willowyhollow.md` | practice → preview → staging2 steps |
| `Circular Deploy — practice ↔ staging2 ↔ production.md` | Full promotion loop |
| `AGENTS.md` | Stack commands, VT architecture, gotchas |

**Until indexed:** read those files directly for procedures; use convmem for **decisions, security context, and past debugging**.

---

## Recording something you want future agents to remember

When you or an agent finishes a useful decision (deploy path confirmed, page ID map updated, CSP rule that worked):

```bash
convmem record -i
# fill: relates-to (search for obs_… or dec_prop_… first)
convmem record --approve-last
```

For Willowy Hollow facts, set **`site:`** to the hostname (`staging2.willowyhollow.com`) or `practice-local` for Docker-only notes.

Agents propose; **you approve** — nothing durable is written without `record --approve-last`.

---

## Environments cheat sheet

| Surface | URL | Repo / dir |
|---------|-----|------------|
| Practice | http://localhost:8081 | `~/WordPress/willowyhollow-practice` |
| Preview | http://localhost:8080 | `~/WordPress/willowyhollow` |
| Staging2 | https://staging2.willowyhollow.com | deploy via `~/GitClones/willowyhollow-dev` (staging branch) |

Promotion: **practice → preview → git push staging → staging2 auto-deploy**

---

## Making convmem more helpful (next steps)

1. **Index Willowy Hollow deploy markdown** into Chroma (searchable deploy steps) — convmem feature / script
2. **Fix staging2 security headers** — clears 6 unresolved obs; real site improvement
3. **Cursor workspace** — open `willowyhollow-practice`; ensure MCP **convmem** enabled; agents read `AGENTS.md` + this guide
4. **Record deploy wins** — each time a promotion path works, one `record` block so ask() cites it next time

**Disable hints:** `CONVMEM_NO_NEXT_STEPS=1 convmem doctor`

After most commands you'll see **── Next steps ──** with suggested follow-ups (cwd-aware in `willowyhollow-practice`).

---

```bash
convmem "staging2 CSP SiteGround htaccess"
convmem "view transition functions.php practice staging"
convmem ask "What security headers are still open on staging2?" --site staging2.willowyhollow.com
convmem unresolved --site staging2.willowyhollow.com
```

---

**Related:** [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md) (convmem repo), [`AGENTS.md`](../../WordPress/willowyhollow-practice/AGENTS.md) (practice repo).
