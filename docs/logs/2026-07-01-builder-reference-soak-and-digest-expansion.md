# 2026-07-01 Builder reference soak and digest expansion

## Work performed

1. **Expanded builder-reference digests**
   - Added more concrete convmem-specific guidance to:
     - `docs/builder-reference/ousterhout-builder-digest.md`
     - `docs/builder-reference/manning-builder-digest.md`
     - `docs/builder-reference/zeller-builder-digest.md`
   - Focused on module depth, retrieval pipeline behavior, and debugging
     workflow mappings for `convmem` work

2. **Verified surface wiring**
   - Confirmed `docs/builder-reference/README.md` and `SOURCES.md` exist
   - Confirmed `config/codex-agents-convmem.example.md` includes builder-reference
     pointer text
   - Confirmed the generated Cursor and Kiro surface files exist
   - Confirmed `~/.config/crush/crush.json` has builder-reference paths in
     `global_context_paths`

3. **Re-ran builder-reference extraction**
   - `scripts/extract-builder-reference.sh` staged the PDF slices into the
     gitignored `staging/builder-reference/` directory

4. **Re-generated protocol surfaces**
   - Ran `scripts/generate-agent-protocol.sh`
   - The Codex AGENTS example regenerated with the builder-reference pointer

## Current status

- Builder-reference skeleton is in place
- Digests are now substantially more detailed than the first pass
- Surface deployment succeeded for Cursor, Kiro, Codex, and Crush
- Live interactive soak remains the main unfinished validation step

## Notes

- The log records the repo state after digest expansion and wiring checks.
- The record thread is tied to the builder-reference coordination decision.
- This entry stays separate from the PDF test harness work in `pdf-ai`.

