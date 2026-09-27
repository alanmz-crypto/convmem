# Arc Brief — R2b Capture Authorization

> **Arc: R2b Capture Authorization.** Current-state snapshot. The Switchboard
> dependency below is static content attestation only and does not reopen live capture.

## 1. Product goal

ConvMem capture must prove that exported source, processed state and bound Chroma
state are one trusted source state while one Ryan-authorized exclusive writer-gate
lease is held continuously. The v2 implementation supplies the mechanism; live use
still requires separate coverage, duration, packet, grant and verification gates.

The current cross-arc goal is narrower: PR `#342` must carry an R2b writer-coverage
inventory whose authority-content identity matches its exact final governed bytes.
That is static merge evidence, not capture authority.

## 2. System state

```text
R2b v2 I1–I3 implementation on main
        │ no live lease / packet / capture authorized
        └─ static 120-member writer-coverage inventory
                    │
                    └─ Switchboard PR #342 changes governed mcp_server.py
                       and plans a governed doctor.py correction
                              │
                              ▼
                    independent final inventory rotation
                    + resolver/content-identity convergence
```

R2b v1 remains historical policy/provenance. V2 I1–I3 implementation and corrective
integration landed via PR `#264`; later I4–I8 operational steps remain blocked.

## 3. Repository facts and document map

| Artifact | Current state |
|---|---|
| V2 implementation | **LANDED** via PR `#264`; no live operation follows automatically |
| Normative v2 architecture | `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` |
| Normative v2 execution | `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` |
| V2 verification | `docs/plans/VERIFY-r2b-v2-quiescence.md`; no operational VERIFY PASS |
| Writer-coverage inventory | `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` |
| Switchboard PR | `#342`, base `5c6a4a8`, pre-correction head `94f29eb`; merge blocked |
| Governed member set | Exactly 120 paths; seed, closure and routes unchanged |
| Pre-correction identities | committed `b716152fbf725633a55371f6acf7ed5580a704bd`; resolved `e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b` |
| Expected final changed governed members | Exactly `mcp_server.py` and `doctor.py` versus fixed main; publisher is not governed |
| Cross-arc control document | This STATUS is the fifth exact reviewed plan blob for the Switchboard corrective |

Existing complete-data Restic artifacts remain backup evidence, not R2b source
authority. The Switchboard qualified runtime and its GitHub delivery are not R2b
capture inputs.

## 4. Completion state

| Milestone | Status | Blocking condition |
|---|---|---|
| V2 architecture and I1–I3 implementation | **LANDED / reviewed** | — |
| Historical authority-content convergence | **CLOSED** for its reviewed implementation | Does not transfer to changed PR bytes |
| Switchboard PR static content attestation | **PLAN ONLY / NOT CONVERGED** | Final governed edits, independent rotation and exact review |
| Exact-tip zero-bypass operational proof | **NOT ACCEPTED** | Separate future operational gate |
| Duration policy | **PENDING** | Separate benchmark and Ryan ratification |
| Live packet/lease/capture | **NOT STARTED / PROHIBITED** | All operational gates and fresh authority chain |
| Operational VERIFY and Ryan GATE | **NOT STARTED** | Later separately authorized attempt |

## 5. Current role and next action

For the Switchboard dependency, review only the static content-attestation plan:

- exact 120-member set, path-set/seed/closure/routes unchanged;
- only `mcp_server.py` and `doctor.py` differ from fixed main after all edits;
- only `R2B-V2-WRITER-COVERAGE-INVENTORY.json` changes in the held rotation;
- an independent lane derives the canonical manifest and computes
  `SHA256("r2b-v2-authority-content:v1:" + canonical_manifest)[:40]`;
- resolver identity, inventory binding/digest and artifact converge exactly; and
- before/after manifests and member-change proof remain durable.

Do not acquire a writer gate, create a packet, run capture, stop/start services,
mutate live state or advance I4–I8. Kiro next reviews the exact five-document
Switchboard plan correction; implementation needs a later Ryan grant.

## 6. Required future sequence

1. Kiro reviews the Switchboard semantic parent/overlay including this exact STATUS
   blob as the fifth reviewed control-plane input.
2. Ryan may separately grant the bounded Switchboard implementation file sets.
3. After all governed product edits, an independent lane derives the final canonical
   120-member manifest and updates only the inventory JSON.
4. Codex proves the member set, seed, closure and routes are unchanged; exactly
   `mcp_server.py` and `doctor.py` changed; every other member is byte-identical to
   fixed main; and all identity/digest/binding surfaces converge.
5. Existing R2b revision, coverage, authority-boundary, negative and shadow-writer
   tests plus the five Switchboard R2b failure nodes pass before PR merge review.
6. Any later live R2b attempt still starts from scratch with coverage acceptance,
   duration ratification, writer-quiescence authority, a fresh packet, Ryan ACCEPT,
   Ryan ACCEPT AND GRANT, one capture, independent VERIFY and Ryan GATE.

## 7. Hard stops

- No live lease, packet, capture directory, service/process or source mutation.
- No member-set, seed, closure, route, algorithm or coordinate change.
- No treating content identity as capture authority or operational VERIFY.
- No inventory rotation before all final governed edits are fixed.
- No self-derived identity accepted without independent recomputation and resolver
  convergence.
- Missing, duplicate, symlinked, uninspectable or unexpected governed members fail.
- No sixth reviewed control document, glob/prefix exception, or source-hash exclusion.
- Historical quarantined capture attempts remain unusable.
- Duration value `900` seconds is not ratified by this correction.

## 8. Relationship to ConvMem Switchboard

Arc ConvMem Switchboard changes a read-only MCP profile and now requires a contained
doctor response; both `mcp_server.py` and `doctor.py` are governed R2b writer-coverage
members. Its publisher correction is outside the R2b member set. This status update
records that static dependency only. It neither imports Switchboard runtime semantics
into R2b nor gives Switchboard authority to operate R2b.

## 9. Key files

| Purpose | Path |
|---|---|
| V2 architecture | `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` |
| V2 execution | `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` |
| V2 verification | `docs/plans/VERIFY-r2b-v2-quiescence.md` |
| Static inventory | `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` |
| Switchboard architecture | `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` §18.22.5 |

## 10. Update protocol

Keep this file a current-state snapshot. Update it when the cross-arc inventory
converges, the Switchboard PR merges/closes, or an R2b operational milestone changes.
Do not append session narrative. Keep one current milestone-level line.

| Date | Who | Change |
|---|---|---|
| 2026-09-27 | Codex + Astra | Recorded the plan-only PR `#342` static authority-content convergence dependency; live R2b operation remains prohibited. |

**TL;DR:** [Arc R2b Capture Authorization] V2 I1–I3 remain landed and live capture
remains prohibited. Switchboard PR `#342` adds only a static 120-member
authority-content convergence dependency, with exactly `mcp_server.py` and `doctor.py`
expected to differ after the separately reviewed correction.
