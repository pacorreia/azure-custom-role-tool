# Multi-Line Paste Mode

## Overview

The console mode includes a **`paste`** command that enables you to paste multiple commands at once, similar to shell script execution. This is ideal for sharing command sequences or pasting examples from documentation.

## Usage

### Basic Workflow

1. **Enter the console**:
   ```
   azure-custom-role-tool console
   ```

2. **Start paste mode**:
   ```
   > paste
   ```

3. **Paste your commands** (lines starting with `#` are filtered as comments):
   ```
   # Create and configure a custom role
   create-custom
   set-name --name DataRole
   set-description --description "My custom role"
   view
   save
   ```

4. **Press Enter twice** (once for last command, once empty line to submit):
   ```
   > paste
   ```
   (paste all lines, then press Enter after last line, then press Enter again for empty line)

## Examples

### Example 1: Create and Configure Role

```
> paste
Enter multiple commands (press Enter twice to submit):
  # Create storage role
  create-custom
  set-name --name StorageAdmin
  set-description --description "Azure Storage administration"
  view
  save
  (press Enter for empty line)
```

### Example 2: Load, Merge, and Modify

```
> paste
Enter multiple commands (press Enter twice to submit):
  # Load and enhance existing role
  load --name BaseComputeRole
  merge --role-dir /templates/compute-enhancements
  set-name --name EnhancedComputeRole
  set-description --description "Updated compute role"
  view
  save
  (press Enter for empty line)
```

### Example 3: Multi-Scope Deployment

```
> paste
Enter multiple commands (press Enter twice to submit):
  # Deploy role across multiple subscriptions
  create-custom
  set-name --name CrossTenantRole
  set-description --description "Role for multiple subscriptions"
  set-scopes /subscriptions/prod-001,/subscriptions/prod-002
  view --show-all
  publish --subscription-id prod-001
  (press Enter for empty line)
```

## Features

- **Comment filtering**: Lines starting with `#` are automatically ignored
- **Empty line support**: Blank lines between commands are skipped
- **Sequential execution**: All commands execute in order with full error handling
- **Output display**: Each command is shown with `[dim]>>` prefix for clarity
- **Error resilience**: If one command fails, remaining commands continue executing

## Differences from Single-Line Mode

| Feature | Single-Line | Paste Mode |
|---------|-----------|-----------|
| Input method | Type one command, press Enter | Paste multiple lines, press Enter twice |
| Comments | Not supported | Automatic filtering of `#` lines |
| Multiple commands | One at a time | All at once |
| Error handling | Stop on error | Continue through errors |
| Use case | Interactive use | Batch operations, scripts, documentation |

## Tips

1. **Copy from documentation**: Open a documentation example, copy it, switch to the console, type `paste`, paste the code, press Enter twice

2. **Reuse workflows**: Keep common command sequences as text files, paste them into paste mode when needed

3. **Share with team**: Write command sequences in a file and share them - team members just paste into `paste` mode

4. **Script testing**: Test shell-like scripts before automating them in CI/CD pipelines

## Related Commands

- `help paste` - Show detailed help for paste command (in interactive mode)
- `console` - Enter interactive console mode
- `!<command>` - Execute shell commands inline
- `shell <cmd>` - Execute shell commands inline

## Exit Paste Mode

You can exit paste mode without executing by pressing Ctrl+C during input.
