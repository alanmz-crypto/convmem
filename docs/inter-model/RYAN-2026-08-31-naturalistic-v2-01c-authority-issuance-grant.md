# Ryan grant — Naturalistic PRE-G6 V2-01C Authority-Issuance Corrective

**Status:** `AUTHORIZED`  
**Arc:** Naturalistic ConvMem product-value evaluation  
**Date:** 2026-08-31  
**Issuer:** Ryan  
**Recorder:** Cursor (GitHub write path). ChatGPT could inspect the repo but
could not create the branch or file: GitHub integration returned
`403 Resource not accessible by integration`.  
**Implementation agent after this grant:** Cursor  
**Scope:** V2-01C only. No V2-02C, V2-03C, V2-04, G6/T0, Agent A/B,
naturalistic evidence collection, registry population, scoring, or product
interpretation.

This file is the durable GitHub routing record of Ryan's grant. Record it
before any V2-01C code change. The corrective implementation must remain a
clean descendant of the failed V2-01 tip, not of this docs branch.

---

## GitHub routing coordinates

| Item | Value |
|---|---|
| **Grant record branch** | `docs/2026-08-31-naturalistic-v2-01c-ryan-grant` |
| **Grant record base** | `1a72a761b2cca3d9f955ad09d7b8b265d1fcaa9c` |
| **Grant file** | `docs/inter-model/RYAN-2026-08-31-naturalistic-v2-01c-authority-issuance-grant.md` |
| **Grant commit subject** | `docs: record Ryan grant for Naturalistic V2-01C` |
| **Cursor semantic implementation parent** | `7b858e7b84686fe1d249634f29364ae7f8d6fa11` |
| **Recommended implementation branch** | `fix/2026-08-31-naturalistic-v2-01c-authority-issuance` |

That separation is load-bearing: this GitHub grant is durable routing
evidence. The corrective code must stay a clean descendant of the exact
failed V2-01 implementation.

**Repo-state note:** a branch named
`feat/2026-08-31-naturalistic-v2-04-adjudication` already exists.
**Do not treat that branch's existence as authorization.** V2-04 remains
blocked by Sol's audit until corrected `V2-01C → V2-02C → V2-03C` passes
the cross-slice gate.

---

# Handoff to Ryan — Authorize Naturalistic PRE-G6 V2-01C Authority-Issuance Corrective

**Arc:** Naturalistic ConvMem product-value evaluation  
**Requested action:** Ryan authorization for one bounded corrective implementation slice  
**Implementation agent after grant:** Cursor  
**Scope:** V2-01C only  
**No V2-02C / V2-03C / V2-04 work in this grant**

## Ryan decision

**Yes.** Ryan authorized V2-01C only on 2026-08-31. This file records that
grant. No broader implementation authorization was requested or granted.

## Locked architecture authority

PRE-G6 Contract V2 remains locked and valid at:

`9f4791c2744c02d742fdb9c0fa1e9dd150591ac1`

Canonical JCS digest:

`917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e`

Do not modify or reinterpret locked V2.

## Current implementation chain

Existing slices:

* V2-00 authority import: `fbb4316b60035ec07c01ac25e146b302e5c043f2`
* V2-01 identity/evidence: `7b858e7b84686fe1d249634f29364ae7f8d6fa11`
* V2-02 adapters/capabilities: `da62adb32485b6101eb2d05c172dfe205cca4b25`
* V2-03 resolver/firewall: `330e10bbc1f6289d723cc19ccfd0dbd21784a5df`

Codex Sol performed a fresh-seed cross-slice authority audit and returned:

**`STRUCTURAL REDESIGN REQUIRED`**

The locked architecture was not rejected.

The implementation chain was.

Sol found that V2-01 currently permits insufficiently verified identity/seal
declarations, V2-02 can self-certify capability, and V2-03 can convert
caller-supplied agreement into `EXACT_MATCH` without independently resolving
sealed P1 evidence.

The dependency order matters:

**V2-01C must be corrected first.**

Current V2-02 and V2-03 become stale for authority purposes when V2-01
identities change.

---

# Requested Ryan grant

Authorize Cursor to implement a **bounded V2-01C authority-issuance/sealing
corrective** on an isolated branch/worktree.

The purpose is:

> Make P1 produce genuinely issued, immutable, byte-verifiable
> occurrence/evidence authority that later V2-02C and V2-03C can safely consume.

This grant must stop before capability derivation or resolution
implementation.

---

# Required V2-01C corrections

## 1. Authoritative occurrence issuance

Current occurrence identity must no longer be accepted merely because callers
supplied non-empty strings.

Create an issuance path that binds an occurrence to sufficient evidence for:

* source occurrence;
* physical source instance;
* native/provider identity where available;
* revision/as-of identity;
* snapshot identity;
* source incarnation/recreation distinction;
* lineage authority;
* issuer/attestation evidence where claimed.

Delete/recreate, clone/import/restore, native-ID reuse, logical lineage and
current-state equivalence must not silently collapse into one authoritative
occurrence.

A content hash or locator must never substitute for occurrence identity.

## 2. Immutable P1 authority objects

Authority-bearing P1 objects must not remain freely mutable dataclasses on
the normative authority path.

Use a builder/finalization path that produces immutable or effectively
immutable sealed authority material.

Raw constructors may remain as data structures/tests where necessary, but
they must not themselves mint P1 authority.

## 3. Real seal verification

Before any P1 artifact can be consumed as authority, verification must fail
closed unless the artifact proves at least:

* sealed state;
* valid seal time;
* canonical content digest;
* recomputed digest equality;
* content/stage-bound artifact identity;
* correct artifact kind;
* required immediate parent bindings;
* parent digest consistency;
* construct-freeze binding where required.

Sol reproduced that an object with `sealed=false`, no seal time and
mismatched header digest could still feed a P2 `EXACT_MATCH`. That path must
become impossible.

## 4. Strict identity parsing

Correct permissive parsing such as:

`bool("false") == True`

Identity/attestation booleans and enums must parse strictly.

Malformed identity assertions must fail closed rather than acquire stronger
authority.

## 5. Lineage binding

Lineage edges must be bound to:

* the exact occurrence;
* the attester/issuer evidence;
* the relevant parent/revision evidence.

An arbitrary lineage declaration must not mint lineage authority.

## 6. Immediate-parent completeness

V2-06 may later provide the full transitive provenance DAG, but V2-01C must
already capture stable issuance and all required immediate parents.

Do not defer missing issuance authority on the theory that V2-06 can repair
it later.

A later provenance graph cannot retroactively make an improperly issued
occurrence authoritative.

## 7. Content-bound implementation identity where V2-01 depends on implementation behavior

Where P1 authority depends on canonicalizers, builders, issuers or
validators, bind behaviorally relevant implementation identity using
existing ConvMem content-bound authority patterns where appropriate.

Do not use a version label alone as proof of implementation identity.

---

# Strong reuse preference

Inspect and selectively reuse existing ConvMem authority machinery instead of
inventing a parallel Naturalistic authority framework.

Sol specifically identified promising existing patterns:

* R2b content-bound authority manifests;
* recursive provenance-envelope verification;
* cycle/missing-parent fail-closed validation;
* immutable/read-only authority inventory patterns;
* writer/authority separation.

Reuse only where semantics actually match.

Do **not** reuse:

* Chroma/search fallback as source truth;
* unverified provenance projections;
* V1 `ArtifactHeaderV1` unchanged if it cannot express the V2 authority
  requirements.

Sol explicitly warned against treating existing V1 single-parent headers as
sufficient without a V2 authority wrapper/transition plan.

---

# Required adversarial tests

At minimum prove rejection of:

1. `sealed=false`
2. absent seal time
3. mismatched content digest
4. mismatched artifact ID
5. wrong artifact kind/stage
6. missing required immediate parent
7. wrong parent digest
8. construct-freeze mismatch
9. arbitrary caller-supplied occurrence identity without issuance evidence
10. locator used as identity
11. content hash used as identity
12. delete/recreate/native-ID-reuse collision
13. clone/import/restore collision where physical identity should differ
14. malformed boolean such as `"false"`
15. lineage edge without attester evidence
16. lineage edge referring to the wrong occurrence
17. post-seal content mutation
18. raw/unfinalized object presented to an authority-consuming interface

Positive tests must show that a correctly issued and sealed P1 package
survives independent reconstruction/verification from canonical bytes.

---

# Required implementation output

Cursor should return:

1. exact parent SHA;
2. exact implementation SHA;
3. branch name;
4. changed-file inventory;
5. explanation of the authority issuance model;
6. explanation of canonical sealing and independent verification;
7. explanation of occurrence/incarnation/revision identity;
8. explanation of immediate-parent binding;
9. explicit list of existing ConvMem authority mechanisms reused;
10. focused and regression test results;
11. exact statement of what remains deferred to V2-02C, V2-03C and V2-06.

---

# Scope firewall

This authorization must **not** include:

* V2-02 capability corrections;
* V2-03 resolver corrections;
* V2-04/P3;
* target adjudication;
* multiplicity implementation;
* source-resolution execution;
* G6/T0 authorization;
* Agent A/B;
* naturalistic evidence collection;
* registry population;
* scoring;
* product interpretation;
* modifications to locked PRE-G6 V2.

Do not attempt to keep current V2-02/V2-03 identities artificially
compatible.

If correct V2-01 issuance changes their inputs/identities, they are expected
to become stale and be rebuilt afterward.

---

# STOP condition

After V2-01C implementation:

**STOP.**

Do not proceed automatically to V2-02C.

Route the exact V2-01C tip to an independent authority review.

The reviewer must answer:

> Does this exact tip now create genuine P1 occurrence/evidence authority,
> rather than merely accepting internally consistent declarations?

Only a PASS allows Ryan to issue a separate V2-02C grant.

## Reviewer seed

Use a **new seed preferred** for the V2-01C exact-tip authority review.

Reason: this is foundational issuance/sealing authority, and independent
reconstruction is more valuable than continuity with the implementation lane.

---

# Downstream routing after PASS

Only after V2-01C independently passes:

1. Ryan separately grants V2-02C:

   * capability derived per occurrence from verified P1 evidence;
   * profile expectation separated from evidence;
   * content-bound profile/implementation authority.

2. Independent V2-02C review.

3. Ryan separately grants V2-03C:

   * real read-only resolution over exact sealed P1 authority;
   * eliminate caller-supplied observations as resolver truth;
   * unique sealed parented P2 output.

4. Independent V2-03C review.

5. Fresh-seed cross-slice audit of corrected:

   `V2-01C → V2-02C → V2-03C`

6. Only a cross-slice PASS may reopen V2-04 implementation planning.

---

# Gate state

* Locked PRE-G6 V2: **VALID / LOCKED**
* V2-00 exact import: **survives**
* V2-01 current authority implementation: **requires corrective**
* V2-02 current tip: **expected stale after V2-01C**
* V2-03 current tip: **expected stale after V2-01C**
* V2-04: **BLOCKED**
* G6/T0: **CLOSED**
* naturalistic execution: **CLOSED**
* product inference: **UNAVAILABLE**

---

## TL;DR

[Arc Naturalistic ConvMem product-value evaluation] Ryan authorized V2-01C
only. Sol found that P1 does not yet issue/verifiably seal authoritative
identity, so V2-02 and V2-03 cannot safely build authority on top of it.
Cursor may implement one bounded V2-01C corrective: authoritative occurrence
issuance, immutable canonical sealing, independent byte verification, strict
identity/lineage parsing, and complete immediate-parent binding. Stop after
V2-01C and obtain a fresh independent exact-tip PASS before Ryan separately
grants V2-02C.
