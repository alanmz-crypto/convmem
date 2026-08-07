# Tool-output hygiene (Crush residual cost)

Standing context is already small (~6k tokens). Most Crush prompt cost is
**bash / view / grep dumps re-billed every later turn**. Keep tool results thin
in chat without hiding failures.

## Hard guidance

When using `bash`, `view`, or `grep` (and similar file/shell tools):

1. **Prefer ranged reads** — `head`, `tail`, `sed -n 'A,Bp'`, `view` with
   offset/limit, `rg` with context flags. Do not dump whole files or full
   test logs into the transcript by default.
2. **Keep what stays in chat small** — aim to leave only the lines needed for
   the next decision (rough target: a few hundred lines / tens of KB, not
   megabytes). If you need more, re-fetch a tighter range.
3. **Failure exception (mandatory)** — on non-zero exit or clear failure:
   show the **exit code** and the **last N lines** of output (enough to see
   the error). Never silently truncate away a failing command.
4. **Do not strip safety text** — ritual, charter, doctor-first, and commit/PR
   quality rules stay intact. This file only constrains tool dumps.

## Why

Unique tool characters are often far smaller than session `prompt_tokens`
because history is re-charged each turn. Early caps compound; late full dumps
erase the savings.

<!-- Deployed by scripts/deploy-agent-protocol.sh →
     ~/.config/crush/rules/tool-output-hygiene.md -->
