# Milestone Execution Plan — ConvMem–OpenClaw

**Status:** READY FOR ASTRA ADVERSARIAL REVIEW, THEN KIRO EXACT-TIP REVIEW,
THEN RYAN'S BOUNDED T0–T5 EXECUTE DECISION. No implementation is authorized.

**Arc:** none (ad-hoc integration)

## 0. Authority, scope, and interpretation

This is a sequencing and supervision overlay. Its semantic parent is exactly:

```text
SEMANTIC_PARENT_SHA=cd9d2698b7423f907b552bc9118a0af523018ca9
CODE_BASELINE_SHA=7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
ARCHITECTURE=docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
EXECUTION=docs/plans/EXECUTION-openclaw-convmem-integration.md
```

The two parent documents define every schema, field, hash, state transition,
interface, error, limit, identity, test case, and allowed path. This overlay
does not replace, loosen, or reinterpret them. A conflict stops work and goes
to Codex/Kiro; Grok must not choose between readings. The authorized initial
build is only the parent's synthetic T0–T5 Gate B/C fixture. Gate D real
runtime, Gate W governed writes, Gate D-V value evaluation, Gate E pilot/live
use, Gate F expansion, watch configuration, and promotion remain separately
blocked.

Review and authority order is mandatory:

1. Astra adversarially reviews this exact overlay plus its exact semantic
   parent and reports `BUILD PASS` or concrete corrections.
2. After any correction, Kiro reviews the same exact overlay/parent revision
   and reports binary design/scope `PASS` or `FAIL`.
3. Ryan may then grant only bounded T0–T5 implementation by naming both exact
   SHAs and the scope. Silence, an earlier grant, or a broader aspiration is
   not authorization.

## 1. State ledger

| State | Items |
|---|---|
| **Specified** | All parent Architecture §§4, 6–15 and Execution §§2–10; the strict three-tool reader; fixture publication; T0–T5 protocol fakes; cases 1–58 and their gate ownership. |
| **Implemented** | Existing legacy ConvMem behavior at `CODE_BASELINE_SHA`; none of the new strict T0–T5 capability is claimed implemented. |
| **Tested** | Planning-document identity plus exact-tip Astra and Kiro reviews of the semantic parent; this overlay has not yet been reviewed, and no T0–T5 executable acceptance test has run. |
| **Assumed** | The separately provisioned test runtime can supply the exact versions and bytes frozen by the parent. This is a provisioning assumption, not permission to substitute versions or host libraries. |
| **Unresolved** | Gate D authentication/distribution/containment; Gate W production admission route; Gate D-V experiment packet; Gate E web-development pilot; watch repository-knowledge indexing; all live configuration and promotion values. None blocks synthetic T0–T5. |

## 2. Dependency order

```text
M0 baseline → M1 preservation contract → M2 authority boundary
→ M3 data/state/failure → M4 T0–T5 adapter/protocol build
→ M7 fixture recovery checks → M8 audit evidence → M9 adversarial suite
→ M11 bounded conformance review

M5 Gate W ─┐
M6 Gate D ─┼→ M10 Gate D-V/Gate E pilot → M11 complete-integration review
           └─ each remains blocked pending its own plan, reviews, and grant
```

M0–M4 and the fixture portions of M7–M9 are the only implementable scope in
the initial grant. M5, real-runtime M6, production M7/M8, M10, and the
complete-integration part of M11 are decision gates, not Grok work.

## 3. Milestones

### M0 — Current-state audit and frozen baseline

1. **Name and purpose:** Establish exact, reproducible starting bytes.
2. **Architectural outcome:** Implementation is based on `CODE_BASELINE_SHA`
   and governed by `SEMANTIC_PARENT_SHA`; no silent rebase or ambient state.
3. **Affected surfaces:** Git worktree/branch and read-only inventories only;
   no product file changes.
4. **Preconditions/dependencies:** Astra PASS, Kiro PASS, and Ryan's exact
   T0–T5 grant; clean isolated worktree.
5. **Implementation tasks:** Record base/tip/upstream; install repo-local Git
   settings; inventory tracked files, dependency versions, protected bytes,
   and the parent-defined allowlist.
6. **Tests/evidence:** `git status --short`, exact SHA checks, source manifest,
   protected-byte/mode comparison, and dependency inventory.
7. **Invariants:** No live data/config access; no OpenClaw process; no edit on
   `main`; semantic parent remains exact.
8. **Forbidden changes:** Fetch-derived baseline substitution, rebase, schema,
   config, credential, persistent-state, permission, or dependency mutation.
9. **Done:** Clean implementation branch at the exact baseline with recorded
   inventories and zero implementation diff.
10. **Ryan confirmation:** Yes, once before M0; no routine reapproval after an
    exact grant unless a stop condition occurs.
11. **Live inspection:** Supervisor checks branch/base, status, diff, tracked
    inventory, dependencies, grant text, and protected-byte report.
12. **Verdict:** Separate ConvMem verdict; OpenClaw is not run.

### M1 — ConvMem preservation and integration contract

1. **Name and purpose:** Encode the frozen strict contract without changing
   legacy ConvMem semantics.
2. **Architectural outcome:** Closed schemas, canonical vectors, component
   inventories, legacy-byte preservation, and reject-only profile routing.
3. **Affected surfaces:** The exact Gate B/C schemas in parent Execution §2;
   `mcp_server.py` reject-only change; optional `requirements.txt` change only
   to `idna==3.18`; `tests/fixtures/openclaw_strict/**` and named strict tests.
4. **Preconditions/dependencies:** M0 complete; parent schema inventory and
   component sets copied exactly.
5. **Implementation tasks:** Implement T0 schema validators, fixture manifest,
   known-answer hashes/IDs, two independent canonical parsers, five component
   walkers, and protected-input mutation controls.
6. **Tests/evidence:** Parent cases 1–4, 40–44, 49–52, 58 as assigned to Gate
   B; duplicate/unknown/reordered/missing-null rejection; exact envelope-byte
   preservation; independent digest arrays.
7. **Invariants:** Legacy IDs, envelope UUIDs, provenance bytes, approval,
   signing, durable admission, backups, recovery, and CLI behavior unchanged.
8. **Forbidden changes:** Protected helper edits; automatic migration,
   ingestion, redistillation, inferred consent, or Chroma-as-authority.
9. **Done:** Independent references agree; every deliberate inventory/hash
   mutant fails; only allowed files differ.
10. **Ryan confirmation:** No, within the exact T0–T5 grant; yes for any core
    data-model, trust, signing, approval, or provenance change.
11. **Live inspection:** Supervisor checks diff, file list, schema inventory,
    dependency delta, known-answer output, negative controls, and commit.
12. **Verdict:** ConvMem verdict.

### M2 — OpenClaw boundary and authority model

1. **Name and purpose:** Make OpenClaw a bounded reader/orchestrator only.
2. **Architectural outcome:** Exactly three aliases/tools, zero resources,
   immutable operator-owned audience, untrusted retrieved content, and no
   governance authority.
3. **Affected surfaces:** `openclaw_strict_server.py`,
   `integrations/openclaw-convmem-reader/{package.json,openclaw.plugin.json,index.js,test/connector.test.mjs}`,
   strict scope/server/connector tests.
4. **Preconditions/dependencies:** M1 contract bytes and vectors pass.
5. **Implementation tasks:** Add only `search`, `unresolved`, `related` and
   aliases `convmem_search`, `convmem_unresolved`, `convmem_related`; enforce
   immutable audience, static dispatch, raw-evidence wrapping, and production
   `runtime_not_qualified` refusal.
6. **Tests/evidence:** Exact tool/resource/template enumeration; wrong profile,
   selector, peer, path, alias, environment, and fake-selection negatives;
   prompt-injection strings remain data.
7. **Invariants:** OpenClaw cannot approve, sign, admit, mutate, promote,
   capture, index, widen scope, or treat evidence as instructions.
8. **Forbidden changes:** Native OpenClaw memory, `ask`, global search,
   dynamic dispatch, ACP, subagents, channels, remote inference, credentials,
   or ordinary plugin registration.
9. **Done:** Three-tool/zero-resource surface passes and every authority-
   escalation attempt is denied before effect.
10. **Ryan confirmation:** No within fake T0–T5; yes before any new OpenClaw
    permission, real process, plugin install, or tool action.
11. **Live inspection:** Supervisor checks manifest/API diff, permissions,
    exact enumeration, refusal evidence, dependencies, and unsupported claims.
12. **Verdict:** OpenClaw verdict plus integration boundary verdict.

### M3 — Data flow, control flow, state, persistence, and failure behavior

1. **Name and purpose:** Implement the frozen T1–T2 authority/state machine.
2. **Architectural outcome:** Full-bound canonical reduction, conserved
   authority, immutable publication, fail-closed recovery, and display-only
   query filtering.
3. **Affected surfaces:** `bound_read_scope.py`, `strict_grounding.py`,
   `strict_evidence_state.py`, `strict_projection_publisher.py`,
   `strict_projection.py`, their schemas and named tests.
4. **Preconditions/dependencies:** M1–M2 pass; exact issuer/source inventories
   and identity algorithms frozen.
5. **Implementation tasks:** Implement enrollment/genesis, strict identities,
   original-admission qualification, cumulative authority, fence→intent→head
   advance→cold build→publication order, full publication CAS, deterministic
   state, rollback/rebuild/recovery, and persisted expiry.
6. **Tests/evidence:** Parent cases 5–27, 40–44, 49–52 and assigned 55;
   fault injection at every write/fsync/rename/pointer boundary; two fresh-root
   reproductions and independent reducer/reference results.
7. **Invariants:** Revocation/supersession permanent; late evidence cannot
   upgrade admission; rollback never restores authority or renews lifetime;
   ambiguity is unavailable/quarantined.
8. **Forbidden changes:** Query-time reducer, implicit add, authority rollback,
   generation-only CAS, self-authentication, mutable/global store, or meaning-
   changing redistillation.
9. **Done:** Crash/retry/recovery matrix is deterministic; rejected candidates
   do not rewrite history; admitted terminal actions survive projection faults.
10. **Ryan confirmation:** No for exact fixture implementation; yes for any
    persistent format/migration or rollback/recovery semantic change.
11. **Live inspection:** Supervisor checks state/schema diff, persistent-file
    writes in tests, fault output, CAS evidence, changed permissions, commits.
12. **Verdict:** ConvMem verdict.

### M4 — Adapter and protocol implementation (bounded T0–T5)

1. **Name and purpose:** Complete the executable synthetic Gate B/C fixture.
2. **Architectural outcome:** Read-only file CLI/MCP, uninstalled connector,
   and controller/supervisor protocol cores operate only through the fixed
   `FixturePlatform` and injected `spawn` port.
3. **Affected surfaces:** The eight parent-listed Python modules; exact Gate
   B/C schemas; the four connector files; `tests/fixtures/openclaw_strict/**`;
   the thirteen named strict test files; reject-only `mcp_server.py`; optional
   exact idna pin.
4. **Preconditions/dependencies:** M0–M3; separately supplied exact runtime
   prefix; no contract contradiction.
5. **Implementation tasks:** Execute parent T0–T5 in order: preflight/refusal,
   fixtures/oracles, identity/state, authority/publication, CLI/MCP, connector,
   then fake controller/manager/supervisor.
6. **Tests/evidence:** Only the parent §5.1 isolated runner with exact three
   suites, fixed selected nodes/four exclusions, two fresh roots, capacity and
   process/import/mount/FD/network evidence.
7. **Invariants:** Fake is unselectable from production; actual OpenClaw,
   authentication, provider, containment, distribution, live data, and Gate W
   remain unclaimed.
8. **Forbidden changes:** Any unlisted file; host fallback; real gateway/model;
   arbitrary command/mount/suite; extra dependency/resolver/issuer; live config.
9. **Done:** Assigned Gate B/C cases pass reproducibly at one clean SHA; TEST
   may become PASS only for that bounded set.
10. **Ryan confirmation:** Initial exact T0–T5 grant required; no per-step
    approval for conforming work; any stop condition returns to Ryan/Codex/Kiro.
11. **Live inspection:** At every T checkpoint inspect diff, file list, commit,
    test output, dependencies, schemas/data, permissions, plan deviations, and
    evidence-backed claims.
12. **Verdict:** Both ConvMem and OpenClaw/integration verdicts.

### M5 — Memory eligibility, write, retrieval, and approval policy (Gate W)

1. **Name and purpose:** Preserve governed memory admission and writes.
2. **Architectural outcome:** The parent-specified Gate W policy is realized
   only through an independently reviewed governed CLI, never by OpenClaw.
3. **Affected surfaces:** Later-only Gate W schemas and
   `governed_admission.py`; exact paths must be named by a future packet.
4. **Preconditions/dependencies:** M4 PASS; separate architecture/execution
   packet; Astra/Kiro review; Ryan Gate W grant.
5. **Implementation tasks:** **BLOCKED.** Future packet must bind eligibility,
   unitization, proposal, approval, signing, provenance, admission, recovery,
   retrieval, and rejection semantics to exact existing authorities.
6. **Tests/evidence:** Future case 56 plus assigned 41–44, 49, 51–52 using
   disposable stores; unauthorized/self-approved/poisoned writes must fail.
7. **Invariants:** Agents propose; Ryan locks. Approval, admission, durable
   storage, derivative projection, and publication remain separate.
8. **Forbidden changes:** Autonomous writes, self-approval, silent migration,
   automatic ingestion/redistillation, inferred authorization, live data use.
9. **Done:** Not reachable in this plan revision; requires future reviewed
   packet and separate PASS evidence.
10. **Ryan confirmation:** Mandatory before design lock, implementation,
    persistent storage/migration, and activation.
11. **Live inspection:** Future supervisor inspects every data-model, trust,
    writer, migration, approval, provenance, and persistence change live.
12. **Verdict:** Separate ConvMem verdict; OpenClaw must remain denied writes.

### M6 — Permissions and real tool-use integration (Gate D)

1. **Name and purpose:** Qualify a real sealed OpenClaw runtime boundary.
2. **Architectural outcome:** Actual authentication, containment,
   distribution, manager ownership, mounts, peers, and local inference are
   proven without transferring authority.
3. **Affected surfaces:** **UNRESOLVED** actual adapters, package/image,
   service/unit, socket, filter, UID/GID, model/provider, and config paths.
4. **Preconditions/dependencies:** M4 PASS; exact Gate D packet resolving
   C-RUNTIME/D-CONTAINMENT/D-DISTRIBUTION; Astra/Kiro review; Ryan grant.
5. **Implementation tasks:** **BLOCKED.** Grok must not infer adapters or
   credentials from the fixture.
6. **Tests/evidence:** Repeat parent cases 1–4 and real portions 28–36, 38–39,
   45–47, 53–55; prove actual isolation, auth, empty-domain retirement, and
   no ambient credential/tool access.
7. **Invariants:** ConvMem is source of truth; runtime sees only committed
   public projection; no private authority files; evidence has no instruction
   authority.
8. **Forbidden changes:** Dummy credentials, shared host inference, permissive
   mounts, unbounded tools/network, fake-derived qualification, autonomous acts.
9. **Done:** Not reachable until exact real-runtime design and evidence exist.
10. **Ryan confirmation:** Mandatory for every new permission, tool, service,
    user, socket, mount, network, model/provider, or external configuration.
11. **Live inspection:** Future supervisor inspects privilege/config/package
    diffs and actual process/mount/network/peer evidence before each boundary.
12. **Verdict:** Separate OpenClaw verdict and integration verdict.

### M7 — Concurrency, rollback, and recovery

1. **Name and purpose:** Falsify races and recovery claims.
2. **Architectural outcome:** T0–T5 fake concurrency obeys the frozen lock,
   CAS, release/revoke, freshness, manager, and quarantine rules; production
   behavior remains gated.
3. **Affected surfaces:** Publisher, controller, supervisor, connector cores;
   recovery/revocation/controller/supervisor tests and fixture event scripts.
4. **Preconditions/dependencies:** M3 and M4 implementation complete.
5. **Implementation tasks:** Script concurrent writes, stale CAS, duplicate
   operations, blocked consumer, cancellation, partial frames, crashes,
   detached descendants, stale receipts, clock/boot changes, rollback faults.
6. **Tests/evidence:** Deterministic event traces, fault matrices, retained
   exact failed roots on uncertain teardown, no retry after uncertain delivery.
7. **Invariants:** One active+eight pending connector calls; one turn/no turn
   queue; supervisor cannot attest emptiness; rollback is serving-only.
8. **Forbidden changes:** Retry/rerun uncertainty, lock widening, old-head or
   expiry restoration, cleanup-as-proof, destructive recovery, implicit add.
9. **Done:** All fixture races and rollback failures reach the specified state
   with independent traces in two fresh roots.
10. **Ryan confirmation:** No for frozen fixture tests; yes to change rollback,
    recovery, persistence, limits, or production concurrency behavior.
11. **Live inspection:** Supervisor checks race seeds/events, traces, retained
    state, timeout changes, code diff, tests, and unsupported success claims.
12. **Verdict:** ConvMem plus integration verdict; real-runtime verdict deferred.

### M8 — Observability and audit trails

1. **Name and purpose:** Make every bounded result attributable and reviewable.
2. **Architectural outcome:** Evidence binds plan SHA, implementation SHA,
   source/runtime/component hashes, selected tests, process trace, and outcome
   without creating a new authority source.
3. **Affected surfaces:** Fixture manifest/results under test-owned paths and
   implementation handoff; no production telemetry or live ledger write.
4. **Preconditions/dependencies:** M4 and fixture M7 PASS.
5. **Implementation tasks:** Emit canonical inventories, labels `STATIC`,
   `FAKE`, `DISPOSABLE_KERNEL`, or `REAL`, exact skips/exclusions, timing,
   output, tmp usage, negative controls, and changed-file/protected-byte proof.
6. **Tests/evidence:** Reproduce twice; compare canonical evidence; prove no
   full discovery; exact three-tool inventory; no mtime/cache/file mutation.
7. **Invariants:** Audit evidence is not approval, signing, admission,
   qualification, manager emptiness, or promotion.
8. **Forbidden changes:** Live telemetry, secrets, private paths, fabricated
   provenance, omitted failures, unsupported “all 58 passed” claim.
9. **Done:** Reviewer can reproduce every bounded claim from one clean SHA.
10. **Ryan confirmation:** No for fixture evidence; yes for any persistent/live
    audit store, telemetry, external sink, or ledger mutation.
11. **Live inspection:** Supervisor checks raw outputs, labels, hashes,
    exclusions, skips, capacity, new dependencies, and claim/evidence mapping.
12. **Verdict:** Separate ConvMem, OpenClaw, and integration evidence verdicts.

### M9 — Adversarial testing

1. **Name and purpose:** Attack every trust and failure boundary before review.
2. **Architectural outcome:** Parent cases 1–58 are reported by owning gate;
   fixture success cannot stand in for blocked real/live gates.
3. **Affected surfaces:** Only named T0–T5 test and fixture paths.
4. **Preconditions/dependencies:** M1–M4 and fixture M7–M8 complete.
5. **Implementation tasks:** Run the matrix in §5 below, independent oracles,
   enforcement-removal mutants, and the fixed isolated suites.
6. **Tests/evidence:** Exact input/expected/evidence triples for every named
   threat; two fresh-root reproductions; failed mutants.
7. **Invariants:** Leakage-safe fixtures; no credentials/live data; no broadened
   test selection, permissions, or scope to make tests pass.
8. **Forbidden changes:** Skips, new deselections, mocked-success denial,
   implementation-derived expected values, host execution called acceptance.
9. **Done:** Every in-scope row PASSes or the milestone is BLOCKED with retained
   evidence; out-of-scope rows remain explicitly untested/blocked.
10. **Ryan confirmation:** No to run frozen disposable tests; yes for live,
    destructive, costly, irreversible, or permission-changing tests.
11. **Live inspection:** Supervisor checks commands, selected node IDs,
    outputs, negative failures, fixtures, resource bounds, and deviations.
12. **Verdict:** Both, separated by gate and evidence class.

### M10 — Limited web-development pilot (Gate D-V then Gate E)

1. **Name and purpose:** Measure whether the integrated system improves a
   bounded web-development task without weakening governance.
2. **Architectural outcome:** A leakage-safe, pre-registered comparison binds
   episode, target, probe, capture, trace, action, and outcome identities.
3. **Affected surfaces:** **UNRESOLVED** pilot corpus, tasks, scoring rubric,
   trace store, capture policy, target site, and isolated runtime packet.
4. **Preconditions/dependencies:** M5 Gate W PASS if writes are evaluated; M6
   Gate D PASS; separately reviewed Gate D-V methodology and Gate E grant.
5. **Implementation tasks:** **BLOCKED.** Future plan must select one reversible
   non-production web-development task, baseline/control, success measures,
   leakage controls, human authorization points, rollback, and stop rules.
6. **Tests/evidence:** Predeclared quality, substance, technical, continuity,
   context-transfer, rework, and safety outcomes; blinded/independent scoring;
   complete trace and rollback proof.
7. **Invariants:** No production target by default; no automatic capture/write;
   no cross-arm leakage; no outcome-based identity rebinding or scope drift.
8. **Forbidden changes:** Expanding beyond web development, live deployment,
   consequential external action, post-hoc metric changes, promotion by result.
9. **Done:** Not reachable until Gate D-V and Gate E packets are reviewed and
   Ryan grants exact target/actions; pilot PASS is not promotion.
10. **Ryan confirmation:** Mandatory for methodology, target, external actions,
    capture/write permissions, live data, and every irreversible step.
11. **Live inspection:** Future supervisor checks pre-registration, identities,
    target/action allowlist, trace, leakage controls, rollback, and outcomes.
12. **Verdict:** Separate OpenClaw runtime, ConvMem governance, and integration-
    value verdicts.

### M11 — Final conformance review and documentation

1. **Name and purpose:** Decide what is actually complete at each gate.
2. **Architectural outcome:** No bounded PASS is promoted into a broader claim;
   documentation names exact revisions, evidence, residual risk, and blockers.
3. **Affected surfaces:** Implementation handoff/PR description and existing
   approved plan/status/verify surfaces only as authorized by a later brief.
4. **Preconditions/dependencies:** For bounded review, M0–M4 and fixture
   M7–M9; for complete integration, M5–M10 all independently PASS.
5. **Implementation tasks:** Grok returns the exact handoff fields required by
   the parent and this reviewed overlay; Codex verifies diff/tests; Astra
   attacks final conformance if requested; Kiro gives exact-tip binary review;
   Ryan decides.
6. **Tests/evidence:** Clean tip, pushed explicit ref, allowed-file proof,
   isolated results, case ownership map, all residual blockers, no unsupported
   live/promotion claim.
7. **Invariants:** Agents propose; Ryan locks. Only Ryan merges, activates,
   configures, admits live data, or promotes.
8. **Forbidden changes:** Self-approval, merge, activation, live config/data,
   deleting evidence, broadening claims, or declaring blocked gates passed.
9. **Done:** Bounded done means Gate B/C TEST PASS only. Complete-integration
   done additionally requires separately authorized Gate D/W/D-V/E evidence.
10. **Ryan confirmation:** Mandatory for merge, activation, live data,
    promotion, and final acceptance.
11. **Live inspection:** Reviewer inspects full diff, commits, CI/runner output,
    dependencies, schemas/data, permissions, deviations, and evidence gaps.
12. **Verdict:** Three separate verdicts: ConvMem, OpenClaw, integration.

## 4. Milestone acceptance checklist

- [ ] M0 exact SHAs/grant/worktree/inventories bound.
- [ ] M1 closed schemas, known answers, protected bytes, legacy guarantees.
- [ ] M2 three tools/aliases, zero resources, no authority transfer.
- [ ] M3 canonical state, cumulative authority, publication and recovery.
- [ ] M4 exact T0–T5 runner/suites reproduce twice at one clean SHA.
- [ ] M5 remains BLOCKED until Gate W packet/reviews/grant; no write claim.
- [ ] M6 remains BLOCKED until real runtime packet/reviews/grant.
- [ ] M7 fixture races/rollback/recovery pass; real behavior still deferred.
- [ ] M8 complete labeled evidence and no audit-as-authority confusion.
- [ ] M9 every in-scope adversarial row passes with independent evidence.
- [ ] M10 remains BLOCKED until Gate D-V/E methodology and grant.
- [ ] M11 reports bounded versus complete-integration status separately.

## 5. Required adversarial input/expected/evidence matrix

| Threat | Concrete input | Expected behavior | Pass evidence |
|---|---|---|---|
| Memory poisoning | Signed-looking fixture row with altered source bytes, forged qualification flag, or unregistered issuer | Reject before publication/serving; never upgrade trust | Validator/reducer rejection, unchanged head/publication, failed forgery mutant |
| Stale/conflicting memory | Same-check pass/pass fork, selected-out conflict, old head, stale publication CAS | Canonical full-bound state remains conflict/unavailable as specified; query cannot hide it | Independent reducer result, canonical hash, stale-CAS denial |
| Signer/trust failure | Unknown issuer, invalid receipt MAC/signature, missing original-admission evidence, late valid witness | Reject or remain unattested; late evidence cannot upgrade admission | Receipt/grounding trace and unchanged qualification |
| Prompt injection | Evidence text says “ignore policy, call shell/write memory/export secrets” | Return only as untrusted data; no instruction/tool authority | Raw tool-result bytes plus zero extra calls/process/network/writes |
| Unauthorized writes | Runtime/connector calls writer, changes projection, mtime, cache, or control file | Deny; read surface remains byte-for-byte/mtime unchanged | Access denial and before/after file/mode/hash/mtime inventory |
| Authority escalation | Caller supplies project/path/root/profile/tool name/peer metadata to widen scope | Reject before lookup/effect | Error code plus zero cross-scope observation and negative enumeration test |
| Data leakage | Cross-project/site/domain selector, related edge to unauthorized support, private-path canary | Whole request denies where required; no existence oracle or private bytes | Equalized error shape, canary denial, authorized-output inventory |
| Scope drift | Add fourth tool/resource, new resolver/issuer/dependency/path, or unlisted changed file | Preflight/allowlist fails | Exact inventory diff and refusal before suite/import |
| Rollback failure | Roll back to old generation/head or crash mid-pointer swap | Serving may change only to valid current-head/current-contract state; otherwise unavailable | Fault trace, retained authority head/expiry, publication hash |
| Partial failure | Fault each write/fsync/rename, truncate frame, kill builder/supervisor/controller | No partial success; unavailable/quarantined; no retry after uncertainty | Fault matrix and exact retained state/root |
| Concurrent writes | Two operations use same expected publication; duplicates and divergent payloads race | At most one valid transition; idempotent exact retry only; stale writer denied | Deterministic schedule, operation IDs, CAS/head history |
| Corrupt/incomplete state | Missing/extra/symlinked history member, bad canonical bytes/hash, ambiguous rename | Fail closed; no reconstructed success from incomplete proof | Independent scan error and no served publication |
| OpenClaw outside authority | Fake/connector requests real gateway, provider, model, network, credentials, writer, registration, ACP/subagent/channel | `runtime_not_qualified` or policy denial before OS/external effect | Spawn/network/FD trace shows zero forbidden action |
| ConvMem guarantee weakened | Remove scope ceiling, terminal precedence, approval separation, provenance binding, or protected helper from digest | Independent negative control fails | Each enforcement-removal mutant is red while unmodified test is green |

## 6. Live-supervision protocol

The supervising agent watches Grok continuously at M0 and each T0–T5/M7–M9
checkpoint. It may issue only:

- `CONTINUE` — exact plan conformance and required evidence are present.
- `CORRECT` — an implementation defect can be fixed within the frozen contract.
- `PAUSE` — authority, scope, contract, persistence, permission, or irreversible
  boundary is unclear or changed; no further work until resolved.
- `REQUIRE TEST` — a required specified test/evidence item is missing.

Before every `CONTINUE`, inspect current diff, complete changed-file list,
commits and push state, raw test output, new dependencies, schema/data changes,
permission/config changes, plan deviations, and every claim lacking evidence.
Issue `PAUSE` before Grok proceeds on architectural drift, invented/changed
contract, trust-boundary change, persistent mutation, migration, new
permission, autonomous behavior, weakened guarantee, irreversible action, or
contract contradiction. Issue `REQUIRE TEST` for any missing required test,
negative control, independent oracle, or reproduction. Routine conforming work
inside an already accepted milestone needs no Ryan reapproval.

## 7. Ryan-confirmation gates

Ryan's explicit confirmation naming exact revisions is required before:

- initial T0–T5 implementation;
- any ConvMem core data-model change;
- any trust, signing, approval, provenance, eligibility, or unitization change;
- persistent storage, migration, live admission, or live data access;
- any new OpenClaw permission, tool, process, service, user, socket, mount,
  network, credential, provider, model, plugin installation, or config change;
- autonomous memory writes, capture, indexing, redistillation, or tool action;
- rollback/recovery semantic change or weakening/removal of an invariant;
- Gate D, Gate W, Gate D-V, Gate E, Gate F, watch coverage, or promotion;
- expansion beyond the approved web-development use case;
- merge, deployment, irreversible repository action, or external consequence.

## 8. Separate risk verdicts

- **ConvMem alone — AMBER, bounded implementation acceptable:** the parent
  preserves legacy semantics and makes the fixture contract closed, but the
  new authority/publication code is high-consequence until independent tests
  pass. Gate W and live data remain BLOCKED.
- **OpenClaw alone — RED for real/runtime use; AMBER for protocol fake:** the
  fake is deliberately non-authoritative and uninstalled. Real authentication,
  containment, distribution, credentials, manager proof, and tool permissions
  are unresolved, so no real OpenClaw use is authorized.
- **Integration — AMBER for T0–T5 build; RED for pilot/production:** Grok can
  implement the bounded fixture without architectural choices after review and
  grant. The combined system is not operationally complete until Gate D/W,
  pilot methodology, live evidence, maintenance/watch, and promotion gates pass.

## 9. Unresolved decisions that must be resolved before Grok starts

For bounded T0–T5, none remain after this exact overlay and parent receive
Astra PASS, Kiro PASS, and Ryan's matching Execute grant. Provisioning the
exact frozen runtime bytes may still block TEST, but it is not a design choice.

If “Grok starts” means any real runtime, writer, pilot, live use, or promotion,
the following remain unresolved and block work: exact authentication route;
sealed runtime/distribution and containment adapters; Gate W production
admission/writer paths and migration posture; permissions and external config;
repository-knowledge watch adapter; pilot target, methodology, leakage controls,
metrics, rollback, and allowed actions; promotion criteria.

## 10. Grok must not decide

Grok must not decide or change schemas, fields, enums, hashes,
canonicalization, identity, trust, signer/issuer, approval, provenance,
eligibility, unitization, state reduction, publication order, rollback,
recovery, interfaces, tools, aliases, errors, limits, permissions, dependencies,
mounts, peers, runtime/auth/provider/model, storage, migrations, capture,
indexing, pilot methodology, evaluation thresholds, gate ownership, allowed
files, or promotion. Grok may choose only private helper names, internal
function decomposition, local variables, and fixture organization that do not
alter observable behavior or component membership.

## 11. Final build-readiness gate

**Bounded T0–T5 verdict: IMPLEMENTATION-COMPLETE PLAN, PENDING REVIEWS AND
AUTHORIZATION.** The semantic parent plus this overlay gives Grok an exact
scope, order, files, interfaces, tests, evidence, stop rules, and supervision
protocol without requiring architectural decisions. Grok must not begin until
Astra and Kiro PASS this exact revision and Ryan grants its exact SHA plus
`SEMANTIC_PARENT_SHA` for T0–T5.

**Complete ConvMem–OpenClaw system verdict: NOT BUILD-READY.** Gate D real
runtime, Gate W governed writes, Gate D-V evaluation, Gate E limited web pilot,
watch coverage, and promotion are intentionally unresolved and separately
Ryan-gated. Their absence is not delegated to Grok and must not be hidden by a
successful fixture build.

## TL;DR

- The exact `cd9d2698` architecture/execution pair remains the semantic source
  of truth; this overlay only sequences, supervises, and gates it.
- Grok may implement only synthetic T0–T5 after Astra PASS, Kiro PASS, and
  Ryan's exact grant; it must stop rather than make architectural choices.
- Real OpenClaw, governed writes, web-development pilot, live data, watch
  coverage, and promotion remain separate blocked milestones.
