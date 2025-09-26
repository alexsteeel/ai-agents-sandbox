"""List command for worktree management."""

import subprocess
from datetime import datetime
from pathlib import Path

import click
from rich.table import Table

from .utils import get_task_description, is_container_running
from .utils import list_worktrees as get_worktrees


@click.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def list_worktrees(ctx: click.Context, verbose: bool) -> None:
    """List all git worktrees with their status.

    Shows worktree paths, branches, and task descriptions.
    """
    from rich.console import Console

    console: Console = ctx.obj["console"]

    # Use exclude_current=True to filter out the main repository
    worktrees = get_worktrees(exclude_current=True)

    if not worktrees:
        console.print("[yellow]No worktrees found[/yellow]")
        console.print("[dim]Use 'ai-sbx worktree create \"task description\"' to create one[/dim]")
        return

    # Create table
    table = Table(show_lines=True)
    table.add_column("Path", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Commit", style="yellow")
    table.add_column("Message", style="dim")
    table.add_column("Container", style="blue")

    if verbose:
        table.add_column("Description")
        table.add_column("Modified")

    for w in worktrees:
        path = Path(w["path"])
        branch = w.get("branch", "[detached]")
        commit = w.get("commit", "")[:7]

        # Get commit message
        commit_msg = "-"
        if path.exists() and commit:
            try:
                result = subprocess.run(
                    ["git", "log", "-1", "--pretty=%s", commit],
                    capture_output=True,
                    text=True,
                    cwd=path,
                    check=True,
                )
                commit_msg = result.stdout.strip()[:50]  # Limit to 50 chars
                if len(result.stdout.strip()) > 50:
                    commit_msg += "..."
            except subprocess.CalledProcessError:
                pass

        # Check container status
        container_base_name = f"{path.name}-devcontainer"
        container_status = "running" if is_container_running(container_base_name) else "stopped"

        row = [path.name, branch, commit, commit_msg, container_status]

        if verbose:
            # Get task description
            desc = get_task_description(path) or "-"

            # Get last modified
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                modified = mtime.strftime("%Y-%m-%d %H:%M")
            else:
                modified = "[missing]"

            row.extend([desc, modified])

        table.add_row(*row)

    console.print(table)
