from types import SimpleNamespace

from azure_custom_role_tool import cli


def test_group_by_namespace():
    permissions = [
        "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Storage/storageAccounts/listKeys/action",
        "Microsoft.Compute/virtualMachines/read",
        "CustomProvider/action",
    ]

    grouped = cli._group_by_namespace(permissions)

    assert "Microsoft.Storage/storageAccounts" in grouped
    assert "Microsoft.Compute/virtualMachines" in grouped
    assert "CustomProvider/action" in grouped


def test_print_grouped_permissions_capture():
    permissions = [
        "Microsoft.Storage/storageAccounts/read",
        "Microsoft.Storage/storageAccounts/listKeys/action",
    ]

    with cli.term.capture() as capture:
        cli._print_grouped_permissions("Actions", permissions, show_all=True, limit=10)

    output = capture.get()
    assert "Actions" in output
    assert "Microsoft.Storage/storageAccounts" in output


def test_run_shell_command_success(monkeypatch):
    result = SimpleNamespace(stdout="ok\n", stderr="", returncode=0)

    def fake_run(*args, **kwargs):
        return result

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with cli.term.capture() as capture:
        cli.run_shell_command("echo ok")

    output = capture.get()
    assert "ok" in output


def test_run_shell_command_error(monkeypatch):
    result = SimpleNamespace(stdout="", stderr="error\n", returncode=2)

    def fake_run(*args, **kwargs):
        return result

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with cli.term.capture() as capture:
        cli.run_shell_command("bad")

    output = capture.get()
    assert "error" in output
    assert "exited with code 2" in output


def test_show_help_and_command_help():
    with cli.term.capture() as capture:
        cli.show_help()

    output = capture.get()
    assert "Available Commands" in output

    with cli.term.capture() as capture:
        cli.show_command_help("load")

    output = capture.get()
    assert "Help for 'load'" in output

    with cli.term.capture() as capture:
        cli.show_command_help("unknown")

    output = capture.get()
    assert "Unknown command" in output


def test_interactive_mode_commands(monkeypatch):
    commands = iter(
        [
            "help",
            "help load",
            "!echo hi",
            "shell pwd",
            "exit",
        ]
    )

    def fake_prompt(*args, **kwargs):
        return next(commands)

    called = {"count": 0}

    def fake_shell(command):
        called["count"] += 1

    monkeypatch.setattr(cli, "prompt", fake_prompt)
    monkeypatch.setattr(cli, "run_shell_command", fake_shell)

    with cli.term.capture() as capture:
        cli.interactive_mode()

    output = capture.get()
    assert "Available Commands" in output
    assert called["count"] == 2
