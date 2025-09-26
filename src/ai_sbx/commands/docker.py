"""Docker management commands for AI Agents Sandbox."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ai_sbx.config import BaseImage, load_project_config
from ai_sbx.utils import (
    find_project_root,
    is_docker_running,
    logger,
    run_command,
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
    "--environment",
    type=click.Choice([v.value for v in BaseImage]),
    help="Development environment to build (base, dotnet, golang)",
)
@click.option("--all", is_flag=True, help="Build all image environments including support images")
@click.option("--no-cache", is_flag=True, help="Build without using cache")
@click.option("--force", is_flag=True, help="Force rebuild even if images exist")
@click.option("--verify", is_flag=True, help="Only verify that images exist")
@click.option("--push", is_flag=True, help="Push images after building")
@click.option("--tag", default="latest", help="Image tag (default: latest)")
@click.pass_context
def build(
    ctx: click.Context,
    environment: Optional[str],
    all: bool,
    no_cache: bool,
    force: bool,
    verify: bool,
    push: bool,
    tag: str,
) -> None:
    """Build Docker images for AI Agents Sandbox.

    This command builds the necessary Docker images for your development
    environment. You can build specific environments or all images at once.

    Examples:

        # Build base devcontainer image
        ai-sbx docker build

        # Build specific environment
        ai-sbx docker build --environment devcontainer-dotnet

        # Build all images including support
        ai-sbx docker build --all

        # Verify images exist
        ai-sbx docker build --verify

        # Force rebuild even if exists
        ai-sbx docker build --force --all

        # Build without cache
        ai-sbx docker build --no-cache
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if not is_docker_running():
        console.print("[red]Docker is not running. Please start Docker first.[/red]")
        sys.exit(1)

    # Verify mode - just check if images exist
    if verify:
        return _verify_images(console, environment, all, tag)

    # Determine which images to build
    if all:
        environments_to_build = list(BaseImage)
    elif environment:
        environments_to_build = [BaseImage(environment)]
    else:
        # Try to detect from project
        project_root = find_project_root()
        if project_root:
            config = load_project_config(project_root)
            if config:
                environments_to_build = [config.base_image]
            else:
                environments_to_build = [BaseImage.BASE]
        else:
            environments_to_build = [BaseImage.BASE]

    console.print(f"\n[bold cyan]Building Docker images (tag: {tag})[/bold cyan]\n")

    # Build images
    success_count = 0
    failed_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Build order: supporting images first, then base, then environments
        images_to_build = []

        # Always build supporting images first
        if all or any(v for v in environments_to_build):
            images_to_build.extend(
                [
                    ("tinyproxy-base", "images/tinyproxy-base", "ai-agents-sandbox/tinyproxy-base"),
                    ("tinyproxy", "images/tinyproxy", "ai-agents-sandbox/tinyproxy"),
                    (
                        "tinyproxy-registry",
                        "images/tinyproxy-registry",
                        "ai-agents-sandbox/tinyproxy-registry",
                    ),
                    ("docker-dind", "images/docker-dind", "ai-agents-sandbox/docker-dind"),
                ]
            )

        # Add environment images
        for environment in environments_to_build:
            spec = _get_environment_image_spec(environment)
            if spec:
                name, dockerfile_dir, image_repo = spec
                images_to_build.append((name, dockerfile_dir, image_repo))

        # Build all images
        for name, dockerfile_dir, image_repo in images_to_build:
            task = progress.add_task(f"Building {name}...", total=None)

            # Check if dockerfile directory exists
            if not Path(dockerfile_dir).exists():
                progress.update(
                    task, description=f"[yellow]⚠[/yellow] Skipped {name} (directory not found)"
                )
                continue

            # Check if image exists and skip if not forcing
            if not force and _image_exists(image_repo, tag):
                progress.update(
                    task,
                    description=f"[yellow]⚠[/yellow] {name} already exists (use --force to rebuild)",
                )
                continue

            if _build_image(
                image_repo,
                dockerfile_dir,
                tag,
                no_cache,
                verbose,
            ):
                progress.update(task, description=f"[green]✓[/green] Built {name}")
                success_count += 1
            else:
                progress.update(task, description=f"[red]✗[/red] Failed to build {name}")
                failed_count += 1

    # Push images if requested
    if push and success_count > 0:
        console.print("\n[cyan]Pushing images...[/cyan]")
        _push_images(environments_to_build, tag, console, verbose)

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

    # Get container base name from project config
    cfg = load_project_config(project_root)
    if not cfg:
        console.print("[red]Project not initialized. Run 'ai-sbx init' first[/red]")
        sys.exit(1)

    container_name = f"{cfg.name}-{service}"

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
    """List running containers for the current project.

    Uses Docker's Go template format '{{json .}}' to output JSON lines,
    where each line is a separate JSON object representing a container.
    This format is more reliable than the plain 'json' format option.
    """
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
            run_command(
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
            run_command(
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
            run_command(
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
            run_command(
                ["docker", "builder", "prune", "-f"],
                capture_output=True,
                verbose=verbose,
            )
            progress.update(task, description="[green]✓[/green] Cleaned build cache")
        except Exception:
            progress.update(task, description="[yellow]⚠[/yellow] Could not clean build cache")

    console.print("\n[green]Docker cleanup complete![/green]")


def _image_exists(image_name: str, tag: str) -> bool:
    """Check if a Docker image exists locally."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", f"{image_name}:{tag}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _verify_images(
    console: Console, environment: Optional[str], all_images: bool, tag: str
) -> None:
    """Verify that Docker images exist."""
    console.print("\n[bold cyan]Verifying Docker images[/bold cyan]\n")

    images_to_check = []

    # Add support images if checking all
    if all_images:
        images_to_check.extend(
            [
                ("tinyproxy-base", "ai-agents-sandbox/tinyproxy-base"),
                ("tinyproxy", "ai-agents-sandbox/tinyproxy"),
                ("tinyproxy-registry", "ai-agents-sandbox/tinyproxy-registry"),
                ("docker-dind", "ai-agents-sandbox/docker-dind"),
            ]
        )

    # Add environment images
    if all_images:
        for v in BaseImage:
            spec = _get_environment_image_spec(v)
            if spec:
                name, _, image_repo = spec
                images_to_check.append((name, image_repo))
    elif environment:
        v = BaseImage(environment)
        spec = _get_environment_image_spec(v)
        if spec:
            name, _, image_repo = spec
            images_to_check.append((name, image_repo))
    else:
        # Default to base
        spec = _get_environment_image_spec(BaseImage.BASE)
        if spec:
            name, _, image_repo = spec
            images_to_check.append((name, image_repo))

    # Check each image
    missing = []
    found = []

    for name, image_repo in images_to_check:
        if _image_exists(image_repo, tag):
            # Get image size
            try:
                result = subprocess.run(
                    ["docker", "image", "inspect", f"{image_repo}:{tag}", "--format={{.Size}}"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                size_bytes = int(result.stdout.strip())
                size_mb = size_bytes / (1024 * 1024)
                found.append((name, image_repo, f"{size_mb:.1f}MB"))
            except Exception:
                found.append((name, image_repo, "unknown"))
        else:
            missing.append((name, image_repo))

    # Display results
    if found:
        console.print("[green]✓ Found images:[/green]")
        for name, repo, size in found:
            console.print(f"  • {repo}:{tag} ({size})")

    if missing:
        console.print("\n[red]✗ Missing images:[/red]")
        for name, repo in missing:
            console.print(f"  • {repo}:{tag}")
        console.print("\n[yellow]Run without --verify to build missing images[/yellow]")
        sys.exit(1)
    else:
        console.print("\n[green]All required images are present![/green]")


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
        # Create minimal Dockerfile for new environments
        dockerfile_path.mkdir(parents=True, exist_ok=True)
        _create_environment_dockerfile(dockerfile_path)

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


def _create_environment_dockerfile(environment_dir: Path) -> None:
    """Create a minimal Dockerfile for a new environment."""
    environment_name = environment_dir.name

    dockerfile_content = f"""# AI Agents Sandbox - {environment_name.capitalize()} environment
FROM ai-agents-sandbox/base:latest

USER root

# Add {environment_name}-specific installations here

USER claude
WORKDIR /workspace
"""

    (environment_dir / "Dockerfile").write_text(dockerfile_content)


def _push_images(environments: list[BaseImage], tag: str, console: Console, verbose: bool) -> None:
    """Push images to registry."""
    for environment in environments:
        # Use mapping for image repo
        spec = _get_environment_image_spec(environment)
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


def _get_environment_image_spec(environment: BaseImage) -> Optional[tuple[str, str, str]]:
    """Map environment to (name, dockerfile_dir, image_repo).

    Returns None if environment is not supported by this repository layout.
    """
    mapping = {
        BaseImage.BASE: (
            "devcontainer-base",
            "images/devcontainer-base",
            "ai-agents-sandbox/devcontainer",
        ),
        BaseImage.DOTNET: (
            "devcontainer-dotnet",
            "images/devcontainer-dotnet",
            "ai-agents-sandbox/devcontainer-dotnet",
        ),
        BaseImage.GOLANG: (
            "devcontainer-golang",
            "images/devcontainer-golang",
            "ai-agents-sandbox/devcontainer-golang",
        ),
    }
    return mapping.get(environment)
