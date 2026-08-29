----------------------------- MODULE CG2Authority -----------------------------
EXTENDS Naturals, FiniteSets

(***************************************************************************
CG-2 bounded authority model

This model is intentionally above Python, Chroma, and filesystem APIs.  It
checks the authority transitions that must remain true while legacy owners,
committed generations, readers, reconciliation, rename migration, and later
reclamation overlap.

The model chooses the architecture's atomic-resolve-and-pin variant: when a
reader tentatively resolves an ACTIVE target, that same transition installs a
tentative pin.  The reader may dereference only after unchanged-evidence
validation upgrades that pin.  Implementations may instead pin then
revalidate, but must refine the same protected-window properties.
***************************************************************************)

CONSTANTS
    Owners,
    Generations,
    Readers,
    SourceHashes,
    OldOwner,
    NewOwner,
    NoGen,
    InitialSource,
    MaxAttempts,
    MaxEvidenceEpoch,
    GRb,
    GCanary,
    Grants,
    QueryContexts,
    D0Artifacts,
    NoArtifact,
    NoGrant

ASSUME /\ Owners # {}
       /\ Generations # {}
       /\ Readers # {}
       /\ SourceHashes # {}
       /\ OldOwner \in Owners
       /\ NewOwner \in Owners
       /\ OldOwner # NewOwner
       /\ NoGen \notin Generations
       /\ InitialSource \in SourceHashes
       /\ MaxAttempts \in Nat \ {0}
       /\ MaxEvidenceEpoch \in Nat \ {0}
       /\ GRb \in Generations
       /\ GCanary \in Generations
       /\ GRb # GCanary
       /\ Grants # {}
       /\ QueryContexts # {}
       /\ D0Artifacts # {}
       /\ NoArtifact \notin D0Artifacts
       /\ NoGrant \notin Grants

RequestStates == {"IDLE", "RESOLVING", "FROZEN", "REFUSED", "DONE"}
ResolvePhases == {"NOT_STARTED", "SNAPSHOT", "VERIFY", "OWNER_DONE"}
AuthorityKinds == {"LEGACY", "ACTIVE", "UNAVAILABLE", "EXCLUDED"}
Errors == {"NONE", "AUTHORITY_UNSTABLE", "RENAME_CONFLICT",
           "AUTHORITY_FAILURE", "BACKEND_INTEGRITY"}
FailureClasses == {"NONE", "AUTHORITY", "INTEGRITY", "TRANSIENT"}
FallbackModes == {"NONE", "MEDIATED"}

ProofProfiles == {"UNKNOWN_MODEL_V1", "KNOWN_MODEL_V1"}
CutoverPhases == {"NONE", "PREFLIGHT_OK", "LOCK_HELD", "FENCED", "GUARDED", "POINTER_PUBLISHED"}
GuardStates == {"ABSENT", "OPEN", "REFUSED"}
LockStates == {"FREE", "HELD"}

D0Type ==
    [candidate : [Owners -> D0Artifacts \cup {NoArtifact}],
     validated : [Owners -> D0Artifacts \cup {NoArtifact}],
     ratified : [Owners -> D0Artifacts \cup {NoArtifact}],
     legacyRootAtCapture : [Owners -> SourceHashes],
     legacyRootAtCutover : [Owners -> SourceHashes],
     ratifiedQueryContext : [Owners -> QueryContexts]]

CutoverTrackType ==
    [grantId : [Owners -> Grants \cup {NoGrant}],
     priorGrantId : [Owners -> Grants \cup {NoGrant}],
     canaryGuard : [Owners -> GuardStates],
     lockHeld : [Owners -> LockStates],
     phase : [Owners -> CutoverPhases],
     retainedBaseline : SUBSET Generations,
     grbBound : [Owners -> Generations \cup {NoGen}],
     proofProfile : [Generations -> ProofProfiles],
     reconciliationDebt : SUBSET Owners,
     firstCutoverDone : SUBSET Owners,
     fenceMonotonic : [Owners -> BOOLEAN],
     guardBytes : [Owners -> BOOLEAN]]

FirstCutoverRecordType ==
    [owner : Owners,
     grant : Grants,
     legacyRoot : SourceHashes,
     casExpected : Generations \cup {NoGen},
     previous : Generations,
     active : Generations]

RollbackRecordType ==
    [owner : Owners,
     target : Generations,
     expectedActive : Generations,
     queryContext : QueryContexts,
     sourceStale : BOOLEAN]


PromotionRecordType ==
    [owner : Owners,
     generation : Generations,
     expected : Generations \cup {NoGen},
     prior : Generations \cup {NoGen},
     candidateSource : SourceHashes,
     sourceAtPublish : SourceHashes,
     coldValidated : BOOLEAN]

RecoveryRecordType ==
    [owner : Owners,
     pointerAtRecovery : Generations \cup {NoGen},
     completenessAtRecovery : BOOLEAN,
     selected : Generations \cup {NoGen}]

ReadTargetType ==
    [reader : Readers, owner : Owners, generation : Generations]

LegacyReadType == [reader : Readers, owner : Owners]

VARIABLES auth, build, reads, pins, history, d0, cutover

vars == <<auth, build, reads, pins, history, d0, cutover>>

AuthType ==
    [present : SUBSET Owners,
     fence : SUBSET Owners,
     retired : SUBSET Owners,
     quarantined : SUBSET Owners,
     pointer : [Owners -> Generations \cup {NoGen}],
     previous : [Owners -> Generations \cup {NoGen}],
     qualified : SUBSET Generations,
     deleted : SUBSET Generations,
     evidenceEpoch : [Owners -> 0..MaxEvidenceEpoch],
     legacyRetained : [Owners -> BOOLEAN],
     sourceHash : [Owners -> SourceHashes],
     manifestSource : [Owners -> SourceHashes],
     completeness : [Owners -> BOOLEAN]]

BuildType ==
    [candidateGen : [Owners -> Generations \cup {NoGen}],
     candidateExpected : [Owners -> Generations \cup {NoGen}],
     candidateSource : [Owners -> SourceHashes],
     candidateCold : [Owners -> BOOLEAN],
     lostDrift : SUBSET Owners,
     queued : SUBSET Owners]

ReaderType ==
    [state : RequestStates,
     phase : [Owners -> ResolvePhases],
     attempts : [Owners -> 0..MaxAttempts],
     tentativeKind : [Owners -> AuthorityKinds],
     tentativeGen : [Owners -> Generations \cup {NoGen}],
     tentativeEpoch : [Owners -> 0..MaxEvidenceEpoch],
     selectedKind : [Owners -> AuthorityKinds],
     selectedGen : [Owners -> Generations \cup {NoGen}],
     linearizedAfterFence : [Owners -> BOOLEAN],
     frozenKind : [Owners -> AuthorityKinds],
     frozenGen : [Owners -> Generations \cup {NoGen}],
     frozenWitness : [Owners -> Generations \cup {NoGen}],
     error : Errors,
     failureClass : FailureClasses,
     fallbackMode : FallbackModes]

HistoryType ==
    [promotionSeen : BOOLEAN,
     lastPromotion : PromotionRecordType,
     staleRejectedOwners : SUBSET Owners,
     recoverySeen : BOOLEAN,
     lastRecovery : RecoveryRecordType,
     generationReadSeen : BOOLEAN,
     lastGenerationRead : ReadTargetType,
     legacyReadSeen : BOOLEAN,
     d0CaptureSeen : BOOLEAN,
     d0ValidationSeen : BOOLEAN,
     d0RatificationSeen : BOOLEAN,
     firstCutoverSeen : BOOLEAN,
     lastFirstCutover : FirstCutoverRecordType,
     rollbackSeen : BOOLEAN,
     lastRollback : RollbackRecordType,
     lockCycleSeen : BOOLEAN,
     lastLockOwner : Owners]

TypeOK ==
    /\ auth \in AuthType
    /\ build \in BuildType
    /\ reads \in [Readers -> ReaderType]
    /\ pins \in SUBSET [reader : Readers,
                         owner : Owners,
                         generation : Generations,
                         validated : BOOLEAN]
    /\ history \in HistoryType
    /\ d0 \in D0Type
    /\ cutover \in CutoverTrackType

NoGenerationMap == [o \in Owners |-> NoGen]
InitialSourceMap == [o \in Owners |-> InitialSource]
ArbitraryGeneration == CHOOSE g \in Generations : TRUE
ArbitraryReader == CHOOSE r \in Readers : TRUE

InitialReader ==
    [state |-> "IDLE",
     phase |-> [o \in Owners |-> "NOT_STARTED"],
     attempts |-> [o \in Owners |-> 0],
     tentativeKind |-> [o \in Owners |-> "EXCLUDED"],
     tentativeGen |-> NoGenerationMap,
     tentativeEpoch |-> [o \in Owners |-> 0],
     selectedKind |-> [o \in Owners |-> "EXCLUDED"],
     selectedGen |-> NoGenerationMap,
     linearizedAfterFence |-> [o \in Owners |-> FALSE],
     frozenKind |-> [o \in Owners |-> "EXCLUDED"],
     frozenGen |-> NoGenerationMap,
     frozenWitness |-> NoGenerationMap,
     error |-> "NONE",
     failureClass |-> "NONE",
     fallbackMode |-> "NONE"]

Init ==
    /\ auth =
        [present |-> {OldOwner},
         fence |-> {},
         retired |-> {},
         quarantined |-> {},
         pointer |-> NoGenerationMap,
         previous |-> NoGenerationMap,
         qualified |-> {},
         deleted |-> {},
         evidenceEpoch |-> [o \in Owners |-> 0],
         legacyRetained |-> [o \in Owners |-> o = OldOwner],
         sourceHash |-> InitialSourceMap,
         manifestSource |-> InitialSourceMap,
         completeness |-> [o \in Owners |-> TRUE]]
    /\ build =
        [candidateGen |-> NoGenerationMap,
         candidateExpected |-> NoGenerationMap,
         candidateSource |-> InitialSourceMap,
         candidateCold |-> [o \in Owners |-> FALSE],
         lostDrift |-> {},
         queued |-> {}]
    /\ reads = [r \in Readers |-> InitialReader]
    /\ pins = {}
    /\ history =
        [promotionSeen |-> FALSE,
         lastPromotion |->
             [owner |-> OldOwner,
              generation |-> ArbitraryGeneration,
              expected |-> NoGen,
              prior |-> NoGen,
              candidateSource |-> InitialSource,
              sourceAtPublish |-> InitialSource,
              coldValidated |-> TRUE],
         staleRejectedOwners |-> {},
         recoverySeen |-> FALSE,
         lastRecovery |->
             [owner |-> OldOwner,
              pointerAtRecovery |-> NoGen,
              completenessAtRecovery |-> TRUE,
              selected |-> NoGen],
         generationReadSeen |-> FALSE,
         lastGenerationRead |->
             [reader |-> ArbitraryReader,
              owner |-> OldOwner,
              generation |-> ArbitraryGeneration],
         legacyReadSeen |-> FALSE,
         d0CaptureSeen |-> FALSE,
         d0ValidationSeen |-> FALSE,
         d0RatificationSeen |-> FALSE,
         firstCutoverSeen |-> FALSE,
         lastFirstCutover |->
             [owner |-> OldOwner,
              grant |-> CHOOSE g \in Grants : TRUE,
              legacyRoot |-> InitialSource,
              casExpected |-> NoGen,
              previous |-> GRb,
              active |-> GCanary],
         rollbackSeen |-> FALSE,
         lastRollback |->
             [owner |-> OldOwner,
              target |-> GRb,
              expectedActive |-> GCanary,
              queryContext |-> CHOOSE q \in QueryContexts : TRUE,
              sourceStale |-> FALSE],
         lockCycleSeen |-> FALSE,
         lastLockOwner |-> OldOwner]
    /\ d0 =
        [candidate |-> [o \in Owners |-> NoArtifact],
         validated |-> [o \in Owners |-> NoArtifact],
         ratified |-> [o \in Owners |-> NoArtifact],
         legacyRootAtCapture |-> InitialSourceMap,
         legacyRootAtCutover |-> InitialSourceMap,
         ratifiedQueryContext |-> [o \in Owners |-> CHOOSE q \in QueryContexts : TRUE]]
    /\ cutover =
        [grantId |-> [o \in Owners |-> NoGrant],
         priorGrantId |-> [o \in Owners |-> NoGrant],
         canaryGuard |-> [o \in Owners |-> "ABSENT"],
         lockHeld |-> [o \in Owners |-> "FREE"],
         phase |-> [o \in Owners |-> "NONE"],
         retainedBaseline |-> {},
         grbBound |-> NoGenerationMap,
         proofProfile |-> [g \in Generations |-> "KNOWN_MODEL_V1"],
         reconciliationDebt |-> {},
         firstCutoverDone |-> {},
         fenceMonotonic |-> [o \in Owners |-> FALSE],
         guardBytes |-> [o \in Owners |-> FALSE]]

OwnerMode(o) ==
    IF o \notin auth.present \/ o \in auth.retired THEN "EXCLUDED"
    ELSE IF o \in auth.quarantined THEN "UNAVAILABLE"
    ELSE IF o \notin auth.fence /\ auth.pointer[o] = NoGen THEN "LEGACY"
    ELSE IF o \in auth.fence
            /\ auth.pointer[o] # NoGen
            /\ auth.pointer[o] \in auth.qualified
            /\ auth.pointer[o] \notin auth.deleted
         THEN "ACTIVE"
    ELSE "UNAVAILABLE"

Admitted(kind) == kind \in {"LEGACY", "ACTIVE"}

PointerGenerations == {auth.pointer[o] : o \in Owners} \ {NoGen}
PreviousGenerations == {auth.previous[o] : o \in Owners} \ {NoGen}
CandidateGenerations == {build.candidateGen[o] : o \in Owners} \ {NoGen}
PinnedGenerations == {p.generation : p \in pins}

ProtectedGenerations ==
    PointerGenerations \cup PreviousGenerations \cup CandidateGenerations
    \cup PinnedGenerations \cup cutover.retainedBaseline

FreeGeneration(g) ==
    /\ g \in Generations
    /\ g \notin auth.qualified
    /\ g \notin auth.deleted
    /\ g \notin CandidateGenerations

CanBump(o) == auth.evidenceEpoch[o] < MaxEvidenceEpoch

Pin(r, o, g, valid) ==
    [reader |-> r, owner |-> o, generation |-> g, validated |-> valid]

ReaderPins(r) == {p \in pins : p.reader = r}
OwnerReaderPins(r, o) == {p \in pins : p.reader = r /\ p.owner = o}

LegacyFrozenFor(o) ==
    {r \in Readers : reads[r].state = "FROZEN"
                    /\ reads[r].frozenKind[o] = "LEGACY"}

EvidenceStable(r, o) ==
    /\ reads[r].tentativeEpoch[o] = auth.evidenceEpoch[o]
    /\ reads[r].tentativeKind[o] = OwnerMode(o)
    /\ IF reads[r].tentativeKind[o] = "ACTIVE"
          THEN auth.pointer[o] = reads[r].tentativeGen[o]
          ELSE reads[r].tentativeGen[o] = NoGen

AllOwnersResolved(r) ==
    \A o \in Owners : reads[r].phase[o] = "OWNER_DONE"

RenameGroupStable(r) ==
    /\ reads[r].tentativeEpoch[OldOwner] = auth.evidenceEpoch[OldOwner]
    /\ reads[r].tentativeEpoch[NewOwner] = auth.evidenceEpoch[NewOwner]
    /\ ~(Admitted(reads[r].selectedKind[OldOwner])
         /\ Admitted(reads[r].selectedKind[NewOwner]))
    /\ ~(Admitted(OwnerMode(OldOwner)) /\ Admitted(OwnerMode(NewOwner)))

BuildCandidate(o, g) ==
    /\ o \in auth.present
    /\ o \notin auth.retired
    /\ build.candidateGen[o] = NoGen
    /\ FreeGeneration(g)
    /\ build' =
        [build EXCEPT
            !.candidateGen[o] = g,
            !.candidateExpected[o] = auth.pointer[o],
            !.candidateSource[o] = auth.sourceHash[o],
            !.candidateCold[o] = FALSE]
    /\ UNCHANGED <<auth, reads, pins, history, d0, cutover>>

ColdValidate(o) ==
    /\ build.candidateGen[o] # NoGen
    /\ ~build.candidateCold[o]
    /\ build' = [build EXCEPT !.candidateCold[o] = TRUE]
    /\ UNCHANGED <<auth, reads, pins, history, d0, cutover>>

LoseNotification(o, newHash) ==
    /\ o \in auth.present
    /\ o \notin build.lostDrift
    /\ newHash \in SourceHashes \ {auth.sourceHash[o]}
    /\ auth' = [auth EXCEPT !.sourceHash[o] = newHash]
    /\ build' = [build EXCEPT !.lostDrift = @ \cup {o}]
    /\ UNCHANGED <<reads, pins, history, d0, cutover>>

ReconcileQueue(o) ==
    /\ o \in build.lostDrift
    /\ auth.sourceHash[o] # auth.manifestSource[o]
    /\ o \notin build.queued
    /\ o \notin auth.quarantined
    /\ build' = [build EXCEPT !.queued = @ \cup {o}]
    /\ UNCHANGED <<auth, reads, pins, history, d0, cutover>>

ReconcileQuarantine(o) ==
    /\ o \in build.lostDrift
    /\ auth.sourceHash[o] # auth.manifestSource[o]
    /\ o \notin build.queued
    /\ o \notin auth.quarantined
    /\ CanBump(o)
    /\ auth' =
        [auth EXCEPT
            !.quarantined = @ \cup {o},
            !.evidenceEpoch[o] = @ + 1]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

Reconcile(o) == ReconcileQueue(o) \/ ReconcileQuarantine(o)

FenceOwner(o) ==
    /\ o \in auth.present
    /\ o \notin auth.retired
    /\ o \notin auth.fence
    /\ CanBump(o)
    /\ auth' =
        [auth EXCEPT
            !.fence = @ \cup {o},
            !.evidenceEpoch[o] = @ + 1]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

PromotionRecord(o, g, expected, prior, source) ==
    [owner |-> o,
     generation |-> g,
     expected |-> expected,
     prior |-> prior,
     candidateSource |-> source,
     sourceAtPublish |-> auth.sourceHash[o],
     coldValidated |-> TRUE]

PromoteCandidate(o) ==
    LET g == build.candidateGen[o]
        old == auth.pointer[o]
    IN /\ g # NoGen
       /\ build.candidateCold[o]
       /\ build.candidateExpected[o] = old
       /\ build.candidateSource[o] = auth.sourceHash[o]
       /\ o \in auth.present
       /\ o \in auth.fence
       /\ o \notin auth.retired
       /\ o \notin auth.quarantined
       /\ o # NewOwner \/ OldOwner \in auth.retired
       /\ CanBump(o)
       /\ auth' =
           [auth EXCEPT
               !.pointer[o] = g,
               !.previous[o] = old,
               !.qualified = @ \cup {g},
               !.manifestSource[o] = build.candidateSource[o],
               !.evidenceEpoch[o] = @ + 1]
       /\ build' =
           [build EXCEPT
               !.candidateGen[o] = NoGen,
               !.candidateCold[o] = FALSE]
       /\ history' =
           [history EXCEPT
               !.promotionSeen = TRUE,
               !.lastPromotion =
                   PromotionRecord(o, g, build.candidateExpected[o], old,
                                   build.candidateSource[o])]
       /\ UNCHANGED <<reads, pins, d0, cutover>>

RejectStaleCandidate(o) ==
    /\ build.candidateGen[o] # NoGen
    /\ build.candidateCold[o]
    /\ (build.candidateExpected[o] # auth.pointer[o]
        \/ build.candidateSource[o] # auth.sourceHash[o])
    /\ build' =
        [build EXCEPT
            !.candidateGen[o] = NoGen,
            !.candidateCold[o] = FALSE]
    /\ history' =
        [history EXCEPT
            !.staleRejectedOwners = @ \cup {o}]
    /\ UNCHANGED <<auth, reads, pins, d0, cutover>>

ConcurrentPromotion(o, g) ==
    LET old == auth.pointer[o]
    IN /\ o \in auth.present
       /\ o \in auth.fence
       /\ o \notin auth.retired
       /\ o \notin auth.quarantined
       /\ o # NewOwner \/ OldOwner \in auth.retired
       /\ FreeGeneration(g)
       /\ CanBump(o)
       /\ auth' =
           [auth EXCEPT
               !.pointer[o] = g,
               !.previous[o] = old,
               !.qualified = @ \cup {g},
               !.manifestSource[o] = auth.sourceHash[o],
               !.evidenceEpoch[o] = @ + 1]
       /\ history' =
           [history EXCEPT
               !.promotionSeen = TRUE,
               !.lastPromotion =
                   PromotionRecord(o, g, old, old, auth.sourceHash[o])]
       /\ UNCHANGED <<build, reads, pins, d0, cutover>>

BeginRename ==
    /\ NewOwner \notin auth.present
    /\ OldOwner \in auth.present
    /\ OwnerMode(OldOwner) = "ACTIVE"
    /\ CanBump(NewOwner)
    /\ auth' =
        [auth EXCEPT
            !.present = @ \cup {NewOwner},
            !.fence = @ \cup {NewOwner},
            !.evidenceEpoch[NewOwner] = @ + 1]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

RetireOldOwner ==
    /\ NewOwner \in auth.present
    /\ NewOwner \in auth.fence
    /\ OldOwner \notin auth.retired
    /\ build.candidateGen[NewOwner] # NoGen
    /\ build.candidateCold[NewOwner]
    /\ CanBump(OldOwner)
    /\ auth' =
        [auth EXCEPT
            !.retired = @ \cup {OldOwner},
            !.evidenceEpoch[OldOwner] = @ + 1]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

Recover(o) ==
    /\ history' =
        [history EXCEPT
            !.recoverySeen = TRUE,
            !.lastRecovery =
                [owner |-> o,
                 pointerAtRecovery |-> auth.pointer[o],
                 completenessAtRecovery |-> auth.completeness[o],
                 selected |-> auth.pointer[o]]]
    /\ UNCHANGED <<auth, build, reads, pins, d0, cutover>>

FlipCompleteness(o) ==
    /\ auth' = [auth EXCEPT !.completeness[o] = ~@]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

GarbageCollect(g) ==
    /\ g \in auth.qualified
    /\ g \notin auth.deleted
    /\ g \notin ProtectedGenerations
    /\ g \notin cutover.retainedBaseline
    /\ auth' = [auth EXCEPT !.deleted = @ \cup {g}]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

DropLegacy(o) ==
    /\ o \in auth.fence
    /\ auth.legacyRetained[o]
    /\ LegacyFrozenFor(o) = {}
    /\ auth' = [auth EXCEPT !.legacyRetained[o] = FALSE]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

StartRequest(r) ==
    /\ reads[r].state = "IDLE"
    /\ reads' =
        [reads EXCEPT
            ![r].state = "RESOLVING",
            ![r].phase = [o \in Owners |-> "SNAPSHOT"],
            ![r].attempts = [o \in Owners |-> 0],
            ![r].error = "NONE",
            ![r].failureClass = "NONE",
            ![r].fallbackMode = "NONE"]
    /\ UNCHANGED <<auth, build, pins, history, d0, cutover>>

SnapshotOwner(r, o) ==
    LET kind == OwnerMode(o)
        g == IF kind = "ACTIVE" THEN auth.pointer[o] ELSE NoGen
    IN /\ reads[r].state = "RESOLVING"
       /\ reads[r].phase[o] = "SNAPSHOT"
       /\ reads' =
           [reads EXCEPT
               ![r].phase[o] = "VERIFY",
               ![r].tentativeKind[o] = kind,
               ![r].tentativeGen[o] = g,
               ![r].tentativeEpoch[o] = auth.evidenceEpoch[o]]
       /\ pins' =
           IF kind = "ACTIVE"
              THEN pins \cup {Pin(r, o, g, FALSE)}
              ELSE pins
       /\ UNCHANGED <<auth, build, history, d0, cutover>>

VerifyOwner(r, o) ==
    LET kind == reads[r].tentativeKind[o]
        g == reads[r].tentativeGen[o]
    IN /\ reads[r].state = "RESOLVING"
       /\ reads[r].phase[o] = "VERIFY"
       /\ EvidenceStable(r, o)
       /\ reads' =
           [reads EXCEPT
               ![r].phase[o] = "OWNER_DONE",
               ![r].selectedKind[o] = kind,
               ![r].selectedGen[o] = g,
               ![r].linearizedAfterFence[o] = o \in auth.fence]
       /\ pins' =
           IF kind = "ACTIVE"
              THEN (pins \ {Pin(r, o, g, FALSE)})
                   \cup {Pin(r, o, g, TRUE)}
              ELSE pins
       /\ UNCHANGED <<auth, build, history, d0, cutover>>

RetryOwner(r, o) ==
    /\ reads[r].state = "RESOLVING"
    /\ reads[r].phase[o] = "VERIFY"
    /\ ~EvidenceStable(r, o)
    /\ reads[r].attempts[o] + 1 < MaxAttempts
    /\ reads' =
        [reads EXCEPT
            ![r].phase[o] = "SNAPSHOT",
            ![r].attempts[o] = @ + 1]
    /\ pins' = pins \ OwnerReaderPins(r, o)
    /\ UNCHANGED <<auth, build, history, d0, cutover>>

ExhaustRetryBudget(r, o) ==
    /\ reads[r].state = "RESOLVING"
    /\ reads[r].phase[o] = "VERIFY"
    /\ ~EvidenceStable(r, o)
    /\ reads[r].attempts[o] + 1 >= MaxAttempts
    /\ reads' =
        [reads EXCEPT
            ![r].state = "REFUSED",
            ![r].attempts[o] = MaxAttempts,
            ![r].error = "AUTHORITY_UNSTABLE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history, d0, cutover>>

FreezeVector(r) ==
    /\ reads[r].state = "RESOLVING"
    /\ AllOwnersResolved(r)
    /\ RenameGroupStable(r)
    /\ reads' =
        [reads EXCEPT
            ![r].state = "FROZEN",
            ![r].frozenKind = reads[r].selectedKind,
            ![r].frozenGen = reads[r].selectedGen,
            ![r].frozenWitness = reads[r].selectedGen]
    /\ UNCHANGED <<auth, build, pins, history, d0, cutover>>

RefuseTornVector(r) ==
    /\ reads[r].state = "RESOLVING"
    /\ AllOwnersResolved(r)
    /\ ~RenameGroupStable(r)
    /\ reads' =
        [reads EXCEPT
            ![r].state = "REFUSED",
            ![r].error =
                IF Admitted(reads[r].selectedKind[OldOwner])
                   /\ Admitted(reads[r].selectedKind[NewOwner])
                THEN "RENAME_CONFLICT"
                ELSE "AUTHORITY_UNSTABLE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history, d0, cutover>>

ResolveStep(r) ==
    (\E o \in Owners : SnapshotOwner(r, o))
    \/ (\E o \in Owners : VerifyOwner(r, o))
    \/ (\E o \in Owners : RetryOwner(r, o))
    \/ (\E o \in Owners : ExhaustRetryBudget(r, o))
    \/ FreezeVector(r)
    \/ RefuseTornVector(r)

ReadGeneration(r, o) ==
    LET g == reads[r].frozenGen[o]
    IN /\ reads[r].state = "FROZEN"
       /\ reads[r].frozenKind[o] = "ACTIVE"
       /\ Pin(r, o, g, TRUE) \in pins
       /\ g \notin auth.deleted
       /\ history' =
           [history EXCEPT
               !.generationReadSeen = TRUE,
               !.lastGenerationRead =
                   [reader |-> r, owner |-> o, generation |-> g]]
       /\ UNCHANGED <<auth, build, reads, pins, d0, cutover>>

ReadLegacy(r, o) ==
    /\ reads[r].state = "FROZEN"
    /\ reads[r].frozenKind[o] = "LEGACY"
    /\ auth.legacyRetained[o]
    /\ history' =
        [history EXCEPT !.legacyReadSeen = TRUE]
    /\ UNCHANGED <<auth, build, reads, pins, d0, cutover>>

FinishRead(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads' = [reads EXCEPT ![r].state = "DONE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history, d0, cutover>>

InjectAuthorityFailure(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads' =
        [reads EXCEPT
            ![r].state = "REFUSED",
            ![r].error = "AUTHORITY_FAILURE",
            ![r].failureClass = "AUTHORITY",
            ![r].fallbackMode = "NONE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history, d0, cutover>>

InjectIntegrityFailure(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads' =
        [reads EXCEPT
            ![r].state = "REFUSED",
            ![r].error = "BACKEND_INTEGRITY",
            ![r].failureClass = "INTEGRITY",
            ![r].fallbackMode = "NONE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history, d0, cutover>>

UseMediatedTransientFallback(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads[r].fallbackMode = "NONE"
    /\ reads' =
        [reads EXCEPT
            ![r].failureClass = "TRANSIENT",
            ![r].fallbackMode = "MEDIATED"]
    /\ UNCHANGED <<auth, build, pins, history, d0, cutover>>

D0ChainComplete(o) ==
    /\ d0.candidate[o] # NoArtifact
    /\ d0.validated[o] = d0.candidate[o]
    /\ d0.ratified[o] = d0.candidate[o]

AcquireOwnerLock(o) ==
    /\ cutover.lockHeld[o] = "FREE"
    /\ cutover' = [cutover EXCEPT !.lockHeld[o] = "HELD"]
    /\ UNCHANGED <<auth, build, reads, pins, history, d0>>

ReleaseOwnerLock(o) ==
    /\ cutover.lockHeld[o] = "HELD"
    /\ cutover' = [cutover EXCEPT !.lockHeld[o] = "FREE"]
    /\ history' =
        [history EXCEPT
            !.lockCycleSeen = TRUE,
            !.lastLockOwner = o]
    /\ UNCHANGED <<auth, build, reads, pins, d0>>

CaptureD0Candidate(o) ==
    /\ o \in auth.present
    /\ OwnerMode(o) = "LEGACY"
    /\ d0.candidate[o] = NoArtifact
    /\ d0' =
        [d0 EXCEPT
            !.candidate[o] = CHOOSE a \in D0Artifacts : TRUE,
            !.legacyRootAtCapture[o] = auth.sourceHash[o]]
    /\ history' = [history EXCEPT !.d0CaptureSeen = TRUE]
    /\ UNCHANGED <<auth, build, reads, pins, cutover>>

ValidateD0Candidate(o) ==
    /\ d0.candidate[o] # NoArtifact
    /\ d0.validated[o] = NoArtifact
    /\ d0' = [d0 EXCEPT !.validated[o] = d0.candidate[o]]
    /\ history' = [history EXCEPT !.d0ValidationSeen = TRUE]
    /\ UNCHANGED <<auth, build, reads, pins, cutover>>

RatifyD0(o, qc) ==
    /\ qc \in QueryContexts
    /\ d0.validated[o] # NoArtifact
    /\ d0.ratified[o] = NoArtifact
    /\ d0' =
        [d0 EXCEPT
            !.ratified[o] = d0.validated[o],
            !.ratifiedQueryContext[o] = qc]
    /\ history' = [history EXCEPT !.d0RatificationSeen = TRUE]
    /\ UNCHANGED <<auth, build, reads, pins, cutover>>

ConvertLegacyToGRb(o) ==
    /\ D0ChainComplete(o)
    /\ cutover.grbBound[o] = NoGen
    /\ cutover.lockHeld[o] = "HELD"
    /\ auth' =
        [auth EXCEPT !.qualified = @ \cup {GRb}]
    /\ cutover' =
        [cutover EXCEPT
            !.grbBound[o] = GRb,
            !.retainedBaseline = @ \cup {GRb},
            !.proofProfile[GRb] = "UNKNOWN_MODEL_V1"]
    /\ UNCHANGED <<build, reads, pins, history, d0>>

RefusePreFenceStructural(o) ==
    /\ o \in auth.present
    /\ OwnerMode(o) = "LEGACY"
    /\ o \notin auth.fence
    /\ UNCHANGED vars

RebindLegacyRoot(o) ==
    /\ cutover.lockHeld[o] = "HELD"
    /\ D0ChainComplete(o)
    /\ d0' = [d0 EXCEPT !.legacyRootAtCutover[o] = auth.sourceHash[o]]
    /\ cutover' = [cutover EXCEPT !.phase[o] = "PREFLIGHT_OK"]
    /\ UNCHANGED <<auth, build, reads, pins, history>>

PublishDesignAFence(o, grant) ==
    /\ grant \in Grants
    /\ cutover.lockHeld[o] = "HELD"
    /\ cutover.phase[o] = "PREFLIGHT_OK"
    /\ o \notin auth.fence
    /\ CanBump(o)
    /\ auth' =
        [auth EXCEPT
            !.fence = @ \cup {o},
            !.evidenceEpoch[o] = @ + 1]
    /\ cutover' =
        [cutover EXCEPT
            !.grantId[o] = grant,
            !.phase[o] = "FENCED",
            !.fenceMonotonic[o] = TRUE]
    /\ UNCHANGED <<build, reads, pins, history, d0>>

CrashAfterFence(o) ==
    /\ cutover.phase[o] = "FENCED"
    /\ auth.pointer[o] = NoGen
    /\ UNCHANGED vars

ResumeFromFence(o, fresh_grant) ==
    /\ fresh_grant \in Grants
    /\ fresh_grant # cutover.grantId[o]
    /\ cutover.phase[o] = "FENCED"
    /\ auth.pointer[o] = NoGen
    /\ cutover.canaryGuard[o] = "ABSENT"
    /\ cutover' =
        [cutover EXCEPT
            !.priorGrantId[o] = cutover.grantId[o],
            !.grantId[o] = fresh_grant]
    /\ UNCHANGED <<auth, build, reads, pins, history, d0>>

PublishCanaryGuard(o, grant) ==
    /\ grant = cutover.grantId[o]
    /\ cutover.phase[o] = "FENCED"
    /\ cutover.canaryGuard[o] = "ABSENT"
    /\ cutover' =
        [cutover EXCEPT
            !.canaryGuard[o] = "OPEN",
            !.guardBytes[o] = TRUE,
            !.phase[o] = "GUARDED"]
    /\ UNCHANGED <<auth, build, reads, pins, history, d0>>

CrashAfterGuard(o) ==
    /\ cutover.phase[o] = "GUARDED"
    /\ auth.pointer[o] = NoGen
    /\ UNCHANGED vars

ResumeFromGuard(o, fresh_grant) ==
    /\ fresh_grant \in Grants
    /\ fresh_grant # cutover.grantId[o]
    /\ cutover.phase[o] = "GUARDED"
    /\ auth.pointer[o] = NoGen
    /\ cutover' =
        [cutover EXCEPT
            !.priorGrantId[o] = cutover.grantId[o],
            !.grantId[o] = fresh_grant]
    /\ UNCHANGED <<auth, build, reads, pins, history, d0>>

RefuseWrongGuard(o) ==
    /\ cutover.phase[o] = "FENCED"
    /\ cutover.canaryGuard[o] = "ABSENT"
    /\ cutover' = [cutover EXCEPT !.canaryGuard[o] = "REFUSED"]
    /\ auth.pointer[o] = NoGen
    /\ UNCHANGED <<auth, build, reads, pins, history, d0>>

PublishFirstPointer(o, grant) ==
    /\ grant = cutover.grantId[o]
    /\ cutover.phase[o] = "GUARDED"
    /\ cutover.grbBound[o] = GRb
    /\ auth.pointer[o] = NoGen
    /\ build.candidateGen[o] = GCanary
    /\ build.candidateCold[o]
    /\ CanBump(o)
    /\ auth' =
        [auth EXCEPT
            !.pointer[o] = GCanary,
            !.previous[o] = GRb,
            !.qualified = @ \cup {GCanary},
            !.manifestSource[o] = build.candidateSource[o],
            !.evidenceEpoch[o] = @ + 1]
    /\ cutover' =
        [cutover EXCEPT
            !.phase[o] = "POINTER_PUBLISHED",
            !.firstCutoverDone = @ \cup {o},
            !.proofProfile[GCanary] = "KNOWN_MODEL_V1"]
    /\ history' =
        [history EXCEPT
            !.firstCutoverSeen = TRUE,
            !.lastFirstCutover =
                [owner |-> o,
                 grant |-> grant,
                 legacyRoot |-> d0.legacyRootAtCutover[o],
                 casExpected |-> NoGen,
                 previous |-> GRb,
                 active |-> GCanary],
            !.promotionSeen = TRUE,
            !.lastPromotion =
                PromotionRecord(o, GCanary, NoGen, GRb, build.candidateSource[o])]
    /\ build' =
        [build EXCEPT
            !.candidateGen[o] = NoGen,
            !.candidateCold[o] = FALSE]
    /\ UNCHANGED <<reads, pins, d0>>

RefuseSecondPromotionWhileGuardOpen(o) ==
    /\ cutover.canaryGuard[o] = "OPEN"
    /\ o \in cutover.firstCutoverDone
    /\ build.candidateGen[o] # NoGen
    /\ UNCHANGED vars

ForwardPromote(o, g, expected_active) ==
    LET old == auth.pointer[o]
    IN /\ cutover.canaryGuard[o] # "OPEN"
       /\ g # NoGen
       /\ expected_active = old
       /\ build.candidateGen[o] = g
       /\ build.candidateCold[o]
       /\ build.candidateExpected[o] = old
       /\ build.candidateSource[o] = auth.sourceHash[o]
       /\ o \in auth.present
       /\ o \in auth.fence
       /\ o \notin auth.retired
       /\ o \notin auth.quarantined
       /\ CanBump(o)
       /\ auth' =
           [auth EXCEPT
               !.pointer[o] = g,
               !.previous[o] = old,
               !.qualified = @ \cup {g},
               !.manifestSource[o] = build.candidateSource[o],
               !.evidenceEpoch[o] = @ + 1]
       /\ build' =
           [build EXCEPT
               !.candidateGen[o] = NoGen,
               !.candidateCold[o] = FALSE]
       /\ history' =
           [history EXCEPT
               !.promotionSeen = TRUE,
               !.lastPromotion =
                   PromotionRecord(o, g, old, old, build.candidateSource[o])]
       /\ UNCHANGED <<reads, pins, d0, cutover>>

AdvanceSource(o, h) ==
    /\ h \in SourceHashes
    /\ h # auth.sourceHash[o]
    /\ auth' = [auth EXCEPT !.sourceHash[o] = h]
    /\ UNCHANGED <<build, reads, pins, history, d0, cutover>>

RollbackToRetained(o, target, expected_active, qc) ==
    /\ target \in cutover.retainedBaseline
    /\ expected_active = auth.pointer[o]
    /\ target = GRb => qc = d0.ratifiedQueryContext[o]
    /\ cutover.lockHeld[o] = "HELD"
    /\ CanBump(o)
    /\ LET stale == (auth.sourceHash[o] # auth.manifestSource[o])
       IN /\ auth' =
              [auth EXCEPT
                  !.pointer[o] = target,
                  !.previous[o] = expected_active,
                  !.evidenceEpoch[o] = @ + 1]
          /\ cutover' =
              IF stale
              THEN [cutover EXCEPT !.reconciliationDebt = @ \cup {o}]
              ELSE cutover
          /\ history' =
              [history EXCEPT
                  !.rollbackSeen = TRUE,
                  !.lastRollback =
                      [owner |-> o,
                       target |-> target,
                       expectedActive |-> expected_active,
                       queryContext |-> qc,
                       sourceStale |-> stale]]
    /\ UNCHANGED <<build, reads, pins, d0>>

RecoverExactPointer(o) ==
    /\ history' =
        [history EXCEPT
            !.recoverySeen = TRUE,
            !.lastRecovery =
                [owner |-> o,
                 pointerAtRecovery |-> auth.pointer[o],
                 completenessAtRecovery |-> auth.completeness[o],
                 selected |-> auth.pointer[o]]]
    /\ UNCHANGED <<auth, build, reads, pins, d0, cutover>>

DesignAAuthorityOps(o, grant, fresh_grant, qc) ==
    CaptureD0Candidate(o)
    \/ ValidateD0Candidate(o)
    \/ RatifyD0(o, qc)
    \/ AcquireOwnerLock(o)
    \/ ConvertLegacyToGRb(o)
    \/ RebindLegacyRoot(o)
    \/ PublishDesignAFence(o, grant)
    \/ CrashAfterFence(o)
    \/ ResumeFromFence(o, fresh_grant)
    \/ PublishCanaryGuard(o, grant)
    \/ CrashAfterGuard(o)
    \/ ResumeFromGuard(o, fresh_grant)
    \/ RefuseWrongGuard(o)
    \/ PublishFirstPointer(o, grant)
    \/ ReleaseOwnerLock(o)
    \/ RefusePreFenceStructural(o)
    \/ RefuseSecondPromotionWhileGuardOpen(o)
    \/ (\E g \in Generations, expected \in Generations :
          ForwardPromote(o, g, expected))
    \/ (\E h \in SourceHashes : AdvanceSource(o, h))
    \/ (\E target \in Generations, expected \in Generations :
          RollbackToRetained(o, target, expected, qc))
    \/ RecoverExactPointer(o)


Next ==
    \/ (\E o \in Owners, grant \in Grants, fresh_grant \in Grants, qc \in QueryContexts :
          DesignAAuthorityOps(o, grant, fresh_grant, qc))
    \/ (\E o \in Owners, g \in Generations : BuildCandidate(o, g))
    \/ (\E o \in Owners : ColdValidate(o))
    \/ (\E o \in Owners, h \in SourceHashes : LoseNotification(o, h))
    \/ (\E o \in Owners : Reconcile(o))
    \/ (\E o \in Owners : FenceOwner(o))
    \/ (\E o \in Owners : PromoteCandidate(o))
    \/ (\E o \in Owners : RejectStaleCandidate(o))
    \/ (\E o \in Owners, g \in Generations : ConcurrentPromotion(o, g))
    \/ BeginRename
    \/ RetireOldOwner
    \/ (\E o \in Owners : Recover(o))
    \/ (\E o \in Owners : FlipCompleteness(o))
    \/ (\E g \in Generations : GarbageCollect(g))
    \/ (\E o \in Owners : DropLegacy(o))
    \/ (\E r \in Readers : StartRequest(r))
    \/ (\E r \in Readers : ResolveStep(r))
    \/ (\E r \in Readers, o \in Owners : ReadGeneration(r, o))
    \/ (\E r \in Readers, o \in Owners : ReadLegacy(r, o))
    \/ (\E r \in Readers : FinishRead(r))
    \/ (\E r \in Readers : InjectAuthorityFailure(r))
    \/ (\E r \in Readers : InjectIntegrityFailure(r))
    \/ (\E r \in Readers : UseMediatedTransientFallback(r))

Spec ==
    /\ Init
    /\ [][Next]_vars
    /\ \A o \in Owners : WF_vars(Reconcile(o))
    /\ \A r \in Readers : WF_vars(ResolveStep(r))
    /\ \A r \in Readers : WF_vars(FinishRead(r))

(***************************************************************************
The lock evidence uses three property-focused exhaustive instances instead
of the monolithic Spec above.  Each instance retains every transition that can
affect its named properties while avoiding an operationally irrelevant cross
product (for example, recovery-history choices cannot affect rename pins).
***************************************************************************)

CutoverNext ==
    \/ (\E o \in Owners, grant \in Grants, fresh_grant \in Grants, qc \in QueryContexts :
          DesignAAuthorityOps(o, grant, fresh_grant, qc))
    \/ (\E g \in Generations : BuildCandidate(OldOwner, g))
    \/ ColdValidate(OldOwner)
    \/ FenceOwner(OldOwner)
    \/ PromoteCandidate(OldOwner)
    \/ RejectStaleCandidate(OldOwner)
    \/ (\E g \in Generations : ConcurrentPromotion(OldOwner, g))
    \/ (\E g \in Generations : GarbageCollect(g))
    \/ DropLegacy(OldOwner)
    \/ (\E r \in Readers : StartRequest(r))
    \/ (\E r \in Readers : ResolveStep(r))
    \/ (\E r \in Readers, o \in Owners : ReadGeneration(r, o))
    \/ (\E r \in Readers, o \in Owners : ReadLegacy(r, o))
    \/ (\E r \in Readers : FinishRead(r))
    \/ (\E r \in Readers : InjectAuthorityFailure(r))
    \/ (\E r \in Readers : InjectIntegrityFailure(r))
    \/ (\E r \in Readers : UseMediatedTransientFallback(r))

CutoverSpec ==
    /\ Init
    /\ [][CutoverNext]_vars
    /\ \A r \in Readers : WF_vars(ResolveStep(r))

StaleReconcileNext ==
    \/ (\E o \in Owners, grant \in Grants, fresh_grant \in Grants, qc \in QueryContexts :
          DesignAAuthorityOps(o, grant, fresh_grant, qc))
    \/ (\E g \in Generations : BuildCandidate(OldOwner, g))
    \/ ColdValidate(OldOwner)
    \/ (\E h \in SourceHashes : LoseNotification(OldOwner, h))
    \/ Reconcile(OldOwner)
    \/ FenceOwner(OldOwner)
    \/ PromoteCandidate(OldOwner)
    \/ RejectStaleCandidate(OldOwner)
    \/ (\E g \in Generations : ConcurrentPromotion(OldOwner, g))
    \/ RecoverExactPointer(OldOwner)
    \/ FlipCompleteness(OldOwner)
    \/ (\E g \in Generations : GarbageCollect(g))

StaleReconcileSpec ==
    /\ Init
    /\ [][StaleReconcileNext]_vars
    /\ WF_vars(Reconcile(OldOwner))

RenameNext ==
    (\E o \in Owners, g \in Generations : BuildCandidate(o, g))
    \/ (\E o \in Owners : ColdValidate(o))
    \/ FenceOwner(OldOwner)
    \/ (\E o \in Owners : PromoteCandidate(o))
    \/ (\E o \in Owners : RejectStaleCandidate(o))
    \/ BeginRename
    \/ RetireOldOwner
    \/ (\E g \in Generations : GarbageCollect(g))
    \/ (\E o \in Owners : DropLegacy(o))
    \/ (\E r \in Readers : StartRequest(r))
    \/ (\E r \in Readers : ResolveStep(r))
    \/ (\E r \in Readers, o \in Owners : ReadGeneration(r, o))
    \/ (\E r \in Readers, o \in Owners : ReadLegacy(r, o))
    \/ (\E r \in Readers : FinishRead(r))
    \/ (\E r \in Readers : InjectAuthorityFailure(r))
    \/ (\E r \in Readers : InjectIntegrityFailure(r))
    \/ (\E r \in Readers : UseMediatedTransientFallback(r))

RenameSpec ==
    /\ Init
    /\ [][RenameNext]_vars
    /\ \A r \in Readers : WF_vars(ResolveStep(r))


DesignANext ==
    (\E o \in Owners, grant \in Grants, fresh_grant \in Grants, qc \in QueryContexts :
        DesignAAuthorityOps(o, grant, fresh_grant, qc))
    \/ (\E g \in Generations : BuildCandidate(OldOwner, g))
    \/ ColdValidate(OldOwner)
    \/ (\E h \in SourceHashes : LoseNotification(OldOwner, h))
    \/ Reconcile(OldOwner)
    \/ (\E r \in Readers : StartRequest(r))
    \/ (\E r \in Readers : ResolveStep(r))
    \/ (\E r \in Readers, o \in Owners : ReadGeneration(r, o))
    \/ (\E r \in Readers, o \in Owners : ReadLegacy(r, o))
    \/ (\E r \in Readers : FinishRead(r))

DesignASpec ==
    /\ Init
    /\ [][DesignANext]_vars
    /\ WF_vars(Reconcile(OldOwner))

(***************************************************************************
Named checks.  The README maps each one to the architecture's twelve gates.
***************************************************************************)

QualifiedPointerServes ==
    \A o \in Owners :
        OwnerMode(o) = "ACTIVE" =>
            /\ auth.pointer[o] # NoGen
            /\ auth.pointer[o] \in auth.qualified
            /\ auth.pointer[o] \notin auth.deleted

SingleCurrentAuthority ==
    \A o \in Owners :
        Cardinality(IF OwnerMode(o) = "ACTIVE"
                    THEN {auth.pointer[o]} ELSE {}) <= 1

PostFenceNeverLegacy ==
    \A r \in Readers, o \in Owners :
        (reads[r].state \in {"FROZEN", "DONE"}
         /\ reads[r].frozenKind[o] = "LEGACY")
        => ~reads[r].linearizedAfterFence[o]

FrozenLegacyProtected ==
    \A r \in Readers, o \in Owners :
        (reads[r].state = "FROZEN"
         /\ reads[r].frozenKind[o] = "LEGACY")
        => auth.legacyRetained[o]

FrozenLegacyFinishEnabled ==
    \A r \in Readers :
        (reads[r].state = "FROZEN"
         /\ \E o \in Owners : reads[r].frozenKind[o] = "LEGACY")
        => ENABLED FinishRead(r)

PromotionChecksRecorded ==
    ~history.promotionSeen \/
        /\ history.lastPromotion.expected = history.lastPromotion.prior
        /\ history.lastPromotion.candidateSource =
              history.lastPromotion.sourceAtPublish
        /\ history.lastPromotion.coldValidated

RecoveryUsesExactPointer ==
    ~history.recoverySeen \/
        history.lastRecovery.selected =
            history.lastRecovery.pointerAtRecovery

GCRespectsProtection ==
    auth.deleted \cap ProtectedGenerations = {}

TentativePinWindowProtected ==
    \A r \in Readers, o \in Owners :
        (reads[r].state = "RESOLVING"
         /\ reads[r].phase[o] = "VERIFY"
         /\ reads[r].tentativeKind[o] = "ACTIVE")
        => /\ Pin(r, o, reads[r].tentativeGen[o], FALSE) \in pins
           /\ reads[r].tentativeGen[o] \notin auth.deleted

ValidatedTargetsRemainPinned ==
    \A r \in Readers, o \in Owners :
        (reads[r].state \in {"RESOLVING", "FROZEN"}
         /\ reads[r].phase[o] = "OWNER_DONE"
         /\ reads[r].selectedKind[o] = "ACTIVE")
        => /\ Pin(r, o, reads[r].selectedGen[o], TRUE) \in pins
           /\ reads[r].selectedGen[o] \notin auth.deleted

RenameVectorExclusive ==
    \A r \in Readers :
        reads[r].state \in {"FROZEN", "DONE"} =>
            ~(Admitted(reads[r].frozenKind[OldOwner])
              /\ Admitted(reads[r].frozenKind[NewOwner]))

FrozenGenerationStable ==
    \A r \in Readers, o \in Owners :
        reads[r].frozenGen[o] = reads[r].frozenWitness[o]

RetryBudgetTerminates ==
    \A r \in Readers, o \in Owners :
        /\ reads[r].attempts[o] <= MaxAttempts
        /\ (reads[r].state = "RESOLVING" =>
                reads[r].attempts[o] < MaxAttempts)
        /\ (reads[r].attempts[o] = MaxAttempts =>
                reads[r].state = "REFUSED"
                /\ reads[r].error = "AUTHORITY_UNSTABLE")

AuthorityFailuresNeverFallback ==
    \A r \in Readers :
        reads[r].failureClass \in {"AUTHORITY", "INTEGRITY"} =>
            /\ reads[r].state = "REFUSED"
            /\ reads[r].fallbackMode = "NONE"

FallbackIsMediated ==
    \A r \in Readers :
        reads[r].fallbackMode = "MEDIATED" =>
            /\ reads[r].failureClass = "TRANSIENT"
            /\ reads[r].state \in {"FROZEN", "DONE"}

GenerationReadsUseFrozenAuthority ==
    ~history.generationReadSeen \/
        history.lastGenerationRead.generation =
            reads[history.lastGenerationRead.reader].frozenWitness[
                history.lastGenerationRead.owner]

DriftPending(o) ==
    /\ o \in build.lostDrift
    /\ auth.sourceHash[o] # auth.manifestSource[o]
    /\ o \notin build.queued
    /\ o \notin auth.quarantined

DriftHandled(o) ==
    \/ o \in build.queued
    \/ o \in auth.quarantined
    \/ auth.sourceHash[o] = auth.manifestSource[o]

LostDriftEventuallyHandled ==
    \A o \in Owners : DriftPending(o) ~> DriftHandled(o)

ResolutionEventuallyTerminates ==
    \A r \in Readers :
        reads[r].state = "RESOLVING" ~>
            reads[r].state \in {"FROZEN", "REFUSED"}


UnknownModelOnlyForRatifiedLegacyBaseline ==
    \A g \in cutover.retainedBaseline :
        cutover.proofProfile[g] = "UNKNOWN_MODEL_V1"

ProspectiveGenerationRequiresKnownWriterModel ==
    \A g \in Generations :
        (g \in auth.qualified /\ g \notin cutover.retainedBaseline)
            => cutover.proofProfile[g] = "KNOWN_MODEL_V1"

D0CandidateNotAuthority ==
    \A o \in Owners :
        (d0.candidate[o] # NoArtifact /\ d0.ratified[o] = NoArtifact)
            => /\ OwnerMode(o) = "LEGACY"
               /\ auth.pointer[o] = NoGen

D0ValidationRequired ==
    ~history.d0RatificationSeen \/ history.d0ValidationSeen

D0RatificationRequired ==
    \A o \in Owners :
        cutover.grbBound[o] # NoGen => D0ChainComplete(o)

FirstCutoverRebindsCurrentLegacyRoot ==
    ~history.firstCutoverSeen \/ history.lastFirstCutover.legacyRoot =
        d0.legacyRootAtCutover[history.lastFirstCutover.owner]

GRollbackRequiresExactQueryContext ==
    ~history.rollbackSeen \/ history.lastRollback.target # GRb \/
        history.lastRollback.queryContext =
            d0.ratifiedQueryContext[history.lastRollback.owner]

FirstCutoverHasExactRollbackBaseline ==
    OldOwner \in cutover.firstCutoverDone =>
        /\ auth.previous[OldOwner] = GRb
           /\ GRb \in cutover.retainedBaseline

FirstCutoverGenerationsDistinct == GRb # GCanary

CASSeparateFromRollbackLineage ==
    ~history.promotionSeen \/ history.lastPromotion.expected = NoGen \/
        history.lastPromotion.expected = history.lastPromotion.prior

PreFenceRefusalPreservesLegacy ==
    \A o \in Owners :
        (OwnerMode(o) = "LEGACY" /\ o \notin auth.fence)
            => cutover.phase[o] \in {"NONE", "PREFLIGHT_OK"}

PostFenceFailureNeverLegacy ==
    \A o \in Owners :
        o \in auth.fence => OwnerMode(o) # "LEGACY"

FenceCrashResumeRequiresFreshGrant ==
    \A o \in Owners :
        (cutover.phase[o] = "FENCED" /\ auth.pointer[o] = NoGen)
            => cutover.grantId[o] # NoGrant

GuardCrashResumeRequiresFreshGrant ==
    \A o \in Owners :
        (cutover.phase[o] = "GUARDED" /\ auth.pointer[o] = NoGen)
            => cutover.grantId[o] # NoGrant

WrongGuardRefusesFirstPointer ==
    \A o \in Owners :
        cutover.canaryGuard[o] = "REFUSED" => auth.pointer[o] = NoGen

RollbackAfterSourceAdvanceKeepsReconciliation ==
    ~history.rollbackSeen \/ ~history.lastRollback.sourceStale \/
        history.lastRollback.owner \in cutover.reconciliationDebt

RollbackNeverResurrectsLegacy ==
    \A o \in Owners :
        o \in auth.fence => OwnerMode(o) # "LEGACY"

RecoveryNeverSwitchesGeneration ==
    ~history.recoverySeen \/ history.lastRecovery.selected =
        history.lastRecovery.pointerAtRecovery

FirstCanaryBlocksSecondPromotion ==
    \A o \in Owners :
        (cutover.canaryGuard[o] = "OPEN" /\ o \in cutover.firstCutoverDone)
            => auth.pointer[o] = GCanary

RollbackBaselineNeverGCEligible ==
    cutover.retainedBaseline \cap auth.deleted = {}

AuthorityOperationAcquiresOwnerLockOnce ==
    ~history.lockCycleSeen \/ history.lastLockOwner \in Owners

FenceMonotonic ==
    \A o \in Owners :
        cutover.fenceMonotonic[o] => o \in auth.fence

FencedNoPointerState ==
    \A o \in Owners :
        (o \in auth.fence /\ o \notin cutover.firstCutoverDone)
            => auth.pointer[o] = NoGen

FirstCutoverCAS ==
    \A o \in Owners :
        o \in cutover.firstCutoverDone =>
            history.lastFirstCutover.casExpected = NoGen


=============================================================================
