"""Draft 2020-12 meta-schema + instance validation for Gate B/C (T0b).

Uses the inventoried runtime `jsonschema` package inside the exact runner.
Filename → `$id` mapping is exact equality (not startswith). Cross-object
graph/history/receipt/file/OS invariants remain deferred to T1–T5.

Field-set comparisons use the independent parent-derived table in
`schema_field_sets.py` (not derived from schemas or positives).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import canonical_oracle as oracle_a  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
import canonical_oracle_b as oracle_b  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
from protocol_fixture import schema_field_sets as field_sets  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
from protocol_fixture.schema_instances import (  # pylint: disable=E0401  # fixture path-injection import; module resolved via sys.path
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


def assert_independent_field_table(schema: dict[str, Any], filename: str) -> None:
    """Compare schema properties/required against the parent-derived table."""
    if filename == "convmem-activation-control-v1.schema.json":
        assert "oneOf" in schema
        by_op: dict[str, dict[str, Any]] = {}
        for variant in schema["oneOf"]:
            op = variant["properties"]["op"]["const"]
            by_op[op] = variant
        assert set(by_op) == set(field_sets.ACTIVATION_CONTROL_VARIANTS_FIELDS)
        for op, expected in field_sets.ACTIVATION_CONTROL_VARIANTS_FIELDS.items():
            props, req = field_sets.schema_shape(by_op[op])
            assert props == expected, f"activation_props:{op}:{sorted(props)}!={sorted(expected)}"
            assert req == expected, f"activation_req:{op}:{sorted(req)}!={sorted(expected)}"
        return

    expected = field_sets.TOP_LEVEL[filename]
    props, req = field_sets.schema_shape(schema)
    assert props == expected, f"props:{filename}:{sorted(props)}!={sorted(expected)}"
    assert req == expected, f"required:{filename}:{sorted(req)}!={sorted(expected)}"


def _nested_item_schema(parent: dict[str, Any], key: str) -> dict[str, Any] | None:
    prop = (parent.get("properties") or {}).get(key)
    if not isinstance(prop, dict):
        return None
    if prop.get("type") == "object" and "properties" in prop:
        return prop
    items = prop.get("items")
    if isinstance(items, dict) and items.get("type") == "object" and "properties" in items:
        return items
    return None


def assert_nested_field_families(schemas_root: Path) -> int:  # pylint: disable=R0914,R0915  # nested field-family checks mirror closed schema contract cases
    """Compare nested frozen families and apply unknown/missing negatives."""
    checked = 0
    registry = load_schema(schemas_root, "convmem-project-binding-registry-v3.schema.json")
    binding = _nested_item_schema(registry, "bindings")
    assert binding is not None
    props, req = field_sets.schema_shape(binding)
    assert props == req == field_sets.NESTED["registry_binding"]
    checked += 1
    for key, family in (
        ("source_registrations", "registry_source"),
        ("capture_issuers", "registry_capture_issuer"),
        ("verification_producers", "registry_verification_producer"),
    ):
        nested = _nested_item_schema(binding, key)
        assert nested is not None, key
        props, req = field_sets.schema_shape(nested)
        assert props == req == field_sets.NESTED[family], family
        checked += 1

    ctx = load_schema(schemas_root, "convmem-strict-provenance-context-v2.schema.json")
    for key, family in (
        ("schema_semantics", "provenance_schema_semantics"),
        ("policies", "provenance_policy"),
        ("recipes", "provenance_recipe"),
        ("verified_channels", "provenance_verified_channel"),
        ("registered_assertions", "provenance_registered_assertion"),
    ):
        nested = _nested_item_schema(ctx, key)
        assert nested is not None, key
        props, req = field_sets.schema_shape(nested)
        assert props == req == field_sets.NESTED[family], family
        checked += 1
    policy = _nested_item_schema(ctx, "policies")
    assert policy is not None
    rule = _nested_item_schema(policy, "rules")
    assert rule is not None
    props, req = field_sets.schema_shape(rule)
    assert props == req == field_sets.NESTED["provenance_policy_rule"]
    checked += 1

    grounding = load_schema(schemas_root, "convmem-strict-grounding-v1.schema.json")
    for key, family in (
        ("blobs", "grounding_blob"),
        ("roots", "grounding_root"),
        ("edges", "grounding_edge"),
        ("outputs", "grounding_output"),
        ("receipts", "capture_receipt"),
    ):
        nested = _nested_item_schema(grounding, key)
        assert nested is not None, key
        props, req = field_sets.schema_shape(nested)
        assert props == req == field_sets.NESTED[family], family
        checked += 1

    fixture = load_schema(schemas_root, "convmem-strict-fixture-bundle-v2.schema.json")
    batch = _nested_item_schema(fixture, "batches")
    assert batch is not None
    props, req = field_sets.schema_shape(batch)
    assert props == req == field_sets.NESTED["fixture_batch"]
    checked += 1
    source = (batch.get("properties") or {}).get("source")
    assert isinstance(source, dict)
    props, req = field_sets.schema_shape(source)
    assert props == req == field_sets.NESTED["fixture_scan_source"]
    checked += 1
    record = _nested_item_schema(source, "records")
    assert record is not None
    props, req = field_sets.schema_shape(record)
    assert props == req == field_sets.NESTED["fixture_source_record"]
    checked += 1

    cite = load_schema(schemas_root, "convmem-strict-citation-map-v1.schema.json")
    entry = _nested_item_schema(cite, "citations")
    assert entry is not None
    props, req = field_sets.schema_shape(entry)
    assert props == req == field_sets.NESTED["citation_entry"]
    checked += 1

    cutoff = load_schema(schemas_root, "convmem-strict-source-cutoff-v1.schema.json")
    op = _nested_item_schema(cutoff, "operations")
    assert op is not None
    props, req = field_sets.schema_shape(op)
    assert props == req == field_sets.NESTED["source_cutoff_operation"]
    checked += 1

    sem = load_schema(schemas_root, "convmem-strict-semantic-contract-v1.schema.json")
    dig = _nested_item_schema(sem, "schema_digests")
    assert dig is not None
    props, req = field_sets.schema_shape(dig)
    assert props == req == field_sets.NESTED["semantic_schema_digest"]
    checked += 1

    state = load_schema(schemas_root, "convmem-strict-state-v2.schema.json")
    vin = _nested_item_schema(state, "verification_inputs")
    assert vin is not None
    props, req = field_sets.schema_shape(vin)
    assert props == req == field_sets.NESTED["strict_state_verification_input"]
    checked += 1

    graph = load_schema(schemas_root, "convmem-strict-graph-v1.schema.json")
    edge = _nested_item_schema(graph, "edges")
    assert edge is not None
    props, req = field_sets.schema_shape(edge)
    assert props == req == field_sets.NESTED["graph_edge"]
    checked += 1

    pub = load_schema(schemas_root, "convmem-strict-publication-v2.schema.json")
    anchor = (pub.get("properties") or {}).get("freshness_anchor")
    assert isinstance(anchor, dict)
    props, req = field_sets.schema_shape(anchor)
    assert props == req == field_sets.NESTED["publication_freshness_anchor"]
    checked += 1

    raw = load_schema(schemas_root, "convmem-raw-evidence-v3.schema.json")
    snap = (raw.get("properties") or {}).get("snapshot")
    assert isinstance(snap, dict)
    props, req = field_sets.schema_shape(snap)
    assert props == req == field_sets.NESTED["raw_evidence_snapshot"]
    checked += 1
    result = _nested_item_schema(raw, "results")
    assert result is not None
    props, req = field_sets.schema_shape(result)
    assert props == req == field_sets.NESTED["raw_evidence_result"]
    checked += 1

    err = load_schema(schemas_root, "convmem-error-v1.schema.json")
    err_obj = (err.get("properties") or {}).get("error")
    assert isinstance(err_obj, dict)
    props, req = field_sets.schema_shape(err_obj)
    assert props == req == field_sets.NESTED["error_object"]
    checked += 1

    launch = load_schema(schemas_root, "convmem-activation-launch-policy-v1.schema.json")
    processes = (launch.get("properties") or {}).get("processes")
    assert isinstance(processes, dict)
    props, req = field_sets.schema_shape(processes)
    assert props == req == field_sets.NESTED["launch_processes_roles"]
    checked += 1
    proc_entry = (processes.get("properties") or {}).get("supervisor")
    assert isinstance(proc_entry, dict)
    props, req = field_sets.schema_shape(proc_entry)
    assert props == req == field_sets.NESTED["launch_process_entry"]
    checked += 1
    for key in ("read_only_mounts", "writable_mounts"):
        mount = _nested_item_schema(launch, key)
        assert mount is not None, key
        props, req = field_sets.schema_shape(mount)
        assert props == req == field_sets.NESTED["launch_mount"]
        checked += 1
    endpoints = (launch.get("properties") or {}).get("endpoints")
    assert isinstance(endpoints, dict)
    props, req = field_sets.schema_shape(endpoints)
    assert props == req == field_sets.NESTED["launch_endpoints"]
    checked += 1

    # Nested unknown/missing negatives against positive instances.
    nested_neg = 0
    nested_neg += _nested_unknown_missing(
        load_schema(schemas_root, "convmem-project-binding-registry-v3.schema.json"),
        POSITIVE_BY_FILENAME["convmem-project-binding-registry-v3.schema.json"],
        ("bindings", 0),
    )
    nested_neg += _nested_unknown_missing(
        grounding,
        POSITIVE_BY_FILENAME["convmem-strict-grounding-v1.schema.json"],
        ("blobs", 0),
    )
    nested_neg += _nested_unknown_missing(
        grounding,
        POSITIVE_BY_FILENAME["convmem-strict-grounding-v1.schema.json"],
        ("roots", 0),
    )
    nested_neg += _nested_unknown_missing(
        grounding,
        POSITIVE_BY_FILENAME["convmem-strict-grounding-v1.schema.json"],
        ("receipts", 0),
    )
    nested_neg += _nested_unknown_missing(
        fixture,
        POSITIVE_BY_FILENAME["convmem-strict-fixture-bundle-v2.schema.json"],
        ("batches", 0, "source"),
    )
    nested_neg += _nested_unknown_missing(
        cite,
        POSITIVE_BY_FILENAME["convmem-strict-citation-map-v1.schema.json"],
        ("citations", 0),
    )
    nested_neg += _nested_unknown_missing(
        pub,
        POSITIVE_BY_FILENAME["convmem-strict-publication-v2.schema.json"],
        ("freshness_anchor",),
    )
    nested_neg += _nested_unknown_missing(
        raw,
        POSITIVE_BY_FILENAME["convmem-raw-evidence-v3.schema.json"],
        ("snapshot",),
    )
    nested_neg += _nested_unknown_missing(
        raw,
        POSITIVE_BY_FILENAME["convmem-raw-evidence-v3.schema.json"],
        ("results", 0),
    )
    nested_neg += _nested_unknown_missing(
        err,
        POSITIVE_BY_FILENAME["convmem-error-v1.schema.json"],
        ("error",),
    )
    nested_neg += _nested_unknown_missing(
        launch,
        POSITIVE_BY_FILENAME["convmem-activation-launch-policy-v1.schema.json"],
        ("endpoints",),
    )
    nested_neg += _nested_unknown_missing(
        launch,
        POSITIVE_BY_FILENAME["convmem-activation-launch-policy-v1.schema.json"],
        ("processes", "supervisor"),
    )
    if nested_neg < 20:
        raise AssertionError(f"nested_negatives_too_few:{nested_neg}")
    return checked + nested_neg


def _resolve_path(obj: Any, path: tuple[Any, ...]) -> Any:
    cur = obj
    for step in path:
        cur = cur[step]
    return cur


def _nested_unknown_missing(
    schema: dict[str, Any], positive: dict[str, Any], path: tuple[Any, ...]
) -> int:
    """Prove unknown-key and missing-required reject on one nested object."""
    target = _resolve_path(positive, path)
    if not isinstance(target, dict):
        raise AssertionError(f"nested_not_object:{path}")
    unknown = copy.deepcopy(positive)
    unk_target = _resolve_path(unknown, path)
    unk_target["__unknown_nested__"] = True
    if not instance_rejects(schema, unknown):
        raise AssertionError(f"nested_unknown_accepted:{path}")
    # Missing first required key present on the nested object.
    keys = list(target.keys())
    if not keys:
        raise AssertionError(f"nested_empty:{path}")
    missing = copy.deepcopy(positive)
    miss_target = _resolve_path(missing, path)
    del miss_target[keys[0]]
    if not instance_rejects(schema, missing):
        raise AssertionError(f"nested_missing_accepted:{path}")
    return 2


def assert_canonical_raw_roundtrip_and_rejects(positive: dict[str, Any], schema: dict[str, Any]) -> None:
    """Encode → strict parse (both oracles) → validate; reorder/duplicate reject first."""
    raw = oracle_a.encode_canonical_bytes(positive)
    assert raw == oracle_b.encode_canonical_bytes(positive)
    parsed_a = oracle_a.parse_strict_raw(raw)
    parsed_b = oracle_b.parse_strict_raw(raw)
    assert parsed_a == parsed_b == positive
    instance_validate(schema, parsed_a)

    # Reordered top-level keys (if >=2 keys): must reject before schema validation.
    keys = list(positive.keys())
    if len(keys) >= 2:
        # Force non-canonical key order in raw text.
        fragments = []
        for k in [keys[-1], *keys[:-1]]:
            frag = json.dumps({k: positive[k]}, ensure_ascii=False, separators=(",", ":"))
            fragments.append(frag[1:-1])  # strip braces
        reordered_raw = ("{" + ",".join(fragments) + "}").encode("utf-8")
        try:
            oracle_a.parse_strict_raw(reordered_raw)
        except oracle_a.CanonicalOracleError:
            pass
        else:
            # If encode happened to match canonical (single-key edge), skip.
            if reordered_raw != raw:
                raise AssertionError("reordered_raw_accepted")
        try:
            oracle_b.parse_strict_raw(reordered_raw)
        except oracle_b.CanonicalOracleBError:
            pass
        else:
            if reordered_raw != raw:
                raise AssertionError("reordered_raw_accepted_b")

    # Duplicate top-level key reject.
    first = keys[0]
    dup_raw = (
        b'{"'
        + first.encode("utf-8")
        + b'":'
        + json.dumps(positive[first], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + b',"'
        + first.encode("utf-8")
        + b'":'
        + json.dumps(positive[first], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + b"}"
    )
    try:
        oracle_a.parse_strict_raw(dup_raw)
    except oracle_a.CanonicalOracleError as exc:
        assert "duplicate_key" in str(exc)
    else:
        raise AssertionError("duplicate_key_accepted_a")
    try:
        oracle_b.parse_strict_raw(dup_raw)
    except oracle_b.CanonicalOracleBError as exc:
        assert "duplicate_key" in str(exc)
    else:
        raise AssertionError("duplicate_key_accepted_b")


def build_negatives(schema: dict[str, Any], positive: dict[str, Any]) -> list[dict[str, Any]]:  # pylint: disable=R0912  # negative specimen matrix branches mirror closed reject cases
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
        for key in required:
            if key == "schema":
                continue
            bad = copy.deepcopy(positive)
            bad[key] = None
            null_case = {"name": "omitted_required_null", "instance": bad}
            break
    if null_case is not None:
        out.append(null_case)

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
    assert set(FILENAME_TO_ID) - {"convmem-activation-control-v1.schema.json"} == set(
        field_sets.TOP_LEVEL
    )

    meta_ok = 0
    positive_ok = 0
    negative_ok = 0
    negative_total = 0
    activation_extra = 0
    field_table_ok = 0
    raw_roundtrip_ok = 0

    for filename, expected_id in FILENAME_TO_ID.items():
        schema = load_schema(schemas_root, filename)
        assert schema["$id"] == expected_id
        meta_schema_check(schema)
        meta_ok += 1

        assert_independent_field_table(schema, filename)
        field_table_ok += 1

        positive = POSITIVE_BY_FILENAME[filename]
        instance_validate(schema, positive)
        positive_ok += 1

        assert_canonical_raw_roundtrip_and_rejects(positive, schema)
        raw_roundtrip_ok += 1

        for neg in build_negatives(schema, positive):
            negative_total += 1
            if not instance_rejects(schema, neg["instance"]):
                raise AssertionError(f"negative_accepted:{filename}:{neg['name']}")
            negative_ok += 1

    control_schema = load_schema(schemas_root, "convmem-activation-control-v1.schema.json")
    for _name, variant in ACTIVATION_CONTROL_VARIANTS.items():
        instance_validate(control_schema, variant)
        assert_canonical_raw_roundtrip_and_rejects(variant, control_schema)
        activation_extra += 1

    nested_checked = assert_nested_field_families(schemas_root)

    return {
        "schema_count": 31,
        "meta_schema_ok": meta_ok,
        "positive_ok": positive_ok,
        "negative_ok": negative_ok,
        "negative_total": negative_total,
        "activation_control_variants_ok": activation_extra,
        "field_table_ok": field_table_ok,
        "raw_roundtrip_ok": raw_roundtrip_ok,
        "nested_families_checked": nested_checked,
        "deferred_cross_object_invariants": list(DEFERRED_CROSS_OBJECT_INVARIANTS),
        "filename_to_id_exact": True,
    }
