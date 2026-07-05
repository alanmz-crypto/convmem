"""Tests for unresolved JSON payload helpers."""

from unresolved import unresolved_items


def test_unresolved_items_strips_metadata():
    rows = [
        {
            "ledger_id": "obs_x",
            "severity": "low",
            "site": "example.com",
            "domain": "web",
            "title": "t",
            "status": "open",
            "last_touched": "",
            "summary": "d",
            "metadata": {"extra": "hidden"},
        }
    ]
    items = unresolved_items(rows)
    assert items[0]["site"] == "example.com"
    assert "metadata" not in items[0]
    assert set(items[0].keys()) == {
        "ledger_id",
        "severity",
        "site",
        "domain",
        "title",
        "status",
        "last_touched",
        "summary",
    }


def test_unresolved_payload_delegates(monkeypatch):
    from unresolved import unresolved_payload

    fake_rows = [
        {
            "ledger_id": "obs_abc123",
            "severity": "high",
            "site": "",
            "domain": "tooling.kiro",
            "title": "Gap",
            "status": "open",
            "last_touched": "2026-07-01",
            "summary": "summary text",
        }
    ]

    def _fake_list(_store, *, site=None, domain=None):
        assert site is None
        assert domain == "tooling.kiro"
        return fake_rows

    monkeypatch.setattr("unresolved.list_unresolved", _fake_list)
    payload = unresolved_payload(object(), domain="tooling.kiro")
    assert payload == {"count": 1, "items": unresolved_items(fake_rows)}
