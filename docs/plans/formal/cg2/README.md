# CG-2 bounded authority model

This directory contains the executable architecture model for CG-2 production
activation. It models authority and lifecycle interleavings, not Python,
Chroma's ANN algorithm, filesystem persistence, or performance.

## Restoration boundary (D6)

The Design A model restores the pre-D5 formal surfaces from architecture commit
`e680ce837653698a5be8b78ba02db2f880c40c63`, then extends them for the locked
Design A contract (D0 chain, retained `G_rb`, first cutover, rollback,
recovery, reconciliation, canary guard, and G_rb-only query context).

Review the restoration diff before treating extensions as proof:

```sh
git diff e680ce837653698a5be8b78ba02db2f880c40c63 -- docs/plans/formal/cg2/
```

Historical TLC results from `e680ce8` / 2026-08-14 remain **historical evidence
only**. They are not Design A proof.

## Model structure

The lock evidence uses four deliberately small exhaustive instances over the
shared transition model:

| Configuration | Specification | Primary focus |
|---|---|---|
| `CG2Cutover.cfg` | `CutoverSpec` | Cutover, read authority, Design A first-cutover properties |
| `CG2StaleReconcile.cfg` | `StaleReconcileSpec` | Stale-source reconciliation, rollback, recovery |
| `CG2Rename.cfg` | `RenameSpec` | Rename/pinning with retained baseline protection |
| `CG2DesignA.cfg` | `DesignASpec` | Focused Design A baseline, D0 chain, first cutover, rollback-after-source-advance, recovery separation, canary guard, query context |

The restored model uses the architecture's atomic-resolve-and-pin option:
tentatively selecting an active generation installs its protective pin in the
same transition, then unchanged-evidence validation marks the pin usable.

### Design A extensions (`CG2Authority.tla`)

New abstract state tracks:

- D0 candidate, validation, and ratification digests (`d0`);
- first-cutover phase, canary guard, owner lock, retained baseline, proof
  profiles, and reconciliation debt (`cutover`);
- distinguished generations `GRb` and `GCanary`.

New transitions include D0 capture/validate/ratify, LEGACY→`G_rb` conversion,
pre-fence refusal, durable fence (`FENCED_NO_POINTER`), fresh-grant crash
resume (fence-only and fence+guard), wrong-guard refusal, first pointer CAS
against `NoGen` with previous=`GRb` and active=`GCanary`, live LEGACY-root
rebind, forward promotion with CAS separate from rollback lineage,
source-advanced rollback with reconciliation debt, G_rb-only query-context
check, same-pointer recovery, first-canary guard blocking second promotion,
rollback-baseline GC exclusion, and one lock interval per authority-changing
operation.

## Architecture-property map (inherited)

| §13.18 requirement | Model check |
|---|---|
| 1. Only a qualified pointer target serves a generational owner | `QualifiedPointerServes` |
| 2. At most one current generation authority exists per owner | `SingleCurrentAuthority` |
| 3. A resolution linearized after fencing cannot resolve legacy | `PostFenceNeverLegacy` |
| 4. A pre-fence frozen reader can finish against retained legacy rows | `FrozenLegacyProtected`, `FrozenLegacyFinishEnabled` |
| 5. Active-generation and source-hash stale candidates cannot promote | `PromotionChecksRecorded`; mismatches have only `RejectStaleCandidate` |
| 6. Fair reconciliation handles source drift despite a lost notification | `LostDriftEventuallyHandled` under `WF_vars(Reconcile(o))` |
| 7. Recovery follows the exact pointer, never completeness | `RecoveryUsesExactPointer`, `RecoveryNeverSwitchesGeneration` |
| 8. GC never selects active, previous, candidate, pinned, or retained-baseline generations | `GCRespectsProtection`, `RollbackBaselineNeverGCEligible` |
| 9. No target is reclaimed between tentative resolution and a validated pin | `TentativePinWindowProtected`, `ValidatedTargetsRemainPinned` |
| 10. A new vector never admits both owners in rename lineage | `RenameVectorExclusive`, `RenameGroupStable` |
| 11. A request does not change its frozen generation | `FrozenGenerationStable`, `GenerationReadsUseFrozenAuthority` |
| 12. Retry exhaustion is finite and returns `AUTHORITY_UNSTABLE` | `RetryBudgetTerminates`, `ResolutionEventuallyTerminates` |

## Design A named properties (§11.3)

**Ratified amendment:**

- `UnknownModelOnlyForRatifiedLegacyBaseline`
- `ProspectiveGenerationRequiresKnownWriterModel`
- `D0CandidateNotAuthority`
- `D0ValidationRequired`
- `D0RatificationRequired`
- `FirstCutoverRebindsCurrentLegacyRoot`
- `GRollbackRequiresExactQueryContext`

**Prior Design A carry-forward:**

- `FirstCutoverHasExactRollbackBaseline`
- `FirstCutoverGenerationsDistinct`
- `CASSeparateFromRollbackLineage`
- `PreFenceRefusalPreservesLegacy`
- `PostFenceFailureNeverLegacy`
- `FenceCrashResumeRequiresFreshGrant`
- `GuardCrashResumeRequiresFreshGrant`
- `WrongGuardRefusesFirstPointer`
- `RollbackAfterSourceAdvanceKeepsReconciliation`
- `RollbackNeverResurrectsLegacy`
- `RecoveryNeverSwitchesGeneration`
- `FirstCanaryBlocksSecondPromotion`
- `RollbackBaselineNeverGCEligible`
- `AuthorityOperationAcquiresOwnerLockOnce`
- `FenceMonotonic`, `FencedNoPointerState`, `FirstCutoverCAS`

## Historical lock evidence (2026-08-14 — `e680ce8` only)

The 2026-08-14 lock-candidate run used the official stable TLA+ v1.7.4 JAR
(TLC 2.19, revision `5a47802`) with published SHA-1
`bee4a54f3ee3d4afc347c3240ec2d9e93b075104`. Every run used two workers and a
2 GiB Java heap and ended with an empty state queue and zero errors.

| Configuration | Generated | Distinct | Depth | Nonzero action coverage includes |
|---|---:|---:|---:|---|
| `CG2Cutover.cfg` | 9,649 | 3,534 | 20 | snapshot/verify, retry, retry exhaustion, freeze, authority refusal, integrity refusal, mediated transient fallback |
| `CG2StaleReconcile.cfg` | 84,535 | 23,538 | 16 | queue/quarantine reconciliation, qualified and concurrent promotion, stale rejection, recovery, eligible GC |
| `CG2Rename.cfg` | 29,097 | 11,062 | 24 | promotion, rename begin, old-owner retirement, freeze, torn-vector refusal, generation read, legacy read |
| **Total across independent graphs (historical)** | **123,281** | **38,134** | — | pre–Design A architecture-property rows |

Counts are historical-only and must not be cited as Design A proof.

## Design A TLC run evidence (pending Ryan JAR approval)

**Status:** model and configurations restored/extended at implementation tip;
**TLC not executed** — awaiting Ryan approval of exact `tla2tools.jar`
SHA-256 per §11.4.

When authorized, run (in order, abort on first failure):

1. `CG2Cutover.cfg`
2. `CG2StaleReconcile.cfg`
3. `CG2Rename.cfg`
4. `CG2DesignA.cfg`

Pinned module: `docs/plans/formal/cg2/CG2Authority.tla`
Pinned timeout: `1800` seconds per configuration

Optional helper (implements §11.4–§11.5 exactly):

```sh
export TLA_JAR=/absolute/path/to/tla2tools.jar
export TLA_JAR_APPROVED_SHA256=<ryan-approved-sha256>
bash docs/plans/formal/cg2/run-design-a-tlc.sh
```

Each successful run must record in this README (one subsection per
configuration):

- exact implementation/model git SHA at TLC run time;
- exact config path;
- exact command line (including `timeout`, Java opts, `-config`, module path);
- `TLA_JAR` path used;
- TLA JAR SHA-256 (`TLA_JAR_SHA256`);
- TLC version string (`TLC_VERSION`);
- Java version string (`JAVA_VERSION`);
- start timestamp and end timestamp (or elapsed seconds);
- exit status;
- PASS or failure result;
- generated states, distinct states, depth, and action-coverage summary from log.

### Design A run subsections (fill after TLC)

#### CG2Cutover.cfg

_Pending JAR approval._

#### CG2StaleReconcile.cfg

_Pending JAR approval._

#### CG2Rename.cfg

_Pending JAR approval._

#### CG2DesignA.cfg

_Pending JAR approval._

## Running TLC manually

With a checksum-verified JAR available outside the repository:

```sh
for config in CG2Cutover CG2StaleReconcile CG2Rename CG2DesignA; do
  timeout 1800 java -Xmx2g -XX:+UseParallelGC -cp /path/to/tla2tools.jar tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla
done
```

Changing a transition, bound, or property requires rerunning TLC and reviewer
delta confirmation after JAR approval.
