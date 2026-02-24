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
azure-custom-role-tool --help

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
azure-custom-role-tool console
```

This launches an interactive menu where you can navigate through all operations.

**Interactive Mode Features:**
- Use arrow keys (↑/↓) to recall and navigate through previous commands
- Command history persists across sessions (stored in `~/.azure-custom-role-tool-history`)
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
azure-custom-role-tool create --name "My Custom Role" --description "Custom role for my team"
```

#### Load Existing Role

```bash
# Load from local file
azure-custom-role-tool load --name "devops-developer"

# Load from custom directory
azure-custom-role-tool load --name "my-role" --role-dir /path/to/roles
```

#### View Role Details

```bash
# Show summary
azure-custom-role-tool view

# Show all permissions (no truncation)
azure-custom-role-tool view --all
```

#### Save Role

```bash
# Save to default roles directory
azure-custom-role-tool save --name "my-role"

# Save to custom location
azure-custom-role-tool save --name "my-role" --output /path/to/my-role.json

# Overwrite existing file
azure-custom-role-tool save --name "my-role" --overwrite
```

## Advanced Examples

### Example 1: Create Developer Role from Scratch

```bash
# Create new role
azure-custom-role-tool create --name "App Developer" --description "Permissions for app development"

# Merge read permissions from multiple roles
azure-custom-role-tool merge --roles "junior-developer,reader" --filter "*read*"

# Remove delete operations
azure-custom-role-tool remove --filter "*delete*" --filter-type control

# Save locally
azure-custom-role-tool save --name "app-developer"

# Publish to Azure
azure-custom-role-tool publish --name "app-developer"
```

### Example 2: Cherry-pick Specific Permissions

```bash
# Create new role
azure-custom-role-tool create --name "Storage Manager" --description "Manage Azure Storage"

# Merge only storage permissions from senior developer role
azure-custom-role-tool merge --roles "senior-developer" --filter "Microsoft.Storage*"

# Add specific data plane permissions
azure-custom-role-tool merge --roles "reader" --filter "blobs/read" --filter-type data

# Save and publish
azure-custom-role-tool save --name "storage-manager" --overwrite
azure-custom-role-tool publish --name "storage-manager"
```

### Example 3: Merge Multiple Roles with Filtering

```bash
# Create new role
azure-custom-role-tool create --name "DevOps Manager" --description "Ops role for DevOps team"

# Merge control plane permissions from multiple roles
azure-custom-role-tool merge \
  --roles "devops-developer,senior-developer,infrastructure-admin" \
  --filter-type control

# Remove specific dangerous operations
azure-custom-role-tool remove --filter "*delete*"
azure-custom-role-tool remove --filter "*deallocate*"

# Save
azure-custom-role-tool save --name "devops-manager" --overwrite
```

### Example 4: Create Restricted Viewer Role

```bash
# Start with reader permissions
azure-custom-role-tool create --name "Audit Viewer" --description "Read-only audit permissions"

# Load and merge reader role
azure-custom-role-tool merge --roles "reader" --filter "*read*"

# Remove sensitive data access
azure-custom-role-tool remove --filter "keys/read" --filter-type data
azure-custom-role-tool remove --filter "secrets/read" --filter-type data

# Save
azure-custom-role-tool save --name "audit-viewer"
```

## Workflow Scenarios

### Scenario 1: Request → Design → Test → Publish

**Step 1: Create Role Design**

```bash
# Create new role based on requirements
azure-custom-role-tool create --name "DataEngineer-Prod" --description "Production data processing"

# Build from senior developer permissions
azure-custom-role-tool merge --roles "senior-developer"

# Keep only data-related permissions
azure-custom-role-tool remove --filter "*Compute*"
azure-custom-role-tool remove --filter "*Network*"
```

**Step 2: Review**

```bash
azure-custom-role-tool view --all
```

**Step 3: Save Locally for Review**

```bash
azure-custom-role-tool save --name "dataengineer-prod"
# Commit to Git for review: roles/dataengineer-prod.json
```

**Step 4: Publish After Approval**

```bash
azure-custom-role-tool publish --name "dataengineer-prod"
```

### Scenario 2: Update Existing Role

```bash
# Load existing role
azure-custom-role-tool load --name "dataengineer-prod"

# View current permissions
azure-custom-role-tool view --all

# Add new required permissions
azure-custom-role-tool merge --roles "senior-developer" --filter "PostgreSQL*"

# Remove deprecated permissions
azure-custom-role-tool remove --filter "Legacy*"

# Save and publish
azure-custom-role-tool save --name "dataengineer-prod" --overwrite
azure-custom-role-tool publish --name "dataengineer-prod"
```

### Scenario 3: Compare Multiple Roles

```bash
# List available roles
azure-custom-role-tool list

# View each role
azure-custom-role-tool list --name "senior-developer"
azure-custom-role-tool list --name "junior-developer"

# Use to understand permission differences before merging
```

## Filtering Guide

### String Filters

String filters use wildcard patterns (case-insensitive):

```bash
# Exact match
azure-custom-role-tool merge --roles "senior-developer" --filter "Microsoft.Storage/storageAccounts/read"

# Wildcard match
azure-custom-role-tool merge --roles "senior-developer" --filter "Microsoft.Storage*"

# Partial match
azure-custom-role-tool merge --roles "senior-developer" --filter "*blobs*"

# Complex patterns
azure-custom-role-tool merge --roles "senior-developer" --filter "Microsoft.*/*/read"
```

### Type Filters

```bash
# Control plane only (management operations)
azure-custom-role-tool merge --roles "senior-developer" --filter-type control

# Data plane only (data operations)
azure-custom-role-tool merge --roles "senior-developer" --filter-type data

# Combine filters
azure-custom-role-tool merge --roles "senior-developer" --filter "Storage*" --filter-type data
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
azure-custom-role-tool create --name "App Developer"
azure-custom-role-tool merge --roles "basic-reader" --filter "Microsoft.Web*"

# Avoid: Creating with wildcard permissions
azure-custom-role-tool merge --roles "contributor"
```

### 2. Document Your Roles

Always include clear descriptions:

```bash
azure-custom-role-tool create \
  --name "DataEngineer" \
  --description "Create/update data pipelines and manage Azure Data Factory, SQL Database, and Storage accounts. Cannot delete resources or modify access controls."
```

### 3. Use Filters for Safety

Always remove dangerous operations:

```bash
azure-custom-role-tool merge --roles "senior-developer"
azure-custom-role-tool remove --filter "*delete*"
azure-custom-role-tool remove --filter "*deallocate*"
```

### 4. Version Your Roles

Include environment/version in role names:

```bash
azure-custom-role-tool create --name "DataEngineer-Dev-v1"
azure-custom-role-tool create --name "DataEngineer-Prod-v2"
```

### 5. Review Changes

Always view the final role before publishing:

```bash
azure-custom-role-tool view --all
# Review output, then:
azure-custom-role-tool publish --name "my-role"
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
azure-custom-role-tool list
azure-custom-role-tool list --role-dir /path/to/roles
```

### Issue: "No current role"

**Solution:** Create or load a role first:

```bash
azure-custom-role-tool create --name "MyRole" --description "Test"
# or
azure-custom-role-tool load --name "existing-role"
```

### Issue: "Permissions not merged as expected"

**Solution:** Check your filters:

```bash
# List role to see permission names
azure-custom-role-tool list --name "source-role"

# Test filter pattern
azure-custom-role-tool merge --roles "source-role" --filter "exact-permission-name"
```

## Integration with CI/CD

### Example: GitHub Actions

```yaml
- name: Create Azure Role
  run: |
    azure-custom-role-tool create --name "CI-Role"
    azure-custom-role-tool merge --roles "devops-developer"
    azure-custom-role-tool publish --name "CI-Role"
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
