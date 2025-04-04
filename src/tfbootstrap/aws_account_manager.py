import boto3
import time
import logging
import os
import random
import string
import configparser
from botocore.exceptions import ClientError
from botocore.config import Config
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AWSAccountManager:
    def __init__(self, profile_name, credpath="~/.aws/credentials", org_client=None):
        """
        Initialize the AWSAccountManager.
        :param profile_name: The AWS CLI profile name to use.
        :param credpath: The file path where AWS credentials will be written.
        :param org_client: Optional mocked Organizations client for testing.
        """
        self.ORG_ROOT_PROFILE = profile_name
        self.credpath = os.path.expanduser(credpath)

        # Use the provided org_client or create a new session
        self.client = org_client or boto3.Session(profile_name=self.ORG_ROOT_PROFILE).client("organizations")

    def create_account(self, account_name, email, role_name="OrganizationAccountAccessRole", tags=None, timeout=600):
        """
        Create a new AWS account within the organization, or return the existing account if it already exists.
        :param account_name: The name of the new account.
        :param email: The email address associated with the new account.
        :param role_name: The IAM role name for the new account.
        :param tags: A dictionary of tags to apply to the account.
        :param timeout: The maximum time (in seconds) to wait for account creation.
        :return: The ID of the newly created or existing account.
        :raises: ClientError if the account creation request fails.
        """
        # Check if the account already exists
        existing_account = self.get_account_by_email(email)
        if existing_account:
            logger.info(f"Account with email {email} already exists: {existing_account['Id']}")
            return existing_account["Id"]

        # Proceed with account creation if it doesn't exist
        try:
            response = self.client.create_account(
                AccountName=account_name,
                Email=email,
                RoleName=role_name,
                IamUserAccessToBilling="ALLOW",
                Tags=[{'Key': k, 'Value': v} for k, v in (tags or {}).items()]
            )
            create_id = response["CreateAccountStatus"]["Id"]
            status = self._wait_for_account_creation(create_id, timeout=timeout)

            account_id = status["AccountId"]
            logger.info(f"Account created: {account_id}, assuming role to set up users.")
            logger.debug(f"Account creation status: {status}")

            return account_id
        except ClientError as e:
            logger.error(f"Failed to initiate account creation: {e}")
            raise

    def _wait_for_account_creation(self, request_id, timeout=600, interval=10):
        """
        Wait for the account creation process to complete.
        :param request_id: The ID of the account creation request.
        :param timeout: The maximum time (in seconds) to wait for account creation.
        :param interval: The time (in seconds) to wait between status checks.
        :return: The account creation status dictionary if successful.
        :raises: TimeoutError if the account creation process exceeds the timeout.
        :raises: Exception if the account creation fails.
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                response = self.client.describe_create_account_status(CreateAccountRequestId=request_id)
                status = response["CreateAccountStatus"]["State"]

                if status == "SUCCEEDED":
                    return response["CreateAccountStatus"]
                elif status == "FAILED":
                    raise Exception(f"Account creation failed: {response['CreateAccountStatus']['FailureReason']}")
            except ClientError as e:
                logger.warning(f"Retrying status check: {e}")

            time.sleep(interval)
            elapsed += interval

        raise TimeoutError("Timed out waiting for account creation to complete.")

    def _assume_role(self, account_id, role_name):
        """
        Assume a role in the specified AWS account using the profile stored in self.ORG_ROOT_PROFILE.
        :param account_id: The ID of the AWS account.
        :param role_name: The name of the IAM role to assume.
        :return: Temporary credentials for the assumed role.
        """
        # Establish a session using the profile stored in self.ORG_ROOT_PROFILE
        session = boto3.Session(profile_name=self.ORG_ROOT_PROFILE)
        sts = session.client("sts")
        
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        logger.info(f"Assuming role {role_arn} using profile {self.ORG_ROOT_PROFILE}")
        
        assumed = sts.assume_role(RoleArn=role_arn, RoleSessionName="AccountSetupSession")
        return assumed["Credentials"]

    # no longer should be using this. TODO: remove
    def _generate_random_password(self, length=12):
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def _write_aws_profile(self, account_name, access_key):
        """
        Write AWS credentials to the specified credentials file.
        :param account_name: The name of the AWS account.
        :param access_key: The access key dictionary containing AccessKeyId and SecretAccessKey.
        """
        config = configparser.ConfigParser()
        config_path = Path(self.credpath)

        if config_path.exists():
            config.read(config_path)

        profile_name = account_name
        config[profile_name] = {
            "aws_access_key_id": access_key["AccessKeyId"],
            "aws_secret_access_key": access_key["SecretAccessKey"]
        }

        with open(config_path, "w") as f:
            config.write(f)
        logger.info(f"Credentials for '{account_name}' written to {self.credpath}")

    def get_account(self, account_id):
        """
        Retrieve details of an AWS account by its account ID.
        :param account_id: The ID of the account to retrieve.
        :return: A dictionary containing account details.
        :raises: ClientError if the account retrieval fails.
        """
        return self.client.describe_account(AccountId=account_id)["Account"]

    def list_accounts(self):
        """
        Retrieve a list of all accounts in the organization.
        :return: A list of dictionaries, each containing details of an account.
        """
        accounts = []
        paginator = self.client.get_paginator("list_accounts")
        for page in paginator.paginate():
            accounts.extend(page["Accounts"])
        return accounts

    def get_account_by_email(self, email):
        """
        Retrieve an account by its email address.
        :param email: The email address of the account to retrieve.
        :return: The account dictionary if found, otherwise None.
        """
        accounts = self.list_accounts()
        for account in accounts:
            if account["Email"].lower() == email.lower():
                return account
        return None

    def create_admin_users(self, account_id, role_name="OrganizationAccountAccessRole", email=None, admin_pw=None, account_name=None):
        """
        Create admin and tf-user accounts in the specified AWS account.
        :param account_id: The ID of the AWS account.
        :param role_name: The IAM role to assume in the target account.
        :param email: The email address to notify about admin credentials.
        :param admin_pw: The password to set for the admin user. This is required.
        """
        if not admin_pw:
            raise ValueError("Admin password is required to create admin users.")

        if not account_name:
            raise ValueError("Must provide account name")

        # Assume the role in the target account
        creds = self._assume_role(account_id, role_name)

        iam = boto3.client(
            "iam",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )

        try:
            # Create admin user (console access)
            iam.create_user(UserName="admin")
            iam.attach_user_policy(UserName="admin", PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
            iam.create_login_profile(
                UserName="admin",
                Password=admin_pw,
                PasswordResetRequired=False
            )
            logger.info(f"Admin user created for Web UI. ")
        except ClientError as e:
            logger.warning(f"Failed to create admin user: {e}")

        try:
            # Create tf-user (CLI access)
            iam.create_user(UserName="tf-user")
            iam.attach_user_policy(UserName="tf-user", PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
            access_key = iam.create_access_key(UserName="tf-user")["AccessKey"]
            self._write_aws_profile(f"tf-user-{account_name}", access_key)
            logger.info(f"tf-user created and local profile 'tf-user-{account_id}' configured.")
        except ClientError as e:
            logger.warning(f"Failed to create tf-user: {e}")

    def delete_admin_users(self, account_id, role_name="OrganizationAccountAccessRole", email=None):
        """
        Delete admin and tf-user accounts in the specified AWS account.
        :param account_id: The ID of the AWS account.
        :param creds: Temporary credentials for the AWS account.
        """
        results = []
        # Assume the role in the target account
        creds = self._assume_role(account_id, role_name)

        iam = boto3.client(
            "iam",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"]
        )

        # Delete tf-user
        try:
            results.append(iam.delete_access_key(UserName="tf-user", AccessKeyId=iam.list_access_keys(UserName="tf-user")["AccessKeyMetadata"][0]["AccessKeyId"]))
            results.append(iam.detach_user_policy(UserName="tf-user", PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"))
            results.append(iam.delete_user(UserName="tf-user"))
            logger.info("tf-user deleted successfully.")
        except ClientError as e:
            logger.error(f"Failed to delete tf-user: {e}")

        # Delete admin user
        try:
            results.append(iam.delete_login_profile(UserName="admin"))
            results.append(iam.detach_user_policy(UserName="admin", PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess"))
            results.append(iam.delete_user(UserName="admin"))
            logger.info("Admin user deleted successfully.")
        except ClientError as e:
            logger.error(f"Failed to delete admin user: {e}")
        
        return results