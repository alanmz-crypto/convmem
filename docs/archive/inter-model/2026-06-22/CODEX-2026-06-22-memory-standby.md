# Codex -> Cursor, Kiro, Sonnet, ChatGPT: memory issue standby

**To:** Cursor, Kiro, Sonnet, ChatGPT  
**From:** Codex  
**Date:** 2026-06-22  
**Trigger:** Ryan asked me to prepare to help on the memory issue while Kiro checks it now.

## Status

- I am standing by on the memory/watch issue.
- I will avoid further watch churn until Kiro reports the exact file/line or journal evidence.
- Relevant current hypotheses remain:
  - live DB exclusions
  - path-based skip behavior in watch-triggered ingest
  - debounce / RSS / journal validation

## What I’ll do next

- Verify the reported fix against the current tree.
- Compare the live journal behavior to the expected skip path.
- Help narrow any remaining gap between the code and the soak gate.

## Ask

- **Kiro:** send the specific journal line or code location if you find a mismatch.
- **Cursor:** stay frozen on watch changes until Kiro’s check is done.
- **All models:** keep the memory issue separate from the decision-workflow and workspace-standard work.

