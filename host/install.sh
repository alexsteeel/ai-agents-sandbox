#!/bin/bash
set -euo pipefail

# Host scripts installer
# Installs AI Agents Sandbox management scripts to system paths

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INSTALL]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "This script must be run as root (use sudo)"
    echo "Usage: sudo $0"
    exit 1
fi

# Installation directories
BIN_DIR="/usr/local/bin"
SHARE_DIR="/usr/local/share/ai-agents-sandbox"

print_status "Installing AI Agents Sandbox host scripts..."

# Create share directory
print_status "Creating shared directory: $SHARE_DIR"
mkdir -p "$SHARE_DIR"

# Install executable scripts to /usr/local/bin
SCRIPTS=(
    "ai-sbx-create-task-worktree"
    "ai-sbx-remove-task-worktree"
    "ai-sbx-notify-watch"
    "ai-sbx-init-project"
)

for script in "${SCRIPTS[@]}"; do
    src="$SCRIPT_DIR/$script"
    dst="$BIN_DIR/$script"
    
    if [[ ! -f "$src" ]]; then
        print_error "Script not found: $src"
        exit 1
    fi
    
    print_status "Installing $script to $BIN_DIR"
    install -m 755 "$src" "$dst"
    
    # Verify installation
    if [[ -x "$dst" ]]; then
        print_status "✓ Installed: $dst"
    else
        print_error "Failed to install: $dst"
        exit 1
    fi
done

# Copy templates to share directory
TEMPLATE_DIR="$SCRIPT_DIR/../templates"
if [[ -d "$TEMPLATE_DIR" ]]; then
    print_status "Installing templates to $SHARE_DIR"
    cp -r "$TEMPLATE_DIR"/* "$SHARE_DIR/"
    
    # Set proper permissions
    chmod 644 "$SHARE_DIR"/*.yaml 2>/dev/null || true
    
    print_status "✓ Templates installed"
else
    print_warning "Templates directory not found at $TEMPLATE_DIR"
fi

# Copy docker-proxy configuration
DOCKER_PROXY_DIR="$SCRIPT_DIR/docker-proxy"
if [[ -d "$DOCKER_PROXY_DIR" ]]; then
    print_status "Installing Docker proxy configuration to $SHARE_DIR/docker-proxy"
    mkdir -p "$SHARE_DIR/docker-proxy"
    cp -r "$DOCKER_PROXY_DIR"/* "$SHARE_DIR/docker-proxy/"
    
    # Set proper permissions
    chmod 644 "$SHARE_DIR/docker-proxy"/*.yaml 2>/dev/null || true
    chmod 644 "$SHARE_DIR/docker-proxy"/*.md 2>/dev/null || true
    
    print_status "✓ Docker proxy configuration installed"
else
    print_warning "Docker proxy directory not found at $DOCKER_PROXY_DIR"
fi

# Create local-ai-team group if it doesn't exist
DEV_GID=2000
if ! getent group $DEV_GID >/dev/null 2>&1; then
    print_status "Creating local-ai-team group (GID $DEV_GID) for file sharing..."
    groupadd -g $DEV_GID local-ai-team
    print_status "✓ Group 'local-ai-team' created"
else
    print_status "✓ Group 'local-ai-team' already exists"
fi

# Add current user (if using sudo) to local-ai-team group
if [[ -n "${SUDO_USER:-}" ]]; then
    print_status "Adding $SUDO_USER to local-ai-team group..."
    usermod -aG local-ai-team "$SUDO_USER"
    print_status "✓ User added to local-ai-team group"
fi

# Create notification directory with proper permissions
if [[ -n "${SUDO_USER:-}" ]]; then
    USER_HOME="/home/${SUDO_USER}"
    CLAUDE_DIR="${USER_HOME}/.ai_agents_sandbox"
    NOTIFICATION_DIR="$CLAUDE_DIR/notifications"
    PROJECTS_DIR="$CLAUDE_DIR/projects"
    
    print_status "Creating AI Agents Sandbox directories for notifications"
    
    # Create directories as root then change ownership
    # This approach is more reliable than sudo -u
    mkdir -p "$NOTIFICATION_DIR"
    mkdir -p "$PROJECTS_DIR"
    
    # Get the user's primary group
    USER_GROUP=$(id -gn "$SUDO_USER")
    
    # Set ownership to the actual user
    chown -R "${SUDO_USER}:${USER_GROUP}" "$CLAUDE_DIR"
    
    print_status "✓ Notification directories created with proper ownership"
fi

# Summary
echo ""
print_status "Installation complete!"
echo ""
echo "Installed commands:"
for script in "${SCRIPTS[@]}"; do
    echo "  - $script"
done
echo ""
echo "Templates installed to: $SHARE_DIR"
echo ""
echo "Next steps:"
echo "1. Log out and back in for group membership to take effect"
echo "2. Copy .devcontainer.example to your project"
echo "3. (Optional) Run 'ai-sbx-notify-watch' to enable desktop notifications"
echo ""

exit 0