#!/usr/bin/env python
"""
Azure Custom Role Designer CLI

A powerful tool for platform engineers to create, update, and manage Azure custom roles.
"""

import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

from role_manager import RoleManager, AzureRoleDefinition
from permission_filter import PermissionFilter, PermissionType
from azure_client import AzureClient


console = Console()
role_manager = RoleManager()


@click.group()
@click.pass_context
def cli(ctx):
    """Azure Custom Role Designer - Create and manage Azure custom roles."""
    if ctx.invoked_subcommand is None:
        interactive_mode()


@cli.command()
@click.option("--name", prompt="Role name", help="Name of the custom role")
@click.option("--description", prompt="Description", help="Role description")
@click.option("--subscription-id", default=None, help="Azure subscription ID")
@click.pass_context
def create(ctx, name: str, description: str, subscription_id: str):
    """Create a new custom role from scratch."""
    try:
        role = role_manager.create_role(name, description)
        console.print(f"[green]✓[/green] Created new role: [bold]{role.Name}[/bold]")
        console.print(f"  Description: {role.Description}")
        console.print(f"  ID: {role.Id}")
        console.print("\nUse 'merge' command to add permissions from existing roles.")
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="Role name or filename")
@click.option("--role-dir", type=click.Path(exists=True), default=None, help="Custom role directory")
def load(name: str, role_dir: Optional[str]):
    """Load an existing role from file or Azure."""
    try:
        role_dir_path = Path(role_dir) if role_dir else None
        role = role_manager.load_from_name(name, role_dir_path)
        console.print(f"[green]✓[/green] Loaded role: [bold]{role.Name}[/bold]")
        print_role_summary(role)
    except FileNotFoundError as e:
        console.print(f"[red]✗ Error:[/red] Role not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--roles", required=True, help="Comma-separated list of role names to merge")
@click.option("--filter", default=None, help="Filter permissions by string pattern (e.g., 'Storage*')")
@click.option("--filter-type", type=click.Choice(["control", "data"]), default=None, help="Filter by permission type")
def merge(roles: str, filter: Optional[str], filter_type: Optional[str]):
    """Merge permissions from multiple roles into the current role."""
    try:
        if role_manager.current_role is None:
            console.print("[red]✗ No current role.[/red] Create or load a role first.", file=sys.stderr)
            sys.exit(1)
        
        role_names = [r.strip() for r in roles.split(",")]
        source_roles = []
        
        for role_name in role_names:
            try:
                role = role_manager.load_from_name(role_name)
                source_roles.append(role)
            except FileNotFoundError:
                console.print(f"[yellow]⚠[/yellow] Role not found: {role_name}")
                continue
        
        if not source_roles:
            console.print("[red]✗ No source roles could be loaded", file=sys.stderr)
            sys.exit(1)
        
        type_filter = PermissionType(filter_type) if filter_type else None
        
        updated = role_manager.merge_roles(source_roles, string_filter=filter, type_filter=type_filter)
        
        console.print(f"[green]✓[/green] Merged permissions from {len(source_roles)} role(s)")
        print_role_summary(updated)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--filter", default=None, help="Filter permissions by string pattern")
@click.option("--filter-type", type=click.Choice(["control", "data"]), default=None, help="Filter by permission type")
def remove(filter: Optional[str], filter_type: Optional[str]):
    """Remove permissions from the current role."""
    try:
        if role_manager.current_role is None:
            console.print("[red]✗ No current role.[/red] Create or load a role first.", file=sys.stderr)
            sys.exit(1)
        
        if not filter and not filter_type:
            console.print("[red]✗ Specify --filter and/or --filter-type", file=sys.stderr)
            sys.exit(1)
        
        type_filter = PermissionType(filter_type) if filter_type else None
        
        updated = role_manager.remove_permissions(string_filter=filter, type_filter=type_filter)
        
        console.print(f"[green]✓[/green] Removed permissions")
        print_role_summary(updated)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--name", default=None, help="Show specific role")
@click.option("--role-dir", type=click.Path(exists=True), default=None, help="Custom role directory")
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
                console.print("No roles found")
                return
            
            table = Table(title="Available Roles")
            table.add_column("Role Name", style="cyan")
            table.add_column("File", style="magenta")
            
            for role_name in roles:
                table.add_row(role_name, f"{role_name}.json")
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="Output filename (without .json)")
@click.option("--output", type=click.Path(), default=None, help="Custom output path")
@click.option("--overwrite", is_flag=True, help="Overwrite existing file")
def save(name: str, output: Optional[str], overwrite: bool):
    """Save the current role to a file."""
    try:
        if role_manager.current_role is None:
            console.print("[red]✗ No current role.[/red] Create or load a role first.", file=sys.stderr)
            sys.exit(1)
        
        if output:
            file_path = Path(output)
        else:
            file_path = role_manager.roles_dir / f"{name.lower().replace(' ', '-')}.json"
        
        saved_path = role_manager.save_to_file(role_manager.current_role, file_path, overwrite=overwrite)
        console.print(f"[green]✓[/green] Role saved to: [bold]{saved_path}[/bold]")
        
    except FileExistsError:
        console.print(f"[red]✗ File already exists:[/red] {output or name}", file=sys.stderr)
        console.print("Use --overwrite to replace")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--name", required=True, help="Role name")
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def publish(name: str, subscription_id: Optional[str]):
    """Publish the current role to Azure."""
    try:
        if role_manager.current_role is None:
            console.print("[red]✗ No current role.[/red] Create or load a role first.", file=sys.stderr)
            sys.exit(1)
        
        with console.status("[bold blue]Publishing to Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=subscription_id)
            result = azure_client.create_custom_role(role_manager.current_role)
        
        console.print(f"[green]✓[/green] Role published to Azure")
        console.print(f"  ID: {result['id']}")
        console.print(f"  Name: {result['name']}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--subscription-id", default=None, help="Azure subscription ID")
def list_azure(subscription_id: Optional[str]):
    """List custom roles in Azure subscription."""
    try:
        with console.status("[bold blue]Fetching roles from Azure...[/bold blue]"):
            azure_client = AzureClient(subscription_id=subscription_id)
            roles = azure_client.list_custom_roles()
        
        if not roles:
            console.print("No custom roles found in subscription")
            return
        
        table = Table(title="Azure Custom Roles")
        table.add_column("Role Name", style="cyan")
        table.add_column("ID", style="magenta")
        table.add_column("Permissions", style="green")
        
        for role in roles:
            perm_count = sum(
                len(p.get("actions", []))
                + len(p.get("data_actions", []))
                for p in role["permissions"]
            )
            table.add_row(role["name"], role["id"][:8] + "...", str(perm_count))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


@cli.command()
@click.option("--all", is_flag=True, help="Show all permissions (not truncated)")
def view(all: bool):
    """View the current role."""
    try:
        if role_manager.current_role is None:
            console.print("[red]✗ No current role loaded", file=sys.stderr)
            sys.exit(1)
        
        print_role_details(role_manager.current_role, show_all=all)
    
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}", file=sys.stderr)
        sys.exit(1)


def print_role_summary(role: AzureRoleDefinition):
    """Print a summary of the role."""
    console.print(f"\n[bold]Role Summary[/bold]")
    console.print(f"  Name: {role.Name}")
    console.print(f"  Description: {role.Description}")
    
    total_actions = 0
    total_data_actions = 0
    for perm in role.Permissions:
        total_actions += len(perm.Actions) + len(perm.NotActions)
        total_data_actions += len(perm.DataActions) + len(perm.NotDataActions)
    
    console.print(f"  Control Plane Actions: {total_actions}")
    console.print(f"  Data Plane Actions: {total_data_actions}")


def print_role_details(role: AzureRoleDefinition, show_all: bool = False):
    """Print detailed role information."""
    console.print(f"\n[bold]═══════════════════════════════════════[/bold]")
    console.print(f"[bold cyan]{role.Name}[/bold cyan]")
    console.print(f"[bold]═══════════════════════════════════════[/bold]")
    console.print(f"Description: {role.Description}")
    console.print(f"ID: {role.Id}")
    console.print(f"Type: {role.Type}")
    console.print(f"Created: {role.CreatedOn}")
    console.print(f"Updated: {role.UpdatedOn}")
    console.print(f"Assignable Scopes: {', '.join(role.AssignableScopes)}")
    
    console.print(f"\n[bold]Permissions:[/bold]")
    
    for i, perm in enumerate(role.Permissions, 1):
        console.print(f"\n[bold cyan]Block {i}[/bold cyan]")
        
        if perm.Actions:
            console.print(f"  [bold]Actions:[/bold] ({len(perm.Actions)})")
            for action in sorted(perm.Actions)[:10]:
                console.print(f"    • {action}")
            if len(perm.Actions) > 10 and not show_all:
                console.print(f"    ... and {len(perm.Actions) - 10} more")
        
        if perm.NotActions:
            console.print(f"  [bold]Not Actions:[/bold] ({len(perm.NotActions)})")
            for action in sorted(perm.NotActions)[:5]:
                console.print(f"    • {action}")
            if len(perm.NotActions) > 5 and not show_all:
                console.print(f"    ... and {len(perm.NotActions) - 5} more")
        
        if perm.DataActions:
            console.print(f"  [bold]Data Actions:[/bold] ({len(perm.DataActions)})")
            for action in sorted(perm.DataActions)[:5]:
                console.print(f"    • {action}")
            if len(perm.DataActions) > 5 and not show_all:
                console.print(f"    ... and {len(perm.DataActions) - 5} more")
        
        if perm.NotDataActions:
            console.print(f"  [bold]Not Data Actions:[/bold] ({len(perm.NotDataActions)})")
            for action in sorted(perm.NotDataActions)[:5]:
                console.print(f"    • {action}")
            if len(perm.NotDataActions) > 5 and not show_all:
                console.print(f"    ... and {len(perm.NotDataActions) - 5} more")


def interactive_mode():
    """Launch interactive menu."""
    console.print("[bold cyan]Azure Custom Role Designer[/bold cyan]")
    console.print("Commands: create, load, merge, remove, list, save, publish, view, list-azure\n")
    
    while True:
        try:
            console.print("\n[bold]Current Role:[/bold]", end=" ")
            if role_manager.current_role:
                console.print(f"[cyan]{role_manager.current_role.Name}[/cyan]")
            else:
                console.print("[dim]None[/dim]")
            
            command = console.input("[bold]>[/bold] ").strip().lower()
            
            if not command:
                continue
            elif command == "quit" or command == "exit":
                console.print("[green]Goodbye![/green]")
                break
            elif command == "help":
                show_help()
            else:
                # Try to invoke the command
                try:
                    ctx = cli.make_context("", [command])
                except:
                    console.print("[red]Invalid command[/red]")
        
        except KeyboardInterrupt:
            console.print("\n[green]Goodbye![/green]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


def show_help():
    """Show help menu."""
    console.print("""
[bold cyan]Available Commands:[/bold cyan]
  create      - Create a new role from scratch
  load        - Load an existing role
  merge       - Merge permissions from other roles
  remove      - Remove permissions
  list        - List available roles
  view        - View current role details
  save        - Save role to file
  publish     - Publish role to Azure
  list-azure  - List custom roles in Azure
  help        - Show this help
  exit        - Exit the tool

Use 'command --help' for more information.
    """)


if __name__ == "__main__":
    cli()
