from pathlib import Path

from click.testing import CliRunner

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition


def configure_manager(monkeypatch, tmp_path: Path) -> RoleManager:
    manager = RoleManager(roles_dir=tmp_path)
    monkeypatch.setattr(cli, "role_manager", manager)
    return manager


def test_load_with_file_path(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    role = manager.create_role("File Role", "Desc")

    file_path = tmp_path / "file-role.json"
    manager.save_to_file(role, file_path, overwrite=True)

    result = runner.invoke(cli.cli, ["load", "--name", str(file_path)])

    assert result.exit_code == 0
    assert "Loaded role" in result.output


def test_load_with_role_dir(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    roles_dir = tmp_path / "roles"
    roles_dir.mkdir()

    manager = RoleManager(roles_dir=roles_dir)
    role = manager.create_role("Dir Role", "Desc")
    manager.save_to_roles_dir(role, overwrite=True)

    monkeypatch.setattr(cli, "role_manager", manager)

    result = runner.invoke(
        cli.cli,
        ["load", "--name", "dir-role", "--role-dir", str(roles_dir)],
    )

    assert result.exit_code == 0
    assert "Dir Role" in result.output


def test_merge_with_missing_role_warning(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Target", "Target role")

    source = AzureRoleDefinition(
        Name="Source Role",
        Description="Source",
        Permissions=[PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"])],
    )
    manager.save_to_roles_dir(source, overwrite=True)

    result = runner.invoke(
        cli.cli,
        ["merge", "--roles", "source-role,missing-role", "--filter", "Microsoft.Storage/*"],
    )

    assert result.exit_code == 0
    assert "Roles not found (local or Azure): missing-role" in result.output
    assert "Merged permissions" in result.output


def test_save_with_output_path(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Save Role", "Desc")

    output_path = tmp_path / "custom.json"
    result = runner.invoke(
        cli.cli,
        ["save", "--name", "save-role", "--output", str(output_path), "--overwrite"],
    )

    assert result.exit_code == 0
    assert output_path.exists()


def test_list_with_name_missing(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["list", "--name", "missing-role"])

    assert result.exit_code != 0
    assert "Error" in result.output


def test_publish_no_current_role(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["publish", "--name", "NoRole"])

    assert result.exit_code != 0
    assert "No current role" in result.output


def test_interactive_keyboard_interrupt(monkeypatch):
    def raise_keyboard_interrupt(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli, "prompt", raise_keyboard_interrupt)

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    assert "Goodbye" in output


def test_run_shell_command_exception(monkeypatch):
    def raise_error(*args, **kwargs):
        raise Exception("boom")

    monkeypatch.setattr(cli.subprocess, "run", raise_error)

    with cli.term.capture() as capture:
        cli.run_shell_command("bad")

    output = capture.get()
    assert "Error executing command" in output
