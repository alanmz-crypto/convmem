# Global planner critique summary

Shared note for other models critiquing or building on the global convmem protocol plan.

## Verbatim note

I read the two newest critique notes:

- [docs/inter-model/GLOBAL-PLANNER-GAP-ANALYSIS.md](/home/lauer/Projects/convmem/docs/inter-model/GLOBAL-PLANNER-GAP-ANALYSIS.md)
- [docs/inter-model/CODEX-2026-06-25-global-convmem-protocol-insights.md](/home/lauer/Projects/convmem/docs/inter-model/CODEX-2026-06-25-global-convmem-protocol-insights.md)

Main takeaways:

- The architecture is still judged sound.
- The biggest concrete gap is deployment fidelity, especially the Cursor rule path mismatch: `~/.cursor/rules/convmem.md` vs the planner’s `~/.cursor/rules/convmem.mdc`.
- MCP needs an explicit shell fallback path for shell-capable agents.
- `brief` should be explicitly marked “call first” in its docstring.
- Codex sandbox/network handling should be part of the canonical protocol, not just a local override.
- The startup protocol needs capability tiers:
  - shell-capable
  - MCP-only
  - paste-only / ChatGPT

If you want, I can now turn these critiques into a patch plan for `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` itself.
