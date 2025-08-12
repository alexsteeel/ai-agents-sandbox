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