# Azure Custom Role Designer

[![Python CI](https://github.com/pacorreia/azure-custom-role-tool/actions/workflows/python-ci.yml/badge.svg)](https://github.com/pacorreia/azure-custom-role-tool/actions/workflows/python-ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://pacorreia.github.io/azure-custom-role-tool/badges/coverage.json)](https://github.com/pacorreia/azure-custom-role-tool/actions/workflows/python-ci.yml)
[![Version](https://img.shields.io/github/v/release/pacorreia/azure-custom-role-tool?style=flat-square)](https://github.com/pacorreia/azure-custom-role-tool/releases)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/pacorreia/azure-custom-role-tool)](LICENSE)

## Welcome

**Azure Custom Role Designer** is a powerful command-line tool for platform engineers to create, manage, and deploy Azure custom roles with granular permission control.

## Quick Start

```bash
# Install
pip install -e .

# Enter interactive mode
azure-custom-role-tool console

# Or use commands directly
azure-custom-role-tool create --name "MyRole" --description "My custom role"
```

## Core Features

- **Create custom roles** from scratch or as templates
- **Load roles** from local storage or Azure
- **Merge permissions** from multiple roles with filtering
- **Remove permissions** by pattern or type
- **Manage role properties** (name, description, scopes)
- **Publish to Azure** directly from CLI
- **Interactive console mode** with command history
- **Multi-line paste mode** for batch operations

## Documentation Structure

### 📖 [Guides](guides/index.md)
Step-by-step guides for common tasks:
- [Platform Engineer Guide](guides/platform-engineer.md)
- [Paste Mode Guide](guides/paste-mode.md)
- [Delete Role Guide](guides/delete-role.md)

### ✨ [Features](features/index.md)
Detailed feature documentation:
- [Multi-line Scripts](features/multiline-scripts.md)
- [Role Properties](features/role-properties.md)
- [Unified Load Feature](features/unified-load.md)
- [Merge with Azure Fallback](features/merge-azure-fallback.md)

### 🔍 [Reference](reference/index.md)
API and command reference:
- [Feature Reference](reference/feature-reference.md)
- [Quick Reference](reference/quick-reference.md)

### 👨‍💻 [Development](development/index.md)
For developers and contributors:
- [Code Refactoring](development/code-refactoring.md)
- [Implementation Summary](development/implementation-summary.md)

## Key Concepts

### Interactive Console Mode
Run `azure-custom-role-tool console` to enter an interactive shell with:
- Command history navigation
- Multi-line paste support
- Real-time role state feedback
- Shell command integration

### Permission Filtering
Filter permissions by:
- **String pattern**: `Microsoft.Storage*`, `*read*`
- **Type**: `control` (management) or `data` (data operations)
- **Combination**: Both string and type filters together

### Role Workflow
Typical workflow:
1. **Create** or **Load** a role
2. **Merge** permissions from other roles
3. **Remove** unnecessary permissions
4. **Modify** properties (name, description, scopes)
5. **Save** locally for review
6. **Publish** to Azure

## Get Started

Choose a getting started guide:

- **New to the tool?** → [Platform Engineer Guide](guides/platform-engineer.md)
- **Want to batch operations?** → [Paste Mode Guide](guides/paste-mode.md)
- **Need to clean up roles?** → [Delete Role Guide](guides/delete-role.md)

## Support

For issues or questions:
- Check the [Feature Reference](reference/feature-reference.md)
- Review the [Platform Engineer Guide](guides/platform-engineer.md#troubleshooting)
- Submit an issue on the repository

---

**Latest Version**: 1.0  
**Last Updated**: February 2026
