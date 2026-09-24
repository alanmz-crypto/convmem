"""Exact three-suite command builders (Execution §5.1)."""

from __future__ import annotations

from constants import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
    CONNECTOR_NODE_TEST,
    LEGACY_DESELECTS,
    LEGACY_PYTEST_FILES,
    STRICT_PYTEST_FILES,
)


def strict_pytest_argv() -> list[str]:
    return [
        "/runtime/bin/python",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp=/fixture/pytest-strict",
        "-o",
        "junit_family=xunit1",
        "--junitxml=/fixture/evidence/pytest-strict-junit.xml",
        *STRICT_PYTEST_FILES,
    ]


def connector_node_argv() -> list[str]:
    return ["/runtime/bin/node", "--test", CONNECTOR_NODE_TEST]


def legacy_pytest_argv() -> list[str]:
    argv = [
        "/runtime/bin/python",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "--basetemp=/fixture/pytest-legacy",
        "-o",
        "junit_family=xunit1",
        "--junitxml=/fixture/evidence/pytest-legacy-junit.xml",
    ]
    for node in LEGACY_DESELECTS:
        argv.append(f"--deselect={node}")
    argv.extend(LEGACY_PYTEST_FILES)
    return argv


def all_suite_commands() -> list[tuple[str, list[str]]]:
    return [
        ("strict_python", strict_pytest_argv()),
        ("connector_node", connector_node_argv()),
        ("legacy_python", legacy_pytest_argv()),
    ]


def validate_frozen_selectors() -> None:
    assert len(STRICT_PYTEST_FILES) == 13
    assert CONNECTOR_NODE_TEST.endswith("connector.test.mjs")
    assert len(LEGACY_DESELECTS) == 4
