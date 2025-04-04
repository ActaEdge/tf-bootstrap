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

@click.command()
@click.option('--profile', help='AWS CLI profile to use')
@click.option('--account-name', help='Name of the AWS account to create')
@click.option('--admin-email', help='Email of the administrator for the new account')
@click.option('--region', default='us-east-1', help='Region for Terraform resources')
@click.option('--output', default='.', help='Output directory for generated Terraform files')
@click.option('--credpath', default='~/.aws/credentials', help='File path where account credentials will be appended')
@click.option('--admin-pw', help='Set password for admin user')
@click.option('--reset-account', help='Provide Account ID to reset')
def main(profile, account_name, admin_email, region, output, credpath, admin_pw, reset_account):
    # Handle reset-account option
    if reset_account:
        if not profile:
            profiles = list_aws_profiles()
            profile = choose_from_list(profiles, "Select an AWS profile")

        click.echo(f"🔄 Resetting account with ID: {reset_account}")
        manager = AWSAccountManager(profile_name=profile, credpath=credpath)
        manager.delete_admin_users(account_id=reset_account)
        click.echo(f"✅ Account {reset_account} has been reset.")
        return

    # Interactive prompts for missing args
    if not profile:
        profiles = list_aws_profiles()
        profile = choose_from_list(profiles, "Select an AWS profile")

    if not account_name:
        account_name = click.prompt("Enter the new account name")

    if not admin_email:
        admin_email = click.prompt("Enter the admin email address")

    if not admin_pw:
        admin_pw = click.prompt("Enter the admin password", hide_input=True)

    click.echo(f"🔐 Using AWS profile: {profile}")
    manager = AWSAccountManager(profile_name=profile, credpath=credpath)

    click.echo(f"🔧 Creating AWS account '{account_name}'...")
    account_id = manager.create_account(account_name=account_name, email=admin_email)

    click.echo("👥 Creating IAM users (admin + tf-user)...")
    manager.create_admin_users(account_id=account_id, email=admin_email, admin_pw=admin_pw, account_name=account_name)

    click.echo("🧱 Generating Terraform tfvars file...")
    create_tf(account_id=account_id, account_name=account_name, region=region, email=admin_email, output_dir=output)

    click.echo(f"✅ Done! Terraform configuration has been created in '{output}/tf/' directory.")
    click.echo("************* Rememeber to enable MFA for 'admin' account ******************")
    click.echo(f"  - Bootstrap configuration: '{output}/tf/tf.bootstrap/'")
    click.echo(f"  - Skeleton configuration: '{output}/tf/tf.skel/'")
    new_account_url = f"https://{account_id}.signin.aws.amazon.com/console"
    click.echo(f"  - New account URL: {new_account_url}")

if __name__ == "__main__":
    main()
