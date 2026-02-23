"""Tests for role deletion functionality."""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner
from azure_custom_role_tool.cli import cli
from azure_custom_role_tool.role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition


class TestDeleteRoleManager:
    """Test RoleManager.delete_role() method."""
    
    def test_delete_existing_role(self):
        """Test deleting an existing role file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create a role
            role = manager.create_role("TestRole", "Test description")
            manager.save_to_file(role, roles_dir / "TestRole.json")
            
            # Verify it exists
            assert (roles_dir / "TestRole.json").exists()
            
            # Delete it
            deleted = manager.delete_role("TestRole", roles_dir)
            
            # Verify deletion
            assert deleted is True
            assert not (roles_dir / "TestRole.json").exists()
    
    def test_delete_nonexistent_role(self):
        """Test deleting a non-existent role returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            deleted = manager.delete_role("NonExistent", roles_dir)
            assert deleted is False
    
    def test_delete_role_with_json_extension(self):
        """Test deleting a role using filename with .json extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create a role
            role = manager.create_role("TestRole", "Test description")
            manager.save_to_file(role, roles_dir / "TestRole.json")
            
            # Delete using name with .json extension
            deleted = manager.delete_role("TestRole.json", roles_dir)
            
            assert deleted is True
            assert not (roles_dir / "TestRole.json").exists()
    
    def test_delete_role_nonexistent_directory(self):
        """Test deleting from non-existent directory raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir) / "nonexistent"
            manager = RoleManager()
            
            with pytest.raises(ValueError, match="Roles directory does not exist"):
                manager.delete_role("TestRole", roles_dir)


class TestDeleteRoleCommand:
    """Test delete command in CLI."""
    
    def test_delete_role_with_confirmation(self):
        """Test deleting a role with user confirmation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create a role
            role = manager.create_role("TestRole", "Test description")
            manager.save_to_file(role, roles_dir / "TestRole.json")
            
            # Verify it exists
            assert (roles_dir / "TestRole.json").exists()
            
            # Delete with confirmation (answer 'y')
            result = runner.invoke(cli, [
                "delete", "TestRole",
                "--role-dir", str(roles_dir)
            ], input="y\n")
            
            # Check result
            assert result.exit_code == 0
            assert "Deleted role" in result.output
            assert not (roles_dir / "TestRole.json").exists()
    
    def test_delete_role_cancel_confirmation(self):
        """Test cancelling role deletion."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create a role
            role = manager.create_role("TestRole", "Test description")
            manager.save_to_file(role, roles_dir / "TestRole.json")
            
            # Delete with cancelled confirmation (answer 'n')
            result = runner.invoke(cli, [
                "delete", "TestRole",
                "--role-dir", str(roles_dir)
            ], input="n\n")
            
            # Check result
            assert result.exit_code == 0
            assert "Deletion cancelled" in result.output
            assert (roles_dir / "TestRole.json").exists()  # Role still exists
    
    def test_delete_role_force_flag(self):
        """Test deleting a role with --force flag skips confirmation."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create a role
            role = manager.create_role("TestRole", "Test description")
            manager.save_to_file(role, roles_dir / "TestRole.json")
            
            # Delete with force flag (no confirmation needed)
            result = runner.invoke(cli, [
                "delete", "TestRole",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            # Check result
            assert result.exit_code == 0
            assert "Deleted role" in result.output
            assert not (roles_dir / "TestRole.json").exists()
    
    def test_delete_nonexistent_role_error(self):
        """Test deleting a non-existent role shows error."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            
            # Try to delete non-existent role
            result = runner.invoke(cli, [
                "delete", "NonExistent",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            # Check result
            assert result.exit_code == 1
            assert "Role not found" in result.output
    
    def test_delete_multiple_roles(self):
        """Test deleting multiple roles sequentially."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create multiple roles
            for i in range(3):
                role = manager.create_role(f"TestRole{i}", f"Test description {i}")
                manager.save_to_file(role, roles_dir / f"TestRole{i}.json")
            
            # List initially
            result = runner.invoke(cli, ["list", "--role-dir", str(roles_dir)])
            assert "TestRole0" in result.output
            assert "TestRole1" in result.output
            assert "TestRole2" in result.output
            
            # Delete first role
            result = runner.invoke(cli, [
                "delete", "TestRole0",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            assert result.exit_code == 0
            assert "Deleted role" in result.output
            
            # Verify deletion
            result = runner.invoke(cli, ["list", "--role-dir", str(roles_dir)])
            assert "TestRole0" not in result.output
            assert "TestRole1" in result.output
            assert "TestRole2" in result.output
    
    def test_delete_by_filter_single_match(self):
        """Test deleting a single role using filter pattern."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create multiple roles
            roles_data = [
                ("test-role-001", "First test role"),
                ("prod-role-001", "Production role"),
                ("test-role-002", "Second test role"),
            ]
            
            for name, desc in roles_data:
                role = manager.create_role(name, desc)
                manager.save_to_file(role, roles_dir / f"{name}.json")
            
            # Delete using filter that matches one role
            result = runner.invoke(cli, [
                "delete", "--filter", "prod-*",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            assert result.exit_code == 0
            assert "Deleted" in result.output and "1" in result.output
            
            # Verify deletion
            result = runner.invoke(cli, ["list", "--role-dir", str(roles_dir)])
            assert "prod-role-001" not in result.output
            assert "test-role-001" in result.output
            assert "test-role-002" in result.output
    
    def test_delete_by_filter_multiple_matches(self):
        """Test deleting multiple roles using filter pattern."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create multiple roles with matching patterns
            roles_data = [
                ("test-role-001", "First test role"),
                ("test-role-002", "Second test role"),
                ("prod-role-001", "Production role"),
            ]
            
            for name, desc in roles_data:
                role = manager.create_role(name, desc)
                manager.save_to_file(role, roles_dir / f"{name}.json")
            
            # Delete using filter that matches multiple roles
            result = runner.invoke(cli, [
                "delete", "--filter", "test-*",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            assert result.exit_code == 0
            assert "Deleted" in result.output and "2" in result.output
            
            # Verify deletion
            result = runner.invoke(cli, ["list", "--role-dir", str(roles_dir)])
            assert "test-role-001" not in result.output
            assert "test-role-002" not in result.output
            assert "prod-role-001" in result.output
    
    def test_delete_by_filter_no_matches(self):
        """Test deleting with filter that matches no roles."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create roles
            role = manager.create_role("my-role", "Test role")
            manager.save_to_file(role, roles_dir / "my-role.json")
            
            # Try to delete using filter that matches nothing
            result = runner.invoke(cli, [
                "delete", "--filter", "nonexistent-*",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            assert result.exit_code == 1
            assert "No roles match" in result.output
    
    def test_delete_filter_requires_one_argument(self):
        """Test that delete requires either name or filter, not both."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            
            # Try delete with neither name nor filter
            result = runner.invoke(cli, [
                "delete",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            assert result.exit_code == 1
            assert "Provide either a role NAME or use --filter" in result.output
    
    def test_delete_filter_mutual_exclusion(self):
        """Test that name and filter cannot be used together."""
        runner = CliRunner()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            roles_dir = Path(tmpdir)
            manager = RoleManager(roles_dir)
            
            # Create a role
            role = manager.create_role("test-role", "Test")
            manager.save_to_file(role, roles_dir / "test-role.json")
            
            # Try delete with both name and filter
            result = runner.invoke(cli, [
                "delete", "test-role",
                "--filter", "test-*",
                "--role-dir", str(roles_dir),
                "--force"
            ])
            
            assert result.exit_code == 1
            assert "Provide either NAME or --filter, not both" in result.output

