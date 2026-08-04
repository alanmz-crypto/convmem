"""Tests for the frozen pre-C0a embedding-evaluation methodology contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval_corpus.methodology_contract import (
    MethodologyError,
    assert_c0b_contract_unchanged,
    load_methodology_v1,
    methodology_sha256,
    validate_methodology_v1,
)

FIXTURE = Path(__file__).parent / "fixtures" / "embedding_eval_methodology_v1.json"


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_frozen_methodology_fixture_is_valid_and_hashable():
    methodology = load_methodology_v1(FIXTURE)
    digest = methodology_sha256(methodology)
    assert len(digest) == 64
    assert methodology["production_output_dimension"] == 768
    assert methodology["ann"]["build_schedule"] == [
        "baseline-0",
        "challenger-0",
        "challenger-1",
        "baseline-1",
        "baseline-2",
        "challenger-2",
    ]


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("request_contract", "truncate", True, "truncate"),
        ("request_contract", "retry_count", 1, "retry_count"),
        ("statistics", "minimum_non_tied_groups", 0, "minimum_non_tied_groups"),
        ("ann", "seed_list", [123], "seed policy"),
        ("latency", "warm_residency_required", False, "latency"),
    ],
)
def test_frozen_choices_reject_changes(section, key, value, message):
    methodology = _load()
    methodology[section][key] = value
    with pytest.raises(MethodologyError, match=message):
        validate_methodology_v1(methodology)


def test_transform_bytes_and_hash_are_bound():
    methodology = _load()
    methodology["transforms"]["query"]["bytes_utf8"] = "query: "
    with pytest.raises(MethodologyError, match="sha256"):
        validate_methodology_v1(methodology)


def test_c0b_cannot_substitute_a_changed_methodology():
    methodology = _load()
    digest = methodology_sha256(methodology)
    assert_c0b_contract_unchanged(methodology, digest)
    with pytest.raises(MethodologyError, match="C0b methodology identity"):
        assert_c0b_contract_unchanged(methodology, "0" * 64)
