# Azure Custom Role Designer - Feature Reference

## 📋 Complete Feature Set

This document provides a comprehensive reference for all capabilities of the Azure Custom Role Designer tool.

## Core Features

### ✅ 1. Create Roles from Scratch

Create a brand new custom role with no initial permissions:

```bash
azure-custom-role-tool create --name "MyRole" --description "My custom role"
```

**Features:**
- Auto-generate unique role IDs
- Set timestamps automatically
- Initialize empty permission blocks
- Ready for adding permissions

### ✅ 2. Cherry-pick Permissions from Roles

Selectively choose specific permissions from existing roles:

```bash
# Merge single permission exactly
azure-custom-role-tool merge --roles "source-role" --filter "Microsoft.Storage/storageAccounts/read"

# Merge specific action patterns
azure-custom-role-tool merge --roles "source-role" --filter "Microsoft.Web*"
```

**Features:**
- Wildcard pattern matching
- Case-insensitive search
- Regex support (if needed)
- Deduplication across merges

### ✅ 3. Merge Permissions from Multiple Roles

Combine permissions from multiple source roles simultaneously:

```bash
# Simple merge
azure-custom-role-tool merge --roles "role1,role2,role3"

# With filtering
azure-custom-role-tool merge --roles "junior-dev,reader,viewer" --filter "*read*"

# Multiple filters
azure-custom-role-tool merge --roles "senior-dev" --filter "Storage*" --filter-type data
```

**Features:**
- Combine multiple roles at once
- Automatic deduplication
- Preserve action/notaction/dataaction/notdataaction structure
- Smart list management

### ✅ 4. Filter by String Pattern

Search and filter permissions by text patterns:

```bash
# Simple wildcard
azure-custom-role-tool merge --roles "senior-dev" --filter "Storage*"

# Partial match
azure-custom-role-tool merge --roles "senior-dev" --filter "*blobs*"

# Complex pattern
azure-custom-role-tool merge --roles "senior-dev" --filter "Microsoft.Storage/storageAccounts/blobServices/*"
```

**Filter Syntax:**
- `*` for wildcards: `Microsoft.Storage*` matches all Storage services
- Case-insensitive matching
- Supports partial token matching: `*/read` matches any read operations
- Regex patterns (optional advanced usage)

**Examples:**
- `Microsoft.Storage*` - All Storage service operations
- `*read` - All read operations
- `Microsoft.*/*/write` - Write operations on any service
- `*Blob*/` - Blob-related operations

### ✅ 5. Filter by Permission Type

Separate and manage control vs. data plane permissions:

```bash
# Control plane only (management operations)
azure-custom-role-tool merge --roles "senior-dev" --filter-type control

# Data plane only (data operations)
azure-custom-role-tool merge --roles "senior-dev" --filter-type data

# Combined with string filter
azure-custom-role-tool merge --roles "senior-dev" --filter "Storage*" --filter-type data
```

**Permission Types:**

**Control Plane (Management):**
- Resource creation/deletion
- Configuration changes
- Access management
- Example: `Microsoft.Compute/virtualMachines/start/action`

**Data Plane (Data Operations):**
- Read/write data
- Query databases
- Blob access
- Example: `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`

### ✅ 6. Remove Permissions

Filter and remove specific permissions from the current role:

```bash
# Remove by pattern
azure-custom-role-tool remove --filter "*delete*"

# Remove by type
azure-custom-role-tool remove --filter-type data

# Combined filtering
azure-custom-role-tool remove --filter "Microsoft.Storage*" --filter-type control

# Remove dangerous operations
azure-custom-role-tool remove --filter "*deallocate*"
azure-custom-role-tool remove --filter "*delete*"
```

**Features:**
- Same filtering syntax as merge
- Safe removal (won't affect unmatched permissions)
- Can be called multiple times

### ✅ 7. Load and Save Local Roles

Persist role definitions locally for version control:

```bash
# Load from default directory
azure-custom-role-tool load --name "my-role"

# Load from custom directory
azure-custom-role-tool load --name "my-role" --role-dir ./archive

# Save to default directory
azure-custom-role-tool save --name "my-role"

# Save to custom location
azure-custom-role-tool save --name "my-role" --output ./roles/my-role.json

# Overwrite existing
azure-custom-role-tool save --name "my-role" --overwrite
```

**Features:**
- JSON-based storage
- Auto-generated filenames
- Preserves metadata (timestamps, IDs)
- Overwrite protection

### ✅ 8. Publish to Azure

Deploy created/modified roles directly to Azure:

```bash
# Publish simple
azure-custom-role-tool publish --name "my-role"

# Publish with specific subscription
azure-custom-role-tool publish --name "my-role" --subscription-id "xxxxx-xxxxx"
```

**Features:**
- Direct Azure deployment
- Automatic subscription detection
- Role versioning support
- Error handling and validation

### ✅ 9. List and View Roles

Browse and inspect local and Azure roles:

```bash
# List all local roles
azure-custom-role-tool list

# View specific role details
azure-custom-role-tool list --name "my-role"

# List Azure roles
azure-custom-role-tool list-azure

# View current role in detail
azure-custom-role-tool view

# Show all permissions (no truncation)
azure-custom-role-tool view --all
```

**Features:**
- Formatted table output
- Permission counts
- Truncation for readability
- Full details on demand

### ✅ 10. Interactive Mode

Full-featured interactive CLI menu:

```bash
azure-custom-role-tool
```

**Features:**
- Menu-driven interface
- Command history
- Real-time role status display
- Help system

## Advanced Usage Patterns

### Pattern 1: Incremental Permission Building

```bash
# Start with empty role
azure-custom-role-tool create --name "BuildingRole" --description "Incrementally built"

# Add read-only permissions
azure-custom-role-tool merge --roles "reader"

# Add specific data access
azure-custom-role-tool merge --roles "senior-dev" --filter "*Blob*" --filter-type data

# Add storage management (but not delete)
azure-custom-role-tool merge --roles "storage-admin" --filter "Microsoft.Storage*"
azure-custom-role-tool remove --filter "*delete*"
```

### Pattern 2: Role Specialization from Broad Base

```bash
# Start with contributor-like permissions
azure-custom-role-tool create --name "WebDeveloper" --description "Web developer permissions"
azure-custom-role-tool merge --roles "contributor"

# Remove unnecessary resources
azure-custom-role-tool remove --filter "Microsoft.Compute*"
azure-custom-role-tool remove --filter "Microsoft.Network*"
azure-custom-role-tool remove --filter "Microsoft.Sql*"

# Remove dangerous operations
azure-custom-role-tool remove --filter "*delete*"
```

### Pattern 3: Role Combination for Teams

```bash
# Combine multiple specialized roles
azure-custom-role-tool create --name "CloudOpsTeam" --description "Combined CloudOps permissions"

# Combine DevOps, Infrastructure, and Monitoring
azure-custom-role-tool merge --roles "devops-developer,infrastructure-admin,monitoring-reader"

# Remove conflicts/sensitive ops
azure-custom-role-tool remove --filter "*delete*"
```

### Pattern 4: Environment-Specific Roles

```bash
# Development role - permissive
azure-custom-role-tool create --name "DataEng-Dev" --description "Dev environment"
azure-custom-role-tool merge --roles "senior-developer"

# Production role - restrictive
azure-custom-role-tool create --name "DataEng-Prod" --description "Prod environment"
azure-custom-role-tool merge --roles "data-reader"
azure-custom-role-tool merge --roles "pipeline-operator" --filter "Pipeline*"
```

## Command Reference

### Global Options

```bash
--help          Show help for any command
--version       Show version information
```

### Commands

| Command | Purpose | Options |
|---------|---------|---------|
| `create` | Create new role | `--name`, `--description`, `--subscription-id` |
| `load` | Load existing role | `--name`, `--role-dir` |
| `merge` | Merge permissions | `--roles`, `--filter`, `--filter-type` |
| `remove` | Remove permissions | `--filter`, `--filter-type` |
| `list` | List roles | `--name`, `--role-dir` |
| `list-azure` | List Azure roles | `--subscription-id` |
| `save` | Save role locally | `--name`, `--output`, `--overwrite` |
| `publish` | Publish to Azure | `--name`, `--subscription-id` |
| `view` | View current role | `--all` |

## File Structure

```
azure-custom-role-tool/
├── README.md                        # Quick start guide
├── PLATFORM_ENGINEER_GUIDE.md       # Detailed usage guide
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── setup.sh                         # Setup script
├── .gitignore                       # Git ignore rules
│
├── custom_role_designer.py          # Main CLI tool
├── role_manager.py                  # Role management logic
├── permission_filter.py             # Filtering utilities
├── azure_client.py                  # Azure SDK integration
├── tests.py                         # Unit tests
│
├── examples/                        # Example role definitions
│   ├── junior-developer.json
│   ├── senior-developer.json
│   └── devops-developer.json
│
├── roles/                           # Local saved roles
└── tests/                           # Test suite
```

## Data Model

### Role Definition (JSON)

```json
{
  "Name": "Custom Role Name",
  "IsCustom": true,
  "Description": "Role description",
  "Type": "CustomRole",
  "Id": "custom-xxxxx",
  "Permissions": [
    {
      "Actions": ["Microsoft.*/*/read"],
      "NotActions": ["Microsoft.Compute/*/delete"],
      "DataActions": ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/*"],
      "NotDataActions": []
    }
  ],
  "AssignableScopes": ["/"],
  "CreatedOn": "2024-01-01T00:00:00",
  "UpdatedOn": "2024-01-01T00:00:00"
}
```

### Action Categories

- **Actions**: Control plane operations
- **NotActions**: Control plane operations to exclude
- **DataActions**: Data plane operations
- **NotDataActions**: Data plane operations to exclude

## Filtering Syntax Reference

### String Patterns

| Pattern | Matches | Example |
|---------|---------|---------|
| `Exact` | Exact match | `Microsoft.Storage/storageAccounts/read` |
| `*` | Wildcard | `Microsoft.Storage*` |
| `prefix*` | Starts with | `Microsoft.Compute*` |
| `*suffix` | Ends with | `*/read` |
| `*middle*` | Contains | `*blobs*` |

### Type Filters

- `control` - Management plane only
- `data` - Data plane only
- (omitted) - Both types

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `No current role` | Not created/loaded | Create or load a role first |
| `Role not found` | File doesn't exist | Check file path and name |
| `AZURE_SUBSCRIPTION_ID not set` | Missing config | Set env var or login to Azure CLI |
| `Failed to authenticate` | Auth issue | Run `az login` |

## Performance

- **Merge many roles**: Efficient deduplication (< 1s for typical roles)
- **Save/load**: Fast JSON I/O (< 100ms)
- **Filter large roles**: Regex matching optimized (< 50ms)
- **Azure operations**: Depends on network (1-10s typical)

## Security Considerations

1. **Never commit secrets**: Use `.env.example` template
2. **Review paths**: Always use `--all` flag before publishing
3. **Role naming**: Follow company standards
4. **Audit logging**: Track all role publications
5. **Version control**: Commit role files to Git

## Integration Examples

### CI/CD Pipeline

```yaml
- name: Deploy Custom Role
  run: |
    azure-custom-role-tool load --name "prod-role"
    azure-custom-role-tool view --all
    azure-custom-role-tool publish --name "prod-role"
  env:
    AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUB }}
```

### Script Automation

```bash
#!/bin/bash
for role in $(ls roles/*.json); do
  azure-custom-role-tool load --role-dir roles --name $(basename $role .json)
  azure-custom-role-tool publish
done
```

## Troubleshooting

- **Permissions not merging**: Check filter pattern with `list --name`
- **File already exists**: Use `--overwrite` flag
- **Azure publish fails**: Verify subscription ID and permissions
- **Tool crashes**: Check Python version (3.8+) and dependencies

---

**Tool Version**: 1.0  
**Last Updated**: January 2024
