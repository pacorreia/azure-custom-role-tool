from azure_custom_role_tool.permission_filter import PermissionFilter, PermissionType


def test_filter_by_string_wildcard():
    actions = [
        "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Compute/virtualMachines/read",
        "Microsoft.Storage/storageAccounts/listKeys/action",
    ]

    filtered = PermissionFilter.filter_by_string(actions, "Microsoft.Storage/*")

    assert "Microsoft.Storage/storageAccounts/read" in filtered
    assert "Microsoft.Storage/storageAccounts/listKeys/action" in filtered
    assert "Microsoft.Compute/virtualMachines/read" not in filtered


def test_filter_by_type_data_plane():
    actions = [
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
        "Microsoft.Compute/virtualMachines/read",
    ]

    data_actions = PermissionFilter.filter_by_type(actions, PermissionType.DATA)

    assert "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read" in data_actions
    assert "Microsoft.Compute/virtualMachines/read" not in data_actions


def test_classify_permissions_and_control_plane():
    actions = [
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
        "Microsoft.Compute/virtualMachines/read",
    ]

    classified = PermissionFilter.classify_permissions(actions)

    assert "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read" in classified["data"]
    assert "Microsoft.Compute/virtualMachines/read" in classified["control"]
    assert PermissionFilter.is_control_plane("Microsoft.Compute/virtualMachines/read") is True


def test_filter_by_string_invalid_regex():
    actions = [
        "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Compute/virtualMachines/read",
    ]

    # Invalid regex falls back to substring matching
    filtered = PermissionFilter.filter_by_string(actions, "[")

    assert filtered == []


def test_filter_permissions_combined():
    actions = [
        "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
    ]

    filtered = PermissionFilter.filter_permissions(
        actions,
        string_filter="Microsoft.Storage/*",
        type_filter=PermissionType.DATA,
    )

    assert filtered == ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"]
