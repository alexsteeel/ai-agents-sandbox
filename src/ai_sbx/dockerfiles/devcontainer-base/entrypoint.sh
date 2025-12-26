#!/bin/bash
set -e

# Set umask to allow group write permissions
umask 0002

# Function to check and warn about directory ownership
check_dir_ownership() {
    local dir="$1"
    local name="$2"

    if [ -d "$dir" ]; then
        if [ "$(stat -c %u "$dir")" = "0" ]; then
            if [ ! -w "$dir" ]; then
                echo "Warning: $name directory is owned by root and not writable"
                echo "To fix, run from HOST (not inside container):"
                echo "  docker exec -u root \$(docker ps -qf name=devcontainer) chown -R claude:local-ai-team $dir"
                echo "Or recreate the volume with: docker compose down -v && docker compose up -d"
                return 1
            fi
        fi
    else
        mkdir -p "$dir"
        chmod 755 "$dir"
    fi
    return 0
}

# Check .codex directory
check_dir_ownership /home/claude/.codex ".codex"

# Check .claude directory - critical for Claude Code to function
if ! check_dir_ownership /home/claude/.claude ".claude"; then
    echo ""
    echo "ERROR: Claude Code will not work until .claude directory permissions are fixed!"
    echo ""
fi

# Check .md-task-mcp directory - needed for task management MCP server
check_dir_ownership /home/claude/.md-task-mcp ".md-task-mcp"

# Ensure Claude defaults are copied on every container start
# This handles cases where the container is recreated or ~/.claude is missing
if [ -d /home/claude/claude-defaults ]; then
    # Create both .claude directories if they don't exist
    mkdir -p /home/claude/.claude 2>/dev/null || true
    mkdir -p /workspace/.claude 2>/dev/null || true

    # Fix ownership of .claude directory if it's owned by root (from volume)
    if [ -d /home/claude/.claude ] && [ "$(stat -c %u /home/claude/.claude 2>/dev/null)" = "0" ]; then
        echo "Warning: ~/.claude is owned by root, some files may not be copied"
    fi

    # Copy all files from claude-defaults to ~/.claude, preserving structure
    # Using cp -n to not overwrite existing files
    cp -rn /home/claude/claude-defaults/* /home/claude/.claude/ 2>/dev/null || true

    # Ensure hooks are executable
    if [ -d /home/claude/.claude/hooks ]; then
        chmod +x /home/claude/.claude/hooks/*.sh 2>/dev/null || true
    fi

    # Always ensure critical files exist (settings.local.json and notify.sh)
    if [ ! -f /home/claude/.claude/settings.local.json ] && [ -f /home/claude/claude-defaults/settings.local.json ]; then
        cp /home/claude/claude-defaults/settings.local.json /home/claude/.claude/ 2>/dev/null || \
            echo "Warning: Could not copy settings.local.json to ~/.claude"
    fi

    if [ ! -f /home/claude/.claude/hooks/notify.sh ] && [ -f /home/claude/claude-defaults/hooks/notify.sh ]; then
        mkdir -p /home/claude/.claude/hooks 2>/dev/null || true
        cp /home/claude/claude-defaults/hooks/notify.sh /home/claude/.claude/hooks/ 2>/dev/null || true
        chmod +x /home/claude/.claude/hooks/notify.sh 2>/dev/null || true
    fi

    # Also copy settings.local.json to /workspace/.claude
    if [ -f /home/claude/claude-defaults/settings.local.json ]; then
        mkdir -p /workspace/.claude 2>/dev/null || true
        cp /home/claude/claude-defaults/settings.local.json /workspace/.claude/ 2>/dev/null || true
    fi
fi

# Copy host Claude settings (commands, agents, hooks) if mounted and enabled
if [ "$COPY_CLAUDE_SETTINGS" = "true" ] && [ -d /host/.claude ]; then
    mkdir -p /home/claude/.claude/commands /home/claude/.claude/agents /home/claude/.claude/hooks 2>/dev/null || true

    # Copy commands from host (merge with existing)
    if [ -d /host/.claude/commands ]; then
        cp -rn /host/.claude/commands/* /home/claude/.claude/commands/ 2>/dev/null || true
    fi

    # Copy agents from host (merge with existing)
    if [ -d /host/.claude/agents ]; then
        cp -rn /host/.claude/agents/* /home/claude/.claude/agents/ 2>/dev/null || true
    fi

    # Copy hooks from host (merge with existing)
    if [ -d /host/.claude/hooks ]; then
        cp -rn /host/.claude/hooks/* /home/claude/.claude/hooks/ 2>/dev/null || true
        chmod +x /home/claude/.claude/hooks/*.sh 2>/dev/null || true
    fi

    # Copy settings.json from host if exists (don't overwrite)
    if [ -f /host/.claude/settings.json ] && [ ! -f /home/claude/.claude/settings.json ]; then
        cp /host/.claude/settings.json /home/claude/.claude/ 2>/dev/null || true
    fi
fi

# Register MCP servers with Claude Code (user-level, persists across projects)
# Check if MCP servers are already configured to avoid duplicates
if command -v claude &> /dev/null; then
    MCP_LIST=$(claude mcp list 2>/dev/null || echo "")

    # Add md-task-mcp server if not already configured
    if echo "$MCP_LIST" | grep -q "md-task-mcp"; then
        true  # already configured
    else
        claude mcp add -s user md-task-mcp -- md-task-mcp serve 2>/dev/null && \
            echo "Added md-task-mcp MCP server" || true
    fi

    # Add context7 MCP server if not already configured
    if echo "$MCP_LIST" | grep -q "context7"; then
        true  # already configured
    else
        claude mcp add -s user context7 -- npx -y @upstash/context7-mcp 2>/dev/null && \
            echo "Added context7 MCP server" || true
    fi

    # Add playwright MCP server if not already configured
    if echo "$MCP_LIST" | grep -q "playwright"; then
        true  # already configured
    else
        claude mcp add -s user playwright -- npx @playwright/mcp@latest --isolated --no-sandbox --headless 2>/dev/null && \
            echo "Added playwright MCP server" || true
    fi
fi

# Execute the original command
exec "$@"