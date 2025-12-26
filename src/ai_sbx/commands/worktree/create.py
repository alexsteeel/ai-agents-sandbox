"""Create command for worktree management."""

import subprocess
from typing import Optional

import click

from ai_sbx.config import IDE
from ai_sbx.utils import find_project_root, logger, prompt_yes_no, run_command

from .utils import (
    copy_secure_init,
    detect_available_ides,
    generate_branch_name,
    get_preferred_ide,
    open_ide,
    prompt_ide_selection,
    save_preferred_ide,
)


@click.command()
@click.argument("description")
@click.option("--branch", help="Custom branch name")
@click.option("--ide", type=click.Choice(["vscode", "devcontainer", "pycharm", "rider", "goland"]))
@click.option("--no-open", is_flag=True, help="Don't open IDE after creation")
@click.pass_context
def create(
    ctx: click.Context,
    description: str,
    branch: Optional[str],
    ide: Optional[str],
    no_open: bool,
) -> None:
    """Create a new worktree for a development task.

    This command creates a git worktree with a descriptive branch name,
    sets up the devcontainer environment, and optionally opens your IDE.

    \b
    Examples:
        ai-sbx worktree create "feature 123 implement user auth"
        ai-sbx worktree create "bugfix memory leak in parser" --branch fix-parser
    """
    from rich.console import Console

    console: Console = ctx.obj["console"]
    verbose: bool = ctx.obj.get("verbose", False)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        console.print("[red]Not in a git repository[/red]")
        return

    # Check if .devcontainer is committed
    devcontainer_path = project_root / ".devcontainer"
    if devcontainer_path.exists():
        try:
            # Check if .devcontainer is tracked by git
            result = subprocess.run(
                ["git", "ls-files", ".devcontainer"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if not result.stdout.strip():
                console.print(
                    "[yellow]⚠ Warning: .devcontainer folder is not committed to git[/yellow]"
                )
                console.print(
                    "[dim]Worktrees won't have access to the devcontainer configuration[/dim]"
                )
                console.print("\nTo fix this, run:")
                console.print(
                    '[cyan]git add .devcontainer && git commit -m "Add devcontainer configuration"[/cyan]'
                )
                if not prompt_yes_no("\nContinue anyway?", default=False):
                    return
        except Exception:
            pass

    # Check for uncommitted changes in .devcontainer folder
    if devcontainer_path.exists():
        try:
            # Check for staged changes
            staged_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only", ".devcontainer"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
            )
            # Check for unstaged changes
            unstaged_result = subprocess.run(
                ["git", "diff", "--name-only", ".devcontainer"],
                cwd=project_root,
                capture_output=True,
                text=True,
                check=False,
            )

            has_devcontainer_changes = bool(
                staged_result.stdout.strip() or unstaged_result.stdout.strip()
            )

            if has_devcontainer_changes:
                console.print(
                    "[yellow]⚠ Warning: .devcontainer folder has uncommitted changes[/yellow]"
                )
                console.print(
                    "[dim]The new worktree will use the older committed version of .devcontainer files[/dim]"
                )
                console.print("\nTo include these changes, commit them first:")
                console.print(
                    '[cyan]git add .devcontainer && git commit -m "Update devcontainer"[/cyan]'
                )
                if not prompt_yes_no("\nContinue with older .devcontainer files?", default=False):
                    return
        except Exception as e:
            logger.warning(f"Could not check for .devcontainer changes: {e}")

    # Check for uncommitted changes in the entire repository
    try:
        # Check for any staged or unstaged changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )

        if status_result.stdout.strip():
            # Parse the changes to show a summary
            lines = status_result.stdout.strip().split("\n")
            modified_files = []
            staged_files = []
            untracked_files = []

            for line in lines:
                if len(line) >= 2:
                    status_code = line[:2]
                    file_path = line[3:]

                    if status_code[0] != " " and status_code[0] != "?":
                        staged_files.append(file_path)
                    elif status_code[1] != " " and status_code[1] != "?":
                        modified_files.append(file_path)
                    elif status_code == "??":
                        untracked_files.append(file_path)

            console.print("[yellow]⚠ Warning: Repository has uncommitted changes[/yellow]")

            if staged_files:
                console.print(f"[green]Staged files: {len(staged_files)}[/green]")
                for f in staged_files[:5]:  # Show first 5
                    console.print(f"  + {f}")
                if len(staged_files) > 5:
                    console.print(f"  ... and {len(staged_files) - 5} more")

            if modified_files:
                console.print(f"[yellow]Modified files: {len(modified_files)}[/yellow]")
                for f in modified_files[:5]:  # Show first 5
                    console.print(f"  M {f}")
                if len(modified_files) > 5:
                    console.print(f"  ... and {len(modified_files) - 5} more")

            if untracked_files:
                console.print(f"[red]Untracked files: {len(untracked_files)}[/red]")
                for f in untracked_files[:5]:  # Show first 5
                    console.print(f"  ? {f}")
                if len(untracked_files) > 5:
                    console.print(f"  ... and {len(untracked_files) - 5} more")

            console.print(
                "\n[dim]The new worktree will be based on the last commit and won't include these changes[/dim]"
            )
            console.print("Consider committing important changes first:")
            console.print(
                '[cyan]git add <files> && git commit -m "Save work before creating worktree"[/cyan]'
            )

            if not prompt_yes_no("\nContinue without these changes?", default=False):
                return

    except Exception as e:
        logger.warning(f"Could not check for uncommitted changes: {e}")

    # Generate branch name if not provided
    if not branch:
        branch = generate_branch_name(description)

    # Get repository name for prefix
    repo_name = project_root.name
    worktree_name = f"{repo_name}-{branch}"
    worktree_path = project_root.parent / worktree_name

    # Check if worktree already exists
    if worktree_path.exists():
        console.print(f"[red]Worktree already exists: {worktree_path}[/red]")
        return

    # Create worktree
    console.print(f"Creating worktree: [cyan]{worktree_name}[/cyan]")
    console.print(f"Branch name: [cyan]{branch}[/cyan]")

    try:
        run_command(
            ["git", "worktree", "add", "-b", branch, str(worktree_path)],
            cwd=project_root,
            verbose=verbose,
        )
        console.print(f"[green]✓[/green] Worktree created at {worktree_path}")
        logger.success(f"Worktree created at {worktree_path}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to create worktree: {e}[/red]")
        return

    # Copy init.secure.sh if it exists (for credentials not in git)
    copy_secure_init(project_root, worktree_path, console)

    # Determine preferred IDE
    preferred_ide = None
    if ide:
        preferred_ide = IDE(ide)
    else:
        # Load preference from .user.env
        saved_preference = get_preferred_ide(project_root)

        # Detect available IDEs
        detected = detect_available_ides()
        if detected and not no_open:
            # Always prompt if we have IDEs available (pass saved preference as default)
            preferred_ide = prompt_ide_selection(detected, project_root, console, saved_preference)
        elif saved_preference:
            # If no_open is set, just use the saved preference
            preferred_ide = saved_preference

    # Open IDE if requested
    opened_ide = False
    if not no_open and preferred_ide:
        console.print(f"\n[cyan]Opening {preferred_ide.value}...[/cyan]")
        open_ide(worktree_path, preferred_ide, console, verbose)
        opened_ide = True

        # Special handling for devcontainer - it runs interactively, so exit after
        if preferred_ide == IDE.DEVCONTAINER:
            return

    # Show summary only if IDE wasn't opened or user chose no IDE
    if not opened_ide:
        console.print("\n" + "=" * 64)
        console.print("[bold green]Task worktree created successfully![/bold green]")
        console.print("")
        console.print(f"[bold]Worktree:[/bold] {worktree_path}")
        console.print(f"[bold]Branch:[/bold] {branch}")
        console.print(f"[bold]Task folder:[/bold] tasks/{branch}")
        console.print(f"[bold]Requirements:[/bold] tasks/{branch}/initial_requirements.md")
        console.print("")
        console.print("To open the worktree:")
        console.print(f"  [cyan]cd {worktree_path}[/cyan]")
        console.print(
            "  [cyan]code .[/cyan]  # Open in VS Code (containers will start automatically)"
        )
        console.print("")
        console.print("To remove this worktree later:")
        console.print(f"  [cyan]git worktree remove {worktree_path}[/cyan]")
        console.print("=" * 64)
    else:
        # If IDE was opened, just show a brief summary
        console.print(f"\n[green]✓[/green] Worktree created: {worktree_path}")
        console.print(f"[green]✓[/green] Branch: {branch}")
        console.print(f"[green]✓[/green] Task folder: tasks/{branch}")
        console.print(f"\n[dim]To remove later: git worktree remove {worktree_path}[/dim]")
