"""Upgrade command for AI Agents Sandbox."""

import subprocess
import sys
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_sbx import __version__
from ai_sbx.utils import logger, run_command, check_command_exists


def run_upgrade(console: Console, verbose: bool = False) -> None:
    """Upgrade AI Agents Sandbox to the latest version."""
    console.print("\n[bold cyan]AI Agents Sandbox - Upgrade[/bold cyan]\n")
    console.print(f"Current version: [yellow]{__version__}[/yellow]")

    # Check for pip or uv
    has_uv = check_command_exists("uv")
    has_pip = check_command_exists("pip") or check_command_exists("pip3")

    if not has_uv and not has_pip:
        console.print("[red]Neither uv nor pip found. Cannot upgrade.[/red]")
        console.print("Install uv: [cyan]curl -LsSf https://astral.sh/uv/install.sh | sh[/cyan]")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Check for updates
        task = progress.add_task("Checking for updates...", total=None)

        latest_version = get_latest_version(verbose)

        if latest_version:
            progress.update(task, description=f"Latest version: {latest_version}")

            if latest_version == __version__:
                console.print("\n[green]You are already running the latest version![/green]")
                return
        else:
            progress.update(task, description="[yellow]Could not check latest version[/yellow]")

        # Perform upgrade
        task = progress.add_task("Upgrading AI Agents Sandbox...", total=None)

        if has_uv:
            cmd = ["uv", "pip", "install", "--upgrade", "ai-sbx"]
        else:
            pip_cmd = "pip3" if check_command_exists("pip3") else "pip"
            cmd = [pip_cmd, "install", "--upgrade", "ai-sbx"]

        try:
            result = run_command(cmd, capture_output=True, verbose=verbose)

            if result.returncode == 0:
                progress.update(task, description="[green]✓ Upgrade successful[/green]")

                # Verify new version
                new_version = get_installed_version()
                if new_version:
                    console.print(
                        f"\n[green]Successfully upgraded to version {new_version}[/green]"
                    )
                else:
                    console.print("\n[green]Upgrade completed successfully![/green]")

                # Check if images need rebuilding
                if latest_version and version_requires_rebuild(__version__, latest_version):
                    console.print("\n[yellow]This version includes Docker image changes.[/yellow]")
                    console.print("Please rebuild images: [cyan]ai-sbx docker build --all[/cyan]")

            else:
                progress.update(task, description="[red]✗ Upgrade failed[/red]")
                console.print(
                    "\n[red]Failed to upgrade. Please check the error messages above.[/red]"
                )

        except Exception as e:
            progress.update(task, description="[red]✗ Upgrade failed[/red]")
            console.print(f"\n[red]Error during upgrade: {e}[/red]")

            # Suggest manual upgrade
            console.print("\n[yellow]Try manual upgrade:[/yellow]")
            if has_uv:
                console.print("  [cyan]uv pip install --upgrade ai-sbx[/cyan]")
            else:
                console.print("  [cyan]pip install --upgrade ai-sbx[/cyan]")


def get_latest_version(verbose: bool = False) -> Optional[str]:
    """Get the latest version from PyPI."""
    try:
        # Try using pip to check
        result = run_command(
            ["pip", "index", "versions", "ai-sbx"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            # Parse output for latest version
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "Available versions:" in line:
                    versions = line.split(":")[-1].strip().split(",")
                    if versions:
                        return versions[0].strip()

        # Fallback to checking PyPI API
        result = run_command(
            ["curl", "-s", "https://pypi.org/pypi/ai-sbx/json"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            import json

            data = json.loads(result.stdout)
            return data.get("info", {}).get("version")

    except Exception as e:
        if verbose:
            logger.debug(f"Could not check latest version: {e}")

    return None


def get_installed_version() -> Optional[str]:
    """Get the currently installed version."""
    try:
        result = run_command(
            ["ai-sbx", "--version"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            # Parse version from output
            output = result.stdout.strip()
            if "v" in output:
                return output.split("v")[-1].strip()

    except Exception:
        pass

    return None


def version_requires_rebuild(old_version: str, new_version: str) -> bool:
    """Check if version change requires Docker image rebuild."""
    # Parse versions
    old_parts = old_version.split(".")
    new_parts = new_version.split(".")

    # Major or minor version changes typically require rebuild
    if len(old_parts) >= 2 and len(new_parts) >= 2:
        old_major, old_minor = int(old_parts[0]), int(old_parts[1])
        new_major, new_minor = int(new_parts[0]), int(new_parts[1])

        if new_major > old_major or new_minor > old_minor:
            return True

    return False
