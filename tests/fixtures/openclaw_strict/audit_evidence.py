"""M7/M8 bounded audit evidence — attributable fixture-only run package.

Architecture / Execution parent (b810fcd) + overlay M7/M8 (67d4f5a):
emit canonical inventories, evidence-class labels, suite selection/exclusions,
timing/output/tmp, negative controls, changed-file/protected-byte proof,
Gate B/C ownership, overlay §5 threat matrix, selected-node inventory,
enforcement-removal mutants, containment evidence, and outcomes under
disposable ``/fixture/evidence`` only. Evidence is not approval, signing,
admission, qualification, manager emptiness, or promotion. Never claims all
58 cases passed.
"""
# pylint: disable=too-many-lines  # preserved fixture audit-evidence module/component boundary

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# pylint: disable-next=E0401  # fixture path-injection import; module resolved via sys.path
from adversarial_matrix import build_adversarial_evidence_section
# pylint: disable-next=E0401  # fixture path-injection import; module resolved via sys.path
from allowlist import path_allowed
from constants import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
    CODE_BASELINE_SHA,
    CONNECTOR_NODE_TEST,
    EVIDENCE_AUDIT_REL,
    EVIDENCE_JUNIT_LEGACY_REL,
    EVIDENCE_JUNIT_STRICT_REL,
    EVIDENCE_LABELS,
    EVIDENCE_MANIFEST_REL,
    EVIDENCE_NODE_OUTCOMES_REL,
    EVIDENCE_SUITE_RESULTS_REL,
    EXPECTED_LEGACY_DESELECTION_COUNT,
    EXPECTED_LEGACY_JUNIT_COUNTS,
    EXPECTED_STRICT_JUNIT_COUNTS,
    GENERATED_EVIDENCE_FIXTURE_RELS,
    GENERATED_EVIDENCE_SOURCE_RELS,
    JUNIT_LEGACY_PATH,
    JUNIT_STRICT_PATH,
    LEGACY_DESELECTS,
    LEGACY_PYTEST_FILES,
    NODE_OUTCOMES_SCHEMA,
    SEMANTIC_PARENT_SHA,
    STRICT_PYTEST_FILES,
    STRICT_TOOL_NAMES,
)
# pylint: disable-next=E0401  # fixture path-injection import; module resolved via sys.path
from suites import all_suite_commands

SCHEMA_ID = "convmem.bounded-audit-evidence.v1"
ARTIFACT_KIND = "bounded_audit_evidence"

REQUIRED_KEYS = (
    "schema",
    "artifact_kind",
    "plan_sha",
    "source_commit",
    "code_baseline_sha",
    "source_tree_sha256",
    "test_runtime_tree_sha256",
    "components",
    "selected_suites",
    "legacy_exclusions",
    "selected_test_files",
    "tool_inventory",
    "suite_discovery",
    "suite_results",
    "negative_controls",
    "changed_files",
    "allowed_file_proof",
    "protected_byte_proof",
    "adversarial_matrix",
    "observations",
    "outcomes",
    "generated_paths",
    "authority",
    "evidence_payload_sha256",
)


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def compute_evidence_payload_sha256(package: dict[str, Any]) -> str:
    body = {k: package[k] for k in REQUIRED_KEYS if k != "evidence_payload_sha256"}
    return _sha256_bytes(canonical_json_bytes(body))


def exact_tool_inventory() -> dict[str, Any]:
    return {
        "tools": list(STRICT_TOOL_NAMES),
        "resources": [],
        "resource_templates": [],
    }


def exact_selected_suites() -> list[dict[str, Any]]:
    return [
        {"name": name, "argv": list(argv)} for name, argv in all_suite_commands()
    ]


def exact_selected_test_files() -> dict[str, Any]:
    return {
        "strict_python": list(STRICT_PYTEST_FILES),
        "connector_node": [CONNECTOR_NODE_TEST],
        "legacy_python": list(LEGACY_PYTEST_FILES),
    }


def exact_legacy_exclusions() -> list[str]:
    return list(LEGACY_DESELECTS)


def suite_discovery_contract() -> dict[str, Any]:
    """Closed §5.1 selection — never repository-wide discovery."""

    return {
        "mode": "exact_selectors",
        "full_repository_discovery": False,
        "caller_filters_forbidden": ["-k", "--ignore", "--collect-only"],
        "suite_count": 3,
        "legacy_exclusion_count": 4,
    }


def generated_evidence_paths() -> list[str]:
    return sorted(
        {
            EVIDENCE_MANIFEST_REL,
            EVIDENCE_AUDIT_REL,
            EVIDENCE_SUITE_RESULTS_REL,
            EVIDENCE_JUNIT_STRICT_REL,
            EVIDENCE_JUNIT_LEGACY_REL,
            EVIDENCE_NODE_OUTCOMES_REL,
            "suite_results.json",
            *GENERATED_EVIDENCE_FIXTURE_RELS,
        }
    )


def authority_disclaimer() -> dict[str, bool]:
    return {
        "evidence_is_not_approval": True,
        "evidence_is_not_signing": True,
        "evidence_is_not_admission": True,
        "evidence_is_not_qualification": True,
        "evidence_is_not_manager_emptiness": True,
        "evidence_is_not_promotion": True,
    }


_LOSSY_ESCAPE_RE = re.compile(r"#x[0-9A-Fa-f]{2}(?:[0-9A-Fa-f]{2})?")
_OUTCOME_BY_TAG = {
    "failure": "failed",
    "error": "error",
    "skipped": "skipped",
}
_SUITE_IGNORED_CHILDREN = frozenset({"properties"})


class JUnitNodeEvidenceError(ValueError):
    """Fail-closed JUnit / node-outcome contract violation."""


def _file_to_dotted(file_path: str) -> str:
    if not file_path.endswith(".py"):
        raise JUnitNodeEvidenceError(f"junit_file_not_py:{file_path}")
    return file_path[: -len(".py")].replace("/", ".")


def _reject_lossy_escapes(*values: str) -> None:
    for value in values:
        if _LOSSY_ESCAPE_RE.search(value):
            raise JUnitNodeEvidenceError(f"junit_lossy_escape:{value}")


def _reconstruct_nodeid(file_attr: str, classname: str, name: str) -> str:
    _reject_lossy_escapes(file_attr, classname, name)
    if not file_attr or not classname or not name:
        raise JUnitNodeEvidenceError("junit_empty_attr")
    dotted = _file_to_dotted(file_attr)
    if classname == dotted:
        segments: list[str] = []
    elif classname.startswith(dotted + "."):
        remainder = classname[len(dotted) + 1 :]
        if not remainder or remainder.startswith(".") or remainder.endswith("."):
            raise JUnitNodeEvidenceError(f"junit_classname_segments:{classname}")
        segments = remainder.split(".")
        if any(not part for part in segments):
            raise JUnitNodeEvidenceError(f"junit_classname_segments:{classname}")
    else:
        raise JUnitNodeEvidenceError(
            f"junit_classname_prefix_mismatch:file={file_attr}:classname={classname}"
        )
    nodeid = file_attr + "".join(f"::{seg}" for seg in segments) + f"::{name}"
    # Unique round-trip to the same three attributes.
    parts = nodeid.split("::")
    if len(parts) < 2:
        raise JUnitNodeEvidenceError(f"junit_roundtrip_short:{nodeid}")
    rt_file = parts[0]
    rt_name = parts[-1]
    rt_segments = parts[1:-1]
    rt_dotted = _file_to_dotted(rt_file)
    rt_classname = (
        rt_dotted if not rt_segments else rt_dotted + "." + ".".join(rt_segments)
    )
    if (rt_file, rt_classname, rt_name) != (file_attr, classname, name):
        raise JUnitNodeEvidenceError(
            f"junit_roundtrip_mismatch:{nodeid}:"
            f"{rt_file!r}/{rt_classname!r}/{rt_name!r}"
        )
    return nodeid


def _testcase_outcome(case: ET.Element) -> str:
    children = list(case)
    if not children:
        return "passed"
    if len(children) != 1:
        raise JUnitNodeEvidenceError(
            f"junit_unexpected_children:{[c.tag for c in children]}"
        )
    tag = children[0].tag
    if tag not in _OUTCOME_BY_TAG:
        raise JUnitNodeEvidenceError(f"junit_unknown_child:{tag}")
    return _OUTCOME_BY_TAG[tag]


def _parse_junit_xml_text(
    *,
    suite_name: str,
    junit_path: str,
    raw: str,
    selector_files: tuple[str, ...],
    deselections: tuple[str, ...],
    expected_counts: dict[str, int],
    process_returncode: int | None,
) -> dict[str, Any]:
    """Fail-closed xunit1 validation for file-backed or in-memory report text."""

    if process_returncode is None:
        raise JUnitNodeEvidenceError(f"junit_missing_process_status:{suite_name}")
    if process_returncode != 0:
        raise JUnitNodeEvidenceError(
            f"junit_nonzero_process_status:{suite_name}:{process_returncode}"
        )
    if "<!DOCTYPE" in raw or "<!ENTITY" in raw:
        raise JUnitNodeEvidenceError(f"junit_dtd_or_entity:{junit_path}")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise JUnitNodeEvidenceError(f"junit_malformed:{junit_path}:{exc}") from exc
    if root.tag != "testsuites":
        raise JUnitNodeEvidenceError(f"junit_root_not_testsuites:{root.tag}")
    suites = list(root)
    if len(suites) != 1 or suites[0].tag != "testsuite":
        raise JUnitNodeEvidenceError(
            f"junit_suite_structure:{[c.tag for c in suites]}"
        )
    testsuite = suites[0]
    if any(child.tag == "testsuite" for child in testsuite):
        raise JUnitNodeEvidenceError("junit_nested_testsuite")

    selectors = set(selector_files)
    deselected = set(deselections)
    seen_files: set[str] = set()
    seen_nodeids: set[str] = set()
    node_outcomes: list[dict[str, str]] = []
    derived = {"collected": 0, "passed": 0, "failed": 0, "error": 0, "skipped": 0}

    for child in testsuite:
        if child.tag in _SUITE_IGNORED_CHILDREN:
            continue
        if child.tag != "testcase":
            raise JUnitNodeEvidenceError(f"junit_unexpected_suite_child:{child.tag}")
        file_attr = child.attrib.get("file", "")
        classname = child.attrib.get("classname", "")
        name = child.attrib.get("name", "")
        if file_attr not in selectors:
            raise JUnitNodeEvidenceError(f"junit_file_outside_selectors:{file_attr}")
        # Unique file-prefix match among exact selectors (Architecture §6.5.8).
        prefix_matches = [
            sel
            for sel in selector_files
            if classname == _file_to_dotted(sel)
            or classname.startswith(_file_to_dotted(sel) + ".")
        ]
        if prefix_matches != [file_attr]:
            raise JUnitNodeEvidenceError(
                f"junit_file_prefix_match:{classname}:{prefix_matches}:{file_attr}"
            )
        nodeid = _reconstruct_nodeid(file_attr, classname, name)
        if nodeid in deselected:
            raise JUnitNodeEvidenceError(f"junit_deselected_present:{nodeid}")
        if nodeid in seen_nodeids:
            raise JUnitNodeEvidenceError(f"junit_duplicate_nodeid:{nodeid}")
        seen_nodeids.add(nodeid)
        seen_files.add(file_attr)
        outcome = _testcase_outcome(child)
        derived["collected"] += 1
        derived[outcome] += 1
        node_outcomes.append({"nodeid": nodeid, "outcome": outcome})

    missing_files = [rel for rel in selector_files if rel not in seen_files]
    if missing_files:
        raise JUnitNodeEvidenceError(
            f"junit_selected_file_without_testcase:{missing_files}"
        )

    try:
        attr_counts = {
            "collected": int(testsuite.attrib["tests"]),
            "failed": int(testsuite.attrib["failures"]),
            "error": int(testsuite.attrib["errors"]),
            "skipped": int(testsuite.attrib["skipped"]),
        }
    except (KeyError, ValueError) as exc:
        raise JUnitNodeEvidenceError(
            f"junit_suite_attr_counts:{testsuite.attrib}:{exc}"
        ) from exc
    attr_counts["passed"] = (
        attr_counts["collected"]
        - attr_counts["failed"]
        - attr_counts["error"]
        - attr_counts["skipped"]
    )
    if derived != attr_counts:
        raise JUnitNodeEvidenceError(
            f"junit_count_disagreement_derived_vs_attrs:{derived}:{attr_counts}"
        )
    if derived != expected_counts:
        raise JUnitNodeEvidenceError(
            f"junit_count_disagreement_behavioral:{derived}:{expected_counts}"
        )
    if derived["failed"] or derived["error"]:
        raise JUnitNodeEvidenceError(
            f"junit_failed_or_error:{suite_name}:{derived}"
        )
    if suite_name == "legacy_python":
        if len(deselections) != EXPECTED_LEGACY_DESELECTION_COUNT:
            raise JUnitNodeEvidenceError(
                f"junit_deselect_count:{len(deselections)}"
            )
        if list(deselections) != list(LEGACY_DESELECTS):
            raise JUnitNodeEvidenceError("junit_deselect_drift")
    elif deselections:
        raise JUnitNodeEvidenceError(f"junit_unexpected_deselections:{suite_name}")

    node_outcomes.sort(key=lambda row: row["nodeid"])
    return {
        "suite": suite_name,
        "junit_path": junit_path,
        "selector_files": list(selector_files),
        "deselections": list(deselections),
        "counts": dict(derived),
        "node_outcomes": node_outcomes,
    }


def _parse_one_junit_suite(
    *,
    suite_name: str,
    junit_path: str,
    report_file: Path,
    selector_files: tuple[str, ...],
    deselections: tuple[str, ...],
    expected_counts: dict[str, int],
    process_returncode: int | None,
) -> dict[str, Any]:
    if not report_file.is_file():
        raise JUnitNodeEvidenceError(f"junit_missing:{junit_path}")
    raw = report_file.read_text(encoding="utf-8")
    return _parse_junit_xml_text(
        suite_name=suite_name,
        junit_path=junit_path,
        raw=raw,
        selector_files=selector_files,
        deselections=deselections,
        expected_counts=expected_counts,
        process_returncode=process_returncode,
    )


def build_pytest_node_outcomes(
    *,
    evidence_dir: Path,
    suite_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Parse both built-in xunit1 reports after the existing Python processes finish."""

    by_name = {str(row.get("name")): row for row in suite_results}
    strict_rc = by_name.get("strict_python", {}).get("returncode")
    legacy_rc = by_name.get("legacy_python", {}).get("returncode")
    strict = _parse_one_junit_suite(
        suite_name="strict_python",
        junit_path=JUNIT_STRICT_PATH,
        report_file=evidence_dir / Path(EVIDENCE_JUNIT_STRICT_REL).name,
        selector_files=STRICT_PYTEST_FILES,
        deselections=(),
        expected_counts=dict(EXPECTED_STRICT_JUNIT_COUNTS),
        process_returncode=strict_rc if isinstance(strict_rc, int) else None,
    )
    legacy = _parse_one_junit_suite(
        suite_name="legacy_python",
        junit_path=JUNIT_LEGACY_PATH,
        report_file=evidence_dir / Path(EVIDENCE_JUNIT_LEGACY_REL).name,
        selector_files=LEGACY_PYTEST_FILES,
        deselections=LEGACY_DESELECTS,
        expected_counts=dict(EXPECTED_LEGACY_JUNIT_COUNTS),
        process_returncode=legacy_rc if isinstance(legacy_rc, int) else None,
    )
    return {
        "schema": NODE_OUTCOMES_SCHEMA,
        "full_repository_discovery": False,
        "suites": [strict, legacy],
    }


def _mini_counts(
    *,
    collected: int,
    passed: int,
    failed: int = 0,
    error: int = 0,
    skipped: int = 0,
) -> dict[str, int]:
    return {
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "error": error,
        "skipped": skipped,
    }


def _mini_suite_xml(
    *,
    tests: int,
    failures: int = 0,
    errors: int = 0,
    skipped: int = 0,
    body: str,
    root: str = "testsuites",
    wrap_suite: bool = True,
) -> str:
    """Build disposable in-memory xunit1 text for one semantic mutant."""

    attrs = (
        f'tests="{tests}" failures="{failures}" '
        f'errors="{errors}" skipped="{skipped}"'
    )
    if wrap_suite:
        inner = f"<testsuite {attrs}>{body}</testsuite>"
    else:
        inner = body
    return f"<{root}>{inner}</{root}>"


def _passed_case(file_attr: str, classname: str, name: str) -> str:
    return (
        f'<testcase classname="{classname}" file="{file_attr}" '
        f'name="{name}" time="0.001" />'
    )


# pylint: disable-next=R0914  # negative-control locals mirror closed junit parser cases
def run_junit_parser_negative_controls() -> list[dict[str, str]]:
    """Deterministic in-process parent JUnit/parser rejection evidence.

    Mutants are disposable in-memory XML only — no new process, plugin,
    persistent file, or output path. Error text is diagnostic only.
    """

    file_a = "tests/test_bound_read_scope.py"
    dotted_a = "tests.test_bound_read_scope"
    file_b = "tests/test_strict_grounding.py"
    dotted_b = "tests.test_strict_grounding"
    # Prefix-collision pair: classname under the nested file also matches the parent.
    file_prefix_parent = "tests/test.py"
    file_prefix_nested = "tests/test/nested.py"
    dotted_nested = "tests.test.nested"
    deselect_node = LEGACY_DESELECTS[0]
    deselect_file, deselect_name = deselect_node.split("::", 1)
    deselect_dotted = _file_to_dotted(deselect_file)
    path_label = "/fixture/evidence/parser-negative-control.xml"
    absent_report = Path(
        "/fixture/evidence/absent-parser-negative-control.xml"
    )

    # Each entry: stable control name, input description, kwargs builder,
    # and whether to invoke the existing file-backed wrapper.
    # Text builders return kwargs for _parse_junit_xml_text; file-wrapper
    # builders return kwargs for _parse_one_junit_suite.
    specs: list[tuple[str, str, Any, bool]] = []

    def _add(
        name: str,
        description: str,
        builder: Any,
        *,
        via_file_wrapper: bool = False,
    ) -> None:
        specs.append((name, description, builder, via_file_wrapper))

    _add(
        "dtd_or_entity",
        "JUnit XML containing DOCTYPE/ENTITY declaration",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": (
                '<?xml version="1.0"?>\n'
                "<!DOCTYPE testsuites [\n"
                '<!ENTITY xxe "xxe">\n'
                "]>\n"
                + _mini_suite_xml(
                    tests=1,
                    body=_passed_case(file_a, dotted_a, "test_ok"),
                )
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "entity_declaration",
        "JUnit XML containing ENTITY declaration without DOCTYPE",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": (
                '<?xml version="1.0"?>\n'
                '<!ENTITY xxe "xxe">\n'
                + _mini_suite_xml(
                    tests=1,
                    body=_passed_case(file_a, dotted_a, "test_ok"),
                )
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "missing_report_file",
        "File-backed wrapper rejects absent JUnit report path",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "report_file": absent_report,
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
        via_file_wrapper=True,
    )
    _add(
        "missing_process_status",
        "Python suite process_returncode is None",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_ok"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": None,
        },
    )
    _add(
        "empty_file_attribute",
        "Testcase file attribute is empty",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=(
                    f'<testcase classname="{dotted_a}" file="" '
                    f'name="test_ok" time="0.001" />'
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "empty_classname_attribute",
        "Testcase classname attribute is empty",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=(
                    f'<testcase classname="" file="{file_a}" '
                    f'name="test_ok" time="0.001" />'
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "empty_name_attribute",
        "Testcase name attribute is empty",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=(
                    f'<testcase classname="{dotted_a}" file="{file_a}" '
                    f'name="" time="0.001" />'
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "unique_round_trip_failure",
        "Otherwise valid attributes contain ambiguous double-colon segment",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "segment::ambiguous"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "malformed_xml",
        "JUnit XML with unclosed testsuite element",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": (
                f'<testsuites><testsuite tests="1" failures="0" '
                f'errors="0" skipped="0">'
                f"{_passed_case(file_a, dotted_a, 'test_ok')}"
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "wrong_root",
        "Root element is testsuite instead of testsuites",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_ok"),
                root="testsuite",
                wrap_suite=False,
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "additional_direct_suite",
        "testsuites root contains two direct testsuite children",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": (
                "<testsuites>"
                f'<testsuite tests="1" failures="0" errors="0" skipped="0">'
                f"{_passed_case(file_a, dotted_a, 'test_ok')}</testsuite>"
                f'<testsuite tests="1" failures="0" errors="0" skipped="0">'
                f"{_passed_case(file_b, dotted_b, 'test_ok')}</testsuite>"
                "</testsuites>"
            ),
            "selector_files": (file_a, file_b),
            "deselections": (),
            "expected_counts": _mini_counts(collected=2, passed=2),
            "process_returncode": 0,
        },
    )
    _add(
        "nested_suite",
        "Direct testsuite contains a nested testsuite element",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=(
                    f'<testsuite tests="1" failures="0" errors="0" skipped="0">'
                    f"{_passed_case(file_a, dotted_a, 'test_ok')}</testsuite>"
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "missing_file_prefix_match",
        "Selected file present but classname matches zero selector prefixes",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, "other.module", "test_ok"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "multiple_file_prefix_matches",
        "Classname matches more than one exact selector file prefix",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(
                    file_prefix_nested, dotted_nested + ".Klass", "test_ok"
                ),
            ),
            "selector_files": (file_prefix_parent, file_prefix_nested),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "lossy_escape_marker",
        "Test name contains lossy #xNN escape marker",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_#x2F_slash"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "lossy_escape_marker_four_hex",
        "Test name contains lossy #xNNNN four-hex escape marker",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_#x002F_slash"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "duplicate_reconstructed_node_id",
        "Two testcases reconstruct to the same node ID",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=2,
                body=(
                    _passed_case(file_a, dotted_a, "test_dup")
                    + _passed_case(file_a, dotted_a, "test_dup")
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=2, passed=2),
            "process_returncode": 0,
        },
    )
    _add(
        "unexpected_testcase_child",
        "Testsuite contains a non-testcase direct child",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=(
                    _passed_case(file_a, dotted_a, "test_ok")
                    + "<bogus/>"
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "multiple_conflicting_outcome_children",
        "Testcase has both failure and error children",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                failures=1,
                errors=1,
                body=(
                    f'<testcase classname="{dotted_a}" file="{file_a}" '
                    f'name="test_conflict" time="0.001">'
                    f"<failure /><error /></testcase>"
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(
                collected=1, passed=0, failed=1, error=1
            ),
            "process_returncode": 0,
        },
    )
    _add(
        "unknown_outcome_child",
        "Testcase has a single unknown outcome child tag",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=(
                    f'<testcase classname="{dotted_a}" file="{file_a}" '
                    f'name="test_unknown" time="0.001">'
                    f"<flaky /></testcase>"
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "node_outside_selectors",
        "Testcase file attribute is outside the exact selector set",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_b, dotted_b, "test_ok"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "deselected_legacy_node_present",
        "Fixed deselected legacy node appears as a collected testcase",
        lambda: {
            "suite_name": "legacy_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(deselect_file, deselect_dotted, deselect_name),
            ),
            "selector_files": (deselect_file,),
            "deselections": LEGACY_DESELECTS,
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    # Indices 1–3: each remaining fixed LEGACY_DESELECT independently.
    # Index 0 remains covered by deselected_legacy_node_present above.
    _deselect_1 = LEGACY_DESELECTS[1]
    _deselect_1_file, _deselect_1_name = _deselect_1.split("::", 1)
    _deselect_1_dotted = _file_to_dotted(_deselect_1_file)
    _add(
        "deselected_legacy_node_present_v6_git_facts",
        "Fixed deselected legacy node appears (test_v6_git_facts_non_git_cwd)",
        lambda: {
            "suite_name": "legacy_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(
                    _deselect_1_file, _deselect_1_dotted, _deselect_1_name
                ),
            ),
            "selector_files": (_deselect_1_file,),
            "deselections": LEGACY_DESELECTS,
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _deselect_2 = LEGACY_DESELECTS[2]
    _deselect_2_file, _deselect_2_name = _deselect_2.split("::", 1)
    _deselect_2_dotted = _file_to_dotted(_deselect_2_file)
    _add(
        "deselected_legacy_node_present_q7_hook_failure",
        "Fixed deselected legacy node appears (test_q7_hook_failure_writes_stderr)",
        lambda: {
            "suite_name": "legacy_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(
                    _deselect_2_file, _deselect_2_dotted, _deselect_2_name
                ),
            ),
            "selector_files": (_deselect_2_file,),
            "deselections": LEGACY_DESELECTS,
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _deselect_3 = LEGACY_DESELECTS[3]
    _deselect_3_file, _deselect_3_name = _deselect_3.split("::", 1)
    _deselect_3_dotted = _file_to_dotted(_deselect_3_file)
    _add(
        "deselected_legacy_node_present_q4_hook_two_missing",
        "Fixed deselected legacy node appears "
        "(test_q4_hook_two_missing_id_starts_same_cwd)",
        lambda: {
            "suite_name": "legacy_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(
                    _deselect_3_file, _deselect_3_dotted, _deselect_3_name
                ),
            ),
            "selector_files": (_deselect_3_file,),
            "deselections": LEGACY_DESELECTS,
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "selected_file_without_testcase",
        "One exact selector file contributes no testcase",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_ok"),
            ),
            "selector_files": (file_a, file_b),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "derived_vs_junit_count_disagreement",
        "Suite attribute counts disagree with derived testcase counts",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=5,
                body=_passed_case(file_a, dotted_a, "test_ok"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "behavioral_count_disagreement",
        "Derived counts disagree with fixed behavioral expected counts",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_ok"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=2, passed=2),
            "process_returncode": 0,
        },
    )
    _add(
        "nonzero_process_status",
        "Python suite process returncode is nonzero",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                body=_passed_case(file_a, dotted_a, "test_ok"),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=1),
            "process_returncode": 1,
        },
    )
    _add(
        "failed_or_error_outcome",
        "Report contains a failed testcase outcome",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                failures=1,
                body=(
                    f'<testcase classname="{dotted_a}" file="{file_a}" '
                    f'name="test_fail" time="0.001">'
                    f"<failure /></testcase>"
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=0, failed=1),
            "process_returncode": 0,
        },
    )
    _add(
        "error_outcome",
        "Report contains an error testcase outcome",
        lambda: {
            "suite_name": "strict_python",
            "junit_path": path_label,
            "raw": _mini_suite_xml(
                tests=1,
                errors=1,
                body=(
                    f'<testcase classname="{dotted_a}" file="{file_a}" '
                    f'name="test_err" time="0.001">'
                    f"<error /></testcase>"
                ),
            ),
            "selector_files": (file_a,),
            "deselections": (),
            "expected_counts": _mini_counts(collected=1, passed=0, error=1),
            "process_returncode": 0,
        },
    )

    results: list[dict[str, str]] = []
    for control, description, builder, via_file_wrapper in specs:
        kwargs = builder()
        try:
            if via_file_wrapper:
                _parse_one_junit_suite(**kwargs)
            else:
                _parse_junit_xml_text(**kwargs)
        except JUnitNodeEvidenceError as exc:
            results.append(
                {
                    "control": control,
                    "expected": "REJECT",
                    "input": description,
                    "observed_exception": type(exc).__name__,
                    "status": "PASS",
                }
            )
            continue
        except Exception as exc:
            raise RuntimeError(
                "junit_parser_negative_control_wrong_exception:"
                f"{control}:{type(exc).__name__}"
            ) from exc
        raise RuntimeError(
            f"junit_parser_negative_control_did_not_reject:{control}"
        )
    results.sort(key=lambda row: row["control"])
    return results


def emit_pytest_node_outcomes(evidence_dir: Path, package: dict[str, Any]) -> Path:
    """Write canonical node/outcome JSON under disposable evidence only."""

    if package.get("schema") != NODE_OUTCOMES_SCHEMA:
        raise JUnitNodeEvidenceError("node_outcomes_schema")
    if package.get("full_repository_discovery") is not False:
        raise JUnitNodeEvidenceError("node_outcomes_full_discovery")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / Path(EVIDENCE_NODE_OUTCOMES_REL).name
    path.write_text(
        json.dumps(package, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return path


def _git_blob_sha256(repo: Path, commit: str, rel: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{rel}"],
        capture_output=True,
        check=False,
        close_fds=True,
    )
    if proc.returncode != 0:
        return None
    return _sha256_bytes(proc.stdout)


def build_protected_byte_proof(
    *,
    repo: Path,
    baseline: str,
    source_root: Path,
    changed_files: list[str],
    protected_paths: list[str],
) -> list[dict[str, Any]]:
    """Prove unchanged protected paths remain byte-identical to baseline."""

    changed = set(changed_files)
    proof: list[dict[str, Any]] = []
    for rel in sorted(set(protected_paths)):
        if rel in changed:
            continue
        baseline_digest = _git_blob_sha256(repo, baseline, rel)
        src_path = source_root / rel
        if baseline_digest is None or not src_path.is_file():
            proof.append(
                {
                    "path": rel,
                    "unchanged": False,
                    "status": "missing_or_unreadable",
                    "baseline_sha256": baseline_digest,
                    "source_sha256": None,
                }
            )
            continue
        source_digest = _sha256_bytes(src_path.read_bytes())
        proof.append(
            {
                "path": rel,
                "unchanged": baseline_digest == source_digest,
                "status": "compared",
                "baseline_sha256": baseline_digest,
                "source_sha256": source_digest,
            }
        )
    return proof


def build_allowed_file_proof(changed_files: list[str]) -> dict[str, Any]:
    """Prove every changed path is on the parent edit allowlist."""

    allowed = []
    forbidden = []
    for rel in sorted(changed_files):
        entry = {"path": rel, "allowed": path_allowed(rel)}
        if entry["allowed"]:
            allowed.append(entry)
        else:
            forbidden.append(entry)
    return {
        "changed_count": len(changed_files),
        "allowed": allowed,
        "forbidden": forbidden,
        "all_changed_allowed": len(forbidden) == 0,
    }


def collect_containment_evidence(
    *,
    fixture_root: Path,
    suite_results: list[dict[str, Any]],
    negative_controls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble capacity/process/import/mount/FD/network from disposable roots."""

    from constants import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
        FD_OBSERVATION_FILE,
        IMPORT_TRACE_PATH,
        NS_OBSERVATION_FILE,
        PREFLIGHT_REPORT_PATH,
        SUITE_OUTPUT_LIMIT_BYTES,
        SUITE_WALL_DEADLINE_SEC,
        TMPFS_SIZE_BYTES,
    )

    def _read_json(path: Path) -> Any | None:
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    # Inside the sandbox these are /fixture/...; on the host they live under fixture_root.
    preflight = _read_json(fixture_root / "preflight_report.json")
    if preflight is None:
        preflight = _read_json(Path(PREFLIGHT_REPORT_PATH))
    import_trace = _read_json(fixture_root / "import_trace.json")
    if import_trace is None:
        import_trace = _read_json(Path(IMPORT_TRACE_PATH))
    fd_obs = _read_json(fixture_root / "fd_observation.json")
    if fd_obs is None:
        fd_obs = _read_json(Path(FD_OBSERVATION_FILE))
    ns_obs = _read_json(fixture_root / "ns_observation.json")
    if ns_obs is None:
        ns_obs = _read_json(Path(NS_OBSERVATION_FILE))

    capacity = {
        "suite_wall_deadline_sec": SUITE_WALL_DEADLINE_SEC,
        "suite_output_limit_bytes": SUITE_OUTPUT_LIMIT_BYTES,
        "tmpfs_size_bytes": TMPFS_SIZE_BYTES,
        "tmpfs_size_observed": (preflight or {}).get("tmpfs_size_bytes"),
        "suite_measurements": [
            {
                "name": r.get("name"),
                "elapsed_sec": r.get("elapsed_sec"),
                "combined_output_bytes": r.get("combined_output_bytes"),
                "max_tmp_bytes": r.get("max_tmp_bytes"),
                "tmp_sample_interval_sec": r.get("tmp_sample_interval_sec"),
                "killed_reason": r.get("killed_reason"),
                "returncode": r.get("returncode"),
            }
            for r in suite_results
        ],
    }
    return {
        "capacity": capacity,
        "process": {
            "negative_controls": negative_controls,
            "bwrap_mandatory": True,
            "preflight_status": (preflight or {}).get("status"),
        },
        "import": {
            "import_sentinel": (preflight or {}).get("import_sentinel"),
            "integration_imports_before": (preflight or {}).get(
                "integration_imports_before"
            ),
            "import_trace": import_trace,
        },
        "mount": {
            "readonly_mounts": (preflight or {}).get("readonly_mounts"),
            "mount_inventory": (preflight or {}).get("mount_inventory"),
            "canaries": (preflight or {}).get("canaries"),
        },
        "fd": {
            "inherited": (preflight or {}).get("fds"),
            "observation": fd_obs,
        },
        "network": {
            "namespace": (preflight or {}).get("network"),
            "ns_observation": ns_obs,
        },
    }


def label_observation(
    *,
    observation_id: str,
    label: str,
    outcome: str,
    detail: str = "",
) -> dict[str, str]:
    if label not in EVIDENCE_LABELS:
        raise ValueError(f"invalid_evidence_label:{label}")
    # Never upgrade fake/static/disposable evidence to a REAL success claim.
    if label != "REAL" and outcome.upper() in {
        "REAL_PASS",
        "RUNTIME_QUALIFIED",
        "LIVE_PASS",
        "PRODUCTION_PASS",
    }:
        raise ValueError(f"label_upgrade_forbidden:{label}:{outcome}")
    if label == "REAL" and outcome.upper() in {"PASS", "QUALIFIED", "GREEN"}:
        raise ValueError(f"real_pass_forbidden_in_fixture:{outcome}")
    return {
        "id": observation_id,
        "label": label,
        "outcome": outcome,
        "detail": detail,
    }


def default_observations(
    *,
    negative_controls: list[dict[str, Any]],
    suite_results: list[dict[str, Any]],
    outer_returncode: int | None,
) -> list[dict[str, str]]:
    obs: list[dict[str, str]] = [
        label_observation(
            observation_id="suite_selection",
            label="STATIC",
            outcome="EXACT_THREE_SUITES",
            detail="Execution §5.1 closed selectors",
        ),
        label_observation(
            observation_id="tool_inventory",
            label="STATIC",
            outcome="THREE_TOOLS_ZERO_RESOURCES",
            detail=",".join(STRICT_TOOL_NAMES),
        ),
        label_observation(
            observation_id="component_inventory",
            label="STATIC",
            outcome="FIVE_COMPONENT_DIGESTS",
            detail="Architecture §6.5.9",
        ),
        label_observation(
            observation_id="legacy_exclusions",
            label="STATIC",
            outcome="EXACT_FOUR",
            detail=",".join(LEGACY_DESELECTS),
        ),
        label_observation(
            observation_id="gate_b_ownership",
            label="STATIC",
            outcome="ASSIGNED_FIXTURE",
            detail="parent cases 1-27,40-44,49-52,47-server,55-boundary,57-58 portions",
        ),
        label_observation(
            observation_id="gate_c_fake_ownership",
            label="FAKE",
            outcome="ASSIGNED_FIXTURE",
            detail="connector/lifecycle portions 33,35,45-46,48,53-55,57-58",
        ),
        label_observation(
            observation_id="gate_d_rows",
            label="REAL",
            outcome="UNTESTED_BLOCKED",
            detail="Gate D real runtime outside T0-T5 fixture scope",
        ),
        label_observation(
            observation_id="gate_w_rows",
            label="REAL",
            outcome="UNTESTED_BLOCKED",
            detail="Gate W governed admission outside T0-T5 fixture scope",
        ),
        label_observation(
            observation_id="gate_e_rows",
            label="REAL",
            outcome="UNTESTED_BLOCKED",
            detail="Gate E pilot outside T0-T5 fixture scope",
        ),
        label_observation(
            observation_id="openclaw_real_runtime",
            label="REAL",
            outcome="NOT_EXECUTED_BLOCKED",
            detail="Gate D/real runtime outside T0-T5 fixture scope",
        ),
        label_observation(
            observation_id="claims_all_58_passed",
            label="STATIC",
            outcome="FALSE",
            detail="Never claim all 58 cases passed from B/C fixture",
        ),
    ]
    for control in negative_controls:
        name = str(control.get("control", "unknown"))
        if name == "production_fake":
            label = "FAKE"
        elif name in {
            "exposed_canary",
            "host_usr",
            "wrong_namespace",
            "extra_fd",
            "wrong_env",
        }:
            label = "DISPOSABLE_KERNEL"
        else:
            label = "STATIC"
        status = str(control.get("status", "UNKNOWN"))
        obs.append(
            label_observation(
                observation_id=f"negative_control:{name}",
                label=label,
                outcome=status,
                detail=str(control.get("independent_failure_reason", ""))[:200],
            )
        )
    for result in suite_results:
        name = str(result.get("name", "suite"))
        # Fixture/protocol suites are FAKE or STATIC — never REAL.
        label = "FAKE" if name in {"connector_node"} else "STATIC"
        rc = result.get("returncode")
        obs.append(
            label_observation(
                observation_id=f"suite:{name}",
                label=label,
                outcome=f"returncode={rc}",
                detail=(
                    f"elapsed_sec={result.get('elapsed_sec')};"
                    f"output_bytes={result.get('combined_output_bytes')};"
                    f"max_tmp_bytes={result.get('max_tmp_bytes')}"
                ),
            )
        )
    overall = "PASS" if outer_returncode == 0 else "FAIL"
    if outer_returncode is None:
        overall = "INCOMPLETE"
    obs.append(
        label_observation(
            observation_id="bounded_run_outcome",
            label="STATIC",
            outcome=overall,
            detail="fixture bounded run; not live qualification",
        )
    )
    return obs


# pylint: disable-next=R0913,R0914  # audit package arity/locals mirror closed evidence envelope inputs
def build_audit_package(
    *,
    plan_sha: str,
    source_commit: str,
    source_tree_sha256: str,
    test_runtime_tree_sha256: str,
    components: list[dict[str, str]],
    suite_results: list[dict[str, Any]],
    negative_controls: list[dict[str, Any]],
    changed_files: list[str],
    protected_byte_proof: list[dict[str, Any]],
    outer_returncode: int | None,
    preflight_ok: bool,
    code_baseline_sha: str = CODE_BASELINE_SHA,
    source_root: Path | None = None,
    containment_evidence: dict[str, Any] | None = None,
    selected_nodes_live: dict[str, Any] | None = None,
    mutant_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if plan_sha != SEMANTIC_PARENT_SHA:
        raise ValueError(f"plan_sha_mismatch:{plan_sha}")
    adversarial = build_adversarial_evidence_section(
        source_root=source_root,
        containment=containment_evidence,
        selected_nodes_live=selected_nodes_live,
        mutant_results=mutant_results,
    )
    package: dict[str, Any] = {
        "schema": SCHEMA_ID,
        "artifact_kind": ARTIFACT_KIND,
        "plan_sha": plan_sha,
        "source_commit": source_commit,
        "code_baseline_sha": code_baseline_sha,
        "source_tree_sha256": source_tree_sha256,
        "test_runtime_tree_sha256": test_runtime_tree_sha256,
        "components": components,
        "selected_suites": exact_selected_suites(),
        "legacy_exclusions": exact_legacy_exclusions(),
        "selected_test_files": exact_selected_test_files(),
        "tool_inventory": exact_tool_inventory(),
        "suite_discovery": suite_discovery_contract(),
        "suite_results": suite_results,
        "negative_controls": negative_controls,
        "changed_files": sorted(changed_files),
        "allowed_file_proof": build_allowed_file_proof(changed_files),
        "protected_byte_proof": protected_byte_proof,
        "adversarial_matrix": adversarial,
        "observations": default_observations(
            negative_controls=negative_controls,
            suite_results=suite_results,
            outer_returncode=outer_returncode,
        ),
        "outcomes": {
            "outer_returncode": outer_returncode,
            "preflight_ok": preflight_ok,
            "overall": (
                "PASS"
                if outer_returncode == 0
                else ("INCOMPLETE" if outer_returncode is None else "FAIL")
            ),
            "claims_live_readiness": False,
            "claims_real_auth_compatibility": False,
            "claims_production_sealing": False,
            "claims_all_58_passed": False,
            "claims_gate_d_pass": False,
            "claims_gate_w_pass": False,
            "claims_gate_e_pass": False,
        },
        "generated_paths": generated_evidence_paths(),
        "authority": authority_disclaimer(),
        "evidence_payload_sha256": "sha256:" + ("0" * 64),
    }
    package["evidence_payload_sha256"] = compute_evidence_payload_sha256(package)
    validate_audit_package(package)
    return package


def validate_audit_package(package: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in package]
    extra = [k for k in package if k not in REQUIRED_KEYS]
    if missing or extra:
        raise ValueError(f"audit_keys invalid missing={missing} extra={extra}")
    if package["schema"] != SCHEMA_ID:
        raise ValueError("schema")
    if package["artifact_kind"] != ARTIFACT_KIND:
        raise ValueError("artifact_kind")
    if package["legacy_exclusions"] != list(LEGACY_DESELECTS):
        raise ValueError("legacy_exclusions")
    if len(package["legacy_exclusions"]) != 4:
        raise ValueError("legacy_exclusion_count")
    if package["tool_inventory"] != exact_tool_inventory():
        raise ValueError("tool_inventory")
    if package["suite_discovery"]["full_repository_discovery"] is not False:
        raise ValueError("full_discovery_forbidden")
    if len(package["selected_suites"]) != 3:
        raise ValueError("suite_count")
    matrix = package["adversarial_matrix"]
    if matrix.get("claims_all_58_passed") is not False:
        raise ValueError("claims_all_58_passed")
    if matrix.get("threat_row_count") != 14:
        raise ValueError("threat_row_count")
    if not matrix.get("gate_b_cases") or not matrix.get("gate_c_fake_cases"):
        raise ValueError("gate_ownership_missing")
    blocked = matrix.get("blocked_later_gates") or {}
    for gate in ("gate_d", "gate_w", "gate_e"):
        if (blocked.get(gate) or {}).get("status") != "UNTESTED_BLOCKED":
            raise ValueError(f"later_gate_not_blocked:{gate}")
    nodes = matrix.get("selected_node_inventory") or {}
    if nodes.get("full_repository_discovery") is not False:
        raise ValueError("selected_nodes_full_discovery")
    if not package["allowed_file_proof"].get("all_changed_allowed", False):
        # Empty changed set is allowed; forbidden non-empty is not.
        if package["allowed_file_proof"].get("forbidden"):
            raise ValueError("allowed_file_proof_forbidden")
    for obs in package["observations"]:
        if obs["label"] not in EVIDENCE_LABELS:
            raise ValueError(f"bad_label:{obs['label']}")
        if obs["label"] == "REAL" and obs["outcome"] in {"PASS", "QUALIFIED", "GREEN"}:
            raise ValueError("real_pass_forbidden")
    if package["outcomes"].get("claims_all_58_passed") is not False:
        raise ValueError("outcomes_claims_all_58")
    expected = compute_evidence_payload_sha256(package)
    if package["evidence_payload_sha256"] != expected:
        raise ValueError("evidence_payload_sha256")
    for key, expected_true in authority_disclaimer().items():
        if package["authority"].get(key) is not expected_true:
            raise ValueError(f"authority:{key}")


def emit_audit_package(evidence_dir: Path, package: dict[str, Any]) -> Path:
    """Write canonical audit JSON under disposable evidence only."""

    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / Path(EVIDENCE_AUDIT_REL).name
    path.write_text(
        json.dumps(package, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return path


def generated_paths_excluded_from_fixture_inventory() -> frozenset[str]:
    return frozenset(GENERATED_EVIDENCE_FIXTURE_RELS)


def generated_paths_excluded_from_source_inventory() -> frozenset[str]:
    return frozenset(GENERATED_EVIDENCE_SOURCE_RELS)
