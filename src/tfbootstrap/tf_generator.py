from pathlib import Path
import os
import shutil
import glob
import json

def create_tf(account_id: str, account_name: str, region: str, email: str, output_dir: str = ".",
              github_org=None, github_repo=None, github_branch=None):
    """
    Create Terraform configuration files in the specified output directory.
    
    Args:
        account_id: AWS Account ID
        account_name: Name of the AWS account
        region: AWS Region
        email: Admin email address
        output_dir: Directory to create Terraform files in (default: current directory)
        github_org: GitHub organization name for CI/CD pipeline
        github_repo: GitHub repository name for CI/CD pipeline
        github_branch: GitHub branch name for CI/CD pipeline
    
    Returns:
        Dictionary with additional outputs (like URL for GitHub connection approval)
    """
    if not account_id or not account_id.isdigit() or len(account_id) != 12:
        raise ValueError("Invalid account_id")

    base_dir = Path(output_dir)
    tf_dir = base_dir / "tf"
    tf_bootstrap_dir = tf_dir / "tf.bootstrap"
    tf_skel_dir = tf_dir / "tf.skel"
    tfvars_file_bootstrap = tf_bootstrap_dir / "terraform.tfvars"
    tfvars_file_skel = tf_skel_dir / "terraform.tfvars"
    backend_file_skel = tf_skel_dir / "backend.tf"
    
    # Output dictionary for additional information
    outputs = {}

    # Create directory structure
    tf_dir.mkdir(parents=True, exist_ok=True)
    tf_bootstrap_dir.mkdir(parents=True, exist_ok=True)
    tf_skel_dir.mkdir(parents=True, exist_ok=True)

    # Copy all template files from tf.templates to tf.bootstrap
    template_dir = Path(__file__).parent.parent / "tf.templates"
    for template_file in template_dir.glob('*.tf'):
        shutil.copy2(template_file, tf_bootstrap_dir)
    
    # Create buildspec.yml template if CI/CD is enabled
    if github_org and github_repo:
        buildspec_path = tf_bootstrap_dir / "buildspec.yml"
        buildspec_content = create_buildspec_template()
        with buildspec_path.open("w") as f:
            f.write(buildspec_content)
        print(f"Created buildspec.yml template at: {buildspec_path}")
        
        # Generate connection approval URL (this is a placeholder URL format)
        outputs["github_connection_approval_url"] = f"https://{region}.console.aws.amazon.com/codesuite/settings/connections"

    # Copy template files to tf.skel
    skel_template_dir = Path(__file__).parent.parent / "tf.skel"
    shutil.copy2(skel_template_dir / "main.tf", tf_skel_dir)
    shutil.copy2(skel_template_dir / "variables.tf", tf_skel_dir)

    # Generate consistent bucket and DynamoDB table names
    bucket_name = f"tf-state-{account_name}-{account_id[-6:]}"
    dynamodb_table = f"tf-locks-{account_name}"

    # Generate terraform.tfvars for bootstrap with GitHub info if provided
    tfvars_content_bootstrap = f"""\
account_id     = "{account_id}"
account_name   = "{account_name}"
bucket_name    = "{bucket_name}"
region         = "{region}"
dynamodb_table = "{dynamodb_table}"
"""
    
    # Add GitHub variables if CI/CD is enabled
    if github_org and github_repo:
        tfvars_content_bootstrap += f"""
# GitHub CI/CD Configuration
github_org    = "{github_org}"
github_repo   = "{github_repo}"
github_branch = "{github_branch}"
"""

    with tfvars_file_bootstrap.open("w") as f:
        f.write(tfvars_content_bootstrap)

    print(f"Created terraform.tfvars file for bootstrap at: {tfvars_file_bootstrap}")

    # Generate terraform.tfvars for skeleton
    tfvars_content_skel = f"""\
account_id     = "{account_id}"
account_name   = "{account_name}"
region         = "{region}"
bucket_name    = "{bucket_name}"
dynamodb_table = "{dynamodb_table}"
"""

    with tfvars_file_skel.open("w") as f:
        f.write(tfvars_content_skel)

    print(f"Created terraform.tfvars file for skeleton at: {tfvars_file_skel}")

    # Generate backend.tf for skeleton
    backend_content = f"""\
terraform {{
  backend "s3" {{
    bucket         = "{bucket_name}"
    key            = "terraform.tfstate"
    region         = "{region}"
    dynamodb_table = "{dynamodb_table}"
    encrypt        = true
  }}
}}
"""

    with backend_file_skel.open("w") as f:
        f.write(backend_content)

    print(f"Created backend.tf file for skeleton at: {backend_file_skel}")

    print(f"Created bootstrap directory at: {tf_bootstrap_dir}")
    print(f"Created skeleton directory at: {tf_skel_dir}")
    
    return outputs

def create_buildspec_template():
    """Create a buildspec.yml template for AWS CodeBuild"""
    return """\
version: 0.2

phases:
  install:
    runtime-versions:
      python: 3.9
    commands:
      - echo Installing Terraform...
      - wget https://releases.hashicorp.com/terraform/1.5.7/terraform_1.5.7_linux_amd64.zip
      - unzip terraform_1.5.7_linux_amd64.zip
      - mv terraform /usr/local/bin/
  
  pre_build:
    commands:
      - echo Initializing Terraform...
      - cd ./tf
      - terraform init -input=false

  build:
    commands:
      - echo Running Terraform plan...
      - terraform plan -out=tfplan -input=false
      - terraform show -json tfplan > tfplan.json

artifacts:
  files:
    - tfplan
    - tfplan.json
    - '**/*'
  base-directory: 'tf'
"""