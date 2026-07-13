from ledger_content_hash import SEMANTIC_FIELDS, ledger_content_hash


def base():
    return {field: (["x"] if field in ("alternatives_rejected", "constraints") else "x") for field in SEMANTIC_FIELDS}


def test_each_semantic_field_changes_hash():
    original = base()
    digest = ledger_content_hash(original)
    for field in SEMANTIC_FIELDS:
        changed = dict(original)
        changed[field] = ["changed"] if field in ("alternatives_rejected", "constraints") else "changed"
        assert ledger_content_hash(changed) != digest, field


def test_operational_fields_do_not_change_hash_and_unicode_is_nfc():
    record = base()
    record["summary"] = "café"
    equivalent = dict(record, proposal_id="p1", timestamp="later", tool="x")
    equivalent["summary"] = "cafe\u0301"
    assert ledger_content_hash(record) == ledger_content_hash(equivalent)
