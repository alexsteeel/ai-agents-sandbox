#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Setup script for Claude defaults and configuration
# Syncs Claude configuration, agents, and hooks to user's home directory

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to setup Claude configuration
setup_claude_config() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local SOURCE_DIR="${HOME}/claude-defaults"
    local TARGET_DIR="${HOME}/.claude"
    
    echo "=== Claude Configuration Setup ==="
    echo "User: ${USER}"
    echo "Source: ${SOURCE_DIR}"
    echo "Target: ${TARGET_DIR}"
    echo ""
    
    # Create target directory
    echo "Creating Claude configuration directory..."
    if mkdir -p "${TARGET_DIR}"; then
        echo -e "${GREEN}✓${NC} Created ${TARGET_DIR}"
    else
        echo -e "${RED}✗${NC} Failed to create ${TARGET_DIR}"
        return 1
    fi
    
    # Check if source directory exists
    if [[ ! -d "${SOURCE_DIR}" ]]; then
        echo -e "${YELLOW}⚠${NC} Source directory not found: ${SOURCE_DIR}"
        echo "  Claude defaults will not be copied."
        return 1
    fi
    
    echo "Source directory found: ${SOURCE_DIR}"
    
    # Copy contents (no nesting - use cp -rT)
    echo "Syncing Claude defaults..."
    if cp -rT "${SOURCE_DIR}" "${TARGET_DIR}"; then
        echo -e "${GREEN}✓${NC} Defaults synced to ${TARGET_DIR}"
    else
        echo -e "${RED}✗${NC} Failed to sync defaults"
        return 1
    fi
    
    # Set proper ownership recursively
    echo "Setting ownership..."
    if chown -R "${USER}:${USER}" "${TARGET_DIR}"; then
        echo -e "${GREEN}✓${NC} Ownership set to ${USER}:${USER}"
    else
        echo -e "${RED}✗${NC} Failed to set ownership"
        return 1
    fi
    
    # Create logs directory
    local LOG_DIR="${TARGET_DIR}/logs"
    if mkdir -p "${LOG_DIR}"; then
        echo -e "${GREEN}✓${NC} Created logs directory: ${LOG_DIR}"
        chown "${USER}:${USER}" "${LOG_DIR}"
    else
        echo -e "${YELLOW}⚠${NC} Failed to create logs directory"
    fi
    
    return 0
}

# Function to verify Claude structure
verify_claude_structure() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local CLAUDE_DIR="${HOME}/.claude"
    
    echo ""
    echo "=== Verifying Claude Structure ==="
    
    local required_dirs=(
        "agents"
        "hooks"
        "logs"
    )
    
    local optional_dirs=(
        "commands"
        "templates"
    )
    
    # Check required directories
    echo "Required directories:"
    for dir in "${required_dirs[@]}"; do
        if [[ -d "${CLAUDE_DIR}/${dir}" ]]; then
            local count=$(ls -1 "${CLAUDE_DIR}/${dir}" 2>/dev/null | wc -l)
            echo -e "${GREEN}✓${NC} ${dir}/: found ($count items)"
        else
            echo -e "${RED}✗${NC} ${dir}/: missing"
        fi
    done
    
    # Check optional directories
    echo ""
    echo "Optional directories:"
    for dir in "${optional_dirs[@]}"; do
        if [[ -d "${CLAUDE_DIR}/${dir}" ]]; then
            local count=$(ls -1 "${CLAUDE_DIR}/${dir}" 2>/dev/null | wc -l)
            echo -e "${GREEN}✓${NC} ${dir}/: found ($count items)"
        else
            echo -e "${YELLOW}⚠${NC} ${dir}/: not present"
        fi
    done
}

# Function to check agents
check_claude_agents() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local AGENTS_DIR="${HOME}/.claude/agents"
    
    echo ""
    echo "=== Claude Agents ==="
    
    if [[ ! -d "${AGENTS_DIR}" ]]; then
        echo -e "${YELLOW}⚠${NC} Agents directory not found"
        return 1
    fi
    
    # List available agents
    local agent_files=($(ls -1 "${AGENTS_DIR}"/*.md 2>/dev/null || true))
    
    if [[ ${#agent_files[@]} -eq 0 ]]; then
        echo -e "${YELLOW}⚠${NC} No agents found"
        return 1
    fi
    
    echo "Available agents:"
    for agent_file in "${agent_files[@]}"; do
        local agent_name=$(basename "${agent_file}" .md)
        echo -e "  ${GREEN}•${NC} ${agent_name}"
    done
    
    echo ""
    echo "Total: ${#agent_files[@]} agent(s)"
}

# Function to check hooks
check_claude_hooks() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local HOOKS_DIR="${HOME}/.claude/hooks"
    
    echo ""
    echo "=== Claude Hooks ==="
    
    if [[ ! -d "${HOOKS_DIR}" ]]; then
        echo -e "${YELLOW}⚠${NC} Hooks directory not found"
        return 1
    fi
    
    # List available hooks
    local hook_files=($(ls -1 "${HOOKS_DIR}"/*.py 2>/dev/null || true))
    
    if [[ ${#hook_files[@]} -eq 0 ]]; then
        echo -e "${YELLOW}⚠${NC} No hooks found"
        return 1
    fi
    
    echo "Available hooks:"
    for hook_file in "${hook_files[@]}"; do
        local hook_name=$(basename "${hook_file}" .py)
        # Check if hook is executable
        if [[ -x "${hook_file}" ]]; then
            echo -e "  ${GREEN}•${NC} ${hook_name} (executable)"
        else
            echo -e "  ${YELLOW}•${NC} ${hook_name} (not executable)"
        fi
    done
    
    echo ""
    echo "Total: ${#hook_files[@]} hook(s)"
}

# Function to check settings
check_claude_settings() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local CLAUDE_DIR="${HOME}/.claude"
    
    echo ""
    echo "=== Claude Settings ==="
    
    # Check for settings files
    local settings_files=(
        "settings.json"
        "settings.local.json"
    )
    
    for settings_file in "${settings_files[@]}"; do
        if [[ -f "${CLAUDE_DIR}/${settings_file}" ]]; then
            local size=$(stat -c%s "${CLAUDE_DIR}/${settings_file}" 2>/dev/null || echo "0")
            echo -e "${GREEN}✓${NC} ${settings_file}: found (${size} bytes)"
        else
            echo -e "${YELLOW}⚠${NC} ${settings_file}: not found"
        fi
    done
}

# Function to set executable permissions on hooks
set_hook_permissions() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local HOOKS_DIR="${HOME}/.claude/hooks"
    
    if [[ ! -d "${HOOKS_DIR}" ]]; then
        return 0
    fi
    
    echo ""
    echo "Setting hook permissions..."
    
    # Make Python hooks executable
    local hook_count=0
    for hook_file in "${HOOKS_DIR}"/*.py; do
        if [[ -f "${hook_file}" ]]; then
            chmod +x "${hook_file}"
            ((hook_count++))
        fi
    done
    
    if [[ ${hook_count} -gt 0 ]]; then
        echo -e "${GREEN}✓${NC} Made ${hook_count} hook(s) executable"
    fi
}

# Main execution
main() {
    local USER="${1:-claude}"
    
    echo "========================================"
    echo "    Claude Defaults Setup"
    echo "========================================"
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    
    # Setup Claude configuration
    if setup_claude_config "$USER"; then
        # Verify structure
        verify_claude_structure "$USER"
        
        # Check agents
        check_claude_agents "$USER"
        
        # Check hooks
        check_claude_hooks "$USER"
        
        # Check settings
        check_claude_settings "$USER"
        
        # Set hook permissions
        set_hook_permissions "$USER"
        
        echo ""
        echo -e "${GREEN}✓${NC} Claude defaults setup completed successfully"
        exit 0
    else
        echo ""
        echo -e "${YELLOW}⚠${NC} Claude defaults setup incomplete"
        # Don't fail if Claude defaults are not present - they're optional
        exit 0
    fi
}

# Run setup
main "$@"