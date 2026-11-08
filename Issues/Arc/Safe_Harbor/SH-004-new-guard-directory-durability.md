# SH-004 — First-marker durability relies on a best-effort event append

**Arc:** Safe Harbor · **Status:** open, conditional static durability gap · **Priority:** P2

Codex, 2026-10-25. Source at `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`; unchanged in inspected `origin/main`. **Confidence: 90% in the missing mandatory durability step.** No power-loss behavior was tested. Local implementation issue in containment publication.

## The narrow failure condition

When first contact with a store creates `<chroma>.write-guard`, syncing that directory persists its contents, but the new directory name also needs its parent synced. Marker publication omits that parent step. The subsequent event append normally supplies it; however, containment treats event errors as best effort and can still report quarantine when that durability step fails.

This concerns a newly created, not-yet-durably-linked guard directory. It does not establish a present defect in this production store's long-established directory, or predict an actual loss on its filesystem.

## Source trace

- [chroma_write_guard.py:1074](../../../chroma_write_guard.py#L1074): lock acquisition may create the guard directory with `mkdir(parents=True)`; no parent-directory sync follows there.
- [chroma_write_guard.py:2237](../../../chroma_write_guard.py#L2237): `_publish_marker()` creates the directory, writes/fsyncs the temporary marker, replaces the marker, and syncs `quarantine_path.parent` only—the guard directory itself.
- [chroma_write_guard.py:1832](../../../chroma_write_guard.py#L1832): event publication uses `_fsync_directory_chain(self.root, stop=self.root.parent)`, which includes the missing parent sync.
- [chroma_write_guard.py:2292](../../../chroma_write_guard.py#L2292): `_contain()` catches an `OSError` from that event path and then raises ordinary `ChromaWriteQuarantinedError`. It does not report `ChromaContainmentUnavailableError` for this dependency failure.

A concrete source-level case is first reconciliation of a corrupt store with no prior guard/save: the new marker is written, the following event's parent fsync fails, and the caller receives normal quarantine wording. The current invocation stops, but the claimed durable admission authority has an unsatisfied naming-durability prerequisite.

## Existing evidence and qualification

[The directory-fsync test](../../../tests/test_safe_harbor_t1.py#L1132) injects failure on the `.write-guard` directory itself and correctly expects containment unavailable. It does not exercise a newly created guard directory's parent or failure in the later event path.

Ordinary successful event publication mitigates this gap, and an existing durably linked guard directory does not require its name to be re-established for every marker. The issue is that mandatory marker durability currently depends on an operation whose errors may be ignored.

## Bounded resolution

Make the existing directory-chain durability step part of marker publication, through the established parent boundary, before it can be called durable. A failure there must report containment unavailable. Event logging may remain best effort only after authority durability is independently established.

**Proposed isolated evidence, not run:** start with an absent guard directory, inject failure specifically at its parent's fsync, and assert no requested mutation/replacement plus containment-unavailable reporting. Separately fail event publication after successful authority durability and verify that the distinction is honest. Track actual fsync paths/order; process restart alone is not power-loss proof.

<!-- src: ../../../chroma_write_guard.py, ../../../tests/test_safe_harbor_t1.py, ../../../docs/plans/EXECUTION-safe-harbor.md -->
