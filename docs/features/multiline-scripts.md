# Multi-Line Script Support in Console Mode

## Overview

The console mode now supports **multi-line command input** with automatic comment filtering. This enables users to paste entire scripts directly into the interactive console, similar to shell script execution. Comments (lines starting with `#`) and blank lines are automatically ignored.

## Motivation

Previously, users could only enter one command per prompt in console mode. This limited automation capabilities and made it tedious to:
- Paste documentation examples with multiple steps
- Execute batch role creation/modification workflows
- Share reusable command sequences with team members

With multi-line support, users can now:
- Copy-paste example scripts from documentation
- Execute batch operations in a single input
- Include comments in scripts for clarity
- Maintain clean, readable command sequences

## Usage

### Paste Mode (Recommended)

To paste multiple commands at once, use the **`paste`** command:

```
> paste
Enter multiple commands (press Enter twice to submit):
  # Create and configure a custom role
  create-custom
  set-name --name StorageManager
  set-description --description "Storage operations role"
  set-scopes /subscriptions/prod-001
  view
  save
  (empty line to submit)
```

### Comments and Blank Lines

Comments (lines starting with `#`) are automatically filtered out:

```
# Setup phase
create-custom

# Configuration phase
set-name --name DataRole
set-description --description "Role for data operations"
set-scopes /subscriptions/prod-sub-001

# Finalization
view
```

### Realistic Workflow Example

Here's how a complete role creation workflow looks in paste mode:

1. Type `paste` in the console
2. Paste the following commands:

```
# Role Creation Workflow
# Step 1: Create new custom role
create-custom

# Step 2: Configure metadata
set-name --name AzureVMManager
set-description --description "Manage virtual machines and compute resources"

# Step 3: Set assignable scopes
set-scopes /subscriptions/prod-sub-001,/subscriptions/prod-sub-002

# Step 4: Merge permissions from template
merge --role-dir /templates/compute-base

# Step 5: Review and finalize
view --show-all
save
```

3. Press Enter (for the last line)
4. Press Enter again (empty line to submit)

**Result**:
```
Executing 8 command(s)...
[dim]>> create-custom[/dim]
✓ Created custom role
[dim]>> set-name --name AzureVMManager[/dim]
✓ Role name updated
... (output for remaining commands)
```

## Features

### Comment Filtering
- Lines starting with `#` (after whitespace stripping) are treated as comments
- Entire line is ignored, including `#` character
- Use `#` freely in command arguments without issues (they're only filtered at line start)

### Blank Line Handling
- Empty lines are silently skipped
- Lines with only whitespace (spaces, tabs) are also skipped
- No extra prompts or confirmation needed

### Command Execution
- Commands are executed sequentially in order of appearance
- Each command is processed with full error handling
- If one command fails, execution continues with the next command
- Output from each command is displayed with standard formatting

### Multi-Line Visibility
When multiple commands are pasted, each command is displayed with a `[dim]>>` prefix:

```
[dim]>> create-custom[/dim]
✓ Created custom role
[dim]>> set-name --name MyRole[/dim]
✓ Role name updated
```

## How It Works

### Implementation Details

1. **Input Capture**: The prompt accepts multiple lines using `prompt_toolkit`'s `multiline=True` setting
   - Single line: Normal behavior (Shift+Enter not needed)
   - Multiple lines: Use Shift+Enter to continue, Enter to submit

2. **Command Parsing**: Raw input is parsed by `parse_multiline_commands()`:
   - Splits input by newlines
   - Strips whitespace from each line
   - Filters comments (lines starting with `#`)
   - Filters empty/whitespace-only lines
   - Returns list of valid commands

3. **Sequential Execution**: Each parsed command is executed:
   - Commands processed in original order
   - All error handling applied per-command
   - Output shown for each command
   - Console context maintained throughout

## Test Coverage

18 comprehensive tests verify the feature:

### Core Parsing Tests
- Single command parsing
- Multiple command separation
- Complex arguments with quotes
- Comment filtering (various positions, with whitespace)
- Empty line handling
- Whitespace-only lines
- Hash characters in command arguments (not filtered)
- Mixed scripts with comments, blanks, and commands
- Edge cases (only comments, empty input, trailing newlines)

### Workflow Tests
- Role creation workflow
- Merge and modify operations
- Complex annotated workflow with detailed comments

All tests pass: ✓ 18/18

## Examples

### Example 1: Simple Role Creation

```
# Create a storage management role
create-custom
set-name --name StorageAdmin
set-description --description "Azure Storage administration"
view
save
```

### Example 2: Load and Enhance Role

```
# Load and enhance an existing role template
load --name BaseComputeRole
merge --role-dir /templates/compute-enhancements
set-name --name EnhancedComputeRole
set-description --description "Updated compute role with new permissions"
view
save
```

### Example 3: Multi-Scope Deployment

```
# Deploy role to multiple subscriptions
create-custom
set-name --name CrossTenantRole
set-description --description "Role available across multiple subscriptions"

# Configure for multiple scopes
set-scopes /subscriptions/prod-001,/subscriptions/prod-002,/subscriptions/prod-003

# Verify configuration
view --show-all
publish --subscription-id prod-001
```

## Backward Compatibility

- Single-line input works exactly as before
- No changes to existing command syntax
- All existing scripts and workflows remain compatible
- Help system unchanged
- History still records all commands

## Related Features

- **Unified Load Command**: Automatically falls back to Azure if local role not found
- **Role Property Modification**: Set name, description, and scopes
- **Merge with Azure Fallback**: Combine permissions from local and Azure sources
- **Shell Command Integration**: Use `!` prefix or `shell` command for system commands

## Performance Notes

- Multi-line parsing is efficient (O(n) where n = input characters)
- No delay between commands in batch
- History file updated normally for each command
- Console remains responsive during batch execution

## Future Enhancements

Potential future improvements:
- Script file loading (e.g., `load-script /path/to/script.cli`)
- Conditional execution based on previous command success
- Variable substitution in scripts
- Loop constructs for repetitive operations

## Troubleshooting

### Commands not executing in order
- Verify no syntax errors in earlier commands
- Check that all commands are on separate lines
- Use `view` command to verify role state between operations

### Comments not being ignored
- Ensure `#` is at the start of the line (after stripping whitespace)
- Hash characters in quoted strings or command arguments are preserved correctly

### Copy-paste not working as expected
- Ensure your terminal supports multi-line paste
- Try using Shift+Enter explicitly between lines instead of pasting
- Some terminals may require special handling for multi-line input
