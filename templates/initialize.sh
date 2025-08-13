#!/bin/bash
set -euo pipefail

# Project-specific initialization script
# This script is called when setting up a new devcontainer environment
# It calls the system initializer and then runs any custom logic

# Get the target directory from arguments
TARGET_DIR="${1:-$(pwd)}"

echo "Initializing devcontainer for: $TARGET_DIR"

# ============================================================================
# SYSTEM INITIALIZATION (Required - do not remove)
# ============================================================================
# Call the system-installed initializer
if command -v claude-workspace-init >/dev/null 2>&1; then
    claude-workspace-init "$TARGET_DIR"
else
    echo "Error: claude-workspace-init not found. Please run the system installer first."
    echo "Run: sudo ./install.sh from the claude-devcontainer repository"
    exit 1
fi

# ============================================================================
# GIT WORKTREE SUPPORT
# ============================================================================

# Check if this is a git worktree and update docker-compose.yaml if needed
if [[ -f "$TARGET_DIR/.git" ]]; then
    echo "Detected git worktree, checking parent repository..."
    
    # Read the gitdir path from .git file
    GITDIR=$(grep "^gitdir:" "$TARGET_DIR/.git" | cut -d' ' -f2)
    
    if [[ -n "$GITDIR" ]]; then
        # Extract the parent git directory (remove /worktrees/... part)
        PARENT_GIT_DIR=$(echo "$GITDIR" | sed 's|/worktrees/.*||')
        
        echo "Parent git directory: $PARENT_GIT_DIR"
        
        # Update docker-compose.yaml to include the parent git directory mount
        COMPOSE_FILE="$TARGET_DIR/.devcontainer/docker-compose.yaml"
        if [[ -f "$COMPOSE_FILE" ]]; then
            echo "Updating docker-compose.yaml with git parent mount..."
            
            # Check if yq is available
            if ! command -v yq &> /dev/null; then
                echo "Installing yq for YAML manipulation..."
                wget -qO /tmp/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64
                chmod +x /tmp/yq
                YQ_CMD="/tmp/yq"
            else
                YQ_CMD="yq"
            fi
            
            # Check if the mount already exists using yq
            MOUNT_EXISTS=$($YQ_CMD eval '.services.devcontainer.volumes[] | select(. == "'$PARENT_GIT_DIR':'$PARENT_GIT_DIR'")' "$COMPOSE_FILE" 2>/dev/null || echo "")
            
            if [[ -z "$MOUNT_EXISTS" ]]; then
                # Add the mount to the devcontainer service volumes using yq
                $YQ_CMD eval -i '.services.devcontainer.volumes += ["'$PARENT_GIT_DIR':'$PARENT_GIT_DIR'"]' "$COMPOSE_FILE"
                
                echo "Added git parent directory mount to docker-compose.yaml"
            else
                echo "Git parent directory mount already exists in docker-compose.yaml"
            fi
            
            # Clean up temporary yq if we downloaded it
            [[ -f /tmp/yq ]] && rm /tmp/yq
        fi
    fi
elif [[ -d "$TARGET_DIR/.git" ]]; then
    echo "Regular git repository detected (not a worktree)"
fi

# ============================================================================
# CUSTOM INITIALIZATION (Add your project-specific setup here)
# ============================================================================

echo "Running project-specific initialization..."

# Example: Create project-specific directories
# mkdir -p "$TARGET_DIR/.devcontainer/ssl-certs"
# mkdir -p "$TARGET_DIR/.devcontainer/configs"

# Example: Copy project templates
# cp /usr/local/share/claude-devcontainer/templates/whitelist.txt "$TARGET_DIR/.devcontainer/"
# cp /usr/local/share/claude-devcontainer/templates/dind-whitelist.txt "$TARGET_DIR/.devcontainer/"

# Example: Set up git configuration
# if [[ ! -f "$TARGET_DIR/.gitignore" ]]; then
#     echo ".env" >> "$TARGET_DIR/.gitignore"
#     echo ".env.project" >> "$TARGET_DIR/.gitignore"
# fi

# Example: Check for required files
# if [[ ! -f "$TARGET_DIR/.devcontainer/whitelist.txt" ]]; then
#     echo "Creating default whitelist.txt..."
#     cat > "$TARGET_DIR/.devcontainer/whitelist.txt" <<EOF
# # Project-specific whitelisted domains
# # Add one domain per line
# api.myproject.com
# EOF
# fi

# Example: Install project dependencies
# echo "Checking for package.json..."
# if [[ -f "$TARGET_DIR/package.json" ]]; then
#     echo "Installing Node.js dependencies..."
#     cd "$TARGET_DIR" && npm install
# fi

# ============================================================================
# FINAL CHECKS
# ============================================================================

# Verify the environment is properly set up
echo ""
echo "Initialization complete! Next steps:"
echo "1. Review and edit .devcontainer/.env with your settings"
echo "2. Add any required domains to .devcontainer/whitelist.txt"
echo "3. Add Docker registry domains to .devcontainer/dind-whitelist.txt"
echo "4. Start the environment with: claude-devcontainer start"
echo ""

# Optional: Run validation
# claude-devcontainer validate "$TARGET_DIR"

exit 0