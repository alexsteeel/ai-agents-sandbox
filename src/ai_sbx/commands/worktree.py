"""Worktree management commands for AI Agents Sandbox."""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import click
import inquirer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ai_sbx.config import IDE, load_project_config
from ai_sbx.utils import (
    logger,
    run_command,
    find_project_root,
    detect_ide,
    check_command_exists,
)


@click.group()
def worktree():
    """Manage git worktrees for isolated development tasks.

    Worktrees allow you to work on multiple branches simultaneously
    in separate directories, each with its own devcontainer environment.
    """
    pass


@worktree.command()
@click.argument("description")
@click.option("--branch", help="Custom branch name")
@click.option("--ide", type=click.Choice(["vscode", "pycharm", "rider", "goland", "claude"]))
@click.option("--no-open", is_flag=True, help="Don't open IDE after creation")
@click.pass_context
def create(
    ctx: click.Context,
    description: str,
    branch: Optional[str],
    ide: Optional[str],
    no_open: bool,
) -> None:
    """Create a new worktree for a development task.

    This command creates a git worktree with a descriptive branch name,
    sets up the devcontainer environment, and optionally opens your IDE.

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

    try:
        run_command(
            ["git", "worktree", "add", "-b", branch, str(worktree_path)],
            cwd=project_root,
            verbose=verbose,
        )
        logger.success(f"Worktree created at {worktree_path}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to create worktree: {e}[/red]")
        return

    # Create task structure
    _create_task_structure(worktree_path, description, console)

    # Initialize devcontainer
    _initialize_worktree_devcontainer(worktree_path, console, verbose)

    # Open IDE if requested
    if not no_open:
        if ide:
            preferred_ide = IDE(ide)
        else:
            # Load project config or detect IDE
            config = load_project_config(worktree_path)
            if config:
                preferred_ide = config.preferred_ide
            else:
                detected = detect_ide()
                if detected:
                    preferred_ide = IDE(detected[0])
                else:
                    preferred_ide = None

        if preferred_ide:
            _open_ide(worktree_path, preferred_ide, console)

    # Show summary
    console.print("\n[bold green]Worktree created successfully![/bold green]")
    console.print(f"Path: [cyan]{worktree_path}[/cyan]")
    console.print(f"Branch: [cyan]{branch}[/cyan]")
    console.print("\nNext steps:")
    console.print("1. Navigate to worktree: [cyan]cd " + str(worktree_path) + "[/cyan]")
    console.print("2. Start development!")


@worktree.command()
@click.argument("name", required=False)
@click.option("--multiple", "-m", is_flag=True, help="Select multiple worktrees")
@click.option("--all", "-a", is_flag=True, help="Remove all worktrees")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.option("--delete-branch", "-b", is_flag=True, help="Also delete the branch")
@click.pass_context
def remove(
    ctx: click.Context,
    name: Optional[str],
    multiple: bool,
    all: bool,
    force: bool,
    delete_branch: bool,
) -> None:
    """Remove git worktrees and optionally their branches.

    Can remove worktrees by name, partial match, or interactively.
    Supports multiple selection for batch removal.

    Examples:

        # Interactive selection
        ai-sbx worktree remove

        # Remove specific worktree
        ai-sbx worktree remove fix-123

        # Remove multiple interactively
        ai-sbx worktree remove -m

        # Remove and delete branch
        ai-sbx worktree remove fix-123 -b
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Get list of worktrees
    worktrees = _list_worktrees()

    if not worktrees:
        console.print("[yellow]No worktrees found[/yellow]")
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
        elif len(matches) == 1:
            to_remove = matches
        else:
            # Multiple matches - let user choose
            console.print(f"Multiple worktrees match '{name}':")
            choices = []
            for i, w in enumerate(matches, 1):
                path = Path(w["path"])
                branch = w.get("branch", "detached")
                choices.append((f"{path.name} [{branch}]", w))

            if multiple:
                questions = [
                    inquirer.Checkbox(
                        "selection",
                        message="Select worktrees to remove",
                        choices=choices,
                    )
                ]
            else:
                questions = [
                    inquirer.List(
                        "selection",
                        message="Select worktree to remove",
                        choices=choices,
                    )
                ]

            answers = inquirer.prompt(questions)
            if answers:
                if multiple:
                    to_remove = answers["selection"]
                else:
                    to_remove = [answers["selection"]]
    else:
        # Interactive selection
        choices = []
        for w in worktrees:
            if w["path"] == w.get("main_path"):
                continue  # Skip main worktree

            path = Path(w["path"])
            branch = w.get("branch", "detached")
            desc = _get_task_description(path)

            label = f"{path.name} [{branch}]"
            if desc:
                label += f" - {desc}"

            choices.append((label, w))

        if not choices:
            console.print("[yellow]No removable worktrees found[/yellow]")
            return

        if multiple:
            questions = [
                inquirer.Checkbox(
                    "selection",
                    message="Select worktrees to remove (space to select, enter to confirm)",
                    choices=choices,
                )
            ]
        else:
            questions = [
                inquirer.List(
                    "selection",
                    message="Select worktree to remove",
                    choices=choices,
                )
            ]

        answers = inquirer.prompt(questions)
        if not answers:
            return

        if multiple:
            to_remove = answers["selection"]
        else:
            to_remove = [answers["selection"]]

    # Confirm removal
    if not force:
        console.print("\n[yellow]The following worktrees will be removed:[/yellow]")
        for w in to_remove:
            path = Path(w["path"])
            branch = w.get("branch", "detached")
            console.print(f"  • {path.name} [{branch}]")

        if not _confirm_removal(console):
            console.print("[yellow]Removal cancelled[/yellow]")
            return

    # Remove worktrees
    removed_count = 0
    failed_count = 0
    branches_to_delete = []

    for w in to_remove:
        path = Path(w["path"])
        branch = w.get("branch")

        console.print(f"Removing worktree: [cyan]{path.name}[/cyan]")

        try:
            # Force removal to handle uncommitted changes
            run_command(
                ["git", "worktree", "remove", str(path), "--force"],
                check=True,
                verbose=verbose,
            )
            removed_count += 1

            if branch and delete_branch:
                branches_to_delete.append(branch)

            logger.success(f"Removed worktree: {path.name}")

        except subprocess.CalledProcessError as e:
            failed_count += 1
            logger.error(f"Failed to remove worktree {path.name}: {e}")

    # Delete branches if requested
    if branches_to_delete:
        console.print("\n[yellow]Deleting associated branches...[/yellow]")
        for branch in branches_to_delete:
            try:
                run_command(
                    ["git", "branch", "-D", branch],
                    check=True,
                    verbose=verbose,
                )
                logger.success(f"Deleted branch: {branch}")
            except subprocess.CalledProcessError:
                logger.warning(f"Could not delete branch: {branch}")

    # Summary
    console.print(f"\n[green]Removed {removed_count} worktree(s)[/green]")
    if failed_count > 0:
        console.print(f"[red]Failed to remove {failed_count} worktree(s)[/red]")


@worktree.command()
@click.pass_context
def connect(ctx: click.Context) -> None:
    """Connect to an existing worktree interactively.

    Shows a list of all worktrees with their status and allows you
    to connect to the devcontainer if it's running, or just navigate
    to the worktree directory.
    """
    console: Console = ctx.obj["console"]

    # Get worktrees
    worktrees = _list_worktrees()

    if not worktrees:
        console.print("[yellow]No worktrees found[/yellow]")
        return

    # Build choices
    choices = []
    for w in worktrees:
        path = Path(w["path"])
        branch = w.get("branch", "detached")
        commit = w.get("commit", "")[:7]
        desc = _get_task_description(path)

        # Check if path exists
        if not path.exists():
            status = "[red]missing[/red]"
        else:
            # Check if container is running
            container_name = f"{path.name}-devcontainer"
            if _is_container_running(container_name):
                status = "[green]running[/green]"
            else:
                status = "[yellow]stopped[/yellow]"

        label = f"{path.name} [{branch}] {status}"
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

    # Check container status
    container_name = f"{path.name}-devcontainer"

    if _is_container_running(container_name):
        # Container is running - offer to connect
        console.print(f"[green]Container '{container_name}' is running[/green]")

        connect_choices = [
            ("Open shell in container", "shell"),
            ("Just change directory", "cd"),
            ("Cancel", "cancel"),
        ]

        questions = [
            inquirer.List(
                "action",
                message="What would you like to do?",
                choices=connect_choices,
            )
        ]

        answers = inquirer.prompt(questions)
        if not answers or answers["action"] == "cancel":
            return

        if answers["action"] == "shell":
            # Connect to container
            console.print(f"Connecting to container: [cyan]{container_name}[/cyan]")
            console.print("[dim]Type 'exit' to disconnect[/dim]\n")

            os.system(f"docker exec -it {container_name} /bin/zsh")
        else:
            # Just show cd command
            console.print(f"\nTo navigate to worktree, run:")
            console.print(f"[cyan]cd {path}[/cyan]")
    else:
        # Container not running
        console.print(f"[yellow]Container '{container_name}' is not running[/yellow]")
        console.print(f"\nTo start the container:")
        console.print(f"1. Navigate to worktree: [cyan]cd {path}[/cyan]")
        console.print(f"2. Start containers: [cyan]ai-sbx docker up[/cyan]")


@worktree.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.pass_context
def list_worktrees(ctx: click.Context, verbose: bool) -> None:
    """List all git worktrees with their status.

    Shows worktree paths, branches, and task descriptions.
    """
    console: Console = ctx.obj["console"]

    worktrees = _list_worktrees()

    if not worktrees:
        console.print("[yellow]No worktrees found[/yellow]")
        return

    # Create table
    table = Table(title="Git Worktrees", show_lines=True)
    table.add_column("Path", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Commit", style="yellow")

    if verbose:
        table.add_column("Description")
        table.add_column("Modified")
        table.add_column("Container")

    for w in worktrees:
        path = Path(w["path"])
        branch = w.get("branch", "[detached]")
        commit = w.get("commit", "")[:7]

        row = [path.name, branch, commit]

        if verbose:
            # Get task description
            desc = _get_task_description(path) or "-"

            # Get last modified
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                modified = mtime.strftime("%Y-%m-%d %H:%M")
            else:
                modified = "[missing]"

            # Check container status
            container_name = f"{path.name}-devcontainer"
            if _is_container_running(container_name):
                container_status = "[green]running[/green]"
            else:
                container_status = "[dim]stopped[/dim]"

            row.extend([desc, modified, container_status])

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


def _create_task_structure(worktree_path: Path, description: str, console: Console) -> None:
    """Create task directory structure."""
    try:
        # Create task directory
        task_dir = worktree_path / "task"
        task_dir.mkdir(exist_ok=True)

        # Create initial requirements file
        requirements_file = task_dir / "initial_requirements.md"
        requirements_file.write_text(
            f"""# Task Requirements

## Description
{description}

## Objectives
- [ ] 

## Technical Requirements
- 

## Acceptance Criteria
- 

## Notes
Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        )

        logger.debug("Created task structure")

    except Exception as e:
        logger.warning(f"Could not create task structure: {e}")


def _initialize_worktree_devcontainer(worktree_path: Path, console: Console, verbose: bool) -> None:
    """Initialize devcontainer for the worktree."""
    # Check if .devcontainer exists in main repo
    main_repo = find_project_root()
    if not main_repo:
        return

    main_devcontainer = main_repo / ".devcontainer"
    worktree_devcontainer = worktree_path / ".devcontainer"

    if main_devcontainer.exists() and not worktree_devcontainer.exists():
        # Copy .devcontainer from main repo
        import shutil

        try:
            shutil.copytree(main_devcontainer, worktree_devcontainer)
            logger.debug("Copied .devcontainer configuration")

            # Update PROJECT_NAME in .env if it exists
            env_file = worktree_devcontainer / ".env"
            if env_file.exists():
                content = env_file.read_text()
                content = re.sub(
                    r"^PROJECT_NAME=.*$",
                    f"PROJECT_NAME={worktree_path.name}",
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r"^PROJECT_DIR=.*$",
                    f"PROJECT_DIR={worktree_path}",
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r"^COMPOSE_PROJECT_NAME=.*$",
                    f"COMPOSE_PROJECT_NAME={worktree_path.name}",
                    content,
                    flags=re.MULTILINE,
                )
                env_file.write_text(content)

        except Exception as e:
            logger.warning(f"Could not copy .devcontainer: {e}")


def _open_ide(worktree_path: Path, ide: IDE, console: Console) -> None:
    """Open IDE for the worktree."""
    ide_commands = {
        IDE.VSCODE: ["code", str(worktree_path)],
        IDE.PYCHARM: ["pycharm", str(worktree_path)],
        IDE.RIDER: ["rider", str(worktree_path)],
        IDE.GOLAND: ["goland", str(worktree_path)],
        IDE.CLAUDE: ["claude", "--dangerously-skip-permissions"],
    }

    if ide not in ide_commands:
        return

    cmd = ide_commands[ide]

    # Check if command exists
    if not check_command_exists(cmd[0]):
        # Try with .sh extension
        cmd[0] = f"{cmd[0]}.sh"
        if not check_command_exists(cmd[0]):
            logger.warning(f"IDE command not found: {ide.value}")
            return

    try:
        # Open IDE in background
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        console.print(f"[green]Opening {ide.value}...[/green]")
    except Exception as e:
        logger.warning(f"Could not open IDE: {e}")


def _list_worktrees() -> List[dict]:
    """Get list of git worktrees."""
    try:
        result = run_command(
            ["git", "worktree", "list", "--porcelain"],
            check=False,
            capture_output=True,
        )

        if result.returncode != 0:
            return []

        worktrees = []
        current = {}

        for line in result.stdout.strip().split("\n"):
            if not line:
                if current:
                    worktrees.append(current)
                    current = {}
            elif line.startswith("worktree "):
                current["path"] = line[9:]
            elif line.startswith("HEAD "):
                current["commit"] = line[5:]
            elif line.startswith("branch "):
                current["branch"] = line[7:].replace("refs/heads/", "")
            elif line.startswith("detached"):
                current["detached"] = True

        if current:
            worktrees.append(current)

        return worktrees

    except Exception:
        return []


def _get_task_description(worktree_path: Path) -> Optional[str]:
    """Get task description from worktree."""
    req_file = worktree_path / "task" / "initial_requirements.md"

    if not req_file.exists():
        return None

    try:
        content = req_file.read_text()
        # Extract description from markdown
        for line in content.split("\n"):
            if line.startswith("## Description"):
                continue
            if line.strip() and not line.startswith("#"):
                return line.strip()[:50]
    except Exception:
        pass

    return None


def _is_container_running(container_name: str) -> bool:
    """Check if a Docker container is running."""
    try:
        result = run_command(
            ["docker", "ps", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            running_containers = result.stdout.strip().split("\n")
            return container_name in running_containers

    except Exception:
        pass

    return False


def _confirm_removal(console: Console) -> bool:
    """Confirm worktree removal."""
    console.print(
        "\n[yellow]Warning: This will remove the worktree directory and all uncommitted changes.[/yellow]"
    )

    questions = [
        inquirer.Confirm(
            "confirm",
            message="Are you sure you want to continue?",
            default=False,
        )
    ]

    answers = inquirer.prompt(questions)
    return answers and answers["confirm"]
