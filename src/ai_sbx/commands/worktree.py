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

from ai_sbx.config import IDE, load_project_config, save_project_config
from ai_sbx.utils import (
    check_command_exists,
    detect_ide,
    find_project_root,
    logger,
    prompt_yes_no,
    run_command,
)


@click.group()
def worktree() -> None:
    """Manage git worktrees for isolated development tasks.

    Worktrees allow you to work on multiple branches simultaneously
    in separate directories, each with its own devcontainer environment.
    """
    pass


@worktree.command()
@click.argument("description")
@click.option("--branch", help="Custom branch name")
@click.option("--ide", type=click.Choice(["vscode", "devcontainer", "pycharm", "rider", "goland", "claude"]))
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
    if not no_open and preferred_ide:
        _open_ide(worktree_path, preferred_ide, console, verbose)
        
        # Special handling for devcontainer - it runs interactively, so exit after
        if preferred_ide == IDE.DEVCONTAINER:
            return

    # Show summary
    console.print("\n" + "="*64)
    console.print("[bold green]Task worktree created successfully![/bold green]")
    console.print("")
    console.print(f"[bold]Worktree:[/bold] {worktree_path}")
    console.print(f"[bold]Branch:[/bold] {branch}")
    console.print(f"[bold]Task folder:[/bold] tasks/{branch}")
    console.print(f"[bold]Requirements:[/bold] tasks/{branch}/initial_requirements.md")
    console.print("")
    console.print("Next steps:")
    console.print(f"1. Edit the initial requirements in: tasks/{branch}/initial_requirements.md")
    if preferred_ide == IDE.VSCODE:
        console.print("2. Click 'Reopen in Container' when VS Code prompts")
        console.print("3. Begin development")
    elif preferred_ide == IDE.DEVCONTAINER:
        console.print("2. DevContainer will start automatically")
        console.print("3. Begin development in the container shell")
    else:
        console.print("2. Start the devcontainer if needed")
        console.print("3. Begin development")
    console.print("")
    console.print("To remove this worktree later:")
    console.print(f"  git worktree remove {worktree_path}")
    console.print("="*64)


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

        to_remove = matches
    else:
        # Interactive selection - always use Checkbox for flexibility
        choices = []
        for w in worktrees:
            label = f"{Path(w['path']).name}"
            if w.get("branch"):
                label += f" ({w['branch']})"
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

    # Ask about containers and branches if not specified via flags
    delete_containers = False
    if not force and not delete_branch:
        # Check if any containers exist for the worktrees
        has_containers = False
        for w in to_remove:
            container_name = f"{Path(w['path']).name}-devcontainer"
            if _is_container_running(container_name):
                has_containers = True
                break
        
        if has_containers:
            delete_containers = prompt_yes_no("Delete associated containers?", default=False)
        
        # Ask about branches if not already specified
        if any(w.get("branch") for w in to_remove):
            delete_branch = prompt_yes_no("Delete branches?", default=False)
    
    # Confirm removal
    if not force:
        console.print("\n[yellow]Will remove:[/yellow]")
        for w in to_remove:
            console.print(f"  - {w['path']}")
            if delete_branch and w.get("branch"):
                console.print(f"    [red]and delete branch: {w['branch']}[/red]")
            if delete_containers:
                container_name = f"{Path(w['path']).name}-devcontainer"
                if _is_container_running(container_name):
                    console.print(f"    [red]and stop container: {container_name}[/red]")

        if not prompt_yes_no("\nContinue?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Remove worktrees
    for w in to_remove:
        path = w["path"]
        branch = w.get("branch")
        
        # Stop and remove container if requested
        if delete_containers:
            container_name = f"{Path(path).name}-devcontainer"
            if _is_container_running(container_name):
                console.print(f"Stopping container: [cyan]{container_name}[/cyan]")
                # Try both with and without -1 suffix
                for name in [f"{container_name}-1", container_name]:
                    try:
                        run_command(["docker", "stop", name], verbose=verbose, check=False)
                        run_command(["docker", "rm", name], verbose=verbose, check=False)
                        console.print(f"[green]✓[/green] Stopped and removed container: {name}")
                        break
                    except subprocess.CalledProcessError:
                        continue

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
@click.pass_context
def connect(ctx: click.Context) -> None:
    """Connect to an existing worktree.

    Interactively select a worktree and either open a shell
    in its container or navigate to its directory.
    """
    console: Console = ctx.obj["console"]

    # Get list of worktrees
    worktrees = _list_worktrees()

    if not worktrees:
        console.print("[yellow]No worktrees found[/yellow]")
        return

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

    # Check container status
    container_base_name = f"{path.name}-devcontainer"
    actual_container_name = _get_running_container_name(container_base_name)

    if actual_container_name:
        # Container is running - offer to connect
        console.print(f"[green]Container '{container_base_name}' is running[/green]")

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
            # Connect to container using actual name
            console.print(f"Connecting to container: [cyan]{actual_container_name}[/cyan]")
            console.print("[dim]Type 'exit' to disconnect[/dim]\n")

            # Use subprocess for safer execution with shell fallback
            subprocess.run([
                "docker", "exec", "-it", actual_container_name,
                "sh", "-lc",
                "if [ -x /bin/zsh ]; then exec /bin/zsh; "
                "elif [ -x /bin/bash ]; then exec /bin/bash; else exec /bin/sh; fi"
            ])
        else:
            # Just show cd command
            console.print("\nTo navigate to worktree, run:")
            console.print(f"[cyan]cd {path}[/cyan]")
    else:
        # Container not running
        console.print(f"[yellow]Container '{container_base_name}' is not running[/yellow]")
        console.print("\nTo start the container:")
        console.print(f"1. Navigate to worktree: [cyan]cd {path}[/cyan]")
        console.print("2. Start containers: [cyan]ai-sbx docker up[/cyan]")


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
            container_base_name = f"{path.name}-devcontainer"
            container_status = "running" if _is_container_running(container_base_name) else "stopped"

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


def _create_task_structure(worktree_path: Path, branch_name: str, description: str, console: Console) -> None:
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
        console.print(f"[green]✓[/green] Initial requirements file created")
        logger.debug(f"Created task structure at {task_dir}")

    except Exception as e:
        logger.warning(f"Could not create task structure: {e}")
        console.print(f"[yellow]Warning: Failed to create task structure: {e}[/yellow]")




def _detect_available_ides() -> list[tuple[IDE, str]]:
    """Detect available IDEs on the system."""
    available = []
    
    # Check for VS Code
    if check_command_exists("code"):
        available.append((IDE.VSCODE, "VS Code"))
    
    # Check for devcontainer CLI (VS Code DevContainer)
    if check_command_exists("devcontainer"):
        available.append((IDE.DEVCONTAINER, "VS Code DevContainer"))
    
    # Check for PyCharm
    if check_command_exists("pycharm") or check_command_exists("pycharm.sh"):
        available.append((IDE.PYCHARM, "PyCharm"))
    
    # Check for Rider
    if check_command_exists("rider") or check_command_exists("rider.sh"):
        available.append((IDE.RIDER, "Rider"))
    
    # Check for GoLand
    if check_command_exists("goland") or check_command_exists("goland.sh"):
        available.append((IDE.GOLAND, "GoLand"))
    
    # Check for Claude
    if check_command_exists("claude"):
        available.append((IDE.CLAUDE, "Claude"))
    
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
    available_ides: list[tuple[IDE, str]], 
    project_root: Path,
    console: Console
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
    
    choices = [(name, ide) for ide, name in available_ides]
    choices.append(("Skip (open manually later)", None))
    
    try:
        questions = [
            inquirer.List(
                "ide",
                message="Select IDE to open",
                choices=choices,
            )
        ]
        
        answers = inquirer.prompt(questions)
        if not answers or not answers["ide"]:
            return None
        
        selected_ide = answers["ide"]
        
        # Ask if user wants to save preference (unless it's devcontainer)
        if selected_ide != IDE.DEVCONTAINER:
            if prompt_yes_no(f"Save {selected_ide.value} as preferred IDE for this project?", default=True):
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
            console.print("Install it from: https://code.visualstudio.com/docs/devcontainers/devcontainer-cli")
            return
            
        console.print("[cyan]Preparing DevContainer environment...[/cyan]")
        
        try:
            # Change to worktree directory for devcontainer commands
            import os
            original_cwd = os.getcwd()
            os.chdir(str(worktree_path))
            
            # Start the devcontainer (this will build images if needed)
            console.print("Starting DevContainer (will build images if needed)...")
            console.print("[dim]This may take several minutes on first run...[/dim]")
            
            # Use subprocess.run directly for interactive output
            result = subprocess.run(
                ["devcontainer", "up", "--workspace-folder", "."],
                cwd=worktree_path
            )
            
            if result.returncode != 0:
                console.print(f"[red]Failed to start DevContainer (exit code: {result.returncode})[/red]")
                os.chdir(original_cwd)
                return
                
            console.print("[green]✓[/green] DevContainer started successfully")
            
            # Open interactive shell in the devcontainer
            console.print("[cyan]Opening shell in DevContainer...[/cyan]")
            console.print("[dim]Type 'exit' to leave the container[/dim]\n")
            
            subprocess.run([
                "devcontainer", "exec", 
                "--workspace-folder", ".",
                "/bin/zsh"
            ], cwd=worktree_path)
            
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
            IDE.CLAUDE: ["claude", "--dangerously-skip-permissions"],
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


def _list_worktrees() -> list[dict]:
    """Get list of git worktrees."""
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        worktrees = []
        current = {}

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