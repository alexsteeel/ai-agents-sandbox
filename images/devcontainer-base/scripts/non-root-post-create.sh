#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Post-create script for devcontainer setup
# This script orchestrates the setup and testing process by calling specialized scripts

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

main() {
    echo "========================================"
    echo "    Post-Create Setup"
    echo "========================================"
    echo "Starting post-create setup..."
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    
    # Get user information
    local USER="claude"
    local HOME="/home/${USER}"
    local SCRIPTS_DIR="$(dirname "$0")"
    
    # Create logs directory in scripts folder to avoid conflicts with .claude directory
    local LOG_DIR="${HOME}/scripts/logs"
    mkdir -p "${LOG_DIR}"
    
    # Start logging while keeping console output
    exec > >(tee -a "${LOG_DIR}/post_create.log") 2>&1
    
    echo "Running as: $(whoami)"
    echo "Scripts directory: ${SCRIPTS_DIR}"
    echo ""
    
    # Setup phase
    echo "========================================"
    echo "    Setup Phase"
    echo "========================================"
    
    # Setup P10k configuration
    echo ""
    echo ">>> Running P10k setup..."
    if [[ -x "${SCRIPTS_DIR}/setup-p10k.sh" ]]; then
        "${SCRIPTS_DIR}/setup-p10k.sh" "${USER}" || echo -e "${YELLOW}⚠${NC} P10k setup had warnings"
    else
        echo -e "${YELLOW}⚠${NC} setup-p10k.sh not found or not executable"
    fi
    
    # Setup Claude defaults
    echo ""
    echo ">>> Running Claude defaults setup..."
    if [[ -x "${SCRIPTS_DIR}/setup-claude-defaults.sh" ]]; then
        "${SCRIPTS_DIR}/setup-claude-defaults.sh" "${USER}" || echo -e "${YELLOW}⚠${NC} Claude setup had warnings"
    else
        echo -e "${YELLOW}⚠${NC} setup-claude-defaults.sh not found or not executable"
    fi
    
    # Configure git safe directory to avoid dubious ownership errors
    echo ""
    echo ">>> Configuring git safe directory..."
    git config --global --add safe.directory /workspace || echo -e "${YELLOW}⚠${NC} Failed to configure git safe directory"
    
    # Testing phase
    echo ""
    echo "========================================"
    echo "    Testing Phase"
    echo "========================================"
    
    # Don't fail on test failures - we want to run all tests
    set +e
    
    local test_results=()
    
    # Run permission tests
    echo ""
    echo ">>> Running permission tests..."
    if [[ -x "${SCRIPTS_DIR}/test-permissions.sh" ]]; then
        if "${SCRIPTS_DIR}/test-permissions.sh" > >(tee -a "${LOG_DIR}/test_permissions.log") 2>&1; then
            test_results+=("permissions: PASSED")
        else
            test_results+=("permissions: FAILED")
        fi
    else
        echo -e "${YELLOW}⚠${NC} test-permissions.sh not found or not executable"
        test_results+=("permissions: SKIPPED")
    fi
    
    # Run network tests
    echo ""
    echo ">>> Running network tests..."
    if [[ -x "${SCRIPTS_DIR}/test-network.sh" ]]; then
        if "${SCRIPTS_DIR}/test-network.sh" > >(tee -a "${LOG_DIR}/test_network.log") 2>&1; then
            test_results+=("network: PASSED")
        else
            test_results+=("network: FAILED")
        fi
    else
        echo -e "${YELLOW}⚠${NC} test-network.sh not found or not executable"
        test_results+=("network: SKIPPED")
    fi
    
    # Run tool tests
    echo ""
    echo ">>> Running tool tests..."
    if [[ -x "${SCRIPTS_DIR}/test-tools.sh" ]]; then
        if "${SCRIPTS_DIR}/test-tools.sh" > >(tee -a "${LOG_DIR}/test_tools.log") 2>&1; then
            test_results+=("tools: PASSED")
        else
            test_results+=("tools: FAILED")
        fi
    else
        echo -e "${YELLOW}⚠${NC} test-tools.sh not found or not executable"
        test_results+=("tools: SKIPPED")
    fi
    
    # Re-enable exit on error
    set -e
    
    # Summary
    echo ""
    echo "========================================"
    echo "    Post-Create Summary"
    echo "========================================"
    
    echo "Test Results:"
    for result in "${test_results[@]}"; do
        echo "  - $result"
    done
    
    echo ""
    echo "Log files created in: ${LOG_DIR}"
    echo "  - post_create.log (this output)"
    echo "  - test_permissions.log"
    echo "  - test_network.log"
    echo "  - test_tools.log"
    
    echo ""
    echo -e "${GREEN}✓${NC} Post-create setup completed"
    echo "========================================"
}

# Run main function
main "$@"