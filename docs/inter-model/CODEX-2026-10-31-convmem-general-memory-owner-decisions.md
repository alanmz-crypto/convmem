# Owner decisions for the general-memory first slice

**Date:** 2026-10-31. **Recorded by:** Codex from Ryan's answers in this conversation. **Arc: none (ad-hoc).**

**F17–F19 are answered.** These are product decisions for the next bounded-plan draft, not approval of a plan, implementation or deployment. The prior reviews and proposals remain unchanged as history.

## Decisions

| Item | Ryan's decision | First-slice boundary |
|---|---|---|
| **F17 — preferences and task state** | Keep source files authoritative. Extract explicit preference and task statements as sourced markers. | Dedicated preference/task lifecycle management is deferred. Preserve origin and context rather than silently establishing a second owning record. |
| **F18 — original-file preservation** | Preserve complete, verifiable original versions for source revisions admitted to the pilot. | The requirement applies to admitted revisions, not every file on the PC or every intermediate edit. Storage, revision binding, retention and deliberate forgetting still need design. |
| **F19 — daily access** | Local CLI access across multiple models and clients is the primary initial workflow. Support mobile and off-site application access for additional authorized users in later phases. | Keep the first slice simple and local. No particular mobile app, model provider, application framework, hosting arrangement or connector is selected. |

The public F19 wording describes the product requirement without personal details. The private decision companion preserves the owner's fuller access context.

## Consequences for the next draft

1. **Use CLI access as the first acceptance surface.** ConvMem remains shared memory infrastructure across model-backed clients; choosing CLI first does not choose one model. The draft should identify the minimum existing CLI/MCP integration surface and its client assumptions without expanding into an application build.
2. **Make original preservation an explicit design change.** The [reviewed first-slice proposal](CODEX-2026-10-31-convmem-general-memory-revised-first-slice.md) did not guarantee complete original-file retention. F18 now requires it for admitted revisions. The plan must explain how stored original bytes, revision identifiers and evidence references can be verified and retrieved after the working file changes or disappears. A hash alone is insufficient to recover missing bytes.
3. **Keep current authority distinct from historical evidence.** A retained revision records what was captured. It does not establish that a claim is true or still current, and it does not automatically replace the owning source file.
4. **Keep future access possible without building it now.** The draft should identify where later clients and user access boundaries can attach. It must not assume all future users receive all memory, or require phone clients to manipulate internal storage directly. Sharing choices, authentication, remote transport and application behavior remain later design work; no remote server or access-control implementation is added to this slice by these decisions.
5. **Retain the review conditions.** Carry G01–G07 and the existing exclusions forward. CLI priority provides no new evidence that Switchboard is needed in the first slice; future mobile access does not select OpenClaw as the transport.

## Review and authorization state

Claude Fable's [second-round verdict](CLAUDE-2026-10-31-convmem-general-memory-reassessment.md) remains `PASS_FOR_BOUNDED_PLANNING`, conditional on §5, for the proposal reviewed at `e81970829ed187eeb5256870fc82ad1376373e40`. The [G01–G07 response](CODEX-2026-10-31-convmem-general-memory-reassessment-response.md) records the planning obligations and source-backed qualifications at `d54f92bcd78248c8aee8a54df758564752d79aa4`.

The owner-answer portion of the promotion gate is now complete. **Plan promotion remains Ryan's decision.** A concrete bounded draft must carry these answers, settle G01–G05, include G06–G07, show the strengthened F18 preservation design and receive reassessment before promotion. No new PASS is claimed for a preservation mechanism that has not been designed or reviewed.

Existing statements that F17–F19 await Ryan are historical in the preserved reviews and responses; this dated decision record supplies the answers. The first-slice scope stays local CLI, with sourced markers and preserved admitted originals. Mobile, off-site and additional-user application access remain future product requirements.

**Next deliverable:** a documentation-only bounded-plan draft and review handoff. **Next lane:** bounded-plan author, followed by independent review and Ryan's promotion decision. No plan is promoted by this record, and no implementation, fixture, project runtime, corpus write, paid call, PR or deployment is authorized by it.
