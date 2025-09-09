"""Utility functions for AI Agents Sandbox."""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler
import logging


class Logger:
    """Custom logger with rich output support."""

    def __init__(self, name: str = "ai-sbx"):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self.console = Console()
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Set up logging handlers."""
        # Remove existing handlers
        self.logger.handlers.clear()

        # Add rich handler
        handler = RichHandler(
            console=self.console,
            show_time=False,
            show_path=False,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def set_verbose(self, verbose: bool) -> None:
        """Enable or disable verbose logging."""
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(f"[yellow]⚠[/yellow] {message}", **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(f"[red]✗[/red] {message}", **kwargs)

    def success(self, message: str, **kwargs: Any) -> None:
        """Log success message."""
        self.logger.info(f"[green]✓[/green] {message}", **kwargs)


# Global logger instance
logger = Logger()


def run_command(
    command: list[str],
    check: bool = True,
    capture_output: bool = True,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    sudo: bool = False,
    verbose: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a shell command with proper error handling.

    Args:
        command: Command and arguments as list
        check: Raise exception on non-zero exit
        capture_output: Capture stdout and stderr
        cwd: Working directory for command
        env: Environment variables
        sudo: Run with sudo
        verbose: Show command output

    Returns:
        CompletedProcess result
    """
    if sudo and not is_root():
        command = ["sudo"] + command

    if verbose:
        logger.debug(f"Running: {' '.join(command)}")

    # Merge environment
    cmd_env = os.environ.copy()
    if env:
        cmd_env.update(env)

    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=capture_output,
            text=True,
            cwd=cwd,
            env=cmd_env,
        )

        if verbose and capture_output:
            if result.stdout:
                logger.debug(f"Output: {result.stdout}")
            if result.stderr:
                logger.debug(f"Error: {result.stderr}")

        return result

    except subprocess.CalledProcessError as e:
        if capture_output:
            logger.error(f"Command failed: {' '.join(command)}")
            if e.stdout:
                logger.error(f"Output: {e.stdout}")
            if e.stderr:
                logger.error(f"Error: {e.stderr}")
        raise


def is_root() -> bool:
    """Check if running as root."""
    return os.geteuid() == 0


def check_command_exists(command: str) -> bool:
    """Check if a command exists in PATH."""
    return shutil.which(command) is not None


def get_platform_info() -> Dict[str, str]:
    """Get platform information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": platform.python_version(),
    }


def ensure_group_exists(group_name: str, gid: int, verbose: bool = False) -> bool:
    """Ensure a group exists with the specified GID.

    Args:
        group_name: Name of the group
        gid: Group ID
        verbose: Show verbose output

    Returns:
        True if group was created or already exists
    """
    try:
        # Check if group exists
        result = run_command(
            ["getent", "group", str(gid)],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            logger.debug(f"Group with GID {gid} already exists")
            return True

        # Create group
        logger.info(f"Creating group '{group_name}' with GID {gid}")
        run_command(
            ["groupadd", "-g", str(gid), group_name],
            sudo=True,
            verbose=verbose,
        )
        logger.success(f"Group '{group_name}' created")
        return True

    except Exception as e:
        logger.error(f"Failed to create group: {e}")
        return False


def add_user_to_group(username: str, group_name: str, verbose: bool = False) -> bool:
    """Add a user to a group.

    Args:
        username: Username to add
        group_name: Group name
        verbose: Show verbose output

    Returns:
        True if user was added or already in group
    """
    try:
        # Check if user is already in group
        result = run_command(
            ["id", "-nG", username],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            groups = result.stdout.strip().split()
            if group_name in groups:
                logger.debug(f"User '{username}' already in group '{group_name}'")
                return True

        # Add user to group
        logger.info(f"Adding user '{username}' to group '{group_name}'")
        run_command(
            ["usermod", "-aG", group_name, username],
            sudo=True,
            verbose=verbose,
        )
        logger.success(f"User added to group")
        logger.warning("Log out and back in for group membership to take effect")
        return True

    except Exception as e:
        logger.error(f"Failed to add user to group: {e}")
        return False


def get_current_user() -> str:
    """Get the current username (handles sudo)."""
    # First check SUDO_USER, then USER
    sudo_user = os.environ.get("SUDO_USER", "")
    if sudo_user:
        return sudo_user
    return os.environ.get("USER", "")


def get_user_home() -> Path:
    """Get the user's home directory (handles sudo)."""
    username = get_current_user()
    if username and username != "root":
        # Try system user database for portability
        try:
            import pwd  # type: ignore

            return Path(pwd.getpwnam(username).pw_dir)
        except Exception:
            # Fallback to standard Linux layout
            return Path(f"/home/{username}")
    return Path.home()


def create_directory(
    path: Path,
    parents: bool = True,
    exist_ok: bool = True,
    mode: Optional[int] = None,
) -> bool:
    """Create a directory with proper permissions.

    Args:
        path: Directory path
        parents: Create parent directories
        exist_ok: Don't error if exists
        mode: Directory permissions

    Returns:
        True if directory was created or exists
    """
    try:
        if mode is not None:
            path.mkdir(parents=parents, exist_ok=exist_ok, mode=mode)
        else:
            path.mkdir(parents=parents, exist_ok=exist_ok)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def copy_template(
    source: Path,
    destination: Path,
    context: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
) -> bool:
    """Copy a template file with optional variable substitution.

    Args:
        source: Source template path
        destination: Destination path
        context: Variables for template substitution
        overwrite: Overwrite existing file

    Returns:
        True if file was copied successfully
    """
    if destination.exists() and not overwrite:
        logger.warning(f"File already exists: {destination}")
        return False

    try:
        if context:
            # Use Jinja2 for template rendering
            from jinja2 import Template

            with open(source) as f:
                template = Template(f.read())

            content = template.render(**context)
            destination.parent.mkdir(parents=True, exist_ok=True)

            with open(destination, "w") as f:
                f.write(content)
        else:
            # Simple copy
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        logger.debug(f"Copied {source} to {destination}")
        return True

    except Exception as e:
        logger.error(f"Failed to copy template: {e}")
        return False


def find_project_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find the project root by looking for .git or .devcontainer.

    Args:
        start_path: Starting directory (default: current)

    Returns:
        Project root path or None
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        if (current / ".git").exists() or (current / ".devcontainer").exists():
            return current
        current = current.parent

    return None


def detect_ide() -> list[str]:
    """Detect installed IDEs.

    Returns:
        List of detected IDE names
    """
    ides = []

    ide_commands = {
        "vscode": ["code"],
        "pycharm": ["pycharm", "pycharm.sh"],
        "rider": ["rider", "rider.sh"],
        "goland": ["goland", "goland.sh"],
        "claude": ["claude"],
    }

    for ide, commands in ide_commands.items():
        for cmd in commands:
            if check_command_exists(cmd):
                ides.append(ide)
                break

    return ides


def format_size(size: int | float) -> str:
    """Format byte size as human-readable string.

    Args:
        size: Size in bytes

    Returns:
        Formatted size string
    """
    x = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if x < 1024.0:
            return f"{x:.1f}{unit}"
        x /= 1024.0
    return f"{x:.1f}PB"


def prompt_yes_no(question: str, default: bool = False) -> bool:
    """Prompt user for yes/no confirmation.

    Args:
        question: Question to ask
        default: Default answer if user presses Enter

    Returns:
        User's answer
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        answer = input(f"{question} [{default_str}]: ").strip().lower()
        if not answer:
            return default
        if answer in ["y", "yes"]:
            return True
        if answer in ["n", "no"]:
            return False
        print("Please answer 'yes' or 'no'")


def get_docker_info() -> Optional[Dict[str, Any]]:
    """Get Docker daemon information.

    Returns:
        Docker info dict or None if Docker not available
    """
    try:
        result = run_command(
            ["docker", "info", "--format", "json"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            import json

            info = json.loads(result.stdout)  # type: ignore[no-any-return]
            # Treat presence of server errors as not running
            if isinstance(info, dict):
                server_errors = info.get("ServerErrors")
                server_version = info.get("ServerVersion")
                if server_errors:
                    return None
                if not server_version:
                    return None
            return info  # type: ignore[return-value]

    except Exception:
        pass

    return None


def is_docker_running() -> bool:
    """Check if Docker daemon is running.

    Returns:
        True if Docker is running
    """
    return get_docker_info() is not None
