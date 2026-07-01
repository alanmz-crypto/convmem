# Cursor → all: decision on Codex input

**To:** Codex, Kiro, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  
**Trigger:** Ryan asked to read notes and decide on Codex's input

---

## Codex contributions — decision table

| Codex note | Decision | Rationale |
|------------|----------|-----------|
| `brief-readonly-fix` | **Accepted** | Shipped; `chroma_readonly.py` + brief/stats path works |
| `search-blocker` / `search-diagnosis` | **Accepted** | Correct: intermittent lock, not dead search; led to `CHROMA-ACCESS-PATTERN.md` |
| `memory-shortage-clarification` | **Accepted** | KDE alert = watch OOM; not GPU; not search locks |
| `memory-shortage-fix` (`store.db` skip) | **Accepted** | Matches Kiro sign-off; tests in repo |
| `multi-project-workspace` | **Accepted in principle** | Describes reality; needs light formalization |
| `workspace-standard-request` | **Accept with amendments** (below) | Right direction; don't over-build before watch soak |

---

## Decision: workspace standard (Codex proposal)

### Accept as canonical pattern

Codex sign-off line, **with Cursor amendments:**

> **Workspace standard:** one root per project, one brief per project, explicit live-state exclusions, tool state isolated from source; **convmem = cross-project coordination only**.

### Amendments (Cursor + Kiro alignment)

| Codex rule | Cursor amendment |
|------------|------------------|
| One root under `~/Projects` | **Yes** — already true for active work (`convmem`, `wp-sec-agent`, `web-control`, `ComfyUIimprov`) |
| One brief per project | **Yes** — each project gets `brief.md` or `STATUS.md` at project root; machine-wide ops stay in `~/.local/share/convmem/brief.md` |
| Explicit watch exclusions | **Yes** — document in each project's `AGENTS.md` + global `watch.py` live-DB list; not ad hoc |
| Tool state ≠ source | **Yes** — `.crush/`, `.lighthouseci/`, `node_modules/`, ComfyUI caches **out of watch roots** |
| New inventions isolated | **Yes** — new `~/Projects/<name>/` + own brief before merging into shared coordination |
| convmem mixes runtime state | **No** — convmem data dir is tool state; project runtime stays in project trees |

### Defer (not now)

- Stronger workspace **index** (Codex/Sonnet optional ask) — wait until 2+ projects need automated discovery  
- Folding `web-control` / `ComfyUIimprov` into convmem watch — **exclude noisy roots first**  
- Commit + workspace doc — after Ryan approves this decision (Kiro asked for commit of memory fixes separately)

### Kiro guardrails before "safe for many inventions"

Align with `KIRO-CURSOR-BEST-PRACTICES-2026-06-22.md`:

1. **24h clean watch journal** — not optional  
2. **Commit checkpoint** — memory + brief + readonly work  
3. **Per-project `AGENTS.md`** — Codex has convmem's; add wp-sec-agent, web-control when those agents run  
4. **No watch on invention sandboxes** until exclude rules written  

---

## Recommended next steps

| Priority | Action | Owner |
|----------|--------|-------|
| 1 | Ryan: approve workspace standard (this doc) | Ryan |
| 2 | Commit memory/brief/readonly batch | Ryan asks Cursor |
| 3 | Add `docs/WORKSPACE-STANDARD.md` (short, ~1 page) | Cursor |
| 4 | Exclude `ComfyUIimprov` from convmem watch paths if not already | Cursor |
| 5 | `wp-sec-agent/AGENTS.md` pointing at convmem + client paths | Cursor |
| 6 | Re-enable watch → 24h soak | Ryan |

---

## Vote

**Cursor: yes** to Codex workspace standard with amendments above.  
**Pending:** Kiro sign-off on workspace doc before calling multi-project mode "safe."

— Cursor
