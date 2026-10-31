# General-memory review revision: document validation

**Date:** 2026-10-31. **Author:** Codex. **Arc: none (ad-hoc).**

This records static document checks for the [finding response](CODEX-2026-10-31-convmem-general-memory-review-response.md) and [revised first slice](CODEX-2026-10-31-convmem-general-memory-revised-first-slice.md). It is not an implementation verification or a replacement for Claude Fable's verdict.

| Check | Result and limit |
|---|---|
| Incoming review | Exactly 28,708 bytes; SHA-256 `be4fb1bf980107b96a8e78fdbf0f8c92a0ed7666dc6fda9ec4dce7b1218a188e`; repository copy equals downloaded bytes. |
| Assessed source | `d54f92bcd78248c8aee8a54df758564752d79aa4`; source citations refer to this commit. |
| Original delivery | `a6d155f1f8d235b488256a47180acf5a5d6377d6`, direct child of the assessed source; fast-forward merged into the prepared verdict branch. |
| Original manifest | SHA-256 `5f446de7077e165a38e3273afe5e97d5fc654d87f4605063840034ad966715ea`; all ten listed file sizes and hashes checked against Git blobs at `a6d155f`. |
| Original research packet | Every tracked file under `review-pack-2026-10-31-convmem/` compared byte-for-byte with `a6d155f`; unchanged, including the manifest. |
| Original Codex handoff | One existing review-state table line replaced; no other line changed. The new value records `DELIVERED`, verdict and reviewer path. |
| LATEST routing | One existing general-memory routing bullet replaced; other entries unchanged. |
| Finding response | F01–F09 each have one individual `ACCEPT` disposition, with qualifications and concrete changes. F17–F19 distinguish observed source evidence from decisions left for Ryan. |
| Source/link checks | Pinned source-link files and line targets checked against the assessed commit; relative document targets checked locally. Link existence does not certify every interpretation. |
| Revision audit | A separate read-only Codex audit identified a revision-identity issue; the slice now includes raw-file digest in ordinary unit identity and distinguishes indexed/current from historical revisions. This is author-side checking, not Claude re-review. |
| Public/private separation | Supplied review and new public documents inspected; no private Drive URLs, private source filenames, email addresses or personal corpus details added. Generic convention markers remain examples of syntax. Private file identifiers belong only in the separate private receipt addition. |
| Diff scope | Documentation only; no source, config, schema, fixture or test-file edits. |
| Execution boundary | No implementation, fixture creation, runtime/doctor invocation, corpus access/write, paid model call, evaluation run or PR creation. |

The original manifest hashes the original Codex handoff. Its authorized review-state edit necessarily changes that file's hash. The original manifest is therefore checked at its original commit; no claim is made that it validates the modified handoff at the verdict tip. The immutable packet subtree is checked separately, and the manifest is not regenerated.

The incoming review is an **addition** to the existing private delivery. A supplemental delivery receipt records its Drive identity, byte count and verified digest without replacing any existing backup artifact. Private receipt information is intentionally absent from this public tree. Remote persistence and fetch-back results are recorded in that receipt after publication of the verdict branch.

**Status:** documents revised; independent reassessment and Ryan's recorded decisions remain next. No capability or study result is certified by these checks.
