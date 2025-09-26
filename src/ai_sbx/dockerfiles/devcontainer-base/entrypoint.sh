#!/bin/bash
set -e

# Set umask to allow group write permissions
umask 0002

# Fix .codex directory ownership if it exists and is owned by root
if [ -d /home/claude/.codex ]; then
    # Check if owned by root (UID 0)
    if [ "$(stat -c %u /home/claude/.codex)" = "0" ]; then
        echo "Fixing .codex directory ownership..."
        # Since we're running as claude user, we can't chown from root
        # But we can create our own directory structure if needed
        if [ -w /home/claude/.codex ]; then
            # If writable, we're good
            true
        else
            echo "Warning: .codex directory is owned by root and not writable"
            echo "To fix: Run 'sudo chown -R claude:local-ai-team /home/claude/.codex' from host"
        fi
    fi
else
    # Create .codex directory with correct ownership
    mkdir -p /home/claude/.codex
    chmod 755 /home/claude/.codex
fi

# Ensure Claude defaults are copied on every container start
# This handles cases where the container is recreated or ~/.claude is missing
if [ -d /home/claude/claude-defaults ]; then
    # Create both .claude directories if they don't exist
    mkdir -p /home/claude/.claude
    mkdir -p /workspace/.claude

    # Copy all files from claude-defaults to ~/.claude, preserving structure
    # Using cp -n to not overwrite existing files
    cp -rn /home/claude/claude-defaults/* /home/claude/.claude/ 2>/dev/null || true

    # Ensure hooks are executable
    if [ -d /home/claude/.claude/hooks ]; then
        chmod +x /home/claude/.claude/hooks/*.sh 2>/dev/null || true
    fi

    # Always ensure critical files exist (settings.local.json and notify.sh)
    if [ ! -f /home/claude/.claude/settings.local.json ] && [ -f /home/claude/claude-defaults/settings.local.json ]; then
        cp /home/claude/claude-defaults/settings.local.json /home/claude/.claude/
        echo "Restored settings.local.json to ~/.claude"
    fi

    if [ ! -f /home/claude/.claude/hooks/notify.sh ] && [ -f /home/claude/claude-defaults/hooks/notify.sh ]; then
        mkdir -p /home/claude/.claude/hooks
        cp /home/claude/claude-defaults/hooks/notify.sh /home/claude/.claude/hooks/
        chmod +x /home/claude/.claude/hooks/notify.sh
        echo "Restored notify.sh hook to ~/.claude"
    fi

    # Also copy settings.local.json to /workspace/.claude
    if [ -f /home/claude/claude-defaults/settings.local.json ]; then
        mkdir -p /workspace/.claude
        cp /home/claude/claude-defaults/settings.local.json /workspace/.claude/
        echo "Copied settings.local.json to /workspace/.claude"
    fi
fi

# Execute the original command
exec "$@"