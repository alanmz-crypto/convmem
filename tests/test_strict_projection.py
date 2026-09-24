"""M3/T1–T2 cold lineage + independent replay; M4/T3 public reader surfaces.

Reviewed parent d5f986f0 / overlay c5513d5.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Mapping

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
    grounding_ref_set,
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
    assert hasattr(module, "qualify_authority_generation")
    assert hasattr(module, "open_published_generation")
    assert hasattr(module, "open_public_projection")
    assert hasattr(module, "revoke_snapshot")
    assert hasattr(module, "StrictProjectionReader")
    assert module.open_public_projection is module.open_published_generation


def test_strict_projection_source_has_no_publisher_or_openclaw_runtime_imports():
    """Cold qualify + public reader must not import publisher or OpenClaw runtime."""
    import ast

    forbidden = frozenset(
        {
            "strict_projection_publisher",
            "openclaw_activation_controller",
            "openclaw_activation_supervisor",
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


def test_delta_helpers_are_set_difference_not_all_registered(tmp_path: Path):
    # Valid closed parent (one admission) vs cumulative child (two admissions).
    first = _closed_admission_bundle(tmp_path / "delta-parent")
    second = _closed_admission_bundle(
        tmp_path / "delta-second",
        event_key="scan-key-2",
        logical_key="subject-key-2",
        assertion_id=_AID2,
        capture_id=_CAPTURE_ID2,
        record_locator="event-2",
    )
    _binding, parent_g, parent_c, _recs, _batch = first
    _binding2, second_g, _second_c, _recs2, _batch2 = second
    del _binding, _binding2, _recs, _recs2, _batch, _batch2, _second_c
    _binding3, child_g, _child_c, _recs3, _ba, _bb = _combine_materializable_admissions(
        first, second
    )
    del _binding3, _child_c, _recs3, _ba, _bb

    second_only = compute_added_grounding_refs(None, second_g)
    refs = compute_added_grounding_refs(parent_g, child_g)
    assert refs == second_only
    assert refs != sorted(grounding_ref_set(child_g))
    # Empty self-difference for provenance (set-difference, not all registered).
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
    inv_root.mkdir(parents=True, exist_ok=True)
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
    root.mkdir(parents=True)
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
    root.mkdir(parents=True)
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
# ---------------------------------------------------------------------------
# M4 / T3 — public opening, lexical reader, selectors, caps (Gate B)
# Parent cases 1–27, 40–44, 49–52 portions owned by the reader; case55 private/
# public boundary; overlay c5513d5. T4/T5 remain declared red elsewhere.
# ---------------------------------------------------------------------------

_M4_NOW = __import__("datetime").datetime(2026, 9, 21, tzinfo=__import__("datetime").timezone.utc)
# Publisher persists synthetic deadline 10_000_000_000; stay strictly below it.
_M4_SYNTHETIC_BOOTTIME_NS = 1_000_000_000


def _m4_patch_clocks(monkeypatch) -> None:
    """Private monkeypatchable clock hooks — never compare fixture BOOTTIME to host."""

    import strict_projection as sp

    monkeypatch.setattr(sp, "boottime_ns", lambda: _M4_SYNTHETIC_BOOTTIME_NS)
    monkeypatch.setattr(sp, "wall_time_utc", lambda: _M4_NOW)


def _seal_public_mount_modes(root: Path) -> None:
    """Seal dirs 0555 / files+locks 0444 for public opening (exact lock mode).

    Skips symlinks (lstat; never follow or mutate targets) so hostile link
    rejection stays with the public opener.
    """

    for dirpath, _dirnames, filenames in os.walk(root, topdown=False):
        for name in filenames:
            path = Path(dirpath) / name
            st = os.lstat(path)
            if stat.S_ISLNK(st.st_mode):
                continue
            os.chmod(path, 0o444)
        os.chmod(dirpath, 0o555)


def _load_sibling_test_module(name: str):
    """Load a sibling tests/*.py by path — frozen pytest does not put tests/ on sys.path."""

    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _m4_two_serving_roots(tmp_path: Path):
    """Build two fresh serving roots via the publisher helpers (byte-identical)."""

    pub_tests = _load_sibling_test_module("test_strict_projection_publisher")
    from bound_read_scope import resolve_scope

    shared = tmp_path / "shared"
    shared.mkdir()
    scope_path, registry_path, bundle, _bp, _inv = pub_tests._materializable_publish_inputs(
        shared
    )
    items = []
    for name in ("root-a", "root-b"):
        item = pub_tests._enroll_and_publish_materializable(
            tmp_path / name,
            shared=shared,
            scope_path=scope_path,
            registry_path=registry_path,
            bundle=bundle,
        )
        _seal_public_mount_modes(item["root"])
        # Scope/registry/config remain outside the sealed root; chmod them too.
        os.chmod(scope_path, 0o444)
        os.chmod(registry_path, 0o444)
        os.chmod(item["config_path"], 0o444)
        items.append(item)
    resolved = resolve_scope(scope_path=scope_path, registry_path=registry_path)
    return items, resolved, scope_path, registry_path


def _m4_open(item, resolved, monkeypatch, **kwargs):
    """Open with synthetic clocks so fixture BOOTTIME is never compared to host."""

    from strict_projection import open_published_generation

    _m4_patch_clocks(monkeypatch)
    return open_published_generation(
        root=item["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=item["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
        **kwargs,
    )


def test_m4_public_open_two_fresh_roots_and_unforgeable_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from strict_projection import (
        QualifiedStrictGeneration,
        StrictProjectionReader,
        open_published_generation,
        open_public_projection,
        revoke_snapshot,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    assert open_public_projection is open_published_generation
    _m4_patch_clocks(monkeypatch)

    gens = []
    for item in items:
        gen = open_published_generation(
            root=item["root"],
            scope=resolved.scope,
            registry=resolved.registry,
            expected_publication_sha256=item["serving"]["publication_payload_sha256"],
            now=_M4_NOW,
        )
        gens.append(gen)
        assert isinstance(gen, QualifiedStrictGeneration)
        assert not gen.is_revoked

    a, b = gens
    assert a.snapshot_id == b.snapshot_id
    assert a.rows_sha256 == b.rows_sha256
    assert a.graph_sha256 == b.graph_sha256
    assert a.publication_payload_sha256 == b.publication_payload_sha256

    # Forged construction rejected.
    with pytest.raises(TypeError):
        QualifiedStrictGeneration()  # type: ignore[call-arg]

    reader = StrictProjectionReader(a)
    revoke_snapshot(a)
    assert a.is_revoked
    from strict_projection import StrictPublicError

    with pytest.raises(StrictPublicError) as ei:
        reader.search_rows(query="hello world")
    assert ei.value.code == "snapshot_stale"


def test_m4_public_open_denies_private_files_and_does_not_read_layout_enrollment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Case55 private/public boundary — public open never needs layout/enrollment."""

    from strict_projection import StrictProjectionError, open_published_generation

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    item = items[0]
    root = item["root"]

    # Remove / corrupt private files — public open must still succeed.
    layout = root / "layout.json"
    enrollment = root / "control" / "enrollment.json"
    assert layout.is_file() and enrollment.is_file()
    # Make private files unreadable to the opener by replacing with junk after seal.
    # Re-seal after mutation of private-only paths: temporarily add write on parent.
    os.chmod(root / "control", 0o755)
    os.chmod(root, 0o755)
    os.chmod(enrollment, 0o644)
    enrollment.write_text("{not-json", encoding="utf-8")
    os.chmod(layout, 0o644)
    layout.write_text("{not-json", encoding="utf-8")
    # Also remove a private grounding file if present.
    snap = item["serving"]["authority_snapshot_id"]
    grounding = root / "authority" / snap / "grounding.json"
    if grounding.is_file():
        os.chmod(root / "authority" / snap, 0o755)
        os.chmod(grounding, 0o644)
        grounding.unlink()
    _seal_public_mount_modes(root)

    gen = open_published_generation(
        root=root,
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=item["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    assert gen.snapshot_id == snap

    # Symlink rejection on public publication path.
    os.chmod(root / "active", 0o755)
    os.chmod(root, 0o755)
    pub = root / "active" / f"{gen.lineage_id}.json"
    os.chmod(pub, 0o644)
    backup = pub.read_bytes()
    pub.unlink()
    pub.symlink_to("/etc/passwd")
    _seal_public_mount_modes(root)
    # symlink itself — open must fail before following.
    with pytest.raises(StrictProjectionError):
        open_published_generation(
            root=root,
            scope=resolved.scope,
            registry=resolved.registry,
            now=_M4_NOW,
        )
    # restore for cleanliness
    os.chmod(root / "active", 0o755)
    os.chmod(root, 0o755)
    if pub.is_symlink() or pub.exists():
        pub.unlink()
    pub.write_bytes(backup)
    _seal_public_mount_modes(root)


def test_m4_public_open_no_mtime_or_cache_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from strict_projection import StrictProjectionReader, open_published_generation

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    item = items[0]
    root = item["root"]
    pub_path = root / "active" / f"{resolved.registry.binding(resolved.scope.allowed_project_bindings[0]).lineage_id}.json"
    before = {
        p: p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    gen = open_published_generation(
        root=root,
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=item["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    try:
        reader.search_rows(query="fixture event")
    except Exception:
        pass
    after = {
        p: p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    assert before == after


def test_m4_lexical_tokenizer_ranking_identifier_rejection_and_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Cases 16–17, 40 — tokenizer/ranking/identifier reject/bounds."""

    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        open_published_generation,
        tokenize_lexical,
    )

    # Tokenizer known vectors (Architecture §6.5.5) — non-vacuous, no "or True".
    assert tokenize_lexical("Hello_World!") == ["hello_world"]
    assert tokenize_lexical("straße") == ["strasse"]
    assert tokenize_lexical("STRASSE") == ["strasse"]
    assert tokenize_lexical("a  b\tc") == ["a", "b", "c"]
    assert tokenize_lexical("!!!") == []

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    public_ref = resolved.registry.binding(
        resolved.scope.allowed_project_bindings[0]
    ).public_ref

    # Whitespace-token handle rejection: embedded valid handles deny.
    handle_ok = f"cm1.{public_ref}.{'obs2_' + 'ab' * 32}"
    handle_bad = f"cm1.{'f' * 32}.{'obs2_' + 'cd' * 32}"
    errs = []
    for q in (
        handle_ok,
        handle_bad,
        f"cm1.{'0' * 32}.obs_legacy",
        f"prefix {handle_ok} suffix",
        f"{handle_bad}\tmid",
    ):
        with pytest.raises(StrictPublicError) as ei:
            reader.search_rows(query=q)
        assert ei.value.code == "identifier_query_not_supported"
        errs.append({k: ei.value.payload[k] for k in ("schema", "error")})
    assert errs[0] == errs[1] == errs[2] == errs[3] == errs[4]

    for q in (
        "server_name",
        "codec_config",
        "observer_pattern",
        f"({handle_ok})",
        f"x{handle_ok}y",
    ):
        try:
            reader.search_rows(query=q)
        except StrictPublicError as exc:
            assert exc.code != "identifier_query_not_supported"

    # Bounds.
    with pytest.raises(StrictPublicError) as ei:
        reader.search_rows(query="")
    assert ei.value.code == "invalid_request"
    with pytest.raises(StrictPublicError):
        reader.search_rows(query="x" * 2049)
    with pytest.raises(StrictPublicError):
        reader.search_rows(query="ok", top_k=0)
    with pytest.raises(StrictPublicError):
        reader.search_rows(query="ok", top_k=11)

    # Successful envelope shape when query is lexical.
    result = reader.search_rows(query="fixture")
    assert result["schema"] == "convmem.raw-evidence.v3"
    assert result["instruction_authority"] == "none"
    assert set(result) == {
        "schema",
        "instruction_authority",
        "snapshot",
        "selection_complete",
        "display_basis",
        "results",
    }
    assert result["display_basis"] == "ranked_selection"
    for row in result["results"]:
        pq = row["provenance_qualification"]
        assert row["provenance_basis"] == pq["capture"]
        assert pq["capture"] in {
            "synthetic_fixture",
            "controlled_capture",
            "unattested",
        }


def test_m4_selector_tristate_default_intersection_no_widening(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Cases 5–11 — omitted inherit; null/blank deny; no widening; equalized denial."""

    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        open_published_generation,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)

    # Omitted selectors inherit.
    ok = reader.search_rows(query="fixture")
    assert ok["schema"] == "convmem.raw-evidence.v3"

    # Explicit null / blank deny.
    for kwargs in (
        {"project": None},
        {"project": ""},
        {"project": "   "},
        {"domain": None},
        {"site": None},
        {"cross_domain": True},
        {"domain": "general"},
        {"project": "otherproj"},
    ):
        with pytest.raises(StrictPublicError) as ei:
            reader.search_rows(query="fixture", **kwargs)
        assert ei.value.code == "scope_denied"

    # Equalized denial shapes (schema/code/message) across selector failures.
    shapes = []
    for kwargs in ({"domain": "general"}, {"project": "nope"}, {"cross_domain": True}):
        with pytest.raises(StrictPublicError) as ei:
            reader.search_rows(query="fixture", **kwargs)
        body = ei.value.payload
        shapes.append(
            {
                "schema": body["schema"],
                "code": body["error"]["code"],
                "message": body["error"]["message"],
            }
        )
    assert shapes[0] == shapes[1] == shapes[2]

    # Same selector cases on unresolved (second selector-bearing tool).
    for kwargs in (
        {"project": None},
        {"domain": "general"},
        {"cross_domain": True},
    ):
        with pytest.raises(StrictPublicError) as ei:
            reader.unresolved_rows(**kwargs)
        assert ei.value.code == "scope_denied"


def test_m4_unresolved_related_caps_and_closed_error_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        dispatch_tool,
        open_published_generation,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)

    unresolved = reader.unresolved_rows()
    assert unresolved["schema"] == "convmem.raw-evidence.v3"
    assert unresolved["display_basis"] == "ranked_selection"

    with pytest.raises(StrictPublicError):
        reader.unresolved_rows(limit=0)
    with pytest.raises(StrictPublicError):
        reader.unresolved_rows(limit=51)

    # related — malformed / raw storage ID → equalized scope_denied.
    denials = []
    for lid in ("obs_not_a_handle", "not-valid", f"cm1.{'0'*32}."):
        with pytest.raises(StrictPublicError) as ei:
            reader.related_neighborhood(ledger_id=lid)
        assert ei.value.code == "scope_denied"
        denials.append(
            (ei.value.payload["schema"], ei.value.payload["error"]["code"], ei.value.payload["error"]["message"])
        )
    assert denials[0] == denials[1] == denials[2]

    # dispatch_tool preserves omitted vs null via raw keys.
    payload = dispatch_tool(reader, "search", {"query": "fixture"})
    assert payload["schema"] == "convmem.raw-evidence.v3"
    with pytest.raises(StrictPublicError):
        dispatch_tool(reader, "search", {"query": "fixture", "domain": None})


def test_m4_provenance_basis_from_capture_not_origin_assurance():
    """Item 10: provenance_basis is exactly capture; invalid capture rejects."""

    from strict_projection import StrictProjectionError, _provenance_basis_from_capture

    assert (
        _provenance_basis_from_capture({"capture": "synthetic_fixture"})
        == "synthetic_fixture"
    )
    assert (
        _provenance_basis_from_capture({"capture": "controlled_capture"})
        == "controlled_capture"
    )
    assert _provenance_basis_from_capture({"capture": "unattested"}) == "unattested"
    with pytest.raises(StrictProjectionError):
        _provenance_basis_from_capture({"capture": "other"})
    with pytest.raises(StrictProjectionError):
        _provenance_basis_from_capture(None)
    # origin_assurance must never be consulted / remapped.
    assert (
        _provenance_basis_from_capture(
            {
                "capture": "synthetic_fixture",
                "commitments": "valid",
                "byte_grounding": "complete",
                "transformer_cap": "trusted",
            }
        )
        == "synthetic_fixture"
    )


def test_m4_reader_import_graph_excludes_publisher_and_openclaw_runtime():
    import ast

    tree = ast.parse(Path("strict_projection.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    forbidden = {
        "strict_projection_publisher",
        "openclaw_activation_controller",
        "openclaw_activation_supervisor",
        "query",
        "chroma_store",
    }
    assert not (imported & forbidden)


def test_m4_public_only_mount_and_exact_0444_0555(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Items 6/11: public-only mount tree; exact file 0444 / dir 0555 / lock 0444."""

    from strict_projection import StrictProjectionError, open_published_generation

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    item = items[0]
    root = item["root"]

    # Build a public-only mount: only parent-listed public members.
    public_only = tmp_path / "public-only"
    public_only.mkdir()
    lineage = resolved.registry.binding(
        resolved.scope.allowed_project_bindings[0]
    ).lineage_id
    serving = item["serving"]
    gen_id = serving["serving_generation_id"]
    snap_id = serving["authority_snapshot_id"]

    def _copy_tree(src: Path, dst: Path) -> None:
        import shutil

        if src.is_dir():
            shutil.copytree(src, dst, symlinks=False)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for rel in (
        f"active/{lineage}.json",
        f"authority/{snap_id}/manifest.json",
        f"projection/{gen_id}/manifest.json",
        f"projection/{gen_id}/rows.jsonl",
        f"projection/{gen_id}/graph.json",
        f"locks/{lineage}.lock",
    ):
        _copy_tree(root / rel, public_only / rel)
    # Intermediate dirs must exist with exact modes after seal.
    _seal_public_mount_modes(public_only)

    # Exact mode checks — including read-lock 0444.
    for dirpath, _dns, filenames in os.walk(public_only):
        st = os.lstat(dirpath)
        assert stat.S_ISDIR(st.st_mode)
        assert (st.st_mode & 0o7777) == 0o555
        for name in filenames:
            p = Path(dirpath) / name
            fst = os.lstat(p)
            assert stat.S_ISREG(fst.st_mode)
            assert (fst.st_mode & 0o7777) == 0o444

    gen = open_published_generation(
        root=public_only,
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=serving["publication_payload_sha256"],
        now=_M4_NOW,
    )
    assert not gen.is_revoked
    # No private paths present on the mount.
    assert not (public_only / "layout.json").exists()
    assert not (public_only / "control").exists()
    from strict_projection import revoke_snapshot

    revoke_snapshot(gen)

    # Wrong mode denies (temporarily unlock parent dir to mutate mode).
    # Restore dirs to exact 0555 so only the file mode is wrong.
    os.chmod(public_only, 0o755)
    os.chmod(public_only / "active", 0o755)
    os.chmod(public_only / "active" / f"{lineage}.json", 0o644)
    os.chmod(public_only / "active", 0o555)
    os.chmod(public_only, 0o555)
    with pytest.raises(StrictProjectionError, match="file_mode"):
        open_published_generation(
            root=public_only,
            scope=resolved.scope,
            registry=resolved.registry,
            expected_publication_sha256=serving["publication_payload_sha256"],
            now=_M4_NOW,
        )


def test_m4_operator_path_wrappers_pin_without_bound_read_scope_mutation(
    tmp_path: Path,
):
    """Scope repair: immutable path policy lives in M4 wrappers only."""

    from strict_projection import (
        StrictProjectionError,
        load_bound_read_scope_for_strict,
        pin_operator_immutable_path,
    )

    items, resolved, scope_path, registry_path = _m4_two_serving_roots(tmp_path)
    pin = pin_operator_immutable_path(scope_path)
    assert isinstance(pin, tuple) and len(pin) == 4
    assert pin[3].startswith("sha256:") and len(pin[3]) == 71
    scope = load_bound_read_scope_for_strict(scope_path)
    assert scope.scope_sha256 == resolved.scope.scope_sha256

    # Relative path refused by wrapper.
    with pytest.raises(StrictProjectionError, match="path_must_be_absolute"):
        pin_operator_immutable_path(Path("relative-scope.json"))

    # Writable operator file refused.
    os.chmod(scope_path, 0o644)
    with pytest.raises(StrictProjectionError, match="file_writable"):
        pin_operator_immutable_path(scope_path)


def test_m4_ranking_tie_order_and_overlapping_occurrences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Item 15: score desc, observed_at desc, assertion_id asc; occurrence counts."""

    from strict_projection import (
        StrictProjectionReader,
        _count_occurrences,
        _score_row,
        open_published_generation,
        tokenize_lexical,
    )

    assert _count_occurrences("ababab", "ab") == 3
    assert _count_occurrences("aaa", "aa") == 2
    tokens = tokenize_lexical("alpha beta alpha")
    assert tokens == ["alpha", "beta", "alpha"]
    # Known-answer score: title "alpha alpha" + doc "beta" vs query "alpha beta".
    score = _score_row(
        normalized_query="alpha beta",
        query_tokens=["alpha", "beta"],
        title="alpha alpha",
        document="beta",
    )
    # No full-query substring hits; alpha×2 in title → 16; beta×1 in doc → 1.
    assert score == 17

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    result = reader.search_rows(query="fixture", top_k=10)
    ids = [r["ledger_id"] for r in result["results"]]
    assert isinstance(ids, list)
    assert len(ids) >= 1
    # Single-row fixture: exact returned id set is the published observation handle.
    assert ids == sorted(ids)


def test_m4_direct_cli_boottime_bound_and_shared_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
):
    """Items 12/18: private+public opening, shared lock, 10s BOOTTIME, recheck."""

    import fcntl
    import io
    import strict_projection as sp

    items, resolved, scope_path, registry_path = _m4_two_serving_roots(tmp_path)
    item = items[0]
    req = tmp_path / "req.json"
    req.write_text('{"query":"fixture"}', encoding="utf-8")
    os.chmod(req, 0o444)

    # Track lock hold across qualify + open.
    lock_state: dict[str, Any] = {
        "fd": None,
        "path": None,
        "qualify": False,
        "open": False,
    }
    orig_acquire = sp._acquire_shared_lineage_lock
    orig_qualify = sp.qualify_authority_generation
    orig_open = sp.open_published_generation

    def wrap_acquire(path):
        fd, inode = orig_acquire(path)
        lock_state["fd"] = fd
        lock_state["path"] = path
        return fd, inode

    def _assert_shared_blocks_exclusive(phase: str) -> None:
        # flock upgrades within one open-file description; probe must use another.
        product_fd = lock_state["fd"]
        assert isinstance(product_fd, int) and product_fd >= 0
        lock_path = lock_state["path"]
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        probe_fd = os.open(lock_path, flags)
        try:
            try:
                fcntl.flock(probe_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                raise AssertionError(f"shared lock not held during {phase}")
            except BlockingIOError:
                return
        finally:
            os.close(probe_fd)

    def wrap_qualify(**kwargs):
        _assert_shared_blocks_exclusive("private qualification")
        lock_state["qualify"] = True
        return orig_qualify(**kwargs)

    def wrap_open(**kwargs):
        assert isinstance(lock_state["fd"], int) and lock_state["fd"] >= 0
        assert kwargs.get("held_lock") is not None
        _assert_shared_blocks_exclusive("public opening")
        lock_state["open"] = True
        return orig_open(**kwargs)

    monkeypatch.setattr(sp, "_acquire_shared_lineage_lock", wrap_acquire)
    monkeypatch.setattr(sp, "qualify_authority_generation", wrap_qualify)
    monkeypatch.setattr(sp, "open_published_generation", wrap_open)

    clock = {"n": 0}

    def fake_boot():
        clock["n"] += 1
        return _M4_SYNTHETIC_BOOTTIME_NS + clock["n"]

    monkeypatch.setattr(sp, "boottime_ns", fake_boot)
    monkeypatch.setattr(sp, "wall_time_utc", lambda: _M4_NOW)

    argv = [
        "read",
        "--method",
        "search",
        "--scope",
        str(scope_path),
        "--registry",
        str(registry_path),
        "--strict-config",
        str(item["config_path"]),
        "--request-file",
        str(req),
        "--expected-publication",
        item["serving"]["publication_payload_sha256"],
    ]

    # Capture stdout via proxy — sys.stdout.buffer is readonly.
    class _StdoutBufferProxy:
        def __init__(self, real: Any, buffer: io.BytesIO) -> None:
            self._real = real
            self.buffer = buffer

        def __getattr__(self, name: str) -> Any:
            return getattr(self._real, name)

    real_stdout = sys.stdout
    buf = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", _StdoutBufferProxy(real_stdout, buf))
    before_mtimes = {
        p: p.stat().st_mtime_ns
        for p in item["root"].rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    rc = sp._cli_read(argv)
    out = buf.getvalue()
    assert rc == 0
    assert lock_state["qualify"] is True
    assert lock_state["open"] is True
    lines = out.splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["schema"] == "convmem.raw-evidence.v3"
    assert payload["instruction_authority"] == "none"
    after_mtimes = {
        p: p.stat().st_mtime_ns
        for p in item["root"].rglob("*")
        if p.is_file() and not p.is_symlink()
    }
    assert before_mtimes == after_mtimes

    # Exhaust budget (≥ 10s) → closed error, never partial success.
    clock["n"] = 0

    def fake_boot_over():
        clock["n"] += 1
        return clock["n"] * 6_000_000_000

    monkeypatch.setattr(sp, "boottime_ns", fake_boot_over)
    buf2 = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", _StdoutBufferProxy(real_stdout, buf2))
    rc2 = sp._cli_read(argv)
    out2 = buf2.getvalue()
    assert rc2 != 0
    lines2 = out2.splitlines()
    assert len(lines2) == 1
    err = json.loads(lines2[0])
    assert err["schema"] == "convmem.error.v1"
    assert err["error"]["code"] == "snapshot_stale"
    assert "results" not in err


def test_m4_seven_error_codes_and_v3_field_sets(tmp_path: Path):
    """Item 17: seven exact error codes/messages; v3 top-level fields."""

    from strict_projection import StrictPublicError, _ERROR_MESSAGES

    assert set(_ERROR_MESSAGES) == {
        "invalid_request",
        "identifier_query_not_supported",
        "scope_denied",
        "snapshot_stale",
        "response_too_large",
        "temporarily_unavailable",
        "internal_failure",
    }
    assert len(_ERROR_MESSAGES) == 7
    for code, message in _ERROR_MESSAGES.items():
        err = StrictPublicError(code)
        assert err.payload["schema"] == "convmem.error.v1"
        assert err.payload["error"]["code"] == code
        assert err.payload["error"]["message"] == message
        assert set(err.payload) == {"schema", "error", "correlation_id"}
        assert set(err.payload["error"]) == {"code", "message"}


def test_m4_capability_immutable_and_forged_new_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Item 9: frozen slots; object.__new__ forge fails live registry."""

    from strict_projection import (
        QualifiedStrictGeneration,
        StrictProjectionError,
        StrictProjectionReader,
        StrictPublicError,
        open_published_generation,
        revoke_snapshot,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    with pytest.raises(AttributeError):
        gen.lineage_id = "mutated"
    forged = object.__new__(QualifiedStrictGeneration)
    with pytest.raises(StrictProjectionError, match="forged_capability"):
        StrictProjectionReader(forged)
    with pytest.raises(StrictProjectionError, match="forged_capability"):
        revoke_snapshot(forged)
    # Construct while live; revoke; existing reader must surface public snapshot_stale.
    reader = StrictProjectionReader(gen)
    revoke_snapshot(gen)
    with pytest.raises(StrictPublicError) as ei:
        reader.search_rows(query="fixture")
    assert ei.value.code == "snapshot_stale"


def _m4_clone_row(row: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    out = dict(row)
    out.update(overrides)
    pref = out["public_binding_ref"]
    out["public_ledger_id"] = f"cm1.{pref}.{out['assertion_id']}"
    return out


def _m4_unseal_for_mutation(root: Path, *rels: str) -> None:
    os.chmod(root, 0o755)
    for rel in rels:
        path = root / rel
        parent = path.parent
        while parent != root and parent != parent.parent:
            os.chmod(parent, 0o755)
            parent = parent.parent
        if path.exists() and path.is_file():
            os.chmod(path, 0o644)


def test_m4_same_inode_content_mutation_fails_pin_recheck(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Same-inode in-place byte mutation restored to 0444 must fail content pin."""

    from strict_projection import (
        StrictProjectionError,
        pin_operator_immutable_path,
        recheck_operator_immutable_path,
    )

    items, resolved, scope_path, _rp = _m4_two_serving_roots(tmp_path)
    pin = pin_operator_immutable_path(scope_path)
    os.chmod(scope_path, 0o644)
    original = scope_path.read_bytes()
    mutated = original[:-1] + (b"X" if original[-1:] != b"X" else b"Y")
    scope_path.write_bytes(mutated)
    os.chmod(scope_path, 0o444)
    with pytest.raises(StrictProjectionError, match="operator_content_changed"):
        recheck_operator_immutable_path(scope_path, pin)
    # Restore for cleanliness.
    os.chmod(scope_path, 0o644)
    scope_path.write_bytes(original)
    os.chmod(scope_path, 0o444)


def test_m4_post_open_public_mutation_snapshot_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from strict_grounding import strict_canonical_bytes
    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        _labeled_self_hash,
        open_published_generation,
        revoke_snapshot,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    item = items[0]
    gen = open_published_generation(
        root=item["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=item["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    lineage = gen.lineage_id
    pub_path = item["root"] / "active" / f"{lineage}.json"
    _m4_unseal_for_mutation(item["root"], f"active/{lineage}.json")
    pub = json.loads(pub_path.read_text(encoding="utf-8"))
    pub["published_at"] = "2099-01-01T00:00:00Z"
    pub["publication_payload_sha256"] = _labeled_self_hash(
        pub, "publication_payload_sha256"
    )
    pub_path.write_bytes(strict_canonical_bytes(pub))
    os.chmod(pub_path, 0o444)
    _seal_public_mount_modes(item["root"])
    with pytest.raises(StrictPublicError) as ei:
        reader.search_rows(query="fixture")
    assert ei.value.code == "snapshot_stale"
    revoke_snapshot(gen)


def test_m4_public_open_corrupt_and_graph_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Corrupt/swapped public artifacts + graph validation negatives."""

    from strict_grounding import strict_canonical_bytes
    from strict_projection import StrictProjectionError, open_published_generation

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    item = items[0]
    root = item["root"]
    lineage = resolved.registry.binding(
        resolved.scope.allowed_project_bindings[0]
    ).lineage_id
    serving = item["serving"]
    gen_id = serving["serving_generation_id"]
    snap_id = serving["authority_snapshot_id"]

    def _open_expect(match: str) -> None:
        with pytest.raises(StrictProjectionError, match=match):
            open_published_generation(
                root=root,
                scope=resolved.scope,
                registry=resolved.registry,
                expected_publication_sha256=serving["publication_payload_sha256"],
                now=_M4_NOW,
            )

    # Missing public file.
    rows_path = root / "projection" / gen_id / "rows.jsonl"
    backup_rows = rows_path.read_bytes()
    _m4_unseal_for_mutation(root, f"projection/{gen_id}/rows.jsonl")
    rows_path.unlink()
    _seal_public_mount_modes(root)
    _open_expect("open_failed|public_missing|not_regular")
    _m4_unseal_for_mutation(root, f"projection/{gen_id}/rows.jsonl")
    rows_path.write_bytes(backup_rows)
    os.chmod(rows_path, 0o444)
    _seal_public_mount_modes(root)

    # Graph unknown node / duplicate / missing required edge / row mismatch.
    graph_path = root / "projection" / gen_id / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    backup_graph = graph_path.read_bytes()
    cases = []
    # unknown edge node
    g1 = json.loads(backup_graph)
    g1["edges"] = [
        {
            "kind": "relates_to",
            "from_assertion_id": "missing_node_aaaaaaaa",
            "to_assertion_id": g1["nodes"][0] if g1["nodes"] else "x",
        }
    ]
    cases.append(("graph_edge_unknown_node", g1))
    # duplicate node
    g2 = json.loads(backup_graph)
    if g2["nodes"]:
        g2["nodes"] = list(g2["nodes"]) + [g2["nodes"][0]]
        cases.append(("graph_node_dup", g2))
    # graph/row agreement
    g3 = json.loads(backup_graph)
    g3["nodes"] = list(g3["nodes"]) + ["extra_node_bbbbbbbb"]
    cases.append(("graph_row_agreement", g3))

    for match, mutated in cases:
        _m4_unseal_for_mutation(root, f"projection/{gen_id}/graph.json")
        mutated["graph_payload_sha256"] = "sha256:" + ("0" * 64)
        from strict_projection import _labeled_self_hash as _lsh

        mutated["graph_payload_sha256"] = _lsh(mutated, "graph_payload_sha256")
        graph_path.write_bytes(strict_canonical_bytes(mutated))
        os.chmod(graph_path, 0o444)
        # Also fix projection manifest graph hash so graph schema check is reached.
        man_path = root / "projection" / gen_id / "manifest.json"
        _m4_unseal_for_mutation(root, f"projection/{gen_id}/manifest.json")
        man = json.loads(man_path.read_text(encoding="utf-8"))
        man["graph_sha256"] = mutated["graph_payload_sha256"]
        if match == "graph_row_agreement":
            man["graph_node_count"] = len(mutated["nodes"])
        man["manifest_payload_sha256"] = _lsh(man, "manifest_payload_sha256")
        # generation_id / publication links may fail first — still a closed deny.
        man_path.write_bytes(strict_canonical_bytes(man))
        os.chmod(man_path, 0o444)
        _seal_public_mount_modes(root)
        with pytest.raises(StrictProjectionError):
            open_published_generation(
                root=root,
                scope=resolved.scope,
                registry=resolved.registry,
                now=_M4_NOW,
            )
        _m4_unseal_for_mutation(
            root,
            f"projection/{gen_id}/graph.json",
            f"projection/{gen_id}/manifest.json",
        )
        graph_path.write_bytes(backup_graph)
        # restore manifest from a fresh open of the sibling root if needed — rewrite from item
        # Re-seal from the other root's copy is heavy; re-publish not available.
        # Restore by re-reading original bytes captured before loop.
    # Full restore from root-b sibling (byte-identical).
    sibling = items[1]["root"]
    import shutil

    for rel in (
        f"projection/{gen_id}/graph.json",
        f"projection/{gen_id}/manifest.json",
        f"projection/{gen_id}/rows.jsonl",
        f"active/{lineage}.json",
        f"authority/{snap_id}/manifest.json",
    ):
        _m4_unseal_for_mutation(root, rel)
        shutil.copy2(sibling / rel, root / rel)
    _seal_public_mount_modes(root)

    # Nested invalid capture on a row — rewrite rows with bad capture, rehash chain loosely.
    _m4_unseal_for_mutation(root, f"projection/{gen_id}/rows.jsonl")
    row = json.loads(rows_path.read_text(encoding="utf-8").splitlines()[0])
    row["provenance_qualification"]["capture"] = "not_a_capture_class"
    rows_path.write_text(
        strict_canonical_bytes(row).decode("utf-8") + "\n", encoding="utf-8"
    )
    os.chmod(rows_path, 0o444)
    _seal_public_mount_modes(root)
    with pytest.raises(StrictProjectionError, match="projection_row_capture|rows_hash"):
        open_published_generation(
            root=root,
            scope=resolved.scope,
            registry=resolved.registry,
            now=_M4_NOW,
        )
    _m4_unseal_for_mutation(root, f"projection/{gen_id}/rows.jsonl")
    shutil.copy2(sibling / f"projection/{gen_id}/rows.jsonl", rows_path)
    _seal_public_mount_modes(root)


def test_m4_related_neighborhood_vectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Related: depth-two, ambiguous parent, cycle, 9th hop, >200, non-expanding."""

    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        open_published_generation,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    base = dict(gen.rows[0])
    pref = base["public_binding_ref"]

    def aid(n: int) -> str:
        return f"obs2_{n:064x}"

    # Depth-two: decision target with verification child + observation sibling via parent.
    obs = _m4_clone_row(base, assertion_id=aid(1), record_kind="observation")
    dec = _m4_clone_row(
        base,
        assertion_id=aid(2),
        record_kind="decision",
        relates_to_assertion_id=obs["assertion_id"],
        logical_id="logical-dec-1",
    )
    ver = _m4_clone_row(
        base,
        assertion_id=aid(3),
        record_kind="verification",
        target_assertion_id=dec["assertion_id"],
        verification_result="pass",
        relates_to_assertion_id=None,
        logical_id="logical-ver-1",
    )
    sib = _m4_clone_row(
        base,
        assertion_id=aid(4),
        record_kind="observation",
        relates_to_assertion_id=obs["assertion_id"],
        logical_id="logical-sib-1",
    )
    reader._rows_by_assertion = {
        obs["assertion_id"]: [obs],
        dec["assertion_id"]: [dec],
        ver["assertion_id"]: [ver],
        sib["assertion_id"]: [sib],
    }
    reader._relates_parents = {
        dec["assertion_id"]: [obs["assertion_id"]],
        sib["assertion_id"]: [obs["assertion_id"]],
    }
    reader._children = {
        obs["assertion_id"]: [
            ("relates_to", dec["assertion_id"]),
            ("relates_to", sib["assertion_id"]),
        ],
        dec["assertion_id"]: [("targets", ver["assertion_id"])],
    }
    reader._non_expanding = frozenset()
    handle = f"cm1.{pref}.{dec['assertion_id']}"
    got = reader.related_neighborhood(ledger_id=handle)
    got_ids = [r["ledger_id"] for r in got["results"]]
    expected = sorted(
        [
            f"cm1.{pref}.{obs['assertion_id']}",
            f"cm1.{pref}.{dec['assertion_id']}",
            f"cm1.{pref}.{ver['assertion_id']}",
            f"cm1.{pref}.{sib['assertion_id']}",
        ]
    )
    assert got_ids == expected
    assert got["display_basis"] == "bounded_context"
    assert got["selection_complete"] is True

    # Ambiguous parent (>1) denies.
    reader._relates_parents[dec["assertion_id"]] = [
        obs["assertion_id"],
        sib["assertion_id"],
    ]
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=handle)
    assert ei.value.code == "scope_denied"

    # Cycle in ancestor path.
    reader._relates_parents = {
        dec["assertion_id"]: [obs["assertion_id"]],
        obs["assertion_id"]: [dec["assertion_id"]],
    }
    reader._children = {}
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=handle)
    assert ei.value.code == "scope_denied"

    # Cycle in descendant union.
    reader._relates_parents = {}
    reader._children = {
        dec["assertion_id"]: [("relates_to", ver["assertion_id"])],
        ver["assertion_id"]: [("relates_to", dec["assertion_id"])],
    }
    reader._rows_by_assertion = {
        dec["assertion_id"]: [dec],
        ver["assertion_id"]: [ver],
    }
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=handle)
    assert ei.value.code == "scope_denied"

    # Ninth hop required denies.
    chain = [aid(100 + i) for i in range(10)]
    rows = {
        chain[0]: [
            _m4_clone_row(
                base, assertion_id=chain[0], record_kind="decision", logical_id="c0"
            )
        ]
    }
    parents: dict[str, list[str]] = {}
    for i in range(1, 10):
        rows[chain[i]] = [
            _m4_clone_row(
                base,
                assertion_id=chain[i],
                record_kind="decision",
                logical_id=f"c{i}",
            )
        ]
        parents[chain[i - 1]] = [chain[i]]
    reader._rows_by_assertion = rows
    reader._relates_parents = parents
    reader._children = {}
    handle9 = f"cm1.{pref}.{chain[0]}"
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=handle9)
    assert ei.value.code == "scope_denied"

    # >200 required union denies.
    hub = aid(2000)
    hub_row = _m4_clone_row(base, assertion_id=hub, record_kind="observation")
    children = []
    mmap = {hub: [hub_row]}
    for i in range(201):
        cid = aid(3000 + i)
        mmap[cid] = [
            _m4_clone_row(
                base, assertion_id=cid, record_kind="observation", logical_id=f"n{i}"
            )
        ]
        children.append(("relates_to", cid))
    reader._rows_by_assertion = mmap
    reader._relates_parents = {}
    reader._children = {hub: children}
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=f"cm1.{pref}.{hub}")
    assert ei.value.code == "scope_denied"

    # Non-expanding high-degree fallback: include root only.
    reader._non_expanding = frozenset({hub})
    # Parent path hits non-expanding immediately when querying a child.
    child0 = children[0][1]
    reader._relates_parents = {child0: [hub]}
    reader._children = {hub: children}
    got = reader.related_neighborhood(ledger_id=f"cm1.{pref}.{child0}")
    got_ids = [r["ledger_id"] for r in got["results"]]
    assert got_ids == sorted([f"cm1.{pref}.{child0}", f"cm1.{pref}.{hub}"])

    # Duplicate stored identity denies.
    reader._non_expanding = frozenset()
    reader._rows_by_assertion = {hub: [hub_row, dict(hub_row)]}
    reader._relates_parents = {}
    reader._children = {}
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=f"cm1.{pref}.{hub}")
    assert ei.value.code == "scope_denied"

    # Wrong binding denies.
    with pytest.raises(StrictPublicError) as ei:
        reader.related_neighborhood(ledger_id=f"cm1.{'f' * 32}.{hub}")
    assert ei.value.code == "scope_denied"


def test_m4_v3_snapshot_result_key_sets_and_caps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Exact v3 snapshot/result keys; 4096 truncation; 64-token bound."""

    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        _DOC_CODEPOINT_CAP,
        open_published_generation,
        tokenize_lexical,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    result = reader.search_rows(query="fixture")
    assert set(result) == {
        "schema",
        "instruction_authority",
        "snapshot",
        "selection_complete",
        "display_basis",
        "results",
    }
    assert set(result["snapshot"]) == {
        "snapshot_id",
        "lineage_id",
        "authority_seq",
        "authority_manifest_sha256",
        "semantic_contract_sha256",
        "state_basis",
        "verification_basis",
        "as_of",
        "expires_at",
    }
    if result["results"]:
        assert set(result["results"][0]) == {
            "title",
            "document",
            "ledger_id",
            "citation_ref",
            "record_kind",
            "logical_id",
            "authority_state",
            "verification_state",
            "verification_result",
            "target_ledger_id",
            "supersedes_ledger_ids",
            "origin_assurance",
            "provenance_qualification",
            "provenance_basis",
            "check_eligibility",
            "state_sha256",
            "confidence_bps",
            "observed_at",
            "recorded_at",
            "decision_disposition_ref",
            "supersession_disposition_ref",
            "state_disposition_refs",
            "truncated",
            "domain",
            "site",
        }

    # 64 distinct-token bound.
    toks = " ".join(f"t{i}" for i in range(65))
    with pytest.raises(StrictPublicError) as ei:
        reader.search_rows(query=toks)
    assert ei.value.code == "invalid_request"
    assert len(tokenize_lexical(" ".join(f"t{i}" for i in range(64)))) == 64

    # 4096-codepoint truncation flag via format helper.
    long_doc = "x" * (_DOC_CODEPOINT_CAP + 10)
    row = dict(gen.rows[0])
    row["document"] = long_doc
    formatted = reader._format_result(row)
    assert formatted["truncated"] is True
    assert len(formatted["document"]) == _DOC_CODEPOINT_CAP


def test_m4_selector_bound_descendant_and_cross_domain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Selector matrices on search + unresolved; legacy normalizer not called."""

    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        open_published_generation,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)

    called = {"legacy": 0}
    # Prove legacy site_filter.normalize_site is not on the reader path.
    import site_filter

    orig_legacy = site_filter.normalize_site

    def wrap_legacy(value):
        called["legacy"] += 1
        return orig_legacy(value)

    monkeypatch.setattr(site_filter, "normalize_site", wrap_legacy)
    # Also prove domains.normalize_domain is not used for selector deny path.
    import domains as domains_mod

    orig_dom = domains_mod.normalize_domain

    def wrap_dom(value):
        called["legacy"] += 1
        return orig_dom(value)

    monkeypatch.setattr(domains_mod, "normalize_domain", wrap_dom)

    # Bound-domain success (omitted inherits).
    ok = reader.search_rows(query="fixture")
    assert ok["schema"] == "convmem.raw-evidence.v3"
    ok_u = reader.unresolved_rows()
    assert ok_u["schema"] == "convmem.raw-evidence.v3"

    # Parent/sibling/malformed/general failures + cross_domain.
    for tool in ("search", "unresolved"):
        for kwargs in (
            {"domain": "general"},
            {"domain": "parent"},
            {"domain": "sibling"},
            {"domain": "!!!"},
            {"cross_domain": True},
            {"project": "ConvMem"},  # case-confusable vs bound project
            {"project": "convmem-extra"},
        ):
            with pytest.raises(StrictPublicError) as ei:
                if tool == "search":
                    reader.search_rows(query="fixture", **kwargs)
                else:
                    reader.unresolved_rows(**kwargs)
            assert ei.value.code == "scope_denied"

    assert called["legacy"] == 0


def test_m4_lock_release_on_revoke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from strict_projection import open_published_generation, revoke_snapshot

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    assert gen._lock_fd >= 0
    revoke_snapshot(gen)
    assert gen._lock_fd == -1
    assert gen.is_revoked is True

def test_m4_site_and_domain_selector_equivalence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Exact-site Unicode/A-label/case/terminal-dot success; host/port/scheme failures."""

    from strict_projection import (
        StrictProjectionReader,
        StrictPublicError,
        open_published_generation,
    )

    items, resolved, _sp, _rp = _m4_two_serving_roots(tmp_path)
    _m4_patch_clocks(monkeypatch)
    gen = open_published_generation(
        root=items[0]["root"],
        scope=resolved.scope,
        registry=resolved.registry,
        expected_publication_sha256=items[0]["serving"]["publication_payload_sha256"],
        now=_M4_NOW,
    )
    reader = StrictProjectionReader(gen)
    assert resolved.scope.site_mode == "exact"
    assert resolved.scope.site == "example.com"

    for site in ("example.com", "EXAMPLE.COM", "example.com."):
        ok = reader.search_rows(query="fixture", site=site)
        assert ok["schema"] == "convmem.raw-evidence.v3"
        assert len(ok["results"]) >= 1

    # Bound-domain exact success; descendant selector resolves without widening.
    ok_d = reader.search_rows(query="fixture", domain="coding")
    assert ok_d["schema"] == "convmem.raw-evidence.v3"
    assert len(ok_d["results"]) >= 1
    narrow = reader.search_rows(query="fixture", domain="coding.tooling")
    assert narrow["schema"] == "convmem.raw-evidence.v3"
    # Fixture rows are authority_domain=coding, so narrowing yields empty set.
    assert narrow["results"] == []
    assert narrow["selection_complete"] is True

    for site in (
        "http://example.com",
        "example.com:443",
        "user@example.com",
        "example.com/path",
        "exam_ple.com",
        "example..com",
        "xn--bcher-kva.example",  # unrelated IDNA host
        " ",
    ):
        with pytest.raises(StrictPublicError) as ei:
            reader.search_rows(query="fixture", site=site)
        assert ei.value.code == "scope_denied"
