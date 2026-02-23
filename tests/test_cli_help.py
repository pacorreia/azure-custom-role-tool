from click.testing import CliRunner

from azure_custom_role_tool.cli import cli


def test_cli_load_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["load", "--help"])

    assert result.exit_code == 0
    assert "Load an existing role" in result.output
    assert "--name" in result.output
