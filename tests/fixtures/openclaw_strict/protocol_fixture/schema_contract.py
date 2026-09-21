"""Draft 2020-12 meta-schema + instance validation for Gate B/C (T0b).

Uses the inventoried runtime `jsonschema` package inside the exact runner.
Filename → `$id` mapping is exact equality (not startswith). Cross-object
graph/history/receipt/file/OS invariants remain deferred to T1–T5.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from protocol_fixture.schema_instances import (
    ACTIVATION_CONTROL_VARIANTS,
    DEFERRED_CROSS_OBJECT_INVARIANTS,
    POSITIVE_BY_FILENAME,
)

# Exact 24 Gate B + 7 Gate C filenames → exact $id literals.
FILENAME_TO_ID: dict[str, str] = {
    "convmem-bound-read-scope-v2.schema.json": "convmem.bound-read-scope.v2",
    "convmem-project-binding-registry-v3.schema.json": "convmem.project-binding-registry.v3",
    "convmem-bound-authority-record-v3.schema.json": "convmem.bound-authority-record.v3",
    "convmem-authority-disposition-v1.schema.json": "convmem.authority-disposition.v1",
    "convmem-strict-provenance-context-v2.schema.json": "convmem.strict-provenance-context.v2",
    "convmem-strict-grounding-v1.schema.json": "convmem.strict-grounding.v1",
    "convmem-capture-receipt-v1.schema.json": "convmem.capture-receipt.v1",
    "convmem-strict-fixture-bundle-v2.schema.json": "convmem.strict-fixture-bundle.v2",
    "convmem-strict-citation-map-v1.schema.json": "convmem.strict-citation-map.v1",
    "convmem-bound-authority-manifest-v3.schema.json": "convmem.bound-authority-manifest.v3",
    "convmem-bound-projection-row-v2.schema.json": "convmem.bound-projection-row.v2",
    "convmem-strict-graph-v1.schema.json": "convmem.strict-graph.v1",
    "convmem-bound-projection-manifest-v3.schema.json": "convmem.bound-projection-manifest.v3",
    "convmem-strict-generation-layout-v2.schema.json": "convmem.strict-generation-layout.v2",
    "convmem-strict-publication-v2.schema.json": "convmem.strict-publication.v2",
    "convmem-strict-enrollment-v1.schema.json": "convmem.strict-enrollment.v1",
    "convmem-strict-slot-v1.schema.json": "convmem.strict-slot.v1",
    "convmem-strict-source-cutoff-v1.schema.json": "convmem.strict-source-cutoff.v1",
    "convmem-strict-semantic-contract-v1.schema.json": "convmem.strict-semantic-contract.v1",
    "convmem-strict-state-v2.schema.json": "convmem.strict-state.v2",
    "convmem-clock-review-v1.schema.json": "convmem.clock-review.v1",
    "convmem-raw-evidence-v3.schema.json": "convmem.raw-evidence.v3",
    "convmem-error-v1.schema.json": "convmem.error.v1",
    "convmem-strict-config-v2.schema.json": "convmem.strict-config.v2",
    "convmem-openclaw-connector-launch-v2.schema.json": "convmem.openclaw-connector-launch.v2",
    "convmem-openclaw-activation-v2.schema.json": "convmem.openclaw-activation.v2",
    "convmem-activation-control-v1.schema.json": "convmem.activation-control.v1",
    "convmem-activation-retirement-v1.schema.json": "convmem.activation-retirement.v1",
    "convmem-activation-launch-policy-v1.schema.json": "convmem.activation-launch-policy.v1",
    "convmem-activation-manager-policy-v1.schema.json": "convmem.activation-manager-policy.v1",
    "convmem-controller-socket-policy-v1.schema.json": "convmem.controller-socket-policy.v1",
}


def load_schema(schemas_root: Path, filename: str) -> dict[str, Any]:
    path = schemas_root / filename
    data = json.loads(path.read_text(encoding="utf-8"))
    expected_id = FILENAME_TO_ID[filename]
    if data.get("$id") != expected_id:
        raise AssertionError(f"id_mismatch:{filename}:got={data.get('$id')}:want={expected_id}")
    if data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise AssertionError(f"draft_mismatch:{filename}")
    return data


def _validator_cls():
    from jsonschema.validators import Draft202012Validator

    return Draft202012Validator


def meta_schema_check(schema: dict[str, Any]) -> None:
    Draft202012Validator = _validator_cls()
    Draft202012Validator.check_schema(schema)


def instance_validate(schema: dict[str, Any], instance: Any) -> None:
    Draft202012Validator = _validator_cls()
    Draft202012Validator(schema).validate(instance)


def instance_rejects(schema: dict[str, Any], instance: Any) -> bool:
    from jsonschema.exceptions import ValidationError

    Draft202012Validator = _validator_cls()
    try:
        Draft202012Validator(schema).validate(instance)
    except ValidationError:
        return True
    return False


def _top_level_object_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if "oneOf" in schema:
        # Prefer the status variant (fewest required) as the object shape for
        # generic negatives; activation-control also has dedicated variants.
        return schema["oneOf"][2]
    return schema


def build_negatives(schema: dict[str, Any], positive: dict[str, Any]) -> list[dict[str, Any]]:
    """Unknown key, missing required, wrong type, omitted required-null, plus enum/bound."""
    shape = _top_level_object_schema(schema)
    required = list(shape.get("required") or [])
    props = dict(shape.get("properties") or {})
    out: list[dict[str, Any]] = []

    unknown = copy.deepcopy(positive)
    unknown["__unknown_top_level__"] = True
    out.append({"name": "unknown_top_level_key", "instance": unknown})

    if required:
        missing = copy.deepcopy(positive)
        del missing[required[0]]
        out.append({"name": "missing_required_key", "instance": missing})

    # Wrong type: prefer a string property; fall back across common types.
    wrong = None
    for key, spec in props.items():
        if key not in positive or key == "schema":
            continue
        t = spec.get("type")
        if t == "string" or (isinstance(t, list) and "string" in t and positive[key] is not None):
            cand = copy.deepcopy(positive)
            cand[key] = 12345
            wrong = {"name": "wrong_type", "instance": cand}
            break
        if t == "integer":
            cand = copy.deepcopy(positive)
            cand[key] = "not-an-integer"
            wrong = {"name": "wrong_type", "instance": cand}
            break
        if t == "boolean":
            cand = copy.deepcopy(positive)
            cand[key] = "not-a-boolean"
            wrong = {"name": "wrong_type", "instance": cand}
            break
        if t == "object":
            cand = copy.deepcopy(positive)
            cand[key] = "not-an-object"
            wrong = {"name": "wrong_type", "instance": cand}
            break
        if t == "array":
            cand = copy.deepcopy(positive)
            cand[key] = "not-an-array"
            wrong = {"name": "wrong_type", "instance": cand}
            break
        if "enum" in spec and positive.get(key) is not None:
            cand = copy.deepcopy(positive)
            cand[key] = 12345
            wrong = {"name": "wrong_type", "instance": cand}
            break
    if wrong is not None:
        out.append(wrong)

    # Omitted required-null: required field whose type includes null must be present.
    null_case = None
    for key in required:
        spec = props.get(key) or {}
        t = spec.get("type")
        allows_null = t == "null" or (isinstance(t, list) and "null" in t)
        if not allows_null and "anyOf" in spec:
            allows_null = any(opt.get("type") == "null" for opt in spec["anyOf"])
        if not allows_null and "enum" in spec and None in spec["enum"]:
            allows_null = True
        if allows_null and key in positive:
            omitted = copy.deepcopy(positive)
            del omitted[key]
            null_case = {"name": "omitted_required_null", "instance": omitted}
            break
    if null_case is None:
        for key in required:
            if key in positive and positive[key] is None:
                omitted = copy.deepcopy(positive)
                del omitted[key]
                null_case = {"name": "omitted_required_null", "instance": omitted}
                break
    if null_case is None:
        # Schema has no nullable required top-level field: setting any required
        # non-schema field to null must still reject (null discipline).
        for key in required:
            if key == "schema":
                continue
            bad = copy.deepcopy(positive)
            bad[key] = None
            null_case = {"name": "omitted_required_null", "instance": bad}
            break
    if null_case is not None:
        out.append(null_case)

    # Conditional / enum / bound negatives where the schema defines them.
    for key, spec in props.items():
        if key not in positive:
            continue
        if "enum" in spec:
            bad = copy.deepcopy(positive)
            bad[key] = "__not_in_enum__"
            out.append({"name": f"enum_reject:{key}", "instance": bad})
            break
        if "const" in spec and key != "schema":
            bad = copy.deepcopy(positive)
            bad[key] = "__not_const__"
            out.append({"name": f"const_reject:{key}", "instance": bad})
            break
        if spec.get("type") == "integer" and "minimum" in spec:
            bad = copy.deepcopy(positive)
            bad[key] = spec["minimum"] - 1
            out.append({"name": f"bound_reject:{key}", "instance": bad})
            break
        if spec.get("type") == "integer" and "maximum" in spec:
            bad = copy.deepcopy(positive)
            bad[key] = spec["maximum"] + 1
            out.append({"name": f"bound_reject:{key}", "instance": bad})
            break

    return out


def run_all_schema_contract_checks(schemas_root: Path) -> dict[str, Any]:
    assert len(FILENAME_TO_ID) == 31
    assert set(FILENAME_TO_ID) == set(POSITIVE_BY_FILENAME)

    meta_ok = 0
    positive_ok = 0
    negative_ok = 0
    negative_total = 0
    activation_extra = 0

    for filename, expected_id in FILENAME_TO_ID.items():
        schema = load_schema(schemas_root, filename)
        assert schema["$id"] == expected_id
        meta_schema_check(schema)
        meta_ok += 1

        positive = POSITIVE_BY_FILENAME[filename]
        instance_validate(schema, positive)
        positive_ok += 1

        for neg in build_negatives(schema, positive):
            negative_total += 1
            if not instance_rejects(schema, neg["instance"]):
                raise AssertionError(f"negative_accepted:{filename}:{neg['name']}")
            negative_ok += 1

    # All four activation-control variants must validate.
    control_schema = load_schema(schemas_root, "convmem-activation-control-v1.schema.json")
    for name, variant in ACTIVATION_CONTROL_VARIANTS.items():
        instance_validate(control_schema, variant)
        activation_extra += 1

    return {
        "schema_count": 31,
        "meta_schema_ok": meta_ok,
        "positive_ok": positive_ok,
        "negative_ok": negative_ok,
        "negative_total": negative_total,
        "activation_control_variants_ok": activation_extra,
        "deferred_cross_object_invariants": list(DEFERRED_CROSS_OBJECT_INVARIANTS),
        "filename_to_id_exact": True,
    }
