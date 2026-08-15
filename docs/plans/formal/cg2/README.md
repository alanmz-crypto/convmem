# CG-2 bounded authority model

This directory contains the executable architecture model for CG-2 production
activation. It models authority and lifecycle interleavings, not Python,
Chroma's ANN algorithm, filesystem persistence, or performance.

The lock evidence uses three deliberately small exhaustive instances over the
same transition model: cutover/read authority, stale-source reconciliation and
recovery, and rename/pinning. Together they use two rename-linked owners, up to
three generations, one request, two source hashes, two authority-resolution
attempts, and up to four durable-evidence changes per owner. TLC exhausts every
ordering within each property-relevant instance. This split avoids the
irrelevant monolithic cross-product that exhausted host memory without dropping
an action that can affect a checked property.

The model uses the architecture's atomic-resolve-and-pin option:
tentatively selecting an active generation installs its protective pin in the
same transition, then unchanged-evidence validation marks the pin usable.

## Architecture-property map

| §13.18 requirement | Model check |
|---|---|
| 1. Only a qualified pointer target serves a generational owner | `QualifiedPointerServes` |
| 2. At most one current generation authority exists per owner | `SingleCurrentAuthority` |
| 3. A resolution linearized after fencing cannot resolve legacy | `PostFenceNeverLegacy` |
| 4. A pre-fence frozen reader can finish against retained legacy rows | `FrozenLegacyProtected`, `FrozenLegacyFinishEnabled` |
| 5. Active-generation and source-hash stale candidates cannot promote | `PromotionChecksRecorded`; mismatches have only `RejectStaleCandidate` |
| 6. Fair reconciliation handles source drift despite a lost notification | `LostDriftEventuallyHandled` under `WF_vars(Reconcile(o))` |
| 7. Recovery follows the exact pointer, never completeness | `RecoveryUsesExactPointer`; `FlipCompleteness` is independent |
| 8. GC never selects active, previous, candidate, or pinned generations | `GCRespectsProtection` |
| 9. No target is reclaimed between tentative resolution and a validated pin | `TentativePinWindowProtected`, `ValidatedTargetsRemainPinned` |
| 10. A new vector never admits both owners in rename lineage | `RenameVectorExclusive`, `RenameGroupStable` |
| 11. A request does not change its frozen generation | `FrozenGenerationStable`, `GenerationReadsUseFrozenAuthority` |
| 12. Retry exhaustion is finite and returns `AUTHORITY_UNSTABLE` | `RetryBudgetTerminates`, `ResolutionEventuallyTerminates` |

The N1 fallback disposition is checked additionally by
`AuthorityFailuresNeverFallback` and `FallbackIsMediated`: authority or
integrity errors refuse the request, while only a typed transient backend error
can enter repository-mediated fallback with the frozen authority vector still
intact.

## Important abstractions

- `evidenceEpoch` represents the exact fence, pointer, manifest, and retirement
  identity set. It is not a proposed production epoch or second authority.
- `MaxEvidenceEpoch` keeps the checked graph finite. Evidence changes never
  wrap; after the bound, reader and reconciliation transitions still progress.
- `MaxAttempts` is the attempt component of
  `authority_resolution_retry_budget`. The independent wall-clock component is
  an implementation timer and must be tested against the ratified
  `max_elapsed`; it does not need another durable state in this model.
- `LoseNotification` changes source state without creating queued work. The
  fair periodic `Reconcile` action is therefore the convergence proof; no
  watchdog overflow event is assumed.
- `ConcurrentPromotion` represents a separately qualified writer publishing
  while another candidate is in flight. Every recorded publication still
  satisfies expected-active and source-freshness checks.
- `completeness` may change independently before recovery, demonstrating that
  recovery records only the exact durable pointer.
- Current pointer authority and request-frozen authority are intentionally
  different notions. A pre-cutover frozen reader can complete after a fence or
  later publication, while `SingleCurrentAuthority` still holds. The model
  checks that `FinishRead` remains enabled for such a healthy reader; injected
  authority/integrity failures may still refuse the request.

## Checked lock evidence

The 2026-08-14 lock-candidate run used the official stable TLA+ v1.7.4 JAR
(TLC 2.19, revision `5a47802`) with published SHA-1
`bee4a54f3ee3d4afc347c3240ec2d9e93b075104`. Every run used two workers and a
2 GiB Java heap and ended with an empty state queue and zero errors.

| Configuration | Generated | Distinct | Depth | Nonzero action coverage includes |
|---|---:|---:|---:|---|
| `CG2Cutover.cfg` | 9,649 | 3,534 | 20 | snapshot/verify, retry, retry exhaustion, freeze, authority refusal, integrity refusal, mediated transient fallback |
| `CG2StaleReconcile.cfg` | 84,535 | 23,538 | 16 | queue/quarantine reconciliation, qualified and concurrent promotion, stale rejection, recovery, eligible GC |
| `CG2Rename.cfg` | 29,097 | 11,062 | 24 | promotion, rename begin, old-owner retirement, freeze, torn-vector refusal, generation read, legacy read |
| **Total across independent graphs** | **123,281** | **38,134** | — | all architecture-property rows above |

Counts are intentionally reported per graph and summed only as execution
volume; states are not deduplicated across configurations. Action coverage was
captured with TLC's `-coverage 1` option to guard against vacuous green checks.

## Running TLC

With that checksum-verified JAR available outside the repository, run each lock
configuration with the same bounded resources:

```sh
for config in CG2Cutover CG2StaleReconcile CG2Rename; do
  java -Xmx2g -XX:+UseParallelGC -cp /path/to/tla2tools.jar tlc2.TLC \
    -workers 2 -coverage 1 \
    -config "docs/plans/formal/cg2/${config}.cfg" \
    docs/plans/formal/cg2/CG2Authority.tla
done
```

The architecture lock candidate must record the exact TLA+ tools release, the
command, explored-state counts, and zero-error result. Changing a transition,
bound, or property requires rerunning TLC and reviewer delta confirmation.
