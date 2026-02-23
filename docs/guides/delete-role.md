# Delete Local Roles

## Overview

The `delete` command allows you to:
- Remove a single local role by name
- Bulk delete multiple roles matching a filter pattern

This is useful for cleaning up old, test, or outdated roles.

## Usage

### Delete Single Role by Name

Delete a role with confirmation prompt:

```
delete MyRole
```

You'll be prompted to confirm:
```
⚠ Delete role 'MyRole'?
Are you sure? [y/N]: y
✓ Deleted role 'MyRole'
```

### Delete Multiple Roles by Filter Pattern

Delete all roles matching a wildcard pattern:

```
delete --filter "*test*"
```

The command shows matching roles and asks for confirmation:
```
Found 3 role(s) matching filter '*test*':
  • test-role-001
  • test-role-002
  • local-test-prod

Delete 3 role(s)? [y/N]: y
✓ Deleted 3 role(s)
```

### Force Delete (Skip Confirmation)

Delete without confirmation using the `--force` flag:

```
delete MyRole --force
```

Or with filter:

```
delete --filter "*test*" --force
```

### Delete from Custom Directory

Specify a custom roles directory:

```
delete MyRole --role-dir /path/to/roles
```

Or with filter:

```
delete --filter "local-*" --role-dir /path/to/roles
```

## Options

| Option | Description |
|--------|-------------|
| `NAME` | Name of a single role to delete (optional if using --filter) |
| `--filter` | Wildcard pattern to match multiple roles (optional if using NAME) |
| `--role-dir` | Custom directory containing roles |
| `--force` | Skip confirmation prompt |

## Filter Patterns

Wildcard patterns use standard shell-style matching:

| Pattern | Matches | Example |
|---------|---------|---------|
| `*` | Any characters | `delete --filter "*"` - delete all roles |
| `prefix*` | Starts with | `delete --filter "test-*"` - all test roles |
| `*suffix` | Ends with | `delete --filter "*-local"` - all local roles |
| `*middle*` | Contains | `delete --filter "*prod*"` - roles with "prod" in name |
| `?` | Single character | `delete --filter "role?"` - role1, role2, etc. |

## Examples

### Example 1: Delete a single role

```
> delete TestRole
⚠ Delete role 'TestRole'?
Are you sure? [y/N]: y
✓ Deleted role 'TestRole'
```

### Example 2: Delete all test roles

```
> delete --filter "*test*"

Found 3 role(s) matching filter '*test*':
  • test-role-001
  • test-role-002
  • integration-test

Delete 3 role(s)? [y/N]: y
✓ Deleted 3 role(s)
```

### Example 3: Force delete all local roles

```
> delete --filter "*local*" --force
✓ Deleted 5 role(s)
```

### Example 4: Delete from alternate directory

```
> delete RoleInBackup --role-dir ./backups --force
✓ Deleted role 'RoleInBackup'
```

## Safety Features

- **Existence check first**: The command verifies role(s) exist before asking for confirmation
- **Clear listing**: Shows all matching roles before asking for deletion
- **Confirmation prompt**: By default, you must confirm deletion with 'y'
- **Error handling**: Shows errors immediately if no roles match or invalid arguments
- **File-based**: Only deletes local JSON files, never affects Azure roles
- **Mutual exclusion**: Cannot use both NAME and --filter in the same command

## Related Commands

- `list` - List available local roles
- `create` - Create a new local role
- `save` - Save current role to file
- `load` - Load a role from file or storage

## Notes

- Only deletes the local JSON file, does not affect Azure roles
- Role names are case-sensitive in filters
- You can use either `RoleName` or `RoleName.json` as the NAME argument
- Filter patterns are case-insensitive
