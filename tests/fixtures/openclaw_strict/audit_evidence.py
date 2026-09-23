"""M7 bounded audit evidence — attributable fixture-only run package.

Architecture / Execution parent (cd9d2698) + overlay M7 (d1ca459):
emit canonical inventories, evidence-class labels, suite selection/exclusions,
timing/output/tmp, negative controls, changed-file/protected-byte proof, and
outcomes under disposable ``/fixture/evidence`` only. Evidence is not approval,
signing, admission, qualification, manager emptiness, or promotion.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from constants import (
    CODE_BASELINE_SHA,
    CONNECTOR_NODE_TEST,
    EVIDENCE_AUDIT_REL,
    EVIDENCE_LABELS,
    EVIDENCE_MANIFEST_REL,
    EVIDENCE_SUITE_RESULTS_REL,
    GENERATED_EVIDENCE_FIXTURE_RELS,
    GENERATED_EVIDENCE_SOURCE_RELS,
    LEGACY_DESELECTS,
    LEGACY_PYTEST_FILES,
    SEMANTIC_PARENT_SHA,
    STRICT_PYTEST_FILES,
    STRICT_TOOL_NAMES,
)
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
    "protected_byte_proof",
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
            observation_id="openclaw_real_runtime",
            label="REAL",
            outcome="NOT_EXECUTED_BLOCKED",
            detail="Gate D/real runtime outside T0-T5 fixture scope",
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
) -> dict[str, Any]:
    if plan_sha != SEMANTIC_PARENT_SHA:
        raise ValueError(f"plan_sha_mismatch:{plan_sha}")
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
        "protected_byte_proof": protected_byte_proof,
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
    for obs in package["observations"]:
        if obs["label"] not in EVIDENCE_LABELS:
            raise ValueError(f"bad_label:{obs['label']}")
        if obs["label"] == "REAL" and obs["outcome"] in {"PASS", "QUALIFIED", "GREEN"}:
            raise ValueError("real_pass_forbidden")
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
