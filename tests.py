"""
Unit tests for Azure Custom Role Designer
"""

import pytest
import tempfile
import json
from pathlib import Path

from role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition
from permission_filter import PermissionFilter, PermissionType


class TestPermissionFilter:
    """Tests for permission filtering."""

    def test_is_data_plane(self):
        """Test data plane permission detection."""
        data_plane_actions = [
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            "Microsoft.Sql/servers/databases/tables/data/read",
            "Microsoft.CosmosDB/databaseAccounts/databases/collections/data/read",
        ]
        
        for action in data_plane_actions:
            assert PermissionFilter.is_data_plane(action), f"Should be data plane: {action}"

    def test_is_control_plane(self):
        """Test control plane permission detection."""
        control_plane_actions = [
            "Microsoft.Compute/virtualMachines/read",
            "Microsoft.Storage/storageAccounts/write",
            "Microsoft.Network/virtualNetworks/read",
        ]
        
        for action in control_plane_actions:
            assert PermissionFilter.is_control_plane(action), f"Should be control plane: {action}"

    def test_classify_permissions(self):
        """Test permission classification."""
        actions = [
            "Microsoft.Compute/virtualMachines/read",  # control
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",  # data
            "Microsoft.Sql/servers/read",  # control
            "Microsoft.Sql/servers/databases/tables/data/read",  # data
        ]
        
        classified = PermissionFilter.classify_permissions(actions)
        
        assert len(classified["control"]) == 2
        assert len(classified["data"]) == 2

    def test_filter_by_string(self):
        """Test string filtering."""
        actions = [
            "Microsoft.Storage/storageAccounts/read",
            "Microsoft.Storage/storageAccounts/write",
            "Microsoft.Storage/storageAccounts/delete",
            "Microsoft.Compute/virtualMachines/read",
        ]
        
        # Filter by Storage
        filtered = PermissionFilter.filter_by_string(actions, "Microsoft.Storage*")
        assert len(filtered) == 3
        assert all("Storage" in a for a in filtered)

    def test_filter_by_type(self):
        """Test type-based filtering."""
        actions = [
            "Microsoft.Storage/storageAccounts/read",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            "Microsoft.Compute/virtualMachines/read",
        ]
        
        # Filter data actions
        data_actions = PermissionFilter.filter_by_type(actions, PermissionType.DATA)
        assert len(data_actions) == 1
        assert "blobServices" in data_actions[0]
        
        # Filter control actions
        control_actions = PermissionFilter.filter_by_type(actions, PermissionType.CONTROL)
        assert len(control_actions) == 2


class TestRoleManager:
    """Tests for role management."""

    def test_create_role(self):
        """Test creating a new role."""
        manager = RoleManager()
        role = manager.create_role("Test Role", "Test description")
        
        assert role.Name == "Test Role"
        assert role.Description == "Test description"
        assert role.IsCustom == True
        assert role.Type == "CustomRole"

    def test_save_and_load_role(self):
        """Test saving and loading roles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create and save role
            role = manager.create_role("Test Role", "Test description")
            role.Permissions = [
                PermissionDefinition(
                    Actions=["Microsoft.Storage/*/read"],
                    DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"],
                )
            ]
            
            saved_path = manager.save_to_file(role, roles_dir / "test-role.json")
            assert saved_path.exists()
            
            # Load role
            manager2 = RoleManager(roles_dir)
            loaded_role = manager2.load_from_name("test-role")
            
            assert loaded_role.Name == role.Name
            assert loaded_role.Description == role.Description
            assert len(loaded_role.Permissions) > 0

    def test_merge_roles(self):
        """Test merging permissions from multiple roles."""
        manager = RoleManager()
        
        # Create source roles
        role1 = AzureRoleDefinition(
            Name="Role1",
            Description="Role 1",
            Permissions=[
                PermissionDefinition(
                    Actions=["Microsoft.Storage/*/read", "Microsoft.Storage/*/write"]
                )
            ],
        )
        
        role2 = AzureRoleDefinition(
            Name="Role2",
            Description="Role 2",
            Permissions=[
                PermissionDefinition(
                    Actions=["Microsoft.Compute/*/read"]
                )
            ],
        )
        
        # Create and merge
        target = manager.create_role("Merged Role", "Merged")
        manager.merge_roles([role1, role2])
        
        all_actions = []
        for perm in manager.current_role.Permissions:
            all_actions.extend(perm.Actions)
        
        assert "Microsoft.Storage/*/read" in all_actions
        assert "Microsoft.Compute/*/read" in all_actions

    def test_filter_merge(self):
        """Test merging with filters."""
        manager = RoleManager()
        
        role = AzureRoleDefinition(
            Name="Role",
            Description="Test",
            Permissions=[
                PermissionDefinition(
                    Actions=[
                        "Microsoft.Storage/storageAccounts/read",
                        "Microsoft.Compute/virtualMachines/read",
                    ]
                )
            ],
        )
        
        manager.create_role("Target", "Target role")
        manager.merge_roles([role], string_filter="Microsoft.Storage*")
        
        merged_actions = []
        for perm in manager.current_role.Permissions:
            merged_actions.extend(perm.Actions)
        
        assert "Microsoft.Storage/storageAccounts/read" in merged_actions
        assert "Microsoft.Compute/virtualMachines/read" not in merged_actions

    def test_remove_permissions(self):
        """Test removing permissions."""
        manager = RoleManager()
        
        manager.create_role("Test", "Test")
        manager.current_role.Permissions = [
            PermissionDefinition(
                Actions=[
                    "Microsoft.Storage/storageAccounts/read",
                    "Microsoft.Storage/storageAccounts/write",
                    "Microsoft.Storage/storageAccounts/delete",
                    "Microsoft.Compute/virtualMachines/read",
                ]
            )
        ]
        
        manager.remove_permissions(string_filter="*delete")
        
        remaining_actions = []
        for perm in manager.current_role.Permissions:
            remaining_actions.extend(perm.Actions)
        
        assert "Microsoft.Storage/storageAccounts/delete" not in remaining_actions
        assert len(remaining_actions) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
