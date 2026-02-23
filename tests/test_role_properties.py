"""Tests for role property modification commands."""

from pathlib import Path
from click.testing import CliRunner
import pytest

from azure_custom_role_tool import cli
from azure_custom_role_tool.role_manager import AzureRoleDefinition, PermissionDefinition


def test_set_name_command(monkeypatch, tmp_path: Path):
    """Test set-name command changes the role name."""
    runner = CliRunner()
    
    # Configure manager
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("OriginalName", "Test role")
    cli.role_manager.current_role = current
    
    # Change name
    result = runner.invoke(cli.cli, ["set-name", "--name", "NewName"])
    assert result.exit_code == 0
    assert "Role name changed" in result.output
    assert "OriginalName" in result.output
    assert "NewName" in result.output
    
    # Verify it was actually changed
    assert cli.role_manager.current_role.Name == "NewName"


def test_set_name_no_role(monkeypatch):
    """Test set-name fails when no role is loaded."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    cli.role_manager.current_role = None
    
    result = runner.invoke(cli.cli, ["set-name", "--name", "SomeName"])
    assert result.exit_code != 0
    assert "No current role" in result.output


def test_set_description_command(monkeypatch):
    """Test set-description command changes the description."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("TestRole", "Original description")
    cli.role_manager.current_role = current
    
    # Change description
    result = runner.invoke(cli.cli, ["set-description", "--description", "Updated description"])
    assert result.exit_code == 0
    assert "Description changed" in result.output
    assert "Original description" in result.output
    assert "Updated description" in result.output
    
    # Verify it was actually changed
    assert cli.role_manager.current_role.Description == "Updated description"


def test_set_description_no_role(monkeypatch):
    """Test set-description fails when no role is loaded."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    cli.role_manager.current_role = None
    
    result = runner.invoke(cli.cli, ["set-description", "--description", "Some description"])
    assert result.exit_code != 0
    assert "No current role" in result.output


def test_set_scopes_command(monkeypatch):
    """Test set-scopes command changes the assignable scopes."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("TestRole", "Test role")
    cli.role_manager.current_role = current
    
    # Change scopes
    result = runner.invoke(cli.cli, ["set-scopes", "--scopes", "/, /subscriptions/sub-123"])
    assert result.exit_code == 0
    assert "Assignable scopes changed" in result.output
    assert "/" in result.output
    assert "/subscriptions/sub-123" in result.output
    
    # Verify it was actually changed
    assert cli.role_manager.current_role.AssignableScopes == ["/", "/subscriptions/sub-123"]


def test_set_scopes_single(monkeypatch):
    """Test set-scopes with a single scope."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("TestRole", "Test role")
    cli.role_manager.current_role = current
    
    # Change scopes to single scope
    result = runner.invoke(cli.cli, ["set-scopes", "--scopes", "/subscriptions/sub-456"])
    assert result.exit_code == 0
    assert "/subscriptions/sub-456" in result.output
    
    # Verify it was actually changed
    assert cli.role_manager.current_role.AssignableScopes == ["/subscriptions/sub-456"]


def test_set_scopes_no_role(monkeypatch):
    """Test set-scopes fails when no role is loaded."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    cli.role_manager.current_role = None
    
    result = runner.invoke(cli.cli, ["set-scopes", "--scopes", "/"])
    assert result.exit_code != 0
    assert "No current role" in result.output


def test_set_multiple_properties(monkeypatch):
    """Test setting multiple properties sequentially."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("Original", "Original description")
    cli.role_manager.current_role = current
    
    # Change name
    result1 = runner.invoke(cli.cli, ["set-name", "--name", "Updated"])
    assert result1.exit_code == 0
    
    # Change description
    result2 = runner.invoke(cli.cli, ["set-description", "--description", "New description"])
    assert result2.exit_code == 0
    
    # Change scopes
    result3 = runner.invoke(cli.cli, ["set-scopes", "--scopes", "/, /subscriptions/abc, /subscriptions/def"])
    assert result3.exit_code == 0
    
    # Verify all changes
    assert cli.role_manager.current_role.Name == "Updated"
    assert cli.role_manager.current_role.Description == "New description"
    assert cli.role_manager.current_role.AssignableScopes == ["/", "/subscriptions/abc", "/subscriptions/def"]


def test_set_scopes_with_whitespace(monkeypatch):
    """Test set-scopes handles whitespace correctly."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("TestRole", "Test role")
    cli.role_manager.current_role = current
    
    # Set scopes with extra whitespace
    result = runner.invoke(cli.cli, ["set-scopes", "--scopes", " / , /subscriptions/sub-123 , /subscriptions/sub-456 "])
    assert result.exit_code == 0
    
    # Verify scopes are trimmed correctly
    assert cli.role_manager.current_role.AssignableScopes == ["/", "/subscriptions/sub-123", "/subscriptions/sub-456"]


def test_properties_persist_after_modification(monkeypatch):
    """Test that modified properties persist when viewing the role."""
    runner = CliRunner()
    
    monkeypatch.setattr(cli, "role_manager", cli.role_manager)
    
    # Create a role
    current = cli.role_manager.create_role("TestRole", "Test description")
    cli.role_manager.current_role = current
    
    # Modify properties
    runner.invoke(cli.cli, ["set-name", "--name", "ModifiedName"])
    runner.invoke(cli.cli, ["set-description", "--description", "Modified description"])
    runner.invoke(cli.cli, ["set-scopes", "--scopes", "/subscriptions/test"])
    
    # View the role - properties should be updated
    result = runner.invoke(cli.cli, ["view"])
    assert result.exit_code == 0
    assert "ModifiedName" in result.output
    assert "Modified description" in result.output
