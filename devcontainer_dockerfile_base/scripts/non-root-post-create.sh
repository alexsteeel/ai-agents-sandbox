#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# Post-create script for devcontainer setup
# This script runs after the devcontainer is created

main() {
    echo "Starting post-create setup..."

    # Copy p10k configuration if it exists
    local USER="claude"
    local HOME="/home/${USER}"
    
    echo "=== P10K Configuration Setup ==="
    echo "Script running as: $(whoami)"
    echo "Target user: ${USER}"
    echo "Target home: ${HOME}"
    
    if [[ -f "/host/.p10k.zsh" ]]; then
        echo "Source file found: /host/.p10k.zsh"
        echo "Copying p10k configuration to ${HOME}/.p10k.zsh..."
        
        # Copy the file to the claude user's home directory
        cp -f /host/.p10k.zsh "${HOME}/.p10k.zsh"
        
        # Set proper ownership for the claude user
        chown ${USER}:${USER} "${HOME}/.p10k.zsh"
        
        # Set readable permissions
        chmod 644 "${HOME}/.p10k.zsh"
        
        echo "✓ p10k configuration copied successfully to ${HOME}/.p10k.zsh"
        ls -la "${HOME}/.p10k.zsh"
    else
        echo "✗ Warning: /host/.p10k.zsh not found"
    fi

    echo "Syncing Claude defaults to ${HOME}/.claude ..."
    mkdir -p "${HOME}/.claude"
    if [[ -d "${HOME}/claude-defaults" ]]; then
        # Copy contents of claude-defaults into ~/.claude (no nesting)
        cp -rT "${HOME}/claude-defaults" "${HOME}/.claude"
    else
        echo "✗ Warning: ${HOME}/claude-defaults directory not found"
    fi
    chown -R ${USER}:${USER} "${HOME}/.claude"
    
    # Start logging self-tests to ~/.claude/logs while keeping console output
    local LOG_DIR="${HOME}/.claude/logs"
    mkdir -p "${LOG_DIR}"
    exec > >(tee -a "${LOG_DIR}/post_create_tests.log") 2>&1
    echo "----- post-create self-tests $(date -u +'%Y-%m-%dT%H:%M:%SZ') -----"
    
    echo "\n=== Environment & Connectivity Self-Tests ==="
    # Do not fail the whole script on test failures
    set +e
    echo "User identity:"; id
    echo "Groups      :"; groups || true

    echo "\n-- Workspace ownership checks --"
    local WS="/workspace"
    if [[ -d "$WS" ]]; then
        local ws_owner ws_group ws_mode
        ws_owner=$(stat -c '%U' "$WS" 2>/dev/null)
        ws_group=$(stat -c '%G' "$WS" 2>/dev/null)
        ws_mode=$(stat -c '%a' "$WS" 2>/dev/null)
        echo "Workspace: $WS owner=$ws_owner group=$ws_group mode=$ws_mode"
        if [[ "$ws_group" != "dev" ]]; then
            echo "✗ Warning: expected group 'dev' for $WS"
        fi
        if [[ "$ws_owner" == "claude" ]]; then
            echo "✗ Warning: expected owner NOT to be 'claude' for $WS"
        fi
    else
        echo "✗ Warning: workspace folder $WS not found"
    fi

    echo "\n-- Home structure checks --"
    if [[ -d "${HOME}/.claude" ]]; then
        echo "✓ Found ${HOME}/.claude"
        if [[ -d "${HOME}/.claude/agents" ]]; then
            echo "✓ Found ${HOME}/.claude/agents"
        else
            echo "✗ Warning: ${HOME}/.claude/agents missing"
        fi
    else
        echo "✗ Warning: ${HOME}/.claude missing"
    fi

    echo "\n-- Proxy and egress checks (HTTP HEAD) --"
    # Expected allowed hosts
    for host in \
        github.com \
        raw.githubusercontent.com \
        pypi.org \
        files.pythonhosted.org \
        github-releases.githubusercontent.com \
        objects.githubusercontent.com \
        gitee.com
    do
        code=$(curl --max-time 5 -ILs -o /dev/null -w '%{http_code}' "https://$host" 2>/dev/null)
        echo "Allow test https://$host -> HTTP $code"
    done
    # Expected blocked host example (should fail/403)
    blocked_code=$(curl --max-time 5 -ILs -o /dev/null -w '%{http_code}' "https://www.google.com" 2>/dev/null)
    echo "Block test https://www.google.com -> HTTP $blocked_code (expect blocked)"

    echo "\n-- Tool checks --"
    check_tool() {
        local bin="$1"; shift
        if command -v "$bin" >/dev/null 2>&1; then
            echo -n "$bin: "; "$bin" --version 2>/dev/null | head -n1 || echo "installed"
        else
            echo "$bin: not found"
        fi
    }
    check_tool claude
    check_tool uv
    check_tool uvx
    check_tool ruff
    check_tool black
    check_tool docker
    check_tool git

    set -e
    echo "\nPost-create setup completed successfully"
}

# Run main function
main "$@"