#!/bin/bash

docker compose down
cp /home/$(basename "$HOME")/.p10k.zsh .
docker build -f Dockerfile -t claude-code-sandbox:1.0 .

docker network create claude-sandbox-network
#docker compose up -d
mkdir -p ~/.claude-docker-certs
docker cp docker:/certs/client/. ~/.claude-docker-certs
ls ~/.claude-docker-certs

if [ $# -lt 1 ]; then
    echo "Usage: $0 <target-directory>"
    exit 1
fi

# Create group
# Config
GROUP_NAME="dev"
GROUP_GID="2000"

# 1. Check if group exists, create if missing
if getent group "$GROUP_NAME" >/dev/null 2>&1; then
    echo "Group '$GROUP_NAME' already exists."
else
    echo "Creating group '$GROUP_NAME' with GID $GROUP_GID..."
    sudo groupadd -g "$GROUP_GID" "$GROUP_NAME"
fi

TARGET_DIR="$1"

# 2. Ensure current user is in the group
if id -nG "$USER" | grep -qw "$GROUP_NAME"; then
    echo "User '$USER' is already in group '$GROUP_NAME'."
else
    echo "Adding user '$USER' to group '$GROUP_NAME'..."
    sudo usermod -aG "$GROUP_NAME" "$USER"
fi

# 3. Change group ownership and permissions for the target directory
if [ -d "$TARGET_DIR" ]; then
    echo "Changing group of '$TARGET_DIR' to '$GROUP_NAME'..."
    sudo chgrp -R "$GROUP_NAME" "$TARGET_DIR"

    echo "Setting group write permissions and setgid bit..."
    sudo chmod -R g+rwX "$TARGET_DIR"
    sudo find "$TARGET_DIR" -type d -exec chmod g+s {} +

    echo "Done."
else
    echo "Directory '$TARGET_DIR' does not exist."
    exit 1
fi
