# tfbootstrap

CLI tool to create new AWS accounts as part of your existing
AWS Organization and bootstrap them with Terraform

## Example usage
### Bootstrap your account
```bash
tfbootstrap --profile org-admin --account-name test-sandbox -sbx --admin-email "example+sbx@example.com" --region us-east-1 --output . --admin-pw <password>
```
This will do the following:

* Leverage your Org's admin profile
* Create a child account named 'test-sandbox' 
* Create two users in your child account:
  * admin - user with AWS UI access and the password you set
  * tf-user - CLI only admin user that you will use to jumpstart terraform.  Credentials will be added to ~/.aws/credentials by default
* Create terraform configuration in two directories:
  * ./tf/tf.bootstrap - use this to initialize your state and locking
  * ./tf/tf.skel - this is your starter terraform configuration. use it as a baseline template to continue making changes to your account

  ### Set up terraform:

  ```bash
  cd ./tf/tf.boostrap
  terraform init
  terraform plan
  terraform apply
  ```

  ### Create a test bucket using terraform
  ```bash
  cd ../tf.skel
  terraform init
  terraform plan
  terraform apply
  ```






## Preparing your parent AWS Organization account

1. **Sign in to AWS**: Log in to the AWS Management Console with your root account credentials.

2. **Enable AWS Organizations**: Navigate to the AWS Organizations service and enable it if it is not already enabled.

3. **Enable All Features**: Ensure that all features are enabled in your AWS Organization to allow full management of accounts.

4. **Create a Management Account**: Create a new account under your organization for managing resources. Provide a unique account name and email address.

5. **Set Up IAM Role**: In the new account, create an IAM role named `OrganizationAccountAccessRole` with the following:
   - Trusted entity: AWS account (your management account ID).
   - Permissions: AdministratorAccess.

6. **Create IAM User**: Create an IAM user for CLI access:
   - Assign a username (e.g., `admin`).
   - Attach the `AdministratorAccess` policy.
   - Enable programmatic access and download the access key and secret key.

7. **Configure AWS CLI**: Install and configure the AWS CLI locally with the IAM user's credentials.

8. **Test**:
This should give you identity of your Org Admin account
```bash
aws sts get-caller-identity --profile <profile_name>
```

## Structure

- `src/tfbootstrap/` — core logic modules
- `tests/` — unit tests
- `cli.py` — entry point for CLI

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

## Testing Setup

need to export the following to run integration tests:
```bash
export TEST_ACCOUNT_NAME=<unique account name>
export TEST_ACCOUNT_EMAIL=<realaccount+<unique identifier>@email.com>
export AWS_PROFILE=<Parent organization profile with permissions to create and access child orgs>
export TEST_ADMIN_PW=<password>
```

## Production Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
tfbootstrap --help
```

## Running without installing

```bash
PYTHONPATH=src python src/cli.py
```
