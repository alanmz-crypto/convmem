"""Canonical real-pilot query-set validation tests."""

from __future__ import annotations

import pytest

from eval_corpus.query_set import (
    APPROVED_DOMAINS,
    QuerySetValidationError,
    normalized_query_sha256,
    validate_canonical_real_query_set,
)


def _package() -> list[dict]:
    return [
        {
            "id": f"unit-{index}",
            "ledger_id": f"ledger-{index}",
            "document_recipe_version": "ordinary_summary_keywords@v1",
        }
        for index in range(40)
    ]


def _rows() -> list[dict]:
    rows: list[dict] = []
    for domain_index, domain in enumerate(APPROVED_DOMAINS):
        for offset in range(8):
            index = domain_index * 8 + offset
            query = f"representative {domain} question {offset}"
            rows.append(
                {
                    "query_id": f"{domain}.{offset:02d}",
                    "domain": domain,
                    "query": query,
                    "query_normalized_sha256": normalized_query_sha256(query),
                    "relevant": [
                        {"namespace": "unit_id", "id": f"unit-{index}", "grade": 1}
                    ],
                    "relevant_complete": False,
                    "recipe_stratum": "ordinary",
                    "top_k": 5,
                    "source_refs": [{"namespace": "unit_id", "id": f"unit-{index}"}],
                    "source_group_id": f"group-{index}",
                    "author": "test-author",
                    "reviewer": "test-reviewer",
                }
            )
    return rows


def test_canonical_real_query_set_validates_exact_domain_design():
    report = validate_canonical_real_query_set(_rows(), _package())
    assert report["schema_version"] == "canonical_real_v1"
    assert report["row_count"] == 40
    assert report["domain_counts"] == {domain: 8 for domain in APPROVED_DOMAINS}


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda row: row.update(acceptable_ids=["ledger-0"]), "acceptable_ids"),
        (lambda row: row.update(query_id=""), "query_id"),
        (lambda row: row.update(top_k=4), "top_k"),
        (lambda row: row.update(source_refs=[]), "source_refs"),
        (lambda row: row.update(query_normalized_sha256="0" * 64), "normalized_sha256"),
    ],
)
def test_canonical_query_rejects_schema_mutations(mutator, message):
    rows = _rows()
    mutator(rows[0])
    with pytest.raises(QuerySetValidationError, match=message):
        validate_canonical_real_query_set(rows, _package())


def test_duplicate_ledger_ids_are_rejected_before_query_resolution():
    package = _package()
    package[1]["ledger_id"] = package[0]["ledger_id"]
    with pytest.raises(QuerySetValidationError, match="ambiguous ledger_id"):
        validate_canonical_real_query_set(_rows(), package)


def test_relevance_aliases_are_rejected():
    rows = _rows()
    rows[0]["relevant"] = [
        {"namespace": "unit_id", "id": "unit-0", "grade": 1},
        {"namespace": "ledger_id", "id": "ledger-0", "grade": 1},
    ]
    with pytest.raises(QuerySetValidationError, match="aliases"):
        validate_canonical_real_query_set(rows, _package())


def test_completeness_requires_review_evidence():
    rows = _rows()
    rows[0]["relevant_complete"] = True
    with pytest.raises(QuerySetValidationError, match="completeness_evidence"):
        validate_canonical_real_query_set(rows, _package())


def test_source_group_cannot_span_domains():
    rows = _rows()
    rows[8]["source_group_id"] = rows[0]["source_group_id"]
    with pytest.raises(QuerySetValidationError, match="spans domains"):
        validate_canonical_real_query_set(rows, _package())
