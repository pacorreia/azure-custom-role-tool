"""Tests for multi-line console script execution and comment filtering."""

import pytest
from azure_custom_role_tool.cli import parse_multiline_commands


class TestParseMultilineCommands:
    """Test the parse_multiline_commands function."""
    
    def test_single_command(self):
        """Test parsing a single command."""
        result = parse_multiline_commands("create-custom")
        assert result == ["create-custom"]
    
    def test_multiple_commands(self):
        """Test parsing multiple commands separated by newlines."""
        input_text = "create-custom\nset-name --name MyRole\nview"
        result = parse_multiline_commands(input_text)
        assert result == ["create-custom", "set-name --name MyRole", "view"]
    
    def test_command_with_arguments(self):
        """Test parsing command with complex arguments."""
        input_text = 'set-description --description "My Role Description"'
        result = parse_multiline_commands(input_text)
        assert result == ['set-description --description "My Role Description"']
    
    def test_comments_ignored(self):
        """Test that lines starting with # are ignored."""
        input_text = """# This is a comment
create-custom
# Another comment
set-name --name MyRole"""
        result = parse_multiline_commands(input_text)
        assert result == ["create-custom", "set-name --name MyRole"]
    
    def test_empty_lines_ignored(self):
        """Test that empty lines are ignored."""
        input_text = """create-custom

set-name --name MyRole

view"""
        result = parse_multiline_commands(input_text)
        assert result == ["create-custom", "set-name --name MyRole", "view"]
    
    def test_whitespace_only_lines_ignored(self):
        """Test that lines with only whitespace are ignored."""
        input_text = """create-custom
    
\t
set-name --name MyRole
  \t  
view"""
        result = parse_multiline_commands(input_text)
        assert result == ["create-custom", "set-name --name MyRole", "view"]
    
    def test_comments_with_whitespace(self):
        """Test that comments with leading whitespace are handled."""
        input_text = """create-custom
  # Comment with leading whitespace
set-name --name MyRole"""
        result = parse_multiline_commands(input_text)
        # Leading whitespace is stripped, so comment should be filtered
        assert result == ["create-custom", "set-name --name MyRole"]
    
    def test_hash_in_middle_of_line_not_filtered(self):
        """Test that # in the middle of a line is preserved."""
        input_text = 'set-description --description "Role #1"'
        result = parse_multiline_commands(input_text)
        # The # is in the middle, not at start, so line should be included
        assert result == ['set-description --description "Role #1"']
    
    def test_mixed_script(self):
        """Test a complete script with comments, blanks, and commands."""
        input_text = """# Custom role designer script
# This script demonstrates creating and modifying a role

create-custom
set-name --name StorageRole

# Configure for storage operations
set-description --description "Custom role for storage operations"
set-scopes /subscriptions/12345

# View the final result
view

# Exit the console
exit"""
        result = parse_multiline_commands(input_text)
        expected = [
            "create-custom",
            "set-name --name StorageRole",
            "set-description --description \"Custom role for storage operations\"",
            "set-scopes /subscriptions/12345",
            "view",
            "exit"
        ]
        assert result == expected
    
    def test_only_comments_and_blanks(self):
        """Test input that contains only comments and blank lines."""
        input_text = """# Just comments
# No commands here

# Really, nothing"""
        result = parse_multiline_commands(input_text)
        assert result == []
    
    def test_empty_string(self):
        """Test empty string input."""
        result = parse_multiline_commands("")
        assert result == []
    
    def test_only_whitespace(self):
        """Test input with only whitespace."""
        result = parse_multiline_commands("   \n  \t  \n    ")
        assert result == []
    
    def test_command_with_pipes_and_quotes(self):
        """Test that commands with pipes and quotes are preserved exactly."""
        input_text = """view --filter 'Microsoft.Compute/*' | grep 'Provider'
create-custom --tags "env=prod,type=custom" """
        result = parse_multiline_commands(input_text)
        # These special characters should be preserved (parsing happens later with shlex)
        assert result == [
            "view --filter 'Microsoft.Compute/*' | grep 'Provider'",
            'create-custom --tags "env=prod,type=custom"'
        ]
    
    def test_trailing_newlines(self):
        """Test that trailing newlines don't cause issues."""
        input_text = """create-custom
set-name --name MyRole
view

"""
        result = parse_multiline_commands(input_text)
        assert result == ["create-custom", "set-name --name MyRole", "view"]
    
    def test_commands_with_long_descriptions(self):
        """Test commands with long multi-word arguments."""
        input_text = """merge --role-dir /path/to/role --permissions Microsoft.Compute/virtualmachines/*
set-description --description "A role for managing VMs and storage accounts with limited permissions\""""
        result = parse_multiline_commands(input_text)
        assert len(result) == 2
        assert "merge" in result[0]
        assert "set-description" in result[1]


class TestMultilineScriptExamples:
    """Test realistic multi-line script scenarios."""
    
    def test_role_creation_workflow(self):
        """Test a realistic role creation workflow script."""
        script = """# Role creation workflow
create-custom
set-name --name AzureVMManager
set-description --description "Manage Azure virtual machines and resources"
set-scopes /subscriptions/abc123/resourceGroups/prod
view
save"""
        result = parse_multiline_commands(script)
        assert "create-custom" in result
        assert "set-name --name AzureVMManager" in result
        assert len(result) == 6
    
    def test_merge_and_modify_workflow(self):
        """Test loading, merging, and modifying a role."""
        script = """# Merge and modify workflow
load --name StorageRole
merge --role-dir /roles/baseline
set-description --description "Enhanced storage role"
view
publish --subscription-id abc123"""
        result = parse_multiline_commands(script)
        assert len(result) == 5
        assert all(cmd.strip() for cmd in result)  # No empty commands
    
    def test_commented_workflow_with_annotations(self):
        """Test a workflow with detailed comments."""
        script = """# ============================================
# Azure Custom Role Configuration Script
# ============================================

# Step 1: Create new role
create-custom

# Step 2: Set metadata - name and description
set-name --name AzureDataManagerRole
set-description --description "Data platform administration role"

# Step 3: Configure scopes
set-scopes /subscriptions/prod-sub-001,/subscriptions/prod-sub-002

# Step 4: Add permissions from template
merge --role-dir /templates/data-platform

# Step 5: Verify and save
view --show-all
save

# Step 6: Deploy to Azure
publish --subscription-id prod-sub-001"""
        result = parse_multiline_commands(script)
        # Should have 8 commands (no comments or blanks)
        assert len(result) == 8
        assert result[0] == "create-custom"
        assert "AzureDataManagerRole" in result[1]
        assert result[-1].startswith("publish")
