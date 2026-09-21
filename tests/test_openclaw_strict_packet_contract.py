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
    import importlib.metadata

    assert os.environ.get("CONVMEM_OPENCLAW_INNER_ROLE") == "inner"
    assert os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == "1"
    pm = pytestconfig.pluginmanager
    # -p no:cacheprovider blocks cacheprovider; never treat it as loaded.
    disabled = {"cacheprovider"}
    loaded_names = sorted(
        {
            name
            for name, _plugin in pm.list_name_plugin()
            if name not in disabled and not name.startswith("no:")
        }
    )
    assert "no:cacheprovider" not in loaded_names
    assert "cacheprovider" not in loaded_names
    assert not pm.has_plugin("cacheprovider")

    distribution_plugins: list[dict[str, str]] = []
    unapproved: list[str] = []
    try:
        eps = importlib.metadata.entry_points(group="pytest11")
    except TypeError:
        eps = importlib.metadata.entry_points().select(group="pytest11")
    for ep in eps:
        name = ep.name
        # Blocked/disabled entry must not be recorded as a loaded plugin.
        if name in disabled or name.startswith("no:"):
            continue
        dist = getattr(ep, "dist", None)
        dist_name = dist.name if dist is not None else ""
        if not pm.has_plugin(name):
            continue
        distribution_plugins.append({"plugin": name, "distribution": dist_name})
        # Autoload false + explicitly_loaded empty → reject external dist plugins.
        if dist_name and dist_name != "pytest":
            unapproved.append(f"{dist_name}:{name}")
    assert not unapproved, f"unapproved_external_distribution_plugins:{unapproved}"

    inventory = {
        "autoload": False,
        "disabled_plugins": ["cacheprovider"],
        "explicitly_loaded_plugins": [],
        "loaded_plugin_names": loaded_names,
        "loaded_distribution_plugins": sorted(
            distribution_plugins, key=lambda d: (d["distribution"], d["plugin"])
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


def test_case58_component_inventory_capability_absent():
    import fixture_manifest as fm

    assert hasattr(fm, "build_component_inventories"), (
        "[T0b] independent component inventory oracle capability absent"
    )
