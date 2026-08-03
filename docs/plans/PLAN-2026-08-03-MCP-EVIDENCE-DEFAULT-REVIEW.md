# Plan: MCP Evidence-Default Review

**Status:** plan-only; authorizes no code, test, MCP, corpus, ledger, service,
or configuration change.

## Finding

The MCP `ask()` surface currently defaults `evidence=True`, while the CLI
`ask()` surface defaults `evidence=False`. The difference is visible in
`mcp_server.py` and `ask.py`, but no current test asserts the intended parity
or divergence. The existing MCP surface exposes some trace and citation
metadata; this plan does not claim that the older trace-desert proposal remains
fully current.

## Decision needed

Ryan must decide whether the MCP default should remain evidence-enabled or be
aligned with the CLI. Until that decision, the mismatch is an explicit open
contract question, not an implicit authorization to change behavior.

## Bounded follow-up

The implementation owner should inspect both callers and add a targeted
regression check for the selected contract. If the default remains divergent,
the public MCP and CLI guidance must state why. If alignment is selected, the
change requires the normal implementation, independent review, and same-tip
verification gates. No agent may infer the intended answer from retrieval
quality claims or change the default during this plan-only phase.

## Evidence

- `mcp_server.py:818` — MCP `ask()` default is `evidence=True`.
- `ask.py:937` — CLI `ask()` default is `evidence=False`.
- `tests/test_mcp_site.py:176-188` — current MCP forwarding test fixes
  `evidence=True` but does not assert the public default contract.
- `docs/inter-model/debate-2026-07-15-who-fixes-retrieval/CONTINUE-DEEPSEEK-problem-3-mcp-evidence-default-trace-desert.md`
  — prior proposal identifies the mismatch; its older line references and
  claim that MCP cannot expose trace must not be treated as current evidence.
