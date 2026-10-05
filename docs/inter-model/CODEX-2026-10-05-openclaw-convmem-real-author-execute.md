# Execute Handoff: Switchboard One-Shot Real Work-Item Author

**Arc:** ConvMem Switchboard  
**Date:** 2026-10-05  
**Author:** Codex supervision lane  
**For:** Astra execution lane  
**Authorization:** Ryan, 2026-10-05 — explicit `granted` response after PR `#362`
merged the reviewed current-state snapshot and Kiro returned exact-main PASS

---

## Resume state

| Field | Value |
|---|---|
| **State** | `AUTHORIZED / NOT_STARTED` — exactly one offline `author-packet` process |
| **Grant branch** | `plan/2026-10-05-openclaw-convmem-real-author-execute-grant` |
| **Plan authorization base** | `ca0397c084b2616809307249212b7153d9d8ba39` |
| **Semantic parent** | `31d4c919cfe77ae6d2fbbcb473a0fd8e0857515d` |
| **Reviewed overlay** | `d7f82fbcd3afd3887d4b3764b173958d5094ee53` |
| **Reviewed plan merge** | PR `#361`, `8d1c01762d920a91667f96182fab04c4fc583e86` |
| **Status merge** | PR `#362`, `ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c` |
| **Push status** | Grant branch must be read from its pushed origin tip before execution |
| **PR** | Not opened; execution does not authorize PR creation or merge |
| **Ryan GATE** | None for this exact one-shot real author process; every deviation or second attempt requires a new Ryan grant |

## Authoritative two-SHA grant

```text
SEMANTIC_PARENT_SHA=31d4c919cfe77ae6d2fbbcb473a0fd8e0857515d
REVIEWED_OVERLAY_SHA=d7f82fbcd3afd3887d4b3764b173958d5094ee53
AUTHORIZATION_BASE_MAIN_SHA=ca0397c084b2616809307249212b7153d9d8ba39
AUTHORIZED_ATTEMPTS=1
AUTHORIZED_PROCESS_COUNT=1
AUTHORIZED_MODE=author-packet
```

The semantic-parent and reviewed-overlay values above are the authoritative two-SHA
grant. The authorization-base, squash-merge and status SHAs are traceability and
binding checks; none may replace either governing SHA. The exact normative contract
is:

1. `docs/plans/STATUS-openclaw-convmem-integration.md`;
2. `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` §18.45, retaining
   §§18.31–18.44 unchanged;
3. `docs/plans/EXECUTION-openclaw-convmem-integration.md` §10.43;
4. `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md` M11 and §7; and
5. this handoff.

Any conflict, missing value or changed governing SHA is `PAUSE`; Astra does not choose
between readings.

## Accepted immutable author

```text
AUTHOR_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
AUTHOR_TREE_SHA256=291cf77798b652a41512902a5bc40a107afa661abf2edec53fa3f32e7158ff20
AUTHOR_ROOT_MODE=0555
AUTHOR_MEMBER_COUNT=6
AUTHOR_MEMBER_MODE=0444
AUTHOR_TOTAL_BYTES=196646
```

| Member | Size | SHA-256 |
|---|---:|---|
| `command-contract.json` | 3,544 | `c413185ef0a90d1e8785655abcdbece0ce94fba42fdaba89a79c6336deb2ba40` |
| `dependency-manifest.json` | 10,921 | `b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63` |
| `fixture-spec.json` | 476 | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `freeze-manifest.json` | 969 | `217e256fce5121f08a5687fba1b2ed4d11f0beeaaa7dd9fb6efe9a58c0ba2005` |
| `self-test-receipt.json` | 32,868 | `3b01f77c48990d115e962d8798820110553962cc2145e2e177872a4ee4932092` |
| `work-item-author-v4.py` | 147,868 | `fcfc60c21623093e75fef7d0cc88eba7481d16fe8a096b20cba3263124d1da07` |

At grant authoring time read-only inspection reproduced every mode, single link,
size and member digest. The author is immutable: do not copy, patch, import, chmod,
rename, delete, repair, regenerate or execute it outside the exact process below.

## Immutable inputs and fresh output coordinates

```text
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

STAGING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
DURABLE_PARTIAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
```

At grant authoring time the packet root was a `0555` directory, the disposition was a
single-link `0444` regular file of exactly 8,383,806 bytes, and all four output
coordinates were absent. Astra must repeat the exact no-follow metadata preflight
before any content read or creation. It may read-only hash the accepted author, but it
must not open packet members or disposition content during preflight. Any coordinate
pre-existence or identity/type/link/mode mismatch is `PAUSE` with zero processes,
zero content bytes read and no created path.

## Exact authorized process

The sole admissible command is this literal twenty-member array:

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

The cwd is exactly `AUTHOR_ROOT`. The complete environment is exactly:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
PYTHONDONTWRITEBYTECODE=1
PYTHONHASHSEED=0
PYTHONNOUSERSITE=1
```

Launch with direct `execve` semantics. No shell, wrapper, inherited descriptor,
extra argument, extra environment member, path substitution, author copy or imported
alternate source is permitted.

## Transaction and ceilings

After successful preflight, run exactly one process. It independently revalidates the
accepted author and both inputs, reads each of the 663 packet files and the disposition
at most once, and consumes exactly 662,531,209 governed input bytes. No output root may
exist before both complete inputs and the 902-row packet-tree identity validate.

The process then exclusive-creates only the exact staging and durable partial roots and
performs the frozen seven-role, fixed-point, file/directory-`fsync` and atomic-
publication transaction. Success requires, in each packet, exactly 1,221 component
items, 19 ownership-dispute items, 98,608 unresolved IDs, 30,421 paths, 1,384 edges,
twenty batches and 49 pages. Packet members are `0444`; `packet/` and final roots are
`0555`; `authoring-result.json` is `0400`. The result schema remains
`convmem.switchboard.work-item-authoring-result.v2`; structural status may be `PASS`,
but provenance/licensing remains `PAUSE` and every authorization/eligibility field
remains false.

The seven packet roles remain exactly:

```text
component-work-items.jsonl
ownership-dispute-work-items.jsonl
component-batches.jsonl
unresolved-pages.jsonl
coverage.json
negative-controls.jsonl
manifest.json
```

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
pass or second process. Failure preserves the exact coordinate state where execution
stopped and returns `PAUSE`.

## Stop conditions

Stop before effects or immediately at `PAUSE` on any pre-existing output coordinate,
governing-SHA mismatch, plan ambiguity, accepted-author mismatch, input metadata or
identity mismatch, argv/cwd/environment drift, unexpected path/type/link/mode,
additional process or descriptor, content-read count/byte drift, packet-tree mismatch,
cardinality/schema/role/control change, durability-order failure, fixed-point or
ledger mismatch, ceiling breach, forbidden access, write error, unexpected exception
or any result that cannot satisfy the complete §18.45/§10.43 contract.

Preserve any partial/final state exactly. Do not repair, delete, chmod, rename, resume,
retry, widen scope or run a second process.

## Required return packet

Return in chat, without creating a repository log:

- process count, exit status, reported status and exact stop stage;
- input bytes by packet/disposition role and aggregate;
- output bytes by staging/durable root and aggregate;
- peak RSS plus subprocess/network/runtime/repository/retained-source/credential/
  acquisition counters;
- all four partial/final presence states, modes and link counts;
- both final canonical tree identities when present;
- external SHA-256 and byte size of each `authoring-result.json`;
- exact seven-role member paths, modes, sizes and SHA-256 values for both packets;
- the 1,221 component, 19 dispute, 98,608 ID, 30,421 path, 1,384 edge, twenty-batch
  and 49-page counts for both outputs;
- ledger/fixed-point and durability counters required by §§18.31–18.45; and
- explicit confirmation that structural process success did not self-accept
  provenance, licensing, acquisition, build, publication or any later gate.

Codex then records the exact returned evidence in a plan-only result-binding overlay.
Kiro reviews that exact overlay before any independent review or later operation.
Astra stops after returning the packet.

## Explicit exclusions

This grant authorizes no second attempt; output repair or acceptance; origin request;
network, runtime, repository, retained-source or credential access; acquisition;
ownership or license decision; binary repair; build; publication; CI admission;
product/test/config/inventory/R2b change; connector implementation; PR `#342` update;
PR creation; merge; deployment; real OpenClaw; live data; watch activation;
promotion; or Gate D/W/D-V/E/F action.

It does not authorize an independent provenance/licensing review. Even two exact,
byte-identical structurally passing packets remain held for a separately planned and
Ryan-granted review.

## Copy-paste Astra launch prompt

```text
You are Astra, the sole execution lane for one bounded offline operation in Arc
ConvMem Switchboard.

Ryan authorized exactly one real work-item author process:
SEMANTIC_PARENT_SHA=31d4c919cfe77ae6d2fbbcb473a0fd8e0857515d
REVIEWED_OVERLAY_SHA=d7f82fbcd3afd3887d4b3764b173958d5094ee53
AUTHORIZATION_BASE_MAIN_SHA=ca0397c084b2616809307249212b7153d9d8ba39
AUTHORIZED_MODE=author-packet

Read the current Switchboard STATUS, Architecture §18.45, Execution §10.43,
milestone M11/§7 and this pushed handoff completely. Verify that the grant branch tip
is the pushed origin tip. Recheck the accepted six-file tree 291cf777…, packet and
disposition metadata, and all four exact absent output coordinates without opening
packet members or disposition content. Any mismatch or pre-existing coordinate is
PAUSE with zero process, zero content bytes and no created path.

If preflight passes, launch only the exact frozen twenty-member no-site author-packet
argv from the accepted final-root cwd with the exact five-key environment. Run one
process, read exactly 662,531,209 governed input bytes in one pass, create only the
four named single-assignment output coordinates, enforce 2 GiB RSS, 2 GiB writes per
root and 4 GiB total writes, and keep every forbidden-access counter zero.

Return the complete evidence packet from this handoff and stop. On any failure,
preserve the stopped coordinate with no deletion, repair, resume or retry. Do not edit
the repository, open a PR, conduct independent review or continue to another gate.
```

## Leaving / picking up checklist

**Codex:**

- [x] PR `#361` merge and Kiro exact-main PASS confirmed.
- [x] PR `#362` status merge and Kiro exact-main PASS confirmed.
- [x] Ryan's exact one-shot grant recorded.
- [x] Accepted author identities and four absent output coordinates rechecked.
- [x] Commit and push this handoff with STATUS and LATEST routing.

**Astra:**

- [ ] Run the session-start protocol and state Goal/role/system/next plus the arc.
- [ ] Resolve and read the pushed grant-branch tip.
- [ ] Verify the governing SHAs, immutable identities and four absent coordinates.
- [ ] Execute at most one exact process under all ceilings and exclusions.
- [ ] Return the complete result packet and stop.

## TL;DR

- Ryan authorized one real `author-packet` process governed by `31d4c919…` plus
  `d7f82fbc…`; accepted author tree `291cf777…` is the sole executable source.
- The immutable 654,147,403-byte packet and 8,383,806-byte disposition may each be
  read once; only the four exact absent output coordinates may be created.
- One process, 662,531,209 input bytes, at most 2 GiB RSS, 2 GiB per root and 4 GiB
  total writes, with every forbidden-access counter zero.
- Any discrepancy is `PAUSE`; no repair, retry, self-acceptance, PR, merge,
  independent review, acquisition, build, publication or later gate.
