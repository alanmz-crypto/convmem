"""Canonical vector serialization tests."""

from __future__ import annotations

import math

import pytest

from eval_corpus.vector_fingerprint import (
    VectorIntegrityError,
    canonical_float32,
    matrix_fingerprint_v1,
    validate_vector,
    vector_fingerprint_v1,
)


def test_signed_zero_and_row_order_are_canonical():
    assert canonical_float32(-0.0) == 0.0
    assert vector_fingerprint_v1([0.0, 1.0]) == vector_fingerprint_v1([-0.0, 1.0])
    left = matrix_fingerprint_v1([("b", [0.2, 0.3]), ("a", [0.4, 0.5])])
    right = matrix_fingerprint_v1([("a", [0.4, 0.5]), ("b", [0.2, 0.3])])
    assert left == right


def test_vector_diagnostics_and_dimension_are_exact():
    info = validate_vector([0.0, 3.0, 4.0], expected_dimension=3)
    assert info["dimension"] == 3
    assert info["finite"] is True
    assert info["norm"] == 5.0
    with pytest.raises(VectorIntegrityError, match="dimension"):
        validate_vector([1.0], expected_dimension=2)


@pytest.mark.parametrize("bad", [[0.0, 0.0], [math.nan], [math.inf]])
def test_invalid_vectors_are_rejected(bad):
    with pytest.raises(VectorIntegrityError):
        validate_vector(bad)


def test_duplicate_matrix_ids_are_rejected():
    with pytest.raises(VectorIntegrityError, match="duplicate"):
        matrix_fingerprint_v1([("same", [1.0]), ("same", [2.0])])
