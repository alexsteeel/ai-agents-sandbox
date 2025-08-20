#!/bin/bash
set -euo pipefail

# DevContainer initialization wrapper
# This is a simple wrapper that calls the system-installed initializer
# NOTE: This runs on the HOST, not in the container

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${1:-$(dirname "$SCRIPT_DIR")}"

# Check if system initializer is installed
if command -v ai-sbx-init-project >/dev/null 2>&1; then
    # Call the system-installed initializer
    ai-sbx-init-project "$PROJECT_DIR"
else
    echo "Error: AI Sandbox system tools not installed."
    echo ""
    echo "Please install the system first:"
    echo "  sudo /path/to/ai_agents_sandbox/install.sh"
    echo ""
    echo "Or if you just need to set permissions manually:"
    echo "  sudo chgrp -R local-ai-team '$PROJECT_DIR'"
    echo "  sudo chmod -R g+rw '$PROJECT_DIR'"
    echo "  find '$PROJECT_DIR' -type d -exec chmod g+s {} +"
    exit 1
fi

# Check for and run secure.init.sh if it exists
SECURE_INIT_SCRIPT="$PROJECT_DIR/.devcontainer/secure.init.sh"
if [[ -x "$SECURE_INIT_SCRIPT" ]]; then
    echo "Found secure.init.sh, running security initialization..."
    "$SECURE_INIT_SCRIPT" "$PROJECT_DIR"
elif [[ -f "$SECURE_INIT_SCRIPT" ]]; then
    echo "Found secure.init.sh but it's not executable, making it executable and running..."
    chmod +x "$SECURE_INIT_SCRIPT"
    "$SECURE_INIT_SCRIPT" "$PROJECT_DIR"
fi