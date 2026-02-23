from pathlib import Path

import click
import pytest

from click.testing import CliRunner

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition


def configure_manager(monkeypatch, tmp_path: Path) -> RoleManager:
    manager = RoleManager(roles_dir=tmp_path)
    monkeypatch.setattr(cli, "role_manager", manager)
    return manager


def test_create_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "create_role", raise_error)

    result = runner.invoke(cli.cli, ["create", "--name", "Role", "--description", "Desc"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_load_role_not_found(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["load", "--name", "missing-role"])
    assert result.exit_code != 0
    assert "Role not found" in result.output


def test_merge_no_current_role(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["merge", "--roles", "missing"])
    assert result.exit_code != 0
    assert "No current role" in result.output


def test_merge_no_source_roles(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Target", "Target role")

    result = runner.invoke(cli.cli, ["merge", "--roles", "missing1,missing2"])
    assert result.exit_code != 0
    assert "No source roles could be loaded" in result.output


def test_list_with_name(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)

    role = AzureRoleDefinition(
        Name="List Role",
        Description="Desc",
        Permissions=[PermissionDefinition()],
    )
    manager.save_to_roles_dir(role, overwrite=True)

    result = runner.invoke(cli.cli, ["list", "--name", "list-role"])
    assert result.exit_code == 0
    assert "List Role" in result.output


def test_save_file_exists_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Save Role", "Desc")

    file_path = tmp_path / "save-role.json"
    file_path.write_text("{}")

    result = runner.invoke(cli.cli, ["save", "--name", "save-role", "--output", str(file_path)])
    assert result.exit_code != 0
    assert "File already exists" in result.output


def test_publish_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Publish Role", "Desc")

    class FailingAzureClient:
        def __init__(self, subscription_id=None):
            self.subscription_id = subscription_id

        def create_custom_role(self, role):
            raise RuntimeError("boom")

    monkeypatch.setattr(cli, "AzureClient", FailingAzureClient)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")  # Set subscription context

    result = runner.invoke(cli.cli, ["publish", "--name", "Publish Role"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_list_azure_empty_and_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    class EmptyAzureClient:
        def __init__(self, subscription_id=None):
            self.subscription_id = subscription_id

        def list_custom_roles(self):
            return []

    monkeypatch.setattr(cli, "AzureClient", EmptyAzureClient)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")  # Set subscription context
    result = runner.invoke(cli.cli, ["list-azure"])
    assert result.exit_code == 0
    assert "No custom roles found" in result.output

    class ErrorAzureClient:
        def __init__(self, subscription_id=None):
            self.subscription_id = subscription_id

        def list_custom_roles(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(cli, "AzureClient", ErrorAzureClient)
    result = runner.invoke(cli.cli, ["list-azure"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_run_shell_command_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise cli.subprocess.TimeoutExpired(cmd="cmd", timeout=60)

    monkeypatch.setattr(cli.subprocess, "run", raise_timeout)

    with cli.term.capture() as capture:
        cli.run_shell_command("sleep 1")

    output = capture.get()
    assert "timed out" in output


def test_print_grouped_permissions_truncation():
    permissions = [
        "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Storage/storageAccounts/listKeys/action",
    ]

    with cli.term.capture() as capture:
        cli._print_grouped_permissions("Actions", permissions, show_all=False, limit=1)

    output = capture.get()
    # Remove ANSI codes to check the actual text
    import re
    clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
    assert "and 1 more" in clean_output


def test_interactive_mode_error_paths(monkeypatch):
    commands = iter([
        "",
        "badcmd",
        "badcmd",
        "badcmd",
        "badcmd",
        "exit",
    ])

    def fake_prompt(*args, **kwargs):
        return next(commands)

    errors = iter([
        click.ClickException("bad"),
        click.exceptions.Exit(),
        SystemExit(1),
        Exception("boom"),
    ])

    def fake_cli_main(*args, **kwargs):
        raise next(errors)

    monkeypatch.setattr(cli, "prompt", fake_prompt)
    monkeypatch.setattr(cli.cli, "main", fake_cli_main)

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    assert "Error" in output
