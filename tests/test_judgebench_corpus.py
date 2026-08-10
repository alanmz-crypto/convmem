"""Corpus-package validation for JudgeBench G3 human gold locking."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from eval_judgebench.corpus_validate import (
    CorpusValidationError,
    assert_corpus_valid,
    validate_corpus,
)

REPO = Path(__file__).resolve().parent.parent
CORPUS_ROOT = REPO / "eval_corpus/fixtures/judgebench/semantic-v1"
RUBRIC = (
    REPO
    / "eval_corpus/fixtures/judgebench/semantic-v1/rubrics/synthesis-grounded-v1.json"
)


def _write_package(
    root: Path,
    *,
    lock_status: str = "locked",
    locked_at: str | None = "2026-08-09",
) -> None:
    rubric_dir = root / "rubrics"
    rubric_dir.mkdir()
    (rubric_dir / RUBRIC.name).write_text(RUBRIC.read_text(encoding="utf-8"))
    case = {
        "case_id": "syn-cal-supported-01",
        "task_kind": "synthesis",
        "rubric_id": "synthesis-grounded-v1",
        "instruction": "Answer only from the evidence.",
        "evidence": [{"id": 1, "text": "The launch is Friday."}],
        "candidate": "The launch is Friday [1].",
        "candidate_mode": "answer",
        "candidate_origin": {
            "kind": "human_curated",
            "author": "Ryan",
            "version": "v1",
        },
        "tags": ["supported", "j0-pass"],
        "split": "calibration",
    }
    gold = {
        "case_id": case["case_id"],
        "j0": {
            "expected_pass": True,
            "expected_candidate_mode": "answer",
            "required_tokens": ["[1]"],
        },
        "j1": {
            "support": "full",
            "coverage": "complete",
            "contradiction": "none",
            "verdict": "pass",
        },
        "rationale": "Every material claim is supported by evidence 1.",
        "lock": {
            "status": lock_status,
            "owner": "Ryan",
            "locked_at": locked_at,
        },
    }
    cases_text = json.dumps(case, sort_keys=True) + "\n"
    gold_text = json.dumps(gold, sort_keys=True) + "\n"
    (root / "cases.jsonl").write_text(cases_text, encoding="utf-8")
    (root / "gold.jsonl").write_text(gold_text, encoding="utf-8")
    manifest = {
        "manifest_version": "judgebench-semantic-v1",
        "corpus": "judgebench",
        "bucket": "semantic-v1",
        "schema": "JudgeBenchCorpusV1",
        "rubric_dir": "rubrics/",
        "case_count": 1,
        "case_rows": [case["case_id"]],
        "split_policy": {
            "strategy": "stratified",
            "calibration_count": 1,
            "holdout_count": 0,
            "minimum_holdout": 0,
        },
        "gold_lock": {"status": lock_status, "owner": "Ryan"},
        "hashes": {
            "cases.jsonl": hashlib.sha256(cases_text.encode()).hexdigest(),
            "gold.jsonl": hashlib.sha256(gold_text.encode()).hexdigest(),
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_locked_package_is_valid(tmp_path: Path) -> None:
    _write_package(tmp_path)
    result = assert_corpus_valid(tmp_path, require_locked=True)
    assert result.valid
    assert result.case_count == 1
    assert result.lock_status == "locked"


def test_proposed_package_is_valid_for_review_but_not_canonical(tmp_path: Path) -> None:
    _write_package(tmp_path, lock_status="proposed", locked_at=None)
    assert validate_corpus(tmp_path).valid
    with pytest.raises(CorpusValidationError, match="Ryan lock"):
        assert_corpus_valid(tmp_path, require_locked=True)


def test_locked_g3_fixture_is_valid_for_canonical_use() -> None:
    result = assert_corpus_valid(CORPUS_ROOT, require_locked=True)
    assert result.case_count == 30
    assert result.calibration_count == 20
    assert result.holdout_count == 10
    assert result.lock_status == "locked"


def test_hash_change_is_rejected(tmp_path: Path) -> None:
    _write_package(tmp_path)
    with (tmp_path / "cases.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    result = validate_corpus(tmp_path)
    assert not result.valid
    assert "manifest hash mismatch for cases.jsonl" in result.violations


def test_split_count_mismatch_is_rejected(tmp_path: Path) -> None:
    _write_package(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["split_policy"]["calibration_count"] = 0
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = validate_corpus(tmp_path)
    assert not result.valid
    assert "manifest calibration_count does not match cases" in result.violations


def test_declared_j0_outcome_must_match_frozen_case(tmp_path: Path) -> None:
    _write_package(tmp_path)
    gold_path = tmp_path / "gold.jsonl"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    gold["j0"]["expected_pass"] = False
    gold_text = json.dumps(gold, sort_keys=True) + "\n"
    gold_path.write_text(gold_text, encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["hashes"]["gold.jsonl"] = hashlib.sha256(gold_text.encode()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = validate_corpus(tmp_path)
    assert not result.valid
    assert any("mechanically grades True" in item for item in result.violations)
