"""Comprehensive CLI-level tests for merge command to ensure correct behavior."""
from pathlib import Path

from click.testing import CliRunner

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition


def configure_manager(monkeypatch, tmp_path: Path) -> RoleManager:
    """Configure a test role manager."""
    manager = RoleManager(roles_dir=tmp_path)
    monkeypatch.setattr(cli, "role_manager", manager)
    return manager


def test_merge_preserves_existing_permissions_via_cli(monkeypatch, tmp_path: Path):
    """Test that merge command preserves existing permissions in current role (reproduces user bug via CLI)."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create current role with existing permissions (simulating Reader)
    current = manager.create_role("My Custom Role", "Role with existing permissions")
    current.Permissions = [
        PermissionDefinition(
            Actions=[
                "Microsoft.Authorization/*/read",
                "Microsoft.Resources/subscriptions/read",
            ],
        )
    ]
    manager.current_role = current
    
    # Create source role to merge (simulating User Access Administrator)
    source = AzureRoleDefinition(
        Name="User Access Administrator",
        Description="Grants access to manage user access",
        Permissions=[
            PermissionDefinition(
                Actions=[
                    "Microsoft.Authorization/roleAssignments/write",
                    "Microsoft.Authorization/roleAssignments/delete",
                ],
            )
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Execute merge command
    result = runner.invoke(cli.cli, ["merge", "--roles", "user-access-administrator"])
    
    # Verify command succeeded
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert "Merged permissions from 1 role(s)" in result.output
    
    # Verify BOTH sets of permissions are present in merged role
    merged_role = manager.current_role
    assert len(merged_role.Permissions) == 1
    
    actions = merged_role.Permissions[0].Actions
    # Original permissions should still exist
    assert "Microsoft.Authorization/*/read" in actions, f"Original permission missing. Actions: {actions}"
    assert "Microsoft.Resources/subscriptions/read" in actions, f"Original permission missing. Actions: {actions}"
    
    # Merged permissions should be added
    assert "Microsoft.Authorization/roleAssignments/write" in actions, f"Merged permission missing. Actions: {actions}"
    assert "Microsoft.Authorization/roleAssignments/delete" in actions, f"Merged permission missing. Actions: {actions}"


def test_merge_multiple_roles_preserves_existing(monkeypatch, tmp_path: Path):
    """Test merging multiple roles preserves existing permissions."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create current role with existing permissions
    current = manager.create_role("Target", "Target with permissions")
    current.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Compute/virtualMachines/read"],
        )
    ]
    manager.current_role = current
    
    # Create first source role
    source1 = AzureRoleDefinition(
        Name="Source One",
        Description="First source",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"]),
        ],
    )
    manager.save_to_roles_dir(source1, overwrite=True)
    
    # Create second source role
    source2 = AzureRoleDefinition(
        Name="Source Two",
        Description="Second source",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Network/virtualNetworks/read"]),
        ],
    )
    manager.save_to_roles_dir(source2, overwrite=True)
    
    # Merge both roles
    result = runner.invoke(cli.cli, ["merge", "--roles", "source-one,source-two"])
    
    assert result.exit_code == 0
    assert "Merged permissions from 2 role(s)" in result.output
    
    # Verify all permissions present
    actions = manager.current_role.Permissions[0].Actions
    assert "Microsoft.Compute/virtualMachines/read" in actions  # Original
    assert "Microsoft.Storage/storageAccounts/read" in actions  # From source1
    assert "Microsoft.Network/virtualNetworks/read" in actions  # From source2


def test_merge_with_data_actions_preserves_existing(monkeypatch, tmp_path: Path):
    """Test merge preserves both control and data plane permissions."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create current role with both control and data actions
    current = manager.create_role("Target", "Target with mixed permissions")
    current.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Storage/storageAccounts/read"],
            DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"],
        )
    ]
    manager.current_role = current
    
    # Create source with additional permissions
    source = AzureRoleDefinition(
        Name="Source",
        Description="Source with more permissions",
        Permissions=[
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/write"],
                DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"],
            )
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Merge
    result = runner.invoke(cli.cli, ["merge", "--roles", "source"])
    
    assert result.exit_code == 0
    
    # Verify all actions preserved and merged
    perms = manager.current_role.Permissions[0]
    assert "Microsoft.Storage/storageAccounts/read" in perms.Actions
    assert "Microsoft.Storage/storageAccounts/write" in perms.Actions
    assert "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read" in perms.DataActions
    assert "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write" in perms.DataActions


def test_merge_with_filter_preserves_existing_unfiltered(monkeypatch, tmp_path: Path):
    """Test merge with filter preserves original permissions that don't match filter."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create role with Compute permissions
    current = manager.create_role("Target", "Target")
    current.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Compute/virtualMachines/read"],
        )
    ]
    manager.current_role = current
    
    # Create source with both Storage and Network permissions
    source = AzureRoleDefinition(
        Name="Source",
        Description="Multi-namespace source",
        Permissions=[
            PermissionDefinition(
                Actions=[
                    "Microsoft.Storage/storageAccounts/read",
                    "Microsoft.Network/virtualNetworks/read",
                ]
            )
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Merge with Storage filter only
    result = runner.invoke(cli.cli, ["merge", "--roles", "source", "--filter", "Microsoft.Storage/*"])
    
    assert result.exit_code == 0
    
    # Original Compute permission should still exist
    # Only Storage permission should be added (Network filtered out)
    actions = manager.current_role.Permissions[0].Actions
    assert "Microsoft.Compute/virtualMachines/read" in actions  # Original
    assert "Microsoft.Storage/storageAccounts/read" in actions  # Added
    assert "Microsoft.Network/virtualNetworks/read" not in actions  # Filtered out


def test_merge_with_type_filter_control_only(monkeypatch, tmp_path: Path):
    """Test merge with control type filter preserves existing and adds only control actions."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create role with both action types
    current = manager.create_role("Target", "Target")
    current.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Compute/virtualMachines/read"],
            DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"],
        )
    ]
    manager.current_role = current
    
    # Create source with both types
    source = AzureRoleDefinition(
        Name="Source",
        Description="Source",
        Permissions=[
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/read"],
                DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"],
            )
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Merge control plane only
    result = runner.invoke(cli.cli, ["merge", "--roles", "source", "--filter-type", "control"])
    
    assert result.exit_code == 0
    
    perms = manager.current_role.Permissions[0]
    # Original control and data should exist
    assert "Microsoft.Compute/virtualMachines/read" in perms.Actions
    assert "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read" in perms.DataActions
    
    # New control action should be added
    assert "Microsoft.Storage/storageAccounts/read" in perms.Actions
    
    # New data action should NOT be added (filtered out)
    assert "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write" not in perms.DataActions


def test_merge_into_empty_role(monkeypatch, tmp_path: Path):
    """Test merge into newly created empty role works correctly."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create empty role
    manager.create_role("Empty Role", "New empty role")
    
    # Create source
    source = AzureRoleDefinition(
        Name="Source",
        Description="Source",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"]),
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Merge
    result = runner.invoke(cli.cli, ["merge", "--roles", "source"])
    
    assert result.exit_code == 0
    assert "Merged permissions from 1 role(s)" in result.output
    
    # Verify permissions added
    actions = manager.current_role.Permissions[0].Actions
    assert "Microsoft.Storage/storageAccounts/read" in actions


def test_merge_deduplicates_permissions(monkeypatch, tmp_path: Path):
    """Test merge deduplicates overlapping permissions."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create current role with permission
    current = manager.create_role("Target", "Target")
    current.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Storage/storageAccounts/read"],
        )
    ]
    manager.current_role = current
    
    # Create source with same permission
    source = AzureRoleDefinition(
        Name="Source",
        Description="Source",
        Permissions=[
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/read"],  # Duplicate
            )
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Merge
    result = runner.invoke(cli.cli, ["merge", "--roles", "source"])
    
    assert result.exit_code == 0
    
    # Verify permission appears only once
    actions = manager.current_role.Permissions[0].Actions
    assert actions.count("Microsoft.Storage/storageAccounts/read") == 1


def test_merge_view_workflow(monkeypatch, tmp_path: Path):
    """Test complete workflow: load role, merge, view to verify."""
    runner = CliRunner()
    manager = configure_manager(monkeypatch, tmp_path)
    
    # Create and save base role
    base = AzureRoleDefinition(
        Name="Base Role",
        Description="Base",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Compute/virtualMachines/read"]),
        ],
    )
    manager.save_to_roles_dir(base, overwrite=True)
    
    # Create source role
    source = AzureRoleDefinition(
        Name="Additional Permissions",
        Description="More perms",
        Permissions=[
            PermissionDefinition(Actions=["Microsoft.Storage/storageAccounts/read"]),
        ],
    )
    manager.save_to_roles_dir(source, overwrite=True)
    
    # Load base role
    load_result = runner.invoke(cli.cli, ["load", "--name", "base-role"])
    assert load_result.exit_code == 0
    
    # Merge additional permissions
    merge_result = runner.invoke(cli.cli, ["merge", "--roles", "additional-permissions"])
    assert merge_result.exit_code == 0
    assert "Merged permissions from 1 role(s)" in merge_result.output
    
    # View to verify both permissions present
    view_result = runner.invoke(cli.cli, ["view"])
    assert view_result.exit_code == 0
    assert "Base Role" in view_result.output
    # Both actions should be visible in output
    assert "Microsoft.Compute" in view_result.output
    assert "Microsoft.Storage" in view_result.output
