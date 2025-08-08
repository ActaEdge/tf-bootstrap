#!/usr/bin/env python3

import click
import boto3
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

def run_cli(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
            github_org, github_repo, github_branch):
    validate_required_params(profile, account_name, admin_email, admin_pw, region, output, reset_account, interactive=False)
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
    click.echo(f"✅ Done! Terraform configuration has been created in '{output}/tf/' directory.")
    click.echo("************* Remember to enable MFA for 'admin' account ******************")
    click.echo(f"  - Bootstrap configuration: '{output}/tf/tf.bootstrap/'")
    click.echo(f"  - Skeleton configuration: '{output}/tf/tf.skel/'")
    new_account_url = f"https://{account_id}.signin.aws.amazon.com/console"
    click.echo(f"  - New account URL: {new_account_url}")
    if github_org and github_repo and tf_outputs and 'github_connection_approval_url' in tf_outputs:
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

def run_interactive(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account,
                    github_org, github_repo, github_branch):
    if not profile:
        profiles = list_aws_profiles()
        profile = choose_from_list(profiles, "Select profile with ORG access")
    if not account_name:
        account_name = click.prompt("Enter the new account name")
    if not admin_email:
        admin_email = click.prompt("Enter the admin email address")
    if not admin_pw:
        admin_pw = click.prompt("Enter the admin password", hide_input=True)
    if not region:
        region = click.prompt("Enter AWS region", default="us-east-1")
    if not output:
        output = click.prompt("Enter output directory for generated Terraform files")
    setup_cicd = click.confirm("Would you like to set up CI/CD with GitHub?", default=False)
    if setup_cicd:
        if not github_org:
            github_org = click.prompt("Enter GitHub organization name")
        if not github_repo:
            github_repo = click.prompt("Enter GitHub repository name")
        if github_branch == 'main':
            custom_branch = click.confirm("Use a branch other than 'main'?", default=False)
            if custom_branch:
                github_branch = click.prompt("Enter GitHub branch name")
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

@click.command()
@click.option('--profile', help=f'AWS profile we can use to create a child account'
                            '\n** THIS MUST HAVE ACCESS TO CREATE ACCOUNTS INSIDE ORGANIZATION **')
@click.option('--account-name', help='Name of the AWS account to create')
@click.option('--admin-email', help='Email of the administrator for the new account')
@click.option('--region', default='us-east-1', help='Region for Terraform resources')
@click.option('--output', default='~/tmp', help='Output directory for generated Terraform files')
@click.option('--credpath', help='File path where account credentials will be appended', default="~/.aws/credentials")
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
    output_changed = output != '~/tmp'
    
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