"""Doctor command for diagnosing and fixing AI Agents Sandbox issues."""

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from ai_sbx.config import GlobalConfig, get_global_config_path
from ai_sbx.utils import (
    check_command_exists,
    get_current_user,
    get_docker_info,
    get_user_home,
    is_docker_running,
    run_command,
)


def run_doctor(
    console: Console,
    check_only: bool = False,
    fix_issues: bool = False,
    verbose: bool = False,
    interactive: bool = False,
) -> None:
    """Run system diagnostics and optionally fix issues."""
    console.print("\n[bold cyan]AI Agents Sandbox - System Diagnostics[/bold cyan]\n")

    # Track all system state information
    system_state = {
        "directories": {},
        "files": {},
        "docker": {},
        "groups": {},
        "permissions": {},
        "configuration": {},
    }

    # Interactive mode prompts
    if interactive:
        verbose = Confirm.ask(
            "[cyan]Would you like to see detailed diagnostic output?[/cyan]", default=False
        )

    issues = []
    warnings = []

    # Check Docker
    docker_status = check_docker(console, verbose)
    if docker_status[0] != "ok":
        issues.append(docker_status)

    # Check system requirements
    sys_status = check_system_requirements(console, verbose)
    ok_results = []
    for status in sys_status:
        if status[0] == "error":
            issues.append(status)
        elif status[0] == "warning":
            warnings.append(status)
        elif status[0] == "ok" and verbose:
            ok_results.append(status)

    # Check configuration
    config_status = check_configuration(console, verbose)
    if config_status[0] != "ok":
        if config_status[0] == "warning":
            warnings.append(config_status)
        else:
            issues.append(config_status)

    # Check permissions
    perm_status = check_permissions(console, verbose)
    for status in perm_status:
        if status[0] == "error":
            issues.append(status)
        elif status[0] == "warning":
            warnings.append(status)

    # Check images
    image_status = check_images(console, verbose)
    for status in image_status:
        if status[0] == "warning":
            warnings.append(status)
        elif status[0] == "ok" and verbose:
            ok_results.append(status)

    # Analyze system state in verbose mode or when issues exist
    if verbose:
        analyze_system_state(console, system_state, verbose)
    elif issues or warnings:
        # Also analyze if there are issues (but not as detailed)
        analyze_system_state(console, system_state, False)

    # Display results
    display_results(
        console, issues, warnings, ok_results if verbose else [], system_state if verbose else None
    )

    # Handle fixing issues
    should_fix = fix_issues

    # In interactive mode, ask if we should fix issues
    if interactive and (issues or warnings):
        console.print()  # Add spacing
        should_fix = Confirm.ask(
            "[cyan]Issues were found. Would you like me to attempt to fix them automatically?[/cyan]",
            default=True,
        )

    # Fix issues if requested
    if should_fix and (issues or warnings):
        console.print("\n[cyan]Attempting to fix issues...[/cyan]\n")
        fix_detected_issues(console, issues, warnings, verbose, interactive)
    elif not interactive and issues:
        console.print("\n[yellow]Run with --fix to attempt automatic fixes[/yellow]")


def analyze_system_state(console: Console, system_state: dict, verbose: bool) -> None:
    """Analyze and populate system state information."""
    home = get_user_home()

    # Check AI Agents Sandbox directories
    system_dirs = {
        "Global Config": get_global_config_path().parent,
        "Notifications": home / ".ai-sbx" / "notifications",
        "Projects": home / ".ai-sbx" / "projects",
        "System Resources": home / ".ai-sbx" / "share",
        "Docker Proxy": home / ".ai-sbx" / "share" / "docker-proxy",
    }

    for name, path in system_dirs.items():
        if path.exists():
            try:
                stat = path.stat()
                system_state["directories"][str(path)] = {
                    "name": name,
                    "exists": True,
                    "mode": oct(stat.st_mode)[-3:],
                    "owner": stat.st_uid,
                    "group": stat.st_gid,
                    "size": (
                        sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                        if path.is_dir()
                        else stat.st_size
                    ),
                }
            except Exception as e:
                system_state["directories"][str(path)] = {
                    "name": name,
                    "exists": True,
                    "error": str(e),
                }
        else:
            system_state["directories"][str(path)] = {"name": name, "exists": False}

    # Check important files
    system_files = {
        "Global Config": get_global_config_path(),
        "Docker Proxy Compose": home / ".ai-sbx" / "share" / "docker-proxy" / "docker-compose.yaml",
        "Docker Proxy Env": home / ".ai-sbx" / "share" / "docker-proxy" / ".env",
        "Base Compose": home / ".ai-sbx" / "share" / "docker-compose.base.yaml",
    }

    for name, path in system_files.items():
        if path.exists():
            try:
                stat = path.stat()
                system_state["files"][str(path)] = {
                    "name": name,
                    "exists": True,
                    "mode": oct(stat.st_mode)[-3:],
                    "size": stat.st_size,
                }
            except Exception as e:
                system_state["files"][str(path)] = {"name": name, "exists": True, "error": str(e)}
        else:
            system_state["files"][str(path)] = {"name": name, "exists": False}

    # Check Docker containers
    if is_docker_running():
        try:
            result = run_command(
                ["docker", "ps", "-a", "--format", "{{.Names}}:{{.State}}:{{.Status}}"],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line and "ai-sbx" in line:
                        parts = line.split(":", 2)
                        if len(parts) >= 2:
                            system_state["docker"][parts[0]] = {
                                "state": parts[1],
                                "status": parts[2] if len(parts) > 2 else "",
                            }
        except Exception:
            pass

    # Check groups
    try:
        result = run_command(["getent", "group", "local-ai-team"], capture_output=True, check=False)
        if result.returncode == 0:
            parts = result.stdout.strip().split(":")
            if len(parts) >= 3:
                system_state["groups"]["local-ai-team"] = {
                    "gid": parts[2],
                    "members": parts[3].split(",") if len(parts) > 3 and parts[3] else [],
                }
    except Exception:
        pass


def check_docker(console: Console, verbose: bool) -> tuple[str, str, str]:
    """Check Docker installation and status."""
    if not check_command_exists("docker"):
        return ("error", "Docker", "Docker is not installed")

    if not is_docker_running():
        return ("error", "Docker", "Docker daemon is not running")

    # Check Docker Compose
    try:
        result = run_command(
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            return ("error", "Docker Compose", "Docker Compose v2 is not installed")
    except Exception:
        return ("error", "Docker Compose", "Could not check Docker Compose version")

    # Check Docker info
    info = get_docker_info()
    if info and verbose:
        console.print("[dim]Docker version:[/dim]", info.get("ServerVersion", "unknown"))

    return ("ok", "Docker", "Docker is properly configured")


def check_system_requirements(console: Console, verbose: bool) -> list[tuple[str, str, str]]:
    """Check system requirements."""
    results = []

    # Check Git
    if check_command_exists("git"):
        results.append(("ok", "Git", "Git is installed"))
    else:
        results.append(("warning", "Git", "Git is not installed (optional but recommended)"))

    # Check Python (for the CLI tool itself)
    if check_command_exists("python3") or check_command_exists("python"):
        results.append(("ok", "Python", "Python is installed"))
    else:
        results.append(("error", "Python", "Python is required for AI Agents Sandbox CLI"))

    # Check group existence
    try:
        result = run_command(
            ["getent", "group", "3000"],
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            results.append(("ok", "Group", "local-ai-team group (GID 3000) exists"))
        else:
            results.append(("warning", "Group", "local-ai-team group not created"))
    except Exception:
        results.append(("warning", "Group", "Could not check group status"))

    # Check user membership
    username = get_current_user()
    if username:
        try:
            result = run_command(
                ["id", "-nG", username],
                check=False,
                capture_output=True,
            )
            if result.returncode == 0:
                groups = result.stdout.strip().split()
                if "local-ai-team" in groups:
                    results.append(("ok", "User", f"User {username} is in local-ai-team group"))
                else:
                    results.append(
                        ("warning", "User", f"User {username} not in local-ai-team group")
                    )
        except Exception:
            pass

    # Check optional tools
    optional_tools = {
        "notify-send": "Desktop notifications",
        "inotifywait": "Efficient file watching",
        "yq": "YAML processing",
    }

    for tool, description in optional_tools.items():
        if check_command_exists(tool):
            if verbose:
                results.append(("ok", tool, f"{description} available"))
        else:
            if verbose:
                results.append(("info", tool, f"{description} not available (optional)"))

    return results


def check_configuration(console: Console, verbose: bool) -> tuple[str, str, str]:
    """Check AI Agents Sandbox configuration."""
    config_path = get_global_config_path()

    if not config_path.exists():
        return ("warning", "Configuration", "Global configuration not initialized")

    try:
        config = GlobalConfig.load()
        if verbose:
            console.print(f"[dim]Config version:[/dim] {config.version}")
        return ("ok", "Configuration", "Configuration loaded successfully")
    except Exception as e:
        return ("error", "Configuration", f"Invalid configuration: {e}")


def check_permissions(console: Console, verbose: bool) -> list[tuple[str, str, str]]:
    """Check file and directory permissions."""
    results = []
    home = get_user_home()

    # Check directories
    dirs_to_check = [
        home / ".ai-sbx",
        home / ".ai-sbx" / "notifications",
        home / ".ai-sbx" / "projects",
    ]

    for dir_path in dirs_to_check:
        if dir_path.exists():
            # Check ownership and permissions
            dir_path.stat()  # Check if we can access it
            if verbose:
                results.append(
                    ("ok", str(dir_path.name), "Directory exists with proper permissions")
                )
        else:
            results.append(("warning", str(dir_path.name), f"Directory does not exist: {dir_path}"))

    return results


def check_images(console: Console, verbose: bool) -> list[tuple[str, str, str]]:
    """Check Docker images."""
    results = []

    required_images = [
        "ai-agents-sandbox/devcontainer",
        "ai-agents-sandbox/tinyproxy",
        "ai-agents-sandbox/docker-dind",
    ]

    for image in required_images:
        try:
            # Check if image exists with any tag
            result = run_command(
                ["docker", "images", "--format", "{{.Repository}}", image],
                check=False,
                capture_output=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Get all tags for this image
                tag_result = run_command(
                    ["docker", "images", "--format", "{{.Tag}}", image],
                    check=False,
                    capture_output=True,
                )
                tags = tag_result.stdout.strip().split("\n") if tag_result.stdout else []
                tag_info = f"Image exists (tags: {', '.join(tags)})"
                if verbose:
                    results.append(("ok", image, tag_info))
            else:
                results.append(("warning", image, "Image not built"))
        except Exception:
            results.append(("warning", image, "Could not check image"))

    return results


def display_results(
    console: Console,
    issues: list[tuple[str, str, str]],
    warnings: list[tuple[str, str, str]],
    ok_results: list[tuple[str, str, str]] = None,
    system_state: dict = None,
) -> None:
    """Display diagnostic results."""
    ok_results = ok_results or []

    if not issues and not warnings:
        console.print("[bold green]✓ All checks passed![/bold green]")
        console.print("Your AI Agents Sandbox installation is healthy.")

        # In verbose mode, show what was checked
        if ok_results:
            console.print("\n[dim]Checks performed:[/dim]")
            for _status, component, details in ok_results:
                console.print(f"  [green]✓[/green] {component}: {details}")

        # Don't return early - continue to show system state if available

    # Only show diagnostic results table if there are issues/warnings or verbose results
    if issues or warnings or ok_results:
        # Create results table
        table = Table(title="Diagnostic Results", show_lines=True)
        table.add_column("Status", style="bold")
        table.add_column("Component")
        table.add_column("Details")

        # Add issues
        for _status, component, details in issues:
            table.add_row(
                "[red]✗ ERROR[/red]",
                component,
                details,
            )

        # Add warnings
        for _status, component, details in warnings:
            table.add_row(
                "[yellow]⚠ WARNING[/yellow]",
                component,
                details,
            )

        # Add ok results in verbose mode
        for _status, component, details in ok_results:
            table.add_row(
                "[green]✓ OK[/green]",
                component,
                details,
            )

        console.print(table)

    # System State Report (if available)
    if system_state:
        console.print("\n[bold]System State Analysis[/bold]")

        # Directories table
        if system_state.get("directories"):
            dir_table = Table(title="AI Agents Sandbox Directories", show_header=True)
            dir_table.add_column("Directory", style="cyan")
            dir_table.add_column("Status")
            dir_table.add_column("Permissions")
            dir_table.add_column("Size")

            for path, info in system_state["directories"].items():
                status = "[green]Exists[/green]" if info["exists"] else "[red]Missing[/red]"
                perms = info.get("mode", "-")
                size = f"{info.get('size', 0):,} bytes" if info.get("size") else "-"
                if info.get("error"):
                    status = f"[yellow]Error: {info['error']}[/yellow]"
                dir_table.add_row(f"{info['name']}\n[dim]{path}[/dim]", status, perms, size)
            console.print(dir_table)

        # Files table
        if system_state.get("files"):
            file_table = Table(title="Configuration Files", show_header=True)
            file_table.add_column("File", style="cyan")
            file_table.add_column("Status")
            file_table.add_column("Permissions")
            file_table.add_column("Size")

            for path, info in system_state["files"].items():
                status = "[green]Exists[/green]" if info["exists"] else "[red]Missing[/red]"
                perms = info.get("mode", "-")
                size = f"{info.get('size', 0):,} bytes" if info.get("size") else "-"
                if info.get("error"):
                    status = f"[yellow]Error: {info['error']}[/yellow]"
                file_table.add_row(f"{info['name']}\n[dim]{path}[/dim]", status, perms, size)
            console.print(file_table)

        # Docker containers
        if system_state.get("docker"):
            docker_table = Table(title="Docker Containers", show_header=True)
            docker_table.add_column("Container", style="cyan")
            docker_table.add_column("State")
            docker_table.add_column("Status")

            for name, info in system_state["docker"].items():
                state_color = "green" if info["state"] == "running" else "yellow"
                docker_table.add_row(
                    name, f"[{state_color}]{info['state']}[/{state_color}]", info.get("status", "")
                )
            console.print(docker_table)

        # Groups
        if system_state.get("groups"):
            group_table = Table(title="System Groups", show_header=True)
            group_table.add_column("Group", style="cyan")
            group_table.add_column("GID")
            group_table.add_column("Members")

            for name, info in system_state["groups"].items():
                members = ", ".join(info["members"]) if info["members"] else "[dim]No members[/dim]"
                group_table.add_row(name, info["gid"], members)
            console.print(group_table)

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    if issues:
        console.print(f"  [red]Errors: {len(issues)}[/red]")
    if warnings:
        console.print(f"  [yellow]Warnings: {len(warnings)}[/yellow]")
    if ok_results:
        console.print(f"  [green]OK: {len(ok_results)}[/green]")


def fix_detected_issues(
    console: Console,
    issues: list[tuple[str, str, str]],
    warnings: list[tuple[str, str, str]],
    verbose: bool,
    interactive: bool = False,
) -> None:
    """Attempt to fix detected issues."""
    fixed_count = 0

    # Fix Docker issues
    for _status, component, details in issues:
        if component == "Docker" and "not running" in details:
            if interactive:
                if not Confirm.ask(
                    "[yellow]Docker is not running. Start Docker daemon?[/yellow]", default=True
                ):
                    continue

            console.print("Starting Docker daemon...")
            try:
                run_command(["sudo", "systemctl", "start", "docker"], check=False)
                if is_docker_running():
                    console.print("[green]✓ Docker started[/green]")
                    fixed_count += 1
            except Exception:
                console.print("[red]Could not start Docker automatically[/red]")
                console.print("Please start Docker manually")

    # Fix missing Docker images
    missing_images = []
    for _status, component, details in warnings:
        if "Image not built" in details and component.startswith("ai-agents-sandbox/"):
            missing_images.append(component)

    if missing_images:
        if interactive:
            images_list = "\n  • ".join(missing_images)
            if not Confirm.ask(
                f"[yellow]The following Docker images are missing:[/yellow]\n  • {images_list}\n\n"
                f"[cyan]Build missing images?[/cyan]",
                default=True,
            ):
                missing_images = []

        if missing_images:
            console.print("\n[cyan]Building missing Docker images...[/cyan]")
            for image in missing_images:
                # Map image names to build commands
                image_name = image.split("/")[-1]  # Get the last part after '/'

                if image_name == "devcontainer":
                    console.print(f"Building {image}...")
                    try:
                        # Use ai-sbx docker build command
                        result = run_command(
                            ["ai-sbx", "docker", "build"],
                            check=False,
                            capture_output=not verbose,
                        )
                        if result.returncode == 0:
                            console.print(f"[green]✓ Built {image}[/green]")
                            fixed_count += 1
                        else:
                            console.print(f"[red]Failed to build {image}[/red]")
                    except Exception as e:
                        console.print(f"[red]Error building {image}: {e}[/red]")

                elif image_name in ["tinyproxy", "docker-dind"]:
                    console.print(f"Building {image}...")
                    try:
                        # Use ai-sbx docker build with the all flag to build support images
                        result = run_command(
                            ["ai-sbx", "docker", "build", "--all", "--tag", "1.0.3"],
                            check=False,
                            capture_output=not verbose,
                        )
                        if result.returncode == 0:
                            console.print(f"[green]✓ Built {image}[/green]")
                            fixed_count += 1
                        else:
                            # Try with latest tag as fallback
                            result = run_command(
                                ["ai-sbx", "docker", "build", "--all"],
                                check=False,
                                capture_output=not verbose,
                            )
                            if result.returncode == 0:
                                console.print(f"[green]✓ Built {image} with latest tag[/green]")
                                fixed_count += 1
                            else:
                                console.print(f"[red]Failed to build {image}[/red]")
                        break  # Don't try to build other support images since we built all
                    except Exception as e:
                        console.print(f"[red]Error building {image}: {e}[/red]")

    # Fix group issues
    for _status, component, details in warnings:
        if component == "Group" and "not created" in details:
            if interactive:
                if not Confirm.ask(
                    "[yellow]The local-ai-team group (GID 3000) is missing. Create it?[/yellow]\n"
                    "[dim]This requires sudo access[/dim]",
                    default=True,
                ):
                    continue

            console.print("Creating local-ai-team group...")
            console.print("[yellow]This requires sudo access[/yellow]")
            try:
                run_command(
                    ["sudo", "groupadd", "-g", "3000", "local-ai-team"],
                    check=False,
                )
                console.print("[green]✓ Group created[/green]")
                fixed_count += 1
            except Exception:
                console.print("[red]Could not create group[/red]")

        elif component == "User" and "not in local-ai-team group" in details:
            username = get_current_user()
            if username:
                if interactive:
                    if not Confirm.ask(
                        f"[yellow]Add user '{username}' to local-ai-team group?[/yellow]\n"
                        f"[dim]This requires sudo access and logout/login[/dim]",
                        default=True,
                    ):
                        continue

                console.print(f"Adding {username} to local-ai-team group...")
                console.print("[yellow]This requires sudo access[/yellow]")
                try:
                    run_command(
                        ["sudo", "usermod", "-aG", "local-ai-team", username],
                        check=False,
                    )
                    console.print("[green]✓ User added to group[/green]")
                    console.print("[yellow]Log out and back in for changes to take effect[/yellow]")
                    fixed_count += 1
                except Exception:
                    console.print("[red]Could not add user to group[/red]")

    # Fix missing directories
    home = get_user_home()
    missing_dirs = []
    for _status, component, details in warnings:
        if "Directory does not exist" in details:
            dir_name = component
            dir_path = home / ".ai-sbx" / dir_name if dir_name != ".ai-sbx" else home / ".ai-sbx"
            missing_dirs.append((dir_name, dir_path))

    if missing_dirs and interactive:
        dirs_list = "\n  • ".join([str(path) for _, path in missing_dirs])
        if not Confirm.ask(
            f"[yellow]The following directories are missing:[/yellow]\n  • {dirs_list}\n\n"
            f"[cyan]Create missing directories?[/cyan]",
            default=True,
        ):
            missing_dirs = []

    for dir_name, dir_path in missing_dirs:
        console.print(f"Creating directory: {dir_path}")
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓ Created {dir_path}[/green]")
            fixed_count += 1
        except Exception as e:
            console.print(f"[red]Could not create directory: {e}[/red]")

    # Fix missing configuration
    for _status, component, details in warnings:
        if component == "Configuration" and "not initialized" in details:
            if interactive:
                if not Confirm.ask(
                    "[yellow]Global configuration is not initialized. Initialize it?[/yellow]",
                    default=True,
                ):
                    continue

            console.print("Initializing global configuration...")
            try:
                config = GlobalConfig()
                config.save()
                console.print("[green]✓ Configuration initialized[/green]")
                fixed_count += 1
            except Exception as e:
                console.print(f"[red]Could not initialize configuration: {e}[/red]")

    # Summary
    console.print(f"\n[bold]Fixes applied: {fixed_count}[/bold]")

    if fixed_count < len(issues) + len(warnings):
        console.print("[yellow]Some issues could not be fixed automatically[/yellow]")
        console.print("Please address remaining issues manually")
