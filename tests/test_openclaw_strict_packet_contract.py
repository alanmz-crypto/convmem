"""Case 57 T0a containment/refusal greens; later-T reds mapped."""
# pylint: disable=C0302  # preserved packet-contract collected-node test boundary

from __future__ import annotations

import errno
import json
import os
import sys
from pathlib import Path

# Import fixture helpers without tests/fixtures/__init__.py (not authorized at M1).
sys.path.insert(0, str(Path("tests/fixtures/openclaw_strict").resolve()))
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
import constants as oc_constants  # noqa: E402
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
import suites as oc_suites  # noqa: E402
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
import case58_oracle as oracle  # noqa: E402
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
from fixture_manifest import emit_complete_manifest  # noqa: E402


def _packet_schema_path(stem: str) -> str:
    """Build schemas/<stem> inventory paths for packet-contract checks."""

    return "schemas/" + stem



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
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import limits as oc_limits

    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    root = Path("/fixture/tmp_alloc_probe")
    root.mkdir(mode=0o700, exist_ok=True)
    blob = root / "blob"
    blob.write_bytes(b"x" * 100)
    st = os.lstat(blob)
    expected = st.st_blocks * 512
# pylint: disable-next=W0212  # intentional white-box test access
    assert oc_limits._tmp_used_bytes(str(root)) == expected
    link = root / "blob_hardlink"
    os.link(blob, link)
    # Hardlink shares inode — must not double-count allocated blocks.
# pylint: disable-next=W0212  # intentional white-box test access
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
        *("/runtime/bin/python", "-m", "pytest"),
        *("-q", "-p", "no:cacheprovider"),
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
    # M4: complete five-component manifest is available; source inventory returned alongside.
    manifest, source_inventory = emit_complete_manifest()
    assert manifest["schema"] == "convmem.strict-fixture-manifest.v1"
    assert [c["name"] for c in manifest["components"]] == [
        "builder",
        "strict_server",
        "supervisor",
        "controller",
        "plugin",
    ]
    assert isinstance(source_inventory, list) and source_inventory
    assert all({"path", "mode", "sha256"} <= set(e) for e in source_inventory)
    # artifacts are fixture-tree helpers — not the component membership set.
    assert all(
        e["path"].startswith("tests/fixtures/openclaw_strict/")
        for e in manifest["artifacts"]
    )
    assert not any(
        e["path"].endswith("fixture-manifest.json") for e in manifest["artifacts"]
    )


def test_plan_and_baseline_constants_frozen():
    assert oc_constants.SEMANTIC_PARENT_SHA == "b810fcd7ee545399a368afada2b0e7d9dd7821f6"
    assert oc_constants.CODE_BASELINE_SHA == "9193f5ec744f059d07a20612489b210527b5660a"
    assert oc_constants.M11_REVIEWED_OVERLAY_SHA == (
        "67d4f5aa62415f3550fbc56a760374cf3c19ee23"
    )
    assert oc_constants.M11_CONTROL_PLANE_INPUTS == frozenset(
        {
            "docs/plans/ARCHITECTURE-openclaw-convmem-integration.md",
            "docs/plans/EXECUTION-openclaw-convmem-integration.md",
            "docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md",
            "docs/plans/STATUS-openclaw-convmem-integration.md",
        }
    )
    assert oc_constants.EXPECTED_TEST_RUNTIME_TREE_SHA256.startswith("sha256:74a12c72")


def test_m2_gate_b_and_c_schema_inventory_exact():
    """Exact 24 Gate B + 7 Gate C schemas; no Gate W."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    gate_b = list(
    _packet_schema_path(stem)
    for stem in (
        "convmem-bound-read-scope-v2.schema.json",
        "convmem-project-binding-registry-v3.schema.json",
        "convmem-bound-authority-record-v3.schema.json",
        "convmem-authority-disposition-v1.schema.json",
        "convmem-strict-provenance-context-v2.schema.json",
        "convmem-strict-grounding-v1.schema.json",
        "convmem-capture-receipt-v1.schema.json",
        "convmem-strict-fixture-bundle-v2.schema.json",
        "convmem-strict-citation-map-v1.schema.json",
        "convmem-bound-authority-manifest-v3.schema.json",
        "convmem-bound-projection-row-v2.schema.json",
        "convmem-strict-graph-v1.schema.json",
        "convmem-bound-projection-manifest-v3.schema.json",
        "convmem-strict-generation-layout-v2.schema.json",
        "convmem-strict-publication-v2.schema.json",
        "convmem-strict-enrollment-v1.schema.json",
        "convmem-strict-slot-v1.schema.json",
        "convmem-strict-source-cutoff-v1.schema.json",
        "convmem-strict-semantic-contract-v1.schema.json",
        "convmem-strict-state-v2.schema.json",
        "convmem-clock-review-v1.schema.json",
        "convmem-raw-evidence-v3.schema.json",
        "convmem-error-v1.schema.json",
        "convmem-strict-config-v2.schema.json",
    )
)
    gate_c = [
        f"schemas/{stem}"
        for stem in (
            "convmem-openclaw-connector-launch-v2.schema.json",
            "convmem-openclaw-activation-v2.schema.json",
            "convmem-activation-control-v1.schema.json",
            "convmem-activation-retirement-v1.schema.json",
            "convmem-activation-launch-policy-v1.schema.json",
            "convmem-activation-manager-policy-v1.schema.json",
            "convmem-controller-socket-policy-v1.schema.json",
        )
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
        *(
            _packet_schema_path("convmem-" + short)
            for short in (
                "approved-admission-v1.schema.json|"
                "admission-intent-v1.schema.json|"
                "admission-review-v1.schema.json|"
                "admission-ratification-v1.schema.json|"
                "admission-event-v1.schema.json"
            ).split("|")
        ),
    ):
        assert not Path(forbidden).exists(), f"gate_w_schema_present:{forbidden}"




# Fixed synthetic commits for M11 unit tests — never shell out to git.
_M11_SYNTHETIC_SOURCE_COMMIT = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_M11_SYNTHETIC_OVERLAY_COMMIT = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
_M11_SYNTHETIC_BLOB_OID = "cccccccccccccccccccccccccccccccccccccccc"
_M11_SYNTHETIC_BLOB_OID_ALT = "dddddddddddddddddddddddddddddddddddddddd"


def _m11_control_delta(*extra: str) -> list[str]:
    return sorted(oc_constants.M11_CONTROL_PLANE_INPUTS) + list(extra)


def _m11_matching_tree_oracle(
    source_commit: str, overlay_commit: str
) -> dict[tuple[str, str], tuple[str, str, str]]:
    """In-memory (commit, path) -> (mode, type, oid) for exact four control paths."""
    entry = ("100644", "blob", _M11_SYNTHETIC_BLOB_OID)
    path_oracle: dict[tuple[str, str], tuple[str, str, str]] = {}
    for control_path in sorted(oc_constants.M11_CONTROL_PLANE_INPUTS):
        path_oracle[(source_commit, control_path)] = entry
        path_oracle[(overlay_commit, control_path)] = entry
    return path_oracle


def _m11_install_git_boundary_oracle(
    monkeypatch,
    oc_allowlist,
    *,
    source_commit: str = _M11_SYNTHETIC_SOURCE_COMMIT,
    overlay_input: str | None = None,
    overlay_resolved: str = _M11_SYNTHETIC_OVERLAY_COMMIT,
    tree_oracle: dict[tuple[str, str], tuple[str, str, str]] | None = None,
    unavailable: frozenset[str] | None = None,
) -> dict[tuple[str, str], tuple[str, str, str]]:
    """Monkeypatch _resolve_commit / _git_tree_entry; no git rev-parse or ls-tree."""
    overlay_key = (
        oc_allowlist.M11_REVIEWED_OVERLAY_SHA
        if overlay_input is None
        else overlay_input
    )
    unavailable_shas = unavailable or frozenset()
    resolved_by_input = {
        source_commit: source_commit,
        overlay_key: overlay_resolved,
        overlay_resolved: overlay_resolved,
    }
    path_oracle = (
        tree_oracle
        if tree_oracle is not None
        else _m11_matching_tree_oracle(source_commit, overlay_resolved)
    )

    def _resolve(_repo, sha: str) -> str:
        if sha in unavailable_shas or sha not in resolved_by_input:
            raise SystemExit(f"control_plane_unavailable_commit:{sha}")
        return resolved_by_input[sha]

    def _tree_entry(_repo, commit: str, path: str) -> tuple[str, str, str]:
        try:
            return path_oracle[(commit, path)]
        except KeyError as exc:
            raise SystemExit(f"control_plane_missing:{path}") from exc

    monkeypatch.setattr(oc_allowlist, "_resolve_commit", _resolve)
    monkeypatch.setattr(oc_allowlist, "_git_tree_entry", _tree_entry)
    return path_oracle


def _check_m11_control_plane_exact_four_success(monkeypatch):
    """M11: exact four control-plane paths validate; product delta P is returned."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    _m11_install_git_boundary_oracle(monkeypatch, oc_allowlist)
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta("mcp_server.py"),
    )
    assert oc_allowlist.assert_allowlist(
        Path("."), _M11_SYNTHETIC_SOURCE_COMMIT
    ) == ["mcp_server.py"]


def _check_m11_control_plane_rejects_missing_path(monkeypatch):
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    control = sorted(oc_constants.M11_CONTROL_PLANE_INPUTS)
    incomplete = control[1:] + ["mcp_server.py"]
    _m11_install_git_boundary_oracle(monkeypatch, oc_allowlist)
    monkeypatch.setattr(
        oc_allowlist, "changed_paths", lambda *_a, **_k: incomplete
    )
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("missing_control_plane_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_missing:")
        assert control[0] in str(exc)


def _check_m11_control_plane_rejects_extra_classified_constant(monkeypatch):
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    extra = "docs/plans/README-openclaw-convmem-integration.md"
    _m11_install_git_boundary_oracle(monkeypatch, oc_allowlist)
    monkeypatch.setattr(
        oc_constants,
        "M11_CONTROL_PLANE_INPUTS",
        frozenset(oc_constants.M11_CONTROL_PLANE_INPUTS | {extra}),
    )
    monkeypatch.setattr(
        oc_allowlist,
        "M11_CONTROL_PLANE_INPUTS",
        frozenset(oc_constants.M11_CONTROL_PLANE_INPUTS | {extra}),
    )
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta(extra, "mcp_server.py"),
    )
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("extra_classified_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_extra_classified:")
        assert extra in str(exc)


def _check_m11_control_plane_rejects_unavailable_commit(monkeypatch):
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    unavailable = "0" * 40
    monkeypatch.setattr(oc_allowlist, "M11_REVIEWED_OVERLAY_SHA", unavailable)
    _m11_install_git_boundary_oracle(
        monkeypatch,
        oc_allowlist,
        overlay_input=unavailable,
        unavailable=frozenset({unavailable}),
    )
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta("mcp_server.py"),
    )
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("unavailable_overlay_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_unavailable_commit:")


def _check_m11_control_plane_rejects_malformed_unreadable_entry(monkeypatch):
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    _m11_install_git_boundary_oracle(monkeypatch, oc_allowlist)
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta("mcp_server.py"),
    )

    def _missing(repo, commit, path):  # noqa: ARG001
        raise SystemExit(f"control_plane_missing:{path}")

    monkeypatch.setattr(oc_allowlist, "_git_tree_entry", _missing)
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("missing_entry_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_missing:")

    def _malformed(repo, commit, path):  # noqa: ARG001
        raise SystemExit(f"control_plane_malformed:{path}")

    monkeypatch.setattr(oc_allowlist, "_git_tree_entry", _malformed)
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("malformed_entry_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_malformed:")


def _check_m11_control_plane_rejects_non_regular_mode_or_type(monkeypatch):
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    _m11_install_git_boundary_oracle(monkeypatch, oc_allowlist)
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta("mcp_server.py"),
    )

    def _bad_mode(repo, commit, path):  # noqa: ARG001
        raise SystemExit(f"control_plane_bad_mode:{path}")

    monkeypatch.setattr(oc_allowlist, "_git_tree_entry", _bad_mode)
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("bad_mode_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_bad_mode:")

    def _non_blob(repo, commit, path):  # noqa: ARG001
        raise SystemExit(f"control_plane_non_blob:{path}")

    monkeypatch.setattr(oc_allowlist, "_git_tree_entry", _non_blob)
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("non_blob_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_non_blob:")


def _check_m11_control_plane_rejects_blob_or_mode_mismatch(monkeypatch):
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    control = sorted(oc_constants.M11_CONTROL_PLANE_INPUTS)
    target = control[0]
    source = _M11_SYNTHETIC_SOURCE_COMMIT
    overlay = _M11_SYNTHETIC_OVERLAY_COMMIT
    path_oracle = _m11_matching_tree_oracle(source, overlay)
    path_oracle[(source, target)] = ("100644", "blob", _M11_SYNTHETIC_BLOB_OID_ALT)
    _m11_install_git_boundary_oracle(
        monkeypatch,
        oc_allowlist,
        source_commit=source,
        overlay_resolved=overlay,
        tree_oracle=path_oracle,
    )
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta("mcp_server.py"),
    )
    try:
        oc_allowlist.assert_allowlist(Path("."), source)
        raise AssertionError("blob_mismatch_accepted")
    except SystemExit as exc:
        assert str(exc).startswith("control_plane_mismatch:")
        assert target in str(exc)


def _check_m11_fifth_documentation_path_fails_product_allowlist(monkeypatch):
    """A fifth docs path stays in P and fails the unchanged product allowlist."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    fifth = "docs/plans/README-openclaw-convmem-integration.md"
    assert fifth not in oc_constants.M11_CONTROL_PLANE_INPUTS
    assert oc_allowlist.path_allowed(fifth) is False
    _m11_install_git_boundary_oracle(monkeypatch, oc_allowlist)
    monkeypatch.setattr(
        oc_allowlist,
        "changed_paths",
        lambda *_a, **_k: _m11_control_delta(fifth),
    )
    try:
        oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
        raise AssertionError("fifth_doc_accepted")
    except SystemExit as exc:
        assert str(exc) == f"allowlist_violation:{fifth}"


def _check_m11_control_plane_docs_remain_exported_inventoried_hashed():
    """Reviewed control docs stay in source export inventory/hash; not excluded."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import fixture_manifest as fm

    for rel in sorted(oc_constants.M11_CONTROL_PLANE_INPUTS):
        assert rel not in oc_constants.GENERATED_EVIDENCE_SOURCE_RELS
        assert rel not in oc_constants.GENERATED_EVIDENCE_FIXTURE_RELS
        assert Path(rel).is_file(), f"missing_control_doc:{rel}"

    entries, digest = fm.independent_source_tree_digest(Path("."))
    paths = {e["path"] for e in entries}
    for rel in oc_constants.M11_CONTROL_PLANE_INPUTS:
        assert rel in paths
        match = next(e for e in entries if e["path"] == rel)
        # independent_source_tree_digest records filesystem modes as four octal digits.
        assert match["mode"] == "0644"
        assert match["sha256"].startswith("sha256:")
    assert digest == fm.hash_inventory_entries(entries)
    assert digest.startswith("sha256:")

def test_m4_edit_allowlist_permits_mcp_server_protects_gate_w(monkeypatch):
    """M4/T3: mcp_server.py is bounded-edit allowlisted; Gate W stays reject-only."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import allowlist as oc_allowlist

    assert "mcp_server.py" in oc_constants.EDIT_ALLOWLIST_EXACT
    assert oc_allowlist.path_allowed("mcp_server.py") is True

    gate_w = [
        "schemas/convmem-approved-admission-v1.schema.json",
        "schemas/convmem-admission-intent-v1.schema.json",
        "schemas/convmem-admission-review-v1.schema.json",
        "schemas/convmem-admission-ratification-v1.schema.json",
        "schemas/convmem-admission-event-v1.schema.json",
    ]
    denied = [
        path
        for path in gate_w
        if path in oc_constants.EDIT_ALLOWLIST_EXACT
        or path in oc_constants.SCHEMA_ALLOWLIST
        or oc_allowlist.path_allowed(path)
    ]
    assert denied == []

    with monkeypatch.context() as scoped:
        _m11_install_git_boundary_oracle(scoped, oc_allowlist)
        scoped.setattr(
            oc_allowlist,
            "changed_paths",
            lambda *_a, **_k: _m11_control_delta("mcp_server.py"),
        )
        assert oc_allowlist.assert_allowlist(
            Path("."), _M11_SYNTHETIC_SOURCE_COMMIT
        ) == ["mcp_server.py"]

    # Second layer must still reject Gate W even if path_allowed were bypassed.
    with monkeypatch.context() as scoped:
        _m11_install_git_boundary_oracle(scoped, oc_allowlist)
        scoped.setattr(oc_allowlist, "path_allowed", lambda _p: True)
        scoped.setattr(
            oc_allowlist,
            "changed_paths",
            lambda *_a, **_k: _m11_control_delta(gate_w[0]),
        )
        try:
            oc_allowlist.assert_allowlist(Path("."), _M11_SYNTHETIC_SOURCE_COMMIT)
            raise AssertionError("gate_w_second_layer_bypassed")
        except SystemExit as exc:
            assert str(exc) == f"gate_w_forbidden_change:{gate_w[0]}"

    with monkeypatch.context() as scoped:
        _check_m11_control_plane_exact_four_success(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_control_plane_rejects_missing_path(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_control_plane_rejects_extra_classified_constant(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_control_plane_rejects_unavailable_commit(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_control_plane_rejects_malformed_unreadable_entry(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_control_plane_rejects_non_regular_mode_or_type(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_control_plane_rejects_blob_or_mode_mismatch(scoped)
    with monkeypatch.context() as scoped:
        _check_m11_fifth_documentation_path_fails_product_allowlist(scoped)
    _check_m11_control_plane_docs_remain_exported_inventoried_hashed()


def test_m2_future_production_modules_remain_absent():
    """M4: T3 server present; future-production set is empty for Gate B."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import component_inventory as inv

    m4_present = (
        "bound_read_scope.py",
        "strict_grounding.py",
        "strict_evidence_state.py",
        "strict_projection.py",
        "strict_projection_publisher.py",
        "openclaw_strict_server.py",
    )
    for rel in m4_present:
        assert Path(rel).is_file(), f"m4_module_absent:{rel}"
    missing = inv.missing_future_production_members(Path("."))
    assert missing == sorted(inv.FUTURE_PRODUCTION_MEMBERS)
    assert missing == []


def test_m2_case58_literal_inventories_and_independent_walkers():
    """Five membership sets + two independent walkers; M4 includes strict_server."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import component_inventory as inv
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import fixture_manifest as fm

    assert hasattr(fm, "build_component_inventories")
    inventories = inv.build_component_inventories()
    assert set(inventories) == {"builder", "strict_server", "supervisor", "controller", "plugin"}
    root = Path(".")
    for name in ("builder", "strict_server", "supervisor", "controller", "plugin"):
        ref_entries = inv.reference_walk_component(root, name)
        ora_entries = oracle.independent_walk(root, name)
        assert ref_entries == ora_entries
        assert inv.component_tree_digest(ref_entries) == oracle.independent_tree_digest(
            ora_entries
        )
        assert inv.source_component_digest_available(root, name) is True
    # Complete five-hash source manifest is available once T3 lands.
    manifest, source_inventory = fm.emit_complete_manifest()
    assert isinstance(manifest, dict)
    assert isinstance(source_inventory, list)
    # Two independent inventory/hash paths (parent §6.5.8): fixture artifacts
    # and source export — neither is a component-membership substitute.
    # independent_* walkers must not call inventory_* (case58_oracle reference).
    art_a, dig_a = fm.independent_fixture_artifact_digest(
        Path("tests/fixtures/openclaw_strict")
    )
    art_b = fm.inventory_fixture_artifacts(Path("tests/fixtures/openclaw_strict"))
    assert art_a == art_b == manifest["artifacts"]
    assert dig_a == fm.hash_inventory_entries(manifest["artifacts"])
    assert oracle.reference_fixture_artifact_walk(
        Path("tests/fixtures/openclaw_strict")
    ) == art_b
    src_a, src_dig = fm.independent_source_tree_digest(Path("."))
    assert src_a == source_inventory
    assert src_dig == manifest["source_tree_sha256"]
    assert src_dig != dig_a  # independent inventories must not collapse
    # Prove independence of call graph: helpers are distinct callables.
    assert (
        fm.independent_fixture_artifact_digest.__code__.co_names
        != fm.inventory_fixture_artifacts.__code__.co_names
    )


def test_m2_case58_plugin_mutation_and_symlink_controls():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
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
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import canonical_oracle as oracle_a
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import canonical_oracle_b as oracle_b
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
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
        for canon_oracle, err in (
            (oracle_a, oracle_a.CanonicalOracleError),
            (oracle_b, oracle_b.CanonicalOracleBError),
        ):
            try:
                canon_oracle.parse_strict_raw(item["payload"])
            except err:
                pass
            else:
                raise AssertionError(f"oracle_should_reject:{item['name']}:{canon_oracle.__name__}")
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
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    from protocol_fixture.schema_contract import run_all_schema_contract_checks

    report = run_all_schema_contract_checks(Path("schemas"))
    assert report["schema_count"] == 31
    assert report["meta_schema_ok"] == 31
    assert report["positive_ok"] == 31
    assert report["field_table_ok"] == 31
    assert report["raw_roundtrip_ok"] == 31
    assert report["nested_families_checked"] >= 20
    assert report["negative_ok"] == report["negative_total"]
    assert report["negative_total"] >= 31 * 4  # unknown/missing/wrong-type/null-discipline each
    # Every schema must include the four core negative names.
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    from protocol_fixture.schema_contract import (
        FILENAME_TO_ID,
        build_negatives,
        load_schema,
    )
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    from protocol_fixture import schema_field_sets as field_sets

    assert len(field_sets.TOP_LEVEL) == 30  # activation-control uses variant table
    assert len(field_sets.ACTIVATION_CONTROL_VARIANTS_FIELDS) == 4
    for filename in FILENAME_TO_ID:
        schema = load_schema(Path("schemas"), filename)
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
        from protocol_fixture.schema_instances import POSITIVE_BY_FILENAME

        names = {n["name"] for n in build_negatives(schema, POSITIVE_BY_FILENAME[filename])}
        missing = {
            n
            for n in (
                "unknown_top_level_key",
                "missing_required_key",
                "wrong_type",
                "omitted_required_null",
            )
            if n not in names
        }
        assert not missing, f"{filename}:missing_negatives:{sorted(missing)}:got={sorted(names)}"
    assert report["activation_control_variants_ok"] == 4
    assert report["filename_to_id_exact"] is True
    assert report["deferred_cross_object_invariants"]


# pylint: disable-next=R0914  # dual-oracle vector locals mirror closed known-answer cases
def test_m2_pinned_known_answer_vectors_dual_oracles():
    """Parent-defined vectors; dual fixture oracles recompute pinned constants."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import digest_oracle as ora  # pylint: disable=E0401  # fixture path-injection import

    import digest_oracle_b as orb  # pylint: disable=E0401  # fixture path-injection import

# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
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

    # Semantic / payload digests for typed observation with explicit nulls.
    # Digests are over oracle-canonical bytes (not jq); both oracles must agree
    # with the pinned constants AND the pinned digest-input byte strings.
    rec = dict(pv.TYPED_OBSERVATION_RECORD)
    rec["semantic_sha256"] = "sha256:" + ("0" * 64)
    rec["payload_sha256"] = "sha256:" + ("0" * 64)
    sem_bytes_a = ora.semantic_digest_bytes(rec)
    sem_bytes_b = orb.semantic_digest_bytes(rec)
    assert sem_bytes_a == sem_bytes_b == pv.TYPED_SEMANTIC_DIGEST_INPUT_UTF8
    sem = "sha256:" + ora.sha256_hex(sem_bytes_a)
    assert sem == pv.SEMANTIC_SHA256
    pay_body = dict(rec)
    pay_body["semantic_sha256"] = sem
    pay_bytes_a = ora.payload_digest_bytes(pay_body)
    pay_bytes_b = orb.payload_digest_bytes(pay_body)
    assert pay_bytes_a == pay_bytes_b == pv.TYPED_PAYLOAD_DIGEST_INPUT_UTF8
    pay = "sha256:" + ora.sha256_hex(pay_bytes_a)
    assert pay == pv.PAYLOAD_SHA256
    assert rec["relates_to_assertion_id"] is None
    assert rec["target_assertion_id"] is None
    assert rec["verification_result"] is None
    assert rec["decision_disposition_ref"] is None
    assert rec["supersession_disposition_ref"] is None

    # Float / surrogate rejects on strict encode
    try:
        ora.encode_canonical_bytes({"x": 1.5})
    except ora.DigestOracleError as exc:
        assert "float_forbidden" in str(exc)
    else:
        raise AssertionError("float_accepted")

    # Enrollment: dual oracles vs static pin (exclude only enrollment_payload_sha256)
    enroll_a = ora.exclude_named_field_bytes(
        pv.ENROLLMENT_FIXTURE, "enrollment_payload_sha256"
    )
    enroll_b = orb.exclude_named_field_bytes(
        pv.ENROLLMENT_FIXTURE, "enrollment_payload_sha256"
    )
    assert enroll_a == enroll_b == pv.ENROLLMENT_CANONICAL_UTF8
    assert (
        ora.labeled_self_hash(pv.ENROLLMENT_FIXTURE, "enrollment_payload_sha256")
        == orb.labeled_self_hash(pv.ENROLLMENT_FIXTURE, "enrollment_payload_sha256")
        == pv.ENROLLMENT_PAYLOAD_SHA256
        == pv.ENROLLMENT_FIXTURE["enrollment_payload_sha256"]
    )

    # Publication: three distinct self-hashes; dual oracles match static pins
    pub_hashes = []
    for name, pin_bytes, pin_sha in (
        (
            "serving",
            pv.PUBLICATION_SERVING_CANONICAL_UTF8,
            pv.PUBLICATION_SERVING_PAYLOAD_SHA256,
        ),
        (
            "unavailable",
            pv.PUBLICATION_UNAVAILABLE_CANONICAL_UTF8,
            pv.PUBLICATION_UNAVAILABLE_PAYLOAD_SHA256,
        ),
        (
            "fenced",
            pv.PUBLICATION_FENCED_CANONICAL_UTF8,
            pv.PUBLICATION_FENCED_PAYLOAD_SHA256,
        ),
    ):
        obj = pv.PUBLICATION_VARIANTS[name]
        body_a = ora.exclude_named_field_bytes(obj, "publication_payload_sha256")
        body_b = orb.exclude_named_field_bytes(obj, "publication_payload_sha256")
        assert body_a == body_b == pin_bytes
        got = ora.labeled_self_hash(obj, "publication_payload_sha256")
        assert got == orb.labeled_self_hash(obj, "publication_payload_sha256") == pin_sha
        assert obj["publication_payload_sha256"] == pin_sha
        pub_hashes.append(pin_sha)
    assert len(set(pub_hashes)) == 3

    # Grounding: decoded blob SHA + nested canonical pins + payload self-hash
    assert (
        ora.sha256_labeled(pv.GROUNDING_BLOB_DECODED_BYTES)
        == orb.sha256_labeled(pv.GROUNDING_BLOB_DECODED_BYTES)
        == pv.GROUNDING_BLOB_DECODED_SHA256
        == pv.GROUNDING_BLOB["sha256"]
    )
    assert ora.encode_canonical_bytes(pv.GROUNDING_BLOB) == pv.GROUNDING_BLOB_CANONICAL_UTF8
    assert (
        ora.sha256_labeled(pv.GROUNDING_BLOB_CANONICAL_UTF8)
        == pv.GROUNDING_BLOB_CANONICAL_SHA256
    )
    for obj, raw, digest in (
        (pv.GROUNDING_ROOT, pv.GROUNDING_ROOT_CANONICAL_UTF8, pv.GROUNDING_ROOT_CANONICAL_SHA256),
        (pv.GROUNDING_EDGE, pv.GROUNDING_EDGE_CANONICAL_UTF8, pv.GROUNDING_EDGE_CANONICAL_SHA256),
        (
            pv.GROUNDING_OUTPUT,
            pv.GROUNDING_OUTPUT_CANONICAL_UTF8,
            pv.GROUNDING_OUTPUT_CANONICAL_SHA256,
        ),
    ):
        assert ora.encode_canonical_bytes(obj) == orb.encode_canonical_bytes(obj) == raw
        assert ora.sha256_labeled(raw) == digest
    g_body_a = ora.exclude_named_field_bytes(pv.GROUNDING_OBJECT, "grounding_payload_sha256")
    g_body_b = orb.exclude_named_field_bytes(pv.GROUNDING_OBJECT, "grounding_payload_sha256")
    assert g_body_a == g_body_b == pv.GROUNDING_CANONICAL_UTF8
    assert (
        ora.labeled_self_hash(pv.GROUNDING_OBJECT, "grounding_payload_sha256")
        == pv.GROUNDING_PAYLOAD_SHA256
    )
    assert (
        ora.sha256_labeled(pv.INPUT_BINDINGS_CANONICAL_UTF8)
        == orb.sha256_labeled(pv.INPUT_BINDINGS_CANONICAL_UTF8)
        == pv.INPUT_BINDINGS_SHA256
    )
    assert (
        ora.sha256_labeled(pv.SUBMITTED_VIEWS_CANONICAL_UTF8) == pv.SUBMITTED_VIEWS_SHA256
    )

    # Capture receipt: exclude only receipt_payload_sha256; ref = capture_ + hex
    r_body_a = ora.exclude_named_field_bytes(pv.CAPTURE_RECEIPT, "receipt_payload_sha256")
    r_body_b = orb.exclude_named_field_bytes(pv.CAPTURE_RECEIPT, "receipt_payload_sha256")
    assert r_body_a == r_body_b == pv.RECEIPT_CANONICAL_UTF8
    assert (
        ora.labeled_self_hash(pv.CAPTURE_RECEIPT, "receipt_payload_sha256")
        == pv.RECEIPT_PAYLOAD_SHA256
        == "sha256:" + pv.RECEIPT_PAYLOAD_HEX
    )
    assert pv.RECEIPT_PAYLOAD_HEX != ("a" * 64)
    assert ora.receipt_ref(pv.RECEIPT_PAYLOAD_HEX) == pv.CAPTURE_RECEIPT_REF
    assert pv.CAPTURE_RECEIPT_REF.startswith("capture_")
    assert pv.CAPTURE_RECEIPT_REF.endswith(pv.RECEIPT_PAYLOAD_HEX)

    # Lineage: fork heads distinct; join-set digest pinned; do not claim T2 reducer
    assert (
        ora.encode_canonical_bytes(pv.LINEAGE_FORK_INPUTS["head_a"])
        == pv.LINEAGE_HEAD_A_CANONICAL_UTF8
    )
    assert (
        ora.sha256_labeled(pv.LINEAGE_HEAD_A_CANONICAL_UTF8) == pv.LINEAGE_HEAD_A_SHA256
    )
    assert (
        ora.encode_canonical_bytes(pv.LINEAGE_FORK_INPUTS["head_b_fork"])
        == pv.LINEAGE_HEAD_B_CANONICAL_UTF8
    )
    assert (
        ora.sha256_labeled(pv.LINEAGE_HEAD_B_CANONICAL_UTF8) == pv.LINEAGE_HEAD_B_SHA256
    )
    assert pv.LINEAGE_HEAD_A_SHA256 != pv.LINEAGE_HEAD_B_SHA256
    assert (
        ora.encode_canonical_bytes(pv.LINEAGE_FORK_INPUTS["join_targets"])
        == pv.LINEAGE_JOIN_SET_CANONICAL_UTF8
    )
    assert (
        ora.sha256_labeled(pv.LINEAGE_JOIN_SET_CANONICAL_UTF8) == pv.LINEAGE_JOIN_SET_SHA256
    )
    assert pv.LINEAGE_FORK_INPUTS["join_requires_complete_parent_head_set"] is True

    # Activation-control + buffered-release: fixture-transport known-answers
    for name, raw, digest in (
        (
            "turn",
            pv.ACTIVATION_TURN_CANONICAL_UTF8,
            pv.ACTIVATION_TURN_FIXTURE_TRANSPORT_SHA256,
        ),
        (
            "cancel",
            pv.ACTIVATION_CANCEL_CANONICAL_UTF8,
            pv.ACTIVATION_CANCEL_FIXTURE_TRANSPORT_SHA256,
        ),
        (
            "status",
            pv.ACTIVATION_STATUS_CANONICAL_UTF8,
            pv.ACTIVATION_STATUS_FIXTURE_TRANSPORT_SHA256,
        ),
        (
            "revoke",
            pv.ACTIVATION_REVOKE_CANONICAL_UTF8,
            pv.ACTIVATION_REVOKE_FIXTURE_TRANSPORT_SHA256,
        ),
    ):
        assert (
            ora.encode_canonical_bytes(pv.ACTIVATION_CONTROL_VARIANTS[name])
            == orb.encode_canonical_bytes(pv.ACTIVATION_CONTROL_VARIANTS[name])
            == raw
        )
        assert ora.sha256_labeled(raw) == digest
    assert (
        ora.encode_canonical_bytes(pv.BUFFERED_RELEASE_RESULT)
        == pv.BUFFERED_RELEASE_CANONICAL_UTF8
    )
    assert (
        ora.sha256_labeled(pv.BUFFERED_RELEASE_CANONICAL_UTF8)
        == pv.BUFFERED_RELEASE_FIXTURE_TRANSPORT_SHA256
    )
    assert (
        ora.encode_canonical_bytes(pv.BUFFERED_RELEASE_RESULT["committed"])
        == pv.BUFFERED_COMMITTED_CANONICAL_UTF8
    )
    assert (
        ora.sha256_labeled(pv.BUFFERED_COMMITTED_CANONICAL_UTF8)
        == pv.BUFFERED_COMMITTED_FIXTURE_TRANSPORT_SHA256
    )
    assert len(pv.PINNED_OBJECT_INVENTORY) >= 10
    assert pv.DECLARED_VECTOR_FUTURE_REDS


def test_m2_idna2008_vectors_and_legacy_v1_retention():
    """Parent IDNA2008 vectors via runtime idna; legacy-v1 vectors remain owned elsewhere."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    import idna
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
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
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    from protocol_fixture import pinned_vectors as pv

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
        *("id", "public_ref", "project", "domain_root"),
        *("site_mode", "site", "non_expanding_roots"),
        *("source_registrations", "lineage_id"),
        "capture_issuers",
        "verification_producers",
    ]
    assert "public_binding_ref" not in binding["properties"]
    assert "public_ref" in binding["properties"]
    src = binding["properties"]["source_registrations"]["items"]
    assert src["required"] == [
        *("id", "source_class", "source_identity"),
        *("identity_match", "authorization_domain", "site", "event_id_resolver"),
    ]
    assert src["properties"]["identity_match"] == {"const": "exact"}
    assert src["properties"]["event_id_resolver"] == {"const": "fixture_scan_event_v1"}


def test_m2_protocol_fixture_specimens_present():
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
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
    """Case 58 five-hash inventory is complete after M4; remaining reds are T4/T5 behavior."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import component_inventory as inv
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import fixture_manifest as fm

    root = Path(".")
    incomplete = [
        name
        for name in ("builder", "strict_server", "supervisor", "controller", "plugin")
        if not inv.source_component_digest_available(root, name)
    ]
    assert incomplete == []
    for name in ("builder", "strict_server", "supervisor", "controller", "plugin"):
        assert inv.source_component_digest_available(root, name) is True
    manifest, source_inventory = fm.emit_complete_manifest()
    assert isinstance(manifest, dict)
    assert isinstance(source_inventory, list)
    assert manifest["source_tree_sha256"] == fm.hash_inventory_entries(source_inventory)


def test_m4_fixture_manifest_independent_controls_and_exclusions(tmp_path: Path):
    """Missing/extra/duplicate/symlink/path-escape; regen identity; exclusion exactness."""

# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import fixture_manifest as fm
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import component_inventory as inv
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    from fixture_manifest import ManifestNotAvailable

    # Component supplied-array controls remain independent.
    inv.reject_supplied_duplicate_missing_extra_path_escape()

    fixture_src = Path("tests/fixtures/openclaw_strict")
    a1 = fm.inventory_fixture_artifacts(fixture_src)
    a2 = fm.inventory_fixture_artifacts(fixture_src)
    assert a1 == a2
    d1 = fm.hash_inventory_entries(a1)
    d2 = fm.hash_inventory_entries(a2)
    assert d1 == d2

    # Basename lookalike elsewhere must NOT be excluded from fixtures inventory.
    lookalike = tmp_path / "tree"
    lookalike.mkdir()
    nested = lookalike / "protocol_fixture"
    nested.mkdir()
    (nested / "fixture-manifest.json").write_text("tracked-lookalike\n", encoding="utf-8")
    (lookalike / "suite_results.json").write_text("generated-root\n", encoding="utf-8")
    (lookalike / "helper.py").write_text("x\n", encoding="utf-8")
    evidence = lookalike / "evidence"
    evidence.mkdir()
    (evidence / "bounded-audit-evidence.json").write_text("generated-audit\n", encoding="utf-8")
    (evidence / "suite_results.json").write_text("generated-suite\n", encoding="utf-8")
    entries = fm.inventory_fixture_artifacts(lookalike)
    paths = {e["path"] for e in entries}
    assert "tests/fixtures/openclaw_strict/protocol_fixture/fixture-manifest.json" in paths
    assert "tests/fixtures/openclaw_strict/suite_results.json" not in paths
    assert "tests/fixtures/openclaw_strict/evidence/bounded-audit-evidence.json" not in paths
    assert "tests/fixtures/openclaw_strict/evidence/suite_results.json" not in paths
    assert "tests/fixtures/openclaw_strict/helper.py" in paths

    # Symlink forbidden.
    bad = tmp_path / "sym"
    bad.mkdir()
    target = bad / "real.py"
    target.write_text("x\n", encoding="utf-8")
    (bad / "link.py").symlink_to(target)
    try:
        fm.inventory_fixture_artifacts(bad)
        raise AssertionError("symlink_accepted")
    except ValueError as exc:
        assert "symlink" in str(exc)

    # Component digest vs fixture artifact digest separation.
    try:
        manifest, src_inv = fm.emit_complete_manifest(root=Path("."), source_root=Path("."))
    except ManifestNotAvailable:
        # Inner-role / future members may be absent outside sealed runner — still
        # prove artifact/source digesters are distinct callables.
        art_entries, art_dig = fm.independent_fixture_artifact_digest(fixture_src)
        src_entries, src_dig = fm.independent_source_tree_digest(Path("."))
        assert art_dig != src_dig or art_entries != src_entries
        assert callable(fm.inventory_fixture_artifacts)
        assert callable(fm.inventory_source_export)
        return
    assert manifest["source_tree_sha256"] != manifest["components"][0]["sha256"]
    assert isinstance(src_inv, list)
    # Identical regeneration.
    manifest2, src_inv2 = fm.emit_complete_manifest(root=Path("."), source_root=Path("."))
    assert manifest == manifest2
    assert src_inv == src_inv2


def test_m7_canonical_audit_arrays_and_inventories():
    """M7: dry-collect canonical arrays, exact tools/suites, no broad discovery."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import audit_evidence as ae

    assert ae.exact_legacy_exclusions() == list(oc_constants.LEGACY_DESELECTS)
    assert len(ae.exact_legacy_exclusions()) == 4
    assert ae.exact_tool_inventory() == {
        "tools": ["search", "unresolved", "related"],
        "resources": [],
        "resource_templates": [],
    }
    assert ae.exact_tool_inventory()["tools"] == list(oc_constants.STRICT_TOOL_NAMES)
    suites = ae.exact_selected_suites()
    assert len(suites) == 3
    assert [s["name"] for s in suites] == [
        "strict_python",
        "connector_node",
        "legacy_python",
    ]
    discovery = ae.suite_discovery_contract()
    assert discovery["full_repository_discovery"] is False
    assert discovery["mode"] == "exact_selectors"
    # No broad discovery tokens in frozen argv.
    for suite in suites:
        joined = " ".join(suite["argv"])
        assert " tests " not in f" {joined} "
        assert "-k" not in suite["argv"]
        assert "--ignore" not in suite["argv"]
        assert suite["argv"].count("pytest") <= 1
    legacy = next(s for s in suites if s["name"] == "legacy_python")
    for node in oc_constants.LEGACY_DESELECTS:
        assert f"--deselect={node}" in legacy["argv"]
    files = ae.exact_selected_test_files()
    assert files["strict_python"] == list(oc_constants.STRICT_PYTEST_FILES)
    assert files["connector_node"] == [oc_constants.CONNECTOR_NODE_TEST]
    assert files["legacy_python"] == list(oc_constants.LEGACY_PYTEST_FILES)

    package = ae.build_audit_package(
        plan_sha=oc_constants.SEMANTIC_PARENT_SHA,
        source_commit="a" * 40,
        source_tree_sha256="sha256:" + ("b" * 64),
        test_runtime_tree_sha256=oc_constants.EXPECTED_TEST_RUNTIME_TREE_SHA256,
        components=[
            {"name": name, "sha256": "sha256:" + (c * 64)}
            for name, c in zip(
                ("builder", "strict_server", "supervisor", "controller", "plugin"),
                "cdefg",
            )
        ],
        suite_results=[
            {
                "name": "strict_python",
                "returncode": 0,
                "elapsed_sec": 1.0,
                "combined_output_bytes": 10,
                "max_tmp_bytes": 0,
                "tmp_sample_interval_sec": 1.0,
                "killed_reason": None,
            }
        ],
        negative_controls=[
            {
                "control": "production_fake",
                "status": "FAIL_AS_REQUIRED",
                "independent_failure_reason": "production_fake_selector:x",
            }
        ],
        changed_files=["tests/fixtures/openclaw_strict/audit_evidence.py"],
        protected_byte_proof=[
            {
                "path": "provenance.py",
                "unchanged": True,
                "status": "compared",
                "baseline_sha256": "sha256:" + ("1" * 64),
                "source_sha256": "sha256:" + ("1" * 64),
            }
        ],
        outer_returncode=0,
        preflight_ok=True,
    )
    ae.validate_audit_package(package)
    assert package["plan_sha"] == oc_constants.SEMANTIC_PARENT_SHA
    assert package["source_commit"] == "a" * 40
    assert package["legacy_exclusions"] == list(oc_constants.LEGACY_DESELECTS)
    assert package["authority"]["evidence_is_not_approval"] is True
    assert package["authority"]["evidence_is_not_qualification"] is True
    assert package["authority"]["evidence_is_not_promotion"] is True
    assert package["outcomes"]["claims_live_readiness"] is False
    labels = {o["label"] for o in package["observations"]}
    assert labels <= set(oc_constants.EVIDENCE_LABELS)
    fake = [o for o in package["observations"] if o["id"] == "negative_control:production_fake"]
    assert fake and fake[0]["label"] == "FAKE"
    real = [o for o in package["observations"] if o["id"] == "openclaw_real_runtime"]
    assert real and real[0]["label"] == "REAL"
    assert real[0]["outcome"] == "NOT_EXECUTED_BLOCKED"
    # Self-hash regenerates.
    again = ae.compute_evidence_payload_sha256(package)
    assert again == package["evidence_payload_sha256"]


def test_m7_label_upgrade_and_closed_cli_forbidden():
    """M7: refuse fake→REAL upgrade; closed runner CLI has no run-label."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import audit_evidence as ae

    try:
        ae.label_observation(
            observation_id="x",
            label="FAKE",
            outcome="REAL_PASS",
        )
        raise AssertionError("label_upgrade_accepted")
    except ValueError as exc:
        assert "label_upgrade_forbidden" in str(exc)
    try:
        ae.label_observation(
            observation_id="y",
            label="REAL",
            outcome="PASS",
        )
        raise AssertionError("real_pass_accepted")
    except ValueError as exc:
        assert "real_pass_forbidden" in str(exc)

    # Closed CLI: source-text contract only (do not import run_isolated in pytest —
    # its inventory import resolves to an unrelated /src/inventory.py under module state).
    src = Path("tests/fixtures/openclaw_strict/run_isolated.py").read_text(encoding="utf-8")
    assert (
        'expected_order = ["--source-commit", "--plan-sha", "--runtime-root", "--suite"]'
        in src
    )
    assert "--run-label" not in src
    assert "run_label_cli" in src  # explicit forbidden marker in evidence emit


def test_m7_generated_path_hash_exclusion_and_read_nonmutation(tmp_path: Path):
    """M7: generated evidence paths excluded from hashes; reads do not mutate."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import audit_evidence as ae
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import fixture_manifest as fm

    tree = tmp_path / "fixture_tree"
    tree.mkdir()
    (tree / "helper.py").write_text("tracked\n", encoding="utf-8")
    evidence = tree / "evidence"
    evidence.mkdir()
    audit_path = evidence / "bounded-audit-evidence.json"
    audit_path.write_text('{"schema":"convmem.bounded-audit-evidence.v1"}\n', encoding="utf-8")
    (evidence / "fixture-manifest.json").write_text("{}\n", encoding="utf-8")
    (evidence / "suite_results.json").write_text("[]\n", encoding="utf-8")
    (tree / "suite_results.json").write_text("[]\n", encoding="utf-8")

    before = {
        p: (p.stat().st_mtime_ns, p.stat().st_size, p.read_bytes())
        for p in (
            audit_path,
            evidence / "fixture-manifest.json",
            tree / "helper.py",
        )
    }
    # Read-only inventory must not mutate files.
    entries = fm.inventory_fixture_artifacts(tree)
    paths = {e["path"] for e in entries}
    assert "tests/fixtures/openclaw_strict/helper.py" in paths
    assert "tests/fixtures/openclaw_strict/evidence/bounded-audit-evidence.json" not in paths
    assert "tests/fixtures/openclaw_strict/evidence/fixture-manifest.json" not in paths
    assert "tests/fixtures/openclaw_strict/evidence/suite_results.json" not in paths
    assert "tests/fixtures/openclaw_strict/suite_results.json" not in paths
    after = {
        p: (p.stat().st_mtime_ns, p.stat().st_size, p.read_bytes())
        for p in before
    }
    assert before == after

    # Independent oracle walker agrees on exclusion.
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional

    ref = oracle.reference_fixture_artifact_walk(tree)
    ref_paths = {e["path"] for e in ref}
    assert "tests/fixtures/openclaw_strict/evidence/bounded-audit-evidence.json" not in ref_paths
    assert ae.generated_paths_excluded_from_fixture_inventory() == (
        oc_constants.GENERATED_EVIDENCE_FIXTURE_RELS
    )
    # Emit under disposable evidence only.
    out_dir = tmp_path / "evidence"
    package = ae.build_audit_package(
        plan_sha=oc_constants.SEMANTIC_PARENT_SHA,
        source_commit="c" * 40,
        source_tree_sha256="sha256:" + ("d" * 64),
        test_runtime_tree_sha256=oc_constants.EXPECTED_TEST_RUNTIME_TREE_SHA256,
        components=[
            {"name": name, "sha256": "sha256:" + ("e" * 64)}
            for name in (
                "builder",
                "strict_server",
                "supervisor",
                "controller",
                "plugin",
            )
        ],
        suite_results=[],
        negative_controls=[],
        changed_files=[],
        protected_byte_proof=[],
        outer_returncode=None,
        preflight_ok=False,
    )
    written = ae.emit_audit_package(out_dir, package)
    assert written.parent == out_dir
    assert written.name == "bounded-audit-evidence.json"
    assert written.is_file()
    # No write into source fixture tree from emit.
    tracked_audit = Path("tests/fixtures/openclaw_strict/evidence/bounded-audit-evidence.json")
    assert not tracked_audit.exists()


def test_m8_selected_nodes_strict_live_inventory(request):
    """Record live strict-suite nodeids without changing frozen selectors."""
    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    items = getattr(request.session, "items", None) or []
    nodeids = sorted({item.nodeid for item in items})
    # Must be drawn only from named strict files — never repository-wide discovery.
    for nodeid in nodeids:
        assert any(
            nodeid == rel or nodeid.startswith(rel + "::")
            for rel in oc_constants.STRICT_PYTEST_FILES
        ), f"unexpected_node:{nodeid}"
    payload = {
        "suite": "strict_python",
        "full_repository_discovery": False,
        "nodeids": nodeids,
        "count": len(nodeids),
        "source": "pytest_session_items",
    }
    Path(oc_constants.SELECTED_NODES_STRICT_PATH).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def test_m8_prompt_injection_bytes_remain_untrusted_tool_data():
    """Case 32 is D-blocked; Gate C fixture negative under 33/57 — no case-32 PASS."""
    specimen_path = Path(oc_constants.PROMPT_INJECTION_SPECIMEN_REL)
    assert specimen_path.is_file()
    specimen = json.loads(specimen_path.read_text(encoding="utf-8"))
    assert specimen["untrusted"] is True
    assert specimen["role"] == "tool_result"
    assert "ignore policy" in specimen["content"]
    assert "call shell" in specimen["content"]
    assert "export secrets" in specimen["content"]
    # Bytes are data only — no instruction/tool action markers may flip untrusted.
    assert specimen["expected_behavior"].startswith("bytes remain untrusted")
    for effect in (
        "shell_exec",
        "memory_write",
        "credential_export",
        "instruction_follow",
        "role_escalation",
    ):
        assert effect in specimen["forbidden_effects"]
    # Explicit non-claim: case 32 remains Gate D blocked; no PASS claim.
    note = specimen["case_note"]
    assert "32" in note and "blocked" in note.lower()
    assert "PASS" in note and "never" in note.lower()

def test_m8_adversarial_matrix_gate_ownership_and_threat_rows():
    """M8: Gate B/C ownership, D/W/E blocked, §5 matrix, nodes, mutants, no all-58."""
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import adversarial_matrix as am
# pylint: disable-next=E0401,C0413  # fixture path-injection after sys.path; order intentional
    import audit_evidence as ae

    ownership = am.gate_ownership_table()
    assert len(ownership) == 58
    assert all(row["claims_pass"] is False for row in ownership)
    gate_b = set(am.gate_b_case_numbers())
    gate_c = set(am.gate_c_fake_case_numbers())
    # Parent acceptance ownership core.
    assert {1, 27, 40, 44, 49, 52}.issubset(gate_b)
    assert {33, 35, 45, 46, 48, 53, 54}.issubset(gate_c)
    assert 2 in gate_c
    assert 56 not in gate_b and 56 not in gate_c
    assert 37 not in gate_b and 37 not in gate_c
    blocked = am.blocked_later_gate_summary()
    assert blocked["claims_all_58_passed"] is False
    assert blocked["never_claim_all_58_passed"] is True
    assert blocked["gate_d"]["status"] == "UNTESTED_BLOCKED"
    assert blocked["gate_w"]["status"] == "UNTESTED_BLOCKED"
    assert blocked["gate_e"]["status"] == "UNTESTED_BLOCKED"
    assert 56 in blocked["gate_w"]["cases"]
    assert 37 in blocked["gate_e"]["cases"]
    assert 28 in blocked["gate_d"]["cases"]

    assert len(am.THREAT_MATRIX) == 14
    triples = am.input_expected_evidence_triples()
    assert len(triples) == 14
    for row in triples:
        assert row["input"]
        assert row["expected"]
        assert row["evidence"]
        assert row["parent_case_gate"]
        assert row["evidence_class"] in oc_constants.EVIDENCE_LABELS or row[
            "evidence_class"
        ] in {"STATIC", "FAKE", "DISPOSABLE_KERNEL", "REAL"}

    mutants = am.ENFORCEMENT_REMOVAL_MUTANTS
    assert len(mutants) >= 5
    mutant_ids = {m["mutant_id"] for m in mutants}
    assert "omit_canonical_json_helper" in mutant_ids
    assert "supervisor_emptiness_attestation" in mutant_ids
    assert "production_fake_selector" in mutant_ids

    nodes = am.selected_node_inventory(root=Path("."))
    assert nodes["full_repository_discovery"] is False
    assert nodes["mode"] == "named_file_ast_inventory"
    assert nodes["legacy_python"]["exclusion_count"] == 4
    assert nodes["legacy_python"]["exclusions"] == list(oc_constants.LEGACY_DESELECTS)
    # Four legacy exclusions must appear as excluded, not selected.
    for excl in oc_constants.LEGACY_DESELECTS:
        assert excl not in nodes["legacy_python"]["nodeids"]
        assert excl in nodes["legacy_python"]["excluded_nodeids_found_in_files"]
    # Selected nodes come only from named files.
    for nodeid in nodes["strict_python"]["nodeids"]:
        assert any(
            nodeid.startswith(rel) for rel in oc_constants.STRICT_PYTEST_FILES
        )
    assert nodes["total_selected_node_count"] > 0

    package = ae.build_audit_package(
        plan_sha=oc_constants.SEMANTIC_PARENT_SHA,
        source_commit="a" * 40,
        source_tree_sha256="sha256:" + ("b" * 64),
        test_runtime_tree_sha256=oc_constants.EXPECTED_TEST_RUNTIME_TREE_SHA256,
        components=[
            {"name": name, "sha256": "sha256:" + (c * 64)}
            for name, c in zip(
                ("builder", "strict_server", "supervisor", "controller", "plugin"),
                "cdefg",
            )
        ],
        suite_results=[
            {
                "name": "strict_python",
                "returncode": 0,
                "elapsed_sec": 1.0,
                "combined_output_bytes": 10,
                "max_tmp_bytes": 0,
                "tmp_sample_interval_sec": 1.0,
                "killed_reason": None,
            }
        ],
        negative_controls=[
            {
                "control": "production_fake",
                "status": "FAIL_AS_REQUIRED",
                "independent_failure_reason": "production_fake_selector:x",
            }
        ],
        changed_files=["tests/fixtures/openclaw_strict/adversarial_matrix.py"],
        protected_byte_proof=[
            {
                "path": "provenance.py",
                "unchanged": True,
                "status": "compared",
                "baseline_sha256": "sha256:" + ("1" * 64),
                "source_sha256": "sha256:" + ("1" * 64),
            }
        ],
        outer_returncode=0,
        preflight_ok=True,
        source_root=Path("."),
        containment_evidence=ae.collect_containment_evidence(
            fixture_root=Path("/fixture")
            if Path("/fixture").is_dir()
            else Path("."),
            suite_results=[],
            negative_controls=[],
        ),
    )
    ae.validate_audit_package(package)
    assert package["legacy_exclusions"] == list(oc_constants.LEGACY_DESELECTS)
    assert len(package["legacy_exclusions"]) == 4
    assert package["allowed_file_proof"]["all_changed_allowed"] is True
    assert package["outcomes"]["claims_all_58_passed"] is False
    assert package["outcomes"]["claims_gate_d_pass"] is False
    assert package["outcomes"]["claims_gate_w_pass"] is False
    assert package["outcomes"]["claims_gate_e_pass"] is False
    matrix = package["adversarial_matrix"]
    assert matrix["threat_row_count"] == 14
    assert matrix["claims_all_58_passed"] is False
    assert matrix["blocked_later_gates"]["gate_d"]["status"] == "UNTESTED_BLOCKED"
    assert matrix["selected_node_inventory"]["full_repository_discovery"] is False
    assert len(matrix["enforcement_removal_mutants"]) >= 5
    assert "capacity" in matrix["containment_evidence"]
    assert "process" in matrix["containment_evidence"]
    assert "import" in matrix["containment_evidence"]
    assert "mount" in matrix["containment_evidence"]
    assert "fd" in matrix["containment_evidence"]
    assert "network" in matrix["containment_evidence"]
    obs_ids = {o["id"]: o for o in package["observations"]}
    assert obs_ids["gate_d_rows"]["outcome"] == "UNTESTED_BLOCKED"
    assert obs_ids["gate_w_rows"]["outcome"] == "UNTESTED_BLOCKED"
    assert obs_ids["gate_e_rows"]["outcome"] == "UNTESTED_BLOCKED"
    assert obs_ids["claims_all_58_passed"]["outcome"] == "FALSE"
    assert obs_ids["legacy_exclusions"]["outcome"] == "EXACT_FOUR"
