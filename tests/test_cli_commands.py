from pathlib import Path

from click.testing import CliRunner

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition


class DummyAzureClient:
    def __init__(self, subscription_id=None):
        self.subscription_id = subscription_id

    def create_custom_role(self, role):
        return {
            "id": "role-id",
            "name": role.Name,
        }

    def list_custom_roles(self):
        return [
            {
                "id": "role-id",
                "name": "Role",
                "permissions": [{"actions": ["a"], "data_actions": []}],
            }
        ]


def configure_manager(monkeypatch, tmp_path: Path) -> RoleManager:
    manager = RoleManager(roles_dir=tmp_path)
    monkeypatch.setattr(cli, "role_manager", manager)
    return manager


def test_create_load_save_view_list(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["create", "--name", "Test Role", "--description", "Desc"])
    assert result.exit_code == 0

    save_result = runner.invoke(cli.cli, ["save", "--name", "test-role", "--overwrite"])
    assert save_result.exit_code == 0

    list_result = runner.invoke(cli.cli, ["list"])
    assert list_result.exit_code == 0
    assert "test-role" in list_result.output

    file_path = tmp_path / "example.json"
    manager.save_to_file(manager.current_role, file_path, overwrite=True)

    load_result = runner.invoke(cli.cli, ["load", "--name", str(file_path)])
    assert load_result.exit_code == 0

    view_result = runner.invoke(cli.cli, ["view"])
    assert view_result.exit_code == 0
    assert "Test Role" in view_result.output


def test_merge_command(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Target", "Target role")

    source = AzureRoleDefinition(
        Name="Source Role",
        Description="Source",
        Permissions=[PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"])],
    )
    manager.save_to_roles_dir(source, overwrite=True)

    result = runner.invoke(cli.cli, ["merge", "--roles", "source-role", "--filter", "Microsoft.Storage/*"])

    assert result.exit_code == 0
    assert "Merged permissions" in result.output


def test_remove_and_errors(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)

    view_result = runner.invoke(cli.cli, ["view"])
    assert view_result.exit_code != 0

    manager.create_role("Remove Role", "Desc")
    remove_result = runner.invoke(cli.cli, ["remove"])
    assert remove_result.exit_code != 0
    assert "Specify --filter" in remove_result.output


def test_publish_and_list_azure(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    manager.create_role("Publish Role", "Desc")

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClient)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")  # Set subscription context

    publish_result = runner.invoke(cli.cli, ["publish", "--name", "Publish Role"])
    assert publish_result.exit_code == 0
    assert "Role published" in publish_result.output

    list_result = runner.invoke(cli.cli, ["list-azure"])
    assert list_result.exit_code == 0
    assert "Azure Custom Roles" in list_result.output


def test_list_no_roles(monkeypatch, tmp_path: Path):
    runner = CliRunner()
    configure_manager(monkeypatch, tmp_path)

    result = runner.invoke(cli.cli, ["list"])
    assert result.exit_code == 0
    assert "No roles found" in result.output
