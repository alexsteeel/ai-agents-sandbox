"""Main CLI entry point for AI Agents Sandbox."""

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ai_sbx import __version__
from ai_sbx.commands import docker, init, notify, worktree
from ai_sbx.utils import logger

console = Console()


@click.group(invoke_without_command=True)
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


# Add command groups
cli.add_command(init.devcontainer_init, name="init")
cli.add_command(init.project_setup, name="project-setup")
cli.add_command(worktree.worktree)
cli.add_command(docker.docker)
cli.add_command(notify.notify)


@cli.command()
@click.option("--check", is_flag=True, help="Check if system is properly configured")
@click.option("--fix", is_flag=True, help="Attempt to fix common issues")
@click.option("--verbose", is_flag=True, help="Show verbose diagnostic details")
@click.pass_context
def doctor(ctx: click.Context, check: bool, fix: bool, verbose: bool) -> None:
    """Diagnose and fix common issues with the AI Agents Sandbox setup."""
    from ai_sbx.commands.doctor import run_doctor

    console = ctx.obj["console"]
    verbose_flag = ctx.obj.get("verbose", False) or verbose

    run_doctor(console, check_only=check, fix_issues=fix, verbose=verbose_flag)


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
