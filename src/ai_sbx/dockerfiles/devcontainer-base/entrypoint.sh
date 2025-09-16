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

# Execute the original command
exec "$@"