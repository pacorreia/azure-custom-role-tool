"""
Azure Custom Role Tool

A powerful CLI tool for platform engineers to create, update, and manage Azure custom roles.
"""

__version__ = "1.0.0"
__author__ = "OI Technologies Platform Engineering"
__license__ = "Internal"

from .role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition
from .permission_filter import PermissionFilter, PermissionType
from .azure_client import AzureClient

__all__ = [
    "RoleManager",
    "AzureRoleDefinition",
    "PermissionDefinition",
    "PermissionFilter",
    "PermissionType",
    "AzureClient",
]
