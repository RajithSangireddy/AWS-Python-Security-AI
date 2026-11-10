import boto3
from botocore.stub import Stubber
from src.collector import list_iam_users
from datetime import datetime, timezone

def test_list_iam_users_success():
    iam = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing"
    )

    stubber = Stubber(iam)

    created_at = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)

    fake_response = {
        "Users": [
            {
            "UserName" : "alice",
            "UserId" : "AIDA1234567890123456",
            "Arn" : "arn:aws:iam::123456789012:user/alice",
            "Path" : "/", 
            "CreateDate" : created_at
            },
            {
            "UserName" : "bob",
            "UserId" : "AIDA1234567890123456",
            "Arn" : "arn:aws:iam::567890123456:user/bob",
            "Path" : "/", 
            "CreateDate" : created_at
            }
        ],
        "IsTruncated": False
    }

    stubber.add_response("list_users", fake_response, {})

    with stubber:
        result = list_iam_users(iam)

        #print(len(result))
        #rint(result[0]["UserName"])

    # --- OR----in test cases, assert is preffered than Print so that we know the test fails/success
        assert len(result) == 2
        assert result[0]["UserName"] == "alice"


def test_list_iam_users_empty():
    iam = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing"
    )

    stubber = Stubber(iam)

    fake_response = {
        "Users": [],
        "IsTruncated": False
    }

    stubber.add_response("list_users", fake_response, {})

    with stubber:
        result = list_iam_users(iam)

        #print(len(result))
        #rint(result[0]["UserName"])

    # --- OR----in test cases, assert is preffered than Print so that we know the test fails/success
        assert result == [] #chekcing if the result is empty
        #assert result[0]["UserName"] == "alice"

def test_list_iam_users_pagination():
    iam = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id="testing",
        aws_secret_access_key="testing"
    )

    stubber = Stubber(iam)
    created_at = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)

    page1 = {
            "Users": [
                {
                "UserName" : "alice",
                "UserId" : "AIDA1234567890123456",
                "Arn" : "arn:aws:iam::123456789012:user/alice",
                "Path" : "/", 
                "CreateDate" : created_at
                },
                {
                "UserName" : "bob",
                "UserId" : "AIDA1234567890123456",
                "Arn" : "arn:aws:iam::567890123456:user/bob",
                "Path" : "/", 
                "CreateDate" : created_at
                }
            ],
            "IsTruncated": True,
            "Marker" : "next-page-token"
    }
    page2 = {
                "Users": [
                    {
                    "UserName" : "charlie",
                    "UserId" : "ABCD1234567890123456",
                    "Arn" : "arn:aws:iam::123456789012:user/charlie",
                    "Path" : "/", 
                    "CreateDate" : created_at
                    },
                    {
                    "UserName" : "delta",
                    "UserId" : "EFGH1234567890123456",
                    "Arn" : "arn:aws:iam::567890123456:user/delta",
                    "Path" : "/", 
                    "CreateDate" : created_at
                    }
                ],
                "IsTruncated": False,
    }

    stubber.add_response("list_users", page1, {})
    stubber.add_response("list_users", page2, {"Marker": "next-page-token"})

    with stubber:
        result = list_iam_users(iam)

    stubber.assert_no_pending_responses()   
    assert len(result) == 4
    assert result[2]["UserName"] == "charlie"