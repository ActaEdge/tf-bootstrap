import os
from pathlib import Path
import shutil
import pytest
from tfbootstrap.tf_generator import create_tf

def test_generate_tfvars():
    # Test that tfvars file is generated with correct content
    account_id = "123456789012"
    account_name = "test-account"
    region = "us-east-1"
    email = "test@example.com"
    
    try:
        create_tf(account_id=account_id, account_name=account_name, region=region, email=email, output_dir="tf_test")
        
        # Check that tfvars file exists and contains required variables
        tfvars_path = Path("tf_test/tf/tf.bootstrap/terraform.tfvars")
        assert tfvars_path.exists(), "tfvars file was not created"
        
        with open(tfvars_path) as f:
            content = f.read()
            assert account_id in content, "account_id not found in tfvars file"
            assert region in content, "region not found in tfvars file"
            assert "bucket_name" in content, "bucket_name not found in tfvars file"
            assert "dynamodb_table" in content, "dynamodb_table not found in tfvars file"
            
        # Verify directory structure
        assert Path("tf_test/tf/tf.bootstrap").exists(), "tf.bootstrap directory was not created"
        assert Path("tf_test/tf/tf.skel").exists(), "tf.skel directory was not created"
    finally:
        # Clean up
        if Path("tf_test").exists():
            shutil.rmtree("tf_test")

def test_generate_state_resources_tf():
    # Test that main.tf is generated with required resources
    account_id = "123456789012"
    account_name = "test-account"
    region = "us-east-1"
    email = "test@example.com"
    
    try:
        create_tf(account_id=account_id, account_name=account_name, region=region, email=email, output_dir="tf_test")
        
        # Check that main.tf exists and contains required resources
        main_tf_path = Path("tf_test/tf/tf.bootstrap/main.tf")
        assert main_tf_path.exists(), "main.tf was not created"
        
        with open(main_tf_path) as f:
            content = f.read()
            assert "aws_s3_bucket" in content, "S3 bucket resource not found in main.tf"
            assert "aws_dynamodb_table" in content, "DynamoDB table resource not found in main.tf"
    finally:
        # Clean up
        if Path("tf_test").exists():
            shutil.rmtree("tf_test")

def test_generate_tfvars_custom_output():
    # Test that tfvars file is generated in custom output directory
    account_id = "123456789012"
    account_name = "test-account"
    region = "us-east-1"
    email = "test@example.com"
    output_dir = "test_output"
    
    try:
        create_tf(account_id=account_id, account_name=account_name, region=region, email=email, output_dir=output_dir)
        
        # Check that tfvars file exists in custom directory
        tfvars_path = Path(output_dir) / "tf/tf.bootstrap/terraform.tfvars"
        assert tfvars_path.exists(), "tfvars file was not created in custom directory"
        
        with open(tfvars_path) as f:
            content = f.read()
            assert account_id in content, "account_id not found in tfvars file"
            assert region in content, "region not found in tfvars file"
            
        # Verify directory structure
        assert Path(output_dir) / "tf/tf.bootstrap" in Path(output_dir).glob("**/*"), "tf.bootstrap directory was not created"
        assert Path(output_dir) / "tf/tf.skel" in Path(output_dir).glob("**/*"), "tf.skel directory was not created"
    finally:
        # Clean up test directory
        pass
        # disable this for now as we need to keep the test directory for debugging purposes
        #if Path(output_dir).exists():
        #    shutil.rmtree(output_dir)

def test_invalid_account_id():
    # Test that invalid account_id raises an error
    with pytest.raises(ValueError, match="Invalid account_id"):
        create_tf(account_id="", account_name="test-account", region="us-east-1", email="test@example.com")