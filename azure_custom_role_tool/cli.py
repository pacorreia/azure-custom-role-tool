#!/usr/bin/env python
"""
Azure Custom Role Designer CLI

A powerful tool for platform engineers to create, update, and manage Azure custom roles.
"""

import sys
import os
import shlex
import subprocess
import fnmatch
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import WordCompleter

from .role_manager import RoleManager, AzureRoleDefinition, PermissionDefinition
from .permission_filter import PermissionFilter, PermissionType
from .azure_client import AzureClient
from . import __version__

term = Console()
role_manager = RoleManager()

# Track current subscription
current_subscription = None
current_role_file_path: Optional[Path] = None

PROMPT_HISTORY_FILE = Path.home() / ".azure-custom-role-tool-history"
PROMPT_HISTORY = FileHistory(str(PROMPT_HISTORY_FILE))
PROMPT_STYLE = Style.from_dict({"prompt": "#00aa00 bold"})

# Create a PromptSession with Tab-only completion (no auto-show dropdown)
PROMPT_SESSION = PromptSession(
    history=PROMPT_HISTORY,
    style=PROMPT_STYLE,
    complete_style="readline",  # Tab-only completion
    complete_while_typing=False,  # Don't show completion menu as you type
)


# ============================================================================
# HELPER FUNCTIONS - Output Formatting & Validation
# ============================================================================


def error(message: str, exit_code: int = 1):
    """Print error message and exit."""
    term.print(f"[red]✗ Error:[/red] {message}")
    sys.exit(exit_code)


def success(message: str):
    """Print success message."""
    term.print(f"[green]✓[/green] {message}")


def warn(message: str):
    """Print warning message."""
    term.print(f"[yellow]⚠[/yellow] {message}")


def info(message: str):
    """Print info message."""
    term.print(f"[cyan]ℹ[/cyan] {message}")


def _prompt_input(label: str, completer=None) -> str:
    """Read input with shared prompt style/history and optional auto-complete.
    
    Uses readline-style Tab-only completion (no popup).
    
    Args:
        label: Prompt label text
        completer: Optional prompt_toolkit completer for auto-complete
    
    Returns:
        User input
    """
    return PROMPT_SESSION.prompt(label, completer=completer)


def prompt_text(label: str, default: Optional[str] = None) -> str:
    """Read a text value using prompt_toolkit when interactive.

    Falls back to click.prompt for non-interactive environments (e.g., tests).
    """
    if sys.stdin.isatty() and sys.stdout.isatty():
        prompt_label = f"{label}: "
        if default is not None:
            prompt_label = f"{label} [{default}]: "

        try:
            value = _prompt_input(prompt_label).strip()
        except (KeyboardInterrupt, EOFError):
            error("Input cancelled")

        if value:
            return value
        if default is not None:
            return default
        error(f"{label} cannot be empty")

    return click.prompt(label, default=default)


def prompt_confirm(message: str, default: bool = False) -> bool:
    """Read yes/no confirmation using prompt_toolkit when interactive.

    Falls back to click.confirm for non-interactive environments (e.g., tests).
    """
    if sys.stdin.isatty() and sys.stdout.isatty():
        default_hint = "Y/n" if default else "y/N"

        while True:
            try:
                response = _prompt_input(f"{message} [{default_hint}]: ").strip()
            except (KeyboardInterrupt, EOFError):
                term.print("[dim]Deletion cancelled[/dim]")
                return False

            if not response:
                return default

            normalized = response.lower()
            if normalized in {"y", "yes"}:
                return True
            if normalized in {"n", "no"}:
                return False

            term.print("[yellow]Please answer 'y' or 'n'.[/yellow]")

    return click.confirm(message, default=default)


def resolve_single_argument(
    option_value: Optional[str],
    positional_value: Optional[str],
    option_name: str,
    description: str,
) -> str:
    """Resolve a command's primary argument from option or positional input."""
    if option_value and positional_value and option_value != positional_value:
        error(
            f"Conflicting values provided. Use either --{option_name} or positional {description}, not both."
        )

    value = option_value or positional_value
    if not value:
        error(f"Missing {description}. Use --{option_name} or pass it as positional argument.")

    return value


def require_current_role() -> AzureRoleDefinition:
    """Validate that a role is loaded, return it or exit.

    Raises:
        SystemExit: If no current role is loaded
    """
    if role_manager.current_role is None:
        error("No current role. Create or load a role first.")
    return role_manager.current_role


def require_subscription(subscription_id: Optional[str] = None) -> str:
    """Validate that a subscription is available.

    Args:
        subscription_id: Optional subscription ID to use instead of current

    Returns:
        str: The effective subscription ID

    Raises:
        SystemExit: If no subscription is available
    """
    effective_id = subscription_id or current_subscription
    if not effective_id:
        error(
            "No subscription selected. Use 'use-subscription' or provide --subscription-id"
        )
    return effective_id


def _set_current_role(
    role: AzureRoleDefinition, source_path: Optional[Path] = None
) -> None:
    """Set current role and track its backing file path when available."""
    global current_role_file_path
    role_manager.current_role = role
    current_role_file_path = Path(source_path) if source_path else None


def _load_azure_role(
    name: str, subscription_id: Optional[str]
) -> Optional[AzureRoleDefinition]:
    """Load a role from Azure by name.

    Args:
        name: Role name to search for (case-insensitive)
        subscription_id: Azure subscription ID

    Returns:
        AzureRoleDefinition if found, None otherwise
    """
    if not subscription_id:
        return None

    try:
        azure_client = AzureClient(subscription_id=subscription_id)
        all_roles = azure_client.list_all_roles()

        # Find role by name (case-insensitive)
        matching_roles = [r for r in all_roles if r["name"].lower() == name.lower()]

        if matching_roles:
            return _convert_azure_role_to_local(matching_roles[0])
    except Exception:
        pass

    return None


# ============================================================================


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="azure-custom-role-tool")
@click.pass_context
def cli(ctx):
    """Azure Custom Role Designer - Create and manage Azure custom roles."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@cli.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Name of the custom role")
@click.option("--description", default=None, help="Role description")
@click.pass_context
def create(
    ctx,
    name_arg: Optional[str],
    name: Optional[str],
    description: Optional[str],
):
    """Create a new custom role from scratch."""
    try:
        global current_role_file_path
        if name or name_arg:
            name = resolve_single_argument(name, name_arg, "name", "role name")
        else:
            name = prompt_text("Role name")

        if description is None:
            description = ""

        role = role_manager.create_role(name, description)
        current_role_file_path = None
        success(f"Created new role: [bold]{role.Name}[/bold]")
        term.print(f"  Description: {role.Description}")
        term.print(f"  ID: {role.Id}")
        term.print("\nUse 'merge' command to add permissions from existing roles.")
    except Exception as e:
        error(str(e))


@cli.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Role name (local or Azure)")
@click.option(
    "--role-dir",
    type=click.Path(exists=True),
    default=None,
    help="Custom role directory",
)
@click.option(
    "--subscription-id", default=None, help="Azure subscription ID for fallback"
)
def load(
    name_arg: Optional[str],
    name: Optional[str],
    role_dir: Optional[str],
    subscription_id: Optional[str],
):
    """Load an existing role from file, local storage, or Azure.

    Tries to load in this order:
    1. Direct file path if provided
    2. Local role by name
    3. Azure role by name (if subscription available)
    """
    try:
        name = resolve_single_argument(name, name_arg, "name", "role name")
        role = None
        source_path = None

        # Check if name is a direct file path
        name_path = Path(name)
        if name_path.exists() and name_path.is_file():
            # Load directly from the file path
            role = role_manager.load_from_file(name_path)
            source_path = name_path
            success(f"Loaded role from file: [bold]{role.Name}[/bold]")
        else:
            # Try loading from local storage
            try:
                role_dir_path = Path(role_dir) if role_dir else None
                role = role_manager.load_from_name(name, role_dir_path)
                resolved_role_dir = role_dir_path or role_manager.roles_dir
                source_path = (
                    resolved_role_dir / name
                    if name.endswith(".json")
                    else resolved_role_dir / f"{name}.json"
                )
                success(f"Loaded role from local storage: [bold]{role.Name}[/bold]")
            except FileNotFoundError:
                # Fall back to Azure
                effective_subscription_id = subscription_id or current_subscription
                if effective_subscription_id:
                    with term.status(
                        "[bold blue]Searching Azure for role...[/bold blue]"
                    ):
                        role = _load_role_from_azure_by_name(
                            name, effective_subscription_id
                        )

                    if role:
                        success(f"Loaded role from Azure: [bold]{role.Name}[/bold]")

        if not role:
            error(f"Role not found (local or Azure): {name}")

        # Set as current role
        _set_current_role(role, source_path=source_path)
        print_role_summary(role)

    except Exception as e:
        error(str(e))


def _convert_azure_role_to_local(azure_role: dict) -> AzureRoleDefinition:
    """Convert Azure role API response to local AzureRoleDefinition.

    Args:
        azure_role: Role dict from Azure API

    Returns:
        AzureRoleDefinition instance
    """
    permissions = []
    for perm_block in azure_role.get("permissions", []):
        permissions.append(
            PermissionDefinition(
                Actions=perm_block.get("actions", []),
                NotActions=perm_block.get("not_actions", []),
                DataActions=perm_block.get("data_actions", []),
                NotDataActions=perm_block.get("not_data_actions", []),
            )
        )

    return AzureRoleDefinition(
        Name=azure_role["name"],
        Description=azure_role.get("description", ""),
        IsCustom=azure_role.get("type") != "Microsoft.Authorization/roleDefinitions"
        or "/" not in azure_role.get("assignable_scopes", []),
        Type=azure_role.get("type", "CustomRole"),
        Permissions=permissions,
        AssignableScopes=azure_role.get("assignable_scopes", ["/"]),
        Id=azure_role.get("id"),
    )


def _load_role_from_azure_by_name(
    name: str, subscription_id: Optional[str]
) -> Optional[AzureRoleDefinition]:
    """Try to load a role from Azure by name.

    Args:
        name: Role name to search for (case-insensitive)
        subscription_id: Azure subscription ID

    Returns:
        AzureRoleDefinition if found, None otherwise
    """
    if not subscription_id:
        return None

    try:
        azure_client = AzureClient(subscription_id=subscription_id)
        all_roles = azure_client.list_all_roles()

        # Find role by name (case-insensitive)
        matching_roles = [r for r in all_roles if r["name"].lower() == name.lower()]

        if matching_roles:
            return _convert_azure_role_to_local(matching_roles[0])
    except Exception:
        pass

    return None


def _collect_permission_matches(
    all_roles: list[dict], permission_filter: str
) -> dict[str, set[str]]:
    """Collect permission matches and the roles they belong to."""
    pf = PermissionFilter()
    matched_permissions: dict[str, set[str]] = {}

    for role in all_roles:
        role_name = role.get("name", "Unknown")
        for perm_block in role.get("permissions", []):
            actions = perm_block.get("actions", [])
            data_actions = perm_block.get("data_actions", [])

            for permission in pf.filter_by_string(actions, permission_filter):
                if permission not in matched_permissions:
                    matched_permissions[permission] = set()
                matched_permissions[permission].add(role_name)

            for permission in pf.filter_by_string(data_actions, permission_filter):
                if permission not in matched_permissions:
                    matched_permissions[permission] = set()
                matched_permissions[permission].add(role_name)

    return matched_permissions


def _collect_permission_matches_typed(
    all_roles: list[dict], permission_filter: str
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Collect matched control/data permissions and the roles they belong to."""
    pf = PermissionFilter()
    matched_actions: dict[str, set[str]] = {}
    matched_data_actions: dict[str, set[str]] = {}

    for role in all_roles:
        role_name = role.get("name", "Unknown")
        for perm_block in role.get("permissions", []):
            actions = perm_block.get("actions", [])
            data_actions = perm_block.get("data_actions", [])

            for permission in pf.filter_by_string(actions, permission_filter):
                if permission not in matched_actions:
                    matched_actions[permission] = set()
                matched_actions[permission].add(role_name)

            for permission in pf.filter_by_string(data_actions, permission_filter):
                if permission not in matched_data_actions:
                    matched_data_actions[permission] = set()
                matched_data_actions[permission].add(role_name)

    return matched_actions, matched_data_actions


def _import_permissions_into_current_role(
    matched_actions: dict[str, set[str]], matched_data_actions: dict[str, set[str]]
) -> tuple[int, int]:
    """Import matched permissions into the current loaded role.

    Returns:
        Tuple with number of newly added actions and data actions.
    """
    role = require_current_role()

    extracted = PermissionFilter.extract_actions(role.Permissions)

    current_actions = set(extracted["actions"])
    current_not_actions = set(extracted["not_actions"])
    current_data_actions = set(extracted["data_actions"])
    current_not_data_actions = set(extracted["not_data_actions"])

    incoming_actions = set(matched_actions.keys())
    incoming_data_actions = set(matched_data_actions.keys())

    added_actions = len(incoming_actions - current_actions)
    added_data_actions = len(incoming_data_actions - current_data_actions)

    merged_actions = sorted(current_actions | incoming_actions)
    merged_data_actions = sorted(current_data_actions | incoming_data_actions)

    role.Permissions = [
        PermissionDefinition(
            Actions=merged_actions,
            NotActions=sorted(current_not_actions),
            DataActions=merged_data_actions,
            NotDataActions=sorted(current_not_data_actions),
        )
    ]

    return added_actions, added_data_actions


def _print_permission_search_results(
    matched_permissions: dict[str, set[str]], permission_filter: str
):
    """Render permission-centric search results with role context."""
    if not matched_permissions:
        term.print(f"No permissions found matching: {permission_filter}")
        return

    table = Table(title=f"Permissions matching '{permission_filter}'")
    table.add_column("Permission", style="cyan", no_wrap=False)
    table.add_column("Roles", style="green")
    table.add_column("Example Roles", style="yellow", no_wrap=False)

    for permission in sorted(matched_permissions.keys()):
        roles = sorted(matched_permissions[permission])
        if len(roles) > 3:
            role_preview = ", ".join(roles[:3]) + f" (+{len(roles) - 3} more)"
        else:
            role_preview = ", ".join(roles)
        table.add_row(permission, str(len(roles)), role_preview)

    term.print(table)
    term.print("\n[bold]Full matched permissions:[/bold]")
    for permission in sorted(matched_permissions.keys()):
        term.print(f"  • {permission}", soft_wrap=True)
    term.print(
        f"Found {len(matched_permissions)} unique permission(s) matching '{permission_filter}'."
    )


@cli.command("load-azure")
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Role name to load from Azure")
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def load_azure(name_arg: Optional[str], name: Optional[str], subscription_id: Optional[str]):
    """Load a role from Azure and set as current role."""
    try:
        name = resolve_single_argument(name, name_arg, "name", "role name")
        # Use provided subscription ID or fall back to current subscription
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Fetching role from Azure...[/bold blue]"):
            role = _load_role_from_azure_by_name(name, effective_subscription_id)

        if not role:
            error(f"Role not found in Azure: {name}")

        # Set as current role
        _set_current_role(role, source_path=None)

        success(f"Loaded role from Azure: [bold]{role.Name}[/bold]")
        print_role_summary(role)

    except Exception as e:
        error(str(e))


@cli.command()
@click.argument("roles_arg", required=False)
@click.option(
    "--roles", default=None, help="Comma-separated list of role names to merge"
)
@click.option(
    "--filter",
    default=None,
    help="Filter permissions by string pattern (e.g., 'Storage%', '%delete'). '*' is literal.",
)
@click.option(
    "--filter-type",
    type=click.Choice(["control", "data"]),
    default=None,
    help="Filter by permission type",
)
def merge(
    roles_arg: Optional[str],
    roles: Optional[str],
    filter: Optional[str],
    filter_type: Optional[str],
):
    """Merge permissions from multiple roles into the current role.

    Roles can be loaded from local storage or fetched from Azure if not found locally.
    """
    try:
        roles = resolve_single_argument(roles, roles_arg, "roles", "role list")
        require_current_role()

        role_names = [r.strip() for r in roles.split(",")]
        source_roles = []
        failed_roles = []

        for role_name in role_names:
            role = None

            # Try loading from local storage first (without setting as current)
            try:
                role = role_manager.load_from_name(role_name, set_as_current=False)
                source_roles.append(role)
                continue
            except FileNotFoundError:
                pass

            # Fall back to Azure if local not found
            role = _load_role_from_azure_by_name(role_name, current_subscription)
            if role:
                source_roles.append(role)
                info(f"Loaded '{role_name}' from Azure")
            else:
                failed_roles.append(role_name)

        if failed_roles:
            warn(f"Roles not found (local or Azure): {', '.join(failed_roles)}")

        if not source_roles:
            error("No source roles could be loaded")

        type_filter = PermissionType(filter_type) if filter_type else None

        updated = role_manager.merge_roles(
            source_roles, string_filter=filter, type_filter=type_filter
        )

        success(f"Merged permissions from {len(source_roles)} role(s)")
        print_role_summary(updated)

    except Exception as e:
        error(str(e))


@cli.command()
@click.option("--filter", default=None, help="Filter permissions by string pattern")
@click.option(
    "--filter-type",
    type=click.Choice(["control", "data"]),
    default=None,
    help="Filter by permission type",
)
def remove(filter: Optional[str], filter_type: Optional[str]):
    """Remove permissions from the current role."""
    try:
        require_current_role()

        if not filter and not filter_type:
            error("Specify --filter and/or --filter-type")

        type_filter = PermissionType(filter_type) if filter_type else None

        updated = role_manager.remove_permissions(
            string_filter=filter, type_filter=type_filter
        )

        success("Removed permissions")
        print_role_summary(updated)

    except Exception as e:
        error(str(e))


@cli.command("set-name")
@click.option("--name", required=True, help="New role name")
def set_name(name: str):
    """Change the current role's name."""
    try:
        role = require_current_role()

        old_name = role.Name
        role.Name = name

        success(f"Role name changed: [bold]{old_name}[/bold] → [bold]{name}[/bold]")

    except Exception as e:
        error(str(e))


@cli.command("set-description")
@click.option("--description", required=True, help="New description")
def set_description(description: str):
    """Change the current role's description."""
    try:
        role = require_current_role()

        old_description = role.Description
        role.Description = description

        success("Description changed:")
        term.print(f"  [yellow]Old:[/yellow] {old_description}")
        term.print(f"  [yellow]New:[/yellow] {description}")

    except Exception as e:
        error(str(e))


@cli.command("set-scopes")
@click.option(
    "--scopes",
    required=True,
    help="Comma-separated list of assignable scopes (e.g., '/, /subscriptions/sub-123')",
)
def set_scopes(scopes: str):
    """Change the current role's assignable scopes."""
    try:
        role = require_current_role()

        scope_list = [s.strip() for s in scopes.split(",")]
        old_scopes = role.AssignableScopes
        role.AssignableScopes = scope_list

        success("Assignable scopes changed:")
        term.print(f"  [yellow]Old:[/yellow] {', '.join(old_scopes)}")
        term.print(f"  [yellow]New:[/yellow] {', '.join(scope_list)}")

    except Exception as e:
        error(str(e))


@cli.command("list")
@click.option("--name", default=None, help="Show specific role")
@click.option(
    "--role-dir",
    type=click.Path(exists=True),
    default=None,
    help="Custom role directory",
)
def list_cmd(name: Optional[str], role_dir: Optional[str]):
    """List available roles or show role details."""
    try:
        role_dir_path = Path(role_dir) if role_dir else None

        if name:
            # Show specific role
            role = role_manager.load_from_name(name, role_dir_path)
            print_role_details(role)
        else:
            # List all roles
            roles = role_manager.list_roles(role_dir_path)

            if not roles:
                term.print("No roles found")
                return

            table = Table(title="Available Roles")
            table.add_column("Role Name", style="cyan")
            table.add_column("File", style="magenta")

            for role_name in roles:
                table.add_row(role_name, f"{role_name}.json")

            term.print(table)

    except Exception as e:
        error(str(e))


@cli.command("delete")
@click.argument("name", required=False, default=None)
@click.option(
    "--role-dir",
    type=click.Path(exists=True),
    default=None,
    help="Custom role directory",
)
@click.option(
    "--filter",
    default=None,
    help="Filter pattern for bulk deletion (e.g., '*test*', 'local-*')",
)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def delete_role_cmd(
    name: Optional[str], role_dir: Optional[str], filter: Optional[str], force: bool
):
    """Delete a local role or roles matching a filter pattern."""
    try:
        role_dir_path = Path(role_dir) if role_dir else role_manager.roles_dir

        # Validate: either name or filter must be provided
        if not name and not filter:
            error("Provide either a role NAME or use --filter for pattern matching")

        if name and filter:
            error("Provide either NAME or --filter, not both")

        # Single role deletion
        if name:
            # First, check if role exists before asking for confirmation
            role_file = role_dir_path / (
                name if name.endswith(".json") else f"{name}.json"
            )
            if not role_file.exists():
                error(f"Role not found: {name}")

            # Confirm deletion unless --force flag is used
            if not force:
                warn(f"Delete role '{name}'?")
                if prompt_confirm("Are you sure?", default=False):
                    pass
                else:
                    term.print("[dim]Deletion cancelled[/dim]")
                    return

            deleted = role_manager.delete_role(name, role_dir_path)

            if deleted:
                success(f"Deleted role '[bold]{name}[/bold]'")
            else:
                error(f"Failed to delete role: {name}")

        # Filter-based bulk deletion
        else:
            # Get all available roles
            available_roles = role_manager.list_roles(role_dir_path)

            if not available_roles:
                error("No roles found")

            # Find matching roles
            matching_roles = [
                r for r in available_roles if fnmatch.fnmatch(r.lower(), filter.lower())
            ]

            if not matching_roles:
                error(f"No roles match filter: {filter}")

            # Show matching roles and ask for confirmation
            term.print(
                f"\n[yellow]Found {len(matching_roles)} role(s) matching filter '[bold]{filter}[/bold]':[/yellow]"
            )
            for role in matching_roles:
                term.print(f"  • {role}")

            # Confirm deletion unless --force flag is used
            if not force:
                term.print()
                if not prompt_confirm(
                    f"Delete {len(matching_roles)} role(s)?", default=False
                ):
                    term.print("[dim]Deletion cancelled[/dim]")
                    return

            # Delete all matching roles
            deleted_count = 0
            for role in matching_roles:
                if role_manager.delete_role(role, role_dir_path):
                    deleted_count += 1

            if deleted_count == len(matching_roles):
                success(f"Deleted [bold]{deleted_count}[/bold] role(s)")
            else:
                warn(
                    f"Deleted [bold]{deleted_count}[/bold] of [bold]{len(matching_roles)}[/bold] role(s)"
                )

    except Exception as e:
        error(str(e))


@cli.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Output filename (without .json)")
@click.option("--output", type=click.Path(), default=None, help="Custom output path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def save(name_arg: Optional[str], name: Optional[str], output: Optional[str], overwrite: bool):
    """Save current role (quick-save by default, save-as when name/path is provided)."""
    try:
        global current_role_file_path
        role = require_current_role()
        prompt_name: Optional[str] = None
        requested_name = name or name_arg

        if name and name_arg and name != name_arg:
            error(
                "Conflicting values provided. Use either --name or positional output filename, not both."
            )

        if output and not requested_name:
            requested_name = role.Name

        if requested_name:
            if output:
                file_path = Path(output)
            else:
                file_path = (
                    role_manager.roles_dir
                    / f"{requested_name.lower().replace(' ', '-')}.json"
                )

            saved_path = role_manager.save_to_file(role, file_path, overwrite=overwrite)
            current_role_file_path = saved_path
            success(f"Role saved to: [bold]{saved_path}[/bold]")
            return

        if current_role_file_path:
            saved_path = role_manager.save_to_file(
                role, current_role_file_path, overwrite=True
            )
            success(f"Role quick-saved to: [bold]{saved_path}[/bold]")
            return

        prompt_name = prompt_text("Output filename")
        file_path = role_manager.roles_dir / f"{prompt_name.lower().replace(' ', '-')}.json"
        saved_path = role_manager.save_to_file(role, file_path, overwrite=overwrite)
        current_role_file_path = saved_path
        success(f"Role saved to: [bold]{saved_path}[/bold]")

    except FileExistsError:
        error(
            f"File already exists: {output or requested_name or prompt_name}. Use --overwrite to replace",
            exit_code=1,
        )
    except Exception as e:
        error(str(e))


@cli.command()
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Role name")
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def publish(name_arg: Optional[str], name: Optional[str], subscription_id: Optional[str]):
    """Publish the current role to Azure."""
    try:
        name = resolve_single_argument(name, name_arg, "name", "role name")
        role = require_current_role()
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Publishing to Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=effective_subscription_id)
            result = azure_client.create_custom_role(role)

        success("Role published to Azure")
        term.print(f"  ID: {result['id']}")
        term.print(f"  Name: {result['name']}")

    except Exception as e:
        error(str(e))


@cli.command("list-azure")
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def list_azure(subscription_id: Optional[str]):
    """List custom roles in Azure subscription."""
    try:
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Fetching roles from Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=effective_subscription_id)
            roles = azure_client.list_custom_roles()

        if not roles:
            term.print("No custom roles found in subscription")
            return

        table = Table(title="Azure Custom Roles")
        table.add_column("Role Name", style="cyan", no_wrap=False)
        table.add_column("ID", style="magenta", no_wrap=False)
        table.add_column("Permissions", style="green")

        for role in roles:
            perm_count = sum(
                len(p.get("actions", [])) + len(p.get("data_actions", []))
                for p in role["permissions"]
            )
            table.add_row(role["name"], role["id"], str(perm_count))

        term.print(table)

    except Exception as e:
        error(str(e))


@cli.command("view-azure")
@click.argument("name_arg", required=False)
@click.option("--name", default=None, help="Role name to view")
@click.option(
    "--filter",
    default=None,
    help="Optional: filter to show matching permissions (e.g., 'Storage%', '%delete'). '*' is literal.",
)
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def view_azure(
    name_arg: Optional[str],
    name: Optional[str],
    filter: Optional[str],
    subscription_id: Optional[str],
):
    """View detailed permissions of an Azure role (built-in or custom)."""
    try:
        name = resolve_single_argument(name, name_arg, "name", "role name")
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Fetching role from Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=effective_subscription_id)
            all_roles = azure_client.list_all_roles()

        # Find role by name (case-insensitive)
        matching_roles = [r for r in all_roles if r["name"].lower() == name.lower()]

        if not matching_roles:
            error(f"Role not found: {name}")

        role = matching_roles[0]

        # Display role details
        term.print(f"\n[bold cyan]═══════════════════════════════════════[/bold cyan]")
        term.print(
            f"[bold cyan]{role['name']}[/bold cyan] ([yellow]{role['type']}[/yellow])"
        )
        term.print(f"[bold cyan]═══════════════════════════════════════[/bold cyan]")
        term.print(f"Description: {role['description'] or 'N/A'}")
        term.print(f"ID: {role['id']}")
        term.print(
            f"Assignable Scopes: {', '.join(role['assignable_scopes']) if role['assignable_scopes'] else 'None'}"
        )

        # Display permissions
        pf = PermissionFilter() if filter else None
        for i, perm_block in enumerate(role["permissions"], 1):
            term.print(f"\n[bold]Permission Block {i}[/bold]")

            # Filter permissions if filter is provided
            if filter and pf:
                actions = pf.filter_by_string(perm_block.get("actions", []), filter)
                not_actions = pf.filter_by_string(
                    perm_block.get("not_actions", []), filter
                )
                data_actions = pf.filter_by_string(
                    perm_block.get("data_actions", []), filter
                )
                not_data_actions = pf.filter_by_string(
                    perm_block.get("not_data_actions", []), filter
                )

                _print_grouped_permissions("Actions", actions, show_all=True)
                _print_grouped_permissions("Not Actions", not_actions, show_all=True)
                _print_grouped_permissions("Data Actions", data_actions, show_all=True)
                _print_grouped_permissions(
                    "Not Data Actions", not_data_actions, show_all=True
                )
            else:
                # Show all permissions if no filter
                _print_grouped_permissions(
                    "Actions", perm_block.get("actions", []), show_all=True
                )
                _print_grouped_permissions(
                    "Not Actions", perm_block.get("not_actions", []), show_all=True
                )
                _print_grouped_permissions(
                    "Data Actions", perm_block.get("data_actions", []), show_all=True
                )
                _print_grouped_permissions(
                    "Not Data Actions",
                    perm_block.get("not_data_actions", []),
                    show_all=True,
                )

    except Exception as e:
        error(str(e))


@cli.command("search-permissions")
@click.argument("filter_arg", required=False)
@click.option(
    "--filter",
    default=None,
    help="Permission filter pattern (e.g., 'Storage%', '%delete'). '*' is literal.",
)
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def search_permissions(filter_arg: Optional[str], filter: Optional[str], subscription_id: Optional[str]):
    """Search for permissions by pattern and show which roles include them."""
    try:
        filter = resolve_single_argument(
            filter, filter_arg, "filter", "permission filter pattern"
        )
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Searching roles in Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=effective_subscription_id)
            all_roles = azure_client.list_all_roles()

        matched_permissions = _collect_permission_matches(all_roles, filter)
        _print_permission_search_results(matched_permissions, filter)

    except Exception as e:
        error(str(e))


@cli.command("import-azure-permissions")
@click.argument("filter_arg", required=False)
@click.option(
    "--filter",
    "permission_filter",
    default=None,
    help="Permission filter pattern (e.g., '%keyvault%/read', 'Microsoft.Storage/%'). '*' is literal.",
)
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def import_azure_permissions(
    filter_arg: Optional[str],
    permission_filter: Optional[str],
    subscription_id: Optional[str],
):
    """Import matching Azure permissions into the current loaded role."""
    try:
        permission_filter = resolve_single_argument(
            permission_filter, filter_arg, "filter", "permission filter pattern"
        )
        role = require_current_role()
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Fetching permissions from Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=effective_subscription_id)
            all_roles = azure_client.list_all_roles()

        matched_permissions = _collect_permission_matches(all_roles, permission_filter)
        if not matched_permissions:
            term.print(f"No permissions found matching: {permission_filter}")
            return

        matched_actions, matched_data_actions = _collect_permission_matches_typed(
            all_roles, permission_filter
        )

        added_actions, added_data_actions = _import_permissions_into_current_role(
            matched_actions, matched_data_actions
        )

        success(
            f"Imported Azure permissions into [bold]{role.Name}[/bold] "
            f"(Actions added: {added_actions}, DataActions added: {added_data_actions})"
        )
        print_role_summary(role)

    except Exception as e:
        error(str(e))


@cli.command("debug-roles")
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def debug_roles(subscription_id: Optional[str]):
    """[DEBUG] List all roles with their types to diagnose filtering issues."""
    try:
        effective_subscription_id = require_subscription(subscription_id)

        with term.status("[bold blue]Fetching all roles from Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=effective_subscription_id)
            all_roles = azure_client.list_all_roles()

        if not all_roles:
            term.print("No roles found in subscription")
            return

        term.print(f"\n[bold]Total roles found: {len(all_roles)}[/bold]")

        # Group by type
        by_type = {}
        for role in all_roles:
            role_type = role.get("type", "Unknown")
            if role_type not in by_type:
                by_type[role_type] = []
            by_type[role_type].append(role)

        # Display summary
        term.print("\n[bold cyan]Role Types Found:[/bold cyan]")
        for role_type, roles in sorted(by_type.items()):
            term.print(f"  {role_type}: {len(roles)} roles")

        # Show details table
        table = Table(title="All Roles with Type Information")
        table.add_column("Name", style="cyan", no_wrap=False)
        table.add_column("Type", style="yellow")
        table.add_column("Assignable Scopes", style="green", no_wrap=False)
        table.add_column("Custom?", style="magenta")

        for role in all_roles[:20]:  # Limit to first 20 for readability
            scopes_str = (
                ", ".join(role["assignable_scopes"][:2])
                if role["assignable_scopes"]
                else "None"
            )
            # Custom roles typically have assignable_scopes limited to subscription
            is_custom = role.get("type") == "CustomRole"
            marker = "✓" if is_custom else "–"
            table.add_row(role["name"], role["type"], scopes_str, marker)

        term.print(table)

        if len(all_roles) > 20:
            term.print(f"\n... and {len(all_roles) - 20} more roles (showing first 20)")

    except Exception as e:
        error(str(e))


@cli.command()
def subscriptions():
    """List available Azure subscriptions."""
    try:
        from .azure_client import SubscriptionManager

        with term.status("[bold blue]Fetching subscriptions...[/bold blue]"):
            sub_manager = SubscriptionManager()
            subs = sub_manager.list_subscriptions()

        if not subs:
            term.print("No subscriptions found")
            return

        table = Table(title="Available Subscriptions")
        table.add_column("Subscription ID", style="cyan")
        table.add_column("Display Name", style="green")
        table.add_column("State", style="yellow")

        for sub in subs:
            marker = (
                " ✓"
                if current_subscription
                and sub["subscription_id"] == current_subscription
                else ""
            )
            table.add_row(
                sub["subscription_id"], sub["display_name"] + marker, sub["state"]
            )

        term.print(table)

    except Exception as e:
        error(str(e))


@cli.command()
@click.argument("subscription", required=False, default=None)
@click.option(
    "--id", "subscription_id", default=None, help="Subscription ID (explicit)"
)
@click.option("--name", default=None, help="Subscription display name (explicit)")
def use_subscription(
    subscription: Optional[str], subscription_id: Optional[str], name: Optional[str]
):
    """Switch to a different Azure subscription.

    Can be used as:
    - use-subscription SUBSCRIPTION_ID_OR_NAME
    - use-subscription --id SUBSCRIPTION_ID
    - use-subscription --name "Display Name"
    """
    global current_subscription

    try:
        from .azure_client import SubscriptionManager

        # Determine which argument was provided
        if not subscription and not subscription_id and not name:
            error("Specify a subscription ID or name")

        sub_manager = SubscriptionManager()
        sub = None

        # Try explicit --id first
        if subscription_id:
            sub = sub_manager.get_subscription_by_id(subscription_id)
        # Then try explicit --name
        elif name:
            sub = sub_manager.get_subscription_by_name(name)
        # Finally try positional argument (could be ID or name)
        elif subscription:
            # Try as ID first
            sub = sub_manager.get_subscription_by_id(subscription)
            # If not found, try as name
            if not sub:
                sub = sub_manager.get_subscription_by_name(subscription)

        if not sub:
            search_term = subscription_id or name or subscription
            error(f"Subscription not found: {search_term}")

        current_subscription = sub["subscription_id"]
        os.environ["AZURE_SUBSCRIPTION_ID"] = current_subscription

        success(f"Switched to subscription: [bold]{sub['display_name']}[/bold]")
        term.print(f"  ID: {sub['subscription_id']}")

    except Exception as e:
        error(str(e))


@cli.command()
@click.option("--all", is_flag=True, help="Show all permissions (not truncated)")
def view(all: bool):
    """View the current role."""
    try:
        role = require_current_role()
        print_role_details(role, show_all=all)

    except Exception as e:
        error(str(e))


@cli.command()
def console():
    """Enter console mode for running multiple commands."""
    interactive_mode()


def print_role_summary(role: AzureRoleDefinition):
    """Print a summary of the role."""
    term.print(f"\n[bold]Role Summary[/bold]")
    term.print(f"  Name: {role.Name}")
    term.print(f"  Description: {role.Description}")

    total_actions = 0
    total_data_actions = 0
    for perm in role.Permissions:
        total_actions += len(perm.Actions) + len(perm.NotActions)
        total_data_actions += len(perm.DataActions) + len(perm.NotDataActions)

    term.print(f"  Control Plane Actions: {total_actions}")
    term.print(f"  Data Plane Actions: {total_data_actions}")


def _group_by_namespace(permissions: list[str]) -> dict[str, list[str]]:
    """Group permissions by namespace (e.g., Microsoft.Compute)."""
    from collections import defaultdict

    grouped = defaultdict(list)

    for perm in permissions:
        # Extract namespace (first part before second /)
        parts = perm.split("/")
        if len(parts) >= 2:
            namespace = f"{parts[0]}/{parts[1]}"
        else:
            namespace = parts[0] if parts else "Other"
        grouped[namespace].append(perm)

    return dict(grouped)


def _print_grouped_permissions(
    title: str, permissions: list[str], show_all: bool = False, limit: int = 10
):
    """Print permissions grouped by namespace."""
    if not permissions:
        return

    term.print(f"  [bold]{title}:[/bold] ({len(permissions)})")
    grouped = _group_by_namespace(permissions)

    for namespace in sorted(grouped.keys()):
        perms = sorted(grouped[namespace])
        term.print(f"    [cyan]{namespace}[/cyan] ({len(perms)})")

        display_perms = perms if show_all else perms[:limit]
        for perm in display_perms:
            term.print(f"      • {perm}")

        if len(perms) > limit and not show_all:
            term.print(f"      [dim]... and {len(perms) - limit} more[/dim]")


def print_role_details(role: AzureRoleDefinition, show_all: bool = False):
    """Print detailed role information."""
    term.print(f"\n[bold]═══════════════════════════════════════[/bold]")
    term.print(f"[bold cyan]{role.Name}[/bold cyan]")
    term.print(f"[bold]═══════════════════════════════════════[/bold]")
    term.print(f"Description: {role.Description}")
    term.print(f"ID: {role.Id}")
    term.print(f"Type: {role.Type}")
    term.print(f"Created: {role.CreatedOn}")
    term.print(f"Updated: {role.UpdatedOn}")
    term.print(f"Assignable Scopes: {', '.join(role.AssignableScopes)}")

    term.print(f"\n[bold]Permissions:[/bold]")

    for i, perm in enumerate(role.Permissions, 1):
        term.print(f"\n[bold cyan]Block {i}[/bold cyan]")

        _print_grouped_permissions("Actions", perm.Actions, show_all, limit=10)
        _print_grouped_permissions("Not Actions", perm.NotActions, show_all, limit=5)
        _print_grouped_permissions("Data Actions", perm.DataActions, show_all, limit=5)
        _print_grouped_permissions(
            "Not Data Actions", perm.NotDataActions, show_all, limit=5
        )


def parse_multiline_commands(text: str) -> list[str]:
    """Parse multi-line input, filtering out comments and empty lines.

    Args:
        text: Raw input text (may contain multiple lines and comments)

    Returns:
        List of command strings, with comments and blank lines filtered out
    """
    commands = []
    for line in text.split("\n"):
        # Strip whitespace
        line = line.strip()
        # Skip empty lines and comment lines (starting with #)
        if line and not line.startswith("#"):
            commands.append(line)
    return commands




def _get_available_commands() -> list[str]:
    """Get list of available CLI commands dynamically.
    
    This function extracts command names from the CLI group, making auto-complete
    automatically available for new commands without code changes.
    
    Returns:
        List of available command names
    """
    commands = []
    if hasattr(cli, "commands"):
        commands = list(cli.commands.keys())
    
    # Add special console commands that aren't in cli.commands
    console_commands = ["help", "paste", "exit", "quit", "!"]
    return sorted(commands + console_commands)


def interactive_mode():
    """Launch interactive menu."""
    term.print("[bold cyan]Azure Custom Role Designer[/bold cyan]\n")

    # Show help menu on startup
    show_help()

    while True:
        try:
            # Display current state
            term.print("\n[bold]Context:[/bold]", end=" ")

            role_display = (
                f"[cyan]{role_manager.current_role.Name}[/cyan]"
                if role_manager.current_role
                else "[dim]None[/dim]"
            )
            term.print(f"Role: {role_display}", end=" ")

            sub_display = (
                f"[green]{current_subscription}[/green]"
                if current_subscription
                else "[dim]None[/dim]"
            )
            term.print(f"| Subscription: {sub_display}")

            # Create auto-complete with available commands
            command_completer = WordCompleter(_get_available_commands(), ignore_case=True)

            # Use prompt_toolkit for command input with history
            raw_input = _prompt_input("> ", completer=command_completer).strip()

            # Parse multi-line input, filtering comments and blank lines
            commands = parse_multiline_commands(raw_input)

            if not commands:
                continue

            # Process each command in sequence
            for command in commands:
                # Display the command being executed if it's multi-line input
                if len(commands) > 1:
                    term.print(f"[dim]>> {command}[/dim]")

                if command.lower() == "quit" or command.lower() == "exit":
                    term.print("[green]Goodbye![/green]")
                    return  # Exit interactive mode
                elif command.lower() == "help":
                    show_help()
                elif command.lower().startswith("help "):
                    # Show help for specific command
                    cmd_name = command[5:].strip()
                    show_command_help(cmd_name)
                elif command.lower() == "paste":
                    # Enter multi-line paste mode
                    term.print(
                        "[dim]Enter multiple commands (press Enter twice to submit):[/dim]"
                    )
                    paste_lines = []
                    # Use completer in paste mode too
                    paste_completer = WordCompleter(_get_available_commands(), ignore_case=True)
                    while True:
                        try:
                            line = _prompt_input("  ", completer=paste_completer)
                            if not line.strip():
                                break
                            paste_lines.append(line)
                        except (KeyboardInterrupt, EOFError):
                            break

                    # Parse and execute all pasted commands
                    pasted_input = "\n".join(paste_lines)
                    pasted_commands = parse_multiline_commands(pasted_input)

                    if pasted_commands:
                        term.print(
                            f"[dim]Executing {len(pasted_commands)} command(s)...[/dim]"
                        )
                        for pasted_cmd in pasted_commands:
                            term.print(f"[dim]>> {pasted_cmd}[/dim]")
                            try:
                                args = shlex.split(pasted_cmd)
                                if args:
                                    cli.main(args, standalone_mode=False)
                            except click.exceptions.ClickException as e:
                                term.print(f"[red]✗ Error:[/red] {e.format_message()}")
                            except click.exceptions.Exit:
                                pass
                            except SystemExit:
                                pass
                            except Exception as e:
                                term.print(f"[red]✗ Error:[/red] {e}")
                elif command.startswith("!"):
                    # Execute shell command with ! prefix
                    shell_cmd = command[1:].strip()
                    if shell_cmd:
                        run_shell_command(shell_cmd)
                elif command.lower().startswith("shell "):
                    # Execute shell command with 'shell' prefix
                    shell_cmd = command[6:].strip()
                    if shell_cmd:
                        run_shell_command(shell_cmd)
                else:
                    # Try to invoke the command
                    try:
                        # Parse the command line input
                        args = shlex.split(command)
                        if not args:
                            continue

                        # Prevent recursive console mode
                        if args[0] == "console":
                            term.print(
                                "[yellow]⚠[/yellow] The 'console' command is not available in console mode"
                            )
                            continue

                        # Invoke the CLI with standalone mode off to prevent sys.exit
                        cli.main(args, standalone_mode=False)

                    except click.exceptions.UsageError as e:
                        # Handle unknown commands
                        error_msg = str(e)
                        if "No such command" in error_msg:
                            term.print(
                                f"[red]✗ Unknown command.[/red] Type 'help' to see available commands."
                            )
                        else:
                            term.print(f"[red]✗ Error:[/red] {e.format_message()}")
                    except click.exceptions.ClickException as e:
                        term.print(f"[red]✗ Error:[/red] {e.format_message()}")
                    except click.exceptions.Exit:
                        # Normal exit (e.g., from --help), ignore
                        pass
                    except SystemExit:
                        # Commands may call sys.exit(), catch it to keep interactive mode running
                        pass
                    except Exception as e:
                        term.print(f"[red]✗ Error:[/red] {e}")

        except KeyboardInterrupt:
            term.print("\n[green]Goodbye![/green]")
            break
        except Exception as e:
            term.print(f"[red]Error:[/red] {e}")


def run_shell_command(command: str):
    """Execute a shell command and display the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout for shell commands
        )

        # Display stdout
        if result.stdout:
            term.print(result.stdout, end="")

        # Display stderr in yellow if there's an error
        if result.stderr:
            term.print(f"[yellow]{result.stderr}[/yellow]", end="")

        # Show exit code if non-zero
        if result.returncode != 0:
            term.print(f"[red]✗ Command exited with code {result.returncode}[/red]")

    except subprocess.TimeoutExpired:
        term.print("[red]✗ Command timed out after 60 seconds[/red]")
    except Exception as e:
        term.print(f"[red]✗ Error executing command:[/red] {e}")


def show_help():
    """Show help menu."""
    command_help = [
        ("create", "Create a new role from scratch"),
        ("load", "Load a role (local, file, or Azure)"),
        ("merge", "Merge permissions from other roles"),
        ("remove", "Remove permissions"),
        ("set-name", "Change role name"),
        ("set-description", "Change role description"),
        ("set-scopes", "Change role assignable scopes"),
        ("list", "List available roles"),
        ("delete", "Delete a local role"),
        ("view", "View current role details"),
        ("save", "Save role to file"),
        ("publish", "Publish role to Azure"),
        ("list-azure", "List custom roles in Azure"),
        ("view-azure", "View detailed permissions of an Azure role"),
        ("search-permissions", "Search for permissions by pattern across roles"),
        (
            "import-azure-permissions",
            "Import matching Azure permissions into current role",
        ),
        ("subscriptions", "List available Azure subscriptions"),
        (
            "use-subscription",
            "Switch to a different subscription (by --id or --name)",
        ),
        ("help", "Show this help"),
        ("paste", "Enter multi-line paste mode (for scripts with comments)"),
        ("exit", "Exit the tool"),
    ]

    cmd_width = max(len(command) for command, _ in command_help) + 1
    command_lines = [
        f"  {command:<{cmd_width}} - {description}"
        for command, description in command_help
    ]

    help_lines = [
        "[bold cyan]Available Commands:[/bold cyan]",
        *command_lines,
        "",
        "[bold cyan]Shell Commands:[/bold cyan]",
        "  !<command>  - Execute a shell command (e.g., !ls -la)",
        "  shell <cmd> - Execute a shell command (e.g., shell pwd)",
        "",
        "Use 'help <command>' for detailed information about a specific command.",
    ]
    term.print("\n" + "\n".join(help_lines))


def show_command_help(command_name: str):
    """Show help for a specific command."""
    # Get the command from the CLI group
    cmd = cli.commands.get(command_name)

    if cmd is None:
        term.print(f"[red]✗ Unknown command:[/red] {command_name}")
        term.print("Type 'help' to see all available commands.")
        return

    # Create a context and get the help text
    ctx = click.Context(cmd, info_name=command_name)
    help_text = cmd.get_help(ctx)

    term.print(f"\n[bold cyan]Help for '{command_name}':[/bold cyan]")
    term.print(help_text)
    term.print()


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
