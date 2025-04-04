import pytest
from unittest.mock import patch, MagicMock
from tfbootstrap.aws_account_manager import AWSAccountManager

@pytest.fixture
def mock_org_client():
    mock = MagicMock()
    mock.get_paginator.return_value.paginate.return_value = [
        {"Accounts": [{"Id": "123456789012", "Email": "test@example.com"}]}
    ]
    return mock

@pytest.fixture
def mock_boto_session(mock_org_client):
    with patch("boto3.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session_instance.client.return_value = mock_org_client
        mock_session.return_value = mock_session_instance
        yield mock_session_instance

@pytest.fixture
def manager(mock_boto_session):
    return AWSAccountManager(profile_name="mock-profile")

@patch("time.sleep", return_value=None)
def test_create_account_success(_, manager, mock_org_client):
    mock_org_client.create_account.return_value = {
        "CreateAccountStatus": {"Id": "test-id"}
    }
    mock_org_client.describe_create_account_status.return_value = {
        "CreateAccountStatus": {
            "Id": "test-id",
            "State": "SUCCEEDED",
            "AccountId": "123456789012"
        }
    }

    result = manager.create_account("TestAccount", "test@example.com")
    assert result == "123456789012"

@patch("time.sleep", return_value=None)
def test_create_account_failure(_, manager, mock_org_client):
    mock_org_client.create_account.return_value = {
        "CreateAccountStatus": {"Id": "fail-id"}
    }
    mock_org_client.describe_create_account_status.return_value = {
        "CreateAccountStatus": {
            "Id": "fail-id",
            "State": "FAILED",
            "FailureReason": "EMAIL_ALREADY_EXISTS"
        }
    }

    with pytest.raises(Exception, match="EMAIL_ALREADY_EXISTS"):
        manager.create_account("FailAccount", "fail@example.com")

@patch("time.sleep", return_value=None)
def test_create_account_timeout(_, manager, mock_org_client):
    mock_org_client.create_account.return_value = {
        "CreateAccountStatus": {"Id": "timeout-id"}
    }
    mock_org_client.describe_create_account_status.side_effect = [
        {"CreateAccountStatus": {"Id": "timeout-id", "State": "IN_PROGRESS"}}
    ] * 10  # Simulate repeated "IN_PROGRESS" responses

    with pytest.raises(TimeoutError):
        manager.create_account("TimeoutAccount", "timeout@example.com", timeout=1)

@patch("boto3.Session")
def test_assume_role(mock_session, manager):
    mock_sts = MagicMock()
    mock_session.return_value.client.return_value = mock_sts
    mock_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "test-key",
            "SecretAccessKey": "test-secret",
            "SessionToken": "test-token"
        }
    }

    creds = manager._assume_role(account_id="123456789012", role_name="test-role")
    assert creds["AccessKeyId"] == "test-key"
    assert creds["SecretAccessKey"] == "test-secret"
    assert creds["SessionToken"] == "test-token"

def test_list_accounts(manager, mock_org_client):
    mock_org_client.list_accounts.return_value = {
        "Accounts": [
            {"Id": "123456789012", "Email": "test@example.com"}
        ]
    }

    accounts = manager.list_accounts()
    assert len(accounts) == 1
    assert accounts[0]["Id"] == "123456789012"
    assert accounts[0]["Email"] == "test@example.com"