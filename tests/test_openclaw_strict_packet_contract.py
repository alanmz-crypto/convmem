"""Case 57 T0a containment/refusal greens; later-T reds mapped."""

from __future__ import annotations

import errno
import json
import os
import sys
from pathlib import Path

# Import fixture helpers without tests/fixtures/__init__.py (not authorized at M1).
sys.path.insert(0, str(Path("tests/fixtures/openclaw_strict").resolve()))
import constants as oc_constants  # noqa: E402
import suites as oc_suites  # noqa: E402
from fixture_manifest import ManifestNotAvailable, emit_complete_manifest  # noqa: E402


def test_case57_preflight_sentinel_present_inside_runner():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    assert Path("/fixture/preflight_ok").is_file()
    report = json.loads(Path("/fixture/preflight_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["tmpfs_size_bytes"] == 268435456
    assert report.get("import_sentinel") == "written"


def test_case57_preflight_fds_proc_self_fd_f_getfd():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    report = json.loads(Path("/fixture/preflight_report.json").read_text(encoding="utf-8"))
    fds = report["fds"]
    assert fds["source"] == "proc_self_fd_f_getfd"
    assert fds["fds"] == [0, 1, 2]
    assert fds["unexpected"] == []


def test_case57_tmp_allocated_bytes_uses_st_blocks():
    """Allocated-byte helper uses st_blocks*512 and counts each inode once."""
    import limits as oc_limits

    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    root = Path("/fixture/tmp_alloc_probe")
    root.mkdir(mode=0o700, exist_ok=True)
    blob = root / "blob"
    blob.write_bytes(b"x" * 100)
    st = os.lstat(blob)
    expected = st.st_blocks * 512
    assert oc_limits._tmp_used_bytes(str(root)) == expected
    link = root / "blob_hardlink"
    os.link(blob, link)
    # Hardlink shares inode — must not double-count allocated blocks.
    assert oc_limits._tmp_used_bytes(str(root)) == expected
    assert expected != st.st_size or expected == st.st_blocks * 512


def test_case57_kernel_denial_readonly_mount_writes():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    for path in ("/src/.case57_write", "/runtime/.case57_write", "/usr/.case57_write"):
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            assert exc.errno in {errno.EROFS, errno.EACCES, errno.EPERM, errno.ENOENT}
        else:
            os.close(fd)
            raise AssertionError(f"readonly mount accepted write: {path}")


def test_case57_outside_root_canary_kernel_denials():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    canaries = json.loads(Path("/fixture/canary_paths.json").read_text(encoding="utf-8"))
    assert len(canaries) >= 2
    for path in canaries:
        try:
            os.open(path, os.O_RDONLY)
        except OSError as exc:
            assert exc.errno in {errno.ENOENT, errno.EACCES, errno.EPERM, errno.ENOTDIR}
        else:
            raise AssertionError(f"outside-root canary readable: {path}")
        try:
            os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError as exc:
            assert exc.errno in {errno.ENOENT, errno.EACCES, errno.EPERM, errno.EROFS, errno.ENOTDIR}
        else:
            raise AssertionError(f"outside-root canary writable: {path}")


def test_case57_runtime_not_host_usr():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    assert Path("/runtime/bin/python").is_file()
    assert Path("/usr").is_dir()


def test_case57_fixture_legacy_identity_config_only():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    cfg = Path("/fixture/home/.config/convmem/config.toml")
    assert cfg.is_file()
    text = cfg.read_text(encoding="utf-8")
    assert text == '[index]\nchroma_dir = "/fixture/legacy-live-identity/chroma"\n'
    assert Path("/fixture/legacy-live-identity/chroma").is_dir()
    assert (Path("/fixture/legacy-live-identity/chroma").stat().st_mode & 0o777) == 0o700


def test_case57_pytest_plugin_inventory(pytestconfig):
    """Record actual loaded plugins from the live strict pytest process."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    assert os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
    pm = pytestconfig.pluginmanager

    # Live loaded names only: blocked registrations keep the name with plugin=None.
    loaded_pairs = [(name, plugin) for name, plugin in pm.list_name_plugin() if plugin is not None]
    loaded_plugin_names = sorted({name for name, _plugin in loaded_pairs})
    assert "cacheprovider" not in loaded_plugin_names
    assert "pytest_cacheprovider" not in loaded_plugin_names
    assert "no:cacheprovider" not in loaded_plugin_names
    assert pm.has_plugin("cacheprovider") is False
    assert pm.has_plugin("pytest_cacheprovider") is False

    # Distribution plugins from the live manager only (not registry-wide entry points).
    distribution_plugins: list[dict[str, str]] = []
    unapproved: list[str] = []
    for plugin, dist in pm.list_plugin_distinfo():
        plugin_name = None
        for name, obj in loaded_pairs:
            if obj is plugin:
                plugin_name = name
                break
        if plugin_name is None:
            plugin_name = getattr(plugin, "__name__", type(plugin).__name__)
        module_name = getattr(plugin, "__module__", "") or ""
        dist_name = getattr(dist, "project_name", None) or getattr(dist, "name", "") or ""
        dist_version = getattr(dist, "version", "") or ""
        entry = {
            "plugin": plugin_name,
            "module": module_name,
            "distribution": dist_name,
            "version": dist_version,
        }
        distribution_plugins.append(entry)
        # Autoload false + explicitly_loaded empty → any live external dist plugin fails.
        if dist_name and dist_name != "pytest":
            unapproved.append(f"{dist_name}:{plugin_name}")
    assert not unapproved, f"unapproved_external_distribution_plugins:{unapproved}"

    inventory = {
        "autoload": False,
        "disabled_plugins": ["cacheprovider"],
        "explicitly_loaded_plugins": [],
        "loaded_plugin_names": loaded_plugin_names,
        "loaded_distribution_plugins": sorted(
            distribution_plugins,
            key=lambda d: (d["distribution"], d["version"], d["plugin"], d["module"]),
        ),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": os.environ.get(
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD"
        ),
    }
    Path(oc_constants.PLUGIN_INVENTORY_PATH).write_text(
        json.dumps(inventory, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def test_runner_frozen_suite_selectors():
    strict = oc_suites.strict_pytest_argv()
    assert strict[:6] == [
        "/runtime/bin/python",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    assert len(oc_constants.STRICT_PYTEST_FILES) == 13
    for path in oc_constants.STRICT_PYTEST_FILES:
        assert path in strict
    assert oc_suites.connector_node_argv() == [
        "/runtime/bin/node",
        "--test",
        "integrations/openclaw-convmem-reader/test/connector.test.mjs",
    ]
    legacy = oc_suites.legacy_pytest_argv()
    for node_id in oc_constants.LEGACY_DESELECTS:
        assert f"--deselect={node_id}" in legacy


def test_fixture_manifest_schema_exists_and_complete_emit_deferred():
    schema = Path("tests/fixtures/openclaw_strict/fixture-manifest.schema.json")
    assert schema.is_file()
    data = json.loads(schema.read_text(encoding="utf-8"))
    assert data["$id"] == "convmem.strict-fixture-manifest.v1"
    try:
        emit_complete_manifest()
    except ManifestNotAvailable:
        pass
    else:
        raise AssertionError("complete manifest must be unavailable at T0a")


def test_plan_and_baseline_constants_frozen():
    assert oc_constants.SEMANTIC_PARENT_SHA == "cd9d2698b7423f907b552bc9118a0af523018ca9"
    assert oc_constants.CODE_BASELINE_SHA == "7809f20dc53d9dd19f765c3ec3214a3df54ca5bf"
    assert oc_constants.EXPECTED_TEST_RUNTIME_TREE_SHA256.startswith("sha256:74a12c72")


def test_m2_gate_b_and_c_schema_inventory_exact():
    """Exact 24 Gate B + 7 Gate C schemas; no Gate W."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    gate_b = [
        "schemas/convmem-bound-read-scope-v2.schema.json",
        "schemas/convmem-project-binding-registry-v3.schema.json",
        "schemas/convmem-bound-authority-record-v3.schema.json",
        "schemas/convmem-authority-disposition-v1.schema.json",
        "schemas/convmem-strict-provenance-context-v2.schema.json",
        "schemas/convmem-strict-grounding-v1.schema.json",
        "schemas/convmem-capture-receipt-v1.schema.json",
        "schemas/convmem-strict-fixture-bundle-v2.schema.json",
        "schemas/convmem-strict-citation-map-v1.schema.json",
        "schemas/convmem-bound-authority-manifest-v3.schema.json",
        "schemas/convmem-bound-projection-row-v2.schema.json",
        "schemas/convmem-strict-graph-v1.schema.json",
        "schemas/convmem-bound-projection-manifest-v3.schema.json",
        "schemas/convmem-strict-generation-layout-v2.schema.json",
        "schemas/convmem-strict-publication-v2.schema.json",
        "schemas/convmem-strict-enrollment-v1.schema.json",
        "schemas/convmem-strict-slot-v1.schema.json",
        "schemas/convmem-strict-source-cutoff-v1.schema.json",
        "schemas/convmem-strict-semantic-contract-v1.schema.json",
        "schemas/convmem-strict-state-v2.schema.json",
        "schemas/convmem-clock-review-v1.schema.json",
        "schemas/convmem-raw-evidence-v3.schema.json",
        "schemas/convmem-error-v1.schema.json",
        "schemas/convmem-strict-config-v2.schema.json",
    ]
    gate_c = [
        "schemas/convmem-openclaw-connector-launch-v2.schema.json",
        "schemas/convmem-openclaw-activation-v2.schema.json",
        "schemas/convmem-activation-control-v1.schema.json",
        "schemas/convmem-activation-retirement-v1.schema.json",
        "schemas/convmem-activation-launch-policy-v1.schema.json",
        "schemas/convmem-activation-manager-policy-v1.schema.json",
        "schemas/convmem-controller-socket-policy-v1.schema.json",
    ]
    assert len(gate_b) == 24
    assert len(gate_c) == 7
    assert set(gate_b) | set(gate_c) == set(oc_constants.SCHEMA_ALLOWLIST)
    for rel in gate_b + gate_c:
        path = Path(rel)
        assert path.is_file(), f"missing_schema:{rel}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        if "oneOf" in data:
            assert data["$id"].startswith("convmem.")
            for variant in data["oneOf"]:
                assert variant.get("additionalProperties") is False
        else:
            assert data.get("additionalProperties") is False
            assert "schema" in data["required"]
    for forbidden in (
        "schemas/convmem-approved-admission-v1.schema.json",
        "schemas/convmem-admission-intent-v1.schema.json",
        "schemas/convmem-admission-review-v1.schema.json",
        "schemas/convmem-admission-ratification-v1.schema.json",
        "schemas/convmem-admission-event-v1.schema.json",
    ):
        assert not Path(forbidden).exists(), f"gate_w_schema_present:{forbidden}"


def test_m2_future_production_modules_remain_absent():
    """Kiro: six future production modules unauthorized at M2."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import component_inventory as inv

    missing = inv.missing_future_production_members(Path("."))
    assert missing == sorted(inv.FUTURE_PRODUCTION_MEMBERS)
    for rel in inv.FUTURE_PRODUCTION_MEMBERS:
        assert not Path(rel).exists(), f"unauthorized_stub_present:{rel}"


def test_m2_case58_literal_inventories_and_independent_walkers():
    """Five membership sets + two independent walkers; incomplete components reject."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import component_inventory as inv
    import case58_oracle as oracle
    import fixture_manifest as fm

    assert hasattr(fm, "build_component_inventories")
    inventories = inv.build_component_inventories()
    assert set(inventories) == {"builder", "strict_server", "supervisor", "controller", "plugin"}
    root = Path(".")
    # Incomplete components: missing future members → reject (future-step red).
    for name in ("builder", "strict_server", "supervisor", "controller"):
        try:
            inv.reference_walk_component(root, name)
        except inv.InventoryError as exc:
            assert "missing_member" in str(exc), name
        else:
            raise AssertionError(f"expected_missing_reject:{name}")
        try:
            oracle.independent_walk(root, name)
        except oracle.Case58OracleError as exc:
            assert "missing" in str(exc), name
        else:
            raise AssertionError(f"oracle_expected_missing:{name}")
        assert inv.source_component_digest_available(root, name) is False
    # Plugin is complete at M2 — both walkers agree.
    ref_entries = inv.reference_walk_component(root, "plugin")
    ora_entries = oracle.independent_walk(root, "plugin")
    assert ref_entries == ora_entries
    assert inv.component_tree_digest(ref_entries) == oracle.independent_tree_digest(ora_entries)
    # Positive source digests / complete five-hash manifest remain future-step red.
    try:
        fm.emit_complete_manifest()
    except fm.ManifestNotAvailable:
        pass
    else:
        raise AssertionError("complete_source_manifest_must_remain_future_red")


def test_m2_case58_plugin_mutation_and_symlink_controls():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import component_inventory as inv

    root = Path(".")
    # Independent byte-only and mode-only mutants (6 controls: 3+3); both walkers.
    plugin_report = inv.assert_plugin_byte_and_mode_mutations(root)
    assert plugin_report["mutant_count"] == 6
    assert plugin_report["byte_only_count"] == 3
    assert plugin_report["mode_only_count"] == 3
    kinds = {(m["path"], m["kind"]) for m in plugin_report["plugin_mutants"]}
    assert len(kinds) == 6
    inv.reject_symlink_member(
        root, "plugin", "integrations/openclaw-convmem-reader/index.js"
    )
    # Literal supplied-inventory: omit only canonical_json; forged digest agrees;
    # reject is exact-set membership (not other absent future sources).
    inv.reject_supplied_omit_only_canonical_json_forged_digest()
    inv.assert_omitted_canonical_json_mutant_fails(root)
    inv.reject_supplied_schema_subset()
    inv.reject_supplied_protected_helper_mutation()
    inv.reject_supplied_duplicate_missing_extra_path_escape()
    # Distinct cases: supplied extra inventory entry rejects; on-disk unrelated ignored.
    good = inv.reference_walk_component(root, "plugin")
    bad = list(good) + [
        {
            "path": "UNLISTED_FORGED.py",
            "mode": "0644",
            "sha256": "sha256:" + ("c" * 64),
        }
    ]
    try:
        inv.reject_supplied_inventory_extra_entry("plugin", bad)
    except inv.InventoryError as exc:
        assert "extra_supplied_member" in str(exc)
    else:
        raise AssertionError("supplied_extra_must_reject")
    inv.unrelated_on_disk_file_leaves_digest_unchanged(root, "plugin")


def test_m2_dual_independent_canonical_parsers_and_vectors():
    """Two independent strict raw parsers + production encode agreement."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import canonical_json
    import canonical_oracle as oracle_a
    import canonical_oracle_b as oracle_b
    from protocol_fixture.vectors import KNOWN_ANSWER_OBJECTS, REJECT_PAYLOADS

    def prod_encode(value):
        return canonical_json.canonical_json_bytes(
            value, validate=lambda _v: None, error_type=ValueError
        )

    for item in KNOWN_ANSWER_OBJECTS:
        prod = prod_encode(item["value"])
        a_bytes = oracle_a.encode_canonical_bytes(item["value"])
        b_bytes = oracle_b.encode_canonical_bytes(item["value"])
        assert prod == a_bytes == b_bytes == item["canonical_utf8"], item["name"]
        # Strict raw: already-canonical bytes accept; fixture-only digests only.
        assert oracle_a.parse_strict_raw(item["canonical_utf8"]) == item["value"]
        assert oracle_b.parse_strict_raw(item["canonical_utf8"]) == item["value"]
        digest_a = oracle_a.digest_sha256(item["value"])
        digest_b = oracle_b.digest_sha256(item["value"])
        assert digest_a == digest_b
        assert digest_a.startswith("sha256:")
        assert digest_a != "source-component"  # never treat as component hash
    for item in REJECT_PAYLOADS:
        for oracle, err in (
            (oracle_a, oracle_a.CanonicalOracleError),
            (oracle_b, oracle_b.CanonicalOracleBError),
        ):
            try:
                oracle.parse_strict_raw(item["payload"])
            except err:
                pass
            else:
                raise AssertionError(f"oracle_should_reject:{item['name']}:{oracle.__name__}")
    # Explicit reordered raw-byte rejection (must not repair via sort-on-output).
    reordered = b'{"b":2,"a":1}'
    try:
        oracle_a.parse_strict_raw(reordered)
    except oracle_a.CanonicalOracleError as exc:
        assert "noncanonical_raw_bytes" in str(exc)
    else:
        raise AssertionError("reordered_raw_accepted_by_oracle_a")
    try:
        oracle_b.parse_strict_raw(reordered)
    except oracle_b.CanonicalOracleBError as exc:
        assert "noncanonical_raw_bytes" in str(exc)
    else:
        raise AssertionError("reordered_raw_accepted_by_oracle_b")


def test_m2_schema_meta_and_31_positive_negative_instances():
    """Draft 2020-12 meta-schema + 31 positives + per-schema negatives inside runner."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    from protocol_fixture.schema_contract import run_all_schema_contract_checks

    report = run_all_schema_contract_checks(Path("schemas"))
    assert report["schema_count"] == 31
    assert report["meta_schema_ok"] == 31
    assert report["positive_ok"] == 31
    assert report["negative_ok"] == report["negative_total"]
    assert report["negative_total"] >= 31 * 4  # unknown/missing/wrong-type/null-discipline each
    # Every schema must include the four core negative names.
    from protocol_fixture.schema_contract import (
        FILENAME_TO_ID,
        build_negatives,
        load_schema,
    )

    for filename in FILENAME_TO_ID:
        schema = load_schema(Path("schemas"), filename)
        from protocol_fixture.schema_instances import POSITIVE_BY_FILENAME

        names = {n["name"] for n in build_negatives(schema, POSITIVE_BY_FILENAME[filename])}
        assert "unknown_top_level_key" in names, filename
        assert "missing_required_key" in names, filename
        assert "wrong_type" in names, filename
        assert "omitted_required_null" in names, filename
    assert report["activation_control_variants_ok"] == 4
    assert report["filename_to_id_exact"] is True
    assert report["deferred_cross_object_invariants"]


def test_m2_pinned_known_answer_vectors_dual_oracles():
    """Parent-defined vectors; dual fixture oracles recompute pinned constants."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import digest_oracle as ora
    import digest_oracle_b as orb
    from protocol_fixture import pinned_vectors as pv

    # Owner digest
    assert ora.owner_digest(**pv.OWNER_INPUT) == orb.owner_digest(**pv.OWNER_INPUT) == pv.OWNER_DIGEST
    assert ora.encode_canonical_bytes(
        {
            "schema": "convmem.strict-owner.v1",
            **{k: pv.OWNER_INPUT[k] for k in ("scope_sha256", "registry_sha256", "project_binding_id")},
        }
    ) == pv.OWNER_CANONICAL_UTF8

    # Event ID
    assert (
        ora.fixture_scan_event_id(**pv.SCAN_INPUT)
        == orb.fixture_scan_event_id(**pv.SCAN_INPUT)
        == pv.EVT_ID
    )

    # Logical IDs — prefixes derived from subject_kind only
    find2 = ora.logical_id(**pv.LOGICAL_COMMON, subject_kind="finding")
    choice2 = ora.logical_id(**pv.LOGICAL_COMMON, subject_kind="decision")
    assert find2 == orb.logical_id(**pv.LOGICAL_COMMON, subject_kind="finding") == pv.FIND2_ID
    assert choice2 == orb.logical_id(**pv.LOGICAL_COMMON, subject_kind="decision") == pv.CHOICE2_ID

    # Assertion IDs
    obs2 = ora.assertion_id(
        project_binding_id="project:convmem:v1",
        source_registration_id="src-reg-1",
        source_event_id=pv.EVT_ID,
        record_kind="observation",
        logical_id_value=pv.FIND2_ID,
    )
    assert obs2 == orb.assertion_id(
        project_binding_id="project:convmem:v1",
        source_registration_id="src-reg-1",
        source_event_id=pv.EVT_ID,
        record_kind="observation",
        logical_id_value=pv.FIND2_ID,
    ) == pv.OBS2_ID

    check2 = ora.logical_id(
        **pv.LOGICAL_COMMON,
        subject_kind="verification",
        target_assertion_id_or_empty=pv.OBS2_ID,
    )
    assert check2 == orb.logical_id(
        **pv.LOGICAL_COMMON,
        subject_kind="verification",
        target_assertion_id_or_empty=pv.OBS2_ID,
    ) == pv.CHECK2_ID

    dec2 = ora.assertion_id(
        project_binding_id="project:convmem:v1",
        source_registration_id="src-reg-1",
        source_event_id=pv.EVT_ID,
        record_kind="decision",
        logical_id_value=pv.CHOICE2_ID,
    )
    assert dec2 == pv.DEC2_ID == orb.assertion_id(
        project_binding_id="project:convmem:v1",
        source_registration_id="src-reg-1",
        source_event_id=pv.EVT_ID,
        record_kind="decision",
        logical_id_value=pv.CHOICE2_ID,
    )
    ver2 = ora.assertion_id(
        project_binding_id="project:convmem:v1",
        source_registration_id="src-reg-1",
        source_event_id=pv.EVT_ID,
        record_kind="verification",
        logical_id_value=pv.CHECK2_ID,
    )
    assert ver2 == pv.VER2_ID

    # Kind/prefix mismatch must reject (no generic prefix minting)
    try:
        ora.assertion_id(
            project_binding_id="project:convmem:v1",
            source_registration_id="src-reg-1",
            source_event_id=pv.EVT_ID,
            record_kind="observation",
            logical_id_value=pv.CHOICE2_ID,
        )
    except ora.DigestOracleError as exc:
        assert "kind_prefix_mismatch" in str(exc)
    else:
        raise AssertionError("kind_prefix_mismatch_accepted")

    # Citation / receipt / public handle
    assert (
        ora.citation_ref(
            project_binding_id="project:convmem:v1",
            assertion_id_value=pv.OBS2_ID,
            provenance_commitment=pv.PROVENANCE_COMMITMENT,
        )
        == orb.citation_ref(
            project_binding_id="project:convmem:v1",
            assertion_id_value=pv.OBS2_ID,
            provenance_commitment=pv.PROVENANCE_COMMITMENT,
        )
        == pv.CITE1_REF
    )
    assert ora.receipt_ref(pv.RECEIPT_PAYLOAD_HEX) == pv.CAPTURE_RECEIPT_REF
    assert (
        ora.public_handle(public_ref=pv.PUBLIC_REF, stored_external_id=pv.OBS2_ID)
        == orb.public_handle(public_ref=pv.PUBLIC_REF, stored_external_id=pv.OBS2_ID)
        == pv.PUBLIC_HANDLE
    )

    # NFC LP equivalence + already-NFC gate for minting
    assert ora.lp(pv.NFC_COMPOSED).hex() == orb.lp(pv.NFC_DECOMPOSED).hex() == pv.LP_CAFE_HEX
    cafe = ora.logical_id(
        project_binding_id="project:convmem:v1",
        source_identity="fixture/source-a",
        authority_site="example.com",
        producer="form-prod",
        logical_key=pv.NFC_COMPOSED,
        subject_kind="finding",
    )
    assert cafe == pv.CAFE_FIND2_ID == orb.logical_id(
        project_binding_id="project:convmem:v1",
        source_identity="fixture/source-a",
        authority_site="example.com",
        producer="form-prod",
        logical_key=pv.NFC_COMPOSED,
        subject_kind="finding",
    )
    try:
        ora.logical_id(
            project_binding_id="project:convmem:v1",
            source_identity="fixture/source-a",
            authority_site="example.com",
            producer="form-prod",
            logical_key=pv.NFC_DECOMPOSED,
            subject_kind="finding",
        )
    except ora.DigestOracleError as exc:
        assert "non_nfc" in str(exc)
    else:
        raise AssertionError("non_nfc_logical_key_accepted")

    # Underscore site rejected before hashing
    try:
        ora.logical_id(
            **{**pv.LOGICAL_COMMON, "authority_site": "bad_host.example"},
            subject_kind="finding",
        )
    except ora.DigestOracleError:
        pass
    else:
        raise AssertionError("underscore_site_accepted")

    # Semantic / payload digests for typed observation with explicit nulls
    rec = dict(pv.TYPED_OBSERVATION_RECORD)
    sem = "sha256:" + ora.sha256_hex(ora.semantic_digest_bytes(rec))
    pay_body = dict(rec)
    pay_body["semantic_sha256"] = sem
    pay = "sha256:" + ora.sha256_hex(ora.payload_digest_bytes(pay_body))
    assert sem == pv.SEMANTIC_SHA256
    assert pay == pv.PAYLOAD_SHA256
    assert "sha256:" + orb.sha256_hex(orb.semantic_digest_bytes(rec)) == pv.SEMANTIC_SHA256
    pay_body_b = dict(rec)
    pay_body_b["semantic_sha256"] = sem
    assert "sha256:" + orb.sha256_hex(orb.payload_digest_bytes(pay_body_b)) == pv.PAYLOAD_SHA256

    # Float / surrogate rejects on strict encode
    try:
        ora.encode_canonical_bytes({"x": 1.5})
    except ora.DigestOracleError as exc:
        assert "float_forbidden" in str(exc)
    else:
        raise AssertionError("float_accepted")

    # Enrollment / publication / activation / grounding / lineage fixtures present
    assert pv.ENROLLMENT_FIXTURE["mode"] == "fixture"
    assert set(pv.PUBLICATION_VARIANTS) == {"serving", "unavailable", "fenced"}
    assert set(pv.ACTIVATION_CONTROL_VARIANTS) == {"turn", "cancel", "status", "revoke"}
    assert pv.BUFFERED_RELEASE_RESULT["schema"] == "convmem.buffered-release.v1"
    assert pv.GROUNDING_BLOB and pv.GROUNDING_ROOT and pv.GROUNDING_EDGE and pv.GROUNDING_OUTPUT
    assert pv.CAPTURE_RECEIPT["receipt_payload_sha256"].startswith("sha256:")
    assert pv.LINEAGE_FORK_INPUTS["join_requires_complete_parent_head_set"] is True
    assert pv.DECLARED_VECTOR_FUTURE_REDS


def test_m2_idna2008_vectors_and_legacy_v1_retention():
    """Parent IDNA2008 vectors via runtime idna; legacy-v1 vectors remain owned elsewhere."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import idna
    from protocol_fixture import pinned_vectors as pv

    assert idna.__version__ == "3.18"
    for row in pv.IDNA2008_VECTORS:
        if row["expect_accept"]:
            got = idna.encode(row["input"], uts46=True, transitional=False, std3_rules=True).decode(
                "ascii"
            )
            assert got == row["expected_ascii"], row["name"]
        else:
            try:
                idna.encode(row["input"], uts46=True, transitional=False, std3_rules=True)
            except idna.IDNAError:
                pass
            else:
                raise AssertionError(f"idna_should_reject:{row['name']}")
    assert "test_site_filter" in pv.LEGACY_V1_NORMALIZE_VECTORS_OWNER


def test_m2_legacy_envelope_bytes_preserved():
    """Bind legacy provenance golden bytes + UUID/commitment into M2 evidence.

    Execution proof remains tests/test_provenance.py (legacy suite); this test
    re-asserts the exact pinned constants without rewriting provenance.py.
    """
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import provenance
    from protocol_fixture import pinned_vectors as pv
    import constants as oc_constants

    assert provenance.SCHEMA_VERSION == "convmem/provenance-envelope-v1"
    assert "test_canonicalization_literal_golden_vector" in pv.LEGACY_PROVENANCE_GOLDEN_TEST
    assert "tests/test_provenance.py" in oc_constants.LEGACY_PYTEST_FILES
    assert pv.LEGACY_PROVENANCE_COMMITMENT == (
        "1849adc132d5d41c1ae3868eaf952b89fd2ccbe3c4373788717e3c34ee6f7418"
    )
    assert pv.LEGACY_PROVENANCE_ASSERTION_UUID == "00000000-0000-4000-8000-000000000001"

    # Same construction as tests/test_provenance.py::test_canonicalization_literal_golden_vector
    root = provenance.root_binding(
        source_identity="fixture/source",
        record_locator="event-1",
        raw_record_sha256=provenance.sha256_hex("raw record"),
        input_view_sha256=provenance.sha256_hex("raw record"),
        origin_class="synthetic",
        origin_assurance="unknown",
        channel_class="unverified",
        channel_locator="unverified://none",
        channel_evidence_sha256=provenance.sha256_hex("no authenticated channel"),
    )
    envelope = provenance.base_envelope(
        assertion_id=pv.LEGACY_PROVENANCE_ASSERTION_UUID,
        root_bindings=[root],
        selection_parameters={"z": "é", "a": 1},
    )
    canonical = provenance.canonical_envelope_bytes(envelope)
    assert canonical.startswith(pv.LEGACY_PROVENANCE_CANONICAL_PREFIX)
    assert provenance.provenance_commitment(envelope) == pv.LEGACY_PROVENANCE_COMMITMENT
    # Domain unchanged: incomplete envelope still rejects.
    try:
        provenance.validate_envelope({"schema": provenance.SCHEMA_VERSION})
    except provenance.EnvelopeValidationError:
        pass
    else:
        raise AssertionError("incomplete_envelope_must_reject")
    text = Path("requirements.txt").read_text(encoding="utf-8")
    assert "idna==3.18" in text


def test_m2_registry_schema_exact_binding_fields():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    data = json.loads(
        Path("schemas/convmem-project-binding-registry-v3.schema.json").read_text(
            encoding="utf-8"
        )
    )
    binding = data["properties"]["bindings"]["items"]
    assert binding["required"] == [
        "id",
        "public_ref",
        "project",
        "domain_root",
        "site_mode",
        "site",
        "non_expanding_roots",
        "source_registrations",
        "lineage_id",
        "capture_issuers",
        "verification_producers",
    ]
    assert "public_binding_ref" not in binding["properties"]
    assert "public_ref" in binding["properties"]
    src = binding["properties"]["source_registrations"]["items"]
    assert src["required"] == [
        "id",
        "source_class",
        "source_identity",
        "identity_match",
        "authorization_domain",
        "site",
        "event_id_resolver",
    ]
    assert src["properties"]["identity_match"] == {"const": "exact"}
    assert src["properties"]["event_id_resolver"] == {"const": "fixture_scan_event_v1"}


def test_m2_protocol_fixture_specimens_present():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    from protocol_fixture.specimens import ROLES, specimen_catalog

    catalog = specimen_catalog()
    assert set(catalog) == set(ROLES)
    root = Path("tests/fixtures/openclaw_strict/protocol_fixture")
    for role in ROLES:
        path = root / f"{role}.specimen.json"
        assert path.is_file(), role
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["artifact_kind"] == "protocol_fixture"
        assert data["role"] == role
        assert "payload" in data
    vectors = root / "known_answer_vectors.json"
    assert vectors.is_file()
    for row in json.loads(vectors.read_text(encoding="utf-8")):
        assert "not a source component hash" in row["note"]
        assert "not authority" in row["note"]


def test_case58_whole_case_not_passed_declared_future_reds():
    """Whole case 58 remains not passed: positive source hashes still future red."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import component_inventory as inv
    import fixture_manifest as fm

    root = Path(".")
    incomplete = [
        name
        for name in ("builder", "strict_server", "supervisor", "controller", "plugin")
        if not inv.source_component_digest_available(root, name)
    ]
    assert set(incomplete) == {
        "builder",
        "strict_server",
        "supervisor",
        "controller",
    }
    assert inv.source_component_digest_available(root, "plugin") is True
    try:
        fm.emit_complete_manifest()
        passed = True
    except fm.ManifestNotAvailable:
        passed = False
    assert passed is False, "case58_complete_manifest_must_stay_red"
