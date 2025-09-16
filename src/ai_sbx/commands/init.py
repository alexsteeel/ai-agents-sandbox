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
    GlobalConfig,
    BaseImage,
    ProjectConfig,
    get_global_config_path,
    load_project_config,
    save_project_config,
)
from ai_sbx.templates import TemplateManager
from rich.console import Console

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
    help="Development environment to use (base, dotnet, golang)"
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

    # Check if already initialized
    config_path = get_global_config_path()
    if config_path.exists() and not force:
        console.print("[yellow]Global configuration already exists.[/yellow]")
        if not prompt_yes_no("Do you want to reconfigure?", default=False):
            return

    # Load or create config
    config = GlobalConfig.load() if config_path.exists() else GlobalConfig()

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
                default=config.default_environment.value,
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
        import subprocess
        try:
            result = subprocess.run(
                ["ai-sbx", "image", "build"],
                capture_output=not verbose,
                text=True,
                check=True
            )
            console.print("[green]✓ Docker images built successfully[/green]")
        except subprocess.CalledProcessError as e:
            console.print("[red]✗ Failed to build Docker images[/red]")
            if not verbose and e.stderr:
                console.print(f"[dim]{e.stderr}[/dim]")
            console.print("\n[yellow]Try running: ai-sbx image build --verbose[/yellow]")
            sys.exit(1)
    else:
        console.print("[green]✓ All required Docker images already exist[/green]")
    
    # Initialize system with progress display
    console.print("\n[bold]Step 2: Setting up system configuration...[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Create group
        task = progress.add_task("Creating system group...", total=None)
        if ensure_group_exists(config.group_name, config.group_gid, verbose=verbose):
            progress.update(task, description="[green]✓[/green] System group created")
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
            else:
                progress.update(task, description="[yellow]⚠[/yellow] Could not add user to group")

        # Create directories
        task = progress.add_task("Creating directories...", total=None)
        home = get_user_home()
        dirs_created = True

        # Create directories with appropriate permissions
        for dir_path, mode in [
            (home / ".ai_agents_sandbox" / "notifications", 0o775),  # Group writable
            (home / ".ai_agents_sandbox" / "projects", 0o755),
            (config_path.parent, 0o755),
        ]:
            if not create_directory(dir_path, mode=mode):
                dirs_created = False
                break

        # Set group ownership for notifications directory if group exists
        notifications_dir = home / ".ai_agents_sandbox" / "notifications"
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

        # Save configuration
        task = progress.add_task("Saving configuration...", total=None)
        config.save()
        progress.update(task, description="[green]✓[/green] Configuration saved")
    
    # Start Docker registry proxy
    console.print("\n[bold]Step 3: Starting Docker registry proxy...[/bold]")
    try:
        # Check if proxy is already running
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if "ai-sbx-docker-proxy" not in result.stdout:
            # Find docker-proxy compose file in package
            from pathlib import Path
            import ai_sbx

            package_dir = Path(ai_sbx.__file__).parent
            proxy_compose = package_dir / "resources" / "docker-proxy" / "docker-compose.yaml"

            if not proxy_compose.exists():
                proxy_compose = None
            
            if proxy_compose:
                console.print("[dim]Starting docker-registry-proxy for image caching...[/dim]")
                subprocess.run(
                    ["docker", "compose", "-f", str(proxy_compose), "up", "-d"],
                    capture_output=True,
                    check=False
                )
                console.print("[green]✓ Docker registry proxy started[/green]")
            else:
                console.print("[yellow]⚠ Could not find docker-proxy configuration[/yellow]")
        else:
            console.print("[green]✓ Docker registry proxy already running[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠ Could not start docker-proxy: {e}[/yellow]")

    # Display summary
    console.print("\n[bold green]Global initialization complete![/bold green]\n")

    table = Table(title="Configuration Summary", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Config Path", str(config_path))
    table.add_row("Group Name", config.group_name)
    table.add_row("Group GID", str(config.group_gid))
    table.add_row("Default IDE", config.default_ide.value)
    table.add_row("Default Base Image", config.default_base_image.value)

    console.print(table)

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

        env_questions = [
            inquirer.List(
                "base_image",
                message="Select base image",
                choices=[
                    ("Base (Python, Node.js, general-purpose)", "base"),
                    (".NET (Base + C#/.NET SDK)", "dotnet"),
                    ("Go (Base + Go compiler)", "golang"),
                    ("Custom (create your own Dockerfile)", "custom"),
                ],
                default=config.base_image.value if config.base_image.value != "custom" else "base",
            ),
        ]

        env_answers = inquirer.prompt(env_questions)
        if not env_answers:
            console.print("[red]Setup cancelled.[/red]")
            return

        custom_dockerfile = False
        if env_answers["base_image"] == "custom":
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
                    console.print(f"  • Agents directory")
                if has_commands:
                    console.print(f"  • Commands directory")
                if has_hooks:
                    console.print(f"  • Hooks directory")
                if has_settings:
                    console.print(f"  • Settings file")

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
                        console.print("[dim]Settings will be mounted readonly and copied on container startup[/dim]")
        else:
            console.print("[dim]No Claude settings found on host system (using minimal defaults)[/dim]")

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
        console.print("[dim]Containers can only access whitelisted domains through proxy filtering[/dim]")

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
                validate=lambda _, x: x == "" or x.startswith("http://") or x.startswith("socks5://") or "Must start with http:// or socks5://",
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
                    default=" ".join(config.proxy.no_proxy) if config.proxy.no_proxy else "github.com gitlab.com",
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

        security_questions = [
            inquirer.Confirm(
                "create_secure_init",
                message="Create secure.init.sh for custom initialization?",
                default=False,
            ),
        ]

        security_answers = inquirer.prompt(security_questions)
        create_secure_init = security_answers.get("create_secure_init", False) if security_answers else False
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
        )

        if files_created:
            progress.update(task, description="[green]✓[/green] Configuration files created")
        else:
            progress.update(task, description="[yellow]⚠[/yellow] Some files already exist")

        # Save project config
        task = progress.add_task("Saving project configuration...", total=None)
        save_project_config(config)
        progress.update(task, description="[green]✓[/green] Configuration saved")

        # Create custom Dockerfile if requested
        if 'custom_dockerfile' in locals() and custom_dockerfile:
            task = progress.add_task("Creating custom Dockerfile...", total=None)
            dockerfile_path = devcontainer_dir / "Dockerfile"

            # Determine the base image name
            base_image_tag = config.docker.image_tag
            base_image_prefix = config.docker.image_prefix
            base_image_name = f"{base_image_prefix}/devcontainer"
            if config.base_image == BaseImage.DOTNET:
                base_image_name = f"{base_image_prefix}/devcontainer-dotnet"
            elif config.base_image == BaseImage.GOLANG:
                base_image_name = f"{base_image_prefix}/devcontainer-golang"

            # Build Dockerfile content
            dockerfile_content = f"""# Custom Dockerfile extending {config.base_image.value} base image
FROM {base_image_name}:{base_image_tag}

# Switch to root for system-level changes
USER root

# Add your custom packages and configurations here
# Example: Install additional tools
# RUN apt-get update && apt-get install -y \\
#     your-package \\
#     && rm -rf /var/lib/apt/lists/*

# Example: Install Python packages globally
# RUN pip install --no-cache-dir \\
#     pandas \\
#     numpy

# Example: Install Node packages globally
# RUN npm install -g \\
#     typescript \\
#     @angular/cli

# Example: Copy custom configuration files
# COPY ./custom-config /home/claude/.config
"""

            # Add footer
            dockerfile_content += """
# Switch back to non-root user
USER claude

# Set any additional environment variables
# ENV MY_CUSTOM_VAR="value"
"""

            dockerfile_path.write_text(dockerfile_content)
            progress.update(task, description="[green]✓[/green] Custom Dockerfile created")

            # Update override.user.yaml to use the custom Dockerfile
            override_file = devcontainer_dir / "override.user.yaml"
            try:
                import yaml

                if override_file.exists():
                    with open(override_file, 'r') as f:
                        override_config = yaml.safe_load(f) or {}
                else:
                    override_config = {}

                # Ensure structure exists
                if 'services' not in override_config:
                    override_config['services'] = {}
                if 'devcontainer' not in override_config['services']:
                    override_config['services']['devcontainer'] = {}
                elif override_config['services']['devcontainer'] is None:
                    override_config['services']['devcontainer'] = {}

                # Add build context
                override_config['services']['devcontainer']['build'] = {
                    'context': '.',
                    'dockerfile': 'Dockerfile'
                }

                # Write updated configuration
                with open(override_file, 'w') as f:
                    yaml.safe_dump(override_config, f, default_flow_style=False, sort_keys=False)

                progress.update(task, description="[green]✓[/green] Updated override.user.yaml for custom Dockerfile")
            except ImportError:
                progress.update(task, description="[yellow]⚠[/yellow] Could not update override.user.yaml")
                console.print("[yellow]Please manually add build configuration to override.user.yaml[/yellow]")

        # Create secure.init.sh if requested
        if 'create_secure_init' in locals() and create_secure_init:
            task = progress.add_task("Creating secure.init.sh...", total=None)
            secure_init_path = devcontainer_dir / "secure.init.sh"

            secure_init_content = """#!/bin/bash
# secure.init.sh - Custom initialization script for the devcontainer
# This script runs during container startup with non-root privileges

set -e  # Exit on error

echo "Running secure initialization..."

# Add your custom initialization commands here
# Note: This runs as the 'claude' user, not root

# Example: Set up project-specific environment
# export PROJECT_ENV="development"

# Example: Create necessary directories
# mkdir -p ~/project-data

# Example: Install project dependencies
# if [ -f "requirements.txt" ]; then
#     pip install --user -r requirements.txt
# fi

# Example: Run setup scripts
# if [ -f "./scripts/setup.sh" ]; then
#     ./scripts/setup.sh
# fi

# Example: Configure git for this project
# git config user.name "Your Name"
# git config user.email "your.email@example.com"

# Example: Set up pre-commit hooks
# if [ -f ".pre-commit-config.yaml" ]; then
#     pre-commit install
# fi

echo "Secure initialization complete!"
"""

            secure_init_path.write_text(secure_init_content)
            secure_init_path.chmod(0o755)
            progress.update(task, description="[green]✓[/green] secure.init.sh created")

            # Update ai-sbx.yaml to include the secure.init.sh
            config_file = devcontainer_dir / "ai-sbx.yaml"
            if config_file.exists():
                try:
                    import yaml
                    with open(config_file, 'r') as f:
                        yaml_config = yaml.safe_load(f)

                    # Add initialization script to config
                    if 'initialization' not in yaml_config:
                        yaml_config['initialization'] = {}
                    yaml_config['initialization']['script'] = './secure.init.sh'

                    with open(config_file, 'w') as f:
                        yaml.safe_dump(yaml_config, f, default_flow_style=False, sort_keys=False)

                    progress.update(task, description="[green]✓[/green] Updated ai-sbx.yaml with secure.init.sh")
                except Exception as e:
                    console.print(f"[yellow]Note: Please add './secure.init.sh' to your initialization scripts[/yellow]")

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
    if 'custom_dockerfile' in locals() and custom_dockerfile:
        table.add_row("Custom Dockerfile", "Created")
    table.add_row("Network Isolation", "Enabled (always on)")
    if config.proxy.upstream:
        table.add_row("Upstream Proxy", config.proxy.upstream)
    if config.proxy.no_proxy:
        table.add_row("Bypass Domains", ", ".join(config.proxy.no_proxy))
    if config.proxy.whitelist_domains:
        table.add_row("Extra Whitelist", ", ".join(config.proxy.whitelist_domains))
    if 'create_secure_init' in locals() and create_secure_init:
        table.add_row("Initialization Script", "secure.init.sh created")

    console.print(table)

    # Next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Verify images: [cyan]ai-sbx image verify[/cyan]")
    console.print("2. [bold yellow]IMPORTANT:[/bold yellow] Commit the .devcontainer folder:")
    console.print("   [cyan]git add .devcontainer && git commit -m \"Add devcontainer configuration\"[/cyan]")
    console.print("   [dim]This is required for worktrees to access the configuration[/dim]")
    console.print("3. Create worktree: [cyan]ai-sbx worktree create \"task name\"[/cyan]")

    if config.preferred_ide == IDE.VSCODE:
        console.print(f"4. Open in VS Code: [cyan]code {project_path}[/cyan]")
        console.print("   Then click 'Reopen in Container' when prompted")
    elif config.preferred_ide == IDE.PYCHARM:
        console.print("4. Open in PyCharm: Settings → Python Interpreter → Docker Compose")
    elif config.preferred_ide == IDE.DEVCONTAINER:
        console.print(f"4. Open with DevContainer CLI: [cyan]devcontainer open {project_path}[/cyan]")


import subprocess


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
            logger.debug(f"Error reading .git file: {e}")
    
    if is_worktree and not parent_git_dir:
        # Fallback method using git worktree list
        try:
            result = subprocess.run(
                ["git", "worktree", "list"],
                cwd=path,
                capture_output=True,
                text=True,
                check=True
            )
            for line in result.stdout.splitlines():
                if str(path) in line:
                    is_worktree = True
                    break
        except:
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
        console.print(f"[green]✓[/green] Created .env file")
    else:
        console.print(f"[dim].env file already exists[/dim]")
    
    # Handle git worktree mount configuration
    if is_worktree and parent_git_dir:
        override_file = path / ".devcontainer" / "override.user.yaml"
        
        try:
            import yaml
            
            # Load existing override file or create new structure
            if override_file.exists():
                with open(override_file, 'r') as f:
                    override_config = yaml.safe_load(f) or {}
            else:
                override_config = {}
            
            # Ensure structure exists
            if 'services' not in override_config:
                override_config['services'] = {}
            if 'devcontainer' not in override_config['services']:
                override_config['services']['devcontainer'] = {}
            if 'volumes' not in override_config['services']['devcontainer']:
                override_config['services']['devcontainer']['volumes'] = []
            
            # Add parent git mount if not already present
            mount_entry = f"{parent_git_dir}:{parent_git_dir}"
            volumes = override_config['services']['devcontainer']['volumes']
            
            if mount_entry not in volumes:
                volumes.append(mount_entry)
                
                # Write updated configuration
                with open(override_file, 'w') as f:
                    yaml.safe_dump(override_config, f, default_flow_style=False, sort_keys=False)
                
                console.print(f"[green]✓[/green] Added git worktree mount to override.user.yaml")
            else:
                console.print(f"[dim]Git worktree mount already configured[/dim]")
            
            # Check if we need to configure git safe.directory in running container
            # This is needed when the container is already running and we just added the mount
            try:
                # Check if container is running
                container_name = f"{path.name}-devcontainer-1"
                result = subprocess.run(
                    ["docker", "ps", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if container_name in result.stdout:
                    # Configure git safe.directory in the running container
                    subprocess.run(
                        ["docker", "exec", container_name, "git", "config", "--global", "--add", "safe.directory", "/workspace"],
                        capture_output=True,
                        check=False
                    )
                    console.print(f"[green]✓[/green] Configured git safe.directory in container")
            except Exception:
                pass  # Ignore errors, this is optional
                
        except ImportError:
            console.print(f"[yellow]⚠[/yellow] PyYAML not available - cannot configure git worktree mount")
            console.print(f"[dim]Manual configuration needed in override.user.yaml:[/dim]")
            console.print(f"[dim]  volumes:[/dim]")
            console.print(f'[dim]    - "{parent_git_dir}:{parent_git_dir}"[/dim]')
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not configure git worktree mount: {e}")
    
    # Set permissions
    try:
        # Get global config for group name
        global_config = GlobalConfig.load()
        
        # Set group permissions on entire project directory (best-effort, ignore failures)
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
        
        console.print(f"[green]✓[/green] Permissions configured")
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
                check=False
            )
            if "ai-sbx-docker-proxy" not in result.stdout:
                console.print("[dim]Starting docker-proxy...[/dim]")
                subprocess.run(
                    ["docker", "compose", "-f", "/usr/local/share/ai-agents-sandbox/docker-proxy/docker-compose.yaml", "up", "-d"],
                    capture_output=True,
                    check=False
                )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not start docker-proxy: {e}")
    
    console.print("[green]✓[/green] Project setup complete")



# Wrapper functions for CLI
def run_global_init(console: Console, verbose: bool = False) -> None:
    """Run global initialization."""
    init_global(console, wizard=False, force=False, verbose=verbose)


def run_project_init(console: Console, path: str, force: bool = False, verbose: bool = False) -> None:
    """Run project initialization."""
    project_path = Path(path).resolve()
    init_project(console, project_path, wizard=False, base_image=None, ide=None, force=force, verbose=verbose)


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
