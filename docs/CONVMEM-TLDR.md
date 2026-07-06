# convmem — TLDR

**Full cheat sheet:** [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md)

---

## Every session

```bash
convmem doctor
convmem brief --stdout-only
convmem unresolved          # add --site <host> for client work
convmem "your question"       # search; convmem ask "…" for summary
```

MCP (Cursor): `brief()` → `search_fast()` / `ask()` before history questions.

---

## Lanes

| Workspace | TLDR |
|-----------|------|
| `willowyhollow-practice` | `convmem tldr` (auto) or [`WILLOWYHOLLOW-TLDR.md`](WILLOWYHOLLOW-TLDR.md) |
| `convmem` repo | this file |
| Lab experiments | `~/Projects/convmem-lab/scripts/convmem-lab.sh doctor` — **no prod MCP** |

---

## Durable facts (you approve)

```bash
convmem record -i
convmem record --approve-last
```

---

## Prod vs lab

- Prod: `convmem` → `~/.local/share/convmem`
- Lab: `convmem-lab.sh` only → `~/.local/share/convmem-lab`
- Cross-lane writes blocked unless `CONVMEM_CONFIRM_PROD=1` / `CONVMEM_CONFIRM_LAB=1`

---

## Footers

Most commands print **── Next steps ──** when done.  
Mute: `CONVMEM_NO_NEXT_STEPS=1`
