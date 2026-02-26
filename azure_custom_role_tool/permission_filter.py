"""
Permission filtering and search utilities for Azure role permissions.
"""

import re
from typing import List, Dict, Set, Optional
from enum import Enum


class PermissionType(Enum):
    """Classification of Azure permission types."""

    CONTROL = "control"  # Management plane operations
    DATA = "data"  # Data plane operations


class PermissionFilter:
    """Utilities for filtering and searching role permissions."""

    WILDCARD_ANY = "%"
    WILDCARD_SINGLE = "?"

    @staticmethod
    def is_data_plane(action: str) -> bool:
        """
        Determine if an action is a data plane permission.

        Data plane actions typically contain specific resource identifiers
        and data operations (read, write, delete data).

        Args:
            action: Permission action string (e.g., "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read")

        Returns:
            True if action is a data plane permission
        """
        # Common data plane patterns
        data_plane_patterns = [
            r"blobServices/containers/blobs",
            r"fileServices/shares/files",
            r"tableServices/tables",
            r"queueServices/queues",
            r"databases/collections",
            r"/data/",
            r"cosmosdb.*documents",
            r"sql.*query",
            r"managedIdentities.*clients",
        ]

        for pattern in data_plane_patterns:
            if re.search(pattern, action, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def is_control_plane(action: str) -> bool:
        """
        Determine if an action is a control plane permission.

        Args:
            action: Permission action string

        Returns:
            True if action is a control plane permission (not data plane)
        """
        return not PermissionFilter.is_data_plane(action)

    @staticmethod
    def classify_permissions(actions: List[str]) -> Dict[str, List[str]]:
        """
        Classify a list of permissions into control and data plane.

        Args:
            actions: List of permission action strings

        Returns:
            Dictionary with 'control' and 'data' keys containing classified permissions
        """
        classified = {"control": [], "data": []}

        for action in actions:
            if PermissionFilter.is_data_plane(action):
                classified["data"].append(action)
            else:
                classified["control"].append(action)

        return classified

    @staticmethod
    def filter_by_string(actions: List[str], pattern: str) -> List[str]:
        """
        Filter permissions by string matching.

        Args:
            actions: List of permission action strings
            pattern: Search pattern.
                - Use '%' for multi-character wildcard
                - Use '?' for single-character wildcard
                - '*' is treated as a literal character

        Returns:
            Filtered list of matching permissions
        """
        has_wildcards = (
            PermissionFilter.WILDCARD_ANY in pattern
            or PermissionFilter.WILDCARD_SINGLE in pattern
        )

        # No wildcard token: substring match (case-insensitive), with '*' treated literally.
        if not has_wildcards:
            pattern_lower = pattern.lower()
            return [action for action in actions if pattern_lower in action.lower()]

        # Wildcard pattern: convert to anchored regex
        regex_parts = []
        for char in pattern:
            if char == PermissionFilter.WILDCARD_ANY:
                regex_parts.append(".*")
            elif char == PermissionFilter.WILDCARD_SINGLE:
                regex_parts.append(".")
            else:
                regex_parts.append(re.escape(char))

        regex_pattern = "^" + "".join(regex_parts) + "$"
        compiled_pattern = re.compile(regex_pattern, re.IGNORECASE)
        return [action for action in actions if compiled_pattern.match(action)]

    @staticmethod
    def filter_by_type(
        actions: List[str], permission_type: PermissionType
    ) -> List[str]:
        """
        Filter permissions by type (control or data plane).

        Args:
            actions: List of permission action strings
            permission_type: PermissionType enum value

        Returns:
            Filtered list of permissions matching the type
        """
        if permission_type == PermissionType.CONTROL:
            return [a for a in actions if PermissionFilter.is_control_plane(a)]
        else:  # DATA
            return [a for a in actions if PermissionFilter.is_data_plane(a)]

    @staticmethod
    def filter_permissions(
        actions: List[str],
        string_filter: Optional[str] = None,
        type_filter: Optional[PermissionType] = None,
    ) -> List[str]:
        """
        Apply multiple filters to a list of permissions.

        Args:
            actions: List of permission action strings
            string_filter: Optional string pattern filter
            type_filter: Optional PermissionType filter

        Returns:
            Filtered list of permissions
        """
        result = actions.copy()

        if string_filter:
            result = PermissionFilter.filter_by_string(result, string_filter)

        if type_filter:
            result = PermissionFilter.filter_by_type(result, type_filter)

        return result

    @staticmethod
    def extract_actions(permissions: List[Dict]) -> Dict[str, Set[str]]:
        """
        Extract all actions from a permission block list.

        Args:
            permissions: List of permission dictionaries (Actions, NotActions, DataActions, NotDataActions)

        Returns:
            Dictionary with 'actions', 'not_actions', 'data_actions', 'not_data_actions' keys
        """
        extracted = {
            "actions": set(),
            "not_actions": set(),
            "data_actions": set(),
            "not_data_actions": set(),
        }

        for perm_block in permissions:
            if hasattr(perm_block, "model_dump"):
                block = perm_block.model_dump()
            elif hasattr(perm_block, "dict"):
                block = perm_block.dict()
            else:
                block = perm_block

            extracted["actions"].update(block.get("Actions", []))
            extracted["not_actions"].update(block.get("NotActions", []))
            extracted["data_actions"].update(block.get("DataActions", []))
            extracted["not_data_actions"].update(block.get("NotDataActions", []))

        return extracted

    @staticmethod
    def merge_permission_blocks(
        existing_blocks: List[Dict], new_actions: Dict[str, List[str]]
    ) -> List[Dict]:
        """
        Merge new permissions into existing permission blocks.

        Args:
            existing_blocks: Existing list of permission dictionaries
            new_actions: Dictionary with 'actions', 'not_actions', 'data_actions', 'not_data_actions'

        Returns:
            Updated permission blocks list
        """
        if not existing_blocks:
            existing_blocks = [{}]

        # Work with the first block (typically there's only one)
        block = existing_blocks[0]

        block["Actions"] = list(
            set(block.get("Actions", []) + (new_actions.get("actions", [])))
        )
        block["NotActions"] = list(
            set(block.get("NotActions", []) + (new_actions.get("not_actions", [])))
        )
        block["DataActions"] = list(
            set(block.get("DataActions", []) + (new_actions.get("data_actions", [])))
        )
        block["NotDataActions"] = list(
            set(
                block.get("NotDataActions", [])
                + (new_actions.get("not_data_actions", []))
            )
        )

        # Remove empty fields
        for key in ["Actions", "NotActions", "DataActions", "NotDataActions"]:
            if not block[key]:
                del block[key]

        return existing_blocks if existing_blocks[0] else existing_blocks
