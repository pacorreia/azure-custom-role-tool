# Unified Load Feature

## Overview
The `load` command now handles all role loading scenarios:
1. **Direct file path** - Load from a specific file
2. **Local storage** - Load from local roles directory
3. **Azure fallback** - Automatically fetch from Azure if not found locally

This eliminates the need for separate `load` and `load-azure` commands for most workflows. The `load-azure` command is retained for backward compatibility.

## Changes Made

### Updated `load` Command
**Location**: `cli.py` lines 57-100

**New behavior:**
- Accepts role name or file path
- Tries all three sources in order:
  1. Direct file path (if exists)
  2. Local role by name
  3. Azure role by name (requires subscription)
- Sets loaded role as current role

**New options:**
- `--name` (required): Role name (local or Azure)
- `--role-dir` (optional): Custom role directory for local search
- `--subscription-id` (optional): Azure subscription ID for fallback

**Output messages:**
- `✓ Loaded role from file: RoleName`
- `✓ Loaded role from local storage: RoleName`
- `✓ Loaded role from Azure: RoleName`
- `✗ Role not found (local or Azure): RoleName`

### Backward Compatible `load-azure`
**Location**: `cli.py` lines 173-206

- Maintained for backward compatibility
- Explicitly loads from Azure only
- Same options and behavior as before
- Docstring indicates it's for backward compatibility

## Example Workflows

### Simple Load (One Command)
```bash
> load --name "Reader"
✓ Loaded role from Azure: Reader
```

### Load with Priority
```bash
# Loads from local if found, otherwise tries Azure
> load --name "MyCustomRole"
```

### Load from Specific Path
```bash
> load --name "/path/to/role.json"
✓ Loaded role from file: MyRole
```

### Mixed Workflow
```bash
> use-subscription "Development – OI – Software"
> load --name "Reader"
✓ Loaded role from Azure: Reader

> merge --roles "Storage Blob Data Reader"
ℹ Loaded 'Storage Blob Data Reader' from Azure
✓ Merged permissions from 1 role(s)
```

## Technical Details

### Helper Functions
Both `load` and `load-azure` use the same helper functions:

**`_convert_azure_role_to_local(azure_role: dict) -> AzureRoleDefinition`**
- Converts Azure API response to local format
- Handles permission block mapping
- Determines custom vs. built-in role status

**`_load_role_from_azure_by_name(name: str, subscription_id: Optional[str]) -> Optional[AzureRoleDefinition]`**
- Searches Azure for role by name (case-insensitive)
- Returns converted role or None
- Gracefully handles errors

### Priority Chain
```
1. File path → role_manager.load_from_file()
                    ↓
2. Local name → role_manager.load_from_name()
                    ↓
3. Azure name → _load_role_from_azure_by_name()
                    ↓
            Role not found (error)
```

## Test Coverage

**New tests added (5):**
1. `test_load_with_azure_fallback()` - Load from Azure when not local
2. `test_load_with_local_takes_priority()` - Local takes precedence
3. `test_load_azure_fallback_not_found()` - Error when nowhere found
4. `test_load_azure_command()` - Backward compatibility
5. `test_load_azure_command_not_found()` - Backward compatibility

**Test Results**: 98 tests passing (was 95)

## Benefits

1. **Simplified API**: One command for all loading scenarios
2. **Better UX**: Users don't need to remember separate commands
3. **Smart Fallback**: Automatically searches Azure if needed
4. **Backward Compatible**: Old `load-azure` still works
5. **Reusable Logic**: Both commands use the same conversion logic

## Migration Guide

### For Existing Scripts
| Old Command | New Equivalent |
|------------|----------------|
| `load-azure --name "Reader"` | `load --name "Reader"` |
| `load-azure --name "Reader" --subscription-id "sub-123"` | `load --name "Reader" --subscription-id "sub-123"` |
| `load --name "role.json"` | `load --name "role.json"` (same) |
| `load --name "MyRole"` | `load --name "MyRole"` (tries Azure automatically) |

The old `load-azure` command still works but isn't needed anymore.

## Help Text
Updated the `help` command to show:
```
load           - Load a role (local, file, or Azure)
```

This accurately describes the new unified behavior.
