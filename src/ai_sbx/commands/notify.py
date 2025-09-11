"""Notification commands for AI Agents Sandbox."""

import os
import sys
import time
from pathlib import Path

import click
from rich.console import Console

from ai_sbx.utils import check_command_exists, get_user_home, run_command


@click.group(invoke_without_command=True)
@click.option("--test", is_flag=True, help="Send a test notification")
@click.option("--daemon", "-d", is_flag=True, help="Run as daemon in background")
@click.pass_context
def notify(ctx: click.Context, test: bool, daemon: bool) -> None:
    """Start notification watcher for container alerts.

    This command monitors for notifications from containers and displays
    desktop alerts when Claude or other tools need your attention.

    Examples:

        # Start notification watcher
        ai-sbx notify

        # Send test notification
        ai-sbx notify --test

        # Run as daemon
        ai-sbx notify -d
    """
    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    if test:
        send_test_notification(console)
        return

    if daemon:
        # Fork to background (Unix-only)
        if not hasattr(os, 'fork'):
            console.print("[red]Daemon mode not supported on Windows[/red]")
            console.print("Run without -d flag: [cyan]ai-sbx notify[/cyan]")
            sys.exit(1)

        try:
            pid = os.fork()
            if pid > 0:
                console.print(f"[green]Notification watcher started (PID: {pid})[/green]")
                console.print("To stop: [cyan]ai-sbx notify stop[/cyan]")
                sys.exit(0)
        except OSError as e:
            console.print(f"[red]Failed to fork process: {e}[/red]")
            sys.exit(1)

    # Start watcher
    start_notification_watcher(console, verbose)


def send_test_notification(console: Console) -> None:
    """Send a test notification."""
    home = get_user_home()
    notifications_dir = home / ".ai_agents_sandbox" / "notifications"

    if not notifications_dir.exists():
        console.print("[red]Notifications directory does not exist[/red]")
        console.print("Run [cyan]ai-sbx init --global[/cyan] to set up notifications")
        return

    # Create test notification
    test_file = notifications_dir / "test.txt"
    try:
        test_file.write_text("test|AI Agents Sandbox|This is a test notification")
    except PermissionError:
        console.print("[yellow]Permission denied writing to notifications directory[/yellow]")
        console.print("You may need to fix permissions on the notifications directory")
        return

    console.print("[green]Test notification created[/green]")
    console.print("If the watcher is running, you should see a desktop notification")


def start_notification_watcher(console: Console, verbose: bool) -> None:
    """Start the notification watcher."""
    home = get_user_home()
    notifications_dir = home / ".ai_agents_sandbox" / "notifications"

    if not notifications_dir.exists():
        console.print("[red]Notifications directory does not exist[/red]")
        console.print("Run [cyan]ai-sbx init --global[/cyan] to set up notifications")
        sys.exit(1)

    # Check for notification tools
    has_notify_send = check_command_exists("notify-send")
    has_inotify = check_command_exists("inotifywait")

    if not has_notify_send:
        console.print("[yellow]Warning: notify-send not found[/yellow]")
        console.print("Desktop notifications will not work")
        console.print("Install: [cyan]sudo apt-get install libnotify-bin[/cyan]")

    console.print(f"[cyan]Monitoring notifications in: {notifications_dir}[/cyan]")

    if has_inotify:
        console.print("[green]Using inotify for instant notifications[/green]")
        watch_with_inotify(notifications_dir, verbose)
    else:
        console.print(
            "[yellow]Using polling (install inotify-tools for better performance)[/yellow]"
        )
        watch_with_polling(notifications_dir, verbose)


def watch_with_inotify(notifications_dir: Path, verbose: bool) -> None:
    """Watch for notifications using inotify."""
    console = Console()

    try:
        while True:
            # Wait for file creation events
            result = run_command(
                [
                    "inotifywait",
                    "-q",  # Quiet
                    "-e",
                    "create",  # Watch for create events
                    str(notifications_dir),
                ],
                capture_output=True,
            )

            if result.returncode == 0:
                # Parse event
                output = result.stdout.strip()
                if output:
                    parts = output.split()
                    if len(parts) >= 3:
                        filename = parts[2]
                        if filename.endswith(".txt"):
                            process_notification(notifications_dir / filename, console, verbose)

    except KeyboardInterrupt:
        console.print("\n[yellow]Notification watcher stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error in notification watcher: {e}[/red]")


def watch_with_polling(notifications_dir: Path, verbose: bool) -> None:
    """Watch for notifications using polling."""
    console = Console()
    processed = set()

    try:
        while True:
            # Check for new files
            for file_path in notifications_dir.glob("*.txt"):
                if file_path.name not in processed:
                    process_notification(file_path, console, verbose)
                    processed.add(file_path.name)

            # Clean up old entries
            if len(processed) > 100:
                processed = set(list(processed)[-50:])

            # Sleep briefly
            time.sleep(0.5)

    except KeyboardInterrupt:
        console.print("\n[yellow]Notification watcher stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error in notification watcher: {e}[/red]")


def process_notification(file_path: Path, console: Console, verbose: bool) -> None:
    """Process a notification file."""
    try:
        # Read notification
        content = file_path.read_text().strip()

        # Parse format: type|title|message
        parts = content.split("|", 2)
        if len(parts) < 3:
            if verbose:
                console.print(f"[yellow]Invalid notification format: {file_path.name}[/yellow]")
            return

        notification_type, title, message = parts

        # Determine urgency
        urgency = get_urgency(notification_type)

        # Display notification
        display_notification(title, message, urgency, console, verbose)

        # Remove processed file
        file_path.unlink()

    except Exception as e:
        if verbose:
            console.print(f"[red]Error processing notification: {e}[/red]")


def get_urgency(notification_type: str) -> str:
    """Get notification urgency from type."""
    critical_types = ["error", "clarification", "blocked", "approval"]
    low_types = ["complete", "success", "done"]

    if notification_type in critical_types:
        return "critical"
    elif notification_type in low_types:
        return "low"
    else:
        return "normal"


def display_notification(
    title: str, message: str, urgency: str, console: Console, verbose: bool
) -> None:
    """Display a desktop notification."""
    # Try desktop notification
    if check_command_exists("notify-send"):
        try:
            cmd = ["notify-send", "-u", urgency]

            # Add icon based on urgency
            if urgency == "critical":
                cmd.extend(["-i", "dialog-error"])
            elif urgency == "low":
                cmd.extend(["-i", "dialog-information"])
            else:
                cmd.extend(["-i", "dialog-warning"])

            cmd.extend([title, message])

            run_command(cmd, check=False)

            if verbose:
                console.print(f"[green]Notification sent: {title}[/green]")

        except Exception as e:
            if verbose:
                console.print(f"[yellow]Could not send desktop notification: {e}[/yellow]")

    # Always show in console
    urgency_color = {
        "critical": "red",
        "normal": "yellow",
        "low": "green",
    }.get(urgency, "white")

    console.print(f"\n[{urgency_color}]● {title}[/{urgency_color}]")
    console.print(f"  {message}")


@notify.command("stop")
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Stop the notification watcher daemon."""
    console: Console = ctx.obj["console"]

    try:
        # Find and kill notify processes
        result = run_command(
            ["pgrep", "-f", "ai-sbx notify"],
            check=False,
            capture_output=True,
        )

        if result.returncode == 0:
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                if pid:
                    run_command(["kill", pid], check=False)

            console.print("[green]Notification watcher stopped[/green]")
        else:
            console.print("[yellow]No notification watcher running[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to stop notification watcher: {e}[/red]")
