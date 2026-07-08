# ksweep routing — read the steering file, do not grep

`#ksweep-<name>` invokes a **Kiro steering file** (a markdown checklist), not a convmem
command and not a script. When asked to run a ksweep, **read the steering file directly**
at the path below and execute its checks in order. Do **not** `grep`/`glob` the home
folder hunting for it.

| Invocation | Read this file |
|---|---|
| `#ksweep-deploy` | `~/GitClones/willowyhollow-dev/.kiro/steering/ksweep-deploy.md` |
| `#ksweep-practice` | `~/WordPress/willowyhollow-practice/.kiro/steering/ksweep-practice.md` |
| `#ksweep-preview` | `~/WordPress/willowyhollow-practice/.kiro/steering/ksweep-preview.md` |
| `#ksweep-all` | `~/WordPress/willowyhollow-practice/.kiro/steering/ksweep-all.md` |
| `#ksweep-tldr` | `~/WordPress/willowyhollow-practice/.kiro/steering/ksweep-tldr.md` |

The full set lives in `~/WordPress/willowyhollow-practice/.kiro/steering/` (invocable from
any workspace). If the current workspace has its own `.kiro/steering/ksweep-<name>.md`,
prefer that copy for that surface.

**Stale-corpus warning:** older chat distillations in convmem claim *"no standalone ksweep
file exists on disk."* That is **outdated** — the files above exist. Trust the paths here
over that corpus hit.

<!-- SUNSET: retire this rule once P1 contradiction-aware ranking ships (ledger/inter-model
outranks older chat distillation on the same entity). At that point search_fast will return
the correct steering path on its own and this static route is redundant. Tracking:
docs/inter-model plan "How the ksweep-deploy incident reflects on convmem" (P0.4 -> P1.3). -->
