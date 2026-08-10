"""Strict validation for a versioned JudgeBench corpus package.

The corpus is human-governed evaluation data, not an informal collection of
JSON objects.  This module validates the manifest, case rows, gold rows,
rubric references, split counts, and content hashes before a canonical run can
use them.  Authoring tools may validate a proposed corpus; canonical execution
additionally requires Ryan's explicit lock metadata.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval_judgebench.contract_validate import validate_judgment_dict
from eval_judgebench.contracts import SemanticJudgmentV1
from eval_judgebench.rubric import load_rubric
from eval_judgebench.rubric_validate import validate_against_rubric

_CASE_FIELDS = {
    "case_id",
    "task_kind",
    "rubric_id",
    "instruction",
    "evidence",
    "candidate",
    "candidate_mode",
    "candidate_origin",
    "tags",
    "split",
}
_GOLD_FIELDS = {"case_id", "j0", "j1", "rationale", "lock"}
_J0_FIELDS = {"expected_pass", "expected_candidate_mode", "required_tokens"}
_LOCK_FIELDS = {"status", "owner", "locked_at"}
_EVIDENCE_FIELDS = {"id", "text"}
_ORIGIN_FIELDS = {
    "human_curated": {"kind", "author", "version"},
    "model_generated": {"kind", "model", "provider", "version"},
}
_SPLITS = {"calibration", "holdout"}
_CANDIDATE_MODES = {"answer", "abstain"}
_CITATION_RE = re.compile(r"\[(\d+)\]")


class CorpusValidationError(ValueError):
    """Raised when a JudgeBench corpus package violates its locked schema."""


@dataclass(frozen=True)
class CorpusValidation:
    """Validation result suitable for tests and authoring CLI output."""

    valid: bool
    violations: tuple[str, ...]
    case_count: int
    calibration_count: int
    holdout_count: int
    lock_status: str


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusValidationError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CorpusValidationError(f"JSON root must be an object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read object-only JSONL with line-addressable validation errors."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise CorpusValidationError(f"cannot read JSONL {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(lines, start=1):
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CorpusValidationError(
                f"invalid JSONL in {path} line {lineno}: {exc}"
            ) from exc
        if not isinstance(row, dict):
            raise CorpusValidationError(
                f"JSONL row must be an object in {path} line {lineno}"
            )
        rows.append(row)
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unknown_fields(row: dict[str, Any], allowed: set[str], label: str) -> list[str]:
    unknown = sorted(set(row) - allowed)
    return [f"{label}: unknown fields: {', '.join(unknown)}"] if unknown else []


def _required_text(value: Any, label: str, violations: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        violations.append(f"{label}: must be a non-empty string")


def _validate_case(row: dict[str, Any], rubric_dir: Path) -> list[str]:
    case_id = str(row.get("case_id") or "<missing>")
    label = f"case {case_id}"
    violations = _unknown_fields(row, _CASE_FIELDS, label)
    missing = sorted(_CASE_FIELDS - set(row))
    if missing:
        violations.append(f"{label}: missing fields: {', '.join(missing)}")
        return violations

    _required_text(row["case_id"], f"{label}.case_id", violations)
    task_kind = row["task_kind"]
    if task_kind not in {"synthesis", "summary"}:
        violations.append(f"{label}.task_kind: expected synthesis or summary")
    _required_text(row["rubric_id"], f"{label}.rubric_id", violations)
    _required_text(row["instruction"], f"{label}.instruction", violations)
    _required_text(row["candidate"], f"{label}.candidate", violations)
    if row["candidate_mode"] not in _CANDIDATE_MODES:
        violations.append(f"{label}.candidate_mode: expected answer or abstain")
    if row["split"] not in _SPLITS:
        violations.append(f"{label}.split: expected calibration or holdout")

    tags = row["tags"]
    if (
        not isinstance(tags, list)
        or not tags
        or any(not isinstance(tag, str) or not tag for tag in tags)
        or len(tags) != len(set(tags))
    ):
        violations.append(f"{label}.tags: expected unique non-empty strings")

    evidence = row["evidence"]
    if not isinstance(evidence, list) or not evidence:
        violations.append(f"{label}.evidence: expected a non-empty ordered list")
    else:
        ids: list[int] = []
        for index, item in enumerate(evidence, start=1):
            if not isinstance(item, dict):
                violations.append(f"{label}.evidence[{index}]: expected object")
                continue
            violations.extend(
                _unknown_fields(item, _EVIDENCE_FIELDS, f"{label}.evidence[{index}]")
            )
            if set(item) != _EVIDENCE_FIELDS:
                violations.append(
                    f"{label}.evidence[{index}]: requires exactly id and text"
                )
                continue
            if not isinstance(item["id"], int) or isinstance(item["id"], bool):
                violations.append(f"{label}.evidence[{index}].id: expected integer")
            else:
                ids.append(item["id"])
            _required_text(item["text"], f"{label}.evidence[{index}].text", violations)
        if ids and ids != list(range(1, len(ids) + 1)):
            violations.append(f"{label}.evidence: ids must be ordered 1..N")

    origin = row["candidate_origin"]
    if not isinstance(origin, dict):
        violations.append(f"{label}.candidate_origin: expected object")
    else:
        kind = origin.get("kind")
        allowed = _ORIGIN_FIELDS.get(str(kind))
        if allowed is None:
            violations.append(
                f"{label}.candidate_origin.kind: expected human_curated or model_generated"
            )
        elif set(origin) != allowed:
            violations.append(
                f"{label}.candidate_origin: {kind} requires exactly "
                f"{', '.join(sorted(allowed))}"
            )
        else:
            for key in allowed - {"kind"}:
                _required_text(origin[key], f"{label}.candidate_origin.{key}", violations)

    try:
        rubric = load_rubric(rubric_dir, str(row["rubric_id"]))
        if rubric.task != task_kind:
            violations.append(
                f"{label}: rubric task {rubric.task!r} != case task {task_kind!r}"
            )
    except (KeyError, ValueError) as exc:
        violations.append(f"{label}.rubric_id: {exc}")
    return violations


def _validate_gold(
    row: dict[str, Any],
    case: dict[str, Any] | None,
    rubric_dir: Path,
    *,
    require_locked: bool,
) -> list[str]:
    case_id = str(row.get("case_id") or "<missing>")
    label = f"gold {case_id}"
    violations = _unknown_fields(row, _GOLD_FIELDS, label)
    missing = sorted(_GOLD_FIELDS - set(row))
    if missing:
        violations.append(f"{label}: missing fields: {', '.join(missing)}")
        return violations
    if case is None:
        violations.append(f"{label}: no matching case")

    j0 = row["j0"]
    if not isinstance(j0, dict):
        violations.append(f"{label}.j0: expected object")
    else:
        violations.extend(_unknown_fields(j0, _J0_FIELDS, f"{label}.j0"))
        if set(j0) != _J0_FIELDS:
            violations.append(
                f"{label}.j0: requires exactly expected_pass, "
                "expected_candidate_mode, required_tokens"
            )
        else:
            if not isinstance(j0["expected_pass"], bool):
                violations.append(f"{label}.j0.expected_pass: expected boolean")
            if j0["expected_candidate_mode"] not in _CANDIDATE_MODES:
                violations.append(
                    f"{label}.j0.expected_candidate_mode: expected answer or abstain"
                )
            tokens = j0["required_tokens"]
            if not isinstance(tokens, list) or any(
                not isinstance(token, str) or not token for token in tokens
            ):
                violations.append(
                    f"{label}.j0.required_tokens: expected list of non-empty strings"
                )

    j1 = row["j1"]
    if not isinstance(j1, dict):
        violations.append(f"{label}.j1: expected object")
    else:
        structural = validate_judgment_dict(j1)
        violations.extend(f"{label}.j1: {item}" for item in structural.violations)
        if structural.valid and case is not None:
            judgment = SemanticJudgmentV1.from_dict(j1)
            try:
                rubric = load_rubric(rubric_dir, str(case["rubric_id"]))
                rubric_result = validate_against_rubric(judgment, rubric)
                violations.extend(
                    f"{label}.j1: {item}" for item in rubric_result.violations
                )
            except (KeyError, ValueError) as exc:
                violations.append(f"{label}.j1: cannot load rubric: {exc}")

    _required_text(row["rationale"], f"{label}.rationale", violations)
    lock = row["lock"]
    if not isinstance(lock, dict):
        violations.append(f"{label}.lock: expected object")
    else:
        violations.extend(_unknown_fields(lock, _LOCK_FIELDS, f"{label}.lock"))
        if set(lock) != _LOCK_FIELDS:
            violations.append(f"{label}.lock: requires status, owner, locked_at")
        else:
            if lock["status"] not in {"proposed", "locked"}:
                violations.append(f"{label}.lock.status: expected proposed or locked")
            if lock["owner"] != "Ryan":
                violations.append(f"{label}.lock.owner: expected Ryan")
            locked_at = lock["locked_at"]
            if lock["status"] == "locked":
                _required_text(locked_at, f"{label}.lock.locked_at", violations)
            elif locked_at is not None:
                violations.append(f"{label}.lock.locked_at: proposed rows require null")
            if require_locked and lock["status"] != "locked":
                violations.append(f"{label}.lock: canonical run requires Ryan lock")
    return violations


def _mechanical_outcome(case: dict[str, Any], gold: dict[str, Any]) -> bool:
    evidence_ids = {item["id"] for item in case["evidence"]}
    cited_ids = {int(value) for value in _CITATION_RE.findall(case["candidate"])}
    j0 = gold["j0"]
    violations = cited_ids - evidence_ids
    missing_tokens = [
        token for token in j0["required_tokens"] if token not in case["candidate"]
    ]
    wrong_mode = case["candidate_mode"] != j0["expected_candidate_mode"]
    return not violations and not missing_tokens and not wrong_mode


def validate_corpus(  # pylint: disable=too-many-branches,too-many-locals
    corpus_dir: Path | str,
    *,
    require_locked: bool = False,
) -> CorpusValidation:
    """Validate one corpus directory and return all discoverable violations."""
    root = Path(corpus_dir)
    manifest_path = root / "manifest.json"
    cases_path = root / "cases.jsonl"
    gold_path = root / "gold.jsonl"
    rubric_dir = root / "rubrics"
    try:
        manifest = _read_json(manifest_path)
        cases = read_jsonl(cases_path)
        gold_rows = read_jsonl(gold_path)
    except CorpusValidationError as exc:
        return CorpusValidation(False, (str(exc),), 0, 0, 0, "unknown")

    violations: list[str] = []
    case_by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        violations.extend(_validate_case(case, rubric_dir))
        case_id = str(case.get("case_id") or "")
        if case_id in case_by_id:
            violations.append(f"duplicate case_id: {case_id}")
        case_by_id[case_id] = case

    gold_by_id: dict[str, dict[str, Any]] = {}
    for gold in gold_rows:
        case_id = str(gold.get("case_id") or "")
        if case_id in gold_by_id:
            violations.append(f"duplicate gold case_id: {case_id}")
        gold_by_id[case_id] = gold
        violations.extend(
            _validate_gold(
                gold,
                case_by_id.get(case_id),
                rubric_dir,
                require_locked=require_locked,
            )
        )

    missing_gold = sorted(set(case_by_id) - set(gold_by_id))
    extra_gold = sorted(set(gold_by_id) - set(case_by_id))
    if missing_gold:
        violations.append(f"cases without gold: {', '.join(missing_gold)}")
    if extra_gold:
        violations.append(f"gold without cases: {', '.join(extra_gold)}")

    for case_id in sorted(set(case_by_id) & set(gold_by_id)):
        case = case_by_id[case_id]
        gold = gold_by_id[case_id]
        if not violations or (
            isinstance(case.get("evidence"), list)
            and isinstance(gold.get("j0"), dict)
            and set(gold["j0"]) == _J0_FIELDS
        ):
            try:
                actual = _mechanical_outcome(case, gold)
                expected = gold["j0"]["expected_pass"]
                if isinstance(expected, bool) and actual != expected:
                    violations.append(
                        f"gold {case_id}.j0.expected_pass={expected} "
                        f"but frozen case mechanically grades {actual}"
                    )
            except (KeyError, TypeError):
                pass

    case_ids = [str(case.get("case_id") or "") for case in cases]
    if manifest.get("case_count") != len(cases):
        violations.append(
            f"manifest.case_count={manifest.get('case_count')!r} != {len(cases)}"
        )
    if manifest.get("case_rows") != case_ids:
        violations.append("manifest.case_rows must exactly match cases.jsonl order")
    hashes = manifest.get("hashes")
    if not isinstance(hashes, dict):
        violations.append("manifest.hashes: expected object")
    else:
        for filename, path in (("cases.jsonl", cases_path), ("gold.jsonl", gold_path)):
            actual_hash = _sha256(path)
            if hashes.get(filename) != actual_hash:
                violations.append(f"manifest hash mismatch for {filename}")

    calibration_count = sum(case.get("split") == "calibration" for case in cases)
    holdout_count = sum(case.get("split") == "holdout" for case in cases)
    split_policy = manifest.get("split_policy")
    if not cases and split_policy is None:
        split_policy = {
            "calibration_count": 0,
            "holdout_count": 0,
            "minimum_holdout": 0,
        }
    if not isinstance(split_policy, dict):
        violations.append("manifest.split_policy: expected object")
    else:
        if split_policy.get("calibration_count") != calibration_count:
            violations.append("manifest calibration_count does not match cases")
        if split_policy.get("holdout_count") != holdout_count:
            violations.append("manifest holdout_count does not match cases")
        minimum = split_policy.get("minimum_holdout")
        if not isinstance(minimum, int) or holdout_count < minimum:
            violations.append("holdout split is below manifest minimum_holdout")

    lock_statuses = {
        str((row.get("lock") or {}).get("status") or "unknown") for row in gold_rows
    }
    lock_status = (
        "empty"
        if not gold_rows
        else next(iter(lock_statuses))
        if len(lock_statuses) == 1
        else "mixed"
    )
    manifest_lock = manifest.get("gold_lock")
    if not cases and manifest_lock is None:
        manifest_lock = {"status": "empty"}
    if not isinstance(manifest_lock, dict):
        violations.append("manifest.gold_lock: expected object")
    elif manifest_lock.get("status") != lock_status:
        violations.append("manifest.gold_lock.status does not match gold rows")
    if len(lock_statuses) > 1:
        violations.append("gold rows must share one lock status")
    if require_locked and cases and lock_status != "locked":
        violations.append("canonical run requires a uniformly Ryan-locked corpus")

    return CorpusValidation(
        valid=not violations,
        violations=tuple(violations),
        case_count=len(cases),
        calibration_count=calibration_count,
        holdout_count=holdout_count,
        lock_status=lock_status,
    )


def assert_corpus_valid(
    corpus_dir: Path | str,
    *,
    require_locked: bool = False,
) -> CorpusValidation:
    """Return validation or raise with a compact deterministic error message."""
    result = validate_corpus(corpus_dir, require_locked=require_locked)
    if not result.valid:
        raise CorpusValidationError("; ".join(result.violations))
    return result
