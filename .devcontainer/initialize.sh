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
docker compose -f ./.devcontainer/docker-compose.yaml down || echo "Warning: docker compose down failed (containers may not be running)"
echo "Starting supporting services (proxy, docker-dind) with Compose-managed networks..."

# Generate Tinyproxy configuration and filter from allowed domains
generate_tinyproxy_conf() {
    local conf_dir="./.devcontainer/tinyproxy"
    local logs_dir="./.devcontainer/tinyproxy-logs"
    local conf_file="${conf_dir}/tinyproxy.conf"
    local filter_file="${conf_dir}/filter"
    local domains_file="./.devcontainer/allowed-domains.txt"
    local default_domains_file="/usr/local/etc/default-allowed-domains.txt"
    echo "Generating Tinyproxy config at ${conf_file}..."
    mkdir -p "${conf_dir}" "${logs_dir}"

    # Base config
    cat >"${conf_file}" <<'TPCONF'
Port 8888
Timeout 600
MaxClients 100
StartServers 5
MinSpareServers 5
MaxSpareServers 20
LogLevel Info
LogFile "/var/log/tinyproxy/tinyproxy.log"
PidFile "/var/run/tinyproxy/tinyproxy.pid"
DisableViaHeader Yes
ConnectPort 443
ConnectPort 80

# Filtering: default deny, allow only patterns in Filter file
Filter "/etc/tinyproxy/filter"
FilterExtended Yes
FilterURLs On
FilterDefaultDeny Yes
TPCONF

    # Build filter allowlist from default + project domains (ignore comments/empty, dedupe)
    : >"${filter_file}"
    if [[ -f "${default_domains_file}" || -f "${domains_file}" ]]; then
        echo "Building filter from default + project allowlists"
        # shellcheck disable=SC2016
        mapfile -t domains < <(cat "${default_domains_file}" "${domains_file}" 2>/dev/null \
            | sed -e 's/#.*$//' -e 's/^\s*//' -e 's/\s*$//' \
            | awk 'NF' \
            | sort -u)
        for domain in "${domains[@]}"; do
            # Escape dots for regex and allow subdomains
            escaped=$(printf '%s' "$domain" | sed 's/\./\\\./g')
            echo "://\(.*\\.\)?${escaped}\(/\|$\)" >>"${filter_file}"
        done
    else
        echo "Warning: No allowlist files found. All outbound traffic will be blocked by default."
    fi

    echo "Tinyproxy configuration generated."
}

generate_tinyproxy_conf

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
