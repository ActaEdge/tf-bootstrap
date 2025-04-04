import pytest
import warnings
import boto3
import os
import time
import logging
from tfbootstrap.aws_account_manager import AWSAccountManager

# Suppress the specific deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="botocore.auth")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



@pytest.fixture(scope="module")
def aws_manager():
    profile_name = os.environ.get("AWS_PROFILE", "default")
    session = boto3.Session(profile_name=profile_name)
    org_client = session.client("organizations")
    return AWSAccountManager(profile_name=profile_name, org_client=org_client)

#@pytest.mark.integration
def test_create_or_check_account(aws_manager):
    email = os.environ["TEST_ACCOUNT_EMAIL"]
    account_name = os.environ.get("TEST_ACCOUNT_NAME")

    # If account exists, return its ID
    # If not, create a new account
    # and return its ID
    # creating aws account is not a trivial matter as deleting them takes 90 days, so we need to make sure
    # this test is idempotent and does not prevent other tests from running
    existing = None
    account_name = os.environ.get("TEST_ACCOUNT_NAME")

    result = aws_manager.get_account_by_email(email)

    if result:
        logger.info(f"Account already exists: {result['Id']}")
        assert result["Status"] == "ACTIVE", f"Account exists but not active: {result['FailureReason']}"
    else:
        result = aws_manager.create_account(
            account_name=account_name,
            email=email,
            tags={"Env": "Integration", "Owner": os.environ.get("TEST_ACCOUNT_TAG_OWNER", "CI")},
            timeout=1200
        )
        time.sleep(30)
        assert result["State"] == "SUCCEEDED", f"Account creation failed: {result['FailureReason']}"

    logger.info(f"Account creation result: {result}")



#@pytest.mark.integration
def test_get_account(aws_manager):
    test_account_id = aws_manager.get_account_by_email(os.environ["TEST_ACCOUNT_EMAIL"])["Id"]

    account = aws_manager.get_account(test_account_id)
    logger.info(f'Account: {test_account_id}')
    assert account["Id"] == test_account_id
    

#@pytest.mark.integration
def test_list_accounts(aws_manager):
    test_account_id = aws_manager.get_account_by_email(os.environ["TEST_ACCOUNT_EMAIL"])["Id"]

    accounts = aws_manager.list_accounts()
    logger.info(f'Accounts: {accounts}')
    assert any((a["Id"] == test_account_id) and ( a["Status"] == "ACTIVE")  for a in accounts)


#@pytest.mark.integration
def test_create_admin_users(aws_manager):
    test_account_id = aws_manager.get_account_by_email(os.environ["TEST_ACCOUNT_EMAIL"])["Id"]
    admin_pw = os.environ.get("TEST_ADMIN_PW")
    account_name = os.environ.get("TEST_ACCOUNT_NAME")

    # Create an admin user in the test account
    results = aws_manager.create_admin_users(test_account_id, admin_pw=admin_pw, account_name=account_name)
    logger.info(f"Admin user creation result: {results}")
    time.sleep(20)
    assert results is None, 'Admin user creation failed'

#@pytest.mark.integration
def test_delete_admin_users(aws_manager):
    test_account_id = aws_manager.get_account_by_email(os.environ["TEST_ACCOUNT_EMAIL"])["Id"]

    # Create an admin user in the test account
    results = aws_manager.delete_admin_users(test_account_id)
    logger.info(f"Admin user creation result: {results}")
    time.sleep(20)
    assert results is not None, 'Admin user deletion failed'