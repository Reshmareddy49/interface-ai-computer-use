import pytest
from agent.policy import assert_action_allowed, assert_url_allowed


def test_policy_blocks_unknown_action():
    with pytest.raises(PermissionError):
        assert_action_allowed("delete")


def test_policy_blocks_unknown_origin():
    with pytest.raises(PermissionError):
        assert_url_allowed("https://example.com")
