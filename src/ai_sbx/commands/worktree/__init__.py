"""Worktree management commands for AI Agents Sandbox."""

import click

from ai_sbx.utils import AliasedGroup

from .connect import connect
from .create import create
from .list import list_worktrees
from .remove import remove


@click.group(
    cls=AliasedGroup,
    aliases={
        "ls": "list",
        "rm": "remove",
        "del": "remove",
        "delete": "remove",
        "new": "create",
        "add": "create",
        "cn": "connect",
    },
)
def worktree() -> None:
    """Manage git worktrees for isolated development tasks.

    Worktrees allow you to work on multiple branches simultaneously
    in separate directories, each with its own devcontainer environment.
    """
    pass


# Add all commands to the group
worktree.add_command(create)
worktree.add_command(remove)
worktree.add_command(connect)
worktree.add_command(list_worktrees)

__all__ = ["worktree"]
