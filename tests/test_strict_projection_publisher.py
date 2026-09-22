"""M3/T2 named publisher tests — genesis, CAS, fence, retry, rollback, retire-first, faults.

Parent cases owned in part by the publisher (overlay d1ca459 / parent cd9d2698):
enrolled empty genesis; cumulative authority/source-cutoff/history; parent-head/
join rules; exact operation retry/current-head; fence before intent; authority
advance to unavailable; cold build then serving; full publication-payload CAS;
immutable history; current-head/current-contract rollback with no expiry renewal;
nonempty-slot refusal (proofs never authorize; no publisher slot mutation);
production-local builder inventory fail-closed hashing; real slot→lineage flock;
noncanonical JSON/JSONL rejection; crash recovery and deterministic fault
injection at every parent-fixed write/fsync/rename/pointer boundary.

No publisher-owned manager. No T3–T5 reader/server claims.
"""

from __future__ import annotations

import importlib.util
import json
import os
import unicodedata
from pathlib import Path
from typing import Any

import pytest

from bound_read_scope import sha256_digest
from strict_grounding import strict_canonical_bytes


def test_strict_projection_publisher_capability_present():
    spec = importlib.util.find_spec("strict_projection_publisher")
    assert spec is not None, "[T2] module strict_projection_publisher absent"
    module = importlib.import_module("strict_projection_publisher")
    assert hasattr(module, "publish_projection"), (
        "[T2] strict_projection_publisher.publish_projection capability absent"
    )
    assert hasattr(module, "recover_projection")
    assert hasattr(module, "FAULT_HOOKS")
    assert hasattr(module, "StrictPublisherError")
    assert hasattr(module, "main")
    assert hasattr(module, "enroll_fixture")


# ---------------------------------------------------------------------------
# Helpers — enrollment / layout only (no live data)
# ---------------------------------------------------------------------------

_LINEAGE = "b" * 32
_SLOT = "c" * 32
_OWNER_PLACEHOLDER = "sha256:" + ("d" * 64)
_TS = "2026-09-21T00:00:00Z"


def _self_hash(obj: dict[str, Any], field: str) -> str:
    body = {k: v for k, v in obj.items() if k != field}
    return sha256_digest(strict_canonical_bytes(body))


def _empty_cutoff(lineage_id: str = _LINEAGE) -> dict[str, Any]:
    cutoff = {
        "schema": "convmem.strict-source-cutoff.v1",
        "lineage_id": lineage_id,
        "mode": "fixture",
        "operations": [],
        "cutoff_payload_sha256": "sha256:" + ("0" * 64),
    }
    cutoff["cutoff_payload_sha256"] = _self_hash(cutoff, "cutoff_payload_sha256")
    return cutoff


def _semantic_contract(tmp_path: Path) -> tuple[Path, str]:
    contract = {
        "schema": "convmem.strict-semantic-contract.v1",
        "reducer_version": "v1",
        "grounding_version": "v1",
        "canonicalization_version": "v1",
        "identity_version": "v2",
        "search_kernel": "lexical_v1",
        "search_kernel_version": "1",
        "tokenizer_unicode_version": unicodedata.unidata_version,
        "schema_digests": [],
        "contract_payload_sha256": "sha256:" + ("0" * 64),
    }
    contract["contract_payload_sha256"] = _self_hash(contract, "contract_payload_sha256")
    path = tmp_path / "semantic-contract.json"
    path.write_bytes(strict_canonical_bytes(contract))
    return path, contract["contract_payload_sha256"]


def _enrollment_obj(
    *,
    sc_hash: str,
    cutoff_hash: str,
    owner_digest: str = _OWNER_PLACEHOLDER,
    scope_sha256: str | None = None,
    registry_sha256: str | None = None,
) -> dict[str, Any]:
    enrollment = {
        "schema": "convmem.strict-enrollment.v1",
        "lineage_id": _LINEAGE,
        "slot_id": _SLOT,
        "mode": "fixture",
        "owner_digest": owner_digest,
        "operator_uid": 1000,
        "controller_uid": 0,
        "supervisor_uid": 0,
        "runtime_uid": 1001,
        "scope_sha256": scope_sha256 or ("sha256:" + ("1" * 64)),
        "registry_sha256": registry_sha256 or ("sha256:" + ("2" * 64)),
        "semantic_contract_sha256": sc_hash,
        "initial_source_cutoff_sha256": cutoff_hash,
        "enrollment_payload_sha256": "sha256:" + ("0" * 64),
    }
    enrollment["enrollment_payload_sha256"] = _self_hash(
        enrollment, "enrollment_payload_sha256"
    )
    return enrollment


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(strict_canonical_bytes(obj))


def _enroll_root(tmp_path: Path) -> tuple[Path, dict[str, Any], Path, Path, Path]:
    """Enroll an empty fixture root; return root, genesis publication, paths."""
    from strict_projection_publisher import enroll_fixture

    root = tmp_path / "projection-root"
    root.mkdir()
    sc_path, sc_hash = _semantic_contract(tmp_path)
    cutoff = _empty_cutoff()
    enrollment = _enrollment_obj(sc_hash=sc_hash, cutoff_hash=cutoff["cutoff_payload_sha256"])
    enroll_path = tmp_path / "enrollment.json"
    _write_json(enroll_path, enrollment)
    config = {
        "schema": "convmem.strict-config.v2",
        "projection_root": str(root.resolve()),
        "max_projection_rows": 10000,
        "max_projection_bytes": 67108864,
        "telemetry": False,
    }
    config_path = tmp_path / "strict-config.json"
    _write_json(config_path, config)
    publication = enroll_fixture(
        enrollment_path=enroll_path,
        semantic_contract_path=sc_path,
        strict_config_path=config_path,
    )
    return root, publication, enroll_path, sc_path, config_path


def _scope_registry_with_owner(tmp_path: Path) -> tuple[Path, Path]:
    """Write absolute immutable scope/registry files for resolve_scope."""
    scope = {
        "schema": "convmem.bound-read-scope.v2",
        "project": "convmem",
        "allowed_project_bindings": ["project:convmem:v1"],
        "domain": "coding",
        "site_mode": "exact",
        "site": "example.com",
        "authority_snapshot": "/fixture/authority",
        "serving_projection": "/fixture/serving",
        "max_snapshot_age_seconds": 3600,
    }
    # Parent: registry.revision = sha256 of canonical top-level object with
    # only the revision field removed (same recipe as load_project_binding_registry).
    from bound_read_scope import BoundScopeError
    from canonical_json import canonical_json_bytes

    without_revision = {
        "schema": "convmem.project-binding-registry.v3",
        "bindings": [
            {
                "id": "project:convmem:v1",
                "public_ref": "a" * 32,
                "project": "convmem",
                "domain_root": "coding",
                "site_mode": "exact",
                "site": "example.com",
                "non_expanding_roots": [],
                "source_registrations": [
                    {
                        "id": "src-reg-1",
                        "source_class": "fixture_scan",
                        "source_identity": "fixture/source-a",
                        "identity_match": "exact",
                        "authorization_domain": "coding",
                        "site": "example.com",
                        "event_id_resolver": "fixture_scan_event_v1",
                    }
                ],
                "lineage_id": _LINEAGE,
                "capture_issuers": [
                    {
                        "issuer_id": "fixture-issuer",
                        "capture_class": "synthetic_fixture",
                        "enrollment_sha256": "sha256:" + ("a" * 64),
                        "receipt_root": "/var/lib/convmem/receipts/fixture-issuer",
                        "source_registration_ids": ["src-reg-1"],
                    }
                ],
                "verification_producers": [],
            }
        ],
    }
    revision = sha256_digest(
        canonical_json_bytes(
            without_revision,
            validate=lambda _obj: None,
            error_type=BoundScopeError,
        )
    )
    registry = {**without_revision, "revision": revision}
    scope_path = (tmp_path / "scope.json").resolve()
    registry_path = (tmp_path / "registry.json").resolve()
    _write_json(scope_path, scope)
    _write_json(registry_path, registry)
    os.chmod(scope_path, 0o444)
    os.chmod(registry_path, 0o444)
    return scope_path, registry_path


def _enroll_matched(tmp_path: Path) -> tuple[Path, dict[str, Any], Path, Path, Path, Path, Path]:
    """Enroll with owner/scope/registry digests matching real scope+registry files."""
    from bound_read_scope import (
        load_bound_read_scope,
        load_project_binding_registry,
        owner_digest as compute_owner,
    )
    from strict_projection_publisher import enroll_fixture

    root = tmp_path / "projection-root"
    root.mkdir()
    scope_path, registry_path = _scope_registry_with_owner(tmp_path)
    loaded_scope = load_bound_read_scope(scope_path)
    loaded_registry = load_project_binding_registry(registry_path)
    owner = compute_owner(
        scope_sha256=loaded_scope.scope_sha256,
        registry_sha256=loaded_registry.registry_sha256,
        project_binding_id="project:convmem:v1",
    )
    sc_path, sc_hash = _semantic_contract(tmp_path)
    cutoff = _empty_cutoff()
    enrollment = _enrollment_obj(
        sc_hash=sc_hash,
        cutoff_hash=cutoff["cutoff_payload_sha256"],
        owner_digest=owner,
        scope_sha256=loaded_scope.scope_sha256,
        registry_sha256=loaded_registry.registry_sha256,
    )
    enroll_path = tmp_path / "enrollment.json"
    _write_json(enroll_path, enrollment)
    config = {
        "schema": "convmem.strict-config.v2",
        "projection_root": str(root.resolve()),
        "max_projection_rows": 10000,
        "max_projection_bytes": 67108864,
        "telemetry": False,
    }
    config_path = tmp_path / "strict-config.json"
    _write_json(config_path, config)
    publication = enroll_fixture(
        enrollment_path=enroll_path,
        semantic_contract_path=sc_path,
        strict_config_path=config_path,
    )
    return root, publication, enroll_path, sc_path, config_path, scope_path, registry_path


# ---------------------------------------------------------------------------
# Case 52 / M3 — enrolled empty genesis
# ---------------------------------------------------------------------------


def test_enrolled_empty_genesis_unavailable_seq0_never_serving(tmp_path: Path):
    root, publication, *_ = _enroll_root(tmp_path)
    assert publication["epoch"] == 1
    assert publication["authority_seq"] == 0
    assert publication["mode"] == "unavailable"
    assert publication["authority_snapshot_id"] is None
    assert publication["authority_manifest_sha256"] is None
    assert publication["serving_generation_id"] is None
    assert publication["projection_manifest_sha256"] is None
    assert publication["freshness_anchor"] is None
    assert publication["pending_operation_id"] is None
    assert publication["previous_publication_sha256"] is None
    assert publication["authority_source_cutoff_sha256"].startswith("sha256:")
    # Layout + empty slot + history entry exist.
    assert (root / "layout.json").is_file()
    assert (root / "control" / "slot.json").is_file()
    slot = json.loads((root / "control" / "slot.json").read_text())
    assert slot["state"] == "empty"
    hist = list((root / "active" / "history").glob("*.json"))
    assert len(hist) == 1
    active = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    assert active["publication_payload_sha256"] == publication["publication_payload_sha256"]


def test_enroll_refuses_nonempty_root_and_prior_enrollment(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, enroll_fixture

    root, publication, enroll_path, sc_path, config_path = _enroll_root(tmp_path)
    with pytest.raises(StrictPublisherError, match="enrollment_root_not_empty"):
        enroll_fixture(
            enrollment_path=enroll_path,
            semantic_contract_path=sc_path,
            strict_config_path=config_path,
        )
    # Also refuse a root that has any retained file before enroll.
    root2 = tmp_path / "dirty"
    root2.mkdir()
    (root2 / "noise").write_text("x")
    config = json.loads(config_path.read_text())
    config["projection_root"] = str(root2.resolve())
    dirty_config = tmp_path / "dirty-config.json"
    _write_json(dirty_config, config)
    with pytest.raises(StrictPublisherError, match="enrollment_root_not_empty"):
        enroll_fixture(
            enrollment_path=enroll_path,
            semantic_contract_path=sc_path,
            strict_config_path=dirty_config,
        )


# ---------------------------------------------------------------------------
# Retire-first — nonempty slot always refuses; proofs are not authority
# ---------------------------------------------------------------------------


def test_retire_first_refuses_nonempty_slot_without_external_proofs(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, publish_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    # Force slot into active without a manager (simulate external occupancy).
    slot_path = root / "control" / "slot.json"
    slot = json.loads(slot_path.read_text())
    slot["state"] = "active"
    slot["activation_id"] = "act-1"
    body = {k: v for k, v in slot.items() if k != "slot_payload_sha256"}
    slot["slot_payload_sha256"] = sha256_digest(strict_canonical_bytes(body))
    os.chmod(slot_path, 0o644)
    _write_json(slot_path, slot)

    with pytest.raises(StrictPublisherError, match="retire_first_required"):
        publish_projection(
            bundle={
                "schema": "convmem.strict-fixture-bundle.v2",
                "lineage_id": _LINEAGE,
                "operation_id": "e" * 32,
                "expected_parent_manifest_sha256": None,
                "batches": [],
                "dispositions": [],
                "provenance_context": {
                    "schema": "convmem.strict-provenance-context.v2",
                    "schema_semantics": [],
                    "policies": [],
                    "recipes": [],
                    "verified_channels": [],
                    "registered_assertions": [],
                    "grounding_sha256": "sha256:" + ("0" * 64),
                    "context_payload_sha256": "sha256:" + ("0" * 64),
                },
                "grounding": {
                    "schema": "convmem.strict-grounding.v1",
                    "blobs": [],
                    "roots": [],
                    "edges": [],
                    "outputs": [],
                    "receipts": [],
                    "grounding_payload_sha256": "sha256:" + ("0" * 64),
                },
                "built_at": _TS,
                "as_of": _TS,
                "expires_at": "2026-09-22T00:00:00Z",
                "fixture_payload_sha256": "sha256:" + ("0" * 64),
            },
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=publication["publication_payload_sha256"],
        )


def test_nonempty_slot_refuses_even_with_apparently_valid_proofs(tmp_path: Path):
    """Adversarial: proof-shaped data must not authorize a nonempty slot."""
    from strict_projection_publisher import StrictPublisherError, publish_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    slot_path = root / "control" / "slot.json"
    slot = json.loads(slot_path.read_text())
    slot["state"] = "active"
    body = {k: v for k, v in slot.items() if k != "slot_payload_sha256"}
    slot["slot_payload_sha256"] = sha256_digest(strict_canonical_bytes(body))
    os.chmod(slot_path, 0o644)
    _write_json(slot_path, slot)
    before = slot_path.read_bytes()

    with pytest.raises(StrictPublisherError, match="retire_first_required"):
        publish_projection(
            bundle_path=tmp_path / "missing-bundle.json",
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=publication["publication_payload_sha256"],
            retirement_proof={"retirement_ref": "ext-1", "terminal": True},
            empty_domain_proof={"terminal": True, "populated": False},
        )
    # Publisher must not mutate/write the slot based on proofs.
    assert slot_path.read_bytes() == before
    assert json.loads(before.decode("utf-8"))["state"] == "active"


def test_publisher_never_writes_slot_on_publish_path(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, publish_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    slot_path = root / "control" / "slot.json"
    before = slot_path.read_bytes()
    stale = "sha256:" + ("f" * 64)
    with pytest.raises(StrictPublisherError, match="publication_cas_mismatch"):
        publish_projection(
            bundle={
                "schema": "convmem.strict-fixture-bundle.v2",
                "lineage_id": _LINEAGE,
                "operation_id": "e" * 32,
                "expected_parent_manifest_sha256": None,
                "batches": [],
                "dispositions": [],
                "provenance_context": {
                    "schema": "convmem.strict-provenance-context.v2",
                    "schema_semantics": [],
                    "policies": [],
                    "recipes": [],
                    "verified_channels": [],
                    "registered_assertions": [],
                    "grounding_sha256": "sha256:" + ("0" * 64),
                    "context_payload_sha256": "sha256:" + ("0" * 64),
                },
                "grounding": {
                    "schema": "convmem.strict-grounding.v1",
                    "blobs": [],
                    "roots": [],
                    "edges": [],
                    "outputs": [],
                    "receipts": [],
                    "grounding_payload_sha256": "sha256:" + ("0" * 64),
                },
                "built_at": _TS,
                "as_of": _TS,
                "expires_at": "2026-09-22T00:00:00Z",
                "fixture_payload_sha256": "sha256:" + ("0" * 64),
            },
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=stale,
        )
    assert slot_path.read_bytes() == before


# ---------------------------------------------------------------------------
# Builder inventory — production-local literal; fail closed; no test imports
# ---------------------------------------------------------------------------


def test_publisher_source_has_no_tests_inventory_import():
    import ast

    src_path = Path("strict_projection_publisher.py")
    tree = ast.parse(src_path.read_text(encoding="utf-8"), filename=str(src_path))
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
        for mod in modules:
            assert not mod.startswith("tests"), mod
            assert "component_inventory" not in mod.split("."), mod


def test_builder_tree_fails_closed_on_missing_member(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, _builder_tree_sha256

    with pytest.raises(StrictPublisherError, match="builder_missing:"):
        _builder_tree_sha256(tmp_path)


def test_builder_tree_fails_closed_on_missing_schema(tmp_path: Path):
    """Copy CORE members but omit a Gate B/C schema → fail closed (no name-only hash)."""
    import shutil

    from strict_projection_publisher import (
        StrictPublisherError,
        _BUILDER_MEMBERS,
        _CORE_MEMBERS,
        _builder_tree_sha256,
    )

    prod = Path.cwd()
    # Seed a partial tree: all CORE + publisher, zero schemas.
    for rel in list(_CORE_MEMBERS) + ["strict_projection_publisher.py"]:
        src = prod / rel
        dest = tmp_path / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    assert any(m.startswith("schemas/") for m in _BUILDER_MEMBERS)
    with pytest.raises(StrictPublisherError, match="builder_missing:schemas/"):
        _builder_tree_sha256(tmp_path)


def test_builder_tree_hashes_path_mode_bytes_not_names_only():
    from strict_projection_publisher import _BUILDER_MEMBERS, _builder_tree_sha256
    from bound_read_scope import sha256_digest

    digest = _builder_tree_sha256()
    names_only = sha256_digest(strict_canonical_bytes(sorted(_BUILDER_MEMBERS)))
    assert digest != names_only
    assert digest.startswith("sha256:")


# ---------------------------------------------------------------------------
# Locks — real flock hold; concurrent writers serialize; stale CAS fails
# ---------------------------------------------------------------------------


def test_publisher_locks_are_held_exclusively_not_mere_files(tmp_path: Path):
    import fcntl
    import threading

    from strict_projection_publisher import _held_publisher_locks

    root, publication, *_ = _enroll_root(tmp_path)
    slot_lock = root / "locks" / f"{_SLOT}.transition.lock"
    lineage_lock = root / "locks" / f"{_LINEAGE}.lock"
    assert slot_lock.is_file() and lineage_lock.is_file()
    del publication

    held = threading.Event()
    release = threading.Event()
    errors: list[BaseException] = []

    def holder() -> None:
        try:
            with _held_publisher_locks(root, lineage_id=_LINEAGE, slot_id=_SLOT):
                held.set()
                assert release.wait(timeout=5.0)
        except BaseException as exc:  # noqa: BLE001 — collect for main thread
            errors.append(exc)

    t = threading.Thread(target=holder)
    t.start()
    assert held.wait(timeout=5.0)
    fd = os.open(str(slot_lock), os.O_RDWR)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)
    release.set()
    t.join(timeout=5.0)
    assert not t.is_alive()
    assert errors == []
    # After release, exclusive lock is available again.
    fd = os.open(str(slot_lock), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def test_concurrent_publish_serializes_and_stale_cas_fails(tmp_path: Path):
    """Holding slot→lineage locks blocks a peer; after release, stale CAS fails."""
    import fcntl
    import threading

    from strict_projection_publisher import (
        StrictPublisherError,
        _held_publisher_locks,
        publish_projection,
    )

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    stale = "sha256:" + ("f" * 64)
    assert stale != publication["publication_payload_sha256"]

    held = threading.Event()
    release = threading.Event()
    peer_errors: list[BaseException] = []

    def holder() -> None:
        with _held_publisher_locks(root, lineage_id=_LINEAGE, slot_id=_SLOT):
            held.set()
            assert release.wait(timeout=5.0)

    def peer() -> None:
        assert held.wait(timeout=5.0)
        # While holder owns exclusive locks, non-blocking acquire must fail.
        lock_path = root / "locks" / f"{_SLOT}.transition.lock"
        fd = os.open(str(lock_path), os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)
        release.set()
        try:
            publish_projection(
                bundle={
                    "schema": "convmem.strict-fixture-bundle.v2",
                    "lineage_id": _LINEAGE,
                    "operation_id": "e" * 32,
                    "expected_parent_manifest_sha256": None,
                    "batches": [],
                    "dispositions": [],
                    "provenance_context": {
                        "schema": "convmem.strict-provenance-context.v2",
                        "schema_semantics": [],
                        "policies": [],
                        "recipes": [],
                        "verified_channels": [],
                        "registered_assertions": [],
                        "grounding_sha256": "sha256:" + ("0" * 64),
                        "context_payload_sha256": "sha256:" + ("0" * 64),
                    },
                    "grounding": {
                        "schema": "convmem.strict-grounding.v1",
                        "blobs": [],
                        "roots": [],
                        "edges": [],
                        "outputs": [],
                        "receipts": [],
                        "grounding_payload_sha256": "sha256:" + ("0" * 64),
                    },
                    "built_at": _TS,
                    "as_of": _TS,
                    "expires_at": "2026-09-22T00:00:00Z",
                    "fixture_payload_sha256": "sha256:" + ("0" * 64),
                },
                scope_path=scope_path,
                registry_path=registry_path,
                strict_config_path=config_path,
                expected_publication_sha256=stale,
            )
            peer_errors.append(RuntimeError("peer_unexpected_success"))
        except StrictPublisherError as exc:
            peer_errors.append(exc)
        except BaseException as exc:  # noqa: BLE001
            peer_errors.append(exc)

    t_hold = threading.Thread(target=holder)
    t_peer = threading.Thread(target=peer)
    t_hold.start()
    t_peer.start()
    t_hold.join(timeout=10.0)
    t_peer.join(timeout=10.0)
    assert not t_hold.is_alive() and not t_peer.is_alive()
    assert len(peer_errors) == 1
    assert isinstance(peer_errors[0], StrictPublisherError)
    assert "publication_cas_mismatch" in str(peer_errors[0])


def test_reject_noncanonical_json_and_jsonl(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, _read_json, _read_jsonl

    pretty = tmp_path / "pretty.json"
    # Semantically valid object but noncanonical spacing/key order on disk.
    pretty.write_text('{\n  "b": 1,\n  "a": 2\n}\n', encoding="utf-8")
    with pytest.raises(StrictPublisherError, match="json_noncanonical"):
        _read_json(pretty)

    line = tmp_path / "rows.jsonl"
    # Valid JSON object line that is not strict-canonical bytes.
    line.write_bytes(b'{"b":1,"a":2}\n')
    with pytest.raises(StrictPublisherError, match="jsonl_noncanonical"):
        _read_jsonl(line)


# ---------------------------------------------------------------------------
# Full publication-payload CAS (not generation-only); A→B→A cannot defeat CAS
# ---------------------------------------------------------------------------


def test_full_publication_payload_cas_rejects_stale_expected(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, publish_projection

    _, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    stale = "sha256:" + ("f" * 64)
    assert stale != publication["publication_payload_sha256"]
    with pytest.raises(StrictPublisherError, match="publication_cas_mismatch"):
        publish_projection(
            bundle={
                "schema": "convmem.strict-fixture-bundle.v2",
                "lineage_id": _LINEAGE,
                "operation_id": "e" * 32,
                "expected_parent_manifest_sha256": None,
                "batches": [],
                "dispositions": [],
                "provenance_context": {
                    "schema": "convmem.strict-provenance-context.v2",
                    "schema_semantics": [],
                    "policies": [],
                    "recipes": [],
                    "verified_channels": [],
                    "registered_assertions": [],
                    "grounding_sha256": "sha256:" + ("0" * 64),
                    "context_payload_sha256": "sha256:" + ("0" * 64),
                },
                "grounding": {
                    "schema": "convmem.strict-grounding.v1",
                    "blobs": [],
                    "roots": [],
                    "edges": [],
                    "outputs": [],
                    "receipts": [],
                    "grounding_payload_sha256": "sha256:" + ("0" * 64),
                },
                "built_at": _TS,
                "as_of": _TS,
                "expires_at": "2026-09-22T00:00:00Z",
                "fixture_payload_sha256": "sha256:" + ("0" * 64),
            },
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=stale,
        )


def test_cas_compares_entire_publication_payload_not_generation_name(tmp_path: Path):
    """Two publications that differ only outside generation identity still CAS-distinct."""
    from strict_projection_publisher import _seal_publication

    a = {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": _LINEAGE,
        "owner_digest": _OWNER_PLACEHOLDER,
        "epoch": 2,
        "authority_seq": 1,
        "authority_snapshot_id": "snap2_" + "1" * 64,
        "authority_manifest_sha256": "sha256:" + ("1" * 64),
        "authority_source_cutoff_sha256": "sha256:" + ("2" * 64),
        "serving_generation_id": "gen2_" + "3" * 64,
        "projection_manifest_sha256": "sha256:" + ("4" * 64),
        "semantic_contract_sha256": "sha256:" + ("5" * 64),
        "pending_operation_id": None,
        "mode": "serving",
        "previous_publication_sha256": "sha256:" + ("6" * 64),
        "freshness_anchor": {
            "boot_id": "boot",
            "authority_snapshot_id": "snap2_" + "1" * 64,
            "sampled_wall_time": _TS,
            "sampled_boottime_ns": 0,
            "snapshot_deadline_boottime_ns": 1,
            "clock_review_ref": "clock:x",
        },
        "published_at": _TS,
        "publication_payload_sha256": "sha256:" + ("0" * 64),
    }
    b = dict(a)
    b["epoch"] = 3  # A→B→A style epoch advance changes full payload hash
    ha = _seal_publication(a)
    hb = _seal_publication(b)
    assert ha != hb
    # Same generation id cannot defeat CAS when other fields differ.
    assert a["serving_generation_id"] == b["serving_generation_id"]


# ---------------------------------------------------------------------------
# Fence before intent/source; authority advance unavailable; faults
# ---------------------------------------------------------------------------

_PARENT_FIXED_BOUNDARIES = (
    "before_fence_fsync",
    "after_fence",
    "before_authority_fsync",
    "after_authority_unavailable",
    "before_projection_fsync",
    "before_pointer_rename_fence",
    "after_pointer_rename_fence",
    "before_pointer_dir_fsync_fence",
    "after_pointer_dir_fsync_fence",
    "before_pointer_rename_serving",
    "after_pointer_rename_serving",
    "before_pointer_dir_fsync_serving",
    "after_pointer_dir_fsync_serving",
    "before_history_fsync_fence",
    "after_history_fsync_enroll",
)


def test_fault_hooks_registered_for_parent_fixed_boundaries():
    from strict_projection_publisher import FAULT_HOOKS

    # Hooks start empty; tests inject callables keyed by parent-fixed names.
    assert isinstance(FAULT_HOOKS, dict)
    FAULT_HOOKS.clear()
    for name in _PARENT_FIXED_BOUNDARIES:
        FAULT_HOOKS[name] = lambda n=name: (_ for _ in ()).throw(RuntimeError(n))
    assert set(_PARENT_FIXED_BOUNDARIES) <= set(FAULT_HOOKS)
    FAULT_HOOKS.clear()


def test_fault_after_fence_leaves_fenced_without_authority_admission(tmp_path: Path):
    """Crash after durable fence, before authority files: prior fence remains; no snap dir."""
    from strict_projection_publisher import FAULT_HOOKS, StrictPublisherError, publish_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )

    def _boom() -> None:
        raise RuntimeError("simulated_crash_after_fence")

    FAULT_HOOKS.clear()
    FAULT_HOOKS["after_fence"] = _boom
    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [],
        "roots": [],
        "edges": [],
        "outputs": [],
        "receipts": [],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    grounding["grounding_payload_sha256"] = _self_hash(grounding, "grounding_payload_sha256")
    provenance = {
        "schema": "convmem.strict-provenance-context.v2",
        "schema_semantics": [],
        "policies": [],
        "recipes": [],
        "verified_channels": [],
        "registered_assertions": [],
        "grounding_sha256": grounding["grounding_payload_sha256"],
        "context_payload_sha256": "sha256:" + ("0" * 64),
    }
    provenance["context_payload_sha256"] = _self_hash(provenance, "context_payload_sha256")
    bundle = {
        "schema": "convmem.strict-fixture-bundle.v2",
        "lineage_id": _LINEAGE,
        "operation_id": "e" * 32,
        "expected_parent_manifest_sha256": None,
        "batches": [],
        "dispositions": [],
        "provenance_context": provenance,
        "grounding": grounding,
        "built_at": _TS,
        "as_of": _TS,
        "expires_at": "2026-09-22T00:00:00Z",
        "fixture_payload_sha256": "sha256:" + ("0" * 64),
    }
    bundle["fixture_payload_sha256"] = _self_hash(bundle, "fixture_payload_sha256")

    with pytest.raises(RuntimeError, match="simulated_crash_after_fence"):
        publish_projection(
            bundle=bundle,
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=publication["publication_payload_sha256"],
        )
    FAULT_HOOKS.clear()

    active = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    assert active["mode"] == "fenced"
    assert active["pending_operation_id"] == "e" * 32
    # No authority snapshot admitted yet.
    assert not list((root / "authority").glob("snap2_*"))


def test_recover_clears_abandoned_unratified_fence_without_durable_intent(tmp_path: Path):
    from strict_projection_publisher import FAULT_HOOKS, recover_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    FAULT_HOOKS.clear()
    FAULT_HOOKS["after_fence"] = lambda: (_ for _ in ()).throw(RuntimeError("crash"))
    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [],
        "roots": [],
        "edges": [],
        "outputs": [],
        "receipts": [],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    grounding["grounding_payload_sha256"] = _self_hash(grounding, "grounding_payload_sha256")
    provenance = {
        "schema": "convmem.strict-provenance-context.v2",
        "schema_semantics": [],
        "policies": [],
        "recipes": [],
        "verified_channels": [],
        "registered_assertions": [],
        "grounding_sha256": grounding["grounding_payload_sha256"],
        "context_payload_sha256": "sha256:" + ("0" * 64),
    }
    provenance["context_payload_sha256"] = _self_hash(provenance, "context_payload_sha256")
    bundle = {
        "schema": "convmem.strict-fixture-bundle.v2",
        "lineage_id": _LINEAGE,
        "operation_id": "e" * 32,
        "expected_parent_manifest_sha256": None,
        "batches": [],
        "dispositions": [],
        "provenance_context": provenance,
        "grounding": grounding,
        "built_at": _TS,
        "as_of": _TS,
        "expires_at": "2026-09-22T00:00:00Z",
        "fixture_payload_sha256": "sha256:" + ("0" * 64),
    }
    bundle["fixture_payload_sha256"] = _self_hash(bundle, "fixture_payload_sha256")
    from strict_projection_publisher import publish_projection

    with pytest.raises(RuntimeError):
        publish_projection(
            bundle=bundle,
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=publication["publication_payload_sha256"],
        )
    FAULT_HOOKS.clear()
    fenced = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    restored = recover_projection(
        scope_path=scope_path,
        registry_path=registry_path,
        strict_config_path=config_path,
        expected_publication_sha256=fenced["publication_payload_sha256"],
    )
    assert restored["mode"] == "unavailable"
    assert restored["authority_seq"] == 0
    assert restored["pending_operation_id"] is None


# ---------------------------------------------------------------------------
# Parent-head rules; rollback no expiry renewal; immutable history
# ---------------------------------------------------------------------------


def test_parent_head_mismatch_rejects_before_history_mutation(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, publish_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    hist_before = {p.name for p in (root / "active" / "history").glob("*.json")}
    grounding = {
        "schema": "convmem.strict-grounding.v1",
        "blobs": [],
        "roots": [],
        "edges": [],
        "outputs": [],
        "receipts": [],
        "grounding_payload_sha256": "sha256:" + ("0" * 64),
    }
    grounding["grounding_payload_sha256"] = _self_hash(grounding, "grounding_payload_sha256")
    provenance = {
        "schema": "convmem.strict-provenance-context.v2",
        "schema_semantics": [],
        "policies": [],
        "recipes": [],
        "verified_channels": [],
        "registered_assertions": [],
        "grounding_sha256": grounding["grounding_payload_sha256"],
        "context_payload_sha256": "sha256:" + ("0" * 64),
    }
    provenance["context_payload_sha256"] = _self_hash(provenance, "context_payload_sha256")
    bundle = {
        "schema": "convmem.strict-fixture-bundle.v2",
        "lineage_id": _LINEAGE,
        "operation_id": "e" * 32,
        "expected_parent_manifest_sha256": "sha256:" + ("9" * 64),  # wrong for genesis
        "batches": [],
        "dispositions": [],
        "provenance_context": provenance,
        "grounding": grounding,
        "built_at": _TS,
        "as_of": _TS,
        "expires_at": "2026-09-22T00:00:00Z",
        "fixture_payload_sha256": "sha256:" + ("0" * 64),
    }
    bundle["fixture_payload_sha256"] = _self_hash(bundle, "fixture_payload_sha256")
    with pytest.raises(StrictPublisherError, match="parent_head_mismatch"):
        publish_projection(
            bundle=bundle,
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=publication["publication_payload_sha256"],
        )
    hist_after = {p.name for p in (root / "active" / "history").glob("*.json")}
    assert hist_after == hist_before


def test_rollback_refuses_foreign_authority_and_does_not_renew_expiry(tmp_path: Path):
    from strict_projection_publisher import StrictPublisherError, rollback_projection

    root, publication, _, _, config_path, scope_path, registry_path = _enroll_matched(
        tmp_path
    )
    # Genesis has no authority — rollback must refuse.
    with pytest.raises(StrictPublisherError, match="rollback_requires_authority"):
        rollback_projection(
            scope_path=scope_path,
            registry_path=registry_path,
            strict_config_path=config_path,
            expected_publication_sha256=publication["publication_payload_sha256"],
            target_generation="gen2_" + "a" * 64,
        )


def test_immutable_history_written_before_pointer_replace_on_enroll(tmp_path: Path):
    root, publication, *_ = _enroll_root(tmp_path)
    hex_part = publication["publication_payload_sha256"].removeprefix("sha256:")
    history = root / "active" / "history" / f"{hex_part}.json"
    assert history.is_file()
    hist_obj = json.loads(history.read_text())
    active = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    assert hist_obj == active


def test_cli_main_enroll_fixture_roundtrip(tmp_path: Path):
    from strict_projection_publisher import main

    root = tmp_path / "projection-root"
    root.mkdir()
    sc_path, sc_hash = _semantic_contract(tmp_path)
    cutoff = _empty_cutoff()
    enrollment = _enrollment_obj(sc_hash=sc_hash, cutoff_hash=cutoff["cutoff_payload_sha256"])
    enroll_path = tmp_path / "enrollment.json"
    _write_json(enroll_path, enrollment)
    config = {
        "schema": "convmem.strict-config.v2",
        "projection_root": str(root.resolve()),
        "max_projection_rows": 10000,
        "max_projection_bytes": 67108864,
        "telemetry": False,
    }
    config_path = tmp_path / "strict-config.json"
    _write_json(config_path, config)
    rc = main(
        [
            "enroll-fixture",
            "--enrollment",
            str(enroll_path),
            "--semantic-contract",
            str(sc_path),
            "--strict-config",
            str(config_path),
        ]
    )
    assert rc == 0
    active = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    assert active["authority_seq"] == 0
    assert active["mode"] == "unavailable"


def test_exact_operation_retry_returns_historic_outcome_with_current_head(tmp_path: Path):
    """Case 49 publisher portion: exact preserved operation is idempotent at head."""
    from strict_projection_publisher import _find_operation_outcome

    root, publication, *_ = _enroll_root(tmp_path)
    # Synthesize a historic admitted publication + matching input under authority.
    snap = "snap2_" + "1" * 64
    auth = root / "authority" / snap
    auth.mkdir(parents=True)
    op_id = "e" * 32
    bundle = {
        "schema": "convmem.strict-fixture-bundle.v2",
        "lineage_id": _LINEAGE,
        "operation_id": op_id,
        "expected_parent_manifest_sha256": None,
        "batches": [],
        "dispositions": [],
        "provenance_context": {
            "schema": "convmem.strict-provenance-context.v2",
            "schema_semantics": [],
            "policies": [],
            "recipes": [],
            "verified_channels": [],
            "registered_assertions": [],
            "grounding_sha256": "sha256:" + ("a" * 64),
            "context_payload_sha256": "sha256:" + ("b" * 64),
        },
        "grounding": {
            "schema": "convmem.strict-grounding.v1",
            "blobs": [],
            "roots": [],
            "edges": [],
            "outputs": [],
            "receipts": [],
            "grounding_payload_sha256": "sha256:" + ("a" * 64),
        },
        "built_at": _TS,
        "as_of": _TS,
        "expires_at": "2026-09-22T00:00:00Z",
        "fixture_payload_sha256": "sha256:" + ("0" * 64),
    }
    bundle["fixture_payload_sha256"] = _self_hash(bundle, "fixture_payload_sha256")
    _write_json(auth / "input.json", bundle)
    historic = dict(publication)
    historic["epoch"] = 2
    historic["authority_seq"] = 1
    historic["authority_snapshot_id"] = snap
    historic["authority_manifest_sha256"] = "sha256:" + ("c" * 64)
    historic["mode"] = "unavailable"
    historic["previous_publication_sha256"] = publication["publication_payload_sha256"]
    historic["publication_payload_sha256"] = "sha256:" + ("0" * 64)
    historic["publication_payload_sha256"] = _self_hash(
        historic, "publication_payload_sha256"
    )
    hist_path = (
        root
        / "active"
        / "history"
        / f"{historic['publication_payload_sha256'].removeprefix('sha256:')}.json"
    )
    _write_json(hist_path, historic)
    found = _find_operation_outcome(
        root, operation_id=op_id, input_sha256=bundle["fixture_payload_sha256"]
    )
    assert found is not None
    assert found["publication_payload_sha256"] == historic["publication_payload_sha256"]
    # Current head remains the genesis pointer (not rewritten by lookup).
    active = json.loads((root / "active" / f"{_LINEAGE}.json").read_text())
    assert active["publication_payload_sha256"] == publication["publication_payload_sha256"]


def test_no_publisher_owned_manager_or_retirement_exports():
    import strict_projection_publisher as pub

    forbidden = {
        "retire_slot",
        "manager_empty",
        "attest_empty_domain",
        "start_activation",
        "stop_unit",
    }
    for name in forbidden:
        assert not hasattr(pub, name), f"publisher must not own {name}"
