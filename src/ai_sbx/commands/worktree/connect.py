"""Connect command for worktree management."""

import subprocess
from pathlib import Path
from typing import Optional

import click
import inquirer

from ai_sbx.config import IDE
from ai_sbx.utils import find_project_root, prompt_yes_no

from .utils import (
    detect_available_ides,
    get_preferred_ide,
    get_running_container_name,
    get_task_description,
    list_worktrees,
    open_ide,
    prompt_ide_selection,
)


@click.command()
@click.argument("name", required=False)
@click.option("--ide", type=click.Choice(["vscode", "devcontainer", "pycharm", "rider", "goland"]))
@click.pass_context
def connect(ctx: click.Context, name: Optional[str], ide: Optional[str]) -> None:
    """Connect to an existing worktree.

    Can specify worktree by name/branch or select interactively.

    \b
    Examples:
        ai-sbx worktree connect                  # Interactive selection
        ai-sbx worktree connect test-feature     # Connect to specific worktree
        ai-sbx worktree connect --ide vscode     # Open with specific IDE
    """
    from rich.console import Console

    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Get list of worktrees (excluding main repository)
    worktrees = list_worktrees(exclude_current=True)

    if not worktrees:
        console.print("[yellow]No worktrees found[/yellow]")
        console.print("[dim]Use 'ai-sbx worktree create \"task description\"' to create one[/dim]")
        return

    selected = None

    # If name provided, try to find matching worktree
    if name:
        for w in worktrees:
            path = Path(w["path"])
            branch = w.get("branch", "")
            # Match by path name or branch name
            if name in path.name or name == branch:
                selected = w
                break

        if not selected:
            console.print(f"[red]No worktree found matching: {name}[/red]")
            console.print("\nAvailable worktrees:")
            for w in worktrees:
                path = Path(w["path"])
                branch = w.get("branch", "")
                console.print(f"  • {path.name} ({branch})")
            return
    else:
        # Interactive selection
        # Create choice list with task descriptions
        choices = []
        for w in worktrees:
            path = Path(w["path"])
            label = f"{path.name}"

            if w.get("branch"):
                label += f" ({w['branch']})"

            # Try to get task description
            desc = get_task_description(path)
            if desc:
                label += f" - {desc}"

            choices.append((label, w))

        questions = [
            inquirer.List(
                "worktree",
                message="Select worktree to connect to",
                choices=choices,
            )
        ]

        answers = inquirer.prompt(questions)
        if not answers:
            return

        selected = answers["worktree"]
    path = Path(selected["path"])

    if not path.exists():
        console.print("[red]Worktree path does not exist[/red]")
        console.print(f"Path: {path}")
        console.print(
            "You may need to remove this worktree with: [cyan]ai-sbx worktree remove[/cyan]"
        )
        return

    # Check if IDE was specified or load preference
    preferred_ide = None
    if ide:
        preferred_ide = IDE(ide)
    else:
        # Load preference from .user.env in the worktree path
        preferred_ide = get_preferred_ide(path)

        # If no preference in worktree, check main project
        if not preferred_ide:
            project_root = find_project_root()
            if project_root:
                preferred_ide = get_preferred_ide(project_root)

    # Check container status
    container_base_name = f"{path.name}-devcontainer"
    actual_container_name = get_running_container_name(container_base_name)

    if actual_container_name:
        # Container is running - offer to connect
        console.print(f"[green]Container '{container_base_name}' is running[/green]")

        connect_choices = [
            ("Open shell in container", "shell"),
            ("Just change directory", "cd"),
        ]

        # Add IDE option if preferred IDE is set
        if preferred_ide:
            connect_choices.insert(0, (f"Open in {preferred_ide.value}", "ide"))
        else:
            # Detect available IDEs
            detected = detect_available_ides()
            if detected:
                connect_choices.insert(0, ("Open in IDE", "ide_select"))

        connect_choices.append(("Cancel", "cancel"))

        questions = [
            inquirer.List(
                "action",
                message="What would you like to do?",
                choices=connect_choices,
                default=connect_choices[0][1] if preferred_ide else None,  # Default to IDE if set
            )
        ]

        answers = inquirer.prompt(questions)
        if not answers or answers["action"] == "cancel":
            return

        if answers["action"] == "ide":
            # Open with preferred IDE
            console.print(f"\n[cyan]Opening {preferred_ide.value}...[/cyan]")
            open_ide(path, preferred_ide, console, verbose)
        elif answers["action"] == "ide_select":
            # Select IDE and remember choice
            detected = detect_available_ides()
            if detected:
                selected_ide = prompt_ide_selection(detected, path, console)
                if selected_ide:
                    console.print(f"\n[cyan]Opening {selected_ide.value}...[/cyan]")
                    open_ide(path, selected_ide, console, verbose)
        elif answers["action"] == "shell":
            # Connect to container using actual name
            console.print(f"Connecting to container: [cyan]{actual_container_name}[/cyan]")
            console.print("[dim]Type 'exit' to disconnect[/dim]\n")

            # Use subprocess for safer execution with shell fallback
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-it",
                    actual_container_name,
                    "sh",
                    "-lc",
                    "if [ -x /bin/zsh ]; then exec /bin/zsh; "
                    "elif [ -x /bin/bash ]; then exec /bin/bash; else exec /bin/sh; fi",
                ]
            )
        else:
            # Just show cd command
            console.print("\nTo navigate to worktree, run:")
            console.print(f"[cyan]cd {path}[/cyan]")
    else:
        # Container not running - offer to start with IDE
        console.print(f"[yellow]Container '{container_base_name}' is not running[/yellow]")

        # Check for preferred IDE or detect available ones
        if preferred_ide or (detected := detect_available_ides()):
            if prompt_yes_no("\nWould you like to open the worktree in an IDE?", default=True):
                if not preferred_ide and detected:
                    # Prompt for IDE selection
                    preferred_ide = prompt_ide_selection(detected, path, console)

                if preferred_ide:
                    console.print(f"\n[cyan]Opening {preferred_ide.value}...[/cyan]")
                    open_ide(path, preferred_ide, console, verbose)
                    return

        # Fallback instructions
        console.print("\nTo start the container:")
        console.print(f"1. Navigate to worktree: [cyan]cd {path}[/cyan]")
        console.print("2. Open in IDE (containers will start automatically)")
