# Independent memory spaces: owner requirement and research

**Date:** 2026-10-31. **Arc: none (ad-hoc).** Documentation and static research only. Source assessed: `d54f92bcd78248c8aee8a54df758564752d79aa4`.

**Recommendation:** design ConvMem around independent, initially empty **memory spaces**. Start with explicit local CLI selection and complete separation of each space's stored state. Later, let authorized applications query a selected space remotely. Add offline copies only when an actual offline requirement justifies synchronization. This is a proposed direction, not an implemented capability or a promoted plan.

## Owner clarification and terminology

The owner requires different activities to have separate bodies of memory, including fresh spaces for application use. One person may work in several spaces; several authorized people may work in one shared space. Separate empty spaces on the PC are preferred if economical. The owner raised mirroring or uploading smaller stores as a possible mechanism and explicitly asked for research instead of prescribing that mechanism. Hardware capacity, offline use, exact applications and hosting have not been established.

This clarification strengthens [F19](CODEX-2026-10-31-convmem-general-memory-owner-decisions.md). CLI remains the first access surface. Space identity and accidental cross-space contamination belong in the local design now; authenticated multi-user application access remains later work. The prior F17 and F18 decisions remain in force.

| Concept | Meaning | Example |
|---|---|---|
| Memory space | A separately identified body of admitted content and derived state | Coding, business operations, a fresh experiment |
| Member | A person or service allowed specified operations in a space | A collaborator can belong to both coding and business spaces |
| Client | A CLI or application using a selected space | Different model-backed CLIs can use the same coding space |
| Source scope | Rules for admitting and interpreting source material within a space | `ordinary_document_v1` and `repository_knowledge_v1` |
| Text chunk | An indexing or evidence unit inside a space | One source passage |
| Replica | A managed copy of some or all of a space on another host | An optional future offline device copy |

Do not equate a person, model, phone, source scope or text chunk with a memory space. The implementation might use directories, databases or namespaces; the product contract should survive that choice. LangGraph's documentation illustrates that long-term namespaces need not be user-specific and are separate from conversation threads [S04]. It is comparative evidence, not a proposal to adopt LangGraph.

## What “starts empty” must mean

A newly created space has no admitted user sources, extracted memories, inherited conversation history, preferences, summaries, task markers, evidence references or content-bearing caches from another space. It can have an empty schema and generic configuration. Empty memory does not erase the AI model's pretrained knowledge. A future mobile client may either create a fresh space or explicitly join an existing space; installing a client must not silently copy or expose the legacy corpus.

The existing corpus remains a separately identified legacy store. No automatic import, repartitioning, reindexing, clearing or migration is proposed for it in the first slice. Moving useful material between spaces is an explicit later import/copy decision with source provenance, not an invisible search fallback.

The separation must cover the complete lifecycle: preserved originals and revisions (F18), extracted units, metadata and indexes, source admission, publication pointers, sidecars, preferences and markers, queues, logs containing content, summaries, caches, exports, backups and client conversation state. A blank vector collection with an inherited summary is not an empty space.

**Client context matters:** selecting a different store does not remove evidence already present in an AI conversation. Recommend a fresh conversation or independently maintained session when changing spaces, with no automatic transcript import. A client that cannot isolate its chat history or application memory cannot promise a clean space merely by changing a ConvMem setting. Generic model weights can be reused; retained prompts, responses, tool results and user-derived adaptations need their own boundary.

## A simple local candidate

Chroma supports a persistent store at an explicit filesystem path [S01]. ConvMem already accepts `CONVMEM_CONFIG`, but that variable is selected at import time and does not relocate every stateful artifact. The [static evidence note](CODEX-2026-10-31-convmem-memory-spaces-code-evidence.md) identifies shared defaults, process caches, whole-store tools and direct SQLite reads.

**Candidate for the next draft:** one complete configuration/data root per selected space, with a process or service instance bound to that root for its lifetime. Reuse the ConvMem software and generic model assets where safe. Make source roots explicit and empty by default; reject missing/unknown space selections in the new isolated entrypoint rather than falling back to the legacy store. Existing legacy entrypoints need not change in the pilot.

This is a simple local candidate supported by the static audit, not a proven cheapest deployment. Separate processes may duplicate model memory. Sharing model services can reduce duplication but introduces request/context handling that also needs isolation. No RAM, startup-time, disk-cost or concurrency measurements were taken. Measure those in a later authorized environment before promising that many spaces are cheap.

Separate roots help prevent accidental mixing; they are **not an OS security boundary** between tools that run as the same unrestricted local user. Later access by different people requires server-enforced membership and permissions across every operation. Native database tenant names or a metadata filter alone are not proof of such enforcement. Chroma's cookbook explicitly places enforcement on the application in its naive approach [S02]. Its current documentation cannot establish behavior in the dependency version installed on the owner's PC.

Do not switch databases now. Qdrant's official guidance shows the tradeoff: collections carry overhead, while shared collections can partition tenants using filters [S03]. That makes physical separation a reasonable candidate for a few local spaces, not a scaling rule for thousands of spaces. It supplies no Chroma cost measurement. ConvMem's current raw SQLite reader also prevents treating native Chroma tenant/database selection as a safe configuration-only change.

## Mobile use does not require mirroring the PC

| Access mode | What reaches the device | Recommendation |
|---|---|---|
| Online query | Authorized results/evidence from the selected space | First mobile approach to evaluate; no whole-store copy required |
| Portable snapshot | An explicitly selected version with a manifest and provenance | Later transfer/reference feature; not live synchronization |
| Offline replica | A selected local copy plus synchronization state | Defer until disconnected use is required |

Chroma documents HTTP clients connecting to a separate server [S05]. This establishes the architectural option, not an existing ConvMem mobile feature. Recommend an application service enforcing identity and space access in front of storage; do not give phone clients unrestricted database access. Search, expand-by-ID, related results, statistics, writes, source downloads, exports and eventual synchronization must all resolve the authorized space on the service side. A caller-supplied space label is not authorization.

If the PC is the only host, it must be on and reachable to answer remote queries. An always-on host for selected spaces is a later alternative. Offline copies are another alternative with different costs. An existing phone application must support a suitable integration; no universal compatibility, particular app, protocol, provider or hosting service is selected here.

Storage capacity and separation are different questions. Subject to available resources, a PC can host differently sized spaces; a phone querying a large space need only receive bounded results. Splitting one large dataset into labels does not by itself reduce total RAM or disk needs. Loading/index strategy, concurrent processes and hosting require separate measurement. A space can also contain more retained originals on disk than should be retrieved into a single model context.

Offline replication adds conflict rules, checkpoints, freshness indicators, deletion propagation and access-revocation behavior. PouchDB warns that replication filters do not replace authentication [S06]; current CouchDB documentation says members can read all document types in their database [S07]. Couchbase documents local purge after revocation on the **next pull replication**, with exceptions [S08]. These are concrete reasons not to equate filtering or copying with access control. A disconnected copy cannot be recalled instantly, and recipient-created copies cannot be recalled by a sync protocol.

Retaining complete admitted originals under F18 is distinct from publishing those originals to every device. Database revisions can be pruned and deletion markers purged [S09]; revision support alone is not a preservation guarantee. A future export/replica must declare whether it includes complete originals or only references, and what evidence remains accessible offline. Copying a live database directory is not a synchronization design.

## Consequences for the next bounded-plan draft

These are design obligations and future acceptance observations, not newly authorized implementation or fixtures.

1. **Put space identity before feature expansion.** Inventory every read/write path and specify how two fresh spaces and the untouched legacy store remain separate. Explain how local clients bind to a space and how a session change avoids inherited context. First constrain the entrypoints supported by the pilot; explicitly exclude unsupported ones.
2. **Keep the documentary proposal bounded.** `ordinary_document_v1` remains a sibling of `repository_knowledge_v1` inside the selected space. Keep convention extraction, the pool sweep followed by the existing keyword scan, and the locked 24-case retrieval design. A new lexical index, E4 and prompt rewrites stay excluded. Fresh-space isolation is an additional correctness requirement, not a replacement for the 24 cases or a claim that their denominators can silently change.
3. **Design preservation with isolation.** Bind each admitted original, revision, source reference and publication record to its space. Retain complete verifiable bytes as required by F18. Explain deliberate forgetting/retention and availability labels without treating a retained old version as current authority.
4. **Carry the review requirements.** Settle G01–G05 and include G06–G07 from the [reassessment response](CODEX-2026-10-31-convmem-general-memory-reassessment-response.md). Publication fencing, candidate merging, evidence offsets and model/cache isolation still apply within each space. The new space boundary must also reach keyword scans and evidence expansion.
5. **Specify future negative observations.** An empty space returns no other-space content; a write/admission to A does not appear in B; direct IDs, related/stats/brief/export paths cannot bypass selection; unknown selection cannot reach legacy defaults; simultaneous clients do not share scope-setting state; changing client sessions does not carry prior-space evidence. Include state-path and original-byte inspection, not just similarity-search outputs. These checks have not been written or run.
6. **Defer application deployment and synchronization.** Describe extension points and eventual membership/read/write roles, but do not pull a mobile app, auth server, hosting stack, multi-writer replication or database migration into this slice. Reassess the expanded local boundary and F18 design before plan promotion. If their minimum safe scope exceeds a bounded first slice, propose a separate smaller isolation/preservation design milestone with evidence.

## What remains an owner choice

F17–F19 have answers; they are not reopened as unanswered gates. The new requirement clarifies F19. Before later mobile planning, identify the applications, whether offline reading or writing matters, required availability while the PC is off, and which spaces/members may read, contribute, export or administer. Those decisions do not block this research or the next local design draft.

The recommendation to use separate roots/process binding and online mobile queries is Codex's recommendation. It has not been separately selected by the owner. **Ryan retains plan-promotion authority.** The prior `PASS_FOR_BOUNDED_PLANNING` remains conditional for the previously reviewed proposal; it does not approve the new preservation or space-isolation design.

## Evidence and delivery

Six Exa searches across two research workstreams requested **30 result slots**. Nine distinct primary pages were fetched; relevant passages were inspected, not every page in full. One mobile page was refetched after truncation. Requested slots are not a count of distinct or fully reviewed sources. Vendor documentation is architectural evidence, not verification of this ConvMem checkout or the owner's installed versions. The older 2015 PouchDB article is used for its filtering warning, corroborated by current CouchDB security documentation; its old API/purge behavior is not treated as current.

The [source register](CODEX-2026-10-31-convmem-memory-spaces-sources.json) links S01–S09 and records limits. Exact queries and raw connector responses are retained in the additive private research delivery for reproducibility. No private corpus was searched for this research; no personal details or private filenames are included here.

The [field guide and Claude prompt](CODEX-2026-10-31-convmem-memory-spaces-handoff.md) route the complete review history and this addition. Original packets, Claude reviews, prior handoffs and owner-decision records remain intact. No project implementation, fixture, runtime, corpus write, paid model call, PR or deployment was performed.
