"""Tests for Azure role viewing and searching commands."""

from pathlib import Path
from click.testing import CliRunner
import pytest

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import (
    RoleManager,
    AzureRoleDefinition,
    PermissionDefinition,
)
from azure_custom_role_tool.azure_client import AzureClient


class DummyAzureClientWithAllRoles:
    """Mock Azure client that returns both custom and built-in roles."""

    def __init__(self, subscription_id=None):
        self.subscription_id = subscription_id

    def list_all_roles(self):
        return [
            {
                "id": "/subscriptions/sub-123/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c",
                "name": "Contributor",
                "description": "Manage all resources",
                "type": "Microsoft.Authorization/roleDefinitions",
                "permissions": [
                    {
                        "actions": ["*"],
                        "not_actions": ["Microsoft.Authorization/*/Delete"],
                        "data_actions": [],
                        "not_data_actions": [],
                    }
                ],
                "assignable_scopes": ["/"],
            },
            {
                "id": "/subscriptions/sub-123/providers/Microsoft.Authorization/roleDefinitions/custom-123",
                "name": "Custom-Storage-Role",
                "description": "Manage storage accounts",
                "type": "Microsoft.Authorization/roleDefinitions",
                "permissions": [
                    {
                        "actions": [
                            "Microsoft.Storage/storageAccounts/read",
                            "Microsoft.Storage/storageAccounts/write",
                        ],
                        "not_actions": [],
                        "data_actions": [
                            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
                        ],
                        "not_data_actions": [],
                    }
                ],
                "assignable_scopes": ["/subscriptions/sub-123"],
            },
        ]


@pytest.fixture(autouse=True)
def isolated_role_manager(monkeypatch, tmp_path: Path):
    """Use an isolated roles directory for every test in this module."""
    manager = RoleManager(roles_dir=tmp_path / "roles")
    monkeypatch.setattr(cli, "role_manager", manager)


def test_view_azure_command_not_found(monkeypatch, tmp_path: Path):
    """Test view-azure command with non-existent role."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["view-azure", "--name", "NonExistentRole"])
    assert result.exit_code != 0
    assert "Role not found" in result.output


def test_view_azure_command_success(monkeypatch):
    """Test view-azure command displays role details and permissions."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["view-azure", "--name", "Contributor"])
    assert result.exit_code == 0
    assert "Contributor" in result.output
    assert "Microsoft.Authorization/roleDefinitions" in result.output
    assert "Microsoft.Authorization" in result.output


def test_view_azure_case_insensitive(monkeypatch):
    """Test view-azure command is case-insensitive."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["view-azure", "--name", "CONTRIBUTOR"])
    assert result.exit_code == 0
    assert "Contributor" in result.output


def test_view_azure_positional_name(monkeypatch):
    """Test view-azure accepts role name as positional argument."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    result = runner.invoke(cli.cli, ["view-azure", "Contributor"])
    assert result.exit_code == 0
    assert "Contributor" in result.output


def test_view_azure_with_filter(monkeypatch):
    """Test view-azure command with permission filter."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(
        cli.cli,
        [
            "view-azure",
            "--name",
            "Custom-Storage-Role",
            "--filter",
            "Microsoft.Storage/%",
        ],
    )
    assert result.exit_code == 0
    assert "Custom-Storage-Role" in result.output
    assert "Microsoft.Storage/storageAccounts" in result.output


def test_search_permissions_command_with_matches(monkeypatch):
    """Test search-permissions command finds matching roles."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["search-permissions", "--filter", "Microsoft.Storage/%"])
    assert result.exit_code == 0
    assert "Custom-Storage-Role" in result.output


def test_search_permissions_positional_filter(monkeypatch):
    """Test search-permissions accepts filter as positional argument."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    result = runner.invoke(cli.cli, ["search-permissions", "Microsoft.Storage/%"])
    assert result.exit_code == 0
    assert "Permissions matching" in result.output
    assert "Microsoft.Storage/storageAccounts/read" in result.output


def test_search_permissions_command_no_matches(monkeypatch):
    """Test search-permissions command when no roles match."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(
        cli.cli, ["search-permissions", "--filter", "Microsoft.Compute/nonexistent%"]
    )
    assert result.exit_code == 0
    assert "No permissions found" in result.output


def test_search_permissions_with_data_actions(monkeypatch):
    """Test search-permissions correctly searches data actions."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(
        cli.cli,
        [
            "search-permissions",
            "--filter",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/%",
        ],
    )
    assert result.exit_code == 0
    assert "Custom-Storage-Role" in result.output
    assert (
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
        in result.output
    )


def test_import_azure_permissions_with_matches(monkeypatch):
    """Test import-azure-permissions imports matching permissions into current role."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")
    cli.role_manager.create_role("TargetRole", "Target")

    result = runner.invoke(
        cli.cli,
        ["import-azure-permissions", "--filter", "Microsoft.Storage/%/read"],
    )
    assert result.exit_code == 0
    assert "Imported Azure permissions into" in result.output
    assert (
        "Microsoft.Storage/storageAccounts/read"
        in cli.role_manager.current_role.Permissions[0].Actions
    )
    assert (
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
        in cli.role_manager.current_role.Permissions[0].DataActions
    )


def test_import_azure_permissions_positional_filter(monkeypatch):
    """Test import-azure-permissions accepts filter as positional argument."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")
    cli.role_manager.create_role("TargetRole", "Target")

    result = runner.invoke(
        cli.cli,
        ["import-azure-permissions", "Microsoft.Storage/%/read"],
    )
    assert result.exit_code == 0
    assert "Imported Azure permissions into" in result.output
    assert (
        "Microsoft.Storage/storageAccounts/read"
        in cli.role_manager.current_role.Permissions[0].Actions
    )


def test_import_azure_permissions_no_matches(monkeypatch):
    """Test import-azure-permissions handles no matches gracefully."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")
    cli.role_manager.create_role("TargetRole", "Target")

    result = runner.invoke(
        cli.cli,
        ["import-azure-permissions", "--filter", "Microsoft.KeyVault/%/delete"],
    )
    assert result.exit_code == 0
    assert "No permissions found matching" in result.output


def test_load_azure_command(monkeypatch):
    """Test load-azure command loads a role from Azure as current role."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["load-azure", "--name", "Custom-Storage-Role"])
    assert result.exit_code == 0
    assert "Loaded role from Azure" in result.output
    assert "Custom-Storage-Role" in result.output


def test_load_azure_command_not_found(monkeypatch):
    """Test load-azure command when role not found."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(
        cli, "current_subscription", "sub-123"
    )  # Set subscription context

    result = runner.invoke(cli.cli, ["load-azure", "--name", "NonExistentRole"])
    assert result.exit_code != 0
    assert "Role not found in Azure" in result.output


def test_load_with_azure_fallback(monkeypatch):
    """Test load command falls back to Azure when local role not found."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    # Load Azure role without pre-loading it
    result = runner.invoke(cli.cli, ["load", "--name", "Custom-Storage-Role"])
    assert result.exit_code == 0
    assert "Loaded role from Azure" in result.output
    assert "Custom-Storage-Role" in result.output


def test_load_with_local_takes_priority(monkeypatch, tmp_path: Path):
    """Test load command loads from local even if Azure has same role."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    # Save a local role with same name as Azure role
    local_role = AzureRoleDefinition(
        Name="contributor-local",
        Description="Local version of Contributor",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Compute/virtualMachines/read"])
        ],
    )
    cli.role_manager.save_to_roles_dir(local_role, overwrite=True)

    # Load should use local version
    result = runner.invoke(cli.cli, ["load", "--name", "contributor-local"])
    assert result.exit_code == 0
    assert "Loaded role from local storage" in result.output
    assert "contributor-local" in result.output


def test_load_azure_fallback_not_found(monkeypatch):
    """Test load command fails when role not found anywhere."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    # Try to load non-existent role
    result = runner.invoke(cli.cli, ["load", "--name", "NonExistentRole"])
    assert result.exit_code != 0
    assert "Role not found" in result.output


def test_merge_with_azure_fallback(monkeypatch, tmp_path: Path):
    """Test merge command falls back to Azure when local role not found."""
    runner = CliRunner()

    # Set up role manager with a saved local role
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    # Create and set a current role
    current = cli.role_manager.create_role("TestRole", "Test role for merging")
    cli.role_manager.current_role = current

    # Merge with Azure role (not found locally)
    result = runner.invoke(cli.cli, ["merge", "--roles", "Custom-Storage-Role"])
    assert result.exit_code == 0
    assert "Loaded 'Custom-Storage-Role' from Azure" in result.output
    assert "Merged permissions from 1 role(s)" in result.output


def test_merge_mixed_local_and_azure(monkeypatch, tmp_path: Path):
    """Test merge command with both local and Azure roles."""
    runner = CliRunner()

    # Set up role manager
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    # Create and set a current role
    current = cli.role_manager.create_role("TestRole", "Test role for merging")
    cli.role_manager.current_role = current

    # Save a local role with unique name to avoid conflicts
    local_role = AzureRoleDefinition(
        Name="local-test-role-xyz",
        Description="Local role for testing",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"])
        ],
    )
    cli.role_manager.save_to_roles_dir(local_role, overwrite=True)

    # Merge both local and Azure roles
    result = runner.invoke(
        cli.cli, ["merge", "--roles", "local-test-role-xyz, Contributor"]
    )
    assert result.exit_code == 0
    assert "Loaded 'Contributor' from Azure" in result.output
    assert "Merged permissions from 2 role(s)" in result.output


def test_merge_azure_role_not_found(monkeypatch):
    """Test merge command when Azure role not found."""
    runner = CliRunner()

    # Set up role manager
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    monkeypatch.setattr(cli, "AzureClient", DummyAzureClientWithAllRoles)
    monkeypatch.setattr(cli, "current_subscription", "sub-123")

    # Create and set a current role
    current = cli.role_manager.create_role("TestRole", "Test role for merging")
    cli.role_manager.current_role = current

    # Try to merge non-existent role
    result = runner.invoke(cli.cli, ["merge", "--roles", "NonExistentRole"])
    assert result.exit_code != 0
    assert "No source roles could be loaded" in result.output
