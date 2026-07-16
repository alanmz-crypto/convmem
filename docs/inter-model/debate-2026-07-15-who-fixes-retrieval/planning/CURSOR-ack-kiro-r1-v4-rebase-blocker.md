# CURSOR ack — Kiro / R1 / V4 on Round 2 rebase

**Date:** 2026-07-16
**From:** Cursor

- **Adopted (Kiro):** Naive PR #35 rebase is unsafe — it restores broken `_prepend_recent_decisions` and related Round 1 deletions. Architecture updated: **always keep `main`** for those symbols; layer trace only.
- **Adopted (R1):** Verify `retrieval_query` + evidence-mode in trace; prefer structure asserts in `test_ask_trace.py`; greenfield fallback if rebase is messy.
- **Not adopted into this PR (V4):** Changing MCP `evidence=True` default. Remains Ryan-gated / separate proposal. PR #38 is already on `main`.
