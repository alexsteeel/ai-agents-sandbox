#!/usr/bin/env python3
"""
Git Guard Hook - blocks dangerous git operations in sandbox.
Prevents: checkout/switch to protected branches, force push, push to protected branches.
"""

import json
import sys

PROTECTED = {"main", "master", "develop", "release"}


def check_command(cmd: str) -> str | None:
    """Return block reason or None if allowed."""
    parts = cmd.split()

    if "git" not in parts:
        return None

    try:
        git_idx = parts.index("git")
        args = parts[git_idx + 1 :]
    except (ValueError, IndexError):
        return None

    if not args:
        return None

    action = args[0]

    # git checkout/switch <protected>
    if action in ("checkout", "switch") and len(args) > 1:
        # Skip flags, find branch name
        for arg in args[1:]:
            if not arg.startswith("-") and arg in PROTECTED:
                return f"Cannot {action} protected branch '{arg}'"

    # git push --force / -f
    if action == "push" and any(a in args for a in ("--force", "-f", "--force-with-lease")):
        return "Force push is not allowed"

    # git push origin <protected>
    if action == "push" and len(args) >= 3:
        branch = args[-1]
        if ":" in branch:
            branch = branch.split(":")[-1]
        if branch in PROTECTED:
            return f"Cannot push to protected branch '{branch}'"

    return None


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        if data.get("tool_name") != "Bash":
            sys.exit(0)

        cmd = data.get("tool_input", {}).get("command", "")
        reason = check_command(cmd)

        if reason:
            print(json.dumps({"decision": "block", "reason": f"[Git Guard] {reason}"}))
            sys.exit(1)
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
