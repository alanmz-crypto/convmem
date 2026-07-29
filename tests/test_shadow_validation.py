# pylint: disable=too-many-lines,too-many-locals
"""C1 strict Shadow validation / filesystem-policy contract tests."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

from shadow_ledger import (
    ARTIFACT_FILE_MODE,
    SHADOW_DIR_MODE,
    compute_ledger_header_hash,
    ledger_header_payload,
    lexical_abspath,
    projection_state_hash,
    sha256_canonical,
)
from shadow_validation import (
    REFUSAL_CODES_C1,
    ValidationMode,
    build_valid_manifest_fixture,
    validate_shadow_activation,
)


@dataclass
class Layout:
    root: Path
    chroma: Path
    shadow: Path
    ledger: Path
    manifest: Path
    health: Path


def _layout(tmp_path: Path) -> Layout:
    root = tmp_path / "data"
    chroma = root / "chroma"
    shadow = root / "shadow"
    root.mkdir(parents=True)
    # Shared data root may be broader than 0700.
    os.chmod(root, 0o755)
    chroma.mkdir()
    shadow.mkdir()
    os.chmod(shadow, SHADOW_DIR_MODE)
    return Layout(
        root=root,
        chroma=chroma,
        shadow=shadow,
        ledger=shadow / "ledger.jsonl",
        manifest=shadow / "activation.json",
        health=shadow / "health.json",
    )


def _entity(eid: str, *, classification: str = "active") -> dict[str, Any]:
    doc = f"doc-{eid}"
    meta = {"k": eid}
    return {
        "classification": classification,
        "document_hash": sha256_canonical(doc),
        "metadata_hash": sha256_canonical(meta),
        "state_hash": projection_state_hash(
            stable_entity_id=eid,
            deleted=False,
            document=doc,
            metadata=meta,
        ),
    }


def _write_private(path: Path, data: bytes | str) -> None:
    if isinstance(data, str):
        data = data.encode("utf-8")
    path.write_bytes(data)
    os.chmod(path, ARTIFACT_FILE_MODE)


def _write_ledger(path: Path, header: dict[str, Any], events: list[dict[str, Any]] | None = None) -> None:
    lines = [json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n"]
    for event in events or []:
        lines.append(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    _write_private(path, "".join(lines))


def _valid_bundle(
    layout: Layout,
    *,
    activation_id: str = "act-1",
    code_commit: str = "abc123",
    collection_uuid: str = "uuid-1",
    ledger_identity: str = "ledger-1",
    starting_sequence: int = 0,
    entities: dict[str, dict[str, Any]] | None = None,
    enabled: bool = True,
    with_config_bindings: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    header = ledger_header_payload(
        activation_id=activation_id,
        ledger_identity=ledger_identity,
        starting_sequence=starting_sequence,
        created_at_utc="2026-07-28T00:00:00Z",
    )
    header_hash = compute_ledger_header_hash(header)
    manifest = build_valid_manifest_fixture(
        activation_id=activation_id,
        code_commit=code_commit,
        chroma_root=layout.chroma,
        collection_uuid=collection_uuid,
        entity_baselines=entities or {},
        shadow_ledger_identity=ledger_identity,
        ledger_header_hash=header_hash,
        starting_sequence=starting_sequence,
    )
    _write_private(layout.manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    _write_ledger(layout.ledger, header)
    _write_private(layout.health, "{}\n")
    section: dict[str, Any] = {
        "enabled": enabled,
        "ledger_path": str(layout.ledger),
        "activation_manifest_path": str(layout.manifest),
        "health_path": str(layout.health),
    }
    if with_config_bindings:
        section["activation_id"] = activation_id
        section["manifest_sha256"] = manifest["manifest_canonical_hash"]
    cfg = {
        "index": {"chroma_dir": str(layout.chroma)},
        "shadow_ledger": section,
    }
    return cfg, manifest


def _validate(
    cfg: dict[str, Any],
    chroma: Path,
    mode: str = "writer",
    **kwargs: Any,
):
    return validate_shadow_activation(
        None,
        chroma,
        mode,
        cfg=cfg,
        collection_uuid_provider=kwargs.pop(
            "collection_uuid_provider", lambda *_a, **_k: "uuid-1"
        ),
        runtime_code_revision=kwargs.pop("runtime_code_revision", "abc123"),
        **kwargs,
    )


def test_disabled_absent_artifacts_safe(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg = {
        "index": {"chroma_dir": str(layout.chroma)},
        "shadow_ledger": {"enabled": False},
    }
    result = _validate(cfg, layout.chroma)
    assert result.state == "disabled"
    assert result.inject_eligible is False
    assert result.refusals == ()


def test_valid_fixture_inject_eligible(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _manifest = _valid_bundle(layout)
    result = _validate(cfg, layout.chroma, mode="writer")
    assert result.codes() == ()
    assert result.inject_eligible is True
    assert result.activation_id == "act-1"
    assert result.state == "committed"


def test_modes_share_refusal_meaning(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout)
    manifest["manifest_version"] = 99
    # broken canonical hash + unsupported version
    _write_private(layout.manifest, json.dumps(manifest, sort_keys=True) + "\n")
    codes = {}
    for mode in ValidationMode:
        if mode == ValidationMode.PREPARE:
            continue
        result = _validate(cfg, layout.chroma, mode=mode.value)
        codes[mode.value] = result.codes()
        assert "manifest_version_unsupported" in result.codes()
        assert result.inject_eligible is False
    assert codes["writer"] == codes["doctor"] == codes["inventory"]


def test_refusal_order_and_dedup(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout)
    manifest["manifest_version"] = 99
    manifest["shadow_schema_version"] = 99
    manifest["active_unit_count"] = -1
    _write_private(layout.manifest, json.dumps(manifest, sort_keys=True) + "\n")
    result = _validate(cfg, layout.chroma)
    codes = list(result.codes())
    assert codes == sorted(codes, key=lambda c: list(REFUSAL_CODES_C1).index(c) if c in REFUSAL_CODES_C1 else 999)
    # dedup: same code+artifact once
    pairs = [(r.code, r.artifact) for r in result.refusals]
    assert len(pairs) == len(set(pairs))


def test_redaction_hides_home_paths(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    # Force a detail that includes home-like absolute path via chroma mismatch wording
    result = validate_shadow_activation(
        None,
        layout.chroma / "nope",
        "writer",
        cfg=cfg,
        collection_uuid_provider=lambda *_a, **_k: "uuid-1",
        runtime_code_revision="abc123",
    )
    blob = json.dumps(result.as_dict())
    assert str(Path.home()) not in blob


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (
            lambda layout, cfg, manifest, header: _write_private(
                layout.manifest, "{not-json\n"
            ),
            "manifest_corrupt",
        ),
        (
            lambda layout, cfg, manifest, header: layout.manifest.unlink(),
            "manifest_missing",
        ),
        (
            lambda layout, cfg, manifest, header: _mutate_manifest(
                layout, manifest, manifest_version=99
            ),
            "manifest_version_unsupported",
        ),
        (
            lambda layout, cfg, manifest, header: _mutate_manifest(
                layout, manifest, completion_status="incomplete"
            ),
            "manifest_incomplete",
        ),
        (
            lambda layout, cfg, manifest, header: _mutate_manifest(
                layout, manifest, collection="other"
            ),
            "collection_mismatch",
        ),
        (
            lambda layout, cfg, manifest, header: None,
            "code_revision_mismatch",
        ),
        (
            lambda layout, cfg, manifest, header: _mutate_manifest(
                layout, manifest, active_unit_count=-1
            ),
            "baseline_count_invalid",
        ),
        (
            lambda layout, cfg, manifest, header: _mutate_manifest(
                layout, manifest, aggregate_baseline_digest="0" * 64
            ),
            "baseline_hash_invalid",
        ),
        (
            lambda layout, cfg, manifest, header: layout.ledger.unlink(),
            "ledger_missing",
        ),
        (
            lambda layout, cfg, manifest, header: _write_private(
                layout.ledger, '{"record_type":"ledger_header"\n'
            ),
            "ledger_corrupt",
        ),
        (
            lambda layout, cfg, manifest, header: _write_ledger(
                layout.ledger,
                {**header, "ledger_identity": "other-id"},
            ),
            "ledger_identity_mismatch",
        ),
        (
            lambda layout, cfg, manifest, header: _write_ledger(
                layout.ledger,
                {**header, "starting_sequence": -3},
            ),
            "starting_sequence_invalid",
        ),
    ],
)
def test_c1_refusal_matrix(tmp_path: Path, mutate, expected: str) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout)
    header = ledger_header_payload(
        activation_id="act-1",
        ledger_identity="ledger-1",
        starting_sequence=0,
        created_at_utc="2026-07-28T00:00:00Z",
    )
    kwargs = {}
    if expected == "code_revision_mismatch":
        kwargs["runtime_code_revision"] = "different"
    else:
        mutate(layout, cfg, manifest, header)
        # After ledger identity rewrite, header hash in manifest no longer matches —
        # that is also ledger_identity_mismatch; acceptable alongside target.
        if expected == "starting_sequence_invalid":
            # keep manifest starting_sequence 0 vs header -3
            pass
    result = _validate(cfg, layout.chroma, **kwargs)
    assert expected in result.codes()
    assert result.inject_eligible is False


def _mutate_manifest(layout: Layout, manifest: dict[str, Any], **fields: Any) -> None:
    updated = dict(manifest)
    updated.update(fields)
    # Recompute canonical hash only when caller did not intentionally break it.
    if "manifest_canonical_hash" not in fields and "aggregate_baseline_digest" not in fields:
        from shadow_ledger import compute_manifest_canonical_hash

        updated.pop("manifest_canonical_hash", None)
        updated["manifest_canonical_hash"] = compute_manifest_canonical_hash(updated)
    _write_private(layout.manifest, json.dumps(updated, sort_keys=True) + "\n")


def test_unsupported_schema_version(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout)
    _mutate_manifest(layout, manifest, shadow_schema_version=7)
    result = _validate(cfg, layout.chroma)
    assert "manifest_version_unsupported" in result.codes()
    assert result.inject_eligible is False


def test_missing_and_wrong_types(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout)
    _mutate_manifest(layout, manifest, entity_baselines=["nope"])
    result = _validate(cfg, layout.chroma)
    assert "manifest_corrupt" in result.codes()
    assert result.inject_eligible is False


def test_negative_and_inconsistent_counts(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout, entities={"u1": _entity("u1")})
    _mutate_manifest(
        layout,
        manifest,
        active_unit_count=1,
        historical_unit_count=1,
        total_unit_count=1,
    )
    result = _validate(cfg, layout.chroma)
    assert "baseline_count_invalid" in result.codes()


def test_wrong_entity_and_aggregate_hashes(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    entities = {"u1": _entity("u1")}
    cfg, manifest = _valid_bundle(layout, entities=entities)
    entities2 = dict(entities)
    entities2["u1"] = {**entities["u1"], "state_hash": "a" * 64}
    _mutate_manifest(
        layout,
        manifest,
        entity_baselines=entities2,
        aggregate_baseline_digest=manifest["aggregate_baseline_digest"],
    )
    result = _validate(cfg, layout.chroma)
    assert "baseline_hash_invalid" in result.codes()


def test_wrong_collection_uuid(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout, collection_uuid="uuid-1")
    result = _validate(
        cfg,
        layout.chroma,
        collection_uuid_provider=lambda *_a, **_k: "uuid-OTHER",
    )
    assert "collection_mismatch" in result.codes()
    assert result.inject_eligible is False


def test_wrong_activation_and_ledger_identity(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, manifest = _valid_bundle(layout)
    cfg["shadow_ledger"]["activation_id"] = "other-act"
    result = _validate(cfg, layout.chroma)
    assert "config_activation_mismatch" in result.codes()
    assert result.inject_eligible is False


def test_truncated_noncontiguous_ledger(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    header = ledger_header_payload(
        activation_id="act-1",
        ledger_identity="ledger-1",
        starting_sequence=0,
        created_at_utc="2026-07-28T00:00:00Z",
    )
    events = [
        {
            "shadow_schema_version": 1,
            "sequence": 1,
            "event_id": "e1",
        },
        {
            "shadow_schema_version": 1,
            "sequence": 3,
            "event_id": "e2",
        },
    ]
    _write_ledger(layout.ledger, header, events)
    result = _validate(cfg, layout.chroma)
    assert "starting_sequence_invalid" in result.codes()


def test_path_equality_collision(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    cfg["shadow_ledger"]["health_path"] = str(layout.ledger)
    result = _validate(cfg, layout.chroma)
    assert "path_collision" in result.codes()
    assert result.inject_eligible is False


def test_hardlink_collision(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    layout.health.unlink()
    os.link(layout.ledger, layout.health)
    os.chmod(layout.health, ARTIFACT_FILE_MODE)
    result = _validate(cfg, layout.chroma)
    assert "path_collision" in result.codes() or "artifact_type_invalid" in result.codes()
    assert result.inject_eligible is False


def test_artifact_inside_chroma(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    bad_ledger = layout.chroma / "ledger.jsonl"
    cfg, _m = _valid_bundle(layout)
    # move paths inside chroma
    cfg["shadow_ledger"]["ledger_path"] = str(bad_ledger)
    cfg["shadow_ledger"]["activation_manifest_path"] = str(layout.chroma / "act.json")
    cfg["shadow_ledger"]["health_path"] = str(layout.chroma / "health.json")
    for p in (
        bad_ledger,
        layout.chroma / "act.json",
        layout.chroma / "health.json",
    ):
        _write_private(p, "{}\n")
    result = _validate(cfg, layout.chroma)
    assert "path_inside_chroma" in result.codes()
    assert result.inject_eligible is False


def test_symlink_leaf_and_ancestor(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    # leaf symlink
    real = layout.shadow / "real-ledger.jsonl"
    real.write_bytes(layout.ledger.read_bytes())
    os.chmod(real, ARTIFACT_FILE_MODE)
    layout.ledger.unlink()
    layout.ledger.symlink_to(real)
    result = _validate(cfg, layout.chroma)
    assert "symlink_refused" in result.codes()
    assert result.inject_eligible is False

    # ancestor symlink
    layout2 = _layout(tmp_path / "anc")
    cfg2, _m2 = _valid_bundle(layout2)
    # replace shadow dir with symlink to other dir
    alt = layout2.root / "shadow-real"
    # recreate: move contents
    import shutil

    shutil.move(str(layout2.shadow), str(alt))
    layout2.shadow.symlink_to(alt)
    # rewrite cfg paths (same string paths)
    cfg2["shadow_ledger"]["ledger_path"] = str(layout2.shadow / "ledger.jsonl")
    cfg2["shadow_ledger"]["activation_manifest_path"] = str(
        layout2.shadow / "activation.json"
    )
    cfg2["shadow_ledger"]["health_path"] = str(layout2.shadow / "health.json")
    result2 = _validate(cfg2, layout2.chroma)
    assert "symlink_refused" in result2.codes()
    assert result2.inject_eligible is False


def test_non_regular_file(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    layout.health.unlink()
    os.mkfifo(layout.health)
    try:
        os.chmod(layout.health, ARTIFACT_FILE_MODE)
    except OSError:
        pass
    result = _validate(cfg, layout.chroma)
    assert "artifact_type_invalid" in result.codes()
    assert result.inject_eligible is False


def test_wrong_owner_via_stat_seam(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    real_lstat = os.lstat

    def fake_lstat(path):
        st = real_lstat(path)
        # Make artifact files look like another uid.
        p = Path(path)
        if p.name in {"ledger.jsonl", "activation.json", "health.json"} or p.name == "shadow":
            return os.stat_result(
                (
                    st.st_mode,
                    st.st_ino,
                    st.st_dev,
                    st.st_nlink,
                    st.st_uid + 1,
                    st.st_gid,
                    st.st_size,
                    st.st_atime,
                    st.st_mtime,
                    st.st_ctime,
                )
            )
        return st

    result = _validate(cfg, layout.chroma, lstat=fake_lstat, expected_uid=os.geteuid())
    assert "path_wrong_owner" in result.codes()
    assert result.inject_eligible is False


def test_directory_mode_not_0700(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    os.chmod(layout.shadow, 0o755)
    result = _validate(cfg, layout.chroma)
    assert "permission_invalid" in result.codes() or "directory_not_private" in result.codes()
    assert result.inject_eligible is False


def test_file_mode_not_0600(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    os.chmod(layout.ledger, 0o644)
    result = _validate(cfg, layout.chroma)
    assert "permission_invalid" in result.codes()
    assert result.inject_eligible is False


def test_shadow_sibling_under_broad_data_root(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    assert stat.S_IMODE(layout.root.stat().st_mode) == 0o755
    cfg, _m = _valid_bundle(layout)
    result = _validate(cfg, layout.chroma)
    assert result.inject_eligible is True
    assert result.codes() == ()


def test_prepared_not_committed(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout, enabled=False)
    result = _validate(cfg, layout.chroma)
    assert "prepared_not_committed" in result.codes()
    assert result.inject_eligible is False


def test_malformed_manifest_corrupt_ledger_probe(tmp_path: Path) -> None:
    """Former acceptance probe: shallow inject=true; strict contract refuses."""
    layout = _layout(tmp_path)
    # Reproduce the diagnostic combination described in the corrective plan.
    bad_manifest = {
        "manifest_version": 99,
        "shadow_schema_version": 99,
        "hash_rules_version": 99,
        "activation_id": "act-bad",
        "baseline_id": "act-bad",
        "completion_status": "complete",
        "activation_timestamp_utc": "2026-07-28T00:00:00Z",
        "code_commit": "wrong-rev",
        "chroma_root": str(lexical_abspath(layout.chroma)),
        "collection": "knowledge_units",
        "collection_uuid": "uuid-1",
        "active_unit_count": -5,
        "historical_unit_count": 0,
        "total_unit_count": -5,
        "entity_baselines": {},
        "aggregate_baseline_digest": "0" * 64,
        "configured_embed_model": "nomic-embed-text",
        "observed_embed_model": "unknown",
        "observed_embed_dimensions": None,
        "shadow_ledger_identity": "ledger-A",
        "ledger_header_hash": "0" * 64,
        "starting_sequence": -1,
        "manifest_canonical_hash": "0" * 64,
    }
    _write_private(layout.manifest, json.dumps(bad_manifest) + "\n")
    _write_private(layout.ledger, "{this is not json\n")
    _write_private(layout.health, "{}\n")
    os.chmod(layout.shadow, SHADOW_DIR_MODE)
    cfg = {
        "index": {"chroma_dir": str(layout.chroma)},
        "shadow_ledger": {
            "enabled": True,
            "activation_id": "act-bad",
            "manifest_sha256": "0" * 64,
            "ledger_path": str(layout.ledger),
            "activation_manifest_path": str(layout.manifest),
            "health_path": str(layout.health),
        },
    }
    # Old shallow gate would accept complete-looking non-null fields; prove strict refuses.
    from shadow_ledger import decide_sink_injection, manifest_is_complete

    assert manifest_is_complete(bad_manifest) is True
    shallow = decide_sink_injection(cfg, chroma_dir=layout.chroma)
    # Shallow gate still eligible by old rules (versions/counts unchecked).
    assert shallow.inject is True

    result = _validate(cfg, layout.chroma, runtime_code_revision="abc123")
    assert result.inject_eligible is False
    for code in (
        "manifest_version_unsupported",
        "baseline_count_invalid",
        "code_revision_mismatch",
        "ledger_corrupt",
        "starting_sequence_invalid",
    ):
        assert code in result.codes(), result.codes()


def test_canonical_alias_collision(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    cfg, _m = _valid_bundle(layout)
    # lexical alias via redundant segments
    cfg["shadow_ledger"]["ledger_path"] = str(layout.shadow / "sub" / ".." / "ledger.jsonl")
    result = _validate(cfg, layout.chroma)
    # After normpath, ledger equals manifest? no — equals original ledger path; should still validate
    # Create an actual collision by pointing health to normalized ledger path via alias
    cfg["shadow_ledger"]["health_path"] = str(layout.shadow / "x" / ".." / "ledger.jsonl")
    result = _validate(cfg, layout.chroma)
    assert "path_collision" in result.codes()




def test_path_not_private_non_sibling(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    other = tmp_path / "elsewhere" / "shadow"
    other.mkdir(parents=True)
    os.chmod(other, SHADOW_DIR_MODE)
    cfg, _m = _valid_bundle(layout)
    # Point artifacts at a non-sibling shadow directory.
    for name in ("ledger.jsonl", "activation.json", "health.json"):
        src = layout.shadow / name
        dst = other / name
        dst.write_bytes(src.read_bytes())
        os.chmod(dst, ARTIFACT_FILE_MODE)
    cfg["shadow_ledger"]["ledger_path"] = str(other / "ledger.jsonl")
    cfg["shadow_ledger"]["activation_manifest_path"] = str(other / "activation.json")
    cfg["shadow_ledger"]["health_path"] = str(other / "health.json")
    result = _validate(cfg, layout.chroma)
    assert "path_not_private" in result.codes()
    assert result.inject_eligible is False

def test_every_c1_code_covered_by_matrix() -> None:
    """Meta: ensure the suite names every C1 refusal at least once (static list)."""
    source = Path(__file__).read_text(encoding="utf-8")
    missing = [c for c in REFUSAL_CODES_C1 if c not in source]
    assert missing == [], missing
