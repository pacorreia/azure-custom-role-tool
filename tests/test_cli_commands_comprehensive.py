"""Comprehensive CLI command tests to ensure all functionality is properly validated."""

from pathlib import Path
from unittest.mock import Mock

from click.testing import CliRunner

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import (
    RoleManager,
    AzureRoleDefinition,
    PermissionDefinition,
)


def configure_manager(monkeypatch, tmp_path: Path) -> RoleManager:
    """Configure a test role manager."""
    manager = RoleManager(roles_dir=tmp_path)
    monkeypatch.setattr(cli, "role_manager", manager)
    monkeypatch.setattr(cli, "current_role_file_path", None)
    return manager


class TestRemoveCommand:
    """Comprehensive tests for the remove command with various filter combinations."""

    def test_remove_with_string_filter(self, monkeypatch, tmp_path: Path):
        """Test remove command removes matching permissions based on string pattern."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with multiple permissions
        role = manager.create_role("Test Role", "Test")
        role.Permissions = [
            PermissionDefinition(
                Actions=[
                    "Microsoft.Storage/storageAccounts/read",
                    "Microsoft.Storage/storageAccounts/write",
                    "Microsoft.Compute/virtualMachines/read",
                ]
            )
        ]
        manager.current_role = role

        # Remove only Storage permissions
        result = runner.invoke(cli.cli, ["remove", "--filter", "Microsoft.Storage/%"])

        assert result.exit_code == 0
        assert "Removed permissions" in result.output

        # Verify only Compute permission remains
        remaining_actions = manager.current_role.Permissions[0].Actions
        assert "Microsoft.Compute/virtualMachines/read" in remaining_actions
        assert "Microsoft.Storage/storageAccounts/read" not in remaining_actions
        assert "Microsoft.Storage/storageAccounts/write" not in remaining_actions

    def test_remove_with_type_filter_control(self, monkeypatch, tmp_path: Path):
        """Test remove command with control type filter."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with both control and data plane permissions
        role = manager.create_role("Test Role", "Test")
        role.Permissions = [
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/read"],
                DataActions=[
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
                ],
            )
        ]
        manager.current_role = role

        # Remove only control plane permissions
        result = runner.invoke(cli.cli, ["remove", "--filter-type", "control"])

        assert result.exit_code == 0

        # Verify data actions remain but control actions removed
        perms = manager.current_role.Permissions[0]
        assert len(perms.Actions) == 0
        assert len(perms.DataActions) == 1

    def test_remove_with_type_filter_data(self, monkeypatch, tmp_path: Path):
        """Test remove command with data type filter."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with both control and data plane permissions
        role = manager.create_role("Test Role", "Test")
        role.Permissions = [
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/read"],
                DataActions=[
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
                ],
            )
        ]
        manager.current_role = role

        # Remove only data plane permissions
        result = runner.invoke(cli.cli, ["remove", "--filter-type", "data"])

        assert result.exit_code == 0

        # Verify control actions remain but data actions removed
        perms = manager.current_role.Permissions[0]
        assert len(perms.Actions) == 1
        assert len(perms.DataActions) == 0

    def test_remove_with_combined_filters(self, monkeypatch, tmp_path: Path):
        """Test remove command with both string and type filters."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with mixed permissions
        role = manager.create_role("Test Role", "Test")
        role.Permissions = [
            PermissionDefinition(
                Actions=[
                    "Microsoft.Storage/storageAccounts/read",
                    "Microsoft.Compute/virtualMachines/read",
                ],
                DataActions=[
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
                ],
            )
        ]
        manager.current_role = role

        # Remove only Storage control plane permissions
        result = runner.invoke(
            cli.cli,
            ["remove", "--filter", "Microsoft.Storage/%", "--filter-type", "control"],
        )

        assert result.exit_code == 0

        # Verify: Compute control remains, Storage data remains, Storage control removed
        perms = manager.current_role.Permissions[0]
        assert "Microsoft.Compute/virtualMachines/read" in perms.Actions
        assert "Microsoft.Storage/storageAccounts/read" not in perms.Actions
        assert (
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
            in perms.DataActions
        )

    def test_remove_all_permissions_results_in_empty(self, monkeypatch, tmp_path: Path):
        """Test that removing all permissions results in empty permissions array."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with permissions
        role = manager.create_role("Test Role", "Test")
        role.Permissions = [
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"])
        ]
        manager.current_role = role

        # Remove all permissions
        result = runner.invoke(cli.cli, ["remove", "--filter", "%"])

        assert result.exit_code == 0
        assert len(manager.current_role.Permissions) == 0

    def test_remove_no_matching_permissions(self, monkeypatch, tmp_path: Path):
        """Test remove command when no permissions match the filter."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with Storage permissions
        role = manager.create_role("Test Role", "Test")
        role.Permissions = [
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"])
        ]
        manager.current_role = role

        # Try to remove Compute permissions (none exist)
        result = runner.invoke(cli.cli, ["remove", "--filter", "Microsoft.Compute/%"])

        assert result.exit_code == 0
        # Original permissions should remain
        assert (
            "Microsoft.Storage/storageAccounts/read"
            in manager.current_role.Permissions[0].Actions
        )


class TestViewCommand:
    """Comprehensive tests for the view command."""

    def test_view_basic_without_all_flag(self, monkeypatch, tmp_path: Path):
        """Test view command displays current role basic information."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with permissions
        role = manager.create_role("Test View Role", "Description for viewing")
        role.Permissions = [
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"])
        ]
        manager.current_role = role

        result = runner.invoke(cli.cli, ["view"])

        assert result.exit_code == 0
        assert "Test View Role" in result.output
        assert "Description for viewing" in result.output
        assert "Microsoft.Storage" in result.output

    def test_view_with_all_flag(self, monkeypatch, tmp_path: Path):
        """Test view command with --all flag shows all permissions without truncation."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with many permissions (more than truncation limit)
        permissions_list = [
            f"Microsoft.ResourceType{i}/resource/action" for i in range(15)
        ]
        role = manager.create_role("Large Role", "Role with many permissions")
        role.Permissions = [PermissionDefinition(Actions=permissions_list)]
        manager.current_role = role

        # View without --all (should truncate)
        result_truncated = runner.invoke(cli.cli, ["view"])
        assert result_truncated.exit_code == 0

        # View with --all (should show all)
        result_all = runner.invoke(cli.cli, ["view", "--all"])
        assert result_all.exit_code == 0
        assert "Large Role" in result_all.output
        # Should contain permissions from the list
        assert "Microsoft.ResourceType" in result_all.output

    def test_view_no_current_role(self, monkeypatch, tmp_path: Path):
        """Test view command fails when no current role is set."""
        runner = CliRunner()
        configure_manager(monkeypatch, tmp_path)

        result = runner.invoke(cli.cli, ["view"])

        assert result.exit_code != 0
        assert "No current role" in result.output

    def test_view_with_data_actions(self, monkeypatch, tmp_path: Path):
        """Test view command displays both control and data plane actions."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with both types
        role = manager.create_role("Mixed Role", "Has both action types")
        role.Permissions = [
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/read"],
                DataActions=[
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
                ],
            )
        ]
        manager.current_role = role

        result = runner.invoke(cli.cli, ["view"])

        assert result.exit_code == 0
        assert "Mixed Role" in result.output
        assert "Actions:" in result.output
        assert "Data Actions:" in result.output or "DataActions:" in result.output

    def test_view_with_not_actions(self, monkeypatch, tmp_path: Path):
        """Test view command displays NotActions if present."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role with NotActions (like Contributor)
        role = manager.create_role("Role with NotActions", "Has exclusions")
        role.Permissions = [
            PermissionDefinition(
                Actions=["*"],
                NotActions=[
                    "Microsoft.Authorization/*/Delete",
                    "Microsoft.Authorization/*/Write",
                ],
            )
        ]
        manager.current_role = role

        result = runner.invoke(cli.cli, ["view"])

        assert result.exit_code == 0
        assert "Role with NotActions" in result.output
        # Should display NotActions section
        assert "Microsoft.Authorization" in result.output


class TestPublishCommand:
    """Comprehensive tests for the publish command."""

    def test_publish_success(self, monkeypatch, tmp_path: Path):
        """Test successful role publication to Azure."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role
        role = manager.create_role("Publish Test", "Test publishing")
        manager.current_role = role

        # Mock Azure client
        mock_client_class = Mock()
        mock_client_instance = Mock()
        mock_client_instance.create_custom_role.return_value = {
            "id": "role-id-123",
            "name": "Publish Test",
        }
        mock_client_class.return_value = mock_client_instance

        monkeypatch.setattr(cli, "AzureClient", mock_client_class)
        monkeypatch.setattr(cli, "current_subscription", "sub-123")

        result = runner.invoke(cli.cli, ["publish", "--name", "Publish Test"])

        assert result.exit_code == 0
        assert "Role published" in result.output

    def test_publish_with_subscription_id(self, monkeypatch, tmp_path: Path):
        """Test publish command with explicit subscription ID."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role
        role = manager.create_role("Publish Test", "Test")
        manager.current_role = role

        # Mock Azure client
        mock_client_class = Mock()
        mock_client_instance = Mock()
        mock_client_instance.create_custom_role.return_value = {
            "id": "role-123",
            "name": "Publish Test",
        }
        mock_client_class.return_value = mock_client_instance

        monkeypatch.setattr(cli, "AzureClient", mock_client_class)

        result = runner.invoke(
            cli.cli,
            ["publish", "--name", "Publish Test", "--subscription-id", "custom-sub-id"],
        )

        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        # Verify Azure client was created with the custom subscription
        mock_client_class.assert_called_with(subscription_id="custom-sub-id")

    def test_publish_no_current_role(self, monkeypatch, tmp_path: Path):
        """Test publish fails when no current role is set."""
        runner = CliRunner()
        configure_manager(monkeypatch, tmp_path)

        result = runner.invoke(cli.cli, ["publish", "--name", "test"])

        assert result.exit_code != 0
        assert "No current role" in result.output

    def test_publish_azure_error(self, monkeypatch, tmp_path: Path):
        """Test publish handles Azure API errors gracefully."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role
        role = manager.create_role("Publish Test", "Test")
        manager.current_role = role

        # Mock Azure client that raises error
        mock_client_class = Mock()
        mock_client_instance = Mock()
        mock_client_instance.create_custom_role.side_effect = Exception(
            "Azure API Error"
        )
        mock_client_class.return_value = mock_client_instance

        monkeypatch.setattr(cli, "AzureClient", mock_client_class)
        monkeypatch.setattr(cli, "current_subscription", "sub-123")

        result = runner.invoke(cli.cli, ["publish", "--name", "Publish Test"])

        assert result.exit_code != 0
        assert "Error" in result.output


class TestCreateCommand:
    """Comprehensive tests for the create command."""

    def test_create_with_valid_inputs(self, monkeypatch, tmp_path: Path):
        """Test creating a role with valid name and description."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        result = runner.invoke(
            cli.cli,
            ["create", "--name", "New Test Role", "--description", "Test description"],
        )

        assert result.exit_code == 0
        assert manager.current_role is not None
        assert manager.current_role.Name == "New Test Role"
        assert manager.current_role.Description == "Test description"

    def test_create_initializes_empty_permissions(self, monkeypatch, tmp_path: Path):
        """Test that create initializes role with empty permission block."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        result = runner.invoke(
            cli.cli, ["create", "--name", "Empty Role", "--description", "No perms yet"]
        )

        assert result.exit_code == 0
        assert len(manager.current_role.Permissions) == 1
        assert manager.current_role.Permissions[0].is_empty()

    def test_create_with_special_characters(self, monkeypatch, tmp_path: Path):
        """Test creating role with special characters in name and description."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        result = runner.invoke(
            cli.cli,
            [
                "create",
                "--name",
                "Role-With_Special.Chars (Test)",
                "--description",
                "Description with 'quotes' and \"double quotes\"",
            ],
        )

        assert result.exit_code == 0
        assert "Role-With_Special.Chars (Test)" in manager.current_role.Name


class TestSaveCommand:
    """Comprehensive tests for the save command."""

    def test_save_to_default_location(self, monkeypatch, tmp_path: Path):
        """Test save command saves to default roles directory."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role
        role = manager.create_role("Save Test", "Test saving")
        manager.current_role = role

        result = runner.invoke(cli.cli, ["save", "--name", "save-test", "--overwrite"])

        assert result.exit_code == 0
        assert (tmp_path / "save-test.json").exists()

    def test_save_to_custom_output_path(self, monkeypatch, tmp_path: Path):
        """Test save command saves to custom output path."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create role
        role = manager.create_role("Custom Path Test", "Test")
        manager.current_role = role

        custom_path = tmp_path / "custom" / "location.json"
        result = runner.invoke(
            cli.cli,
            ["save", "--name", "test", "--output", str(custom_path), "--overwrite"],
        )

        assert result.exit_code == 0
        assert custom_path.exists()

    def test_save_without_overwrite_flag_fails_if_exists(
        self, monkeypatch, tmp_path: Path
    ):
        """Test save command fails when file exists and overwrite not specified."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create and save role first time
        role = manager.create_role("Duplicate Test", "Test")
        manager.current_role = role

        # Save first time with overwrite
        result1 = runner.invoke(cli.cli, ["save", "--name", "duplicate", "--overwrite"])
        assert result1.exit_code == 0

        # Try to save again without overwrite flag
        result2 = runner.invoke(cli.cli, ["save", "--name", "duplicate"])
        assert result2.exit_code != 0

    def test_save_without_args_quick_saves_to_previous_path(
        self, monkeypatch, tmp_path: Path
    ):
        """Test save without args reuses the previous saved filename/path."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        role = manager.create_role("Quick Save", "Initial")
        manager.current_role = role

        first = runner.invoke(cli.cli, ["save", "--name", "quick-save", "--overwrite"])
        assert first.exit_code == 0

        role.Description = "Updated"
        second = runner.invoke(cli.cli, ["save"])

        assert second.exit_code == 0
        assert "quick-saved" in second.output
        assert (tmp_path / "quick-save.json").exists()

    def test_save_without_args_prompts_filename_when_never_saved(
        self, monkeypatch, tmp_path: Path
    ):
        """Test save without args asks for filename when role was never saved."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        role = manager.create_role("Prompt Save", "Desc")
        manager.current_role = role

        result = runner.invoke(cli.cli, ["save"], input="prompt-target\n")

        assert result.exit_code == 0
        assert "Output filename" in result.output
        assert (tmp_path / "prompt-target.json").exists()


class TestListCommand:
    """Comprehensive tests for the list command."""

    def test_list_all_roles(self, monkeypatch, tmp_path: Path):
        """Test list command displays all roles in directory."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create and save multiple roles
        for i in range(3):
            role = AzureRoleDefinition(
                Name=f"Test Role {i}",
                Description=f"Description {i}",
                Permissions=[PermissionDefinition()],
            )
            manager.save_to_roles_dir(role, overwrite=True)

        result = runner.invoke(cli.cli, ["list"])

        assert result.exit_code == 0
        assert "test-role-0" in result.output
        assert "test-role-1" in result.output
        assert "test-role-2" in result.output

    def test_list_specific_role_by_name(self, monkeypatch, tmp_path: Path):
        """Test list command with --name filter."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create multiple roles
        role1 = AzureRoleDefinition(
            Name="Storage Admin", Description="D1", Permissions=[PermissionDefinition()]
        )
        role2 = AzureRoleDefinition(
            Name="Compute Admin", Description="D2", Permissions=[PermissionDefinition()]
        )

        manager.save_to_roles_dir(role1, overwrite=True)
        manager.save_to_roles_dir(role2, overwrite=True)

        result = runner.invoke(cli.cli, ["list", "--name", "storage-admin"])

        assert result.exit_code == 0
        assert "storage-admin" in result.output or "Storage Admin" in result.output

    def test_list_empty_directory(self, monkeypatch, tmp_path: Path):
        """Test list command handles empty roles directory gracefully."""
        runner = CliRunner()
        configure_manager(monkeypatch, tmp_path)

        result = runner.invoke(cli.cli, ["list"])

        assert result.exit_code == 0
        assert "No roles found" in result.output

    def test_list_with_custom_role_dir(self, monkeypatch, tmp_path: Path):
        """Test list command with custom --role-dir."""
        runner = CliRunner()
        configure_manager(monkeypatch, tmp_path)

        # Create custom directory with role
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        role = AzureRoleDefinition(
            Name="Custom Dir Role",
            Description="Test",
            Permissions=[PermissionDefinition()],
        )
        manager = RoleManager(roles_dir=custom_dir)
        manager.save_to_roles_dir(role, overwrite=True)

        result = runner.invoke(cli.cli, ["list", "--role-dir", str(custom_dir)])

        assert result.exit_code == 0
        assert "custom-dir-role" in result.output or "Custom Dir Role" in result.output


class TestLoadCommand:
    """Comprehensive tests for the load command."""

    def test_load_by_name_from_default_dir(self, monkeypatch, tmp_path: Path):
        """Test load command loads role by name from default directory."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Save a role first
        role = AzureRoleDefinition(
            Name="Loadable Role",
            Description="Test loading",
            Permissions=[PermissionDefinition(Actions=["Microsoft.Storage/*/read"])],
        )
        manager.save_to_roles_dir(role, overwrite=True)

        result = runner.invoke(cli.cli, ["load", "--name", "loadable-role"])

        assert result.exit_code == 0
        assert manager.current_role is not None
        assert manager.current_role.Name == "Loadable Role"

    def test_load_from_file_path(self, monkeypatch, tmp_path: Path):
        """Test load command loads role from explicit file path."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Save role to specific path
        role = AzureRoleDefinition(
            Name="File Path Role",
            Description="Test",
            Permissions=[PermissionDefinition()],
        )
        file_path = tmp_path / "explicit-path.json"
        manager.save_to_file(role, file_path, overwrite=True)

        result = runner.invoke(cli.cli, ["load", "--name", str(file_path)])

        assert result.exit_code == 0
        assert manager.current_role.Name == "File Path Role"

    def test_load_nonexistent_role(self, monkeypatch, tmp_path: Path):
        """Test load command fails gracefully for nonexistent role."""
        runner = CliRunner()
        configure_manager(monkeypatch, tmp_path)

        # Mock to prevent Azure fallback
        monkeypatch.setattr(cli, "current_subscription", None)

        result = runner.invoke(cli.cli, ["load", "--name", "nonexistent-role"])

        assert result.exit_code != 0
        assert "Role not found" in result.output or "not found" in result.output

    def test_load_replaces_current_role(self, monkeypatch, tmp_path: Path):
        """Test load command replaces the current role."""
        runner = CliRunner()
        manager = configure_manager(monkeypatch, tmp_path)

        # Create initial role
        initial = manager.create_role("Initial Role", "First")

        # Save a different role
        replacement = AzureRoleDefinition(
            Name="Replacement",
            Description="Second",
            Permissions=[PermissionDefinition()],
        )
        manager.save_to_roles_dir(replacement, overwrite=True)

        # Load the replacement
        result = runner.invoke(cli.cli, ["load", "--name", "replacement"])

        assert result.exit_code == 0
        assert manager.current_role.Name == "Replacement"
        assert manager.current_role.Name != "Initial Role"
