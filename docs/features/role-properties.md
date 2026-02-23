# Role Property Modification Feature

## Overview
Users can now modify role properties locally using dedicated commands for:
- **Name** - Change role name
- **Description** - Change role description  
- **Assignable Scopes** - Change the scopes where the role can be assigned

## New Commands

### `set-name --name <new-name>`
Changes the current role's name.

**Example:**
```bash
> create --name "OriginalName" --description "Test role"
> set-name --name "UpdatedName"
✓ Role name changed: OriginalName → UpdatedName
```

### `set-description --description <new-description>`
Changes the current role's description.

**Example:**
```bash
> set-description --description "Updated role description"
✓ Description changed:
  Old: Original description
  New: Updated role description
```

### `set-scopes --scopes <scope1>, <scope2>, ...`
Changes the assignable scopes for the role. Scopes are comma-separated and automatically trimmed of whitespace.

**Example:**
```bash
> set-scopes --scopes "/, /subscriptions/sub-123"
✓ Assignable scopes changed:
  Old: /
  New: /, /subscriptions/sub-123
```

**With whitespace:**
```bash
> set-scopes --scopes " / , /subscriptions/sub-123 , /subscriptions/sub-456 "
✓ Assignable scopes changed:
  Old: /
  New: /, /subscriptions/sub-123, /subscriptions/sub-456
```

## Example Workflow

Complete role customization workflow:

```bash
# 1. Load a role from Azure
> load --name "Contributor"
✓ Loaded role from Azure: Contributor

# 2. Customize the role for your needs
> set-name --name "Custom Contributor"
✓ Role name changed: Contributor → Custom Contributor

> set-description --description "Custom role based on Contributor for our team"
✓ Description changed:
  Old: Manage all resources
  New: Custom role based on Contributor for our team

> set-scopes --scopes "/subscriptions/main-subscription"
✓ Assignable scopes changed:
  Old: /
  New: /subscriptions/main-subscription

# 3. Add/remove specific permissions
> merge --roles "Storage Blob Data Reader"
ℹ Loaded 'Storage Blob Data Reader' from Azure
✓ Merged permissions from 1 role(s)

# 4. View the customized role
> view
[Shows updated role with all customizations]

# 5. Save the role locally
> save --name "custom-contributor" --overwrite
✓ Saved role to: roles/custom-contributor.json

# 6. Publish to Azure
> publish
✓ Published role to Azure
```

## Error Handling

All property modification commands check for a loaded role before allowing modifications:

```bash
> set-name --name "MyRole"
✗ No current role. Create or load a role first.
```

## Test Coverage

Added 10 comprehensive tests in `tests/test_role_properties.py`:

1. **test_set_name_command** - Verify name change
2. **test_set_name_no_role** - Error when no role loaded
3. **test_set_description_command** - Verify description change
4. **test_set_description_no_role** - Error when no role loaded  
5. **test_set_scopes_command** - Verify multiple scopes
6. **test_set_scopes_single** - Verify single scope
7. **test_set_scopes_no_role** - Error when no role loaded
8. **test_set_multiple_properties** - Sequential modifications stay in effect
9. **test_set_scopes_with_whitespace** - Scopes trimmed properly
10. **test_properties_persist_after_modification** - Changes visible in view command

**Test Results**: 108 tests passing (was 98)

## Help Menu
The help system has been updated to include the new commands:

```
set-name       - Change role name
set-description - Change role description
set-scopes     - Change role assignable scopes
```

## Technical Details

### Implementation
- Commands directly modify `role_manager.current_role` properties
- Properties persist in memory until role is saved
- All commands follow standard error handling patterns
- Clear output shows old vs. new values for verification

### Properties Modified
- **Name**: `AzureRoleDefinition.Name`
- **Description**: `AzureRoleDefinition.Description`
- **AssignableScopes**: `AzureRoleDefinition.AssignableScopes` (list of strings)

### Scope Parsing
The `--scopes` option:
- Accepts comma-separated values
- Automatically trims whitespace from each scope
- Converts to proper list format for Azure API submission

## Integration with Existing Features

These commands integrate seamlessly with:
- **load** - Load a role, then modify properties
- **merge** - Merge permissions then adjust scopes/metadata
- **save** - Save modified role locally
- **publish** - Publish customized role to Azure
- **view** - View all modifications in current role display

## Benefits

1. **Local Customization** - Modify Azure roles before publishing
2. **Template Adaptation** - Use standard roles as templates, customize for specific needs
3. **Clear Feedback** - Each command shows old→new values for verification
4. **Non-destructive** - Changes only affect current role in memory until saved
5. **Professional Workflow** - Complete role lifecycle from Azure to custom published role
