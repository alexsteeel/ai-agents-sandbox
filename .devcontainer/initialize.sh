#!/bin/bash
set -euo pipefail

# Project initialization wrapper
# This script calls the system-installed claude-project-init with project-specific logic

# Get the target directory from arguments (default to parent directory)
TARGET_DIR="${1:-$(dirname "$(dirname "$(realpath "$0")")")}"

echo "Initializing project at: $TARGET_DIR"

# Call the system-installed initializer
if command -v claude-project-init >/dev/null 2>&1; then
    # The system script handles all the core initialization
    claude-project-init "$TARGET_DIR"
else
    echo "Error: claude-project-init not found. Please run the system installer first."
    echo "Run: sudo ./install.sh from the ai_agents_sandbox repository"
    exit 1
fi

# ============================================================================
# PROJECT-SPECIFIC CUSTOMIZATION
# ============================================================================
# Add any project-specific initialization here if needed

# Example: Set up project-specific configuration
# if [[ ! -f ".env" ]]; then
#     cp .env.example .env
#     echo "Created .env from .env.example - please edit with your settings"
# fi

echo ""
echo "Project initialization complete!"
echo "You can now start the devcontainer with VS Code or your IDE."