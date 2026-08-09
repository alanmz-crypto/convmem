"""JudgeBench offline semantic calibration runner (JudgeBench T4).

Frozen case -> J0 (deterministic mechanical grade) -> J1 (semantic judge) ->
compare with locked gold. Chroma is prohibited in this import graph. Provider
failures surface as provider_error/not_run, never as semantic FAIL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from eval_judgebench.contract_validate import validate_judgment_dict
from eval_judgebench.contracts import (
    IndependenceClass,
    InvocationStatus,
    JudgeInvocationV1,
    SelectionRole,
    SemanticJudgmentV1,
)
from eval_judgebench.rubric_validate import validate_judgment_against_rubric_file
from eval_model_identity import (
    assert_canonical_preflight,
    classify_independence,
    load_registry,
    resolve_identity,
)
from eval_provenance import (
    attach_comparison_signature,
    build_comparison_signature,
    fixture_hash,
    model_context,
    ollama_version,
)

SemanticJudgeFn = Callable[[dict[str, Any]], JudgeInvocationV1]


class CorpusLoadError(ValueError):
    """Raised when corpus files are missing or corrupt."""


@dataclass
class MechanicalGrade:
    passed: bool
    violations: list[str] = field(default_factory=list)


@dataclass
class CaseResult:
    case_id: str
    mechanical: MechanicalGrade
    invocation: JudgeInvocationV1 | None
    gold_verdict: str | None
    agrees_with_gold: bool | None


@dataclass
class RunResult:
    cases: list[CaseResult]
    independence_class: IndependenceClass
    comparison_signature: dict[str, Any]
    provenance: dict[str, Any]
    gold_hash_before: str
    gold_hash_after: str
    pinned_judge_model: str


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise CorpusLoadError(f"missing corpus file: {path}")
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CorpusLoadError(f"invalid JSONL in {path} line {lineno}: {exc}") from exc
        if not isinstance(row, dict):
            raise CorpusLoadError(f"JSONL row must be object in {path} line {lineno}")
        rows.append(row)
    return rows


def load_corpus(corpus_dir: Path | str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load manifest, cases, and gold keyed by case id."""
    root = Path(corpus_dir)
    manifest_path = root / "manifest.json"
    cases_path = root / "cases.jsonl"
    gold_path = root / "gold.jsonl"
    if not manifest_path.is_file():
        raise CorpusLoadError(f"missing manifest: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusLoadError(f"invalid manifest JSON: {exc}") from exc
    cases = _read_jsonl(cases_path)
    gold_rows = _read_jsonl(gold_path)
    gold_by_id = {str(row.get("case_id") or row.get("id")): row for row in gold_rows}
    return manifest, cases, gold_by_id


def grade_mechanical(case: dict[str, Any], gold: dict[str, Any] | None) -> MechanicalGrade:
    """Deterministic J0 checks declared in the fixture (no LLM)."""
    violations: list[str] = []
    case_id = case.get("case_id") or case.get("id")
    if not case_id:
        violations.append("case missing case_id")
    if not case.get("rubric_id"):
        violations.append("case missing rubric_id")
    if gold is None:
        violations.append(f"no gold row for case {case_id!r}")
    else:
        expected_mode = gold.get("expected_candidate_mode")
        actual_mode = case.get("candidate_mode")
        if expected_mode is not None and actual_mode != expected_mode:
            violations.append(
                f"candidate_mode {actual_mode!r} != expected {expected_mode!r}"
            )
    return MechanicalGrade(passed=not violations, violations=violations)


def _compare_verdict(invocation: JudgeInvocationV1 | None, gold: dict[str, Any] | None) -> bool | None:
    if gold is None or invocation is None:
        return None
    if invocation.status != InvocationStatus.OK or invocation.semantic_judgment is None:
        return None
    expected = gold.get("verdict")
    if expected is None:
        return None
    return invocation.semantic_judgment.verdict.value == expected


def _validate_judgment_output(
    raw: dict[str, Any],
    rubric_id: str,
    rubric_dir: Path,
) -> tuple[SemanticJudgmentV1 | None, InvocationStatus, str | None]:
    validation = validate_judgment_dict(raw)
    if not validation.valid:
        return None, validation.as_status(), "; ".join(validation.violations)
    judgment = SemanticJudgmentV1.from_dict(raw)
    rubric_result = validate_judgment_against_rubric_file(judgment, rubric_dir, rubric_id)
    if not rubric_result.valid:
        return None, InvocationStatus.INVALID_OUTPUT, "; ".join(rubric_result.violations)
    return judgment, InvocationStatus.OK, None


def run_case(
    case: dict[str, Any],
    *,
    gold: dict[str, Any] | None,
    rubric_dir: Path,
    judge_identity: str,
    under_test_identity: str,
    independence: IndependenceClass,
    semantic_judge: SemanticJudgeFn | None,
) -> CaseResult:
    """Run J0 + optional J1 for a single frozen case."""
    case_id = str(case.get("case_id") or case.get("id") or "")
    mechanical = grade_mechanical(case, gold)
    invocation: JudgeInvocationV1 | None = None
    if semantic_judge is None:
        invocation = JudgeInvocationV1(
            status=InvocationStatus.NOT_RUN,
            judge_identity=judge_identity,
            under_test_identity=under_test_identity,
            independence_class=independence,
            failure_code="no_semantic_judge",
        )
    else:
        try:
            invocation = semantic_judge(case)
        except Exception as exc:  # provider failure must not become semantic FAIL
            invocation = JudgeInvocationV1(
                status=InvocationStatus.PROVIDER_ERROR,
                judge_identity=judge_identity,
                under_test_identity=under_test_identity,
                independence_class=independence,
                failure_code=f"{type(exc).__name__}: {exc}",
            )
    return CaseResult(
        case_id=case_id,
        mechanical=mechanical,
        invocation=invocation,
        gold_verdict=(gold or {}).get("verdict"),
        agrees_with_gold=_compare_verdict(invocation, gold),
    )


def run_judgebench(
    corpus_dir: Path | str,
    *,
    cfg: dict,
    judge_model: str,
    under_test_model: str,
    registry_path: Path | str,
    semantic_judge: SemanticJudgeFn | None = None,
    canonical: bool = True,
    temperature: float = 0.0,
    metric_policy_version: str = "judgebench-v1",
) -> RunResult:
    """Execute JudgeBench offline calibration for a frozen corpus directory."""
    root = Path(corpus_dir)
    gold_path = root / "gold.jsonl"
    gold_hash_before = fixture_hash(gold_path)
    registry = load_registry(registry_path)
    judge_ident = resolve_identity(judge_model, registry, cfg)
    under_ident = resolve_identity(under_test_model, registry, cfg)
    independence = classify_independence(
        judge_ident,
        under_ident,
        under_test_human_curated=bool(cfg.get("under_test_human_curated")),
    )
    if canonical:
        assert_canonical_preflight(independence)

    manifest, cases, gold_by_id = load_corpus(root)
    rubric_dir = root / str(manifest.get("rubric_dir") or "rubrics")
    pinned_judge = judge_model.strip()

    results: list[CaseResult] = []
    for case in cases:
        case_id = str(case.get("case_id") or case.get("id") or "")
        results.append(
            run_case(
                case,
                gold=gold_by_id.get(case_id),
                rubric_dir=rubric_dir,
                judge_identity=judge_ident.normalized_name,
                under_test_identity=under_ident.normalized_name,
                independence=independence,
                semantic_judge=semantic_judge,
            )
        )

    gold_hash_after = fixture_hash(gold_path)
    signature = build_comparison_signature(
        evaluation_surface=str(manifest.get("manifest_version") or "judgebench"),
        case_hash=fixture_hash(root / "cases.jsonl"),
        fixture_hash_value=fixture_hash(root / "manifest.json"),
        gold_hash=gold_hash_after,
        identity_policy_version=registry.version,
        resolved_identities={
            "judge": judge_ident.to_record_dict(),
            "under_test": under_ident.to_record_dict(),
        },
        judge_pin={
            "model": pinned_judge,
            "lineage": judge_ident.base_lineage,
            "digest": judge_ident.revision_digest,
            "quant": judge_ident.quantization,
            "role": SelectionRole.PRIMARY.value,
        },
        under_test_provenance=under_ident.to_record_dict(),
        independence_class=independence.value,
        decoding_params={"temperature": temperature},
        model_serving_version=ollama_version(cfg),
        metric_policy_version=metric_policy_version,
    )
    provenance = attach_comparison_signature(
        model_context(cfg, under_test_model, root / "cases.jsonl"),
        signature,
    )
    return RunResult(
        cases=results,
        independence_class=independence,
        comparison_signature=signature,
        provenance=provenance,
        gold_hash_before=gold_hash_before,
        gold_hash_after=gold_hash_after,
        pinned_judge_model=pinned_judge,
    )


def parse_semantic_judge_output(
    raw: dict[str, Any],
    *,
    rubric_id: str,
    rubric_dir: Path,
    judge_identity: str,
    under_test_identity: str,
    independence: IndependenceClass,
) -> JudgeInvocationV1:
    """Helper to turn raw judge JSON into a JudgeInvocationV1."""
    judgment, status, failure = _validate_judgment_output(raw, rubric_id, rubric_dir)
    return JudgeInvocationV1(
        status=status,
        judge_identity=judge_identity,
        under_test_identity=under_test_identity,
        independence_class=independence,
        failure_code=failure,
        semantic_judgment=judgment,
    )
