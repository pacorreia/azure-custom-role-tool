from types import SimpleNamespace

import pytest

from azure_custom_role_tool import azure_client
from azure_custom_role_tool.role_manager import (
    AzureRoleDefinition,
    PermissionDefinition,
)


class DummyPermission:
    def __init__(
        self, actions=None, not_actions=None, data_actions=None, not_data_actions=None
    ):
        self.actions = actions or []
        self.not_actions = not_actions or []
        self.data_actions = data_actions or []
        self.not_data_actions = not_data_actions or []


class DummyRoleDefinitionModel:
    def __init__(self, type, name, description, permissions, assignable_scopes):
        self.type = type
        self.name = name
        self.description = description
        self.permissions = permissions
        self.assignable_scopes = assignable_scopes


class DummyRole:
    def __init__(
        self,
        role_id="role-id",
        name="Role",
        description="Desc",
        type="CustomRole",
        permissions=None,
        assignable_scopes=None,
        role_name=None,
    ):
        self.id = role_id
        self.name = name
        self.role_name = role_name or name  # role_name is the display name
        self.description = description
        self.type = type
        self.permissions = permissions or []
        self.assignable_scopes = assignable_scopes or ["/subscriptions/test-sub"]


class DummyRoleDefinitions:
    def __init__(self):
        self.deleted = None
        self.created = None

    def list(self, scope):
        return [
            DummyRole(type="CustomRole", assignable_scopes=["/subscriptions/test-sub"]),
            DummyRole(type="BuiltInRole", assignable_scopes=["/"]),
        ]

    def get_by_id(self, role_id):
        return DummyRole(role_id=role_id)

    def create_or_update(self, scope, role_definition_id, role_definition):
        self.created = (scope, role_definition_id, role_definition)
        return DummyRole(
            role_id=role_definition_id or "new-id",
            name=role_definition.name,
            description=role_definition.description,
            type=role_definition.type,
            permissions=role_definition.permissions,
            assignable_scopes=role_definition.assignable_scopes,
        )

    def delete(self, scope, role_id):
        self.deleted = (scope, role_id)


class DummyAuthClient:
    def __init__(self, *args, **kwargs):
        self.role_definitions = DummyRoleDefinitions()


def configure_client(monkeypatch):
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "test-sub")
    monkeypatch.setattr(azure_client, "AuthorizationManagementClient", DummyAuthClient)
    monkeypatch.setattr(azure_client, "Permission", DummyPermission)
    monkeypatch.setattr(azure_client, "RoleDefinition", DummyRoleDefinitionModel)


def test_init_requires_subscription(monkeypatch):
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    with pytest.raises(ValueError):
        azure_client.AzureClient()


def test_list_custom_roles(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")
    roles = client.list_custom_roles()

    assert len(roles) == 1
    assert roles[0]["type"] == "CustomRole"


def test_get_role(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")

    role = client.get_role("role-id")

    assert role["id"] == "role-id"
    assert role["name"] == "Role"


def test_create_and_update_custom_role(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")

    role_def = AzureRoleDefinition(
        Name="MyRole",
        Description="Role desc",
        Permissions=[
            PermissionDefinition(
                Actions=["Microsoft.Storage/storageAccounts/read"],
                DataActions=[
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
                ],
            )
        ],
        AssignableScopes=["/subscriptions/test-sub"],
        Id="custom-id",
    )

    created = client.create_custom_role(role_def)
    updated = client.update_custom_role("custom-id", role_def)

    assert created["name"] == "MyRole"
    assert updated["id"] == "custom-id"


def test_delete_custom_role(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")

    assert client.delete_custom_role("role-id") is True


def test_permission_to_dict_defaults():
    permission = DummyPermission()
    result = azure_client.AzureClient._permission_to_dict(permission)

    assert result == {
        "actions": [],
        "not_actions": [],
        "data_actions": [],
        "not_data_actions": [],
    }


def test_list_custom_roles_failure(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")

    def raise_error(_scope):
        raise RuntimeError("boom")

    client.auth_client.role_definitions.list = raise_error

    with pytest.raises(RuntimeError, match="Failed to list custom roles"):
        client.list_custom_roles()


def test_get_role_failure(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")

    def raise_error(_role_id):
        raise RuntimeError("boom")

    client.auth_client.role_definitions.get_by_id = raise_error

    with pytest.raises(RuntimeError, match="Failed to get role"):
        client.get_role("role-id")


def test_delete_custom_role_failure(monkeypatch):
    configure_client(monkeypatch)
    client = azure_client.AzureClient(subscription_id="test-sub")

    def raise_error(_scope, _role_id):
        raise RuntimeError("boom")

    client.auth_client.role_definitions.delete = raise_error

    with pytest.raises(RuntimeError, match="Failed to delete custom role"):
        client.delete_custom_role("role-id")
