#!/bin/bash
set -euo pipefail

# DevContainer initialization wrapper
# This is a simple wrapper that calls the system-installed initializer

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
