"""
Azure role definition management and manipulation.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from .permission_filter import PermissionFilter, PermissionType


class PermissionDefinition(BaseModel):
    """Single permission definition block."""

    Actions: List[str] = Field(default_factory=list)
    NotActions: List[str] = Field(default_factory=list)
    DataActions: List[str] = Field(default_factory=list)
    NotDataActions: List[str] = Field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if the permission block is empty."""
        return not any(
            [self.Actions, self.NotActions, self.DataActions, self.NotDataActions]
        )


class AzureRoleDefinition(BaseModel):
    """Azure custom role definition model."""

    Name: str
    IsCustom: bool = True
    Description: str
    Type: str = "CustomRole"
    Permissions: List[PermissionDefinition] = Field(default_factory=list)
    AssignableScopes: List[str] = Field(default_factory=lambda: ["/"])
    Id: Optional[str] = None
    CreatedOn: Optional[str] = None
    UpdatedOn: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return self.model_dump(exclude_unset=True)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class RoleManager:
    """Management of role definitions - loading, saving, and manipulation."""

    def __init__(self, roles_dir: Path = None):
        """
        Initialize RoleManager.

        Args:
            roles_dir: Directory for storing role definitions (default: ./roles)
        """
        self.roles_dir = roles_dir or Path("./roles")
        self.roles_dir.mkdir(parents=True, exist_ok=True)
        self.current_role: Optional[AzureRoleDefinition] = None

    def create_role(self, name: str, description: str) -> AzureRoleDefinition:
        """
        Create a new empty role.

        Args:
            name: Role name
            description: Role description

        Returns:
            New AzureRoleDefinition instance
        """
        self.current_role = AzureRoleDefinition(
            Name=name,
            Description=description,
            Id=f"custom-{uuid.uuid4().hex[:8]}",
            CreatedOn=datetime.now(timezone.utc).isoformat(),
            UpdatedOn=datetime.now(timezone.utc).isoformat(),
            Permissions=[PermissionDefinition()],
        )
        return self.current_role

    def load_from_file(
        self, file_path: Path, set_as_current: bool = True
    ) -> AzureRoleDefinition:
        """
        Load role from JSON file.

        Args:
            file_path: Path to role JSON file
            set_as_current: Whether to set as current role (default: True)

        Returns:
            Loaded AzureRoleDefinition

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not valid JSON
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Role file not found: {file_path}")

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Handle permission blocks
            permissions = []
            for perm in data.get("Permissions", []):
                permissions.append(PermissionDefinition(**perm))

            data["Permissions"] = permissions
            role = AzureRoleDefinition(**data)

            if set_as_current:
                self.current_role = role

            return role
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in role file: {e}")

    def load_from_name(
        self, name: str, role_dir: Path = None, set_as_current: bool = True
    ) -> AzureRoleDefinition:
        """
        Load role by name from roles directory.

        Args:
            name: Role name (or filename without .json)
            role_dir: Directory to search in (default: self.roles_dir)
            set_as_current: Whether to set as current role (default: True)

        Returns:
            Loaded AzureRoleDefinition
        """
        if role_dir is None:
            role_dir = self.roles_dir

        # Try exact name first, then with .json extension
        file_path = (
            role_dir / name if name.endswith(".json") else role_dir / f"{name}.json"
        )
        return self.load_from_file(file_path, set_as_current=set_as_current)

    def save_to_file(
        self, role: AzureRoleDefinition, file_path: Path, overwrite: bool = False
    ) -> Path:
        """
        Save role to JSON file.

        Args:
            role: AzureRoleDefinition to save
            file_path: Path to save to
            overwrite: Allow overwriting existing file

        Returns:
            Path where file was saved

        Raises:
            FileExistsError: If file exists and overwrite is False
        """
        file_path = Path(file_path)

        if file_path.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {file_path}")

        file_path.parent.mkdir(parents=True, exist_ok=True)

        role.UpdatedOn = datetime.now(timezone.utc).isoformat()

        with open(file_path, "w") as f:
            f.write(role.to_json())

        return file_path

    def save_to_roles_dir(
        self, role: AzureRoleDefinition, overwrite: bool = False
    ) -> Path:
        """
        Save role to roles directory.

        Args:
            role: AzureRoleDefinition to save
            overwrite: Allow overwriting existing file

        Returns:
            Path where file was saved
        """
        file_name = role.Name.lower().replace(" ", "-") + ".json"
        return self.save_to_file(role, self.roles_dir / file_name, overwrite=overwrite)

    def merge_roles(
        self,
        source_roles: List[AzureRoleDefinition],
        string_filter: Optional[str] = None,
        type_filter: Optional[PermissionType] = None,
    ) -> AzureRoleDefinition:
        """
        Merge permissions from multiple roles into the current role.

        Args:
            source_roles: List of roles to merge from
            string_filter: Optional string pattern to filter permissions
            type_filter: Optional permission type filter (control/data)

        Returns:
            Updated current role

        Raises:
            ValueError: If no current role is set
        """
        if self.current_role is None:
            raise ValueError(
                "No current role set. Call create_role() or load_from_file() first."
            )

        # Collect all actions from source roles
        all_actions = {
            "actions": [],
            "not_actions": [],
            "data_actions": [],
            "not_data_actions": [],
        }

        # First, extract existing permissions from current role
        if (
            self.current_role.Permissions
            and not self.current_role.Permissions[0].is_empty()
        ):
            existing = PermissionFilter.extract_actions(self.current_role.Permissions)
            for key in all_actions:
                all_actions[key].extend(existing[key])

        # Then collect from source roles
        for source_role in source_roles:
            extracted = PermissionFilter.extract_actions(source_role.Permissions)

            # Apply filters
            for key in all_actions:
                actions = sorted(list(extracted[key]))
                filtered = PermissionFilter.filter_permissions(
                    actions,
                    string_filter=string_filter,
                    type_filter=type_filter,
                )
                all_actions[key].extend(filtered)

        # Deduplicate and sort
        for key in all_actions:
            all_actions[key] = sorted(list(set(all_actions[key])))

        # Create new permission block with all merged actions
        self.current_role.Permissions = [
            PermissionDefinition(
                Actions=all_actions["actions"],
                NotActions=all_actions["not_actions"],
                DataActions=all_actions["data_actions"],
                NotDataActions=all_actions["not_data_actions"],
            )
        ]

        self.current_role.UpdatedOn = datetime.now(timezone.utc).isoformat()
        return self.current_role

    def remove_permissions(
        self,
        string_filter: Optional[str] = None,
        type_filter: Optional[PermissionType] = None,
    ) -> AzureRoleDefinition:
        """
        Remove permissions from the current role based on filters.

        Args:
            string_filter: Optional string pattern to match permissions to remove
            type_filter: Optional permission type to remove (control/data)

        Returns:
            Updated current role

        Raises:
            ValueError: If no current role is set
        """
        if self.current_role is None:
            raise ValueError("No current role set.")

        extracted = PermissionFilter.extract_actions(self.current_role.Permissions)

        # Apply filters to get permissions to REMOVE
        for key in ["actions", "not_actions", "data_actions", "not_data_actions"]:
            actions = sorted(list(extracted[key]))
            to_remove = PermissionFilter.filter_permissions(
                actions,
                string_filter=string_filter,
                type_filter=type_filter,
            )

            # Remove from set
            remaining = [a for a in actions if a not in to_remove]
            extracted[key] = remaining

        # Update role
        if any(extracted.values()):
            new_actions = {
                "actions": extracted["actions"],
                "not_actions": extracted["not_actions"],
                "data_actions": extracted["data_actions"],
                "not_data_actions": extracted["not_data_actions"],
            }

            self.current_role.Permissions = [
                PermissionDefinition(
                    Actions=new_actions["actions"],
                    NotActions=new_actions["not_actions"],
                    DataActions=new_actions["data_actions"],
                    NotDataActions=new_actions["not_data_actions"],
                )
            ]
        else:
            self.current_role.Permissions = []

        self.current_role.UpdatedOn = datetime.now(timezone.utc).isoformat()
        return self.current_role

    def list_roles(self, role_dir: Path = None) -> List[str]:
        """
        List all available roles in a directory.

        Args:
            role_dir: Directory to search in (default: self.roles_dir)

        Returns:
            List of role filenames
        """
        if role_dir is None:
            role_dir = self.roles_dir

        if not role_dir.exists():
            return []

        return sorted([f.stem for f in role_dir.glob("*.json")])

    def delete_role(self, name: str, role_dir: Path = None) -> bool:
        """
        Delete a role file from the directory.

        Args:
            name: Role name (or filename without .json)
            role_dir: Directory to search in (default: self.roles_dir)

        Returns:
            True if role was deleted, False if not found

        Raises:
            ValueError: If role_dir doesn't exist
        """
        if role_dir is None:
            role_dir = self.roles_dir

        if not role_dir.exists():
            raise ValueError(f"Roles directory does not exist: {role_dir}")

        # Try exact name first, then with .json extension
        file_path = (
            role_dir / name if name.endswith(".json") else role_dir / f"{name}.json"
        )

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    def export_role(self, role: AzureRoleDefinition) -> Dict:
        """
        Export role to dictionary (Azure format).

        Args:
            role: AzureRoleDefinition to export

        Returns:
            Dictionary in Azure role format
        """
        return role.to_dict()
