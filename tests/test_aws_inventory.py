"""Tests for Module 03 IAM inventory orchestration.

Run from the repository root:
    python -m pytest tests/test_aws_inventory.py -v

These tests mock the collector functions at the point where aws_inventory.py
imports them. No AWS credentials or network requests are required.
"""

from unittest.mock import Mock, call, patch

import pytest

from src.aws_inventory import collect_aws_iam_inventory


# Patch names where collect_aws_iam_inventory looks them up, NOT in src.collector.
MODULE = "src.aws_inventory"


def test_empty_iam_inventory():
    """No users should produce all three keys, each with an empty list."""
    with patch(f"{MODULE}.list_iam_users", return_value=[]) as mock_users, \
         patch(f"{MODULE}.list_user_access_keys") as mock_keys, \
         patch(f"{MODULE}.list_iam_roles", return_value=[]) as mock_roles, \
         patch(f"{MODULE}.get_access_key_usage") as mock_usage, \
         patch(f"{MODULE}.normalize_access_key") as mock_normalize:
        iam = Mock(name="iam_client")
        inventory = collect_aws_iam_inventory(iam)

    assert inventory == {"users": [], "access_keys": [], "normalized_keys": [], "roles": [], "normalized_roles": [] }
    mock_users.assert_called_once_with(iam)
    mock_keys.assert_not_called()
    mock_usage.assert_not_called()
    mock_normalize.assert_not_called()


def test_multiple_users_and_access_keys():
    """Two users, two keys for Alice, none for Bob: check flow and call counts."""
    iam = Mock(name="iam_client")
    users = [{"UserName": "alice"}, {"UserName": "bob"}]
    keys = [
        {"UserName": "alice", "AccessKeyId": "AKIAEXAMPLE00000001", "Status": "Active"},
        {"UserName": "alice", "AccessKeyId": "AKIAEXAMPLE00000002", "Status": "Inactive"},
    ]
    usage = [
        {"last_used_at": None, "last_used_service": None, "last_used_region": None},
        {"last_used_at": "2026-01-01", "last_used_service": "s3", "last_used_region": "us-east-1"},
    ]
    normalized = [
        {"access_key_id": "AKIAEXAMPLE00000001", "status": "Active"},
        {"access_key_id": "AKIAEXAMPLE00000002", "status": "Inactive"},
    ]

    with patch(f"{MODULE}.list_iam_users", return_value=users) as mock_users, \
         patch(f"{MODULE}.list_user_access_keys", side_effect=[keys, []]) as mock_keys, \
         patch(f"{MODULE}.list_iam_roles", return_value=[]) as mock_roles, \
         patch(f"{MODULE}.get_access_key_usage", side_effect=usage) as mock_usage, \
         patch(f"{MODULE}.normalize_access_key", side_effect=normalized) as mock_normalize:

        inventory = collect_aws_iam_inventory(iam)

    assert inventory["users"] == users
    assert inventory["access_keys"] == keys
    assert inventory["normalized_keys"] == normalized
    mock_users.assert_called_once_with(iam)
    assert mock_keys.call_args_list == [call(iam, "alice"), call(iam, "bob")]
    assert mock_usage.call_args_list == [
        call(iam, "AKIAEXAMPLE00000001"),
        call(iam, "AKIAEXAMPLE00000002"),
    ]
    assert mock_normalize.call_count == 2
    assert mock_normalize.call_args_list[0].args[0] == {**keys[0], **usage[0]}
    assert mock_normalize.call_args_list[1].args[0] == {**keys[1], **usage[1]}

    # The original raw access-key dictionaries must not be mutated by update().
    assert "last_used_at" not in keys[0]
    assert "last_used_at" not in keys[1]


def test_users_with_no_access_keys():
    """A nonempty user list can legitimately have zero access keys."""
    iam = Mock(name="iam_client")
    users = [{"UserName": "alice"}]
    with patch(f"{MODULE}.list_iam_users", return_value=users), \
         patch(f"{MODULE}.list_user_access_keys", return_value=[]) as mock_keys, \
         patch(f"{MODULE}.list_iam_roles", return_value=[]) as mock_roles, \
         patch(f"{MODULE}.get_access_key_usage") as mock_usage, \
         patch(f"{MODULE}.normalize_access_key") as mock_normalize:
        inventory = collect_aws_iam_inventory(iam)

    assert inventory == {"users": users, "access_keys": [], "normalized_keys": [], "roles": [], "normalized_roles": [] }
    mock_keys.assert_called_once_with(iam, "alice")
    mock_usage.assert_not_called()
    mock_normalize.assert_not_called()


@pytest.mark.parametrize("failing_operation", ["list_iam_users", "list_user_access_keys", "get_access_key_usage", "normalize_access_key"])
def test_collector_failure_propagates(failing_operation):
    """Orchestration must not silently return partial inventory on a failure."""
    iam = Mock(name="iam_client")
    with patch(f"{MODULE}.list_iam_users", return_value=[{"UserName": "alice"}]) as mock_users, \
         patch(f"{MODULE}.list_user_access_keys", return_value=[{"UserName": "alice", "AccessKeyId": "AKIAEXAMPLE00000001"}]) as mock_keys, \
         patch(f"{MODULE}.get_access_key_usage", return_value={"last_used_at": None}) as mock_usage, \
         patch(f"{MODULE}.normalize_access_key", return_value={"access_key_id": "AKIAEXAMPLE00000001"}) as mock_normalize:
        targets = {
            "list_iam_users": mock_users,
            "list_user_access_keys": mock_keys,
            "get_access_key_usage": mock_usage,
            "normalize_access_key": mock_normalize,
        }
        targets[failing_operation].side_effect = RuntimeError("simulated collector failure")
        with pytest.raises(RuntimeError, match="simulated collector failure"):
            collect_aws_iam_inventory(iam)
