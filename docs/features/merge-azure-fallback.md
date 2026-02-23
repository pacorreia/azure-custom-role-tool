# Merge with Azure Fallback

## Overview
The `merge` command now automatically fetches roles from Azure if they are not found in local storage. This creates a seamless workflow for combining permissions from local and Azure roles without requiring explicit `load-azure` calls for each role.

## Changes Made

### 1. New Helper Functions (cli.py)

#### `_convert_azure_role_to_local(azure_role: dict) -> AzureRoleDefinition`
- Converts Azure API response format to local `AzureRoleDefinition` format
- Handles permission block mapping (actions, not_actions, data_actions, not_data_actions)
- Properly determines if a role is custom or built-in based on assignable_scopes
- **Reused by**: Both `load_azure` and `merge` commands for consistency

#### `_load_role_from_azure_by_name(name: str, subscription_id: Optional[str]) -> Optional[AzureRoleDefinition]`
- Searches Azure for a role by name (case-insensitive)
- Returns the converted `AzureRoleDefinition` or None if not found
- Gracefully handles errors without throwing exceptions
- **Used by**: `merge` command as fallback when local role is not found

### 2. Updated `merge` Command

**New behavior:**
1. Tries to load each role from local storage first
2. If not found locally, searches Azure for the role
3. Reports which roles were found locally vs. fetched from Azure
4. Fails only if NO roles can be found (local or Azure)

**Output changes:**
- When loading from Azure: `ℹ Loaded 'RoleName' from Azure`
- When roles are not found: `⚠ Roles not found (local or Azure): RoleName1, RoleName2`
- Original behavior: `⚠ Role not found: RoleName`

**Example usage:**
```
> merge --roles "Storage Blob Data Reader"
ℹ Loaded 'Storage Blob Data Reader' from Azure
✓ Merged permissions from 1 role(s)
```

Mixed local and Azure:
```
> merge --roles "LocalRole, Reader, Storage Blob Data Reader"
ℹ Loaded 'Reader' from Azure
ℹ Loaded 'Storage Blob Data Reader' from Azure
✓ Merged permissions from 3 role(s)
```

### 3. Code Reuse

Both `load_azure` and `merge` now use the same conversion logic:
- `_convert_azure_role_to_local()` - Ensures consistent format conversion
- No duplication of Azure role handling logic
- Easier maintenance if Azure response format changes

## Benefits

1. **Seamless Workflow**: Users can merge roles from Azure without pre-loading them locally
2. **Flexibility**: Supports mixing local and Azure roles in a single merge command
3. **Better UX**: Clear messaging about which roles came from where
4. **Resilience**: Gracefully handles roles that don't exist anywhere (local or Azure)

## Test Coverage

Added 3 new tests to verify the feature:
1. `test_merge_with_azure_fallback` - Basic Azure fallback functionality
2. `test_merge_mixed_local_and_azure` - Mixed local and Azure roles
3. `test_merge_azure_role_not_found` - Error handling when no roles found

Updated 1 existing test:
- `test_merge_with_missing_role_warning` - Changed expected message to reflect new behavior

**Test Results**: 95 tests passing (was 92)

## Example Workflow

```bash
# Set subscription
use-subscription "Development – OI – Software"

# Create a new role
create --name "MyCustomRole" --description "Custom storage role"

# Merge permissions from Azure roles without loading them first
merge --roles "Storage Blob Data Reader, Storage Queue Data Contributor"

# View the merged permissions
show
```

## Requirements Met

✅ Merge automatically fetches roles from Azure if not found locally
✅ Clear messaging about which roles came from where
✅ Proper error handling when roles aren't found
✅ Backward compatible - local roles still work as before
✅ Reuses existing filter logic for consistency
✅ All tests passing with no regressions
