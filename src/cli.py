#!/usr/bin/env python3

import click
import boto3
import os
import re
from tfbootstrap.aws_account_manager import AWSAccountManager
from tfbootstrap.tf_generator import create_tf

def list_aws_profiles():
    session = boto3.Session()
    return session.available_profiles

def choose_from_list(options, prompt):
    for idx, option in enumerate(options):
        click.echo(f"[{idx}] {option}")
    choice = click.prompt(prompt, type=click.IntRange(0, len(options)-1))
    return options[choice]

def validate_account_name(account_name):
    """Validate AWS account name - alphanumeric, hyphens, no spaces, 1-50 chars"""
    if not account_name:
        return False, "Account name is required"
    if not re.match(r'^[a-zA-Z0-9-]+$', account_name):
        return False, "Account name can only contain letters, numbers, and hyphens"
    if len(account_name) < 1 or len(account_name) > 50:
        return False, "Account name must be between 1 and 50 characters"
    if account_name.startswith('-') or account_name.endswith('-'):
        return False, "Account name cannot start or end with a hyphen"
    return True, ""

def validate_email(email):
    """Validate email format"""
    if not email:
        return False, "Email is required"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    return True, ""

def validate_region(region):
    """Validate AWS region format"""
    if not region:
        return False, "Region is required"
    # AWS regions follow pattern: us-east-1, eu-west-2, ap-southeast-1, etc.
    pattern = r'^[a-z]{2,3}-[a-z]+-\d+$'
    if not re.match(pattern, region):
        return False, "Invalid AWS region format (e.g., us-east-1, eu-west-2)"
    return True, ""

def validate_output_path(output):
    """Validate output path - parent directory must exist"""
    if not output:
        return False, "Output path is required"
    
    # Expand any remaining tildes or environment variables
    expanded_path = os.path.expanduser(os.path.expandvars(output))
    parent_dir = os.path.dirname(expanded_path)
    
    # If parent_dir is empty, it means output is just a filename in current dir
    if not parent_dir:
        parent_dir = '.'
    
    if not os.path.exists(parent_dir):
        return False, f"Parent directory does not exist: {parent_dir}"
    if not os.path.isdir(parent_dir):
        return False, f"Parent path is not a directory: {parent_dir}"
    if not os.access(parent_dir, os.W_OK):
        return False, f"No write permission to parent directory: {parent_dir}"
    
    return True, ""

def validate_credpath(credpath):
    """Validate credentials path - parent directory must exist"""
    if not credpath:
        return False, "Credentials path is required"
    
    expanded_path = os.path.expanduser(os.path.expandvars(credpath))
    parent_dir = os.path.dirname(expanded_path)
    
    if not os.path.exists(parent_dir):
        return False, f"Parent directory does not exist: {parent_dir}"
    if not os.path.isdir(parent_dir):
        return False, f"Parent path is not a directory: {parent_dir}"
    if not os.access(parent_dir, os.W_OK):
        return False, f"No write permission to parent directory: {parent_dir}"
    
    return True, ""

def validate_reset_account(reset_account):
    """Validate AWS account ID format"""
    if not reset_account:
        return True, ""  # Optional parameter
    
    # AWS account IDs are 12-digit numbers
    if not re.match(r'^\d{12}$', reset_account):
        return False, "AWS account ID must be exactly 12 digits"
    
    return True, ""

def validate_inputs(profile, account_name, admin_email, admin_pw, region, output, credpath, reset_account):
    """Validate all inputs and return list of errors"""
    errors = []
    
    # For reset account mode, only validate reset_account and profile
    if reset_account:
        valid, msg = validate_reset_account(reset_account)
        if not valid:
            errors.append(msg)
        return errors
    
    # For normal account creation, validate all required fields
    if account_name:
        valid, msg = validate_account_name(account_name)
        if not valid:
            errors.append(f"Account name: {msg}")
    
    if admin_email:
        valid, msg = validate_email(admin_email)
        if not valid:
            errors.append(f"Email: {msg}")
    
    if region:
        valid, msg = validate_region(region)
        if not valid:
            errors.append(f"Region: {msg}")
    
    if output:
        valid, msg = validate_output_path(output)
        if not valid:
            errors.append(f"Output path: {msg}")
    
    if credpath:
        valid, msg = validate_credpath(credpath)
        if not valid:
            errors.append(f"Credentials path: {msg}")
    
    return errors

def validate_required_params(profile, account_name, admin_email, admin_pw, region, output, reset_account, interactive):
    # Only validate if not running interactively (i.e., all params should be provided)
    missing = []
    if not profile: missing.append("profile")
    if not account_name and not reset_account: missing.append("account-name")
    if not admin_email and not reset_account: missing.append("admin-email")
    if not admin_pw and not reset_account: missing.append("admin-pw")
    if not region and not reset_account: missing.append("region")
    if not output and not reset_account: missing.append("output")
    if missing and not interactive:
        raise click.UsageError(f"Missing required parameters: {', '.join(missing)}. Please provide them as command line options.")

def output_on_success(account_id, account_name, output, tf_outputs, setup_cicd=False):
    """Display success message and instructions after account creation"""
    click.echo(f"✅ Done! Terraform configuration has been created in '{output}/tf/' directory.")
    click.echo("************* Remember to enable MFA for 'admin' account ******************")
    click.echo(f"  - Bootstrap configuration: '{output}/tf/tf.bootstrap/'")
    click.echo(f"  - Skeleton configuration: '{output}/tf/tf.skel/'")
    new_account_url = f"https://{account_id}.signin.aws.amazon.com/console"
    click.echo(f"  - New account URL: {new_account_url}")
    
    if setup_cicd and tf_outputs and 'github_connection_approval_url' in tf_outputs:
        click.echo("\n⚠️  GitHub CI/CD Setup Instructions")
        click.echo("Complete the following steps to set up CI/CD:")
        click.echo("1. First apply the bootstrap Terraform configuration:")
        click.echo(f"   cd {output}/tf/tf.bootstrap && terraform init && terraform apply")
        click.echo("\n2. Then apply the skeleton Terraform configuration that includes CI/CD:")
        click.echo(f"   cd {output}/tf/tf.skel && terraform init && terraform apply")
        click.echo("\n3. Visit the AWS CodeStar Connections console to approve the GitHub connection:")
        click.echo(f"   URL: {tf_outputs['github_connection_approval_url']}")
        click.echo(f"   - Find 'github-connection-{account_name}' and click 'Update pending connection'")
        click.echo("   - Follow the steps to authorize AWS to access your GitHub repository")
        click.echo("\n4. After approving the connection, your CodeBuild project and pipeline will be able to access your GitHub repository")
        click.echo("   - You can verify this by checking the CodeBuild project in the AWS console")
        click.echo("   - The first pipeline run may fail until the connection is approved")
        click.echo("\n5. You may need to push code to your repository to trigger the pipeline")

def run_cli(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
            github_org, github_repo, github_branch):
    validate_required_params(profile, account_name, admin_email, admin_pw, region, output, reset_account, interactive=False)
    
    # Validate input formats
    validation_errors = validate_inputs(profile, account_name, admin_email, admin_pw, region, output, credpath, reset_account)
    if validation_errors:
        raise click.UsageError(f"Validation errors:\n  - {chr(10).join(validation_errors)}")
    
    
    if reset_account:
        if not profile:
            profiles = list_aws_profiles()
            profile = choose_from_list(profiles, "Select an AWS profile")
        click.echo(f"🔄 Resetting account with ID: {reset_account}")
        manager = AWSAccountManager(profile_name=profile, credpath=credpath)
        manager.delete_admin_users(account_id=reset_account)
        click.echo(f"✅ Account {reset_account} has been reset.")
        return

    click.echo(f"🔐 Using AWS profile: {profile}")
    manager = AWSAccountManager(profile_name=profile, credpath=credpath)
    click.echo(f"🔧 Creating AWS account '{account_name}'...")
    account_id = manager.create_account(account_name=account_name, email=admin_email)
    click.echo("👥 Creating IAM users (admin + tf-user)...")
    manager.create_admin_users(account_id=account_id, email=admin_email, admin_pw=admin_pw, account_name=account_name)
    click.echo("🧱 Generating Terraform tfvars file...")
    tf_outputs = create_tf(
        account_id=account_id,
        account_name=account_name,
        region=region,
        email=admin_email,
        output_dir=output,
        github_org=github_org,
        github_repo=github_repo,
        github_branch=github_branch
    )
    setup_cicd = github_org and github_repo
    output_on_success(account_id, account_name, output, tf_outputs, setup_cicd)

def run_interactive(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
                    github_org, github_repo, github_branch):
    if not profile:
        profiles = list_aws_profiles()
        profile = choose_from_list(profiles, "Select profile with ORG access")
    
    # Account name with validation
    while not account_name:
        account_name = click.prompt("Enter the new account name")
        valid, msg = validate_account_name(account_name)
        if not valid:
            click.echo(f"❌ {msg}")
            account_name = None
    
    # Email with validation
    while not admin_email:
        admin_email = click.prompt("Enter the admin email address")
        valid, msg = validate_email(admin_email)
        if not valid:
            click.echo(f"❌ {msg}")
            admin_email = None
    
    # Password (no format validation needed)
    if not admin_pw:
        admin_pw = click.prompt("Enter the admin password", hide_input=True)
    
    # Region with validation
    while True:
        region = click.prompt("Enter AWS region", default=region)
        valid, msg = validate_region(region)
        if valid:
            break
        click.echo(f"❌ {msg}")
    
    # Output with validation
    while True:
        output = click.prompt("Enter output directory for generated Terraform files", default=output)
        valid, msg = validate_output_path(output)
        if valid:
            break
        click.echo(f"❌ {msg}")
    
    # Validate credpath
    valid, msg = validate_credpath(credpath)
    if not valid:
        click.echo(f"❌ Credentials path: {msg}")
        raise click.Abort()
    
    setup_cicd = click.confirm("Would you like to set up CI/CD with GitHub?", default=False)
    if setup_cicd:
        if not github_org:
            github_org = click.prompt("Enter GitHub organization name")
        if not github_repo:
            github_repo = click.prompt("Enter GitHub repository name")
        # GitHub branch already has a default from click.option
        github_branch = click.prompt("Enter GitHub branch name", default=github_branch)
    else:
        github_org = None
        github_repo = None
        github_branch = None

    click.echo(f"🔐 Using AWS profile: {profile}")
    manager = AWSAccountManager(profile_name=profile, credpath=credpath)
    click.echo(f"🔧 Creating AWS account '{account_name}'...")
    account_id = manager.create_account(account_name=account_name, email=admin_email)
    click.echo("👥 Creating IAM users (admin + tf-user)...")
    manager.create_admin_users(account_id=account_id, email=admin_email, admin_pw=admin_pw, account_name=account_name)
    click.echo("🧱 Generating Terraform tfvars file...")
    tf_outputs = create_tf(
        account_id=account_id,
        account_name=account_name,
        region=region,
        email=admin_email,
        output_dir=output,
        github_org=github_org,
        github_repo=github_repo,
        github_branch=github_branch
    )

    output_on_success(account_id, account_name, output, tf_outputs, setup_cicd)

@click.command()
@click.option('--profile', help=f'AWS profile we can use to create a child account'
                            '\n** THIS MUST HAVE ACCESS TO CREATE ACCOUNTS INSIDE ORGANIZATION **')
@click.option('--account-name', help='Name of the AWS account to create')
@click.option('--admin-email', help='Email of the administrator for the new account')
@click.option('--region', default='us-east-1', help='Region for Terraform resources')
@click.option('--output', default=f"{os.environ['HOME']}/tmp", help='Output directory for generated Terraform files')
@click.option('--credpath', help='File path where account credentials will be appended', default=f"{os.environ['HOME']}/.aws/credentials")
@click.option('--admin-pw', help='Set password for admin user')
@click.option('--reset-account', help='Provide Account ID to reset')
@click.option('--github-org', help='GitHub organization name for CI/CD pipeline')
@click.option('--github-repo', help='GitHub repository name for CI/CD pipeline')
@click.option('--github-branch', default='main', help='GitHub branch to use for CI/CD pipeline')
def main(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
         github_org, github_repo, github_branch):
    # Check if any non-default parameters were provided
    # Exclude parameters with defaults: credpath, github_branch, region, output
    cli_params = [profile, account_name, admin_email, admin_pw, reset_account, github_org, github_repo]
    
    # Also check if region or output were explicitly changed from their defaults
    has_cli_params = any(param is not None for param in cli_params)
    region_changed = region != 'us-east-1'
    output_changed = output != f"{os.environ['HOME']}/tmp"
    
    if has_cli_params or region_changed or output_changed:
        # CLI mode - validate required parameters and fail gracefully if missing
        run_cli(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
                github_org, github_repo, github_branch)
    else:
        # Interactive mode - prompt for missing parameters
        run_interactive(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
                        github_org, github_repo, github_branch)

if __name__ == "__main__":
    main()