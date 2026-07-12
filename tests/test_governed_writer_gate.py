import pytest

from observe import _reject_governed_bypass


def test_governed_decision_upsert_requires_protocol_marker():
    with pytest.raises(ValueError, match="proposal_id"):
        _reject_governed_bypass({"id": "dec_shared"}, upsert=True)


def test_protocol_marker_and_non_governed_writers_are_allowed():
    _reject_governed_bypass({"id": "dec_shared", "proposal_id": "dec_prop_x"}, upsert=True)
    _reject_governed_bypass({"id": "obs_x"}, upsert=True)
