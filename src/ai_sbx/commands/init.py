"""Initialize command for setting up AI Agents Sandbox."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
import inquirer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ai_sbx.config import (
    IDE,
    BaseImage,
    GlobalConfig,
    ProjectConfig,
    get_global_config_path,
    load_project_config,
    save_project_config,
)
from ai_sbx.templates import TemplateManager
from ai_sbx.utils import (
    add_user_to_group,
    create_directory,
    detect_ide,
    ensure_group_exists,
    find_project_root,
    get_current_user,
    get_user_home,
    is_docker_running,
    prompt_yes_no,
    run_command,
)


# New clear command structure
@click.command()
@click.option("--wizard", is_flag=True, help="Run interactive setup wizard")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init_global_cmd(ctx: click.Context, wizard: bool, force: bool) -> None:
    """Initialize global AI Agents Sandbox configuration.

    Sets up system-wide configuration including groups and directories.
    This should be run once after installation.
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)
    init_global(console, wizard=wizard, force=force, verbose=verbose)


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--wizard", is_flag=True, help="Run interactive setup wizard")
@click.option(
    "--base-image",
    type=click.Choice([v.value for v in BaseImage]),
    help="Development environment to use (base, dotnet, golang)",
)
@click.option("--ide", type=click.Choice([i.value for i in IDE]), help="Preferred IDE")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init_project_cmd(
    ctx: click.Context,
    path: Optional[Path],
    wizard: bool,
    base_image: Optional[str],
    ide: Optional[str],
    force: bool,
) -> None:
    """Initialize a project for AI Agents Sandbox.

    Creates .devcontainer configuration in the project directory.
    Run this in your repository root before creating worktrees.
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if path is None:
        path = find_project_root() or Path.cwd()

    init_project(
        console,
        path,
        wizard=wizard,
        base_image=base_image,
        ide=ide,
        force=force,
        verbose=verbose,
    )


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--skip-proxy", is_flag=True, help="Skip docker-proxy startup")
@click.pass_context
def init_container_cmd(
    ctx: click.Context,
    path: Optional[Path],
    skip_proxy: bool,
) -> None:
    """Initialize container environment.

    This command is called automatically by devcontainer during startup.
    It sets up permissions and environment variables.
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if not path:
        path = Path.cwd()

    # Call the actual implementation
    project_setup_impl(console, path, skip_proxy, verbose)


def init_global(
    console: Console,
    wizard: bool = False,
    force: bool = False,
    verbose: bool = False,
) -> None:
    """Initialize global AI Agents Sandbox configuration."""
    console.print("\n[bold cyan]AI Agents Sandbox - Global Initialization[/bold cyan]\n")

    # Track all changes made to the system
    system_changes = {
        "directories_created": [],
        "files_created": [],
        "files_modified": [],
        "groups_created": [],
        "user_modifications": [],
        "docker_images_built": [],
        "docker_containers_started": [],
        "errors": [],
    }

    # Check if already initialized
    config_path = get_global_config_path()
    if config_path.exists() and not force:
        console.print("[yellow]Global configuration already exists.[/yellow]")
        if not prompt_yes_no("Do you want to reconfigure?", default=False):
            return

    # Load or create config
    config = GlobalConfig.load() if config_path.exists() else GlobalConfig()

    # Ask user whether to use defaults or run wizard
    if not wizard:  # If wizard not explicitly requested via --wizard flag
        console.print("\n[cyan]AI Agents Sandbox Global Configuration[/cyan]\n")
        use_defaults = prompt_yes_no(
            "Use default configuration settings? (Choose 'No' to customize)", default=True
        )
        if not use_defaults:
            wizard = True  # Switch to wizard mode

    if wizard:
        # Interactive configuration
        console.print("[cyan]Let's configure AI Agents Sandbox for your system.[/cyan]\n")

        questions = [
            inquirer.List(
                "default_ide",
                message="Select your preferred IDE",
                choices=[(i.value.upper(), i.value) for i in IDE],
                default=config.default_ide.value,
            ),
            inquirer.List(
                "default_base_image",
                message="Select default base image",
                choices=[(v.value.capitalize(), v.value) for v in BaseImage],
                default=config.default_base_image.value,
            ),
            inquirer.Text(
                "group_name",
                message="Group name for file sharing",
                default=config.group_name,
            ),
            inquirer.Text(
                "group_gid",
                message="Group ID (GID)",
                default=str(config.group_gid),
                validate=lambda _, x: x.isdigit(),
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            config.default_ide = IDE(answers["default_ide"])
            config.default_base_image = BaseImage(answers["default_base_image"])
            config.group_name = answers["group_name"]
            config.group_gid = int(answers["group_gid"])

        # Custom Registry Configuration
        console.print("\n[cyan]Custom Registry Configuration (Optional)[/cyan]")
        console.print("[dim]You can configure custom Docker registries for caching.[/dim]")
        console.print(
            "[dim]This is useful for corporate environments with private registries.[/dim]\n"
        )

        if prompt_yes_no("Do you want to configure custom registries?", default=False):
            console.print()
            registry_input = inquirer.prompt(
                [
                    inquirer.Text(
                        "custom_registries",
                        message="Enter your custom registry URLs (comma-separated, e.g., proget.company.com,registry.local)",
                        default="",
                    )
                ]
            )

            if registry_input and registry_input["custom_registries"]:
                # Parse registry URLs
                registries = [
                    r.strip() for r in registry_input["custom_registries"].split(",") if r.strip()
                ]
                if registries:
                    config.docker.custom_registries = registries
                    console.print(
                        f"[green]✓ Configured {len(registries)} custom registries[/green]"
                    )

                    # Ask about custom docker-registry-proxy image
                    console.print(
                        "\n[dim]If your registry uses self-signed or internal CA certificates,[/dim]"
                    )
                    console.print(
                        "[dim]you may need a custom docker-registry-proxy image with embedded CA certs.[/dim]\n"
                    )

                    if prompt_yes_no(
                        "Do you have a custom docker-registry-proxy image with CA certificates?",
                        default=False,
                    ):
                        custom_image_input = inquirer.prompt(
                            [
                                inquirer.Text(
                                    "custom_proxy_image",
                                    message="Enter the custom image name (e.g., myregistry/docker-registry-proxy:custom)",
                                    default="",
                                )
                            ]
                        )

                        if custom_image_input and custom_image_input["custom_proxy_image"]:
                            # Store custom proxy image in build_args
                            config.docker.build_args["DOCKER_REGISTRY_PROXY_IMAGE"] = (
                                custom_image_input["custom_proxy_image"]
                            )
                            console.print(
                                f"[green]✓ Custom proxy image configured: {custom_image_input['custom_proxy_image']}[/green]"
                            )

    # Build Docker images first
    console.print("\n[bold]Step 1: Building Docker images...[/bold]")
    from ai_sbx.commands.image import _image_exists

    # Check if images already exist
    required_images = [
        "ai-agents-sandbox/tinyproxy-base",
        "ai-agents-sandbox/tinyproxy",
        "ai-agents-sandbox/docker-dind",
        "ai-agents-sandbox/devcontainer",
    ]

    missing_images = [img for img in required_images if not _image_exists(img, "1.0.0")]

    if missing_images:
        console.print(f"[yellow]Found {len(missing_images)} missing images. Building...[/yellow]")
        # Use subprocess to call ai-sbx image build
        try:
            result = subprocess.run(
                ["ai-sbx", "image", "build"], capture_output=not verbose, text=True, check=True
            )
            console.print("[green]✓ Docker images built successfully[/green]")
            system_changes["docker_images_built"].extend(missing_images)
        except subprocess.CalledProcessError as e:
            console.print("[red]✗ Failed to build Docker images[/red]")
            system_changes["errors"].append(f"Failed to build Docker images: {e}")
            if not verbose and e.stderr:
                console.print(f"[dim]{e.stderr}[/dim]")
            console.print("\n[yellow]Try running: ai-sbx image build --verbose[/yellow]")
            sys.exit(1)
    else:
        console.print("[green]✓ All required Docker images already exist[/green]")

    # Copy docker-proxy resources to system location
    console.print("\n[bold]Step 2: Installing docker-proxy resources...[/bold]")

    import ai_sbx

    package_dir = Path(ai_sbx.__file__).parent
    source_proxy_dir = package_dir / "resources" / "docker-proxy"
    target_proxy_dir = Path.home() / ".ai-sbx" / "share" / "docker-proxy"
    source_compose_base = package_dir / "docker-compose.base.yaml"
    target_compose_base = Path.home() / ".ai-sbx" / "share" / "docker-compose.base.yaml"

    try:
        # Create target directory
        if not target_proxy_dir.exists():
            target_proxy_dir.mkdir(parents=True, exist_ok=True)
            system_changes["directories_created"].append(str(target_proxy_dir))

        # Copy docker-compose.yaml for docker-proxy
        source_compose = source_proxy_dir / "docker-compose.yaml"
        target_compose = target_proxy_dir / "docker-compose.yaml"
        if source_compose.exists() and (not target_compose.exists() or force):
            import shutil

            shutil.copy2(str(source_compose), str(target_compose))
            console.print("[green]✓ Docker proxy compose file installed[/green]")
            system_changes[
                "files_created" if not target_compose.exists() else "files_modified"
            ].append(str(target_compose))

        # Copy docker-compose.base.yaml
        if source_compose_base.exists() and (not target_compose_base.exists() or force):
            import shutil

            shutil.copy2(str(source_compose_base), str(target_compose_base))
            console.print("[green]✓ Base compose file installed[/green]")
            system_changes[
                "files_created" if not target_compose_base.exists() else "files_modified"
            ].append(str(target_compose_base))

    except Exception as e:
        console.print(f"[yellow]⚠ Could not install docker-proxy resources: {e}[/yellow]")
        if verbose:
            console.print(f"[dim]Error details: {e}[/dim]")

    # Initialize system with progress display
    console.print("\n[bold]Step 3: Setting up system configuration...[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create group
        task = progress.add_task("Creating system group...", total=None)
        if ensure_group_exists(config.group_name, config.group_gid, verbose=verbose):
            progress.update(task, description="[green]✓[/green] System group created")
            system_changes["groups_created"].append(
                f"{config.group_name} (GID: {config.group_gid})"
            )
        else:
            progress.update(task, description="[red]✗[/red] Failed to create group")
            console.print("\n[red]Some operations require sudo access.[/red]")
            console.print("Please run: [yellow]sudo ai-sbx init global[/yellow]")
            sys.exit(1)

        # Add current user to group
        username = get_current_user()
        if username:
            task = progress.add_task(f"Adding {username} to group...", total=None)
            if add_user_to_group(username, config.group_name, verbose=verbose):
                progress.update(task, description="[green]✓[/green] User added to group")
                system_changes["user_modifications"].append(
                    f"Added {username} to group {config.group_name}"
                )
            else:
                progress.update(task, description="[yellow]⚠[/yellow] Could not add user to group")

        # Create directories
        task = progress.add_task("Creating directories...", total=None)
        home = get_user_home()
        dirs_created = True

        # Create directories with appropriate permissions
        for dir_path, mode in [
            (home / ".ai-sbx" / "notifications", 0o775),  # Group writable
            (home / ".ai-sbx" / "projects", 0o755),
            (config_path.parent, 0o755),
        ]:
            if not create_directory(dir_path, mode=mode):
                dirs_created = False
                system_changes["errors"].append(f"Failed to create directory: {dir_path}")
                break
            else:
                if not dir_path.exists():
                    system_changes["directories_created"].append(str(dir_path))

        # Set group ownership for notifications directory if group exists
        notifications_dir = home / ".ai-sbx" / "notifications"
        if notifications_dir.exists():
            try:
                run_command(
                    ["chgrp", config.group_name, str(notifications_dir)],
                    check=False,
                    verbose=verbose,
                )
            except Exception:
                pass  # Group may not exist yet

        if dirs_created:
            progress.update(task, description="[green]✓[/green] Directories created")
        else:
            progress.update(task, description="[yellow]⚠[/yellow] Some directories not created")

        # Create docker-proxy .env file if custom registries are configured
        if config.docker.custom_registries:
            task = progress.add_task(
                "Configuring docker-proxy for custom registries...", total=None
            )
            try:
                # Ensure docker-proxy directory exists
                proxy_dir = Path.home() / ".ai-sbx" / "share" / "docker-proxy"
                if not proxy_dir.exists():
                    proxy_dir.mkdir(parents=True, exist_ok=True)
                    system_changes["directories_created"].append(str(proxy_dir))

                # Create .env content
                env_content = "# Custom Docker Registry Configuration\n"
                env_content += (
                    f"ADDITIONAL_REGISTRIES={' '.join(config.docker.custom_registries)}\n"
                )
                env_content += f"REGISTRY_WHITELIST={','.join(config.docker.custom_registries)}\n"

                # Add custom proxy image if configured
                custom_proxy_image = config.docker.build_args.get("DOCKER_REGISTRY_PROXY_IMAGE")
                if custom_proxy_image:
                    env_content += "\n# Custom docker-registry-proxy image (with CA certificates)\n"
                    env_content += f"DOCKER_REGISTRY_PROXY_IMAGE={custom_proxy_image}\n"

                # Write .env file
                env_file = proxy_dir / ".env"
                env_file.write_text(env_content)
                env_file.chmod(0o644)
                system_changes["files_created"].append(str(env_file))

                progress.update(
                    task,
                    description="[green]✓[/green] Docker proxy configured for custom registries",
                )
                console.print(f"[dim]Registry configuration saved to {env_file}[/dim]")
            except Exception as e:
                progress.update(
                    task, description="[yellow]⚠[/yellow] Could not configure docker proxy"
                )
                if verbose:
                    console.print(f"[red]Error: {e}[/red]")

        # Save configuration
        task = progress.add_task("Saving configuration...", total=None)
        config.save()
        system_changes["files_created" if not config_path.exists() else "files_modified"].append(
            str(config_path)
        )
        progress.update(task, description="[green]✓[/green] Configuration saved")

    # Start Docker registry proxy
    console.print("\n[bold]Step 3: Starting Docker registry proxy...[/bold]")
    try:
        # Check if proxy is already running
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, check=False
        )

        if "ai-sbx-docker-proxy" not in result.stdout:
            # Use system location for docker-proxy
            proxy_compose = (
                Path.home() / ".ai-sbx" / "share" / "docker-proxy" / "docker-compose.yaml"
            )

            if proxy_compose.exists():
                console.print("[dim]Starting docker-registry-proxy for image caching...[/dim]")
                # Change to the directory containing docker-compose.yaml so .env file is loaded
                subprocess.run(
                    ["docker", "compose", "up", "-d"],
                    capture_output=True,
                    check=False,
                    cwd=proxy_compose.parent,
                )
                console.print("[green]✓ Docker registry proxy started[/green]")
                system_changes["docker_containers_started"].append("ai-sbx-docker-proxy")
                system_changes["docker_containers_started"].append("ai-sbx-tinyproxy-registry")
            else:
                console.print("[yellow]⚠ Could not find docker-proxy configuration[/yellow]")
        else:
            console.print("[green]✓ Docker registry proxy already running[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not start docker-proxy: {e}[/yellow]")

    # Display summary
    console.print("\n[bold green]Global initialization complete![/bold green]\n")

    # Configuration Summary Table
    config_table = Table(title="Configuration Summary", show_header=False)
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value")

    config_table.add_row("Config Path", str(config_path))
    config_table.add_row("Group Name", config.group_name)
    config_table.add_row("Group GID", str(config.group_gid))
    config_table.add_row("Default IDE", config.default_ide.value)
    config_table.add_row("Default Base Image", config.default_base_image.value)
    if config.docker.custom_registries:
        config_table.add_row("Custom Registries", ", ".join(config.docker.custom_registries))
    if config.docker.build_args.get("DOCKER_REGISTRY_PROXY_IMAGE"):
        config_table.add_row(
            "Custom Proxy Image", config.docker.build_args["DOCKER_REGISTRY_PROXY_IMAGE"]
        )

    console.print(config_table)

    # System Changes Report
    console.print("\n[bold]System Changes Report[/bold]")

    changes_table = Table(show_header=True)
    changes_table.add_column("Change Type", style="cyan")
    changes_table.add_column("Details")

    if system_changes["directories_created"]:
        changes_table.add_row(
            "Directories Created", "\n".join(system_changes["directories_created"])
        )

    if system_changes["files_created"]:
        changes_table.add_row("Files Created", "\n".join(system_changes["files_created"]))

    if system_changes["files_modified"]:
        changes_table.add_row("Files Modified", "\n".join(system_changes["files_modified"]))

    if system_changes["groups_created"]:
        changes_table.add_row("Groups Created", "\n".join(system_changes["groups_created"]))

    if system_changes["user_modifications"]:
        changes_table.add_row("User Modifications", "\n".join(system_changes["user_modifications"]))

    if system_changes["docker_images_built"]:
        changes_table.add_row(
            "Docker Images Built", "\n".join(system_changes["docker_images_built"])
        )

    if system_changes["docker_containers_started"]:
        changes_table.add_row(
            "Containers Started", "\n".join(system_changes["docker_containers_started"])
        )

    if system_changes["errors"]:
        changes_table.add_row("[red]Errors[/red]", "\n".join(system_changes["errors"]))

    if any(system_changes[k] for k in system_changes if k != "errors"):
        console.print(changes_table)
    else:
        console.print("[dim]No new changes made to the system (already configured)[/dim]")

    if username:
        console.print(
            "\n[yellow]⚠ Important:[/yellow] Log out and back in for group changes to take effect."
        )


def init_project(
    console: Console,
    project_path: Path,
    wizard: bool = False,
    base_image: Optional[str] = None,
    ide: Optional[str] = None,
    force: bool = False,
    verbose: bool = False,
) -> None:
    """Initialize a project for AI Agents Sandbox."""
    project_path = project_path.resolve()

    console.print(f"\n[bold cyan]Initializing project: {project_path.name}[/bold cyan]\n")

    # Check Docker
    if not is_docker_running():
        console.print("[red]Docker is not running.[/red]")
        console.print("Please start Docker and try again.")
        sys.exit(1)

    # Check for template-based initialization
    devcontainer_dir = project_path / ".devcontainer"
    template_file = devcontainer_dir / "ai-sbx.yaml.template"
    config_file = devcontainer_dir / "ai-sbx.yaml"

    # If template exists but config doesn't, initialize from template
    if template_file.exists() and not config_file.exists():
        console.print("[cyan]Found ai-sbx.yaml.template. Initializing from template...[/cyan]\n")

        # Load the template
        import yaml

        with open(template_file) as f:
            template_data = yaml.safe_load(f)

        # Create config from template
        config = ProjectConfig(
            name=template_data.get("name", project_path.name),
            path=project_path,  # Always use local path
            preferred_ide=IDE(template_data.get("preferred_ide", "vscode")),
            base_image=BaseImage(template_data.get("base_image", "base")),
            main_branch=template_data.get("main_branch"),
        )

        # Apply proxy settings from template
        if "proxy" in template_data:
            proxy_data = template_data["proxy"]
            config.proxy.enabled = True  # Always enabled
            config.proxy.upstream = proxy_data.get("upstream")
            config.proxy.no_proxy = proxy_data.get("no_proxy", [])
            config.proxy.whitelist_domains = proxy_data.get("whitelist_domains", [])

        # Apply docker settings from template
        if "docker" in template_data:
            docker_data = template_data["docker"]
            config.docker.image_tag = docker_data.get("image_tag", "1.0.0")
            config.docker.custom_registries = docker_data.get("custom_registries", [])

        # Apply environment variables from template
        if "environment" in template_data:
            config.environment = template_data["environment"]

        # Save the local configuration
        save_project_config(config)

        # Generate .env file
        manager = TemplateManager()
        env_content = manager._generate_env_file(config)
        env_file = devcontainer_dir / ".env"
        env_file.write_text(env_content)

        console.print(
            f"[green]✅ Project initialized from template![/green]\n\n"
            f"📁 Configuration generated at: {config_file}\n"
            f"🔧 Review .devcontainer/ai-sbx.yaml and adjust if needed\n\n"
            f"[yellow]Next steps:[/yellow]\n"
            f"  1. Run 'ai-sbx init update' if you modify ai-sbx.yaml\n"
            f"  2. Open in your IDE (VS Code: Reopen in Container)\n"
        )
        return

    # Check if already initialized
    existing_config = load_project_config(project_path)
    if existing_config and not force:
        console.print("[yellow]Project already initialized.[/yellow]")
        if not prompt_yes_no("Do you want to reconfigure?", default=False):
            return

    # Load global config for defaults
    global_config = GlobalConfig.load()

    # Get current git branch
    current_branch = None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            current_branch = result.stdout.strip()
    except Exception:
        pass

    # Create or update project config
    if existing_config:
        config = existing_config
        # Update main branch if not set
        if not config.main_branch and current_branch:
            config.main_branch = current_branch
        # Ensure proxy is always enabled for security
        config.proxy.enabled = True
    else:
        config = ProjectConfig(
            name=project_path.name,
            path=project_path,
            preferred_ide=global_config.default_ide,
            base_image=global_config.default_base_image,
            main_branch=current_branch,
        )
        # Ensure proxy is always enabled for security
        config.proxy.enabled = True

    # Apply command-line options
    if base_image:
        config.base_image = BaseImage(base_image)
    if ide:
        config.preferred_ide = IDE(ide)

    # Always run wizard for init project (unless CLI options are provided)
    if not base_image and not ide:
        wizard = True

    # Interactive wizard
    if wizard:
        console.print("[cyan]Let's configure your project step by step.[/cyan]\n")

        # Step 1: Basic Configuration
        console.print("[bold]Step 1: Basic Configuration[/bold]")

        questions = [
            inquirer.Text(
                "name",
                message="Project name",
                default=config.name,
            ),
        ]

        answers = inquirer.prompt(questions)
        if not answers:
            console.print("[red]Setup cancelled.[/red]")
            return
        config.name = answers["name"]

        # Step 2: Development Environment
        console.print("\n[bold]Step 2: Development Environment[/bold]")
        console.print("[dim]Choose the base image that matches your technology stack[/dim]")

        # Determine default selection based on existing config
        default_base_image = (
            config.base_image.value if config.base_image.value != "custom" else "base"
        )
        # If reconfiguring and has custom Docker image, default to "custom_image"
        if existing_config and "CUSTOM_DOCKER_IMAGE" in existing_config.environment:
            default_base_image = "custom_image"

        env_questions = [
            inquirer.List(
                "base_image",
                message="Select base image",
                choices=[
                    ("Base (Python, Node.js, general-purpose)", "base"),
                    (".NET (Base + C#/.NET SDK)", "dotnet"),
                    ("Go (Base + Go compiler)", "golang"),
                    ("Custom (create your own Dockerfile)", "custom"),
                    ("Custom Docker Image (use existing image:tag)", "custom_image"),
                ],
                default=default_base_image,
            ),
        ]

        env_answers = inquirer.prompt(env_questions)
        if not env_answers:
            console.print("[red]Setup cancelled.[/red]")
            return

        custom_dockerfile = False
        custom_docker_image = None

        if env_answers["base_image"] == "custom_image":
            # User wants to use a custom Docker image
            console.print(
                "\n[dim]Enter the Docker image name with tag (e.g., myregistry/myimage:1.0)[/dim]"
            )

            # Auto-fill with existing custom image if reconfiguring
            default_custom_image = ""
            if existing_config and "CUSTOM_DOCKER_IMAGE" in existing_config.environment:
                default_custom_image = existing_config.environment["CUSTOM_DOCKER_IMAGE"]
                console.print(f"[dim]Current custom image: {default_custom_image}[/dim]")

            image_questions = [
                inquirer.Text(
                    "custom_image",
                    message="Docker image:tag",
                    default=default_custom_image,
                    validate=lambda _, x: ":" in x or "Image must include a tag (e.g., image:tag)",
                ),
            ]

            image_answers = inquirer.prompt(image_questions)
            if not image_answers:
                console.print("[red]Setup cancelled.[/red]")
                return

            custom_docker_image = image_answers["custom_image"]
            # Store the custom image in config environment
            config.environment["CUSTOM_DOCKER_IMAGE"] = custom_docker_image
            # Set base_image to base as a fallback
            config.base_image = BaseImage("base")
            console.print(f"[green]✓ Will use custom image: {custom_docker_image}[/green]")

        elif env_answers["base_image"] == "custom":
            # User selected custom, so they definitely want a Dockerfile
            custom_dockerfile = True
            console.print("\n[dim]A custom Dockerfile will be created for you to modify[/dim]")

            # Only ask which base image to extend from
            custom_questions = [
                inquirer.List(
                    "custom_base",
                    message="Which base image to extend from?",
                    choices=[
                        ("Base (Python, Node.js, general-purpose)", "base"),
                        (".NET (Base + C#/.NET SDK)", "dotnet"),
                        ("Go (Base + Go compiler)", "golang"),
                    ],
                    default="base",
                ),
            ]

            custom_answers = inquirer.prompt(custom_questions)
            if custom_answers:
                config.base_image = BaseImage(custom_answers["custom_base"])
        else:
            config.base_image = BaseImage(env_answers["base_image"])

        # Step 2.4: Ask about custom Docker-in-Docker image
        console.print("\n[bold]Step 2.4: Docker-in-Docker Configuration[/bold]")
        console.print(
            "[dim]Docker-in-Docker allows running Docker commands inside the container[/dim]"
        )

        # Auto-fill with existing custom dind image if reconfiguring
        default_custom_dind = ""
        if existing_config and "CUSTOM_DIND_IMAGE" in existing_config.environment:
            default_custom_dind = existing_config.environment["CUSTOM_DIND_IMAGE"]

        dind_questions = [
            inquirer.Confirm(
                "use_custom_dind",
                message="Use a custom Docker-in-Docker image?",
                default=bool(default_custom_dind),
            ),
        ]

        dind_answers = inquirer.prompt(dind_questions)
        if dind_answers and dind_answers.get("use_custom_dind"):
            if default_custom_dind:
                console.print(f"[dim]Current custom DinD image: {default_custom_dind}[/dim]")

            dind_image_questions = [
                inquirer.Text(
                    "custom_dind",
                    message="Docker-in-Docker image:tag",
                    default=default_custom_dind or "docker:dind",
                    validate=lambda _, x: ":" in x
                    or "Image must include a tag (e.g., docker:dind)",
                ),
            ]

            dind_image_answers = inquirer.prompt(dind_image_questions)
            if dind_image_answers and dind_image_answers["custom_dind"]:
                config.environment["CUSTOM_DIND_IMAGE"] = dind_image_answers["custom_dind"]
                console.print(
                    f"[green]✓ Will use custom DinD image: {dind_image_answers['custom_dind']}[/green]"
                )
        elif existing_config and "CUSTOM_DIND_IMAGE" in existing_config.environment:
            # User said no to custom dind, but had one before - remove it
            if "CUSTOM_DIND_IMAGE" in config.environment:
                del config.environment["CUSTOM_DIND_IMAGE"]

        # Step 2.5: Check for Claude settings on host
        console.print("\n[bold]Step 2.5: Claude Code Settings[/bold]")

        # Check if user has Claude settings on host
        home = Path.home()
        claude_dir = home / ".claude"
        has_claude_settings = False
        mount_claude_settings = False

        if claude_dir.exists() and claude_dir.is_dir():
            # Check for any content
            agents_dir = claude_dir / "agents"
            commands_dir = claude_dir / "commands"
            hooks_dir = claude_dir / "hooks"
            settings_file = claude_dir / "settings.json"

            has_agents = agents_dir.exists() and any(agents_dir.glob("*.md"))
            has_commands = commands_dir.exists() and any(commands_dir.glob("*.md"))
            has_hooks = hooks_dir.exists() and any(hooks_dir.glob("*"))
            has_settings = settings_file.exists()

            has_claude_settings = has_agents or has_commands or has_hooks or has_settings

            if has_claude_settings:
                console.print("[green]✓ Found Claude settings on your host system[/green]")
                if has_agents:
                    console.print("  • Agents directory")
                if has_commands:
                    console.print("  • Commands directory")
                if has_hooks:
                    console.print("  • Hooks directory")
                if has_settings:
                    console.print("  • Settings file")

                claude_questions = [
                    inquirer.Confirm(
                        "mount_claude",
                        message="Mount your Claude settings (readonly) in the container?",
                        default=True,
                    ),
                ]

                claude_answers = inquirer.prompt(claude_questions)
                if claude_answers:
                    mount_claude_settings = claude_answers.get("mount_claude", False)
                    if mount_claude_settings:
                        # Store this preference in the config
                        config.environment["MOUNT_CLAUDE_SETTINGS"] = "true"
                        console.print(
                            "[dim]Settings will be mounted readonly and copied on container startup[/dim]"
                        )
        else:
            console.print(
                "[dim]No Claude settings found on host system (using minimal defaults)[/dim]"
            )

        # Step 3: IDE Selection
        console.print("\n[bold]Step 3: IDE/Editor Selection[/bold]")

        # Detect available IDEs on the system
        detected_ides = detect_ide()

        # Build IDE choices - show only detected IDEs plus DevContainer
        ide_choices = []

        # IDE display names
        ide_display_names = {
            "vscode": "VS Code",
            "pycharm": "PyCharm",
            "rider": "Rider (.NET)",
            "goland": "GoLand",
            "webstorm": "WebStorm",
            "intellij": "IntelliJ IDEA",
            "rubymine": "RubyMine",
            "clion": "CLion",
            "datagrip": "DataGrip",
            "phpstorm": "PhpStorm",
            "devcontainer": "DevContainer CLI",
        }

        # Add detected IDEs (without "(detected)" suffix)
        for ide_name in detected_ides:
            if ide_name in ide_display_names:
                ide_choices.append((ide_display_names[ide_name], ide_name))

        # Always add DevContainer option at the end if not already detected
        if "devcontainer" not in detected_ides:
            ide_choices.append(("DevContainer", "devcontainer"))

        # Display detected IDEs info
        if detected_ides:
            detected_display = [ide_display_names.get(ide, ide) for ide in detected_ides]
            console.print(f"[green]✓ Detected IDEs: {', '.join(detected_display)}[/green]")
        else:
            console.print("[yellow]No IDEs detected. DevContainer option available.[/yellow]")

        # Determine default selection
        default_ide = config.preferred_ide.value
        available_values = [c[1] for c in ide_choices]

        if default_ide not in available_values:
            # If preferred IDE not available, use first detected or devcontainer
            default_ide = detected_ides[0] if detected_ides else "devcontainer"

        ide_questions = [
            inquirer.List(
                "ide",
                message="Select your preferred IDE",
                choices=ide_choices,
                default=default_ide,
            ),
        ]

        ide_answers = inquirer.prompt(ide_questions)
        if not ide_answers:
            console.print("[red]Setup cancelled.[/red]")
            return
        config.preferred_ide = IDE(ide_answers["ide"])

        # Step 4: Network & Proxy Configuration
        console.print("\n[bold]Step 4: Network & Proxy Configuration[/bold]")
        console.print("[dim]Network isolation is always enabled for security[/dim]")
        console.print(
            "[dim]Containers can only access whitelisted domains through proxy filtering[/dim]"
        )

        # Always enable proxy for security
        config.proxy.enabled = True

        # Ask for upstream proxy configuration
        console.print("\n[cyan]Corporate/Upstream Proxy Configuration[/cyan]")
        console.print("[dim]Note: Proxy must be accessible from the host machine[/dim]")
        console.print("[dim]Use 'host.gateway' to access services running on the host[/dim]")
        upstream_questions = [
            inquirer.Text(
                "upstream",
                message="Upstream proxy URL (e.g., socks5://host.gateway:8888, http://host.gateway:3128, or empty)",
                default=config.proxy.upstream or "",
                validate=lambda _, x: x == ""
                or x.startswith("http://")
                or x.startswith("socks5://")
                or "Must start with http:// or socks5://",
            ),
        ]

        upstream_answers = inquirer.prompt(upstream_questions)
        if not upstream_answers:
            console.print("[red]Setup cancelled.[/red]")
            return

        if upstream_answers["upstream"]:
            config.proxy.upstream = upstream_answers["upstream"]

            # Ask for no_proxy domains if upstream is configured
            console.print("\n[cyan]Proxy Bypass Configuration[/cyan]")
            no_proxy_questions = [
                inquirer.Text(
                    "no_proxy",
                    message="Domains to bypass upstream proxy (space-separated)",
                    default=(
                        " ".join(config.proxy.no_proxy)
                        if config.proxy.no_proxy
                        else "github.com gitlab.com"
                    ),
                ),
            ]

            no_proxy_answers = inquirer.prompt(no_proxy_questions)
            if no_proxy_answers and no_proxy_answers["no_proxy"]:
                config.proxy.no_proxy = no_proxy_answers["no_proxy"].split()

        # Whitelist domains
        console.print("\n[cyan]Domain Whitelist Configuration[/cyan]")
        console.print("[dim]Default whitelist includes: GitHub, PyPI, npm, Docker registries[/dim]")

        whitelist_questions = [
            inquirer.Text(
                "whitelist",
                message="Additional domains to whitelist (space-separated, or Enter to skip)",
                default=" ".join(config.proxy.whitelist_domains),
            ),
        ]

        whitelist_answers = inquirer.prompt(whitelist_questions)
        if whitelist_answers and whitelist_answers["whitelist"].strip():
            config.proxy.whitelist_domains = whitelist_answers["whitelist"].split()

        # Step 5: Security & Initialization
        console.print("\n[bold]Step 5: Security & Initialization[/bold]")
        console.print("[dim]Configure additional security and initialization options[/dim]")

        # Check if init.secure.sh already exists
        secure_init_path = devcontainer_dir / "init.secure.sh"
        init_secure_exists = secure_init_path.exists()

        if init_secure_exists:
            # File exists - ask whether to keep or replace
            security_questions = [
                inquirer.List(
                    "init_secure_action",
                    message="init.secure.sh already exists. What would you like to do?",
                    choices=[
                        ("Keep existing file (no changes)", "keep"),
                        ("Replace with new template", "replace"),
                        ("View existing file first", "view"),
                    ],
                    default="keep",
                ),
            ]
        else:
            # File doesn't exist - ask whether to create
            security_questions = [
                inquirer.Confirm(
                    "create_secure_init",
                    message="Create init.secure.sh for custom initialization?",
                    default=False,
                ),
            ]

        security_answers = inquirer.prompt(security_questions)

        # Handle the response
        create_secure_init = False
        if security_answers:
            if init_secure_exists:
                if security_answers.get("init_secure_action") == "view":
                    # Show the existing file content
                    console.print("\n[cyan]Current init.secure.sh content:[/cyan]")
                    console.print("[dim]" + "-" * 60 + "[/dim]")
                    with open(secure_init_path) as f:
                        console.print(f.read())
                    console.print("[dim]" + "-" * 60 + "[/dim]\n")

                    # Ask again after viewing
                    replace_questions = [
                        inquirer.Confirm(
                            "replace_after_view",
                            message="Replace with new template?",
                            default=False,
                        ),
                    ]
                    replace_answers = inquirer.prompt(replace_questions)
                    if replace_answers and replace_answers.get("replace_after_view"):
                        create_secure_init = True
                elif security_answers.get("init_secure_action") == "replace":
                    create_secure_init = True
                # "keep" means create_secure_init stays False
            else:
                create_secure_init = security_answers.get("create_secure_init", False)
    else:
        custom_dockerfile = False
        create_secure_init = False

    # Create .devcontainer directory
    devcontainer_dir = project_path / ".devcontainer"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create directory
        task = progress.add_task("Creating .devcontainer directory...", total=None)
        if create_directory(devcontainer_dir):
            progress.update(task, description="[green]✓[/green] Directory created")
        else:
            progress.update(task, description="[red]✗[/red] Failed to create directory")
            sys.exit(1)

        # Generate templates
        task = progress.add_task("Generating configuration files...", total=None)
        template_manager = TemplateManager()

        files_created = template_manager.generate_project_files(
            devcontainer_dir,
            config,
            force=force,
            custom_dockerfile=custom_dockerfile if "custom_dockerfile" in locals() else False,
        )

        if files_created:
            progress.update(task, description="[green]✓[/green] Configuration files created")
        else:
            progress.update(task, description="[yellow]⚠[/yellow] Some files already exist")

        # Copy docker-compose.base.yaml from global share
        task = progress.add_task("Copying docker-compose.base.yaml...", total=None)
        compose_base = devcontainer_dir / "docker-compose.base.yaml"
        base_source = Path.home() / ".ai-sbx" / "share" / "docker-compose.base.yaml"

        if base_source.exists():
            if not compose_base.exists() or force:
                import shutil

                shutil.copy2(base_source, compose_base)
                progress.update(
                    task, description="[green]✓[/green] Copied docker-compose.base.yaml"
                )
            else:
                progress.update(
                    task, description="[yellow]⚠[/yellow] docker-compose.base.yaml already exists"
                )
        else:
            progress.update(
                task, description="[red]✗[/red] docker-compose.base.yaml not found in global share"
            )
            console.print(
                "[yellow]Run 'ai-sbx init global' first to set up global resources[/yellow]"
            )

        # Save project config
        task = progress.add_task("Saving project configuration...", total=None)
        save_project_config(config)
        progress.update(task, description="[green]✓[/green] Configuration saved")

        # Create init.secure.sh if requested
        if "create_secure_init" in locals() and create_secure_init:
            task = progress.add_task("Creating init.secure.sh...", total=None)
            secure_init_path = devcontainer_dir / "init.secure.sh"

            secure_init_content = """#!/bin/bash
# Custom initialization script for the devcontainer
# Runs during container startup as 'claude' user (non-root)

set -e  # Exit on error

echo "Running project initialization..."

# Add your custom initialization commands below:

# Install dependencies
# pip install --user -r requirements.txt
# npm install

# Set up git
# git config user.name "Your Name"
# git config user.email "your.email@example.com"

# Run project setup
# ./scripts/setup.sh

echo "Initialization complete!"
"""

            secure_init_path.write_text(secure_init_content)
            secure_init_path.chmod(0o755)
            progress.update(task, description="[green]✓[/green] init.secure.sh created")

            # Update ai-sbx.yaml to include the init.secure.sh
            config_file = devcontainer_dir / "ai-sbx.yaml"
            if config_file.exists():
                try:
                    import yaml

                    with open(config_file) as f:
                        yaml_config = yaml.safe_load(f)

                    # Add initialization script to config
                    if "initialization" not in yaml_config:
                        yaml_config["initialization"] = {}
                    yaml_config["initialization"]["script"] = "./init.secure.sh"

                    with open(config_file, "w") as f:
                        yaml.safe_dump(yaml_config, f, default_flow_style=False, sort_keys=False)

                    progress.update(
                        task, description="[green]✓[/green] Updated ai-sbx.yaml with init.secure.sh"
                    )
                except Exception:
                    console.print(
                        "[yellow]Note: Please add './init.secure.sh' to your initialization scripts[/yellow]"
                    )

        # Set permissions
        task = progress.add_task("Setting permissions...", total=None)
        try:
            # Make scripts executable
            for script in devcontainer_dir.glob("*.sh"):
                script.chmod(0o755)

            # Set group permissions (best-effort, ignore failures)
            run_command(
                ["chgrp", "-R", global_config.group_name, str(devcontainer_dir)],
                check=False,
                capture_output=True,
            )
            run_command(
                ["chmod", "-R", "g+rw", str(devcontainer_dir)],
                check=False,
                capture_output=True,
            )

            progress.update(task, description="[green]✓[/green] Permissions set")
        except Exception:
            progress.update(task, description="[yellow]⚠[/yellow] Could not set all permissions")

    # Display summary
    console.print("\n[bold green]Project initialization complete![/bold green]\n")

    table = Table(title="Project Configuration", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Project Name", config.name)
    table.add_row("Project Path", str(config.path))
    table.add_row("IDE", config.preferred_ide.value)
    table.add_row("Base Image", config.base_image.value)
    if "custom_dockerfile" in locals() and custom_dockerfile:
        table.add_row("Custom Dockerfile", "Created")
    if "CUSTOM_DOCKER_IMAGE" in config.environment:
        table.add_row("Custom Image", config.environment["CUSTOM_DOCKER_IMAGE"])
    if "CUSTOM_DIND_IMAGE" in config.environment:
        table.add_row("Custom DinD Image", config.environment["CUSTOM_DIND_IMAGE"])
    table.add_row("Network Isolation", "Enabled (always on)")
    if config.proxy.upstream:
        table.add_row("Upstream Proxy", config.proxy.upstream)
    if config.proxy.no_proxy:
        table.add_row("Bypass Domains", ", ".join(config.proxy.no_proxy))
    if config.proxy.whitelist_domains:
        table.add_row("Extra Whitelist", ", ".join(config.proxy.whitelist_domains))
    if "create_secure_init" in locals() and create_secure_init:
        table.add_row("Initialization Script", "init.secure.sh created")

    console.print(table)

    # Next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Verify images: [cyan]ai-sbx image verify[/cyan]")
    console.print("2. [bold yellow]IMPORTANT:[/bold yellow] Commit the .devcontainer folder:")
    console.print(
        '   [cyan]git add .devcontainer && git commit -m "Add devcontainer configuration"[/cyan]'
    )
    console.print("   [dim]This is required for worktrees to access the configuration[/dim]")
    console.print('3. Create worktree: [cyan]ai-sbx worktree create "task name"[/cyan]')

    if config.preferred_ide == IDE.VSCODE:
        console.print(f"4. Open in VS Code: [cyan]code {project_path}[/cyan]")
        console.print("   Then click 'Reopen in Container' when prompted")
    elif config.preferred_ide == IDE.PYCHARM:
        console.print("4. Open in PyCharm: Settings → Python Interpreter → Docker Compose")
    elif config.preferred_ide == IDE.DEVCONTAINER:
        console.print(
            f"4. Open with DevContainer CLI: [cyan]devcontainer open {project_path}[/cyan]"
        )


def project_setup_impl(
    console: Console,
    path: Path,
    skip_proxy: bool,
    verbose: bool = False,
) -> None:
    """Setup project permissions and environment for Docker.

    This command sets up the necessary permissions and environment variables
    for running the project with Docker. It's automatically called by
    devcontainer when starting up.
    """

    # Use current directory if no path provided
    if not path:
        path = Path.cwd()

    path = path.resolve()

    console.print(f"Setting up project: [cyan]{path.name}[/cyan]")

    # Check if we're in a git worktree and handle mounts
    is_worktree = False
    parent_git_dir = None

    # Check if this is a git worktree by looking for .git file (not directory)
    git_file = path / ".git"
    if git_file.is_file():
        try:
            # Read the gitdir path from .git file
            gitdir_content = git_file.read_text().strip()
            if gitdir_content.startswith("gitdir:"):
                gitdir_path = gitdir_content.replace("gitdir:", "").strip()
                is_worktree = True

                # Extract parent git directory (remove /worktrees/... part)
                if "/worktrees/" in gitdir_path:
                    parent_git_dir = gitdir_path.split("/worktrees/")[0]
                    console.print(f"[dim]Detected git worktree, parent: {parent_git_dir}[/dim]")
        except Exception as e:
            console.print(f"[dim]Error reading .git file: {e}[/dim]", verbose=True)

    if is_worktree and not parent_git_dir:
        # Fallback method using git worktree list
        try:
            result = subprocess.run(
                ["git", "worktree", "list"], cwd=path, capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                if str(path) in line:
                    is_worktree = True
                    break
        except Exception:
            pass

    # Create .env file if it doesn't exist
    env_file = path / ".devcontainer" / ".env"
    if not env_file.exists():
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_content = f"""# Project environment variables
PROJECT_NAME={path.name}
PROJECT_DIR={path}
COMPOSE_PROJECT_NAME={path.name}
"""
        env_file.write_text(env_content)
        console.print("[green]✓[/green] Created .env file")
    else:
        console.print("[dim].env file already exists[/dim]")

    # Copy docker-compose.base.yaml to project
    devcontainer_dir = path / ".devcontainer"
    compose_base = devcontainer_dir / "docker-compose.base.yaml"
    base_source = Path.home() / ".ai-sbx" / "share" / "docker-compose.base.yaml"

    if not compose_base.exists() and base_source.exists():
        import shutil

        shutil.copy2(base_source, compose_base)
        console.print("[green]✓[/green] Copied docker-compose.base.yaml")

    # Handle git worktree mount configuration
    if is_worktree and parent_git_dir:
        override_file = path / ".devcontainer" / "docker-compose.override.yaml"

        try:
            import yaml

            # Load existing override file or create new structure
            if override_file.exists():
                with open(override_file) as f:
                    override_config = yaml.safe_load(f) or {}
            else:
                override_config = {}

            # Ensure structure exists
            if "services" not in override_config:
                override_config["services"] = {}
            if "devcontainer" not in override_config["services"]:
                override_config["services"]["devcontainer"] = {}
            if "volumes" not in override_config["services"]["devcontainer"]:
                override_config["services"]["devcontainer"]["volumes"] = []

            # Add parent git mount if not already present
            mount_entry = f"{parent_git_dir}:{parent_git_dir}"
            volumes = override_config["services"]["devcontainer"]["volumes"]

            if mount_entry not in volumes:
                volumes.append(mount_entry)

                # Write updated configuration
                with open(override_file, "w") as f:
                    yaml.safe_dump(override_config, f, default_flow_style=False, sort_keys=False)

                console.print(
                    "[green]✓[/green] Added git worktree mount to docker-compose.override.yaml"
                )
            else:
                console.print("[dim]Git worktree mount already configured[/dim]")

            # Check if we need to configure git safe.directory in running container
            # This is needed when the container is already running and we just added the mount
            try:
                # Check if container is running
                container_name = f"{path.name}-devcontainer-1"
                result = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if container_name in result.stdout:
                    # Configure git safe.directory in the running container
                    subprocess.run(
                        [
                            "docker",
                            "exec",
                            container_name,
                            "git",
                            "config",
                            "--global",
                            "--add",
                            "safe.directory",
                            "/workspace",
                        ],
                        capture_output=True,
                        check=False,
                    )
                    console.print("[green]✓[/green] Configured git safe.directory in container")
            except Exception:
                pass  # Ignore errors, this is optional

        except ImportError:
            console.print(
                "[yellow]⚠[/yellow] PyYAML not available - cannot configure git worktree mount"
            )
            console.print("[dim]Manual configuration needed in docker-compose.override.yaml:[/dim]")
            console.print("[dim]  volumes:[/dim]")
            console.print(f'[dim]    - "{parent_git_dir}:{parent_git_dir}"[/dim]')
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not configure git worktree mount: {e}")

    # Set permissions
    try:
        # Get global config for group name
        global_config = GlobalConfig.load()

        # IMPORTANT: Only set permissions on project files, not on mounted volumes
        # Skip setting permissions if we're inside a container (where path would be /workspace)
        # and avoid changing ownership of mounted directories like ~/.claude/projects

        # Check if we're running inside the container
        in_container = Path("/.dockerenv").exists() or Path("/workspace").samefile(path)

        if in_container:
            console.print("[dim]Skipping recursive permission changes (running in container)[/dim]")
            # Only set permissions on the .devcontainer directory itself
            devcontainer_path = path / ".devcontainer"
            if devcontainer_path.exists():
                run_command(
                    ["chgrp", global_config.group_name, str(devcontainer_path)],
                    check=False,
                    capture_output=True,
                )
                run_command(
                    ["chmod", "g+rw", str(devcontainer_path)],
                    check=False,
                    capture_output=True,
                )
        else:
            # We're on the host, safe to set permissions recursively
            run_command(
                ["chgrp", "-R", global_config.group_name, str(path)],
                check=False,
                capture_output=True,
            )
            run_command(
                ["chmod", "-R", "g+rw", str(path)],
                check=False,
                capture_output=True,
            )
            # Set SGID on directories so new files inherit the group
            run_command(
                ["find", str(path), "-type", "d", "-exec", "chmod", "g+s", "{}", "+"],
                check=False,
                capture_output=True,
            )

        # Make scripts executable
        for script in (path / ".devcontainer").glob("*.sh"):
            script.chmod(0o755)

        console.print("[green]✓[/green] Permissions configured")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Could not set all permissions: {e}")

    # Start docker-proxy if not running (unless skipped)
    if not skip_proxy:
        try:
            # Check if proxy is running
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if "ai-sbx-docker-proxy" not in result.stdout:
                console.print("[dim]Starting docker-proxy...[/dim]")
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "-f",
                        str(Path.home() / ".ai-sbx" / "docker-proxy" / "docker-compose.yaml"),
                        "up",
                        "-d",
                    ],
                    capture_output=True,
                    check=False,
                )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not start docker-proxy: {e}")

    console.print("[green]✓[/green] Project setup complete")


# Wrapper functions for CLI
def run_global_init(console: Console, verbose: bool = False) -> None:
    """Run global initialization."""
    init_global(console, wizard=False, force=False, verbose=verbose)


def run_project_init(
    console: Console, path: str, force: bool = False, verbose: bool = False
) -> None:
    """Run project initialization."""
    project_path = Path(path).resolve()
    init_project(
        console, project_path, wizard=False, base_image=None, ide=None, force=force, verbose=verbose
    )


def run_worktree_init(console: Console, path: str, verbose: bool = False) -> None:
    """Run worktree/container initialization."""
    project_path = Path(path).resolve()
    project_setup_impl(console, project_path, skip_proxy=False, verbose=verbose)


def run_update_env(console: Console, path: str, verbose: bool = False) -> None:
    """Update .env file from ai-sbx.yaml configuration."""
    from pathlib import Path

    project_path = Path(path).resolve()

    # Load existing ai-sbx.yaml
    config = load_project_config(project_path)
    if not config:
        console.print(f"[red]No ai-sbx.yaml found in {project_path / '.devcontainer'}[/red]")
        console.print("Run [cyan]ai-sbx init project[/cyan] first.")
        return

    # Generate new .env file
    template_manager = TemplateManager()
    env_content = template_manager._generate_env_file(config)

    # Write .env file
    env_path = project_path / ".devcontainer" / ".env"
    env_path.write_text(env_content)

    console.print(f"[green]✓[/green] Updated {env_path} from ai-sbx.yaml")

    if verbose:
        console.print("\n[dim]Generated .env content:[/dim]")
        console.print(env_content)
