# Azure Custom Role Designer

[![Python CI](https://github.com/pacorreia/azure-custom-role-tool/workflows/Python%20CI/badge.svg)](https://github.com/pacorreia/azure-custom-role-tool/actions/workflows/python-ci.yml)
[![Documentation](https://github.com/pacorreia/azure-custom-role-tool/workflows/Deploy%20Documentation/badge.svg)](https://pacorreia.github.io/azure-custom-role-tool/)
[![Coverage](https://img.shields.io/endpoint?url=https://pacorreia.github.io/azure-custom-role-tool/badges/coverage.json)](https://pacorreia.github.io/azure-custom-role-tool/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A powerful CLI tool for platform engineers to create, update, and manage Azure custom roles with granular control over permissions.

## Features

- **Create roles from scratch** - Start with an empty role definition
- **Cherry-pick permissions** - Select specific permissions from existing roles
- **Merge permissions** - Combine permissions from one or more existing roles with filtering capabilities
- **Remove permissions** - Filter and exclude specific permissions with advanced filtering
- **Filter by string** - Search permissions by action name pattern
- **Filter by type** - Separate control and data plane permissions
- **Persist roles** - Save and load role definitions locally and to Azure

## Installation

### Option 1: Install from the repository (Recommended)

```bash
# Clone/navigate to the project
cd azure-custom-role-tool

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

### Option 2: Install with all dependencies

```bash
pip install azure-custom-role-tool
```

### Option 3: Install from source with all requirements

```bash
git clone <repo-url>
cd azure-custom-role-tool
pip install .
```

## Quick Start

### Using the installed command

```bash
# Check version
custom-role-designer --version

# Interactive mode
custom-role-designer

# Or use specific commands
custom-role-designer create --name "My Custom Role" --description "Custom role for my team"
custom-role-designer merge --roles "devops-developer,reader" --filter "Storage"
custom-role-designer remove --filter "Delete"
```

### Using the module directly

```bash
# Check version
python -m azure_custom_role_tool --version

# Run as module
python -m azure_custom_role_tool

# Or use the module in your Python code
from azure_custom_role_tool import RoleManager, PermissionFilter, __version__
print(f"Using Azure Custom Role Tool v{__version__}")
manager = RoleManager()
role = manager.create_role("MyRole", "My custom role")
```

## Usage

### Interactive Mode

Run the tool without arguments or use the `console` command to enter console mode:

```bash
custom-role-designer console
```

This launches an interactive menu where you can:
1. Create a new role
2. Load an existing role
3. Merge permissions
4. Remove permissions
5. Filter and view permissions
6. Save/publish the role

**Interactive Features:**
- **Command History**: Use arrow keys (↑/↓) to navigate through previous commands
- **Persistent History**: Command history is saved to `~/.custom-role-designer-history` and persists across sessions
- **Context Help**: Type `help <command>` to see detailed help for any command
- **State Preservation**: The current role remains loaded across multiple commands within the session

### Command Line Mode

```bash
# Create a new role
custom-role-designer create --name "Name" --description "Description" --subscription-id xx-xx-xx

# Start from existing role
custom-role-designer load --name "existing-role"

# Merge multiple roles
custom-role-designer merge --roles role1,role2,role3 --filter "Storage" --filter-type control

# Remove permissions
custom-role-designer remove --filter "*/Delete/*" --filter-type data

# List available roles
custom-role-designer list

# View role details
custom-role-designer view --name "role-name"

# Save role locally
custom-role-designer save --name "role-name" --output roles/my-role.json

# Publish to Azure
custom-role-designer publish --name "role-name"
```

## Configuration

Create a `.env` file for Azure authentication:

```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

Or use Azure CLI authentication (default).

## File Structure

```
azure-custom-role-tool/
├── custom_role_designer.py      # Main CLI tool
├── role_manager.py              # Role management logic
├── permission_filter.py          # Filtering and search
├── azure_client.py              # Azure SDK integration
├── requirements.txt             # Dependencies
├── roles/                       # Local role definitions
├── examples/                    # Example role definitions
└── tests/                       # Unit tests
```

## Architecture

### Role Definition Schema

Roles are stored as JSON files conforming to Azure custom role definition format:

```json
{
  "Name": "Custom Role Name",
  "IsCustom": true,
  "Description": "Role description",
  "Type": "CustomRole",
  "Permissions": [
    {
      "Actions": ["Microsoft.Storage/*/read"],
      "NotActions": ["Microsoft.Storage/*/delete"],
      "DataActions": ["Microsoft.Storage/storageAccounts/blobServices/containers/blobs/*"],
      "NotDataActions": []
    }
  ],
  "CreatedOn": "2024-01-01",
  "UpdatedOn": "2024-01-01"
}
```

## Permission Type Classification

- **Control Plane**: Management operations (e.g., `Microsoft.Compute/virtualMachines/start/action`)
- **Data Plane**: Data operations (e.g., `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`)

## Examples

See the `examples/` directory for pre-built roles like:
- `devops-developer.json` - DevOps developer permissions
- `junior-developer.json` - Junior developer restricted permissions
- `senior-developer.json` - Senior developer full permissions

## Contributing

For issues or feature requests, contact the platform engineering team.

## License

Internal - OI Technologies
