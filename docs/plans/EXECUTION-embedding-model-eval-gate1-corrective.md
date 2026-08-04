# Gate 1 Corrective Revision Plan — Final Integration Candidate

**Status:** REVISE — final incorporation-only review requested. This plan authorizes
nothing by itself. Until it receives PASS, there will be no repository edit, model
acquisition, R2b action, production-corpus access, R3–R7 execution, Gate 2 decision,
or promotion.

## 1. Governing status and relationship to the existing runbook

\`REVISE\` remains upheld. R3–R7 and their grants remain blocked. R2b is a distinct
Ryan gate but is administratively held: the required default is a unified corrective
execution pin, so capture cannot be granted until that pin exists.

The historical Gate 1 Git object \`3b2790f50414f0445c35748e52f849c6276839f7\` is
review history only. It cannot authorize R2b or R3–R7 after this corrective revision.
The final same-tip-reviewed corrective Git object becomes the sole execution pin.

This plan supplements and selectively supersedes
\`docs/plans/EXECUTION-embedding-model-eval.md\`. Every requirement there that is not
explicitly replaced below remains binding. If the two documents conflict on a
corrective subject, this document controls.

| Original subject | Status under this plan |
| --- | --- |
| Gate 1 / Gate 2 separation; Ryan-only promotion | Remains binding |
| Exact argv, R2b V0–V6, one capture attempt | Remains binding and is extended by source and filesystem checks |
| Fake/http-fake fixture modes | Fixture-only; forbidden for every real build and scored query |
| \`--resume\` and collection reuse | Replaced: forbidden for every real build |
| R2b–R7 source pin | Replaced: exact source, import and dependency verification applies to all evidence-producing helpers |
| Fallback exercise in compare | Replaced: non-scoring Gate 1 fallback test only; scored retrieval is vector-only |
| One-shot scoring; five warmups; 20 timing repetitions | Retained and made more specific below |
| First-pilot-query latency limitation | Retained with deterministic selection and complete raw evidence |
| Collection provenance | Extended to vector content, query clones, and non-mutation proof |
| Gate 2 marker and archive | Replaced with marker-last directory, deterministic archive, and external receipt |

## 2. Status model and non-negotiable stop rules

Every phase records a \`phase_status\` of \`PENDING\`, \`VALID\`, \`INVALID\`,
\`INCOMPLETE\`, or \`QUARANTINED\`. The completed run alone records:

    technical_status: VALID | INVALID | INCOMPLETE
    evidence_verdict: BETTER | WORSE | INCONCLUSIVE | NOT_ISSUED

Identity, authorization, provenance, schema, source, collection-integrity, or
malformed-output failures make the affected phase \`INVALID\`. A mandatory measurement
that cannot complete—for example verified warm residency—makes it \`INCOMPLETE\`.
Failed attempts are preserved and quarantined.

The final \`evidence_verdict\` is \`NOT_ISSUED\` unless every mandatory phase is valid and
the final \`technical_status\` is \`VALID\`. Only a technically valid comparison may issue
\`BETTER\`, \`WORSE\`, or \`INCONCLUSIVE\`. Predeclared ANN semantic instability may produce
a valid \`INCONCLUSIVE\`; a digest mismatch, fake vector, or malformed worker result may
not.

## 3. Policy decisions frozen by this plan

1. **Execution pin:** R2b and all later phases use one final corrective pin. A
   split-pin sequence needs a new, separate Ryan exception; no attestation alone
   authorizes it.
2. **Experiment:** this is a production-swap experiment. Both models receive the
   same frozen production document and query transformations, request contract, and
   output dimension. It measures a drop-in replacement, not either model's maximum
   independently tuned capability.
3. **Authorization threat model:** operational authorization on a trusted local host
   and operating-system account. Sidecars prevent accidental wrong/replayed runs; they
   are not cryptographic proof of Ryan's or Kiro's identity.
4. **Quality target:** the production \`embedding_influenced\` pipeline is decisive.
   Exact-vector retrieval is mandatory diagnostic evidence, not a separate promotion
   test.
5. **Performance:** latency and throughput are descriptive for the quality verdict.
   Numerically frozen safety ceilings may stop/quarantine an unsafe attempt or block a
   recommendation, but cannot alter a quality verdict after results exist.
6. **Warm latency:** a warm result requires verified continuous residency. Shared-server
   reload or eviction measurements are separately labeled diagnostics and cannot
   substitute for warm p50/p95.
7. **Retries:** only acquisition retries before an evidence-producing attempt are
   allowed. Every probe, materialization, build, compare, package, archive, or receipt
   retry receives a new attempt ID, absent root, manifest, and required grant; failed
   roots remain quarantined.

## 4. Pre-patch methodology contract and C0 boundaries

Before implementation code is written, the first corrective-branch artifact after the
pre-patch receipt is a byte-stable \`methodology-v1\` fixture. It supplies the values
below; its SHA is reviewed with the corrective implementation. Code must reject an
omitted, zero-placeholder, or post-C0a change to any required field.

### C0a: freeze before acquisition or probing

C0a binds the accepted corpus identity; unchanged reviewed query JSONL SHA; relevance
and source-label review SHA; \`top_k=5\`; the canonical query-normalization algorithm
and version; the complete production document/query transform bytes and hashes;
prefix/instruction bytes; the exact production output dimension; normalization;
endpoint path and HTTP method; request-schema version; \`truncate\`; batching; timeout;
retry count; \`keep_alive\`; options object; candidate depth; filters; boosts; source
trust; recency and frozen \`as_of\`; reranking; distance metric; all ANN controls;
latency residency criteria; numerical safety ceilings; and the methodology below.

The requested dimension is the existing production dimension, not a new challenger
projection. R3 must prove both exact locally resolved model digests honor it. Failure
is a stop requiring a new C0a/plan; there is no substitution or adaptation at C0b.

The frozen inference contract is:

- Primary metric/view: paired Hit@5 in \`embedding_influenced\` retrieval; P@1 and MRR
  are secondary descriptive metrics and cannot reverse the primary verdict.
- Point estimand: each of five domains has weight 1/5; queries have equal weight
  within their domain. \`source_group_id\` affects uncertainty only and may not span
  domains. A cross-domain group is invalid.
- Uncertainty: 95% percentile CI from 100,000 domain-stratified cluster bootstrap
  replicates, fixed seed \`20260804\`. Within each domain, source groups—not individual
  queries—are resampled with replacement; all queries in a selected group travel
  together and retain the point-estimate query weights.
- Significance: one-sided, domain-stratified paired cluster sign-flip permutation test
  with 100,000 fixed-seed (\`20260805\`) draws. Each independent source group has its
  complete vector of within-domain query deltas sign-flipped as one block. The test
  statistic is the domain-equal query-weighted paired Hit@5 mean. \`p <= 0.05\` is
  required for BETTER and the symmetric test is used for WORSE.
- A non-tied independent group has nonzero mean Hit@5 delta over its member queries.
  At least 20 such groups are required. Fewer than 20 is a valid \`INCONCLUSIVE\`, not
  an implementation failure.
- Tie epsilon is exactly \`0.0\`. Bootstrap, permutation, CI, percentile, and metric
  implementations are named by algorithm/version in \`methodology-v1\`.
- Exact-vector algorithm: \`exact_vector_rank_v1\` computes cosine distance with
  float64 accumulation over the same finite float32 query/document vectors used by
  ANN, rejects zero norms, orders \`(distance ascending, UTF-8 unit_id ascending)\`, and
  applies the same frozen candidate eligibility filters. It is a raw candidate-stage
  diagnostic before lexical boosts, trust, recency, or reranking.
- ANN: \`hnsw:space=cosine\`; the methodology fixture binds all construction/search
  settings, canonical UTF-8 unit-ID insertion order, thread/concurrency settings, and
  persistent-client version. Chroma/HNSW exposes no supported run seed in this run;
  the exact seed list is \`[]\` with \`seed_control="not_exposed"\`. Independence comes
  from fresh roots and processes, fixed insertion order, and frozen concurrency.
- Six-build schedule is exactly \`baseline-0\`, \`challenger-0\`, \`challenger-1\`,
  \`baseline-1\`, \`baseline-2\`, \`challenger-2\`. It cannot be reordered for observed
  throughput, failures, thermals, or residency.
- ANN instability is material, and forces valid \`INCONCLUSIVE\`, when any condition
  occurs: (a) a primary-view top-1 ID differs for two or more query/arm pairs over the
  three realizations; (b) the mean pairwise top-5 Jaccard across all query/arm pairs
  is below \`0.98\`; or (c) the primary evidence class calculated from matched
  realization pairs (0/0, 1/1, 2/2) is not identical. The diagnostic report retains
  all values even when the final class is inconclusive.

The implementation may not select a different test, seed, tolerances, scheduler,
dimension, transform, request behavior, threshold, or decision rule.

### R3 and C0b: observe, then attest compatibility

R3 pulls only the expressly approved challenger, records pre/post model inventories,
argv, stdout/stderr bytes, exit code, timestamps, an exact request/response probe, and
the resolved local model facts. It cannot replace \`qwen3-embedding:8b\` with another
model.

C0b freezes only facts mechanically learned from R3: model tag, full digest, variant,
quantization, parameter size, observed dimension, Ollama executable/path/hash/version,
server PID/start time/store path/socket, loaded-model state, and a pass/fail
compatibility attestation against C0a. On a passing attestation, C0b compiles and
hashes two authoritative arm-configuration byte files solely from the unchanged C0a
contract and those learned identity facts. The later materializer may only copy these
exact bytes into arm roots; it cannot generate alternate effective configuration.
C0b may not change a transform, requested dimension, prefix, endpoint, option, retry,
threshold, safety ceiling, ANN rule, statistic, or decision rule.

After implementation and same-tip review—not before—the execution packet also freezes
the exact-search, statistical, and ANN-repeatability implementation hashes; dependency
versions; and the final approved source Git object.

## 5. Query lifecycle and canonical validation

The real pilot has exactly 40 rows: eight per approved domain. Before R2b, independent
review approves the final canonical JSONL bytes and the R2b packet binds that SHA.
Each row requires namespaced \`relevant\`, nonempty \`source_refs\`, \`source_group_id\`,
domain, \`recipe_stratum\`, \`relevant_complete\`, \`top_k=5\`, author/reviewer provenance,
and \`query_normalized_sha256\`. Legacy \`acceptable_ids\` remains supported generically
but is forbidden in this pilot.

After B-Accept, the validator runs again against the accepted package using the same
unchanged query bytes. It proves count/domain balance, unique IDs, no normalized-query
duplicates, normalized source-group/domain compatibility, no duplicate/conflicting
relevance, namespace correctness, unique resolution through multimaps, alias
normalization, source-reference resolution, stratum agreement, and review support for
any completeness claim. If a query, label, source reference, or stratum changes after
capture, the capture is ineligible unless R2b is rerun under a new packet or Ryan
approves a separate exception proving the change cannot affect capture.

## 6. Source, environment, and model/request identity

Every R2b–R7 command and every evidence-producing helper—capture, B-Accept generator,
query validator, C0 materializer, R3 runner, all builders, compare, evidence writer,
archive builder, and receipt generator—independently verifies repository root, exact
Git object, tracked-tree SHA-256, clean tracked worktree, untracked and ignored
import-shadow inventory, submodule/LFS state, Python executable path/hash, isolated
import controls, \`PYTHONPATH\`, user-site state, \`sitecustomize\`/\`usercustomize\`,
critical module paths/hashes, dependency-lock SHA-256, resolved dependency inventory,
and native-library versions. A 40-hex Git object is recorded as
\`approved_source_git_oid\`; it is never labeled a SHA-256.

The model contract binds tag, local digest, variant, quantization, dimension, transform
IDs/hashes, prefix/instruction bytes, normalization, truncation, endpoint, method,
schema version, request fields, options, timeout/retry/batch policies, \`keep_alive\`,
host, proxy-neutralized loopback endpoint, Ollama binary/server identity and loaded
state. Digest/loaded-state receipts occur before and after each build, at worker start,
and after comparison. Per-request Ollama timing fields are captured, but no separate
identity-discovery call is made inside a timed interval.

Environment evidence uses an allowlist only: relevant Ollama/Python/thread/locale/
timezone/hardware variables and proxy presence with redacted or approved non-secret
identity. Credentials record only variable name, present/absent, and redacted class;
no credential value or credential hash is retained. CPU/RAM/GPU/driver/runtime,
OS/kernel, disk, package/native versions, and model residency state are recorded.

## 7. Authorization, attempts, and filesystem isolation

Every evidence-affecting operation has an operation-specific manifest, attempt ID,
command/argv/environment/exit evidence, source verification, quarantine semantics, and
an absent output root or absent output file. Human-authorized operations are R2b,
B-Accept, R3, C0 materialization, each of the six R4/R5 realizations, and R7. Evidence
assembly, deterministic archive creation, and release-receipt creation are mechanically
bound suboperations, not implicit human grants; they still validate their manifest and
source identity. No helper may run unbound.

Each human sidecar binds \`grant_id\`, \`attempt_id\`, \`run_id\`, operation,
manifest-body hash, approved paths, approved Git object, not-before, optional expiry,
and maximum invocation count one. Consumption is atomic: validate; atomically move to a
consumed state; fsync a consumption receipt; then begin. A consumed sidecar is never
restored, even after failure. New attempt means new root, manifest, sidecar, and
timestamped record.

Filesystem controls apply to every sensitive read/write:

- Approved-root containment is verified by canonical path components, never string
  prefixes. Parent and leaf components are opened no-follow; any symlink is rejected.
- Arm roots are siblings, absent before creation, and proven non-overlapping and
  non-nested. Each attempt owns a complete root: authorization, config, immutable
  inputs, probes, build, Chroma, logs, and receipts. Existing roots are invalid rather
  than reusable.
- Inputs are read once, copied with atomic no-follow creation into the attempt root,
  SHA-256 hashed, and parsed from those copied bytes. A later path reopen is not trusted.
- Mutable inputs and all final evidence artifacts must be regular files with
  \`link_count=1\`. Device/inode/mode receipts are taken before and after sensitive
  operations. Evidence packages forbid symlinks and hard links entirely.
- Writers use a temporary regular file in the target directory, \`fsync\`, atomic rename,
  and directory \`fsync\`; archive creation rejects anything other than regular files and
  approved directories.

## 8. Deterministic configuration and enrichment materialization

Each arm has one C0b-authoritative, manifest-bound configuration byte file and one
identical copy in its own absent attempt root. The materializer reads the authoritative
bytes once, hashes and parses those same bytes, then copies them with atomic no-follow
creation. Model, host, adapter, transformations, request contract, collection paths,
enrichment, retrieval controls, and output settings are derived solely from the parsed
bytes. Duplicate or overriding CLI settings are rejected.

The materializer is its own granted attempt. It copies the approved enrichment bytes
into each arm root; records source/destination content SHA, device/inode, row count,
and semantic decision-set fingerprint; and performs a schema-aware cross-arm semantic
diff. Only explicitly approved model-identity and isolated path fields may differ.
The actual runtime enrichment reader emits its resolved path, file SHA, inode/device,
row count, parser version, and semantic fingerprint. A derived parent-directory path
does not count as reader provenance.

## 9. Vector, collection, and query immutability

Real builds require \`embed_mode=ollama\`, \`fallback_policy=forbid\`, and \`resume=false\`.
Fake/http-fake adapters, existing outputs, resume/reuse, wrong digest, wrong dimension,
non-finite vectors, zero norms where normalization requires a norm, and failed readback
are invalid.

Vectors are converted to float32 once before collection write. For actual stored/read
back values, normalize \`-0.0\` to \`+0.0\`, reject NaN/infinity, and compute:

    matrix_fingerprint_v1 = SHA-256(
      for each UTF-8 unit_id sorted lexically:
        uint32_be(length(unit_id_bytes)) || unit_id_bytes ||
        uint32_be(vector_dimension) || float32_little_endian(vector)
    )

The result includes canonical unit ordering, dimension/finite/norm diagnostics, sample
vector hashes, and both build-time and readback matrix fingerprints. It is exact
within-run stored-artifact integrity. Cross-build reproducibility is separately
tolerance-based and semantic; it never demands cross-hardware bit identity without
proof.

The authoritative build collection is never silently queried. The selected default is
the **disposable-query-clone** mode: a separately authorized clone is created from the
authoritative collection, its logical/vector identity is proved before query, and all
scoring occurs only in the disposable root. Clone mutation is allowed only there and is
reported as working-copy mutation. A future proven-non-mutating mode needs full
pre/post equality under the frozen rule, no create-or-open path, absent-collection
failure, and no unapproved WAL/journal/metadata writes before it can replace this
default.

For each result, the worker produces one query vector and its float32 fingerprint,
dimension, finite/norm checks, model digest, and transform/request identity. ANN and
exact-vector retrieval consume that same captured query vector and the same stored
document vectors/filters/distance metric; neither re-embeds corpus nor regenerates the
query.

## 10. Six realizations, single-execution capture, and fail-closed comparison

There are three separately granted fresh realizations per arm. \`baseline-0\` and
\`challenger-0\` are the primary collections; \`*-1\` and \`*-2\` are ANN repeatability
realizations. All six must be technically valid for a final valid package.

There are three execution classes:

1. **Decisive quality capture:** each \`(query_id, arm, view, collection_realization)\`
   executes exactly once. \`embedding_influenced\` is primary and \`exact_vector\` is
   diagnostic.
2. **ANN repeatability capture:** the same rows execute exactly once for each of all
   three independently built realizations; derived stability evidence follows C0a.
3. **Latency capture:** repeated calls are timing-only and never supply quality ranks
   or quality metrics.

Every raw quality result is stored before aggregation with query/domain/query-text SHA,
top-k IDs, scores/distances, collection identity, view, timestamps, worker identity,
model digest, query-vector fingerprint, retrieval mode, vector attempt/fallback flags,
and stdout/stderr byte-file hashes and paths. A semantic validator rejects duplicate or
unknown hit IDs, wrong/missing IDs or model/view/collection identity, fewer than k hits
without frozen explanation, non-finite scores, invalid distances, filters not frozen,
fallback use, missing vector evidence, malformed output, duplicate rows, or nonzero
worker exit. No failure becomes a retrieval miss.

Scored workers must emit \`retrieval_mode="vector"\`, \`vector_query_attempted=true\`, and
\`fallback_used=false\`. The broad fallback path is exercised only by a separate,
non-scoring Gate 1 test with distinct roots and run IDs.

## 11. Latency and throughput evidence

Warm latency is descriptive in model selection but mandatory for Gate 2 package
completeness. The latency query is the first canonical query by UTF-8 \`query_id\` in the
already frozen JSONL. Its ID, text SHA, domain, character count, token count, and
selection rule are reported.

For each view, five discarded warmups and twenty timed repetitions are retained. Arm
and view order are counterbalanced by a frozen four-cycle Latin schedule; the raw
monotonic-nanosecond samples, per-request server \`load_duration\`, \`total_duration\`,
prompt/token fields, order, and raw outputs are retained. p50/p95 use the frozen
nearest-rank percentile algorithm over unrounded raw samples; its implementation hash
is later pinned. Process launch-to-ready, model-load, embedding request, Chroma query,
end-to-end cold request, and shutdown are separate labels.

Before, passively during, and after the timed block, receipts prove both intended model
digests are resident in the approved server/process and no timed request reloaded or
evicted a model. If this fails, warm latency is \`INCOMPLETE\`; shared-server eviction is
reported only as a separate descriptive diagnostic and cannot replace warm p50/p95.
Single-run serial per-document embedding plus batched index-write throughput is
descriptive, source-bound, and not an inferential performance comparison.

## 12. Fixture-only Gate 1 integration testing

After plan approval, corrective implementation may use a dedicated \`TEST_ONLY\` fixture
lane: synthetic/dedicated corpus, dedicated configs, ephemeral test-only Chroma/attempt
roots, and an already-installed approved test embedding model. It must not access R2b
or an accepted production corpus, production Chroma, live configuration, or Gate 2
evidence paths. Outputs are clearly marked, retained or cleaned under a stated test
policy, and cannot be evidence.

No challenger pull occurs in this lane. A real-Ollama positive integration test may use
only that installed test model; a test-model pull requires a separate explicit Ryan
test-acquisition grant. The test suite includes both positive paths (valid capture
V0–V6, valid real fixture build, valid worker, valid three-realization suite, valid
package/receipt) and adversarial rejection of fake/http-fake real mode, resume,
existing roots, digest mismatch, source/dependency mismatch, enrichment loss/SHA error,
fallback, malformed workers/packages, link/race paths, clone/provenance violations,
and archive nondeterminism.

## 13. Gate 2 package and release construction

An absent evidence directory receives raw evidence, raw stdout/stderr files, reports,
environment/attempt history, Copilot audit, Kiro verdict, recommendation, and a
canonical inventory. \`inventory_root_v1\` is SHA-256 over lexically sorted normalized
relative paths, each encoded as \`uint32_be(path_byte_length) || UTF-8 path || raw
32-byte file SHA-256 || uint64_be(size) || uint8(executable)\`. It excludes the marker,
archive, and external receipt. Times, ownership, and links are not inputs; links are
forbidden.

After every non-marker artifact and inventory is fsynced, write
\`gate2_evidence_manifest.json\` last. It contains the inventory root, every artifact
identity, source/run/query/model/config/build identities, final \`technical_status\`,
\`evidence_verdict\`, recommendation, \`not_promotion_authority=true\`, and the marker
write receipt. Only then create the deterministic archive: sorted UTF-8 path order,
regular files only, normalized mtime=0, uid/gid=0, empty owner names, normalized
0644/0755 permissions, GNU tar plus gzip \`-n -9\`, and an archive-recipe identifier,
tool version, and recipe SHA. The archive SHA is external to the directory.

The external release receipt records marker-body SHA, inventory-root SHA, archive SHA,
archive recipe identity/SHA, approved Git object, constituent run IDs, Kiro review
identity/timestamp, and attestation type. Kiro reviews and signs/attests to this receipt
and archive according to the operational—not cryptographic—threat model. Ryan alone
records Gate 2 and any promotion decision.

## 14. Execution sequence after a PASS

1. Capture the pre-patch repository/worktree receipt, including shared-checkout
   branch/commit/porcelain/untracked/ignored inventory and corrective worktree state.
2. Add the pre-patch methodology fixture; implement and test only corrective Gate 1
   hardening in the fixture-only lane.
3. Establish final merged execution commit; conduct same-tip review of that exact
   object; issue the new corrective execution pin.
4. Prepare/review final query bytes, bind their SHA into R2b, then issue a separate
   Ryan R2b grant under the unified pin.
5. B-Accept, followed by unchanged-byte query validation against the accepted package.
6. C0a freeze; R3 acquisition/probe; C0b facts/compatibility freeze and authoritative
   configuration-byte generation; then granted configuration/enrichment materialization.
7. Grant and execute the six scheduled R4/R5 realization attempts; clone and validate
   collections; grant R7 and perform raw quality/ANN/latency capture.
8. Construct immutable Gate 2 evidence, deterministic archive, and external receipt;
   obtain independent Copilot safety audit and Kiro exact-package review; Ryan separately
   decides Gate 2 and promotion.

## 15. Incorporation matrix for the final review

| Review amendment | Incorporated in |
| --- | --- |
| Restored filesystem authorization and TOCTOU controls | §7 |
| Restored deterministic config/enrichment materialization | §8 |
| All contract choices fixed at C0a; C0b facts only | §4 |
| Pre-patch methodology versus post-review implementation hashes | §4 |
| R7/package/archive/receipt authorization coverage | §7 and §13 |
| Mechanically enforced collection immutability via default clone | §9 |
| Fixture-only real-Ollama integration-test lane | §12 |
| Canonical signed-zero handling and stored-vector fingerprint | §9 |
| Phase status distinct from final technical/evidence status | §2 |
| Mandatory-but-descriptive warm latency | §3 and §11 |
| Secret-safe provenance; raw stdout/stderr retention | §6, §10, §13 |
| Query normalization/group-domain rule and six-build schedule | §4 and §5 |
