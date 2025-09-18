"""Worktree management commands for AI Agents Sandbox."""

import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import inquirer
from rich.console import Console
from rich.table import Table

from ai_sbx.config import IDE, load_project_config
from ai_sbx.utils import (
    AliasedGroup,
    check_command_exists,
    detect_ide,
    find_project_root,
    logger,
    prompt_yes_no,
    run_command,
)


@click.group(
    cls=AliasedGroup,
    aliases={
        "ls": "list",
        "rm": "remove",
        "del": "remove",
        "delete": "remove",
        "new": "create",
        "add": "create",
        "cn": "connect",
    },
)
def worktree() -> None:
    """Manage git worktrees for isolated development tasks.

    Worktrees allow you to work on multiple branches simultaneously
    in separate directories, each with its own devcontainer environment.
    """
    pass


@worktree.command()
@click.argument("description")
@click.option("--branch", help="Custom branch name")
@click.option("--ide", type=click.Choice(["vscode", "devcontainer", "pycharm", "rider", "goland"]))
@click.option("--no-open", is_flag=True, help="Don't open IDE after creation")
@click.option(
    "--with-task-folder/--no-task-folder",
    default=None,
    help="Create task folder (prompts if not specified)",
)
@click.pass_context
def create(
    ctx: click.Context,
    description: str,
    branch: Optional[str],
    ide: Optional[str],
    no_open: bool,
    with_task_folder: Optional[bool],
) -> None:
    """Create a new worktree for a development task.

    This command creates a git worktree with a descriptive branch name,
    sets up the devcontainer environment, and optionally opens your IDE.

    \b
    Examples:
        ai-sbx worktree create "feature 123 implement user auth"
        ai-sbx worktree create "bugfix memory leak in parser" --branch fix-parser
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a git repository[/red]")
        return

    # Check if .devcontainer is committed
    devcontainer_path = project_root / ".devcontainer"
    if devcontainer_path.exists():
        try:
            # Check if .devcontainer is tracked by git
            result = subprocess.run(
                ["git", "ls-files", ".devcontainer"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if not result.stdout.strip():
                console.print(
                    "[yellow]⚠ Warning: .devcontainer folder is not committed to git[/yellow]"
                )
                console.print(
                    "[dim]Worktrees won't have access to the devcontainer configuration[/dim]"
                )
                console.print("\nTo fix this, run:")
                console.print(
                    '[cyan]git add .devcontainer && git commit -m "Add devcontainer configuration"[/cyan]'
                )
                if not prompt_yes_no("\nContinue anyway?", default=False):
                    return
        except Exception:
            pass

    # Generate branch name if not provided
    if not branch:
        branch = _generate_branch_name(description)

    # Get repository name for prefix
    repo_name = project_root.name
    worktree_name = f"{repo_name}-{branch}"
    worktree_path = project_root.parent / worktree_name

    # Check if worktree already exists
    if worktree_path.exists():
        console.print(f"[red]Worktree already exists: {worktree_path}[/red]")
        return

    # Create worktree
    console.print(f"Creating worktree: [cyan]{worktree_name}[/cyan]")
    console.print(f"Branch name: [cyan]{branch}[/cyan]")

    try:
        run_command(
            ["git", "worktree", "add", "-b", branch, str(worktree_path)],
            cwd=project_root,
            verbose=verbose,
        )
        console.print(f"[green]✓[/green] Worktree created at {worktree_path}")
        logger.success(f"Worktree created at {worktree_path}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to create worktree: {e}[/red]")
        return

    # Copy secure.init.sh if it exists (for credentials not in git)
    _copy_secure_init(project_root, worktree_path, console)

    # Determine if we should create task folder
    if with_task_folder is None:
        # Not specified on command line, ask the user
        create_task_folder = prompt_yes_no(
            "Create task folder with requirements template?", default=True
        )
    else:
        # Use command line flag value
        create_task_folder = with_task_folder

    if create_task_folder:
        # Create task folder structure
        _create_task_structure(worktree_path, branch, description, console)

    # Determine preferred IDE
    preferred_ide = None
    if ide:
        preferred_ide = IDE(ide)
    else:
        # Load preference from .user.env
        preferred_ide = _get_preferred_ide(project_root)

        # If no preference, detect available IDEs
        if not preferred_ide:
            detected = _detect_available_ides()
            if detected:
                # If multiple IDEs available, prompt user
                if len(detected) > 1 and not no_open:
                    preferred_ide = _prompt_ide_selection(detected, project_root, console)
                elif len(detected) == 1:
                    preferred_ide = detected[0][0]
                    _save_preferred_ide(project_root, preferred_ide, console)

    # Open IDE if requested
    opened_ide = False
    if not no_open and preferred_ide:
        console.print(f"\n[cyan]Opening {preferred_ide.value}...[/cyan]")
        _open_ide(worktree_path, preferred_ide, console, verbose)
        opened_ide = True

        # Special handling for devcontainer - it runs interactively, so exit after
        if preferred_ide == IDE.DEVCONTAINER:
            return

    # Show summary only if IDE wasn't opened or user chose no IDE
    if not opened_ide:
        console.print("\n" + "=" * 64)
        console.print("[bold green]Task worktree created successfully![/bold green]")
        console.print("")
        console.print(f"[bold]Worktree:[/bold] {worktree_path}")
        console.print(f"[bold]Branch:[/bold] {branch}")
        console.print(f"[bold]Task folder:[/bold] tasks/{branch}")
        console.print(f"[bold]Requirements:[/bold] tasks/{branch}/initial_requirements.md")
        console.print("")
        console.print("To open the worktree:")
        console.print(f"  [cyan]cd {worktree_path}[/cyan]")
        console.print(
            "  [cyan]code .[/cyan]  # Open in VS Code (containers will start automatically)"
        )
        console.print("")
        console.print("To remove this worktree later:")
        console.print(f"  [cyan]git worktree remove {worktree_path}[/cyan]")
        console.print("=" * 64)
    else:
        # If IDE was opened, just show a brief summary
        console.print(f"\n[green]✓[/green] Worktree created: {worktree_path}")
        console.print(f"[green]✓[/green] Branch: {branch}")
        console.print(f"[green]✓[/green] Task folder: tasks/{branch}")
        console.print(f"\n[dim]To remove later: git worktree remove {worktree_path}[/dim]")


@worktree.command()
@click.argument("name", required=False)
@click.option("--all", "-a", is_flag=True, help="Remove all worktrees")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.option("--delete-branch", "-b", is_flag=True, help="Also delete the branch")
@click.pass_context
def remove(
    ctx: click.Context,
    name: Optional[str],
    all: bool,
    force: bool,
    delete_branch: bool,
) -> None:
    """Remove git worktrees and optionally their branches.

    Can remove worktrees by name, partial match, or interactively.
    Interactive mode allows selecting multiple worktrees at once.

    \b
    Examples:
        # Interactive selection (can select multiple)
        ai-sbx worktree remove

        # Remove specific worktree
        ai-sbx worktree remove fix-123

        # Remove all worktrees
        ai-sbx worktree remove --all

        # Remove and delete branch
        ai-sbx worktree remove fix-123 -b
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Get list of worktrees (excluding main repository)
    worktrees = _list_worktrees(exclude_current=True)

    if not worktrees:
        console.print("[yellow]No worktrees found to remove[/yellow]")
        return

    # Filter worktrees to remove
    to_remove = []

    if all:
        to_remove = worktrees
    elif name:
        # Find matching worktrees
        matches = [w for w in worktrees if name in w["path"] or name in w.get("branch", "")]

        if not matches:
            console.print(f"[red]No worktrees matching '{name}'[/red]")
            return

        to_remove = matches
    else:
        # Interactive selection - always use Checkbox for flexibility
        choices = []
        for w in worktrees:
            label = f"{Path(w['path']).name}"
            if w.get("branch"):
                label += f" ({w['branch']})"

            # Check if container is running
            container_base_name = f"{Path(w['path']).name}-devcontainer"
            actual_container = _get_running_container_name(container_base_name)
            if actual_container:
                label += f" [container: {actual_container}]"

            choices.append((label, w))

        questions = [
            inquirer.Checkbox(
                "worktrees",
                message="Select worktree(s) to remove (space to select, enter to confirm)",
                choices=choices,
            )
        ]

        answers = inquirer.prompt(questions)
        if not answers or not answers["worktrees"]:
            console.print("[yellow]No worktrees selected[/yellow]")
            return

        to_remove = answers["worktrees"]

    # Check for running containers
    containers_to_stop = {}
    for w in to_remove:
        container_base_name = f"{Path(w['path']).name}-devcontainer"
        actual_container = _get_running_container_name(container_base_name)
        if actual_container:
            containers_to_stop[w["path"]] = actual_container

    # Ask about containers and branches if not specified via flags
    delete_containers = False
    if not force:
        # Ask about containers if any are running
        if containers_to_stop:
            delete_containers = prompt_yes_no("Delete associated containers?", default=False)

        # Ask about branches if not already specified via flag
        if not delete_branch and any(w.get("branch") for w in to_remove):
            delete_branch = prompt_yes_no("Delete branches?", default=False)

    # Confirm removal
    if not force:
        console.print("\n[yellow]Will remove:[/yellow]")
        for w in to_remove:
            console.print(f"  - {w['path']}")
            if delete_branch and w.get("branch"):
                console.print(f"    [red]and delete branch: {w['branch']}[/red]")
            if delete_containers and w["path"] in containers_to_stop:
                console.print(f"    [red]and stop container: {containers_to_stop[w['path']]}[/red]")

        if not prompt_yes_no("\nContinue?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Remove worktrees
    main_path = _get_main_worktree_path()
    for w in to_remove:
        path = w["path"]
        branch = w.get("branch")

        # Safety check: Never remove the main repository
        if main_path and Path(path) == main_path:
            console.print(f"\n[red]Cannot remove main repository: {path}[/red]")
            console.print("[dim]The main repository is where the project was initialized[/dim]")
            continue

        # Stop and remove container if requested
        if delete_containers and path in containers_to_stop:
            actual_container = containers_to_stop[path]
            console.print(f"Stopping container: [cyan]{actual_container}[/cyan]")
            try:
                run_command(["docker", "stop", actual_container], verbose=verbose, check=False)
                run_command(["docker", "rm", actual_container], verbose=verbose, check=False)
                console.print(f"[green]✓[/green] Stopped and removed container: {actual_container}")
            except subprocess.CalledProcessError as e:
                console.print(f"[yellow]Warning: Could not stop/remove container: {e}[/yellow]")

        console.print(f"Removing worktree: [cyan]{path}[/cyan]")

        try:
            # Remove worktree
            run_command(["git", "worktree", "remove", path, "--force"], verbose=verbose)
            console.print(f"[green]✓[/green] Removed worktree: {path}")

            # Delete branch if requested
            if delete_branch and branch:
                try:
                    run_command(["git", "branch", "-D", branch], verbose=verbose)
                    console.print(f"[green]✓[/green] Deleted branch: {branch}")
                except subprocess.CalledProcessError:
                    console.print(f"[yellow]Warning: Could not delete branch: {branch}[/yellow]")

        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to remove worktree: {e}[/red]")

            # Try to clean up directory if it exists
            worktree_path = Path(path)
            if worktree_path.exists():
                console.print("[yellow]Attempting to clean up directory...[/yellow]")
                try:
                    import shutil

                    shutil.rmtree(worktree_path)
                    console.print(f"[green]✓[/green] Cleaned up directory: {path}")
                except Exception as cleanup_error:
                    console.print(f"[red]Could not clean up directory: {cleanup_error}[/red]")

    # Clean up prunable worktrees
    try:
        run_command(["git", "worktree", "prune"], verbose=verbose)
        logger.debug("Pruned worktrees")
    except subprocess.CalledProcessError:
        pass


@worktree.command()
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
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Get list of worktrees (excluding main repository)
    worktrees = _list_worktrees(exclude_current=True)

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
            desc = _get_task_description(path)
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
        preferred_ide = _get_preferred_ide(path)

        # If no preference in worktree, check main project
        if not preferred_ide:
            project_root = find_project_root()
            if project_root:
                preferred_ide = _get_preferred_ide(project_root)

    # Check container status
    container_base_name = f"{path.name}-devcontainer"
    actual_container_name = _get_running_container_name(container_base_name)

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
            detected = _detect_available_ides()
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
            _open_ide(path, preferred_ide, console, verbose)
        elif answers["action"] == "ide_select":
            # Select IDE and remember choice
            detected = _detect_available_ides()
            if detected:
                selected_ide = _prompt_ide_selection(detected, path, console)
                if selected_ide:
                    console.print(f"\n[cyan]Opening {selected_ide.value}...[/cyan]")
                    _open_ide(path, selected_ide, console, verbose)
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
        if preferred_ide or (detected := _detect_available_ides()):
            if prompt_yes_no("\nWould you like to open the worktree in an IDE?", default=True):
                if not preferred_ide and detected:
                    # Prompt for IDE selection
                    preferred_ide = _prompt_ide_selection(detected, path, console)

                if preferred_ide:
                    console.print(f"\n[cyan]Opening {preferred_ide.value}...[/cyan]")
                    _open_ide(path, preferred_ide, console, verbose)
                    return

        # Fallback instructions
        console.print("\nTo start the container:")
        console.print(f"1. Navigate to worktree: [cyan]cd {path}[/cyan]")
        console.print("2. Open in IDE (containers will start automatically)")


@worktree.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def list_worktrees(ctx: click.Context, verbose: bool) -> None:
    """List all git worktrees with their status.

    Shows worktree paths, branches, and task descriptions.
    """
    console: Console = ctx.obj["console"]

    # Use exclude_current=True to filter out the main repository
    worktrees = _list_worktrees(exclude_current=True)

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
        container_status = "running" if _is_container_running(container_base_name) else "stopped"

        row = [path.name, branch, commit, commit_msg, container_status]

        if verbose:
            # Get task description
            desc = _get_task_description(path) or "-"

            # Get last modified
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                modified = mtime.strftime("%Y-%m-%d %H:%M")
            else:
                modified = "[missing]"

            row.extend([desc, modified])

        table.add_row(*row)

    console.print(table)


def _generate_branch_name(description: str) -> str:
    """Generate a branch name from a task description."""
    # Convert to lowercase and replace spaces with hyphens
    branch = description.lower()
    branch = re.sub(r"[^a-z0-9-]+", "-", branch)
    branch = re.sub(r"-+", "-", branch)
    branch = branch.strip("-")

    # Limit length
    if len(branch) > 50:
        branch = branch[:50].rsplit("-", 1)[0]

    return branch


def _copy_secure_init(project_root: Path, worktree_path: Path, console: Console) -> None:
    """Copy secure.init.sh if it exists (for credentials not in git)."""
    secure_init_src = project_root / ".devcontainer" / "secure.init.sh"
    secure_init_dest = worktree_path / ".devcontainer" / "secure.init.sh"

    if secure_init_src.exists():
        console.print("[cyan]Found secure.init.sh, copying to worktree...[/cyan]")

        # Ensure .devcontainer directory exists
        secure_init_dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        shutil.copy2(secure_init_src, secure_init_dest)

        # Preserve executable permissions
        if os.access(secure_init_src, os.X_OK):
            os.chmod(secure_init_dest, os.stat(secure_init_src).st_mode)

        console.print("[green]✓[/green] Copied secure.init.sh (contains credentials)")
    else:
        logger.debug("No secure.init.sh found")


def _create_task_structure(
    worktree_path: Path, branch_name: str, description: str, console: Console
) -> None:
    """Create task directory structure matching original shell script."""
    try:
        # Create tasks/{branch-name} directory structure
        task_dir = worktree_path / "tasks" / branch_name
        task_dir.mkdir(parents=True, exist_ok=True)

        # Create initial requirements file
        requirements_file = task_dir / "initial_requirements.md"
        requirements_file.write_text(
            f"""# Task: {description}

## Task ID: {branch_name}

## Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Initial Requirements

[Describe the task requirements here]

## Acceptance Criteria

- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

## Technical Approach

[Describe the technical approach]

## Notes

[Additional notes]
"""
        )

        console.print(f"[green]✓[/green] Task folder created: tasks/{branch_name}")
        console.print("[green]✓[/green] Initial requirements file created")
        logger.debug(f"Created task structure at {task_dir}")

    except Exception as e:
        logger.warning(f"Could not create task structure: {e}")
        console.print(f"[yellow]Warning: Failed to create task structure: {e}[/yellow]")


def _detect_available_ides() -> list[tuple[IDE, str]]:
    """Detect available IDEs on the system using shared detection logic."""
    available = []

    # Use the shared detect_ide function to get detected IDE names
    detected = detect_ide()

    # Map detected names to IDE enum and display names
    ide_mapping = {
        "vscode": (IDE.VSCODE, "VS Code"),
        "pycharm": (IDE.PYCHARM, "PyCharm"),
        "rider": (IDE.RIDER, "Rider"),
        "goland": (IDE.GOLAND, "GoLand"),
        "devcontainer": (IDE.DEVCONTAINER, "DevContainer"),
    }

    for ide_name in detected:
        if ide_name in ide_mapping:
            available.append(ide_mapping[ide_name])

    return available


def _get_preferred_ide(project_root: Path) -> Optional[IDE]:
    """Get preferred IDE from .user.env file."""
    user_env = project_root / ".devcontainer" / ".user.env"

    if user_env.exists():
        try:
            content = user_env.read_text()
            for line in content.splitlines():
                if line.startswith("PREFERRED_IDE="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    try:
                        return IDE(value)
                    except ValueError:
                        pass
        except Exception:
            pass

    return None


def _save_preferred_ide(project_root: Path, ide: IDE, console: Console) -> None:
    """Save preferred IDE to .user.env file."""
    user_env = project_root / ".devcontainer" / ".user.env"

    # Ensure directory exists
    user_env.parent.mkdir(parents=True, exist_ok=True)

    # Read existing content
    lines = []
    if user_env.exists():
        try:
            content = user_env.read_text()
            lines = [line for line in content.splitlines() if not line.startswith("PREFERRED_IDE=")]
        except Exception:
            pass

    # Add new preference
    lines.append(f"PREFERRED_IDE={ide.value}")

    # Write back
    try:
        user_env.write_text("\n".join(lines) + "\n")
        console.print(f"[dim]Saved IDE preference to .user.env: {ide.value}[/dim]")
    except Exception as e:
        logger.warning(f"Could not save IDE preference: {e}")


def _prompt_ide_selection(
    available_ides: list[tuple[IDE, str]], project_root: Path, console: Console
) -> Optional[IDE]:
    """Prompt user to select an IDE."""
    import sys

    # Check if we're in an interactive terminal
    if not sys.stdin.isatty():
        console.print("[yellow]Non-interactive mode detected. Skipping IDE selection.[/yellow]")
        console.print("Available IDEs:")
        for ide, name in available_ides:
            console.print(f"  - {name} ({ide.value})")
        console.print("\nYou can open the project manually or specify --ide option")
        return None

    # Load project configuration to get preferred IDE

    config = load_project_config(project_root)
    preferred_ide = config.preferred_ide if config else None

    choices = [(name, ide) for ide, name in available_ides]
    choices.append(("Skip (open manually later)", None))

    # Find the default choice based on preferred IDE
    default_choice = choices[-1][0]  # Default to "Skip" if preferred not found
    if preferred_ide:
        for name, ide in choices:
            if ide == preferred_ide:
                default_choice = name
                break

    try:
        questions = [
            inquirer.List(
                "ide",
                message="Select IDE to open",
                choices=choices,
                default=default_choice,
            )
        ]

        answers = inquirer.prompt(questions)
        if not answers or not answers["ide"]:
            return None

        selected_ide = answers["ide"]

        # Ask if user wants to save preference (unless it's devcontainer)
        if selected_ide != IDE.DEVCONTAINER:
            if prompt_yes_no(
                f"Save {selected_ide.value} as preferred IDE for this project?", default=True
            ):
                _save_preferred_ide(project_root, selected_ide, console)

        return selected_ide
    except Exception as e:
        console.print(f"[yellow]Cannot prompt for IDE selection: {e}[/yellow]")
        console.print("Available IDEs:")
        for ide, name in available_ides:
            console.print(f"  - {name} ({ide.value})")
        console.print("\nYou can open the project manually or specify --ide option")
        return None


def _open_ide(worktree_path: Path, ide: IDE, console: Console, verbose: bool = False) -> None:
    """Open IDE for the worktree with special devcontainer handling."""

    # Special handling for devcontainer CLI - it starts container and opens interactive shell
    if ide == IDE.DEVCONTAINER:
        if not check_command_exists("devcontainer"):
            console.print("[red]devcontainer CLI not found[/red]")
            console.print(
                "Install it from: https://code.visualstudio.com/docs/devcontainers/devcontainer-cli"
            )
            return

        console.print("[cyan]Preparing DevContainer environment...[/cyan]")

        # Check for required Docker images
        import os

        from ai_sbx.utils import check_docker_images, prompt_build_images

        # Get the image tag from environment or use default
        image_tag = os.environ.get("IMAGE_TAG", "1.0.0")
        required_images = [
            f"ai-agents-sandbox/devcontainer:{image_tag}",
            f"ai-agents-sandbox/tinyproxy:{image_tag}",
            f"ai-agents-sandbox/docker-dind:{image_tag}",
        ]

        existing, missing = check_docker_images(required_images, console)

        if missing:
            if prompt_build_images(missing, console):
                console.print("\n[cyan]Building images...[/cyan]")
                # Use ai-sbx image build command
                result = subprocess.run(
                    ["ai-sbx", "image", "build", "--tag", image_tag], cwd=worktree_path
                )
                if result.returncode != 0:
                    console.print("[red]Failed to build images[/red]")
                    return
                console.print("[green]✓ Images built successfully[/green]\n")
            else:
                console.print("[yellow]Cannot start DevContainer without required images[/yellow]")
                return

        try:
            # Change to worktree directory for devcontainer commands
            original_cwd = os.getcwd()
            os.chdir(str(worktree_path))

            # Start the devcontainer (this will build images if needed)
            console.print("Starting DevContainer...")
            console.print("[dim]This may take a few moments...[/dim]")

            # Check if devcontainer CLI works (quick test with timeout)
            devcontainer_works = False
            try:
                test_result = subprocess.run(
                    ["timeout", "2", "devcontainer", "--version"],
                    capture_output=True,
                    text=True,
                    cwd=worktree_path,
                )
                if test_result.returncode == 0 and test_result.stdout.strip():
                    devcontainer_works = True
            except Exception:
                pass

            if devcontainer_works:
                # Use devcontainer CLI if it works
                result = subprocess.run(
                    ["devcontainer", "up", "--workspace-folder", "."], cwd=worktree_path
                )
            else:
                # Fallback to docker-compose
                console.print(
                    "[yellow]DevContainer CLI not responding, using docker-compose directly[/yellow]"
                )
                devcontainer_dir = worktree_path / ".devcontainer"
                result = subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        "docker-compose.base.yaml",
                        "-f",
                        "docker-compose.override.yaml",
                        "up",
                        "-d",
                    ],
                    cwd=devcontainer_dir,
                )

            if result.returncode != 0:
                console.print(
                    f"[red]Failed to start DevContainer (exit code: {result.returncode})[/red]"
                )
                os.chdir(original_cwd)
                return

            console.print("[green]✓[/green] DevContainer started successfully")

            # Open interactive shell in the devcontainer
            console.print("[cyan]Opening shell in DevContainer...[/cyan]")
            console.print("[dim]Type 'exit' to leave the container[/dim]\n")

            if devcontainer_works:
                subprocess.run(
                    ["devcontainer", "exec", "--workspace-folder", ".", "/bin/zsh"], cwd=worktree_path
                )
            else:
                # Use docker exec directly
                project_name = worktree_path.name
                subprocess.run(
                    ["docker", "exec", "-it", f"{project_name}-devcontainer-1", "/bin/zsh"]
                )

            os.chdir(original_cwd)
            console.print("\n[green]DevContainer session ended[/green]")
            return

        except Exception as e:
            console.print(f"[red]Failed to start DevContainer: {e}[/red]")
            return

    # Regular IDE handling
    if ide == IDE.VSCODE:
        cmd = ["code", str(worktree_path)]
        console.print("[cyan]Opening VS Code...[/cyan]")
    else:
        # Other IDEs
        ide_commands = {
            IDE.PYCHARM: ["pycharm", str(worktree_path)],
            IDE.RIDER: ["rider", str(worktree_path)],
            IDE.GOLAND: ["goland", str(worktree_path)],
        }

        if ide not in ide_commands:
            return

        cmd = ide_commands[ide]
        console.print(f"[cyan]Opening {ide.value}...[/cyan]")

    # Check if command exists
    if not check_command_exists(cmd[0]):
        # Try with .sh extension
        cmd[0] = f"{cmd[0]}.sh"
        if not check_command_exists(cmd[0]):
            logger.warning(f"IDE command not found: {ide.value}")
            console.print(f"[red]IDE command not found: {ide.value}[/red]")
            return

    try:
        # Run in background
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print(f"[green]✓[/green] {ide.value} opened in background")
        logger.info(f"Opened {ide.value}")

    except Exception as e:
        logger.error(f"Failed to open IDE: {e}")
        console.print(f"[red]Failed to open {ide.value}: {e}[/red]")


def _get_current_branch() -> Optional[str]:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def _get_main_worktree_path() -> Optional[Path]:
    """Get the path of the main worktree (non-worktree checkout)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def _list_worktrees(exclude_current: bool = True) -> list[dict]:
    """Get list of git worktrees.

    Args:
        exclude_current: If True, excludes the main worktree from the list
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        worktrees = []
        current = {}
        main_path = _get_main_worktree_path()

        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                current = {"path": line[9:]}
            elif line.startswith("HEAD "):
                current["commit"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line.startswith("detached"):
                current["detached"] = True

        if current:
            worktrees.append(current)

        # Filter out the main worktree if requested
        if exclude_current and main_path:
            worktrees = [w for w in worktrees if Path(w["path"]) != main_path]

        return worktrees

    except subprocess.CalledProcessError:
        return []


def _get_task_description(worktree_path: Path) -> Optional[str]:
    """Get task description from worktree."""
    # Try to find task description in various locations

    # Check for tasks/{branch}/initial_requirements.md
    tasks_dir = worktree_path / "tasks"
    if tasks_dir.exists():
        for task_dir in tasks_dir.iterdir():
            if task_dir.is_dir():
                req_file = task_dir / "initial_requirements.md"
                if req_file.exists():
                    try:
                        content = req_file.read_text()
                        # Extract first line after "# Task:"
                        for line in content.splitlines():
                            if line.startswith("# Task:"):
                                return line[7:].strip()
                    except Exception:
                        pass

    # Legacy: check task/initial_requirements.md
    req_file = worktree_path / "task" / "initial_requirements.md"
    if req_file.exists():
        try:
            content = req_file.read_text()
            for line in content.splitlines():
                if line.startswith("## Description"):
                    # Get next non-empty line
                    lines = content.splitlines()
                    idx = lines.index(line)
                    for next_line in lines[idx + 1 :]:
                        if next_line.strip():
                            return next_line.strip()
        except Exception:
            pass

    return None


def _get_running_container_name(container_name: str) -> Optional[str]:
    """Get the actual running container name (with or without -1 suffix)."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Check for exact match or with -1 suffix (docker compose adds it)
        container_names = result.stdout.splitlines()
        for name in container_names:
            if name == container_name or name == f"{container_name}-1":
                return name
        return None

    except subprocess.CalledProcessError:
        return None


def _is_container_running(container_name: str) -> bool:
    """Check if a container is running."""
    return _get_running_container_name(container_name) is not None
