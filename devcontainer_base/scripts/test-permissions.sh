#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# File and directory permission tests for devcontainer
# Verifies proper ownership and permissions

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Function to check directory permissions
check_directory_permissions() {
    local dir="$1"
    local expected_owner="$2"
    local expected_group="$3"
    local description="$4"
    
    if [[ ! -d "$dir" ]]; then
        echo -e "${YELLOW}⚠${NC} $description: Directory $dir does not exist"
        return 1
    fi
    
    local actual_owner=$(stat -c '%U' "$dir" 2>/dev/null)
    local actual_group=$(stat -c '%G' "$dir" 2>/dev/null)
    local actual_mode=$(stat -c '%a' "$dir" 2>/dev/null)
    
    echo "$description:"
    echo "  Path: $dir"
    echo "  Owner: $actual_owner (expected: $expected_owner)"
    echo "  Group: $actual_group (expected: $expected_group)"
    echo "  Mode: $actual_mode"
    
    local all_good=true
    
    # Check owner
    if [[ "$actual_owner" == "$expected_owner" ]]; then
        echo -e "  ${GREEN}✓${NC} Owner correct"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}✗${NC} Owner mismatch"
        ((TESTS_FAILED++))
        all_good=false
    fi
    
    # Check group
    if [[ "$actual_group" == "$expected_group" ]]; then
        echo -e "  ${GREEN}✓${NC} Group correct"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}✗${NC} Group mismatch"
        ((TESTS_FAILED++))
        all_good=false
    fi
    
    # Check if writable by user
    if [[ -w "$dir" ]]; then
        echo -e "  ${GREEN}✓${NC} Directory is writable"
        ((TESTS_PASSED++))
    else
        echo -e "  ${YELLOW}⚠${NC} Directory is not writable"
    fi
    
    if $all_good; then
        return 0
    else
        return 1
    fi
}

# Function to check workspace permissions
check_workspace_permissions() {
    echo ""
    echo "=== Workspace Permissions Check ==="
    
    local workspace="/workspace"
    
    if [[ ! -d "$workspace" ]]; then
        echo -e "${YELLOW}⚠${NC} Workspace directory $workspace does not exist"
        return 1
    fi
    
    local ws_owner=$(stat -c '%U' "$workspace" 2>/dev/null)
    local ws_group=$(stat -c '%G' "$workspace" 2>/dev/null)
    local ws_mode=$(stat -c '%a' "$workspace" 2>/dev/null)
    
    echo "Workspace: $workspace"
    echo "  Owner: $ws_owner"
    echo "  Group: $ws_group"
    echo "  Mode: $ws_mode"
    
    # Workspace should be owned by host user (not claude) but group should be dev
    if [[ "$ws_group" == "$EXPECTED_GROUP" ]]; then
        echo -e "  ${GREEN}✓${NC} Workspace group is $EXPECTED_GROUP"
        ((TESTS_PASSED++))
    else
        echo -e "  ${YELLOW}⚠${NC} Workspace group is not $EXPECTED_GROUP (this may be expected)"
    fi
    
    # Check if workspace is writable
    if [[ -w "$workspace" ]]; then
        echo -e "  ${GREEN}✓${NC} Workspace is writable"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}✗${NC} Workspace is not writable"
        ((TESTS_FAILED++))
    fi
    
    # Check if we can create files in workspace
    local test_file="$workspace/.permission_test_$$"
    if touch "$test_file" 2>/dev/null; then
        rm -f "$test_file"
        echo -e "  ${GREEN}✓${NC} Can create files in workspace"
        ((TESTS_PASSED++))
    else
        echo -e "  ${RED}✗${NC} Cannot create files in workspace"
        ((TESTS_FAILED++))
    fi
}

# Function to check home directory structure
check_home_directory() {
    echo ""
    echo "=== Home Directory Check ==="
    
    local home="/home/$EXPECTED_USER"
    
    # Check home directory
    check_directory_permissions "$home" "$EXPECTED_USER" "$EXPECTED_USER" "Home directory"
    
    # Check important subdirectories
    echo ""
    echo "Checking home subdirectories:"
    
    # .claude directory
    if [[ -d "$home/.claude" ]]; then
        check_directory_permissions "$home/.claude" "$EXPECTED_USER" "$EXPECTED_USER" ".claude directory"
    else
        echo -e "${YELLOW}⚠${NC} .claude directory does not exist"
    fi
    
    # Check for important files
    echo ""
    echo "Checking configuration files:"
    
    local files_to_check=(
        ".zshrc"
        ".p10k.zsh"
        ".tmux.conf"
    )
    
    for file in "${files_to_check[@]}"; do
        if [[ -f "$home/$file" ]]; then
            local owner=$(stat -c '%U' "$home/$file" 2>/dev/null)
            if [[ "$owner" == "$EXPECTED_USER" ]]; then
                echo -e "${GREEN}✓${NC} $file exists and owned by $EXPECTED_USER"
                ((TESTS_PASSED++))
            else
                echo -e "${YELLOW}⚠${NC} $file exists but owned by $owner"
            fi
        else
            echo -e "${YELLOW}⚠${NC} $file does not exist"
        fi
    done
}

# Function to check Docker socket access
check_docker_access() {
    echo ""
    echo "=== Docker Access Check ==="
    
    # Check if Docker environment variables are set
    if [[ -n "${DOCKER_HOST:-}" ]]; then
        echo -e "${GREEN}✓${NC} DOCKER_HOST is set: $DOCKER_HOST"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} DOCKER_HOST is not set"
    fi
    
    # Check if docker command is available
    if command -v docker >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker command is available"
        ((TESTS_PASSED++))
        
        # Try to connect to Docker daemon
        if docker version >/dev/null 2>&1; then
            echo -e "${GREEN}✓${NC} Can connect to Docker daemon"
            ((TESTS_PASSED++))
        else
            echo -e "${YELLOW}⚠${NC} Cannot connect to Docker daemon"
        fi
    else
        echo -e "${RED}✗${NC} Docker command not found"
        ((TESTS_FAILED++))
    fi
}

# Main test execution
main() {
    echo "========================================"
    echo "    File & Directory Permission Tests"
    echo "========================================"
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    
    # Run tests
    check_workspace_permissions
    check_home_directory
    check_docker_access
    
    # Summary
    echo ""
    echo "========================================"
    echo "Test Summary:"
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All permission tests passed!${NC}"
        exit 0
    else
        echo -e "${YELLOW}Some tests failed. Check permissions configuration.${NC}"
        exit 1
    fi
}

# Run tests
main "$@"