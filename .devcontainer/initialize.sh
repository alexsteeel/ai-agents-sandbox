#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# Initialize development environment script
# Sets up Docker environment and configures directory permissions
# 
# IMPORTANT: Run this BEFORE starting the devcontainer!
# This script sets up host permissions so the container's claude user can write.
#
# Usage: 
#   ./initialize.sh <target-dir>     # Full initialization
#
# Example:
#   ./initialize.sh /home/user/myproject
#   ./initialize.sh $(pwd)/..         # For parent directory
#   ./initialize.sh .                 # For current directory

# Parse arguments
TARGET_DIR="${1:-}"
if [[ -z "$TARGET_DIR" ]]; then
    echo "Error: Target directory required for initialization"
    echo ""
    echo "Usage: $0 <target-dir>"
    echo ""
    echo "Examples:"
    echo "  $0 /home/user/myproject   # Absolute path"
    echo "  $0 \$(pwd)/..              # Parent directory"  
    echo "  $0 .                       # Current directory"
    echo ""
    echo "This script will:"
    echo "  1. Set up Docker services (proxy, docker-in-docker) with project-specific namespace"
    echo "  2. Create 'dev' group (GID 2000) on host"
    echo "  3. Add you to the 'dev' group"
    echo "  4. Set target directory group to 'dev' with write permissions"
    echo ""
    echo "The target directory will be mounted as /workspace in the container."
    exit 1
fi

# Convert to absolute path
TARGET_DIR=$(realpath "$TARGET_DIR")

# Generate project-specific name from full path to ensure uniqueness
# This handles git worktrees and similarly named projects
# Use MD5 hash of path for uniqueness, combined with readable basename
BASENAME=$(basename "$TARGET_DIR" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g')
HASH=$(echo -n "$TARGET_DIR" | md5sum | cut -c1-8)
PROJECT_NAME="${BASENAME}-${HASH}"

echo "Starting initialization for project: $PROJECT_NAME"
echo "Target directory: $TARGET_DIR"
echo "Setting up Docker environment..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Store the project name in .env for Docker Compose to use
# This ensures VS Code uses the same project name
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    # Remove any existing COMPOSE_PROJECT_NAME line
    grep -v "^COMPOSE_PROJECT_NAME=" "$SCRIPT_DIR/.env" > "$SCRIPT_DIR/.env.tmp" || true
    mv "$SCRIPT_DIR/.env.tmp" "$SCRIPT_DIR/.env"
fi
# Add the project name
echo "COMPOSE_PROJECT_NAME=$PROJECT_NAME" >> "$SCRIPT_DIR/.env"
echo "COMPOSE_PROJECT_NAME=$PROJECT_NAME" > "$SCRIPT_DIR/.env.project"

# Check if we're being called from IDE
if [[ -n "${VSCODE_REMOTE_CONTAINERS_SESSION:-}" ]] || [[ "${INITIALIZE_MODE:-}" == "vscode" ]]; then
    echo "Running in VS Code context - skipping service startup (VS Code will handle it)"
else
    # Use project name as Docker Compose project name for isolation
    echo "Starting supporting services with project namespace: $PROJECT_NAME"
    cd "$SCRIPT_DIR"
    COMPOSE_PROJECT_NAME="$PROJECT_NAME" docker compose -f docker-compose.yaml up -d
fi

# Use project name as Docker Compose project name for isolation
echo "Starting supporting services with project namespace: $PROJECT_NAME"
docker compose -f "$SCRIPT_DIR/docker-compose.yaml" -p "$PROJECT_NAME" up docker tinyproxy-dind -d

echo "Setting up Docker certificates for project $PROJECT_NAME..."
CERT_DIR="$HOME/.claude-docker-certs-$PROJECT_NAME"
mkdir -p "$CERT_DIR"

# Container names will be prefixed with project name
# Docker Compose v2 uses hyphen separator with service name
DOCKER_CONTAINER="${PROJECT_NAME}-docker-1"
# Also check with underscore format (older compose versions)
DOCKER_CONTAINER_ALT="${PROJECT_NAME}_docker_1"

if docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER}$"; then
    docker cp "${DOCKER_CONTAINER}:/certs/client/." "$CERT_DIR"
    echo "Docker certificates copied successfully to $CERT_DIR"
    ls -la "$CERT_DIR"
elif docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER_ALT}$"; then
    docker cp "${DOCKER_CONTAINER_ALT}:/certs/client/." "$CERT_DIR"
    echo "Docker certificates copied successfully to $CERT_DIR"
    ls -la "$CERT_DIR"
else
    echo "Warning: Docker container '${DOCKER_CONTAINER}' or '${DOCKER_CONTAINER_ALT}' not found, skipping certificate setup"
fi

echo "Setting up development group..."
readonly GROUP_NAME="dev"
readonly GROUP_GID="2000"

# Check if group exists, create if missing
if getent group "$GROUP_NAME" >/dev/null 2>&1; then
    echo "Group '$GROUP_NAME' already exists."
else
    echo "Creating group '$GROUP_NAME' with GID $GROUP_GID..."
    sudo groupadd -g "$GROUP_GID" "$GROUP_NAME"
fi

# Ensure current user is in the group
if id -Gn "$USER" | tr ' ' '\n' | grep -Fxq "$GROUP_NAME"; then
    echo "User '$USER' is already in group '$GROUP_NAME'."
else
    echo "Adding user '$USER' to group '$GROUP_NAME'..."
    sudo usermod -aG "$GROUP_NAME" "$USER"
    echo "Warning: You may need to log out and back in for group changes to take effect"
fi

echo "Configuring directory permissions..."
if [[ -d "$TARGET_DIR" ]]; then
    echo "Changing group ownership of '$TARGET_DIR' to '$GROUP_NAME'..."
    sudo chgrp -R "$GROUP_NAME" "$TARGET_DIR"

    echo "Setting group write permissions and setgid bit..."
    sudo chmod -R g+rwX "$TARGET_DIR"
    sudo find "$TARGET_DIR" -type d -exec chmod g+s {} +

    # Also set up .claude/projects directory for dev group access
    CLAUDE_PROJECTS_DIR="$HOME/.claude/projects"
    if [[ ! -d "$CLAUDE_PROJECTS_DIR" ]]; then
        echo "Creating .claude/projects directory..."
        mkdir -p "$CLAUDE_PROJECTS_DIR"
    fi

    echo "Setting group ownership of .claude/projects to '$GROUP_NAME'..."
    sudo chgrp -R "$GROUP_NAME" "$CLAUDE_PROJECTS_DIR"
    sudo chmod -R g+rwX "$CLAUDE_PROJECTS_DIR"

    echo "Directory permissions configured successfully."
    echo "Directory: $TARGET_DIR"
    echo "Group: $GROUP_NAME"
    echo "Permissions: Group read/write with setgid"
    
    # Verify permissions
    echo ""
    echo "Verifying permissions:"
    ls -ld "$TARGET_DIR" | head -1
    echo ""
    echo "✓ The 'claude' user in the container (member of 'dev' group) can now write to this directory."
else
    echo "Error: Directory '$TARGET_DIR' does not exist."
    echo "Please create the directory first or provide a valid path."
    exit 1
fi

echo ""
echo "================================================================"
echo "Initialization completed successfully!"
echo ""
echo "Project: $PROJECT_NAME"
echo "Directory: $TARGET_DIR"
echo ""
echo "Proxy Configuration:"
echo "  - Default whitelist domains are built into the proxy image"
echo "  - Add project-specific domains to .devcontainer/whitelist.txt"
echo "  - Restart proxy to apply changes: docker restart ${PROJECT_NAME}-tinyproxy-1"
echo ""
echo "Services running (project-isolated):"
echo "  - ${PROJECT_NAME}-tinyproxy-1: HTTP/HTTPS proxy with whitelist filtering"
echo "  - ${PROJECT_NAME}-docker-1: Docker-in-Docker for isolated container operations"
echo "  - ${PROJECT_NAME}-devcontainer-1: Development environment (when started)"
echo ""
echo "To manage this project's services:"
echo "  cd .devcontainer && COMPOSE_PROJECT_NAME=$PROJECT_NAME docker compose ps     # List services"
echo "  cd .devcontainer && COMPOSE_PROJECT_NAME=$PROJECT_NAME docker compose down   # Stop services"
echo "  cd .devcontainer && COMPOSE_PROJECT_NAME=$PROJECT_NAME docker compose up -d  # Start services"
echo "================================================================"