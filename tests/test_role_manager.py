from pathlib import Path

from azure_custom_role_tool.role_manager import RoleManager, PermissionDefinition, AzureRoleDefinition
from azure_custom_role_tool.permission_filter import PermissionType


def test_create_save_load_role(tmp_path: Path):
    manager = RoleManager(roles_dir=tmp_path)
    role = manager.create_role("My Role", "Role description")

    file_path = tmp_path / "my-role.json"
    saved_path = manager.save_to_file(role, file_path, overwrite=True)

    loaded = manager.load_from_file(saved_path)

    assert loaded.Name == "My Role"
    assert loaded.Description == "Role description"
    assert len(loaded.Permissions) == 1
    assert loaded.Permissions[0].is_empty()


def test_load_from_name_uses_roles_dir(tmp_path: Path):
    manager = RoleManager(roles_dir=tmp_path)
    role = manager.create_role("Team Role", "Role for team")

    manager.save_to_roles_dir(role, overwrite=True)

    loaded = manager.load_from_name("team-role")

    assert loaded.Name == role.Name
    assert loaded.Description == role.Description


def test_merge_roles_with_filters(tmp_path: Path):
    manager = RoleManager(roles_dir=tmp_path)
    target = manager.create_role("Target", "Target role")
    source = AzureRoleDefinition(
        Name="Source",
        Description="Source role",
        Permissions=[],
    )

    source.Permissions = [
        PermissionDefinition(
            Actions=[
                "Microsoft.Storage/storageAccounts/read",
                "Microsoft.Compute/virtualMachines/read",
            ],
            DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"],
        )
    ]

    updated = manager.merge_roles(
        [source],
        string_filter="Microsoft.Storage/*",
        type_filter=PermissionType.CONTROL,
    )

    assert updated is target
    assert "Microsoft.Storage/storageAccounts/read" in updated.Permissions[0].Actions
    assert "Microsoft.Compute/virtualMachines/read" not in updated.Permissions[0].Actions


def test_remove_permissions(tmp_path: Path):
    manager = RoleManager(roles_dir=tmp_path)
    manager.current_role = manager.create_role("ToRemove", "Remove role")

    manager.current_role.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Storage/storageAccounts/read"],
            DataActions=["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"],
        )
    ]

    updated = manager.remove_permissions(string_filter="Microsoft.Storage/*")

    assert updated.Permissions == []


def test_list_roles_missing_dir(tmp_path: Path):
    missing_dir = tmp_path / "missing"
    manager = RoleManager(roles_dir=missing_dir)

    roles = manager.list_roles(missing_dir)

    assert roles == []


def test_merge_into_role_with_existing_permissions(tmp_path: Path):
    """Test merging into a role that already has permissions (reproduces user bug)."""
    manager = RoleManager(roles_dir=tmp_path)
    
    # Create a role with existing permissions (like Reader)
    target = manager.create_role("Target", "Target role with existing perms")
    target.Permissions = [
        PermissionDefinition(
            Actions=["Microsoft.Authorization/*/read"],
        )
    ]
    manager.current_role = target
    
    # Create source role to merge (like User Access Administrator)
    source = AzureRoleDefinition(
        Name="Source",
        Description="Source role",
        Permissions=[
            PermissionDefinition(
                Actions=[
                    "Microsoft.Authorization/roleAssignments/write",
                    "Microsoft.Authorization/roleAssignments/delete",
                ],
            )
        ],
    )
    
    # Merge source into target
    updated = manager.merge_roles([source])
    
    # Verify BOTH sets of permissions are present
    assert updated is target
    assert len(updated.Permissions) == 1
    assert "Microsoft.Authorization/*/read" in updated.Permissions[0].Actions
    assert "Microsoft.Authorization/roleAssignments/write" in updated.Permissions[0].Actions
    assert "Microsoft.Authorization/roleAssignments/delete" in updated.Permissions[0].Actions
