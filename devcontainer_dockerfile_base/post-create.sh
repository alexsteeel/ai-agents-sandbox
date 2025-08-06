#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# Post-create script for devcontainer setup
# This script runs after the devcontainer is created

main() {
    echo "Starting post-create setup..."
    
    # Fix .claude directory ownership if it exists
    if [[ -d "/home/claude/.claude" ]]; then
        echo "Fixing .claude directory ownership..."
        sudo chown -R claude:claude /home/claude/.claude
    else
        echo "Warning: /home/claude/.claude directory not found"
    fi

    # Initialize firewall if the script exists
    if [[ -f "/usr/local/bin/init-firewall.sh" ]]; then
        echo "Initializing firewall..."
        sudo /usr/local/bin/init-firewall.sh -d /usr/local/etc/allowed-domains.txt
    else
        echo "Warning: /usr/local/bin/init-firewall.sh not found"
    fi

    # Copy p10k configuration if it exists
    local TARGET_USER="claude"
    local TARGET_HOME="/home/${TARGET_USER}"
    
    echo "=== P10K Configuration Setup ==="
    echo "Script running as: $(whoami)"
    echo "Target user: ${TARGET_USER}"
    echo "Target home: ${TARGET_HOME}"
    
    if [[ -f "/etc/zsh/.p10k.zsh" ]]; then
        echo "Source file found: /etc/zsh/.p10k.zsh"
        echo "Copying p10k configuration to ${TARGET_HOME}/.p10k.zsh..."
        
        # Copy the file to the claude user's home directory
        cp -f /etc/zsh/.p10k.zsh "${TARGET_HOME}/.p10k.zsh"
        
        # Set proper ownership for the claude user
        chown ${TARGET_USER}:${TARGET_USER} "${TARGET_HOME}/.p10k.zsh"
        
        # Set readable permissions
        chmod 644 "${TARGET_HOME}/.p10k.zsh"
        
        echo "✓ p10k configuration copied successfully to ${TARGET_HOME}/.p10k.zsh"
        ls -la "${TARGET_HOME}/.p10k.zsh"
    else
        echo "✗ Warning: /etc/zsh/.p10k.zsh not found"
    fi
    
    echo "Post-create setup completed successfully"
}

# Run main function
main "$@"