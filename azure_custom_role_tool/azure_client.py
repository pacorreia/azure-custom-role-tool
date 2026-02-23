"""
Azure SDK integration for managing custom roles.
"""

import os
from typing import List, Optional, Dict
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.mgmt.authorization import AuthorizationManagementClient
from azure.mgmt.authorization.models import RoleDefinition, Permission
from azure.mgmt.subscription import SubscriptionClient

from .role_manager import AzureRoleDefinition, PermissionDefinition


load_dotenv()


class SubscriptionManager:
    """Manages Azure subscriptions."""
    
    def __init__(self):
        """Initialize subscription manager with credentials."""
        try:
            self.credential = AzureCliCredential()
        except Exception:
            self.credential = DefaultAzureCredential()
        
        self.subscription_client = SubscriptionClient(self.credential)
    
    def list_subscriptions(self) -> List[Dict]:
        """
        List all available subscriptions.
        
        Returns:
            List of subscription dictionaries with id, display_name, state
        """
        try:
            subscriptions = self.subscription_client.subscriptions.list()
            return [
                {
                    "subscription_id": sub.subscription_id,
                    "display_name": sub.display_name,
                    "state": sub.state,
                }
                for sub in subscriptions
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list subscriptions: {e}")
    
    def get_subscription_by_id(self, subscription_id: str) -> Optional[Dict]:
        """
        Get a specific subscription by ID.
        
        Args:
            subscription_id: The subscription ID
        
        Returns:
            Subscription dictionary or None if not found
        """
        try:
            subs = [s for s in self.list_subscriptions() if s["subscription_id"] == subscription_id]
            return subs[0] if subs else None
        except Exception as e:
            raise RuntimeError(f"Failed to get subscription: {e}")
    
    def get_subscription_by_name(self, name: str) -> Optional[Dict]:
        """
        Get a subscription by display name (case-insensitive).
        
        Args:
            name: The subscription display name
        
        Returns:
            Subscription dictionary or None if not found
        """
        try:
            subs = [s for s in self.list_subscriptions() if s["display_name"].lower() == name.lower()]
            return subs[0] if subs else None
        except Exception as e:
            raise RuntimeError(f"Failed to get subscription: {e}")


class AzureClient:
    """Azure SDK integration for role management."""

    def __init__(self, subscription_id: Optional[str] = None):
        """
        Initialize Azure client.
        
        Args:
            subscription_id: Azure subscription ID (uses env var if not provided)
        """
        self.subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        if not self.subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID not set in environment or parameters")
        
        # Try Azure CLI credential first (for local development), then DefaultAzureCredential
        try:
            self.credential = AzureCliCredential()
        except Exception:
            self.credential = DefaultAzureCredential()
        
        self.auth_client = AuthorizationManagementClient(
            self.credential,
            self.subscription_id,
        )

    def list_custom_roles(self, scope: str = None) -> List[Dict]:
        """
        List all custom roles in the subscription or scope.
        
        Custom roles are identified by:
        1. type == "CustomRole", OR
        2. Roles with limited assignable_scopes (not including "/" which indicates built-in roles)
        
        Args:
            scope: Azure resource scope (default: subscription)
        
        Returns:
            List of role definitions
        """
        if scope is None:
            scope = f"/subscriptions/{self.subscription_id}"
        
        try:
            roles = self.auth_client.role_definitions.list(scope)
            custom_roles = []
            
            for r in roles:
                # Custom roles are either explicitly marked as CustomRole or
                # have limited assignable scopes (not "/" which is for built-in roles)
                is_custom = (
                    r.type == "CustomRole" or 
                    (r.assignable_scopes and "/" not in r.assignable_scopes)
                )
                if is_custom:
                    custom_roles.append(r)
            
            return [
                {
                    "id": r.id,
                    "name": r.role_name or r.name,  # role_name is the display name, fallback to name if not available
                    "description": r.description,
                    "type": r.type,
                    "permissions": [self._permission_to_dict(p) for p in r.permissions],
                    "assignable_scopes": r.assignable_scopes,
                }
                for r in custom_roles
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list custom roles: {e}")

    def list_all_roles(self, scope: str = None) -> List[Dict]:
        """
        List all roles (built-in and custom) in the subscription or scope.
        
        Args:
            scope: Azure resource scope (default: subscription)
        
        Returns:
            List of role definitions
        """
        if scope is None:
            scope = f"/subscriptions/{self.subscription_id}"
        
        try:
            roles = self.auth_client.role_definitions.list(scope)
            
            return [
                {
                    "id": r.id,
                    "name": r.role_name or r.name,  # role_name is the display name, fallback to name if not available
                    "description": r.description,
                    "type": r.type,
                    "permissions": [self._permission_to_dict(p) for p in r.permissions],
                    "assignable_scopes": r.assignable_scopes,
                }
                for r in roles
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list all roles: {e}")

    def get_role(self, role_id: str, scope: str = None) -> Dict:
        """
        Get a specific role definition.
        
        Args:
            role_id: Role definition ID
            scope: Azure resource scope (default: subscription)
        
        Returns:
            Role definition dictionary
        """
        if scope is None:
            scope = f"/subscriptions/{self.subscription_id}"
        
        try:
            role = self.auth_client.role_definitions.get_by_id(role_id)
            
            return {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "type": role.type,
                "permissions": [self._permission_to_dict(p) for p in role.permissions],
                "assignable_scopes": role.assignable_scopes,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to get role: {e}")

    def create_custom_role(self, role_def: AzureRoleDefinition) -> Dict:
        """
        Create a custom role in Azure.
        
        Args:
            role_def: AzureRoleDefinition instance
        
        Returns:
            Created role definition
        """
        scope = f"/subscriptions/{self.subscription_id}"
        
        try:
            # Convert permissions
            permissions = []
            for perm_block in role_def.Permissions:
                permission = Permission(
                    actions=perm_block.Actions or [],
                    not_actions=perm_block.NotActions or [],
                    data_actions=perm_block.DataActions or [],
                    not_data_actions=perm_block.NotDataActions or [],
                )
                permissions.append(permission)
            
            # Create role definition
            role_definition = RoleDefinition(
                type="CustomRole",
                name=role_def.Name,
                description=role_def.Description,
                permissions=permissions,
                assignable_scopes=role_def.AssignableScopes or [scope],
            )
            
            created = self.auth_client.role_definitions.create_or_update(
                scope=scope,
                role_definition_id=role_def.Id or "",
                role_definition=role_definition,
            )
            
            return {
                "id": created.id,
                "name": created.name,
                "description": created.description,
                "type": created.type,
                "permissions": [self._permission_to_dict(p) for p in created.permissions],
                "assignable_scopes": created.assignable_scopes,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to create custom role: {e}")

    def update_custom_role(self, role_id: str, role_def: AzureRoleDefinition) -> Dict:
        """
        Update an existing custom role.
        
        Args:
            role_id: Existing role ID
            role_def: Updated AzureRoleDefinition instance
        
        Returns:
            Updated role definition
        """
        scope = f"/subscriptions/{self.subscription_id}"
        
        try:
            # Convert permissions
            permissions = []
            for perm_block in role_def.Permissions:
                permission = Permission(
                    actions=perm_block.Actions or [],
                    not_actions=perm_block.NotActions or [],
                    data_actions=perm_block.DataActions or [],
                    not_data_actions=perm_block.NotDataActions or [],
                )
                permissions.append(permission)
            
            # Update role definition
            role_definition = RoleDefinition(
                type="CustomRole",
                name=role_def.Name,
                description=role_def.Description,
                permissions=permissions,
                assignable_scopes=role_def.AssignableScopes or [scope],
            )
            
            updated = self.auth_client.role_definitions.create_or_update(
                scope=scope,
                role_definition_id=role_id,
                role_definition=role_definition,
            )
            
            return {
                "id": updated.id,
                "name": updated.name,
                "description": updated.description,
                "type": updated.type,
                "permissions": [self._permission_to_dict(p) for p in updated.permissions],
                "assignable_scopes": updated.assignable_scopes,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to update custom role: {e}")

    def delete_custom_role(self, role_id: str) -> bool:
        """
        Delete a custom role.
        
        Args:
            role_id: Custom role ID to delete
        
        Returns:
            True if successful
        """
        scope = f"/subscriptions/{self.subscription_id}"
        
        try:
            self.auth_client.role_definitions.delete(scope, role_id)
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete custom role: {e}")

    @staticmethod
    def _permission_to_dict(permission: Permission) -> Dict:
        """Convert Permission object to dictionary."""
        return {
            "actions": permission.actions or [],
            "not_actions": permission.not_actions or [],
            "data_actions": permission.data_actions or [],
            "not_data_actions": permission.not_data_actions or [],
        }
