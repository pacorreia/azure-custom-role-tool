# Azure Custom Role Designer - Platform Engineer Guide

## Overview

Azure Custom Role Designer is a command-line tool that streamlines the creation and management of Azure custom roles. It provides a flexible interface for platform engineers to build roles with granular permission control.

## Table of Contents

1. [Installation](#installation)
2. [Authentication](#authentication)
3. [Basic Usage](#basic-usage)
4. [Advanced Examples](#advanced-examples)
5. [Workflow Scenarios](#workflow-scenarios)
6. [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.8+
- Azure CLI (for authentication)
- Access to an Azure subscription

### Setup

```bash
# Navigate to the project
cd azure-custom-role-tool

# Option 1: Quick setup script
bash setup.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install .

# Or install in development mode (for contributions)
pip install -e .
```

### Verify Installation

```bash
# Check that the command is available
custom-role-designer --help

# Or use it through Python
python -m azure_custom_role_tool --help
```

### Azure CLI Login

If using Azure CLI authentication (recommended):

```bash
az login
az account set --subscription "your-subscription-id"
```

## Authentication

### Option 1: Azure CLI (Recommended)

Most straightforward for local development:

```bash
az login
# The tool will automatically use your CLI credentials
```

### Option 2: Service Principal

For CI/CD pipelines or headless environments:

```bash
# Set environment variables
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# Copy .env.example to .env and fill in values
cp .env.example .env
```

### Option 3: Managed Identity

When running on Azure resources (VMs, ACI, App Service):

```bash
# No configuration needed - automatically detected
```

## Basic Usage

### Interactive Mode

```bash
custom-role-designer console
```

This launches an interactive menu where you can navigate through all operations.

**Interactive Mode Features:**
- Use arrow keys (↑/↓) to recall and navigate through previous commands
- Command history persists across sessions (stored in `~/.custom-role-designer-history`)
- Type `help <command>` for detailed help on specific commands
- The current role stays loaded throughout the session, making it easy to chain operations

**Tips for Interactive Mode:**
- Start with loading or creating a role
- Use arrow keys to quickly repeat or modify previous commands
- View the current role at any time with the `view` command
- Exit with `exit` or `quit` commands, or press Ctrl+C

### Command Line Mode

#### Create a New Role

```bash
# Start with empty role
custom-role-designer create --name "My Custom Role" --description "Custom role for my team"
```

#### Load Existing Role

```bash
# Load from local file
custom-role-designer load --name "devops-developer"

# Load from custom directory
custom-role-designer load --name "my-role" --role-dir /path/to/roles
```

#### View Role Details

```bash
# Show summary
custom-role-designer view

# Show all permissions (no truncation)
custom-role-designer view --all
```

#### Save Role

```bash
# Save to default roles directory
custom-role-designer save --name "my-role"

# Save to custom location
custom-role-designer save --name "my-role" --output /path/to/my-role.json

# Overwrite existing file
custom-role-designer save --name "my-role" --overwrite
```

## Advanced Examples

### Example 1: Create Developer Role from Scratch

```bash
# Create new role
custom-role-designer create --name "App Developer" --description "Permissions for app development"

# Merge read permissions from multiple roles
custom-role-designer merge --roles "junior-developer,reader" --filter "*read*"

# Remove delete operations
custom-role-designer remove --filter "*delete*" --filter-type control

# Save locally
custom-role-designer save --name "app-developer"

# Publish to Azure
custom-role-designer publish --name "app-developer"
```

### Example 2: Cherry-pick Specific Permissions

```bash
# Create new role
custom-role-designer create --name "Storage Manager" --description "Manage Azure Storage"

# Merge only storage permissions from senior developer role
custom-role-designer merge --roles "senior-developer" --filter "Microsoft.Storage*"

# Add specific data plane permissions
custom-role-designer merge --roles "reader" --filter "blobs/read" --filter-type data

# Save and publish
custom-role-designer save --name "storage-manager" --overwrite
custom-role-designer publish --name "storage-manager"
```

### Example 3: Merge Multiple Roles with Filtering

```bash
# Create new role
custom-role-designer create --name "DevOps Manager" --description "Ops role for DevOps team"

# Merge control plane permissions from multiple roles
custom-role-designer merge \
  --roles "devops-developer,senior-developer,infrastructure-admin" \
  --filter-type control

# Remove specific dangerous operations
custom-role-designer remove --filter "*delete*"
custom-role-designer remove --filter "*deallocate*"

# Save
custom-role-designer save --name "devops-manager" --overwrite
```

### Example 4: Create Restricted Viewer Role

```bash
# Start with reader permissions
custom-role-designer create --name "Audit Viewer" --description "Read-only audit permissions"

# Load and merge reader role
custom-role-designer merge --roles "reader" --filter "*read*"

# Remove sensitive data access
custom-role-designer remove --filter "keys/read" --filter-type data
custom-role-designer remove --filter "secrets/read" --filter-type data

# Save
custom-role-designer save --name "audit-viewer"
```

## Workflow Scenarios

### Scenario 1: Request → Design → Test → Publish

**Step 1: Create Role Design**

```bash
# Create new role based on requirements
custom-role-designer create --name "DataEngineer-Prod" --description "Production data processing"

# Build from senior developer permissions
custom-role-designer merge --roles "senior-developer"

# Keep only data-related permissions
custom-role-designer remove --filter "*Compute*"
custom-role-designer remove --filter "*Network*"
```

**Step 2: Review**

```bash
custom-role-designer view --all
```

**Step 3: Save Locally for Review**

```bash
custom-role-designer save --name "dataengineer-prod"
# Commit to Git for review: roles/dataengineer-prod.json
```

**Step 4: Publish After Approval**

```bash
custom-role-designer publish --name "dataengineer-prod"
```

### Scenario 2: Update Existing Role

```bash
# Load existing role
custom-role-designer load --name "dataengineer-prod"

# View current permissions
custom-role-designer view --all

# Add new required permissions
custom-role-designer merge --roles "senior-developer" --filter "PostgreSQL*"

# Remove deprecated permissions
custom-role-designer remove --filter "Legacy*"

# Save and publish
custom-role-designer save --name "dataengineer-prod" --overwrite
custom-role-designer publish --name "dataengineer-prod"
```

### Scenario 3: Compare Multiple Roles

```bash
# List available roles
custom-role-designer list

# View each role
custom-role-designer list --name "senior-developer"
custom-role-designer list --name "junior-developer"

# Use to understand permission differences before merging
```

## Filtering Guide

### String Filters

String filters use wildcard patterns (case-insensitive):

```bash
# Exact match
custom-role-designer merge --roles "senior-developer" --filter "Microsoft.Storage/storageAccounts/read"

# Wildcard match
custom-role-designer merge --roles "senior-developer" --filter "Microsoft.Storage*"

# Partial match
custom-role-designer merge --roles "senior-developer" --filter "*blobs*"

# Complex patterns
custom-role-designer merge --roles "senior-developer" --filter "Microsoft.*/*/read"
```

### Type Filters

```bash
# Control plane only (management operations)
custom-role-designer merge --roles "senior-developer" --filter-type control

# Data plane only (data operations)
custom-role-designer merge --roles "senior-developer" --filter-type data

# Combine filters
custom-role-designer merge --roles "senior-developer" --filter "Storage*" --filter-type data
```

## Permission Categories

### Control Plane Permissions

Management operations on Azure resources. Examples:
- `Microsoft.Compute/virtualMachines/start/action`
- `Microsoft.Storage/storageAccounts/write`
- `Microsoft.Network/virtualNetworks/delete`

### Data Plane Permissions

Operations on data within Azure resources. Examples:
- `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`
- `Microsoft.Sql/servers/databases/tables/data/read`
- `Microsoft.KeyVault/vaults/secrets/read`

## Best Practices

### 1. Principle of Least Privilege

Always start restrictive and add permissions as needed:

```bash
# Good: Create empty, add specific permissions
custom-role-designer create --name "App Developer"
custom-role-designer merge --roles "basic-reader" --filter "Microsoft.Web*"

# Avoid: Creating with wildcard permissions
custom-role-designer merge --roles "contributor"
```

### 2. Document Your Roles

Always include clear descriptions:

```bash
custom-role-designer create \
  --name "DataEngineer" \
  --description "Create/update data pipelines and manage Azure Data Factory, SQL Database, and Storage accounts. Cannot delete resources or modify access controls."
```

### 3. Use Filters for Safety

Always remove dangerous operations:

```bash
custom-role-designer merge --roles "senior-developer"
custom-role-designer remove --filter "*delete*"
custom-role-designer remove --filter "*deallocate*"
```

### 4. Version Your Roles

Include environment/version in role names:

```bash
custom-role-designer create --name "DataEngineer-Dev-v1"
custom-role-designer create --name "DataEngineer-Prod-v2"
```

### 5. Review Changes

Always view the final role before publishing:

```bash
custom-role-designer view --all
# Review output, then:
custom-role-designer publish --name "my-role"
```

## Troubleshooting

### Issue: "AZURE_SUBSCRIPTION_ID not set"

**Solution:** Set your subscription ID:

```bash
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
# Or
echo "AZURE_SUBSCRIPTION_ID=your-subscription-id" > .env
```

### Issue: "Failed to authenticate"

**Solution:** Ensure Azure CLI is logged in:

```bash
az login
az account set --subscription "your-subscription-id"
```

### Issue: "Role not found"

**Solution:** Verify role exists and correct directory:

```bash
custom-role-designer list
custom-role-designer list --role-dir /path/to/roles
```

### Issue: "No current role"

**Solution:** Create or load a role first:

```bash
custom-role-designer create --name "MyRole" --description "Test"
# or
custom-role-designer load --name "existing-role"
```

### Issue: "Permissions not merged as expected"

**Solution:** Check your filters:

```bash
# List role to see permission names
custom-role-designer list --name "source-role"

# Test filter pattern
custom-role-designer merge --roles "source-role" --filter "exact-permission-name"
```

## Integration with CI/CD

### Example: GitHub Actions

```yaml
- name: Create Azure Role
  run: |
    custom-role-designer create --name "CI-Role"
    custom-role-designer merge --roles "devops-developer"
    custom-role-designer publish --name "CI-Role"
  env:
    AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
    AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
    AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
    AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
```

## Support and Contribution

For issues, feature requests, or contributions:

1. Document your use case
2. Include example commands
3. Share any relevant logs
4. Contact the platform engineering team

---

**Last Updated:** February 2026
**Version:** 1.0
