"""Tests for version information."""

from click.testing import CliRunner

from azure_custom_role_tool import __version__
from azure_custom_role_tool.cli import cli


def test_version_defined():
    """Test that __version__ is defined."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format():
    """Test that version follows semantic versioning format."""
    parts = __version__.split(".")
    assert len(parts) >= 2, "Version should have at least major.minor"
    for part in parts:
        assert (
            part.isdigit() or "-" in part
        ), f"Version part '{part}' should be numeric or contain pre-release info"


def test_cli_version_option():
    """Test that --version flag works in CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output
    assert "azure-custom-role-tool" in result.output


def test_cli_version_option_with_command():
    """Test that --version takes precedence over commands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version", "create"])

    assert result.exit_code == 0
    assert __version__ in result.output
