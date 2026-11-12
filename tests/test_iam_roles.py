"""Module 04: IAM role collection, trust-policy extraction, and orchestration.

Run from repository root:
    python -m pytest tests/test_iam_roles.py -v

No AWS credentials or network calls required.
"""

from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import EndpointConnectionError

from src.collector import list_iam_roles, normalize_role_trust_policy
from src.aws_inventory import collect_aws_iam_inventory


def make_role(name, statements):
    return {
        "RoleName": name,
        "Arn": f"arn:aws:iam::123456789012:role/{name}",
        "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": statements},
    }


def test_list_roles_collects_all_pages_as_dictionaries():
    roles_page_1 = [make_role("RoleA", []), make_role("RoleB", [])]
    roles_page_2 = [make_role("RoleC", [])]
    iam = Mock()
    paginator = iam.get_paginator.return_value
    paginator.paginate.return_value = iter([
        {"Roles": roles_page_1},
        {"Roles": roles_page_2},
    ])

    result = list_iam_roles(iam)

    iam.get_paginator.assert_called_once_with("list_roles")
    paginator.paginate.assert_called_once_with()
    assert result == roles_page_1 + roles_page_2
    assert all(isinstance(role, dict) for role in result)


def test_list_roles_empty_response():
    iam = Mock()
    iam.get_paginator.return_value.paginate.return_value = iter([{"Roles": []}])
    assert list_iam_roles(iam) == []


def test_normalizer_preserves_multiple_statements_and_conditions():
    statements = [
        {"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"},
        {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
            "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"sts:ExternalId": "example-only"}},
        },
    ]
    role = make_role("MultiStatementRole", statements)

    result = normalize_role_trust_policy(role)

    assert result["role_name"] == "MultiStatementRole"
    assert result["role_arn"] == role["Arn"]
    assert result["trust_statements"] == statements
    assert len(result["trust_statements"]) == 2
    assert result["trust_statements"][1]["Condition"] == statements[1]["Condition"]


def test_normalizer_wraps_single_statement_dictionary_in_list():
    statement = {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}
    role = make_role("SingleStatementRole", statement)

    result = normalize_role_trust_policy(role)

    assert result["trust_statements"] == [statement]
    assert isinstance(result["trust_statements"], list)
    # Normalization must not change the original AWS response.
    assert role["AssumeRolePolicyDocument"]["Statement"] == statement


def test_list_roles_sdk_failure_propagates():
    iam = Mock()
    iam.get_paginator.return_value.paginate.side_effect = EndpointConnectionError(endpoint_url="https://iam.amazonaws.com")
    with pytest.raises(RuntimeError, match="AWS SDK error"):
        list_iam_roles(iam)


def test_inventory_includes_raw_and_normalized_roles():
    roles = [
        make_role("RoleA", [{"Effect": "Allow", "Action": "sts:AssumeRole", "Principal": {"Service": "ec2.amazonaws.com"}}]),
        make_role("RoleB", [{"Effect": "Allow", "Action": "sts:AssumeRole", "Principal": {"Service": "lambda.amazonaws.com"}}]),
    ]
    iam = Mock()
    with patch("src.aws_inventory.list_iam_users", return_value=[]), \
         patch("src.aws_inventory.list_iam_roles", return_value=roles) as mock_list_roles:
        result = collect_aws_iam_inventory(iam)

    mock_list_roles.assert_called_once_with(iam)
    assert result["roles"] == roles
    assert len(result["normalized_roles"]) == 2
    assert [r["role_name"] for r in result["normalized_roles"]] == ["RoleA", "RoleB"]
    assert [r["role_arn"] for r in result["normalized_roles"]] == [r["Arn"] for r in roles]
    assert result["users"] == []
    assert result["access_keys"] == []
    assert result["normalized_keys"] == []


def test_inventory_role_collector_failure_propagates():
    iam = Mock()
    with patch("src.aws_inventory.list_iam_users", return_value=[]), \
         patch("src.aws_inventory.list_iam_roles", side_effect=RuntimeError("role collection failed")):
        with pytest.raises(RuntimeError, match="role collection failed"):
            collect_aws_iam_inventory(iam)
