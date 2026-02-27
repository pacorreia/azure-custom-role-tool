from pathlib import Path
import runpy
import sys

import pytest
from click.testing import CliRunner

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import (
    RoleManager,
    AzureRoleDefinition,
    PermissionDefinition,
)


def configure_manager(monkeypatch, tmp_path: Path) -> RoleManager:
    manager = RoleManager(roles_dir=tmp_path)
    monkeypatch.setattr(cli, "role_manager", manager)
    monkeypatch.setattr(cli, "current_role_file_path", None)
    return manager


def test_load_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "load_from_name", raise_error)

    result = runner.invoke(cli.cli, ["load", "--name", "role"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_merge_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Target", "Target role")

    def load_role(_name):
        return AzureRoleDefinition(Name="Source", Description="Source", Permissions=[])

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "load_from_name", load_role)
    monkeypatch.setattr(manager, "merge_roles", raise_error)

    result = runner.invoke(
        cli.cli, ["merge", "--roles", "source", "--filter", "Microsoft.Storage/%"]
    )
    assert result.exit_code != 0
    assert "Error" in result.output


def test_remove_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Remove", "Desc")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "remove_permissions", raise_error)

    result = runner.invoke(cli.cli, ["remove", "--filter", "Microsoft.Storage/%"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_list_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "list_roles", raise_error)

    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_save_no_current_role(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["save", "--name", "role"])
    assert result.exit_code != 0
    assert "No current role" in result.output


def test_publish_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Publish", "Desc")

    class ErrorAzureClient:
        def __init__(self, subscription_id=None):
            self.subscription_id = subscription_id

        def create_custom_role(self, role):
            raise RuntimeError("boom")

    monkeypatch.setattr(cli, "AzureClient", ErrorAzureClient)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["publish", "--name", "Publish"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_view_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("View", "Desc")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "print_role_details", raise_error)

    result = runner.invoke(cli.cli, ["view"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_group_by_namespace_other_bucket():
    grouped = cli._group_by_namespace([""])
    assert "" in grouped


def test_interactive_current_role_and_empty_args(monkeypatch, tmp_path: Path):
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Interactive", "Desc")

    commands = iter(["   ", "exit"])

    def fake_prompt(*args, **kwargs):
        return next(commands)

    monkeypatch.setattr(cli, "PROMPT_SESSION", type('MockSession', (), {'prompt': fake_prompt})())

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    assert "Interactive" in output


def test_interactive_empty_args_path(monkeypatch):
    commands = iter(["noop", "exit"])

    def fake_prompt(*args, **kwargs):
        return next(commands)

    def fake_split(_value):
        return []

    monkeypatch.setattr(cli, "PROMPT_SESSION", type('MockSession', (), {'prompt': fake_prompt})())
    monkeypatch.setattr(cli.shlex, "split", fake_split)

    with cli.term.capture():
        cli.interactive_mode()


def test_interactive_outer_exception(monkeypatch):
    steps = iter([Exception("boom"), "exit"])

    def fake_prompt(*args, **kwargs):
        item = next(steps)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(cli, "PROMPT_SESSION", type('MockSession', (), {'prompt': fake_prompt})())

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    assert "Error" in output


def test_cli_main_function(monkeypatch):
    called = {"count": 0}

    def fake_cli():
        called["count"] += 1

    monkeypatch.setattr(cli, "cli", fake_cli)

    cli.main()

    assert called["count"] == 1


def test_cli_module_main(monkeypatch):
    argv = ["prog", "--help"]
    monkeypatch.setattr(sys, "argv", argv)

    # Avoid RuntimeWarning about re-importing an already-loaded module.
    sys.modules.pop("azure_custom_role_tool.cli", None)

    with pytest.raises(SystemExit):
        runpy.run_module("azure_custom_role_tool.cli", run_name="__main__")


def test_remove_no_current_role(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["remove", "--filter", "Microsoft.Storage/%"])
    assert result.exit_code != 0
    assert "No current role" in result.output


def test_remove_success(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Remove", "Desc")

    result = runner.invoke(cli.cli, ["remove", "--filter", "Microsoft.Storage/%"])
    assert result.exit_code == 0
    assert "Removed permissions" in result.output


def test_save_unexpected_error(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Save", "Desc")

    def raise_error(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(manager, "save_to_file", raise_error)

    result = runner.invoke(cli.cli, ["save", "--name", "save"])
    assert result.exit_code != 0
    assert "Error" in result.output


def test_interactive_command_entry(monkeypatch):
    called = {"count": 0}

    def fake_interactive():
        called["count"] += 1

    monkeypatch.setattr(cli, "interactive_mode", fake_interactive)

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["console"])

    assert result.exit_code == 0
    assert called["count"] == 1


def test_console_command_blocked_in_console_mode(monkeypatch):
    """Test that console command is blocked when already in console mode."""
    commands = iter(["console", "exit"])

    def fake_prompt(*args, **kwargs):
        return next(commands)

    monkeypatch.setattr(cli, "PROMPT_SESSION", type('MockSession', (), {'prompt': fake_prompt})())

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    assert "not available in console mode" in output


def test_unknown_command_in_console_mode(monkeypatch):
    """Test that unknown commands show appropriate error message."""
    commands = iter(["unknowncommand", "exit"])

    def fake_prompt(*args, **kwargs):
        return next(commands)

    monkeypatch.setattr(cli, "PROMPT_SESSION", type('MockSession', (), {'prompt': fake_prompt})())

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    # Remove ANSI codes for cleaner assertion
    import re

    clean_output = re.sub(r"\x1b\[[0-9;]*m", "", output)
    assert "Unknown command" in clean_output
    assert "help" in clean_output
