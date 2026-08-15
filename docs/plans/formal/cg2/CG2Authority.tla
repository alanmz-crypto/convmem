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
    MaxEvidenceEpoch

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

RequestStates == {"IDLE", "RESOLVING", "FROZEN", "REFUSED", "DONE"}
ResolvePhases == {"NOT_STARTED", "SNAPSHOT", "VERIFY", "OWNER_DONE"}
AuthorityKinds == {"LEGACY", "ACTIVE", "UNAVAILABLE", "EXCLUDED"}
Errors == {"NONE", "AUTHORITY_UNSTABLE", "RENAME_CONFLICT",
           "AUTHORITY_FAILURE", "BACKEND_INTEGRITY"}
FailureClasses == {"NONE", "AUTHORITY", "INTEGRITY", "TRANSIENT"}
FallbackModes == {"NONE", "MEDIATED"}

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

VARIABLES auth, build, reads, pins, history

vars == <<auth, build, reads, pins, history>>

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
     legacyReadSeen : BOOLEAN]

TypeOK ==
    /\ auth \in AuthType
    /\ build \in BuildType
    /\ reads \in [Readers -> ReaderType]
    /\ pins \in SUBSET [reader : Readers,
                         owner : Owners,
                         generation : Generations,
                         validated : BOOLEAN]
    /\ history \in HistoryType

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
         legacyReadSeen |-> FALSE]

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
    \cup PinnedGenerations

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
    /\ UNCHANGED <<auth, reads, pins, history>>

ColdValidate(o) ==
    /\ build.candidateGen[o] # NoGen
    /\ ~build.candidateCold[o]
    /\ build' = [build EXCEPT !.candidateCold[o] = TRUE]
    /\ UNCHANGED <<auth, reads, pins, history>>

LoseNotification(o, newHash) ==
    /\ o \in auth.present
    /\ o \notin build.lostDrift
    /\ newHash \in SourceHashes \ {auth.sourceHash[o]}
    /\ auth' = [auth EXCEPT !.sourceHash[o] = newHash]
    /\ build' = [build EXCEPT !.lostDrift = @ \cup {o}]
    /\ UNCHANGED <<reads, pins, history>>

ReconcileQueue(o) ==
    /\ o \in build.lostDrift
    /\ auth.sourceHash[o] # auth.manifestSource[o]
    /\ o \notin build.queued
    /\ o \notin auth.quarantined
    /\ build' = [build EXCEPT !.queued = @ \cup {o}]
    /\ UNCHANGED <<auth, reads, pins, history>>

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
    /\ UNCHANGED <<build, reads, pins, history>>

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
    /\ UNCHANGED <<build, reads, pins, history>>

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
       /\ UNCHANGED <<reads, pins>>

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
    /\ UNCHANGED <<auth, reads, pins>>

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
       /\ UNCHANGED <<build, reads, pins>>

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
    /\ UNCHANGED <<build, reads, pins, history>>

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
    /\ UNCHANGED <<build, reads, pins, history>>

Recover(o) ==
    /\ history' =
        [history EXCEPT
            !.recoverySeen = TRUE,
            !.lastRecovery =
                [owner |-> o,
                 pointerAtRecovery |-> auth.pointer[o],
                 completenessAtRecovery |-> auth.completeness[o],
                 selected |-> auth.pointer[o]]]
    /\ UNCHANGED <<auth, build, reads, pins>>

FlipCompleteness(o) ==
    /\ auth' = [auth EXCEPT !.completeness[o] = ~@]
    /\ UNCHANGED <<build, reads, pins, history>>

GarbageCollect(g) ==
    /\ g \in auth.qualified
    /\ g \notin auth.deleted
    /\ g \notin ProtectedGenerations
    /\ auth' = [auth EXCEPT !.deleted = @ \cup {g}]
    /\ UNCHANGED <<build, reads, pins, history>>

DropLegacy(o) ==
    /\ o \in auth.fence
    /\ auth.legacyRetained[o]
    /\ LegacyFrozenFor(o) = {}
    /\ auth' = [auth EXCEPT !.legacyRetained[o] = FALSE]
    /\ UNCHANGED <<build, reads, pins, history>>

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
    /\ UNCHANGED <<auth, build, pins, history>>

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
       /\ UNCHANGED <<auth, build, history>>

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
       /\ UNCHANGED <<auth, build, history>>

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
    /\ UNCHANGED <<auth, build, history>>

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
    /\ UNCHANGED <<auth, build, history>>

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
    /\ UNCHANGED <<auth, build, pins, history>>

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
    /\ UNCHANGED <<auth, build, history>>

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
       /\ UNCHANGED <<auth, build, reads, pins>>

ReadLegacy(r, o) ==
    /\ reads[r].state = "FROZEN"
    /\ reads[r].frozenKind[o] = "LEGACY"
    /\ auth.legacyRetained[o]
    /\ history' =
        [history EXCEPT !.legacyReadSeen = TRUE]
    /\ UNCHANGED <<auth, build, reads, pins>>

FinishRead(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads' = [reads EXCEPT ![r].state = "DONE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history>>

InjectAuthorityFailure(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads' =
        [reads EXCEPT
            ![r].state = "REFUSED",
            ![r].error = "AUTHORITY_FAILURE",
            ![r].failureClass = "AUTHORITY",
            ![r].fallbackMode = "NONE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history>>

InjectIntegrityFailure(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads' =
        [reads EXCEPT
            ![r].state = "REFUSED",
            ![r].error = "BACKEND_INTEGRITY",
            ![r].failureClass = "INTEGRITY",
            ![r].fallbackMode = "NONE"]
    /\ pins' = pins \ ReaderPins(r)
    /\ UNCHANGED <<auth, build, history>>

UseMediatedTransientFallback(r) ==
    /\ reads[r].state = "FROZEN"
    /\ reads[r].fallbackMode = "NONE"
    /\ reads' =
        [reads EXCEPT
            ![r].failureClass = "TRANSIENT",
            ![r].fallbackMode = "MEDIATED"]
    /\ UNCHANGED <<auth, build, pins, history>>

Next ==
    (\E o \in Owners, g \in Generations : BuildCandidate(o, g))
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
    (\E g \in Generations : BuildCandidate(OldOwner, g))
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
    (\E g \in Generations : BuildCandidate(OldOwner, g))
    \/ ColdValidate(OldOwner)
    \/ (\E h \in SourceHashes : LoseNotification(OldOwner, h))
    \/ Reconcile(OldOwner)
    \/ FenceOwner(OldOwner)
    \/ PromoteCandidate(OldOwner)
    \/ RejectStaleCandidate(OldOwner)
    \/ (\E g \in Generations : ConcurrentPromotion(OldOwner, g))
    \/ Recover(OldOwner)
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

=============================================================================
