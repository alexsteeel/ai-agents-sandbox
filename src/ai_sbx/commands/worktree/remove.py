"""Remove command for worktree management."""

import subprocess
from pathlib import Path
from typing import Optional

import click
import inquirer

from ai_sbx.utils import logger, prompt_yes_no, run_command

from .utils import get_main_worktree_path, get_running_container_name, list_worktrees


@click.command()
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
    from rich.console import Console

    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Get list of worktrees (excluding main repository)
    worktrees = list_worktrees(exclude_current=True)

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
            actual_container = get_running_container_name(container_base_name)
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
        actual_container = get_running_container_name(container_base_name)
        if actual_container:
            containers_to_stop[w["path"]] = actual_container

    # Ask about containers, volumes and branches if not specified via flags
    delete_containers = False
    delete_volumes = False
    if not force:
        # Ask about containers if any are running
        if containers_to_stop:
            delete_containers = prompt_yes_no("Delete associated containers?", default=False)

            # If deleting containers, also ask about volumes
            if delete_containers:
                delete_volumes = prompt_yes_no("Delete associated Docker volumes?", default=False)

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
                if delete_volumes:
                    console.print("    [red]and delete Docker volumes[/red]")

        if not prompt_yes_no("\nContinue?", default=False):
            console.print("[yellow]Cancelled[/yellow]")
            return

    # Remove worktrees
    main_path = get_main_worktree_path()
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
            # Get the project name from the path (used by docker-compose)
            project_name = Path(path).name
            devcontainer_dir = Path(path) / ".devcontainer"

            console.print(f"Stopping docker-compose services for: [cyan]{project_name}[/cyan]")

            # First try to stop using docker-compose
            compose_stopped = False
            if devcontainer_dir.exists():
                # Prepare down command with volume flag if needed
                down_flags = ["down"]
                if delete_volumes:
                    down_flags.append("--volumes")

                try:
                    # Try to stop all services using docker-compose
                    run_command(
                        ["docker", "compose", "-p", project_name] + down_flags,
                        cwd=devcontainer_dir,
                        verbose=verbose,
                        check=False,
                    )
                    console.print(
                        f"[green]✓[/green] Stopped docker-compose services for {project_name}"
                    )
                    if delete_volumes:
                        console.print(f"[green]✓[/green] Removed Docker volumes for {project_name}")
                    compose_stopped = True
                except subprocess.CalledProcessError:
                    # If docker-compose fails, try alternative approach
                    try:
                        run_command(
                            [
                                "docker",
                                "compose",
                                "-f",
                                "docker-compose.base.yaml",
                                "-f",
                                "docker-compose.override.yaml",
                            ]
                            + down_flags,
                            cwd=devcontainer_dir,
                            verbose=verbose,
                            check=False,
                        )
                        console.print(
                            f"[green]✓[/green] Stopped docker-compose services for {project_name}"
                        )
                        if delete_volumes:
                            console.print(
                                f"[green]✓[/green] Removed Docker volumes for {project_name}"
                            )
                        compose_stopped = True
                    except subprocess.CalledProcessError:
                        pass

            # If docker-compose didn't work, fall back to stopping individual containers
            if not compose_stopped:
                # Stop all containers with the project name prefix
                try:
                    # Get all containers with this project name
                    list_result = run_command(
                        [
                            "docker",
                            "ps",
                            "-a",
                            "--filter",
                            f"label=com.docker.compose.project={project_name}",
                            "--format",
                            "{{.Names}}",
                        ],
                        verbose=verbose,
                        check=False,
                        capture_output=True,
                        text=True,
                    )

                    if list_result.stdout:
                        container_names = list_result.stdout.strip().split("\n")
                        for container in container_names:
                            if container:
                                try:
                                    run_command(
                                        ["docker", "stop", container], verbose=verbose, check=False
                                    )
                                    run_command(
                                        ["docker", "rm", container], verbose=verbose, check=False
                                    )
                                    console.print(
                                        f"[green]✓[/green] Stopped and removed container: {container}"
                                    )
                                except subprocess.CalledProcessError:
                                    pass

                        # Also remove volumes if requested
                        if delete_volumes:
                            try:
                                # Get all volumes for this project
                                volume_result = run_command(
                                    [
                                        "docker",
                                        "volume",
                                        "ls",
                                        "--filter",
                                        f"label=com.docker.compose.project={project_name}",
                                        "--format",
                                        "{{.Name}}",
                                    ],
                                    verbose=verbose,
                                    check=False,
                                    capture_output=True,
                                    text=True,
                                )
                                if volume_result.stdout:
                                    volume_names = volume_result.stdout.strip().split("\n")
                                    for volume in volume_names:
                                        if volume:
                                            try:
                                                run_command(
                                                    ["docker", "volume", "rm", volume],
                                                    verbose=verbose,
                                                    check=False,
                                                )
                                                console.print(
                                                    f"[green]✓[/green] Removed volume: {volume}"
                                                )
                                            except subprocess.CalledProcessError:
                                                pass
                            except subprocess.CalledProcessError:
                                pass

                except subprocess.CalledProcessError:
                    # Final fallback: try to stop the originally detected container
                    actual_container = containers_to_stop[path]
                    try:
                        run_command(
                            ["docker", "stop", actual_container], verbose=verbose, check=False
                        )
                        run_command(
                            ["docker", "rm", actual_container], verbose=verbose, check=False
                        )
                        console.print(
                            f"[green]✓[/green] Stopped and removed container: {actual_container}"
                        )
                    except subprocess.CalledProcessError as e:
                        console.print(
                            f"[yellow]Warning: Could not stop/remove containers: {e}[/yellow]"
                        )

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
