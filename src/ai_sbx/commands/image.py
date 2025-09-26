"""Docker image management for AI Agents Sandbox."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ai_sbx.utils import AliasedGroup, is_docker_running, logger

# Required images for AI Agents Sandbox
REQUIRED_IMAGES = [
    "ai-agents-sandbox/tinyproxy-base",
    "ai-agents-sandbox/tinyproxy",
    "ai-agents-sandbox/docker-dind",
    "ai-agents-sandbox/devcontainer",
]

OPTIONAL_IMAGES = [
    "ai-agents-sandbox/devcontainer-dotnet",
    "ai-agents-sandbox/devcontainer-golang",
]

# Image build order and directory mapping (relative to images dir)
BUILD_ORDER = [
    ("tinyproxy-base", "tinyproxy-base"),
    ("tinyproxy", "tinyproxy"),
    ("tinyproxy-registry", "tinyproxy-registry"),
    ("docker-dind", "docker-dind"),
    ("devcontainer", "devcontainer-base"),
    ("devcontainer-dotnet", "devcontainer-dotnet"),
    ("devcontainer-golang", "devcontainer-golang"),
]


@click.group(
    cls=AliasedGroup,
    aliases={
        "ls": "list",
        "b": "build",
        "v": "verify",
        "check": "verify",
    },
)
def image() -> None:
    """Manage Docker images for AI Agents Sandbox."""
    pass


@image.command()
@click.option("--all", is_flag=True, help="Build all images including optional environments")
@click.option("--force", is_flag=True, help="Force rebuild even if images exist")
@click.option("--no-cache", is_flag=True, help="Build without using Docker cache")
@click.option("--tag", default="1.0.0", help="Tag for the images (default: 1.0.0)")
@click.option("--show-logs", is_flag=True, help="Show Docker build output")
@click.pass_context
def build(
    ctx: click.Context, all: bool, force: bool, no_cache: bool, tag: str, show_logs: bool
) -> None:
    """Build Docker images for AI Agents Sandbox.

    Builds images from the repository's images/ directory.

    \b
    Examples:
        ai-sbx image build               # Build required images with tag 1.0.0
        ai-sbx image build --tag 1.0.3  # Build with custom tag
        ai-sbx image build --all        # Build all images
        ai-sbx image build --force      # Force rebuild
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if not is_docker_running():
        console.print("[red]Docker is not running. Please start Docker first.[/red]")
        sys.exit(1)

    # Find dockerfiles location (either package or repository)
    images_dir = _find_dockerfiles_dir()
    if not images_dir:
        console.print("[red]Could not find Docker build files.[/red]")
        console.print("Please ensure ai-sbx is properly installed or run from repository.")
        sys.exit(1)

    # Build images directly using Python
    images_to_build = BUILD_ORDER if all else BUILD_ORDER[:5]  # First 5 are required

    # Count images that need building
    images_to_process = []
    for image_name, image_subdir in images_to_build:
        full_path = images_dir / image_subdir
        if not full_path.exists():
            console.print(f"[yellow]Skipping {image_name} - directory not found[/yellow]")
            continue

        full_image_name = f"ai-agents-sandbox/{image_name}"

        # Check if image exists (unless force)
        if not force and _image_exists(full_image_name, tag):
            console.print(f"[dim]Skipping {image_name} - already exists[/dim]")
            continue

        images_to_process.append((image_name, full_path, full_image_name))

    if not images_to_process:
        console.print("[green]All images are already built. Use --force to rebuild.[/green]")
        return

    total_images = len(images_to_process)
    console.print(
        f"[cyan]Building {total_images} Docker image{'s' if total_images > 1 else ''}...[/cyan]"
    )

    if show_logs or verbose:
        # When showing logs, don't use progress spinner
        console.print("[dim]Showing Docker build output...[/dim]\n")

        for idx, (image_name, full_path, full_image_name) in enumerate(images_to_process, 1):
            console.print(f"\n[cyan][{idx}/{total_images}] Building {image_name}...[/cyan]")

            # Build the image with visible output
            success = _build_image(full_image_name, tag, full_path, no_cache=no_cache, verbose=True)

            if success:
                console.print(
                    f"[green]✓ [{idx}/{total_images}] {image_name} built successfully[/green]"
                )
            else:
                console.print(f"[red]✗ [{idx}/{total_images}] Failed to build {image_name}[/red]")
                sys.exit(1)
    else:
        # Use progress spinner when not showing logs
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for idx, (image_name, full_path, full_image_name) in enumerate(images_to_process, 1):
                task = progress.add_task(
                    f"[{idx}/{total_images}] Building {image_name}...", total=None
                )

                # Build the image silently
                success = _build_image(
                    full_image_name, tag, full_path, no_cache=no_cache, verbose=False
                )

                if success:
                    progress.update(
                        task, description=f"[green]✓[/green] [{idx}/{total_images}] {image_name}"
                    )
                else:
                    progress.update(
                        task, description=f"[red]✗[/red] [{idx}/{total_images}] {image_name}"
                    )
                    console.print(f"\n[red]Failed to build {image_name}[/red]")
                    sys.exit(1)

    console.print("\n[green]✓ All images built successfully![/green]")


@image.command(name="list")
@click.pass_context
def list_images(ctx: click.Context) -> None:
    """List AI Agents Sandbox Docker images and their status."""
    console: Console = ctx.obj["console"]

    if not is_docker_running():
        console.print("[red]Docker is not running. Please start Docker first.[/red]")
        sys.exit(1)

    table = Table(title="AI Agents Sandbox Images")
    table.add_column("Image", style="cyan")
    table.add_column("Tag", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Required", style="yellow")

    all_images = REQUIRED_IMAGES + OPTIONAL_IMAGES

    for image_name in all_images:
        is_required = image_name in REQUIRED_IMAGES

        # Check for 1.0.0 tag
        if _image_exists(image_name, "1.0.0"):
            status = "✓ Installed"
            style = "green"
        else:
            status = "✗ Not found"
            style = "red"

        table.add_row(
            image_name.replace("ai-agents-sandbox/", ""),
            "1.0.0",
            f"[{style}]{status}[/{style}]",
            "Yes" if is_required else "No",
        )

    console.print(table)

    # Check if any required images are missing
    missing_required = [img for img in REQUIRED_IMAGES if not _image_exists(img, "1.0.0")]

    if missing_required:
        console.print("\n[yellow]Some required images are missing.[/yellow]")
        console.print("Run: [cyan]ai-sbx image build[/cyan]")


@image.command()
@click.pass_context
def verify(ctx: click.Context) -> None:
    """Verify that all required images are installed."""
    console: Console = ctx.obj["console"]

    if not is_docker_running():
        console.print("[red]Docker is not running. Please start Docker first.[/red]")
        sys.exit(1)

    all_ok = True
    for image_name in REQUIRED_IMAGES:
        if _image_exists(image_name, "1.0.0"):
            console.print(f"[green]✓[/green] {image_name}")
        else:
            console.print(f"[red]✗[/red] {image_name} - missing")
            all_ok = False

    if all_ok:
        console.print("\n[green]All required images are installed![/green]")
    else:
        console.print("\n[red]Some images are missing.[/red]")
        console.print("Run: [cyan]ai-sbx image build[/cyan]")
        sys.exit(1)


def _find_dockerfiles_dir() -> Optional[Path]:
    """Find the dockerfiles directory in the package."""
    import ai_sbx

    package_dir = Path(ai_sbx.__file__).parent
    dockerfiles_dir = package_dir / "dockerfiles"
    if dockerfiles_dir.exists():
        return dockerfiles_dir
    return None


def _build_image(
    image_name: str, tag: str, build_path: Path, no_cache: bool = False, verbose: bool = False
) -> bool:
    """Build a Docker image."""
    try:
        # Build context is the dockerfiles directory itself
        # This allows COPY commands to use relative paths like "common-settings/..."
        build_context = build_path.parent

        cmd = [
            "docker",
            "build",
            "-t",
            f"{image_name}:{tag}",
            "-f",
            str(build_path / "Dockerfile"),
            str(build_context),
        ]

        if no_cache:
            cmd.insert(2, "--no-cache")

        # Add build args
        cmd.extend(["--build-arg", f"IMAGE_TAG={tag}"])

        if verbose:
            result = subprocess.run(cmd, check=True)
        else:
            result = subprocess.run(cmd, capture_output=True, check=True)

        # Also tag as latest
        subprocess.run(
            ["docker", "tag", f"{image_name}:{tag}", f"{image_name}:latest"], capture_output=True
        )

        return True
    except subprocess.CalledProcessError as e:
        if verbose:
            logger.error(f"Failed to build {image_name}: {e}")
        return False


def _image_exists(image_name: str, tag: str) -> bool:
    """Check if a Docker image exists."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", f"{image_name}:{tag}"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False
