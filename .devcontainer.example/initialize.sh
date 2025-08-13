#!/bin/bash
set -euo pipefail

# Project initialization wrapper example
# This script demonstrates how to call the system-installed initializer
# and add project-specific customizations

# Get the target directory from arguments (default to parent directory)
TARGET_DIR="${1:-$(dirname "$(dirname "$(realpath "$0")")")}"

echo "Initializing project at: $TARGET_DIR"

# Call the system-installed initializer
if command -v claude-project-init >/dev/null 2>&1; then
    # The system script handles:
    # - Docker services startup with project namespace
    # - Dev group creation and permissions
    # - Docker certificates setup
    # - Notification directory creation
    # - Git worktree support
    claude-project-init "$TARGET_DIR"
else
    echo "Error: claude-project-init not found. Please run the system installer first."
    echo "Run: sudo ./install.sh from the ai_agents_sandbox repository"
    exit 1
fi

# ============================================================================
# PROJECT-SPECIFIC CUSTOMIZATION EXAMPLES
# ============================================================================

# Example 1: Set up project environment file
if [[ ! -f ".env" ]] && [[ -f ".env.example" ]]; then
    cp .env.example .env
    echo "Created .env from .env.example - please edit with your settings"
fi

# Example 2: Check for required configuration files
if [[ ! -f "whitelist.txt" ]]; then
    echo "Warning: whitelist.txt not found. Using default domains only."
    echo "Create whitelist.txt to add project-specific domains."
fi

# Example 3: Install project dependencies (if needed)
# if [[ -f "../package.json" ]]; then
#     echo "Installing Node.js dependencies..."
#     (cd .. && npm install)
# fi

# Example 4: Set up project-specific directories
# mkdir -p ../data ../logs ../cache

# Example 5: Configure git for the project
# if [[ -d "../.git" ]]; then
#     git config --local user.name "Your Name"
#     git config --local user.email "your.email@example.com"
# fi

echo ""
echo "================================================================"
echo "Project initialization complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your project name and settings"
echo "2. Add required domains to whitelist.txt"
echo "3. Add Docker registries to dind-whitelist.txt (if needed)"
echo "4. Start the devcontainer with VS Code or run:"
echo "   docker compose up -d"
echo "================================================================"