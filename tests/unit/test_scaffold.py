import os
import subprocess

def test_cli_runs_and_lists_commands():
    result = subprocess.run(
        ["python", "src/cli.py", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    # The CLI now shows options instead of commands
    assert "--profile" in result.stdout
    assert "--account-name" in result.stdout
    assert "--admin-email" in result.stdout
    assert "--region" in result.stdout

def test_cli_with_profile():
    result = subprocess.run(
        ["python", "src/cli.py", "--profile", "test-profile", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "--profile" in result.stdout