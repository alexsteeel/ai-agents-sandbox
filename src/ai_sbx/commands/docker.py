"""Docker management commands for AI Agents Sandbox."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ai_sbx.config import ImageVariant, load_project_config
from ai_sbx.utils import (
    logger,
    run_command,
    is_docker_running,
    find_project_root,
)


@click.group()
def docker() -> None:
    """Manage Docker images and containers for AI Agents Sandbox.

    These commands help you build images, manage containers, and
    handle the Docker environment for your development setup.
    """
    pass


@docker.command()
@click.option(
    "--variant", type=click.Choice([v.value for v in ImageVariant]), help="Image variant to build"
)
@click.option("--all", is_flag=True, help="Build all image variants")
@click.option("--no-cache", is_flag=True, help="Build without using cache")
@click.option("--push", is_flag=True, help="Push images after building")
@click.option("--tag", default="latest", help="Image tag")
@click.pass_context
def build(
    ctx: click.Context,
    variant: Optional[str],
    all: bool,
    no_cache: bool,
    push: bool,
    tag: str,
) -> None:
    """Build Docker images for AI Agents Sandbox.

    This command builds the necessary Docker images for your development
    environment. You can build specific variants or all images at once.

    Examples:

        # Build base image
        ai-sbx docker build

        # Build specific variant
        ai-sbx docker build --variant python

        # Build all variants
        ai-sbx docker build --all

        # Build without cache
        ai-sbx docker build --no-cache
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if not is_docker_running():
        console.print("[red]Docker is not running. Please start Docker first.[/red]")
        sys.exit(1)

    # Determine which images to build
    if all:
        variants_to_build = list(ImageVariant)
    elif variant:
        variants_to_build = [ImageVariant(variant)]
    else:
        # Try to detect from project
        project_root = find_project_root()
        if project_root:
            config = load_project_config(project_root)
            if config:
                variants_to_build = [config.variant]
            else:
                variants_to_build = [ImageVariant.BASE]
        else:
            variants_to_build = [ImageVariant.BASE]

    console.print(f"\n[bold cyan]Building Docker images (tag: {tag})[/bold cyan]\n")

    # Build images
    success_count = 0
    failed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # First build supporting images
        support_images = [
            ("tinyproxy-base", "images/tinyproxy-base"),
            ("tinyproxy", "images/tinyproxy"),
            ("docker-dind", "images/docker-dind"),
        ]

        for image_name, dockerfile_dir in support_images:
            task = progress.add_task(f"Building {image_name}...", total=None)

            if _build_image(
                f"ai-agents-sandbox/{image_name}",
                dockerfile_dir,
                tag,
                no_cache,
                verbose,
            ):
                progress.update(task, description=f"[green]✓[/green] Built {image_name}")
                success_count += 1
            else:
                progress.update(task, description=f"[red]✗[/red] Failed to build {image_name}")
                failed_count += 1

        # Build base image if needed
        if ImageVariant.BASE in variants_to_build or len(variants_to_build) > 1:
            task = progress.add_task("Building base image...", total=None)

            if _build_image(
                "ai-agents-sandbox/base",
                "images/base",
                tag,
                no_cache,
                verbose,
            ):
                progress.update(task, description="[green]✓[/green] Built base image")
                success_count += 1
            else:
                progress.update(task, description="[red]✗[/red] Failed to build base image")
                failed_count += 1
                console.print("\n[red]Cannot build variants without base image[/red]")
                sys.exit(1)

        # Build variant images
        for variant in variants_to_build:
            if variant == ImageVariant.BASE:
                continue  # Already built

            spec = _get_variant_image_spec(variant)
            if spec is None:
                task = progress.add_task(
                    f"Skipping {variant.value} (unsupported in this repo)...", total=None
                )
                progress.update(
                    task, description=f"[yellow]⚠[/yellow] Skipped {variant.value} (unsupported)"
                )
                continue

            image_repo, dockerfile_dir = spec
            task = progress.add_task(f"Building {variant.value} image...", total=None)

            if _build_image(
                image_repo,
                dockerfile_dir,
                tag,
                no_cache,
                verbose,
            ):
                progress.update(task, description=f"[green]✓[/green] Built {variant.value} image")
                success_count += 1
            else:
                progress.update(
                    task, description=f"[red]✗[/red] Failed to build {variant.value} image"
                )
                failed_count += 1

    # Push images if requested
    if push and success_count > 0:
        console.print("\n[cyan]Pushing images...[/cyan]")
        _push_images(variants_to_build, tag, console, verbose)

    # Summary
    console.print("\n[bold]Build Summary:[/bold]")
    console.print(f"  [green]✓ Built: {success_count} images[/green]")
    if failed_count > 0:
        console.print(f"  [red]✗ Failed: {failed_count} images[/red]")


@docker.command()
@click.option("--detach", "-d", is_flag=True, help="Run in background")
@click.option("--build", is_flag=True, help="Build images before starting")
@click.option("--force-recreate", is_flag=True, help="Recreate containers even if config unchanged")
@click.pass_context
def up(ctx: click.Context, detach: bool, build: bool, force_recreate: bool) -> None:
    """Start Docker containers for the current project.

    This command starts all containers defined in your project's
    docker-compose.yaml file.

    Examples:

        # Start containers (attached)
        ai-sbx docker up

        # Start in background
        ai-sbx docker up -d

        # Build and start
        ai-sbx docker up --build
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a project directory[/red]")
        sys.exit(1)

    compose_file = project_root / ".devcontainer" / "docker-compose.yaml"
    if not compose_file.exists():
        console.print("[red].devcontainer/docker-compose.yaml not found[/red]")
        console.print("Run [cyan]ai-sbx init[/cyan] to initialize the project")
        sys.exit(1)

    # Build command
    cmd = ["docker", "compose", "-f", str(compose_file), "up"]

    if detach:
        cmd.append("-d")
    if build:
        cmd.append("--build")
    if force_recreate:
        cmd.append("--force-recreate")

    console.print("[cyan]Starting containers...[/cyan]")

    try:
        if detach:
            run_command(cmd, verbose=verbose)
            console.print("[green]✓ Containers started in background[/green]")
            console.print("\nTo view logs: [cyan]ai-sbx docker logs[/cyan]")
            console.print("To stop: [cyan]ai-sbx docker down[/cyan]")
        else:
            # Run interactively
            subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start containers: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping containers...[/yellow]")


@docker.command()
@click.option("--volumes", "-v", is_flag=True, help="Remove volumes")
@click.option("--remove-orphans", is_flag=True, help="Remove orphaned containers")
@click.pass_context
def down(ctx: click.Context, volumes: bool, remove_orphans: bool) -> None:
    """Stop Docker containers for the current project.

    This command stops and removes all containers defined in your
    project's docker-compose.yaml file.

    Examples:

        # Stop containers
        ai-sbx docker down

        # Stop and remove volumes
        ai-sbx docker down -v
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a project directory[/red]")
        sys.exit(1)

    compose_file = project_root / ".devcontainer" / "docker-compose.yaml"
    if not compose_file.exists():
        console.print("[red].devcontainer/docker-compose.yaml not found[/red]")
        sys.exit(1)

    # Build command
    cmd = ["docker", "compose", "-f", str(compose_file), "down"]

    if volumes:
        cmd.append("-v")
    if remove_orphans:
        cmd.append("--remove-orphans")

    console.print("[cyan]Stopping containers...[/cyan]")

    try:
        run_command(cmd, verbose=verbose)
        console.print("[green]✓ Containers stopped[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to stop containers: {e}[/red]")
        sys.exit(1)


@docker.command()
@click.argument("service", required=False)
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--tail", default=100, help="Number of lines to show")
@click.pass_context
def logs(ctx: click.Context, service: Optional[str], follow: bool, tail: int) -> None:
    """View Docker container logs.

    Examples:

        # View all logs
        ai-sbx docker logs

        # View specific service logs
        ai-sbx docker logs devcontainer

        # Follow logs
        ai-sbx docker logs -f
    """
    console: Console = ctx.obj["console"]

    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a project directory[/red]")
        sys.exit(1)

    compose_file = project_root / ".devcontainer" / "docker-compose.yaml"
    if not compose_file.exists():
        console.print("[red].devcontainer/docker-compose.yaml not found[/red]")
        sys.exit(1)

    # Build command
    cmd = ["docker", "compose", "-f", str(compose_file), "logs"]

    if follow:
        cmd.append("-f")

    cmd.extend(["--tail", str(tail)])

    if service:
        cmd.append(service)

    try:
        # Run interactively
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


@docker.command()
@click.argument("service", default="devcontainer")
@click.argument("command", nargs=-1)
@click.pass_context
def exec(ctx: click.Context, service: str, command: tuple[str, ...]) -> None:
    """Execute a command in a running container.

    Examples:

        # Open shell in devcontainer
        ai-sbx docker exec

        # Run specific command
        ai-sbx docker exec devcontainer ls -la

        # Open shell in different service
        ai-sbx docker exec docker sh
    """
    console: Console = ctx.obj["console"]

    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a project directory[/red]")
        sys.exit(1)

    # Get container base name from project config if available
    base_name = project_root.name
    try:
        cfg = load_project_config(project_root)
        if cfg:
            base_name = cfg.name
    except Exception:
        pass

    container_name = f"{base_name}-{service}"

    # Check if container is running
    try:
        result = run_command(
            ["docker", "ps", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
        )

        if result.returncode != 0 or container_name not in result.stdout:
            console.print(f"[red]Container '{container_name}' is not running[/red]")
            console.print("Start it with: [cyan]ai-sbx docker up[/cyan]")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error checking container status: {e}[/red]")
        sys.exit(1)

    # Build exec command
    if command:
        cmd = ["docker", "exec", container_name] + list(command)
    else:
        # Default to interactive shell with fallback: zsh -> bash -> sh
        cmd = [
            "docker",
            "exec",
            "-it",
            container_name,
            "sh",
            "-lc",
            "if [ -x /bin/zsh ]; then exec /bin/zsh; "
            "elif [ -x /bin/bash ]; then exec /bin/bash; else exec /bin/sh; fi",
        ]

    try:
        # Run interactively
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


@docker.command()
@click.pass_context
def ps(ctx: click.Context) -> None:
    """List running containers for the current project."""
    console: Console = ctx.obj["console"]

    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a project directory[/red]")
        sys.exit(1)

    project_name = project_root.name

    # Get running containers
    try:
        result = run_command(
            ["docker", "ps", "--format", "{{json .}}"],
            check=False,
            capture_output=True,
        )

        if result.returncode != 0:
            console.print("[red]Failed to list containers[/red]")
            sys.exit(1)

        # Parse containers
        import json

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                container = json.loads(line)
                # Filter by project
                if project_name in container.get("Names", ""):
                    containers.append(container)

        if not containers:
            console.print(f"[yellow]No running containers for project '{project_name}'[/yellow]")
            return

        # Display table
        table = Table(title=f"Containers for {project_name}")
        table.add_column("Name", style="cyan")
        table.add_column("Image", style="green")
        table.add_column("Status")
        table.add_column("Ports", style="yellow")

        for container in containers:
            name = container.get("Names", "")
            image = container.get("Image", "")
            status = container.get("State", "")
            ports = container.get("Ports", "")

            # Color status
            if status == "running":
                status = f"[green]{status}[/green]"
            else:
                status = f"[yellow]{status}[/yellow]"

            table.add_row(name, image, status, ports)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error listing containers: {e}[/red]")
        sys.exit(1)


@docker.command()
@click.pass_context
def clean(ctx: click.Context) -> None:
    """Clean up unused Docker resources.

    This command removes:
    - Stopped containers
    - Unused networks
    - Dangling images
    - Build cache
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    console.print("[bold cyan]Cleaning Docker resources[/bold cyan]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Remove stopped containers
        task = progress.add_task("Removing stopped containers...", total=None)
        try:
            result = run_command(
                ["docker", "container", "prune", "-f"],
                capture_output=True,
                verbose=verbose,
            )
            progress.update(task, description="[green]✓[/green] Removed stopped containers")
        except Exception:
            progress.update(task, description="[yellow]⚠[/yellow] Could not remove containers")

        # Remove unused networks
        task = progress.add_task("Removing unused networks...", total=None)
        try:
            result = run_command(
                ["docker", "network", "prune", "-f"],
                capture_output=True,
                verbose=verbose,
            )
            progress.update(task, description="[green]✓[/green] Removed unused networks")
        except Exception:
            progress.update(task, description="[yellow]⚠[/yellow] Could not remove networks")

        # Remove dangling images
        task = progress.add_task("Removing dangling images...", total=None)
        try:
            result = run_command(
                ["docker", "image", "prune", "-f"],
                capture_output=True,
                verbose=verbose,
            )
            progress.update(task, description="[green]✓[/green] Removed dangling images")
        except Exception:
            progress.update(task, description="[yellow]⚠[/yellow] Could not remove images")

        # Clean build cache
        task = progress.add_task("Cleaning build cache...", total=None)
        try:
            result = run_command(
                ["docker", "builder", "prune", "-f"],
                capture_output=True,
                verbose=verbose,
            )
            progress.update(task, description="[green]✓[/green] Cleaned build cache")
        except Exception:
            progress.update(task, description="[yellow]⚠[/yellow] Could not clean build cache")

    console.print("\n[green]Docker cleanup complete![/green]")


def _build_image(
    image_name: str,
    dockerfile_dir: str,
    tag: str,
    no_cache: bool,
    verbose: bool,
) -> bool:
    """Build a Docker image."""
    dockerfile_path = Path(dockerfile_dir)

    if not dockerfile_path.exists():
        # Create minimal Dockerfile for new variants
        dockerfile_path.mkdir(parents=True, exist_ok=True)
        _create_variant_dockerfile(dockerfile_path)

    dockerfile = dockerfile_path / "Dockerfile"
    if not dockerfile.exists():
        logger.error(f"Dockerfile not found: {dockerfile}")
        return False

    # Build command
    cmd = [
        "docker",
        "build",
        "-t",
        f"{image_name}:{tag}",
        "-f",
        str(dockerfile),
    ]

    if no_cache:
        cmd.append("--no-cache")

    # Add build context (parent of dockerfile dir)
    cmd.append(str(dockerfile_path.parent))

    try:
        run_command(cmd, verbose=verbose)
        return True
    except subprocess.CalledProcessError:
        return False


def _create_variant_dockerfile(variant_dir: Path) -> None:
    """Create a minimal Dockerfile for a new variant."""
    variant_name = variant_dir.name

    dockerfile_content = f"""# AI Agents Sandbox - {variant_name.capitalize()} variant
FROM ai-agents-sandbox/base:latest

USER root

# Add {variant_name}-specific installations here

USER claude
WORKDIR /workspace
"""

    (variant_dir / "Dockerfile").write_text(dockerfile_content)


def _push_images(variants: list[ImageVariant], tag: str, console: Console, verbose: bool) -> None:
    """Push images to registry."""
    for variant in variants:
        # Use mapping for image repo
        spec = _get_variant_image_spec(variant)
        if spec is None:
            continue
        image_repo, _ = spec
        image_name = f"{image_repo}:{tag}"

        try:
            console.print(f"Pushing {image_name}...")
            run_command(["docker", "push", image_name], verbose=verbose)
            console.print(f"[green]✓ Pushed {image_name}[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Failed to push {image_name}: {e}[/red]")


def _get_variant_image_spec(variant: ImageVariant) -> Optional[Tuple[str, str]]:
    """Map variant to (image_repo, dockerfile_dir).

    Returns None if variant is not supported by this repository layout.
    """
    mapping = {
        ImageVariant.BASE: ("ai-agents-sandbox/base", "images/base"),
        ImageVariant.MINIMAL: ("ai-agents-sandbox/minimal", "images/minimal"),
        ImageVariant.PYTHON: ("ai-agents-sandbox/python", "images/python"),
        ImageVariant.NODEJS: ("ai-agents-sandbox/nodejs", "images/nodejs"),
        # Repository uses devcontainer-* directories for these variants
        ImageVariant.DOTNET: ("ai-agents-sandbox/devcontainer-dotnet", "images/devcontainer-dotnet"),
        ImageVariant.GOLANG: ("ai-agents-sandbox/devcontainer-golang", "images/devcontainer-golang"),
    }
    return mapping.get(variant)
