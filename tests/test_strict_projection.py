"""M3/T1–T2 cold lineage + independent replay (CORRECT B).

T3 reader capability remains intentionally absent/red until M4.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import pytest

from bound_read_scope import (
    CaptureIssuer,
    ProjectBinding,
    SourceRegistration,
    owner_digest,
    sha256_digest,
)
from provenance import (
    BINDING_VERSION,
    POLICY_VERSION,
    SCHEMA_SEMANTICS_BYTES,
    SCHEMA_SEMANTICS_SHA256,
    SCHEMA_VERSION,
    ProvenanceRegistry,
    base_envelope,
    provenance_commitment,
    root_binding,
)
from strict_evidence_state import (
    build_citation_map,
    disposition_id,
    materialize_authority_records,
    payload_sha256,
    semantic_sha256,
    strict_source_payload_sha256,
)
from strict_grounding import (
    compute_added_grounding_refs,
    compute_added_provenance_ids,
    grounding_entry_hash,
    load_bound_issuer_inventories,
    qualify_assertions,
    receipt_ref_for,
    strict_canonical_bytes,
)
from strict_projection import StrictProjectionError, qualify_authority_generation


def test_strict_projection_capability_present():
    spec = importlib.util.find_spec("strict_projection")
    assert spec is not None, "[T3] module strict_projection absent"
    module = importlib.import_module("strict_projection")
    # T3 reader remains red until M4; cold qualify is the M3 surface.
    assert hasattr(module, "qualify_authority_generation")
    assert not hasattr(module, "open_public_projection")
    assert not hasattr(module, "revoke_snapshot")


def test_strict_projection_source_has_no_publisher_or_openclaw_runtime_imports():
    """M3: cold qualify must not import publisher or OpenClaw runtime modules."""
    import ast

    forbidden = frozenset(
        {
            "strict_projection_publisher",
            "strict_openclaw_controller",
            "strict_openclaw_supervisor",
        }
    )
    src_path = Path("strict_projection.py")
    tree = ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
        for mod in modules:
            top = mod.split(".", 1)[0]
            assert top not in forbidden, f"forbidden import: {mod}"


# ---------------------------------------------------------------------------
# Synthetic two-head lineage helpers (hermetic; no live data)
# ---------------------------------------------------------------------------

_LINEAGE = "a" * 32
_TS = "2026-09-21T00:00:00Z"
_SCOPE = "sha256:" + ("2" * 64)
_REG = "sha256:" + ("3" * 64)
_BUILDER = "strict-projection-publisher/v1"
_TREE = "sha256:" + ("5" * 64)
_OWNER = owner_digest(
    scope_sha256=_SCOPE,
    registry_sha256=_REG,
    project_binding_id="project:convmem:v1",
)
_BLOB = b"test"
_BLOB_HEX = sha256_digest(_BLOB).removeprefix("sha256:")
_BLOB_SHA = "sha256:" + _BLOB_HEX
_BLOB_B64 = "dGVzdA=="
_AID = "00000000-0000-4000-8000-000000000001"
_AID2 = "00000000-0000-4000-8000-000000000002"
_ISSUER = "fixture-issuer"
_SRC = "src-reg-1"
_CAPTURE_ID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_CAPTURE_ID2 = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


def _self_hash(obj: dict[str, Any], field: str) -> str:
    body = {k: v for k, v in obj.items() if k != field}
    return sha256_digest(strict_canonical_bytes(body))


def _semantic_contract() -> dict[str, Any]:
    from strict_projection import _recompute_schema_digests

    sc = {
        "schema": "convmem.strict-semantic-contract.v1",
        "reducer_version": "v1",
        "grounding_version": "v1",
        "canonicalization_version": "v1",
        "identity_version": "v2",
        "search_kernel": "lexical_v1",
        "search_kernel_version": "1",
        "tokenizer_unicode_version": "15.1.0",
        "schema_digests": _recompute_schema_digests(),
        "contract_payload_sha256": "sha256:" + ("0" * 64),
    }
    sc["contract_payload_sha256"] = _self_hash(sc, "contract_payload_sha256")
    return sc


_SC_OBJ = _semantic_contract()
_SC = _SC_OBJ["contract_payload_sha256"]


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(strict_canonical_bytes(obj))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_bytes(b"")
        return
    path.write_bytes(b"".join(strict_canonical_bytes(r) + b"\n" for r in rows))


def _empty_grounding() -> dict[str, Any]:
    g = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [],
        "roots": [],
        "edges": [],
        "outputs": [],
        "receipts": [],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    g["grounding_payload_sha256"] = _self_hash(g, "grounding_payload_sha256")
    return g


def _empty_context(grounding_sha: str) -> dict[str, Any]:
    ctx = {
        "schema": "convmem.strict-provenance-context.v2",
        "schema_semantics": [],
        "policies": [],
        "recipes": [],
        "verified_channels": [],
        "registered_assertions": [],
        "grounding_sha256": grounding_sha,
        "context_payload_sha256": "sha256:" + ("0" * 64),
    }
    ctx["context_payload_sha256"] = _self_hash(ctx, "context_payload_sha256")
    return ctx


def _minimal_record(assertion_id: str, *, title: str = "t") -> dict[str, Any]:
    env = {
        "assertion_id": "00000000-0000-4000-8000-000000000001",
        "schema": "convmem/provenance-envelope-v1",
        "root_bindings": [
            {
                "source_identity": "fixture/source-a",
                "record_locator": "e1",
                "raw_record_sha256": "a" * 64,
                "input_view_sha256": "a" * 64,
            }
        ],
        "input_bindings": [],
        "selection_parameters": {"output_sha256": "a" * 64},
    }
    rec = {
        "schema": "convmem.bound-authority-record.v3",
        "project_binding_id": "project:convmem:v1",
        "source_registration_id": "src-reg-1",
        "authority_site": "example.com",
        "authority_domain": "coding",
        "record_kind": "observation",
        "logical_id": "find2_" + ("b" * 64),
        "assertion_id": assertion_id,
        "source_event_id": "evt_" + ("c" * 64),
        "producer": "fixture",
        "logical_key": "k1",
        "semantic_sha256": "sha256:" + ("0" * 64),
        "payload_sha256": "sha256:" + ("0" * 64),
        "title": title,
        "document": "doc",
        "observed_at": _TS,
        "recorded_at": _TS,
        "confidence_bps": 100,
        "relates_to_assertion_id": None,
        "target_assertion_id": None,
        "verification_result": None,
        "supersedes_assertion_ids": [],
        "decision_disposition_ref": None,
        "supersession_disposition_ref": None,
        "provenance_envelope": env,
        "provenance_commitment": "sha256:" + ("d" * 64),
        "origin_assurance": "untrusted",
        "provenance_qualification": {
            "commitments": "incomplete",
            "byte_grounding": "missing",
            "capture": "unattested",
            "transformer_cap": "untrusted",
        },
        "check_eligibility": "not_applicable",
    }
    rec["semantic_sha256"] = semantic_sha256(rec)
    rec["payload_sha256"] = payload_sha256(rec)
    return rec


def _snapshot_id(manifest: dict[str, Any]) -> str:
    body = {
        k: v
        for k, v in manifest.items()
        if k not in {"snapshot_id", "manifest_payload_sha256"}
    }
    import hashlib

    return "snap2_" + hashlib.sha256(strict_canonical_bytes(body)).hexdigest()


def _cutoff(lineage: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
    c = {
        "schema": "convmem.strict-source-cutoff.v1",
        "lineage_id": lineage,
        "mode": "fixture",
        "operations": ops,
        "cutoff_payload_sha256": "sha256:" + ("0" * 64),
    }
    c["cutoff_payload_sha256"] = _self_hash(c, "cutoff_payload_sha256")
    return c


def _empty_cutoff_digest(lineage: str = _LINEAGE, *, mode: str = "fixture") -> str:
    body = {
        "schema": "convmem.strict-source-cutoff.v1",
        "lineage_id": lineage,
        "mode": mode,
        "operations": [],
    }
    return sha256_digest(strict_canonical_bytes(body))


def _bundle(
    lineage: str,
    op: str,
    parent_manifest: str | None,
    *,
    batches: list[Any] | None = None,
) -> dict[str, Any]:
    g = _empty_grounding()
    ctx = _empty_context(g["grounding_payload_sha256"])
    b = {
        "schema": "convmem.strict-fixture-bundle.v2",
        "lineage_id": lineage,
        "operation_id": op,
        "expected_parent_manifest_sha256": parent_manifest,
        "batches": list(batches) if batches is not None else [],
        "dispositions": [],
        "provenance_context": ctx,
        "grounding": g,
        "built_at": _TS,
        "as_of": _TS,
        "expires_at": "2026-09-22T00:00:00Z",
        "fixture_payload_sha256": "sha256:" + ("0" * 64),
    }
    b["fixture_payload_sha256"] = _self_hash(b, "fixture_payload_sha256")
    return b


def _write_head(
    root: Path,
    *,
    seq: int,
    parent_snapshot_id: str | None,
    parent_manifest_sha256: str | None,
    records: list[dict[str, Any]],
    dispositions: list[dict[str, Any]],
    grounding: dict[str, Any],
    context: dict[str, Any],
    added_assertion_ids: list[str],
    added_disposition_ids: list[str],
    added_provenance_ids: list[str],
    added_grounding_refs: list[str],
    op_id: str,
    parent_ops: list[dict[str, Any]],
    batches: list[Any] | None = None,
    input_dispositions: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    citation_map = build_citation_map(records)
    input_obj = _bundle(
        _LINEAGE,
        op_id,
        parent_manifest_sha256,
        batches=batches,
    )
    # Keep bundle grounding/context/dispositions aligned with head inventories.
    input_obj["grounding"] = grounding
    input_obj["provenance_context"] = context
    input_obj["dispositions"] = (
        list(input_dispositions) if input_dispositions is not None else []
    )
    input_obj["fixture_payload_sha256"] = _self_hash(input_obj, "fixture_payload_sha256")
    source_prefix = sha256_digest(strict_canonical_bytes(input_obj["batches"]))
    ops = list(parent_ops) + [
        {
            "operation_id": op_id,
            "input_sha256": input_obj["fixture_payload_sha256"],
            "source_prefix_sha256": source_prefix,
        }
    ]
    cutoff = _cutoff(_LINEAGE, ops)
    records_digest = sha256_digest(
        b"".join(strict_canonical_bytes(r) + b"\n" for r in records) if records else b""
    )
    disp_digest = sha256_digest(
        b"".join(strict_canonical_bytes(d) + b"\n" for d in dispositions)
        if dispositions
        else b""
    )
    manifest: dict[str, Any] = {
        "schema": "convmem.bound-authority-manifest.v3",
        "lineage_id": _LINEAGE,
        "authority_seq": seq,
        "owner_digest": _OWNER,
        "snapshot_id": "pending",
        "parent_snapshot_id": parent_snapshot_id,
        "parent_manifest_sha256": parent_manifest_sha256,
        "scope_sha256": _SCOPE,
        "registry_sha256": _REG,
        "input_sha256": input_obj["fixture_payload_sha256"],
        "source_cutoff_sha256": cutoff["cutoff_payload_sha256"],
        "operation_id": op_id,
        "authority_records_sha256": records_digest,
        "record_count": len(records),
        "dispositions_sha256": disp_digest,
        "disposition_count": len(dispositions),
        "citation_map_sha256": citation_map["citation_map_payload_sha256"],
        "provenance_context_sha256": context["context_payload_sha256"],
        "grounding_sha256": grounding["grounding_payload_sha256"],
        "added_assertion_ids": added_assertion_ids,
        "added_disposition_ids": added_disposition_ids,
        "added_provenance_ids": added_provenance_ids,
        "added_grounding_refs": added_grounding_refs,
        "semantic_contract_sha256": _SC,
        "reducer_version": "v1",
        "canonicalization_version": "v1",
        "builder_version": _BUILDER,
        "builder_tree_sha256": _TREE,
        "built_at": _TS,
        "as_of": _TS,
        "expires_at": "2026-09-22T00:00:00Z",
        "manifest_payload_sha256": "sha256:" + ("0" * 64),
    }
    sid = _snapshot_id(manifest)
    manifest["snapshot_id"] = sid
    manifest["manifest_payload_sha256"] = _self_hash(manifest, "manifest_payload_sha256")
    auth = root / "authority" / sid
    auth.mkdir(parents=True)
    _write_json(auth / "input.json", input_obj)
    _write_json(auth / "source-cutoff.json", cutoff)
    _write_jsonl(auth / "records.jsonl", records)
    _write_jsonl(auth / "dispositions.jsonl", dispositions)
    _write_json(auth / "citation-map.json", citation_map)
    _write_json(auth / "provenance-context.json", context)
    _write_json(auth / "grounding.json", grounding)
    _write_json(auth / "manifest.json", manifest)
    return sid, manifest["manifest_payload_sha256"]


def _layout_enrollment(root: Path) -> None:
    layout = {
        "schema": "convmem.strict-generation-layout.v2",
        "authority_dir": "authority",
        "projection_dir": "projection",
        "active_dir": "active",
        "locks_dir": "locks",
        "control_dir": "control",
        "layout_payload_sha256": "sha256:" + ("0" * 64),
    }
    layout["layout_payload_sha256"] = _self_hash(layout, "layout_payload_sha256")
    _write_json(root / "layout.json", layout)
    enrollment = {
        "schema": "convmem.strict-enrollment.v1",
        "lineage_id": _LINEAGE,
        "slot_id": "b" * 32,
        "mode": "fixture",
        "owner_digest": _OWNER,
        "operator_uid": 1000,
        "controller_uid": 0,
        "supervisor_uid": 0,
        "runtime_uid": 1001,
        "scope_sha256": _SCOPE,
        "registry_sha256": _REG,
        "semantic_contract_sha256": _SC,
        "initial_source_cutoff_sha256": _empty_cutoff_digest(),
        "enrollment_payload_sha256": "sha256:" + ("0" * 64),
    }
    enrollment["enrollment_payload_sha256"] = _self_hash(
        enrollment, "enrollment_payload_sha256"
    )
    _write_json(root / "control" / "enrollment.json", enrollment)
    _write_json(root / "control" / "semantic-contract.json", dict(_SC_OBJ))


def _publish_unavailable(
    root: Path, *, seq: int, snapshot_id: str, manifest_sha: str, cutoff_sha: str
) -> str:
    pub = {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": _LINEAGE,
        "owner_digest": _OWNER,
        "epoch": seq + 1,
        "authority_seq": seq,
        "authority_snapshot_id": snapshot_id,
        "authority_manifest_sha256": manifest_sha,
        "authority_source_cutoff_sha256": cutoff_sha,
        "serving_generation_id": None,
        "projection_manifest_sha256": None,
        "semantic_contract_sha256": _SC,
        "pending_operation_id": None,
        "mode": "unavailable",
        "previous_publication_sha256": None,
        "freshness_anchor": {
            "boot_id": "boot",
            "authority_snapshot_id": snapshot_id,
            "sampled_wall_time": _TS,
            "sampled_boottime_ns": 0,
            "snapshot_deadline_boottime_ns": 1,
            "clock_review_ref": "clock:x",
        },
        "published_at": _TS,
        "publication_payload_sha256": "sha256:" + ("0" * 64),
    }
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    return pub["publication_payload_sha256"]


class _FakeScope:
    project = "convmem"
    site = "example.com"
    site_mode = "exact"
    domain = "coding"
    scope_sha256 = _SCOPE
    allowed_project_bindings = ["project:convmem:v1"]


class _FakeRegistry:
    registry_sha256 = _REG

    def binding(self, _bid: str) -> Any:
        class B:
            public_ref = "p" * 32
            capture_issuers = ()
            source_registrations = ()
            verification_producers = ()

        return B()


def _two_head_root(
    tmp_path: Path,
    *,
    h1_batches: list[Any] | None = None,
    h2_batches: list[Any] | None = None,
    plant_hand_records: bool = False,
) -> tuple[Path, str, str, str]:
    """Build H1 then H2; default empty admission so cold reconstruct can pass.

    When plant_hand_records=True, plants impossible hand-written records (empty
    batches) for cumulative-retention / forged-input adversarials.
    """
    root = tmp_path / "root"
    root.mkdir(parents=True)
    (root / "authority").mkdir()
    (root / "active").mkdir()
    (root / "control").mkdir()
    (root / "projection").mkdir()
    (root / "locks").mkdir()
    _layout_enrollment(root)

    g1 = _empty_grounding()
    c1 = _empty_context(g1["grounding_payload_sha256"])
    if plant_hand_records:
        rec1 = _minimal_record("obs2_" + ("1" * 64), title="one")
        records1 = [rec1]
        added1 = [rec1["assertion_id"]]
    else:
        records1 = []
        added1 = []
    sid1, hash1 = _write_head(
        root,
        seq=1,
        parent_snapshot_id=None,
        parent_manifest_sha256=None,
        records=records1,
        dispositions=[],
        grounding=g1,
        context=c1,
        added_assertion_ids=added1,
        added_disposition_ids=[],
        added_provenance_ids=[],
        added_grounding_refs=[],
        op_id="1" * 32,
        parent_ops=[],
        batches=h1_batches,
    )
    g2 = _empty_grounding()
    c2 = _empty_context(g2["grounding_payload_sha256"])
    cutoff1 = json.loads(
        (root / "authority" / sid1 / "source-cutoff.json").read_text(encoding="utf-8")
    )
    if h2_batches is None:
        prior = h1_batches if h1_batches is not None else []
        h2_batches = list(prior)
    if plant_hand_records:
        rec1 = _minimal_record("obs2_" + ("1" * 64), title="one")
        rec2 = _minimal_record("obs2_" + ("2" * 64), title="two")
        records2 = sorted([rec1, rec2], key=lambda r: r["assertion_id"])
        added2 = [rec2["assertion_id"]]
    else:
        records2 = []
        added2 = []
    sid2, hash2 = _write_head(
        root,
        seq=2,
        parent_snapshot_id=sid1,
        parent_manifest_sha256=hash1,
        records=records2,
        dispositions=[],
        grounding=g2,
        context=c2,
        added_assertion_ids=added2,
        added_disposition_ids=[],
        added_provenance_ids=[],
        added_grounding_refs=[],
        op_id="2" * 32,
        parent_ops=list(cutoff1["operations"]),
        batches=h2_batches,
    )
    cutoff2 = json.loads(
        (root / "authority" / sid2 / "source-cutoff.json").read_text(encoding="utf-8")
    )
    _publish_unavailable(
        root,
        seq=2,
        snapshot_id=sid2,
        manifest_sha=hash2,
        cutoff_sha=cutoff2["cutoff_payload_sha256"],
    )
    return root, sid2, hash2, sid1


def _bypass_builder_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hermetic cold tests pin builder_tree_sha256; bypass independent recompute."""
    monkeypatch.setattr(
        "strict_projection._recompute_builder_tree_sha256",
        lambda root=None: _TREE,
    )


def _reseal_authority_after_cutoff_edit(root: Path, auth: Path) -> Path:
    """Reseal cutoff + manifest + publication after mutating source-cutoff.json."""
    cutoff = json.loads((auth / "source-cutoff.json").read_text(encoding="utf-8"))
    cutoff["cutoff_payload_sha256"] = _self_hash(cutoff, "cutoff_payload_sha256")
    _write_json(auth / "source-cutoff.json", cutoff)
    man = json.loads((auth / "manifest.json").read_text(encoding="utf-8"))
    man["source_cutoff_sha256"] = cutoff["cutoff_payload_sha256"]
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    new_dir = root / "authority" / man["snapshot_id"]
    if new_dir != auth:
        auth.rename(new_dir)
        auth = new_dir
    _write_json(auth / "manifest.json", man)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text(encoding="utf-8"))
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["authority_source_cutoff_sha256"] = cutoff["cutoff_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    return auth


def test_cold_rejects_wrong_resealed_source_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    root, sid2, _, _ = _two_head_root(tmp_path)
    auth = root / "authority" / sid2
    cutoff = json.loads((auth / "source-cutoff.json").read_text(encoding="utf-8"))
    cutoff["operations"][-1]["source_prefix_sha256"] = "sha256:" + ("e" * 64)
    _write_json(auth / "source-cutoff.json", cutoff)
    _reseal_authority_after_cutoff_edit(root, auth)
    with pytest.raises(StrictProjectionError, match="source_prefix_mismatch"):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )


def test_cold_rejects_input_manifest_operation_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    root, sid2, _, _ = _two_head_root(tmp_path)
    auth = root / "authority" / sid2
    man = json.loads((auth / "manifest.json").read_text(encoding="utf-8"))
    man["operation_id"] = "9" * 32
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    new_dir = root / "authority" / man["snapshot_id"]
    if new_dir != auth:
        auth.rename(new_dir)
        auth = new_dir
    _write_json(auth / "manifest.json", man)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text(encoding="utf-8"))
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(
        StrictProjectionError, match="operation_id_input_manifest_mismatch"
    ):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )


def test_cold_rejects_non_prefix_and_reordered_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    # Non-prefix: H1 admits materializable batch_a; H2 retains state but substitutes
    # batch_b (valid scan shape) so cold reaches fixture_batches_not_prefix.
    root, binding, sid1, records, _batch_a = _materializable_seq1_root(tmp_path / "nonprefix")
    _, _, _, _, batch_b = _closed_admission_bundle(
        tmp_path / "nonprefix-b",
        event_key="scan-key-2",
        logical_key="subject-key-2",
        assertion_id=_AID2,
        capture_id=_CAPTURE_ID2,
        record_locator="event-2",
    )
    auth1 = root / "authority" / sid1
    man1 = json.loads((auth1 / "manifest.json").read_text(encoding="utf-8"))
    cutoff1 = json.loads((auth1 / "source-cutoff.json").read_text(encoding="utf-8"))
    grounding = json.loads((auth1 / "grounding.json").read_text(encoding="utf-8"))
    context = json.loads(
        (auth1 / "provenance-context.json").read_text(encoding="utf-8")
    )
    sid2, hash2 = _write_head(
        root,
        seq=2,
        parent_snapshot_id=sid1,
        parent_manifest_sha256=man1["manifest_payload_sha256"],
        records=sorted(records, key=lambda r: r["assertion_id"]),
        dispositions=[],
        grounding=grounding,
        context=context,
        added_assertion_ids=[],
        added_disposition_ids=[],
        added_provenance_ids=[],
        added_grounding_refs=[],
        op_id="2" * 32,
        parent_ops=list(cutoff1["operations"]),
        batches=[batch_b],
    )
    cutoff2 = json.loads(
        (root / "authority" / sid2 / "source-cutoff.json").read_text(encoding="utf-8")
    )
    _publish_unavailable(
        root,
        seq=2,
        snapshot_id=sid2,
        manifest_sha=hash2,
        cutoff_sha=cutoff2["cutoff_payload_sha256"],
    )
    with pytest.raises(StrictProjectionError, match="fixture_batches_not_prefix"):
        qualify_authority_generation(
            root=root,
            scope=_FakeScope(),  # type: ignore[arg-type]
            registry=_MaterialRegistry(binding),  # type: ignore[arg-type]
        )

    # Reordered: H1 commits [batch_a, batch_b]; H2 has both but wrong order.
    root2, binding2, sid1b, records2, batch_a2, batch_b2 = (
        _two_batch_materializable_seq1_root(tmp_path / "reorder")
    )
    auth_h1 = root2 / "authority" / sid1b
    man_h1 = json.loads((auth_h1 / "manifest.json").read_text(encoding="utf-8"))
    cutoff_h1 = json.loads(
        (auth_h1 / "source-cutoff.json").read_text(encoding="utf-8")
    )
    g_h1 = json.loads((auth_h1 / "grounding.json").read_text(encoding="utf-8"))
    c_h1 = json.loads(
        (auth_h1 / "provenance-context.json").read_text(encoding="utf-8")
    )
    sid2b, hash2b = _write_head(
        root2,
        seq=2,
        parent_snapshot_id=sid1b,
        parent_manifest_sha256=man_h1["manifest_payload_sha256"],
        records=sorted(records2, key=lambda r: r["assertion_id"]),
        dispositions=[],
        grounding=g_h1,
        context=c_h1,
        added_assertion_ids=[],
        added_disposition_ids=[],
        added_provenance_ids=[],
        added_grounding_refs=[],
        op_id="2" * 32,
        parent_ops=list(cutoff_h1["operations"]),
        batches=[batch_b2, batch_a2],
    )
    cutoff2b = json.loads(
        (root2 / "authority" / sid2b / "source-cutoff.json").read_text(encoding="utf-8")
    )
    _publish_unavailable(
        root2,
        seq=2,
        snapshot_id=sid2b,
        manifest_sha=hash2b,
        cutoff_sha=cutoff2b["cutoff_payload_sha256"],
    )
    with pytest.raises(StrictProjectionError, match="fixture_batches_not_prefix"):
        qualify_authority_generation(
            root=root2,
            scope=_FakeScope(),  # type: ignore[arg-type]
            registry=_MaterialRegistry(binding2),  # type: ignore[arg-type]
        )


def test_cold_rejects_duplicate_and_conflicting_cutoff_operation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    # Duplicate operation_id inside one cutoff.
    root, sid2, _, _ = _two_head_root(tmp_path / "dup")
    auth = root / "authority" / sid2
    cutoff = json.loads((auth / "source-cutoff.json").read_text(encoding="utf-8"))
    cutoff["operations"].append(dict(cutoff["operations"][-1]))
    _write_json(auth / "source-cutoff.json", cutoff)
    _reseal_authority_after_cutoff_edit(root, auth)
    with pytest.raises(StrictProjectionError, match="source_cutoff_operation_id"):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )
    # Conflicting: cutoff last entry input_sha256 disagrees with manifest.
    root2, sid2b, _, _ = _two_head_root(tmp_path / "conflict")
    auth2 = root2 / "authority" / sid2b
    cutoff2 = json.loads((auth2 / "source-cutoff.json").read_text(encoding="utf-8"))
    cutoff2["operations"][-1]["input_sha256"] = "sha256:" + ("c" * 64)
    _write_json(auth2 / "source-cutoff.json", cutoff2)
    _reseal_authority_after_cutoff_edit(root2, auth2)
    with pytest.raises(StrictProjectionError, match="input_sha256_cutoff_mismatch"):
        qualify_authority_generation(
            root=root2, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )


def test_cold_rejects_deleted_or_changed_retained_record(tmp_path: Path):
    root, sid2, _hash2, sid1 = _two_head_root(tmp_path, plant_hand_records=True)
    # Delete retained H1 record from H2.
    auth2 = root / "authority" / sid2
    rows = [
        json.loads(line)
        for line in auth2.joinpath("records.jsonl").read_text().splitlines()
        if line
    ]
    kept = [r for r in rows if r["assertion_id"].endswith("2" * 64)]
    _write_jsonl(auth2 / "records.jsonl", kept)
    with pytest.raises(StrictProjectionError):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )
    # Restore then mutate retained bytes.
    rec1 = _minimal_record("obs2_" + ("1" * 64), title="one")
    rec2 = _minimal_record("obs2_" + ("2" * 64), title="two")
    mutated = dict(rec1)
    mutated["title"] = "mutated"
    mutated["semantic_sha256"] = semantic_sha256(mutated)
    mutated["payload_sha256"] = payload_sha256(mutated)
    _write_jsonl(auth2 / "records.jsonl", sorted([mutated, rec2], key=lambda r: r["assertion_id"]))
    with pytest.raises(StrictProjectionError):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )
    del sid1


def test_cold_rejects_wrong_skipped_cyclic_parent_and_forged_deltas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import strict_projection as sp

    # Bind real builder-tree digest so earlier checks pass without bypassing validation.
    monkeypatch.setattr(f"{__name__}._TREE", sp._recompute_builder_tree_sha256())
    root, sid2, hash2, sid1 = _two_head_root(tmp_path)
    auth2 = root / "authority" / sid2
    man = json.loads((auth2 / "manifest.json").read_text())
    # Wrong parent hash.
    man["parent_manifest_sha256"] = "sha256:" + ("9" * 64)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    # snapshot_id no longer matches content-address — cold must reject.
    _write_json(auth2 / "manifest.json", man)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(StrictProjectionError):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )

    # Rebuild clean two-head and forge added arrays.
    root2, sid2b, hash2b, _ = _two_head_root(tmp_path / "b")
    auth = root2 / "authority" / sid2b
    man = json.loads((auth / "manifest.json").read_text())
    man["added_assertion_ids"] = sorted(man["added_assertion_ids"] + ["obs2_" + ("9" * 64)])
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    # Move directory to content-addressed id.
    new_dir = root2 / "authority" / man["snapshot_id"]
    auth.rename(new_dir)
    _write_json(new_dir / "manifest.json", man)
    pub = json.loads((root2 / "active" / f"{_LINEAGE}.json").read_text())
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root2 / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(StrictProjectionError, match="added_assertion_ids_mismatch"):
        qualify_authority_generation(
            root=root2, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )


def test_cold_rejects_forged_stored_hashes_and_citation_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import strict_projection as sp

    # Preserve independent builder-tree validation: plant the real digest, do not bypass.
    monkeypatch.setattr(f"{__name__}._TREE", sp._recompute_builder_tree_sha256())
    root, sid2, _, _ = _two_head_root(tmp_path, plant_hand_records=True)
    auth = root / "authority" / sid2
    rows = [
        json.loads(line)
        for line in auth.joinpath("records.jsonl").read_text().splitlines()
        if line
    ]
    forged = dict(rows[0])
    forged["provenance_qualification"] = {
        "commitments": "valid",
        "byte_grounding": "complete",
        "capture": "synthetic_fixture",
        "transformer_cap": "trusted",
    }
    forged["origin_assurance"] = "verified"
    forged["semantic_sha256"] = semantic_sha256(forged)
    forged["payload_sha256"] = payload_sha256(forged)
    rows[0] = forged
    rows.sort(key=lambda r: r["assertion_id"])
    _write_jsonl(auth / "records.jsonl", rows)
    # Reseal records digest + manifest payload so only independent requalify catches it.
    man = json.loads((auth / "manifest.json").read_text())
    man["authority_records_sha256"] = sha256_digest(
        b"".join(strict_canonical_bytes(r) + b"\n" for r in rows)
    )
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    new_dir = root / "authority" / man["snapshot_id"]
    if new_dir != auth:
        auth.rename(new_dir)
        auth = new_dir
    _write_json(auth / "manifest.json", man)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(StrictProjectionError):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )

    # Citation empty/swapped bindings on an otherwise-admissible materializable head.
    root3, binding3, sid3, _records3, _batch3 = _materializable_seq1_root(tmp_path / "cite")
    auth = root3 / "authority" / sid3
    cmap = json.loads((auth / "citation-map.json").read_text())
    assert cmap["citations"], "materializable head must expose citations to forge"
    for c in cmap["citations"]:
        c["root_bindings"] = []
        c["input_bindings"] = [{"forged": True}]
    cmap["citation_map_payload_sha256"] = _self_hash(cmap, "citation_map_payload_sha256")
    _write_json(auth / "citation-map.json", cmap)
    man = json.loads((auth / "manifest.json").read_text())
    man["citation_map_sha256"] = cmap["citation_map_payload_sha256"]
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    new_dir = root3 / "authority" / man["snapshot_id"]
    if new_dir != auth:
        auth.rename(new_dir)
    _write_json(new_dir / "manifest.json", man)
    pub = json.loads((root3 / "active" / f"{_LINEAGE}.json").read_text())
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root3 / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(StrictProjectionError, match="citation_map_mismatch"):
        qualify_authority_generation(
            root=root3,
            scope=_FakeScope(),  # type: ignore[arg-type]
            registry=_MaterialRegistry(binding3),  # type: ignore[arg-type]
        )


def test_delta_helpers_are_set_difference_not_all_registered():
    parent_g = _empty_grounding()
    child_g = _empty_grounding()
    blob = {"sha256": sha256_digest(b"a"), "length": 1, "bytes_b64": "YQ=="}
    child_g["blobs"] = [blob]
    child_g["grounding_payload_sha256"] = _self_hash(child_g, "grounding_payload_sha256")
    refs = compute_added_grounding_refs(parent_g, child_g)
    assert refs == [grounding_entry_hash("blob", blob)]
    parent_c = _empty_context(parent_g["grounding_payload_sha256"])
    child_c = _empty_context(child_g["grounding_payload_sha256"])
    child_c["registered_assertions"] = [
        {
            "assertion_id": "00000000-0000-4000-8000-000000000099",
            "provenance_commitment": "sha256:" + ("b" * 64),
            "envelope": {"assertion_id": "00000000-0000-4000-8000-000000000099"},
        }
    ]
    # Unsealed child will fail validate — only test set-difference helper shape via empty.
    assert compute_added_provenance_ids(parent_c, parent_c) == []


# ---------------------------------------------------------------------------
# Independent admission replay — materializable fixtures (not hand-impossible)
# ---------------------------------------------------------------------------


def _b64(raw: bytes) -> str:
    import base64

    return base64.b64encode(raw).decode("ascii")


def _default_context_materials() -> tuple[list, list, list]:
    policy = ProvenanceRegistry().current_policy
    schema_semantics = [
        {
            "schema_version": SCHEMA_VERSION,
            "binding_version": BINDING_VERSION,
            "semantic_bytes_b64": _b64(SCHEMA_SEMANTICS_BYTES),
            "semantic_sha256": "sha256:" + SCHEMA_SEMANTICS_SHA256,
        }
    ]
    policies = [
        {
            "policy_version": POLICY_VERSION,
            "semantic_bytes_b64": _b64(policy.semantic_bytes),
            "semantic_sha256": "sha256:" + policy.semantic_sha256,
            "rules": [],
        }
    ]
    recipe_bytes = b"convmem:root-recipe-v1"
    recipes = [
        {
            "recipe_id": "root-v1",
            "recipe_bytes_b64": _b64(recipe_bytes),
            "recipe_sha256": sha256_digest(recipe_bytes),
        }
    ]
    return schema_semantics, policies, recipes


def _seal_context(ctx: dict[str, Any]) -> dict[str, Any]:
    payload = {k: v for k, v in ctx.items() if k != "context_payload_sha256"}
    ctx["context_payload_sha256"] = sha256_digest(strict_canonical_bytes(payload))
    return ctx


def _source_record(*, provenance_assertion_id: str, logical_key: str = "subject-key-1") -> dict[str, Any]:
    return {
        "record_kind": "observation",
        "producer": "form-prod",
        "logical_key": logical_key,
        "title": "fixture title",
        "document": "fixture document",
        "observed_at": _TS,
        "confidence_bps": 7000,
        "relates_to_assertion_id": None,
        "target_assertion_id": None,
        "verification_result": None,
        "provenance_assertion_id": provenance_assertion_id,
    }


def _closed_admission_bundle(
    tmp_path: Path,
    *,
    logical_key: str = "subject-key-1",
    event_key: str = "scan-key-1",
    assertion_id: str = _AID,
    capture_id: str = _CAPTURE_ID,
    record_locator: str = "event-1",
) -> tuple[ProjectBinding, dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Build binding + grounding/context + one materializable batch/record set."""
    from strict_grounding import (
        compute_input_bindings_sha256,
        compute_submitted_views_sha256,
    )

    source = _source_record(provenance_assertion_id=assertion_id, logical_key=logical_key)
    # Blob bytes must be the exact canonical source payload (excl. provenance_assertion_id).
    source_payload_body = {
        k: v for k, v in source.items() if k != "provenance_assertion_id"
    }
    blob = strict_canonical_bytes(source_payload_body)
    payload = strict_source_payload_sha256(source)
    blob_hex = payload.removeprefix("sha256:")
    blob_sha = payload
    blob_b64 = _b64(blob)
    unlabeled = blob_hex
    env = base_envelope(
        assertion_id=assertion_id,
        root_bindings=[
            root_binding(
                source_identity="fixture/source-a",
                record_locator=record_locator,
                raw_record_sha256=blob_hex,
                input_view_sha256=blob_hex,
            )
        ],
        transformer_artifact_sha256=_BLOB_HEX,
        transformer_recipe_sha256=_BLOB_HEX,
        selection_parameters={"output_sha256": unlabeled},
        producer_class="agent",
        producer_assurance="claimed",
    )
    commitment = "sha256:" + provenance_commitment(env)

    def _make_receipt(roots: list[dict[str, Any]]) -> dict[str, Any]:
        receipt = {
            "schema": "convmem.capture-receipt.v1",
            "capture_id": capture_id,
            "capture_class": "synthetic_fixture",
            "capture_issuer_id": _ISSUER,
            "source_registration_id": _SRC,
            "source_event_id": "evt_placeholder",
            "provenance_assertion_id": assertion_id,
            "provenance_commitment": commitment,
            "input_bindings_sha256": compute_input_bindings_sha256(roots, []),
            "transformer_artifact_sha256": _BLOB_SHA,
            "recipe_sha256": _BLOB_SHA,
            "submitted_views_sha256": compute_submitted_views_sha256(roots, []),
            "returned_output_sha256": blob_sha,
            "captured_at": _TS,
            "receipt_payload_sha256": "sha256:" + ("0" * 64),
        }
        receipt["receipt_payload_sha256"] = _self_hash(receipt, "receipt_payload_sha256")
        return receipt

    root_bind = {
        "provenance_assertion_id": assertion_id,
        "provenance_commitment": commitment,
        "source_registration_id": _SRC,
        "source_event_id": "evt_placeholder",
        "source_identity": "fixture/source-a",
        "record_locator": record_locator,
        "raw_blob_sha256": blob_sha,
        "view_blob_sha256": blob_sha,
        "selector": {"kind": "identity"},
        "receipt_ref": "capture_" + ("0" * 64),
    }
    receipt = _make_receipt([root_bind])
    ref = receipt_ref_for(receipt)
    root_bind["receipt_ref"] = ref
    receipt = _make_receipt([root_bind])
    ref = receipt_ref_for(receipt)
    root_bind["receipt_ref"] = ref

    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [{"sha256": blob_sha, "length": len(blob), "bytes_b64": blob_b64}],
        "roots": [root_bind],
        "edges": [],
        "outputs": [
            {
                "provenance_assertion_id": assertion_id,
                "provenance_commitment": commitment,
                "output_blob_sha256": blob_sha,
            }
        ],
        "receipts": [receipt],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    grounding["grounding_payload_sha256"] = _self_hash(grounding, "grounding_payload_sha256")

    schema_semantics, policies, recipes = _default_context_materials()
    context = _seal_context(
        {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": schema_semantics,
            "policies": policies,
            "recipes": recipes,
            "verified_channels": [],
            "registered_assertions": [
                {
                    "assertion_id": assertion_id,
                    "provenance_commitment": commitment,
                    "envelope": env,
                }
            ],
            "grounding_sha256": grounding["grounding_payload_sha256"],
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )

    inv_root = tmp_path / "issuer_inventory"
    if inv_root.is_dir():
        os.chmod(inv_root, 0o755)
    inv_root.mkdir(exist_ok=True)
    inv_path = inv_root / f"{capture_id}.json"
    inv_path.write_bytes(strict_canonical_bytes(receipt))
    os.chmod(inv_path, 0o444)
    os.chmod(inv_root, 0o555)

    binding = ProjectBinding(
        id="project:convmem:v1",
        public_ref="a" * 32,
        project="convmem",
        domain_root="coding",
        site_mode="exact",
        site="example.com",
        non_expanding_roots=(),
        source_registrations=(
            SourceRegistration(
                id=_SRC,
                source_class="fixture_scan",
                source_identity="fixture/source-a",
                identity_match="exact",
                authorization_domain="coding",
                site="example.com",
                event_id_resolver="fixture_scan_event_v1",
            ),
        ),
        lineage_id=_LINEAGE,
        capture_issuers=(
            CaptureIssuer(
                issuer_id=_ISSUER,
                capture_class="synthetic_fixture",
                enrollment_sha256=_BLOB_SHA,
                receipt_root=str(inv_root),
                source_registration_ids=(_SRC,),
            ),
        ),
        verification_producers=(),
    )
    issuer_inventory = load_bound_issuer_inventories(binding.capture_issuers)
    quals = qualify_assertions(
        grounding=grounding,
        provenance_context=context,
        issuer_inventory=issuer_inventory,
        capture_issuers=binding.capture_issuers,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
    )
    registered = {
        assertion_id: {
            "assertion_id": assertion_id,
            "provenance_commitment": commitment,
            "envelope": env,
        }
    }
    scan = {
        "schema": "convmem.fixture-scan.v1",
        "event_key": event_key,
        "captured_at": "2026-09-21T00:00:01Z",
        "records": [source],
    }
    records = materialize_authority_records(
        binding=binding,
        source_registration_id=_SRC,
        scan=scan,
        registered_assertions=registered,
        qualification_by_provenance=quals,
    )
    batch = {"source_registration_id": _SRC, "source": scan}
    return binding, grounding, context, records, batch


def _combine_materializable_admissions(
    first: tuple[ProjectBinding, dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]],
    second: tuple[ProjectBinding, dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]],
) -> tuple[ProjectBinding, dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Merge two closed admissions into one cumulative grounding/context/record set."""
    binding, g1, c1, recs1, batch_a = first
    _binding2, g2, c2, recs2, batch_b = second
    del _binding2
    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": sorted(g1["blobs"] + g2["blobs"], key=lambda b: b["sha256"]),
        "roots": sorted(
            g1["roots"] + g2["roots"],
            key=lambda r: (
                r["provenance_assertion_id"],
                r["source_registration_id"],
                r["source_event_id"],
                r["record_locator"],
            ),
        ),
        "edges": [],
        "outputs": sorted(
            g1["outputs"] + g2["outputs"],
            key=lambda o: o["provenance_assertion_id"],
        ),
        "receipts": sorted(
            g1["receipts"] + g2["receipts"], key=lambda r: r["capture_id"]
        ),
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    grounding["grounding_payload_sha256"] = _self_hash(
        grounding, "grounding_payload_sha256"
    )
    registered = sorted(
        c1["registered_assertions"] + c2["registered_assertions"],
        key=lambda e: e["assertion_id"],
    )
    context = _seal_context(
        {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": c1["schema_semantics"],
            "policies": c1["policies"],
            "recipes": c1["recipes"],
            "verified_channels": [],
            "registered_assertions": registered,
            "grounding_sha256": grounding["grounding_payload_sha256"],
            "context_payload_sha256": "sha256:" + ("0" * 64),
        }
    )
    records = sorted(recs1 + recs2, key=lambda r: r["assertion_id"])
    return binding, grounding, context, records, batch_a, batch_b


class _MaterialRegistry:
    registry_sha256 = _REG

    def __init__(self, binding: ProjectBinding) -> None:
        self._binding = binding

    def binding(self, _bid: str) -> ProjectBinding:
        return self._binding


def _reseal_head_records(root: Path, auth: Path, records: list[dict[str, Any]]) -> Path:
    _write_jsonl(auth / "records.jsonl", records)
    man = json.loads((auth / "manifest.json").read_text(encoding="utf-8"))
    man["authority_records_sha256"] = sha256_digest(
        b"".join(strict_canonical_bytes(r) + b"\n" for r in records) if records else b""
    )
    man["record_count"] = len(records)
    citation_map = build_citation_map(records)
    _write_json(auth / "citation-map.json", citation_map)
    man["citation_map_sha256"] = citation_map["citation_map_payload_sha256"]
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    new_dir = root / "authority" / man["snapshot_id"]
    if new_dir != auth:
        auth.rename(new_dir)
        auth = new_dir
    _write_json(auth / "manifest.json", man)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text(encoding="utf-8"))
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    return auth


def _materializable_seq1_root(
    tmp_path: Path,
) -> tuple[Path, ProjectBinding, str, list[dict[str, Any]], dict[str, Any]]:
    root = tmp_path / "mat-root"
    root.mkdir()
    for name in ("authority", "active", "control", "projection", "locks"):
        (root / name).mkdir()
    _layout_enrollment(root)
    binding, grounding, context, records, batch = _closed_admission_bundle(tmp_path)
    added_prov = compute_added_provenance_ids(None, context)
    added_g = compute_added_grounding_refs(None, grounding)
    sid, man_hash = _write_head(
        root,
        seq=1,
        parent_snapshot_id=None,
        parent_manifest_sha256=None,
        records=sorted(records, key=lambda r: r["assertion_id"]),
        dispositions=[],
        grounding=grounding,
        context=context,
        added_assertion_ids=sorted(r["assertion_id"] for r in records),
        added_disposition_ids=[],
        added_provenance_ids=added_prov,
        added_grounding_refs=added_g,
        op_id="1" * 32,
        parent_ops=[],
        batches=[batch],
    )
    cutoff = json.loads(
        (root / "authority" / sid / "source-cutoff.json").read_text(encoding="utf-8")
    )
    _publish_unavailable(
        root,
        seq=1,
        snapshot_id=sid,
        manifest_sha=man_hash,
        cutoff_sha=cutoff["cutoff_payload_sha256"],
    )
    return root, binding, sid, records, batch


def _two_batch_materializable_seq1_root(
    tmp_path: Path,
) -> tuple[
    Path, ProjectBinding, str, list[dict[str, Any]], dict[str, Any], dict[str, Any]
]:
    """Seq-1 head whose cumulative batches are two distinct materializable scans."""
    root = tmp_path / "mat-root-2"
    root.mkdir()
    for name in ("authority", "active", "control", "projection", "locks"):
        (root / name).mkdir()
    _layout_enrollment(root)
    first = _closed_admission_bundle(
        tmp_path,
        event_key="scan-key-1",
        logical_key="subject-key-1",
    )
    second = _closed_admission_bundle(
        tmp_path,
        event_key="scan-key-2",
        logical_key="subject-key-2",
        assertion_id=_AID2,
        capture_id=_CAPTURE_ID2,
        record_locator="event-2",
    )
    binding, grounding, context, records, batch_a, batch_b = (
        _combine_materializable_admissions(first, second)
    )
    # Re-qualify/materialize under the merged inventories so planted records match cold replay.
    issuer_inventory = load_bound_issuer_inventories(binding.capture_issuers)
    quals = qualify_assertions(
        grounding=grounding,
        provenance_context=context,
        issuer_inventory=issuer_inventory,
        capture_issuers=binding.capture_issuers,
        allowed_issuer_ids={_ISSUER},
        allowed_source_registration_ids={_SRC},
    )
    registered = {
        e["assertion_id"]: e for e in context["registered_assertions"]
    }
    records = []
    for batch in (batch_a, batch_b):
        records.extend(
            materialize_authority_records(
                binding=binding,
                source_registration_id=batch["source_registration_id"],
                scan=batch["source"],
                registered_assertions=registered,
                qualification_by_provenance=quals,
                prior_records=records,
            )
        )
    records = sorted(records, key=lambda r: r["assertion_id"])
    added_prov = compute_added_provenance_ids(None, context)
    added_g = compute_added_grounding_refs(None, grounding)
    sid, man_hash = _write_head(
        root,
        seq=1,
        parent_snapshot_id=None,
        parent_manifest_sha256=None,
        records=records,
        dispositions=[],
        grounding=grounding,
        context=context,
        added_assertion_ids=sorted(r["assertion_id"] for r in records),
        added_disposition_ids=[],
        added_provenance_ids=added_prov,
        added_grounding_refs=added_g,
        op_id="1" * 32,
        parent_ops=[],
        batches=[batch_a, batch_b],
    )
    cutoff = json.loads(
        (root / "authority" / sid / "source-cutoff.json").read_text(encoding="utf-8")
    )
    _publish_unavailable(
        root,
        seq=1,
        snapshot_id=sid,
        manifest_sha=man_hash,
        cutoff_sha=cutoff["cutoff_payload_sha256"],
    )
    return root, binding, sid, records, batch_a, batch_b


def test_cold_admission_replay_accepts_materializable_fixture_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    root, binding, _sid, records, _batch = _materializable_seq1_root(tmp_path)
    assert records
    qualified = qualify_authority_generation(
        root=root,
        scope=_FakeScope(),  # type: ignore[arg-type]
        registry=_MaterialRegistry(binding),  # type: ignore[arg-type]
    )
    assert qualified.authority_seq == 1
    assert len(qualified.state_by_assertion) == len(records)


def test_cold_rejects_forged_input_to_record_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Planted records with empty batches cannot be reconstructed from input."""
    _bypass_builder_tree(monkeypatch)
    root, _sid, _, _ = _two_head_root(tmp_path, plant_hand_records=True)
    with pytest.raises(StrictProjectionError, match="admission_added_records_mismatch"):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )


def test_cold_rejects_wrong_source_payload_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    root, binding, sid, _records, batch = _materializable_seq1_root(tmp_path)
    auth = root / "authority" / sid
    # Corrupt the committed input scan so envelope output no longer binds.
    inp = json.loads((auth / "input.json").read_text(encoding="utf-8"))
    bad_source = dict(batch["source"]["records"][0])
    bad_source["title"] = "other-title"
    inp["batches"][0]["source"]["records"] = [bad_source]
    inp["fixture_payload_sha256"] = _self_hash(inp, "fixture_payload_sha256")
    _write_json(auth / "input.json", inp)
    # Reseal cutoff + manifest input link for the mutated input digest.
    cutoff = json.loads((auth / "source-cutoff.json").read_text(encoding="utf-8"))
    cutoff["operations"][-1]["input_sha256"] = inp["fixture_payload_sha256"]
    cutoff["operations"][-1]["source_prefix_sha256"] = sha256_digest(
        strict_canonical_bytes(inp["batches"])
    )
    _write_json(auth / "source-cutoff.json", cutoff)
    auth = _reseal_authority_after_cutoff_edit(root, auth)
    man = json.loads((auth / "manifest.json").read_text(encoding="utf-8"))
    man["input_sha256"] = inp["fixture_payload_sha256"]
    man["snapshot_id"] = _snapshot_id(man)
    man["manifest_payload_sha256"] = _self_hash(man, "manifest_payload_sha256")
    new_dir = root / "authority" / man["snapshot_id"]
    if new_dir != auth:
        auth.rename(new_dir)
        auth = new_dir
    _write_json(auth / "manifest.json", man)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text(encoding="utf-8"))
    pub["authority_snapshot_id"] = man["snapshot_id"]
    pub["authority_manifest_sha256"] = man["manifest_payload_sha256"]
    pub["freshness_anchor"]["authority_snapshot_id"] = man["snapshot_id"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(StrictProjectionError, match="admission_materialize:source_payload_binding"):
        qualify_authority_generation(
            root=root,
            scope=_FakeScope(),  # type: ignore[arg-type]
            registry=_MaterialRegistry(binding),  # type: ignore[arg-type]
        )


def test_cold_rejects_forged_eligibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    root, binding, sid, records, _batch = _materializable_seq1_root(tmp_path)
    auth = root / "authority" / sid
    forged = dict(records[0])
    assert forged["check_eligibility"] == "not_applicable"
    forged["check_eligibility"] = "qualified"
    forged["semantic_sha256"] = semantic_sha256(forged)
    forged["payload_sha256"] = payload_sha256(forged)
    _reseal_head_records(root, auth, [forged])
    with pytest.raises(StrictProjectionError, match="admission_added_records_mismatch"):
        qualify_authority_generation(
            root=root,
            scope=_FakeScope(),  # type: ignore[arg-type]
            registry=_MaterialRegistry(binding),  # type: ignore[arg-type]
        )


def test_cold_rejects_disposition_valid_only_under_different_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _bypass_builder_tree(monkeypatch)
    root, binding, sid1, records, batch = _materializable_seq1_root(tmp_path)
    # Build H2 that retains H1 and adds a withdrawal disposition whose basis
    # matches a foreign snapshot id (valid only under a different parent).
    auth1 = root / "authority" / sid1
    man1 = json.loads((auth1 / "manifest.json").read_text(encoding="utf-8"))
    cutoff1 = json.loads((auth1 / "source-cutoff.json").read_text(encoding="utf-8"))
    grounding = json.loads((auth1 / "grounding.json").read_text(encoding="utf-8"))
    context = json.loads((auth1 / "provenance-context.json").read_text(encoding="utf-8"))
    subject = records[0]
    foreign_parent = "snap2_" + ("f" * 64)
    withdraw = {
        "schema": "convmem.authority-disposition.v1",
        "action": "evidence_withdrawn",
        "project_binding_id": "project:convmem:v1",
        "subject_assertion_id": subject["assertion_id"],
        "subject_semantic_sha256": subject["semantic_sha256"],
        "target_assertion_ids": [],
        "basis_snapshot_id": foreign_parent,
        "expected_head_assertion_ids": [],
        "replaces_disposition_ref": None,
        "review_actor": "kiro",
        "review_role": "kiro-design-reviewer",
        "review_outcome": "pass",
        "reviewed_at": _TS,
        "ratifier_actor": "ryan",
        "ratifier_role": "ryan-authority-owner",
        "ratified_at": _TS,
        "rationale_sha256": "sha256:" + ("a" * 64),
    }
    # Cumulative batches unchanged (disposition-only delta).
    sid2, hash2 = _write_head(
        root,
        seq=2,
        parent_snapshot_id=sid1,
        parent_manifest_sha256=man1["manifest_payload_sha256"],
        records=sorted(records, key=lambda r: r["assertion_id"]),
        dispositions=sorted([withdraw], key=disposition_id),
        grounding=grounding,
        context=context,
        added_assertion_ids=[],
        added_disposition_ids=[disposition_id(withdraw)],
        added_provenance_ids=[],
        added_grounding_refs=[],
        op_id="2" * 32,
        parent_ops=list(cutoff1["operations"]),
        batches=[batch],
        input_dispositions=[withdraw],
    )
    cutoff2 = json.loads(
        (root / "authority" / sid2 / "source-cutoff.json").read_text(encoding="utf-8")
    )
    _publish_unavailable(
        root,
        seq=2,
        snapshot_id=sid2,
        manifest_sha=hash2,
        cutoff_sha=cutoff2["cutoff_payload_sha256"],
    )
    with pytest.raises(StrictProjectionError, match="admission_dispositions:withdraw_basis"):
        qualify_authority_generation(
            root=root,
            scope=_FakeScope(),  # type: ignore[arg-type]
            registry=_MaterialRegistry(binding),  # type: ignore[arg-type]
        )


def test_cold_rejects_wrong_schema_digest_and_wrong_contract_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Reader independently enforces contract digests/versions (no publisher import)."""
    _bypass_builder_tree(monkeypatch)
    root, _sid, _, _ = _two_head_root(tmp_path / "digest")
    contract = json.loads(
        (root / "control" / "semantic-contract.json").read_text(encoding="utf-8")
    )
    contract["schema_digests"] = [
        {
            "path": contract["schema_digests"][0]["path"],
            "sha256": "sha256:" + ("e" * 64),
        }
    ] + list(contract["schema_digests"][1:])
    contract["contract_payload_sha256"] = _self_hash(contract, "contract_payload_sha256")
    _write_json(root / "control" / "semantic-contract.json", contract)
    enrollment = json.loads(
        (root / "control" / "enrollment.json").read_text(encoding="utf-8")
    )
    enrollment["semantic_contract_sha256"] = contract["contract_payload_sha256"]
    enrollment["enrollment_payload_sha256"] = _self_hash(
        enrollment, "enrollment_payload_sha256"
    )
    _write_json(root / "control" / "enrollment.json", enrollment)
    pub = json.loads((root / "active" / f"{_LINEAGE}.json").read_text(encoding="utf-8"))
    pub["semantic_contract_sha256"] = contract["contract_payload_sha256"]
    pub["publication_payload_sha256"] = _self_hash(pub, "publication_payload_sha256")
    _write_json(root / "active" / f"{_LINEAGE}.json", pub)
    with pytest.raises(StrictProjectionError, match="schema_digests_mismatch"):
        qualify_authority_generation(
            root=root, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )

    root2, _sid2, _, _ = _two_head_root(tmp_path / "version")
    contract2 = json.loads(
        (root2 / "control" / "semantic-contract.json").read_text(encoding="utf-8")
    )
    contract2["search_kernel_version"] = "9"
    contract2["contract_payload_sha256"] = _self_hash(
        contract2, "contract_payload_sha256"
    )
    _write_json(root2 / "control" / "semantic-contract.json", contract2)
    enrollment2 = json.loads(
        (root2 / "control" / "enrollment.json").read_text(encoding="utf-8")
    )
    enrollment2["semantic_contract_sha256"] = contract2["contract_payload_sha256"]
    enrollment2["enrollment_payload_sha256"] = _self_hash(
        enrollment2, "enrollment_payload_sha256"
    )
    _write_json(root2 / "control" / "enrollment.json", enrollment2)
    pub2 = json.loads((root2 / "active" / f"{_LINEAGE}.json").read_text(encoding="utf-8"))
    pub2["semantic_contract_sha256"] = contract2["contract_payload_sha256"]
    pub2["publication_payload_sha256"] = _self_hash(pub2, "publication_payload_sha256")
    _write_json(root2 / "active" / f"{_LINEAGE}.json", pub2)
    with pytest.raises(
        StrictProjectionError, match="semantic_contract_search_kernel_version"
    ):
        qualify_authority_generation(
            root=root2, scope=_FakeScope(), registry=_FakeRegistry()  # type: ignore[arg-type]
        )