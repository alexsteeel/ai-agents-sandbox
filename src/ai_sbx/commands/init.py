"""Initialize command for setting up AI Agents Sandbox."""

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
    ImageVariant,
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


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--global", "global_init", is_flag=True, help="Initialize global configuration")
@click.option("--wizard", is_flag=True, help="Run interactive setup wizard")
@click.option(
    "--variant", type=click.Choice([v.value for v in ImageVariant]), help="Image variant to use"
)
@click.option("--ide", type=click.Choice([i.value for i in IDE]), help="Preferred IDE")
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init(
    ctx: click.Context,
    path: Optional[Path],
    global_init: bool,
    wizard: bool,
    variant: Optional[str],
    ide: Optional[str],
    force: bool,
) -> None:
    """Initialize AI Agents Sandbox for a project or globally.

    This command sets up the necessary configuration and environment for
    using AI Agents Sandbox. It can be run globally (once per system) or
    per project.

    Examples:

        # Initialize current project
        ai-sbx init

        # Initialize specific project
        ai-sbx init /path/to/project

        # Run interactive wizard
        ai-sbx init --wizard

        # Initialize global configuration
        ai-sbx init --global
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if global_init:
        init_global(console, wizard=wizard, force=force, verbose=verbose)
    else:
        if path is None:
            path = find_project_root() or Path.cwd()
        init_project(
            console,
            path,
            wizard=wizard,
            variant=variant,
            ide=ide,
            force=force,
            verbose=verbose,
        )


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
                "default_variant",
                message="Select default image variant",
                choices=[(v.value.capitalize(), v.value) for v in ImageVariant],
                default=config.default_variant.value,
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
            config.default_variant = ImageVariant(answers["default_variant"])
            config.group_name = answers["group_name"]
            config.group_gid = int(answers["group_gid"])

    # Initialize system with progress display
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
            console.print("Please run: [yellow]sudo ai-sbx init --global[/yellow]")
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

    # Display summary
    console.print("\n[bold green]Global initialization complete![/bold green]\n")

    table = Table(title="Configuration Summary", show_header=False)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    table.add_row("Config Path", str(config_path))
    table.add_row("Group Name", config.group_name)
    table.add_row("Group GID", str(config.group_gid))
    table.add_row("Default IDE", config.default_ide.value)
    table.add_row("Default Variant", config.default_variant.value)

    console.print(table)

    if username:
        console.print(
            "\n[yellow]⚠ Important:[/yellow] Log out and back in for group changes to take effect."
        )


def init_project(
    console: Console,
    project_path: Path,
    wizard: bool = False,
    variant: Optional[str] = None,
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

    # Check if already initialized
    existing_config = load_project_config(project_path)
    if existing_config and not force:
        console.print("[yellow]Project already initialized.[/yellow]")
        if not prompt_yes_no("Do you want to reconfigure?", default=False):
            return

    # Load global config for defaults
    global_config = GlobalConfig.load()

    # Create or update project config
    if existing_config:
        config = existing_config
    else:
        config = ProjectConfig(
            name=project_path.name,
            path=project_path,
            preferred_ide=global_config.default_ide,
            variant=global_config.default_variant,
        )

    # Apply command-line options
    if variant:
        config.variant = ImageVariant(variant)
    if ide:
        config.preferred_ide = IDE(ide)

    # Interactive wizard
    if wizard:
        console.print("[cyan]Let's configure your project.[/cyan]\n")

        # Detect available IDEs
        detected_ides = detect_ide()
        ide_choices = [(i.value.upper(), i.value) for i in IDE]
        if detected_ides:
            console.print(f"[green]Detected IDEs: {', '.join(detected_ides)}[/green]")

        questions = [
            inquirer.Text(
                "name",
                message="Project name",
                default=config.name,
            ),
            inquirer.List(
                "ide",
                message="Preferred IDE",
                choices=ide_choices,
                default=config.preferred_ide.value,
            ),
            inquirer.List(
                "variant",
                message="Image variant",
                choices=[
                    ("Base (minimal)", "base"),
                    ("Python", "python"),
                    (".NET", "dotnet"),
                    ("Go", "golang"),
                    ("Node.js", "nodejs"),
                    ("Rust", "rust"),
                    ("Java", "java"),
                ],
                default=config.variant.value,
            ),
            inquirer.Confirm(
                "proxy",
                message="Enable proxy filtering?",
                default=config.proxy.enabled,
            ),
        ]

        answers = inquirer.prompt(questions)
        if answers:
            config.name = answers["name"]
            config.preferred_ide = IDE(answers["ide"])
            config.variant = ImageVariant(answers["variant"])
            config.proxy.enabled = answers["proxy"]

            # Proxy configuration
            if answers["proxy"]:
                proxy_questions = [
                    inquirer.Text(
                        "upstream",
                        message="Upstream proxy (optional, e.g., http://proxy:3128)",
                        default=config.proxy.upstream or "",
                    ),
                    inquirer.Text(
                        "whitelist",
                        message="Additional whitelist domains (space-separated)",
                        default=" ".join(config.proxy.whitelist_domains),
                    ),
                ]

                proxy_answers = inquirer.prompt(proxy_questions)
                if proxy_answers:
                    if proxy_answers["upstream"]:
                        config.proxy.upstream = proxy_answers["upstream"]
                    if proxy_answers["whitelist"]:
                        config.proxy.whitelist_domains = proxy_answers["whitelist"].split()

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
    table.add_row("Variant", config.variant.value)
    table.add_row("Proxy Enabled", "Yes" if config.proxy.enabled else "No")
    if config.proxy.upstream:
        table.add_row("Upstream Proxy", config.proxy.upstream)

    console.print(table)

    # Next steps
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Build images: [cyan]ai-sbx docker build[/cyan]")
    console.print("2. Start container: [cyan]ai-sbx docker up[/cyan]")

    if config.preferred_ide == IDE.VSCODE:
        console.print(f"3. Open in VS Code: [cyan]code {project_path}[/cyan]")
        console.print("   Then click 'Reopen in Container' when prompted")
    elif config.preferred_ide == IDE.PYCHARM:
        console.print("3. Open in PyCharm: Settings → Python Interpreter → Docker Compose")
    elif config.preferred_ide == IDE.CLAUDE:
        console.print("3. Open in Claude: [cyan]claude --dangerously-skip-permissions[/cyan]")
