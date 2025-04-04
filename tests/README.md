# Integration Testing for AWSAccountManager

This test suite runs unit and live integration tests against your AWS Organization using the `AWSAccountManager` class. It validates account creation, querying, and listing using real AWS APIs.

> ⚠️ Use a **sandbox org**. This test creates real accounts that cannot be deleted programmatically.

---

## 🔧 Prerequisites

- Python 3.8+
- AWS credentials configured with access to AWS Organizations

---

## 🧪 Environment Variables
Set the following environment variables before running tests:

```bash
export AWS_PROFILE=tfbootstrap-dev                 # Your AWS CLI profile
export TEST_ACCOUNT_EMAIL=test-ci@example.com      # Unique email per org
export TEST_ACCOUNT_NAME=TFB-TestAccount           # Name of the account to create or reuse
export TEST_ACCOUNT_TAG_OWNER=ci                   # Tag value for account ownership (optional)
```

---

## 🚀 Run Tests

### Run unit tests
```bash
pytest
```

### Run integration tests
```bash
pytest -m integration
```

### Run a specific test
```bash
pytest -m integration tests/test_integration_aws_account_manager.py::test_get_account
```

### Run with debug logging
```bash
pytest -m integration -o log_cli=true -o log_level=INFO
```
## 💡 Tips

- Use a `pytest.ini` to register the `integration` marker and set `pythonpath`:

```ini
[pytest]
pythonpath = src
markers =
    integration: mark a test as requiring integration
```
- Always use dedicated test accounts/emails to avoid polluting production environments.

---

## 📦 Cleanup

Accounts created through AWS Organizations cannot be deleted programmatically.
You must manually close them via the AWS Console.

Tag your test accounts to make cleanup easier later.
