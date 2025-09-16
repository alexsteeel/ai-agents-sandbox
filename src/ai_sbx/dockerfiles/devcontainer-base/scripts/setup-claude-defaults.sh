#!/bin/bash
# Don't use set -e in setup scripts since we handle errors explicitly
IFS=$'\n\t'

# Setup script for Claude defaults
# Copies from built-in defaults or mounted host directory

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to copy host Claude settings if mounted
copy_host_claude_settings() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local HOST_SOURCE="/host/.claude"
    local TARGET_DIR="${HOME}/.claude"

    # Check if host Claude directory is mounted and we should copy
    if [[ "$COPY_CLAUDE_SETTINGS" != "true" ]]; then
        return 1
    fi

    if [[ ! -d "${HOST_SOURCE}" ]]; then
        echo -e "${YELLOW}⚠${NC} Host Claude directory not mounted: ${HOST_SOURCE}"
        return 1
    fi

    echo ""
    echo "=== Copying Host Claude Settings ==="
    echo "Source: ${HOST_SOURCE}"
    echo "Target: ${TARGET_DIR}"

    # Create target directories
    mkdir -p "${TARGET_DIR}/agents" "${TARGET_DIR}/commands" "${TARGET_DIR}/hooks" "${TARGET_DIR}/logs"

    # Copy agents if they exist
    if [[ -d "${HOST_SOURCE}/agents" ]]; then
        local agent_count=$(find "${HOST_SOURCE}/agents" -name "*.md" -type f 2>/dev/null | wc -l)
        if [[ $agent_count -gt 0 ]]; then
            cp -r "${HOST_SOURCE}/agents/"* "${TARGET_DIR}/agents/" 2>/dev/null
            echo -e "${GREEN}✓${NC} Copied $agent_count agent(s)"
        fi
    fi

    # Copy commands if they exist
    if [[ -d "${HOST_SOURCE}/commands" ]]; then
        local command_count=$(find "${HOST_SOURCE}/commands" -name "*.md" -type f 2>/dev/null | wc -l)
        if [[ $command_count -gt 0 ]]; then
            cp -r "${HOST_SOURCE}/commands/"* "${TARGET_DIR}/commands/" 2>/dev/null
            echo -e "${GREEN}✓${NC} Copied $command_count command(s)"
        fi
    fi

    # Copy hooks if they exist
    if [[ -d "${HOST_SOURCE}/hooks" ]]; then
        local hook_count=$(find "${HOST_SOURCE}/hooks" -type f 2>/dev/null | wc -l)
        if [[ $hook_count -gt 0 ]]; then
            cp -r "${HOST_SOURCE}/hooks/"* "${TARGET_DIR}/hooks/" 2>/dev/null
            # Make hooks executable
            find "${TARGET_DIR}/hooks" -type f -exec chmod +x {} \;
            echo -e "${GREEN}✓${NC} Copied $hook_count hook(s)"
        fi
    fi

    # Copy settings.json if it exists (but don't override settings.local.json)
    if [[ -f "${HOST_SOURCE}/settings.json" ]]; then
        cp "${HOST_SOURCE}/settings.json" "${TARGET_DIR}/settings.json"
        echo -e "${GREEN}✓${NC} Copied settings.json"
    fi

    # Set proper ownership
    chown -R "${USER}:${USER}" "${TARGET_DIR}" 2>/dev/null

    echo -e "${GREEN}✓${NC} Host Claude settings copied successfully"
    return 0
}

# Function to setup minimal Claude defaults
setup_minimal_claude_defaults() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local SOURCE_DIR="${HOME}/claude-defaults"
    local TARGET_DIR="${HOME}/.claude"

    echo "=== Setting up Minimal Claude Defaults ==="

    # Create target directory structure
    echo "Creating Claude configuration directories..."
    if mkdir -p "${TARGET_DIR}/hooks" "${TARGET_DIR}/logs"; then
        echo -e "${GREEN}✓${NC} Created ${TARGET_DIR} structure"
    else
        echo -e "${RED}✗${NC} Failed to create ${TARGET_DIR} structure"
        return 1
    fi

    # Check if source directory exists
    if [[ ! -d "${SOURCE_DIR}" ]]; then
        echo -e "${YELLOW}⚠${NC} Source directory not found: ${SOURCE_DIR}"
        return 1
    fi

    # Copy minimal files from built-in defaults
    echo "Copying minimal Claude defaults..."

    # Copy settings.json (base settings) if target doesn't exist
    if [[ ! -f "${TARGET_DIR}/settings.json" ]] && [[ -f "${SOURCE_DIR}/settings.json" ]]; then
        cp "${SOURCE_DIR}/settings.json" "${TARGET_DIR}/"
        echo -e "${GREEN}✓${NC} Copied default settings.json"
    fi

    # Copy settings.local.json (notification hook)
    if [[ -f "${SOURCE_DIR}/settings.local.json" ]]; then
        cp "${SOURCE_DIR}/settings.local.json" "${TARGET_DIR}/"
        echo -e "${GREEN}✓${NC} Copied settings.local.json (notification hook)"
    fi

    # Copy notification hook script
    if [[ -f "${SOURCE_DIR}/hooks/notify.sh" ]]; then
        mkdir -p "${TARGET_DIR}/hooks"
        cp "${SOURCE_DIR}/hooks/notify.sh" "${TARGET_DIR}/hooks/"
        chmod +x "${TARGET_DIR}/hooks/notify.sh"
        echo -e "${GREEN}✓${NC} Copied and made executable: notify.sh"
    fi

    # Set proper ownership
    chown -R "${USER}:${USER}" "${TARGET_DIR}" 2>/dev/null

    return 0
}

# Function to verify Claude structure
verify_claude_structure() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local CLAUDE_DIR="${HOME}/.claude"

    echo ""
    echo "=== Verifying Claude Structure ==="

    # Check for settings files
    if [[ -f "${CLAUDE_DIR}/settings.json" ]]; then
        echo -e "${GREEN}✓${NC} settings.json: found"
    else
        echo -e "${YELLOW}⚠${NC} settings.json: not found"
    fi

    if [[ -f "${CLAUDE_DIR}/settings.local.json" ]]; then
        echo -e "${GREEN}✓${NC} settings.local.json: found"
    else
        echo -e "${YELLOW}⚠${NC} settings.local.json: not found"
    fi

    # Count agents, commands, hooks
    local agent_count=0
    local command_count=0
    local hook_count=0

    if [[ -d "${CLAUDE_DIR}/agents" ]]; then
        agent_count=$(find "${CLAUDE_DIR}/agents" -name "*.md" -type f 2>/dev/null | wc -l)
        if [[ $agent_count -gt 0 ]]; then
            echo -e "${GREEN}✓${NC} Agents: $agent_count found"
        fi
    fi

    if [[ -d "${CLAUDE_DIR}/commands" ]]; then
        command_count=$(find "${CLAUDE_DIR}/commands" -name "*.md" -type f 2>/dev/null | wc -l)
        if [[ $command_count -gt 0 ]]; then
            echo -e "${GREEN}✓${NC} Commands: $command_count found"
        fi
    fi

    if [[ -d "${CLAUDE_DIR}/hooks" ]]; then
        hook_count=$(find "${CLAUDE_DIR}/hooks" -type f 2>/dev/null | wc -l)
        if [[ $hook_count -gt 0 ]]; then
            echo -e "${GREEN}✓${NC} Hooks: $hook_count found"
        fi
    fi

    # Show summary
    echo ""
    if [[ "$COPY_CLAUDE_SETTINGS" == "true" ]] && [[ $agent_count -gt 0 || $command_count -gt 0 || $hook_count -gt 1 ]]; then
        echo -e "${GREEN}Using host Claude settings${NC}"
    else
        echo -e "${YELLOW}Using minimal Claude defaults${NC}"
    fi
}

# Main execution
main() {
    local USER="${1:-claude}"

    echo "========================================"
    echo "    Claude Settings Setup"
    echo "========================================"
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""

    # Try to copy host settings first
    if copy_host_claude_settings "$USER"; then
        echo -e "${GREEN}✓${NC} Using host Claude settings"
    else
        # Fall back to minimal defaults
        if setup_minimal_claude_defaults "$USER"; then
            echo -e "${GREEN}✓${NC} Using minimal Claude defaults"
        else
            echo -e "${YELLOW}⚠${NC} Claude setup incomplete"
        fi
    fi

    # Verify structure
    verify_claude_structure "$USER"

    echo ""
    echo -e "${GREEN}✓${NC} Claude setup completed"
    exit 0
}

# Run setup
main "$@"