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
        echo "✗ Warning: /etc/zsh/.p10k.zsh not found"
    fi

    cp -r "${HOME}/claude_defaults "${HOME}/.claude
    
    echo "Post-create setup completed successfully"
}

# Run main function
main "$@"