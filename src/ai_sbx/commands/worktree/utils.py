"""Utility functions for worktree management."""

import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from ai_sbx.config import IDE, load_project_config
from ai_sbx.utils import check_command_exists, logger, prompt_yes_no


def generate_branch_name(description: str) -> str:
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


def copy_secure_init(project_root: Path, worktree_path: Path, console: Console) -> None:
    """Copy init.secure.sh if it exists (for credentials not in git)."""
    secure_init_src = project_root / ".devcontainer" / "init.secure.sh"
    secure_init_dest = worktree_path / ".devcontainer" / "init.secure.sh"

    if secure_init_src.exists():
        console.print("[cyan]Found init.secure.sh, copying to worktree...[/cyan]")

        # Ensure .devcontainer directory exists
        secure_init_dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy the file
        shutil.copy2(secure_init_src, secure_init_dest)

        # Preserve executable permissions
        if os.access(secure_init_src, os.X_OK):
            os.chmod(secure_init_dest, os.stat(secure_init_src).st_mode)

        console.print("[green]✓[/green] Copied init.secure.sh (contains credentials)")
    else:
        logger.debug("No init.secure.sh found")


def create_task_structure(
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


def detect_available_ides() -> list[tuple[IDE, str]]:
    """Detect available IDEs on the system using shared detection logic."""
    from ai_sbx.utils import detect_ide

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


def get_preferred_ide(project_root: Path) -> Optional[IDE]:
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


def save_preferred_ide(project_root: Path, ide: IDE, console: Console) -> None:
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


def prompt_ide_selection(
    available_ides: list[tuple[IDE, str]], project_root: Path, console: Console
) -> Optional[IDE]:
    """Prompt user to select an IDE."""
    import sys

    import inquirer

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
                save_preferred_ide(project_root, selected_ide, console)

        return selected_ide
    except Exception as e:
        console.print(f"[yellow]Cannot prompt for IDE selection: {e}[/yellow]")
        console.print("Available IDEs:")
        for ide, name in available_ides:
            console.print(f"  - {name} ({ide.value})")
        console.print("\nYou can open the project manually or specify --ide option")
        return None


def open_ide(worktree_path: Path, ide: IDE, console: Console, verbose: bool = False) -> None:
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
                    ["devcontainer", "exec", "--workspace-folder", ".", "/bin/zsh"],
                    cwd=worktree_path,
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


def get_current_branch() -> Optional[str]:
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


def get_main_worktree_path() -> Optional[Path]:
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


def list_worktrees(exclude_current: bool = True) -> list[dict]:
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
        main_path = get_main_worktree_path()

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


def get_task_description(worktree_path: Path) -> Optional[str]:
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


def get_running_container_name(container_name: str) -> Optional[str]:
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


def is_container_running(container_name: str) -> bool:
    """Check if a container is running."""
    return get_running_container_name(container_name) is not None
