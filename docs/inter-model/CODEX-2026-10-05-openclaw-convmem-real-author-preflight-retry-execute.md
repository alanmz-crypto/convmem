# Execute Handoff: Switchboard Real-Author Preflight Retry

**Arc:** ConvMem Switchboard
**Date:** 2026-10-05
**Author:** Codex supervision lane
**For:** Astra execution lane
**Authorization:** Ryan, 2026-10-05 — explicit `grant issued` response after the
first grant's zero-effect read-only preflight `PAUSE` was recorded

---

## Resume state

| Field | Value |
|---|---|
| **State** | `CONSUMED / PAUSE` — corrected preflight passed; the sole offline `author-packet` process exited `1` at `DEPENDENCY_CLOSURE` |
| **Grant branch** | `plan/2026-10-05-openclaw-convmem-real-author-preflight-retry-grant` |
| **Semantic parent** | `31d4c919cfe77ae6d2fbbcb473a0fd8e0857515d` |
| **Reviewed overlay** | `d7f82fbcd3afd3887d4b3764b173958d5094ee53` |
| **Authorization base** | `ca0397c084b2616809307249212b7153d9d8ba39` |
| **Reviewed plan merge** | PR `#361`, `8d1c01762d920a91667f96182fab04c4fc583e86` |
| **Reviewed status merge** | PR `#362`, `ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c` |
| **Consumed predecessor** | `d6ff557f8759db442221f8a0d1e88a83d5672543` — zero effects, non-reusable |
| **Push status** | Read and execute only the exact pushed origin tip of this branch |
| **PR** | Not opened; this grant authorizes no PR creation or merge |
| **Ryan GATE** | Fresh planning and review are required before any correction or further attempt; this grant is non-reusable |

## Consumed-attempt result

The corrected component-wise no-follow preflight passed without reading packet or
disposition content and without creating or mutating a path. Astra then launched the
literal twenty-member command exactly once from the accepted final author root with
the exact five-key environment. The process failed closed:

```text
PROCESS_COUNT=1
SUBPROCESSES=0
EXIT_STATUS=1
REPORTED_STATUS=PAUSE
STOP_STAGE=DEPENDENCY_CLOSURE
EXCEPTION=Refusal: W001: input ID prefix
REAL_INPUT_READ_BYTES=54052776
PEAK_RSS_BYTES=2059636736
RSS_CEILING_BYTES=2147483648
ACCEPTED=false
```

The first missing component for both staging targets was
`/home/lauer/.cache/convmem-switchboard-provenance-work-items`; the first missing
component for both durable targets was
`/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items`. Per the
corrected rule, each `ENOENT` proved its two named partial/final descendants absent
without probing beneath the missing component.

All network, repository, runtime, retained-source, credential and acquisition counters
were zero. All four authorized output coordinates remain absent; no output root,
receipt, result, ledger, role file, hash, size, mode, link count or work-item
cardinality exists. `baseline_count=0`, `controls=[]`, and the ledger and both
forecast/observed written-byte fields are null. The process result's
`final_exists=true` refers to the immutable accepted author-capability root, not an
authorized output final root. No retry, repair, deletion, resume, second process,
acceptance or later-gate action occurred.

Durability counters stopped before the first governed event:

```text
ROW_ZERO_SETUP_FILE_FSYNC_COUNT=1
ROW_ZERO_SETUP_DIRECTORY_FSYNC_COUNT=1
GOVERNED_ROW_ZERO_FILE_FSYNC_COUNT=0
GOVERNED_ROW_ZERO_DIRECTORY_FSYNC_COUNT=0
EVENT_ONE_WRITE_AFTER_GOVERNED_FSYNC_COUNT=0
COORDINATE_PARENT_PRE_RENAME_OPEN_COUNT=0
COORDINATE_PARENT_PRE_RENAME_FSYNC_COUNT=0
COORDINATE_PARENT_POST_RENAME_OPEN_COUNT=0
COORDINATE_PARENT_POST_RENAME_FSYNC_COUNT=0
```

This evidence records a consumed fail-closed attempt only. It grants no diagnosis,
source change, new root, retry, execution, read, acquisition, build, publication,
implementation, PR, merge, deployment, real OpenClaw or later-gate authority.

## Consumed two-SHA grant

```text
SEMANTIC_PARENT_SHA=31d4c919cfe77ae6d2fbbcb473a0fd8e0857515d
REVIEWED_OVERLAY_SHA=d7f82fbcd3afd3887d4b3764b173958d5094ee53
AUTHORIZATION_BASE_MAIN_SHA=ca0397c084b2616809307249212b7153d9d8ba39
AUTHORIZED_ATTEMPTS=1
AUTHORIZED_PROCESS_COUNT_MAX=1
AUTHORIZED_MODE=author-packet
```

The semantic parent and reviewed overlay are the governing pair. The merge, snapshot,
predecessor and grant-branch SHAs are traceability checks and cannot replace either
governing SHA. The normative contract is Architecture §18.45 retaining §§18.31–18.44,
Execution §10.43, milestone M11/§7, current STATUS and this handoff.

The predecessor grant stopped before effects and was not reused, resumed or repaired.
This successor grant is also consumed and cannot be reused. Any future correction or
attempt requires a new reviewed plan and a new Ryan decision.

## Sole correction: expected-absence ancestor handling

The first preflight raised `FileNotFoundError` while walking the absent staging base.
This successor changes only the read-only interpretation of `ENOENT` on the four exact
output lineages:

1. Walk each exact output lineage component-by-component with no-follow metadata
   operations. Do not enumerate a directory or inspect an unrelated sibling.
2. Existing components must be directories of the expected operator-owned lineage;
   reject any symlink, special file, wrong type, unexpected link state or path drift.
3. The first `ENOENT` on an exact expected output component proves that component and
   every named descendant on that same lineage absent. Record the exact missing
   component and classify the target coordinate `ABSENT`; stop that lineage's walk.
4. Do not call metadata operations on descendants beneath the first missing component.
   Do not convert that expected `ENOENT` into an exception or `PAUSE`.
5. `EACCES`, `ELOOP`, `ENOTDIR`, `EIO`, an unexpected exception, or any error other
   than `ENOENT` remains immediate `PAUSE` with zero content read and no creation.
6. Preflight creates no directory, file, descriptor sidecar, wrapper, log or helper.

This rule proves absence only. It adds no writable ancestor authority. Parent creation
remains inside the frozen author transaction after all author and input validation.
Every process, content-read, output and later-gate boundary is otherwise unchanged.

## Accepted author and immutable inputs

```text
AUTHOR_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
AUTHOR_TREE_SHA256=291cf77798b652a41512902a5bc40a107afa661abf2edec53fa3f32e7158ff20
AUTHOR_ROOT_MODE=0555
AUTHOR_MEMBER_COUNT=6
AUTHOR_MEMBER_MODE=0444
AUTHOR_TOTAL_BYTES=196646

INPUT_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
INPUT_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
INPUT_PACKET_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
INPUT_PACKET_MEMBER_COUNT=902
INPUT_PACKET_FILE_COUNT=663
INPUT_PACKET_DIRECTORY_COUNT=239
INPUT_PACKET_BYTES=654147403

INPUT_DISPOSITION=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json
INPUT_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
INPUT_DISPOSITION_BYTES=8383806
TOTAL_REAL_INPUT_READ_BYTES=662531209
```

The six accepted members remain exact:

| Member | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `command-contract.json` | 3,544 | `0444` | `c413185ef0a90d1e8785655abcdbece0ce94fba42fdaba89a79c6336deb2ba40` |
| `dependency-manifest.json` | 10,921 | `0444` | `b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63` |
| `fixture-spec.json` | 476 | `0444` | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `freeze-manifest.json` | 969 | `0444` | `217e256fce5121f08a5687fba1b2ed4d11f0beeaaa7dd9fb6efe9a58c0ba2005` |
| `self-test-receipt.json` | 32,868 | `0444` | `3b01f77c48990d115e962d8798820110553962cc2145e2e177872a4ee4932092` |
| `work-item-author-v4.py` | 147,868 | `0444` | `fcfc60c21623093e75fef7d0cc88eba7481d16fe8a096b20cba3263124d1da07` |

Fresh grant-time inspection reproduced the author modes, links, sizes and hashes, the
packet root's `0555` directory metadata, and the disposition's single-link `0444`
regular-file metadata and exact size. Packet members and disposition content were not
opened.

## Exact still-absent output coordinates

```text
STAGING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
DURABLE_PARTIAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
```

All four were absent at fresh grant authoring time. Astra must repeat the corrected
no-follow preflight. Any present target, symlink/special/wrong-type component or
non-`ENOENT` error is `PAUSE` with zero process/content read/create.

## Exact authorized process

The only command is this literal twenty-member vector:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/freeze-manifest.json"
]
```

The cwd is exactly `AUTHOR_ROOT`. The environment has exactly five members:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
PYTHONDONTWRITEBYTECODE=1
PYTHONHASHSEED=0
PYTHONNOUSERSITE=1
```

Launch directly without shell, wrapper, extra argument/environment, inherited
descriptor, source copy, path substitution or alternate import.

## Transaction, outputs and ceilings

After successful preflight, at most one process may run. It independently revalidates
the accepted author and both inputs; reads each of 663 packet files and the disposition
at most once; consumes exactly 662,531,209 governed bytes; and creates no output until
the complete inputs and 902-row packet-tree identity validate.

It then performs the unchanged exclusive-create, seven-role, fixed-point, file/directory
`fsync` and atomic-publication transaction for staging and durable packets. The seven
roles are `component-work-items.jsonl`, `ownership-dispute-work-items.jsonl`,
`component-batches.jsonl`, `unresolved-pages.jsonl`, `coverage.json`,
`negative-controls.jsonl` and `manifest.json`. Success requires 1,221 component items,
19 disputes, 98,608 unresolved IDs, 30,421 paths, 1,384 edges, twenty batches and 49
pages in each output. Packet members are `0444`, packet/final directories `0555`, and
external `authoring-result.json` files `0400` under schema
`convmem.switchboard.work-item-authoring-result.v2`. Structural `PASS` cannot change
provenance/licensing `PAUSE` or any false authorization/eligibility field.

```text
MAX_PROCESS_COUNT=1
SUBPROCESSES=0
MAX_PEAK_RSS_BYTES=2147483648
MAX_WRITTEN_BYTES_PER_ROOT=2147483648
MAX_TOTAL_WRITTEN_BYTES=4294967296
NETWORK_REQUESTS=0
RUNTIME_READS=0
REPOSITORY_READS=0
RETAINED_SOURCE_READS=0
CREDENTIAL_ACCESS=0
ACQUIRED_BYTES=0
```

There is no retry, resume, repair, deletion, cleanup, partial acceptance, second input
pass or second process. Any failure preserves the exact coordinate state and returns
`PAUSE`.

## Required return and stop — satisfied

Astra returned in chat, without a repository log:

- corrected-preflight outcome and the first missing component for each absent lineage;
- process count, exit status, reported status and exact stop stage;
- input bytes by role and aggregate, output bytes by root and aggregate, peak RSS and
  every forbidden-access counter;
- all four partial/final presence states, modes and links;
- final tree identities and external result hashes/sizes when present;
- seven-role paths/modes/sizes/hashes, all cardinalities, ledger/fixed-point and
  durability counters for both outputs; and
- confirmation that process success did not self-accept or authorize another gate.

Stop immediately at `PAUSE` for any SHA/identity/type/link/mode/path mismatch, present
output, non-`ENOENT` preflight error, argv/cwd/environment drift, extra process or
descriptor, input/read/write/cardinality/schema/role/control/durability/ledger drift,
ceiling breach, forbidden access, write failure or unexpected exception. Preserve
state; do not repair, delete, resume, retry or continue.

## Explicit exclusions

This grant authorizes no further attempt; independent review; output acceptance;
origin request; network/runtime/repository/retained-source/credential access;
acquisition; ownership/license decision; repair; build; publication; CI admission;
product/test/config/inventory/R2b edit; implementation; PR `#342` update; PR creation;
merge; deployment; real OpenClaw; live data; watch activation; promotion; or Gate
D/W/D-V/E/F action. Ryan's subsequent `record` direction authorizes only this
handoff/LATEST/STATUS current-state update. It grants no diagnosis, correction or new
attempt.

## Consumed-grant disposition

Do not copy, invoke or reinterpret the former Astra launch prompt. Both grants are
consumed. The first stopped before effects at ancestor preflight; the second passed
the corrected preflight and failed closed after one launch on `W001`. A later plan may
diagnose that exact input-ID-prefix rejection, but this handoff supplies no authority
to inspect content again, change the author, create a root or launch another process.

## TL;DR

- The fresh `31d4c919…` + `d7f82fbc…` grant is consumed: corrected preflight passed,
  then the sole process exited `1` at `DEPENDENCY_CLOSURE` with `Refusal: W001: input
  ID prefix`.
- All four output coordinates remain absent. The process created no output receipt,
  result, ledger or work-item files; forbidden-access counters remained zero.
- Peak RSS was 2,059,636,736 bytes under the 2-GiB ceiling; 54,052,776 real-input
  bytes were read before the fail-closed stop.
- No retry, repair, self-acceptance, independent review, acquisition, build,
  publication, PR, merge, real OpenClaw or later gate is authorized.
