#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# Initialize development environment script
# Sets up Docker environment and configures directory permissions

# Validate target directory argument
TARGET_DIR="$1"
if [[ -z "$TARGET_DIR" ]]; then
    echo "Error: Target directory cannot be empty"
    exit 1
fi

echo "Starting initialization with target directory: $TARGET_DIR"

echo "Setting up Docker environment..."
docker compose -f ./.devcontainer/docker-compose.yaml down || echo "Warning: docker compose down failed (container may not be running)"

if ! docker network ls | grep -q claude-sandbox-network; then
    echo "Creating claude-sandbox-network..."
    docker network create claude-sandbox-network
else
    echo "Network claude-sandbox-network already exists"
fi

echo "Starting Docker containers..."
docker compose -f ./.devcontainer/docker-compose.yaml  up -d

echo "Setting up Docker certificates..."
mkdir -p ~/.claude-docker-certs
if docker ps --format '{{.Names}}' | grep -q '^docker$'; then
    docker cp docker:/certs/client/. ~/.claude-docker-certs
    echo "Docker certificates copied successfully"
    ls -la ~/.claude-docker-certs
else
    echo "Warning: Docker container 'docker' not found, skipping certificate setup"
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

    echo "Directory permissions configured successfully."
    echo "Directory: $TARGET_DIR"
    echo "Group: $GROUP_NAME"
    echo "Permissions: Group read/write with setgid"
else
    echo "Error: Directory '$TARGET_DIR' does not exist."
    echo "Please create the directory first or provide a valid path."
    exit 1
fi

echo "Initialization completed successfully!"
