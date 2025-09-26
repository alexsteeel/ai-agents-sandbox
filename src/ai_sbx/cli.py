"""Main CLI entry point for AI Agents Sandbox."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ai_sbx import __version__
from ai_sbx.commands import image, notify, worktree
from ai_sbx.commands import init as init_module
from ai_sbx.utils import AliasedGroup, logger

console = Console()


@click.group(
    cls=AliasedGroup,
    aliases={
        "wt": "worktree",
        "w": "worktree",
        "workspace": "worktree",
        "ws": "worktree",
        "img": "image",
        "images": "image",
        "i": "init",
        "d": "doctor",
        "dr": "doctor",
        "n": "notify",
        "u": "upgrade",
        "up": "upgrade",
        "h": "help",
    },
    invoke_without_command=True,
)
@click.option("--version", "-v", is_flag=True, help="Show version and exit")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, version: bool, verbose: bool) -> None:
    """AI Agents Sandbox - Secure development environments for AI-assisted coding.

    A comprehensive tool for managing isolated development containers with
    built-in security, proxy controls, and AI assistant integration.
    """
    # Store settings in context
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["console"] = console

    # Configure logging
    if verbose:
        logger.set_verbose(True)

    if version:
        console.print(f"AI Agents Sandbox v{__version__}")
        sys.exit(0)

    # Show help if no command provided
    if ctx.invoked_subcommand is None:
        show_welcome()
        click.echo(ctx.get_help())


def show_welcome() -> None:
    """Display welcome banner."""
    panel = Panel.fit(
        Text.from_markup(
            f"[bold cyan]AI Agents Sandbox[/bold cyan] [dim]v{__version__}[/dim]\n"
            "[yellow]Secure development environments for AI-assisted coding[/yellow]\n\n"
            "[dim]Use --help for more information[/dim]"
        ),
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


# Create init subcommand group
@cli.group(
    cls=AliasedGroup,
    aliases={
        "g": "global",
        "p": "project",
        "proj": "project",
        "wt": "worktree",
        "w": "worktree",
    },
)
def init() -> None:
    """Initialize AI Agents Sandbox components."""
    pass


@init.command(name="global")
@click.option(
    "--wizard", is_flag=True, help="Run interactive setup wizard with custom registry configuration"
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init_global(ctx: click.Context, wizard: bool, force: bool) -> None:
    """Initialize global AI Agents Sandbox configuration.

    Sets up system-wide configuration including:

    \b
    • Building Docker images
    • Creating system groups and directories
    • Configuring Docker registry proxy
    • Optional: Custom registry configuration (with --wizard)

    The command provides detailed reporting of all system changes made
    to your system, including directories, files, groups, and containers.
    """
    from ai_sbx.commands.init import init_global as init_global_impl

    console = ctx.obj["console"]
    verbose = ctx.obj.get("verbose", False)
    init_global_impl(console, wizard=wizard, force=force, verbose=verbose)


@init.command(name="project")
@click.argument("path", type=click.Path(), default=".")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--wizard", is_flag=True, help="Run interactive setup wizard")
@click.option(
    "--base-image",
    type=click.Choice(["base", "dotnet", "golang"]),
    help="Development environment to use",
)
@click.option(
    "--ide",
    type=click.Choice(["vscode", "pycharm", "rider", "goland", "devcontainer"]),
    help="Preferred IDE",
)
@click.pass_context
def init_project(
    ctx: click.Context, path: str, force: bool, wizard: bool, base_image: str, ide: str
) -> None:
    """Initialize a project with AI Agents Sandbox.

    Creates .devcontainer directory with all necessary configuration files.
    Run this in your repository root before creating worktrees.

    \b
    Features:
    • Network isolation with proxy filtering
    • Claude settings detection and integration
    • IDE-specific configurations (VS Code, PyCharm, etc.)
    • Custom registry support
    """
    from pathlib import Path

    from ai_sbx.commands.init import init_project as init_project_impl
    from ai_sbx.config import BaseImage, IDE

    console = ctx.obj["console"]
    verbose = ctx.obj.get("verbose", False)

    project_path = Path(path).resolve()

    # Convert string values to enums
    base_image_enum = BaseImage(base_image) if base_image else None
    ide_enum = IDE(ide) if ide else None

    init_project_impl(
        console,
        project_path,
        wizard=wizard,
        base_image=base_image,
        ide=ide,
        force=force,
        verbose=verbose,
    )


@init.command(name="worktree")
@click.argument("path", type=click.Path(), default=".")
@click.pass_context
def init_worktree(ctx: click.Context, path: str) -> None:
    """Initialize worktree environment (container setup).

    This is called automatically by devcontainer initialization.
    Sets up the development environment inside the container.
    """
    from ai_sbx.commands.init import run_worktree_init

    console = ctx.obj["console"]
    verbose = ctx.obj.get("verbose", False)
    run_worktree_init(console, path, verbose=verbose)


@init.command(name="update")
@click.argument("path", type=click.Path(), default=".")
@click.pass_context
def init_update(ctx: click.Context, path: str) -> None:
    """Update .env file from ai-sbx.yaml configuration.

    Regenerates the .env file based on current ai-sbx.yaml settings.
    This is useful after editing ai-sbx.yaml manually.
    """
    from ai_sbx.commands.init import run_update_env

    console = ctx.obj["console"]
    verbose = ctx.obj.get("verbose", False)
    run_update_env(console, path, verbose=verbose)


# Add other commands
cli.add_command(worktree)
cli.add_command(image.image)
cli.add_command(notify.notify)


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version information."""
    console = ctx.obj["console"]
    console.print(f"AI Agents Sandbox v{__version__}")


@cli.command()
@click.pass_context
def help(ctx: click.Context) -> None:
    """Show help information and command overview."""
    console = ctx.obj["console"]

    console.print("\n[bold cyan]AI Agents Sandbox - Command Overview[/bold cyan]\n")

    help_text = """
[bold yellow]Initialization Commands:[/bold yellow]
  [cyan]ai-sbx init global[/cyan]      - One-time setup (builds images, creates groups, starts proxy)
  [cyan]ai-sbx init project[/cyan]     - Initialize a project with .devcontainer
  [cyan]ai-sbx init worktree[/cyan]    - Initialize container environment (auto-called)

[bold yellow]Development Commands:[/bold yellow]
  [cyan]ai-sbx worktree create[/cyan]  - Create a new git worktree for a task
  [cyan]ai-sbx worktree list[/cyan]    - List all worktrees
  [cyan]ai-sbx worktree remove[/cyan]  - Remove a worktree
  [cyan]ai-sbx worktree connect[/cyan] - Connect to existing worktree

[bold yellow]Image Management:[/bold yellow]
  [cyan]ai-sbx image build[/cyan]      - Build Docker images
  [cyan]ai-sbx image list[/cyan]       - List Docker images and status
  [cyan]ai-sbx image verify[/cyan]     - Verify required images are installed

[bold yellow]Utilities:[/bold yellow]
  [cyan]ai-sbx doctor[/cyan]           - Diagnose and fix issues
  [cyan]ai-sbx notify[/cyan]           - Start notification watcher
  [cyan]ai-sbx upgrade[/cyan]          - Upgrade to latest version
  [cyan]ai-sbx help[/cyan]             - Show this help message

[bold yellow]Typical Workflow:[/bold yellow]
  1. [cyan]ai-sbx init global[/cyan]     # One-time setup
  2. [cyan]cd /your/project[/cyan]
  3. [cyan]ai-sbx init project[/cyan]    # Setup project
  4. [cyan]ai-sbx worktree create[/cyan] # Create task worktree
  5. Open in IDE (VS Code/PyCharm)
"""
    console.print(help_text)

    console.print("\n[dim]For detailed help on any command, use: ai-sbx COMMAND --help[/dim]\n")


@cli.command()
@click.option("--check", is_flag=True, help="Check if system is properly configured")
@click.option("--fix", is_flag=True, help="Attempt to fix common issues")
@click.option("--verbose", is_flag=True, help="Show verbose diagnostic details")
@click.option("--non-interactive", is_flag=True, help="Run without prompts")
@click.pass_context
def doctor(
    ctx: click.Context, check: bool, fix: bool, verbose: bool, non_interactive: bool
) -> None:
    """Diagnose and fix common issues with the AI Agents Sandbox setup.

    When run without flags, enters interactive mode with prompts for options."""
    from ai_sbx.commands.doctor import run_doctor

    console = ctx.obj["console"]
    verbose_flag = ctx.obj.get("verbose", False) or verbose

    # Determine if we're in interactive mode
    interactive = not non_interactive and not (check or fix or verbose)

    run_doctor(
        console, check_only=check, fix_issues=fix, verbose=verbose_flag, interactive=interactive
    )


@cli.command()
@click.pass_context
def upgrade(ctx: click.Context) -> None:
    """Upgrade AI Agents Sandbox to the latest version."""
    from ai_sbx.commands.upgrade import run_upgrade

    console = ctx.obj["console"]
    verbose = ctx.obj.get("verbose", False)

    run_upgrade(console, verbose=verbose)


if __name__ == "__main__":
    cli()
