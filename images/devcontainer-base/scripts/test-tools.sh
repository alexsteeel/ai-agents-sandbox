#!/bin/bash
# Tool availability tests for devcontainer
# Verifies that all required development tools are installed and functional

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Function to check if a tool is available
check_tool() {
    local tool_name="$1"
    local version_cmd="${2:---version}"
    local required="${3:-true}"  # true or false
    
    if command -v "$tool_name" >/dev/null 2>&1; then
        local version_output
        # Special handling for different version commands
        case "$tool_name" in
            curl|wget)
                version_output=$("$tool_name" --version 2>&1 | head -n1 || echo "installed")
                ;;
            shellcheck|shfmt|yamllint|hadolint)
                version_output=$("$tool_name" --version 2>&1 | head -n1 || echo "installed")
                ;;
            *)
                version_output=$("$tool_name" $version_cmd 2>&1 | head -n1 || echo "installed")
                ;;
        esac
        
        echo -e "${GREEN}✓${NC} $tool_name: $version_output"
        ((TESTS_PASSED++))
        return 0
    else
        if [[ "$required" == "true" ]]; then
            echo -e "${RED}✗${NC} $tool_name: not found (required)"
            ((TESTS_FAILED++))
            return 1
        else
            echo -e "${YELLOW}⚠${NC} $tool_name: not found (optional)"
            return 1
        fi
    fi
}

# Function to check Python tools
check_python_tools() {
    echo "=== Python Development Tools ==="
    
    # Check Python
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1)
        echo -e "${GREEN}✓${NC} Python: $python_version"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${NC} Python3: not found"
        ((TESTS_FAILED++))
    fi
    
    # Check uv (Python package manager)
    check_tool "uv" "--version" "true"
    
    # Check uvx
    check_tool "uvx" "--version" "true"
    
    # Check Python linters (via uvx)
    echo ""
    echo "Python linters (via uvx):"
    
    # Test ruff
    if uvx ruff --version >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} ruff: available via uvx"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} ruff: not available via uvx"
    fi
    
    # Test black
    if uvx black --version >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} black: available via uvx"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} black: not available via uvx"
    fi
    
    # Test mypy
    if uvx mypy --version >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} mypy: available via uvx"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} mypy: not available via uvx"
    fi
}

# Function to check Node.js tools
check_nodejs_tools() {
    echo ""
    echo "=== Node.js Development Tools ==="
    
    # Check Node.js
    check_tool "node" "--version" "true"
    
    # Check npm
    check_tool "npm" "--version" "true"
    
    # Check yarn (optional)
    check_tool "yarn" "--version" "false"
    
    # Check pnpm (optional)
    check_tool "pnpm" "--version" "false"
}

# Function to check container/Docker tools
check_container_tools() {
    echo ""
    echo "=== Container Tools ==="
    
    # Check Docker CLI
    check_tool "docker" "--version" "true"
    
    # Check docker-compose
    check_tool "docker-compose" "--version" "false"
    
    # Check if Docker daemon is accessible
    if docker version >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Docker daemon: accessible"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Docker daemon: not accessible"
    fi
}

# Function to check version control tools
check_vcs_tools() {
    echo ""
    echo "=== Version Control Tools ==="
    
    # Check git
    check_tool "git" "--version" "true"
    
    # GitHub CLI and git-lfs are optional and not checked by default
}

# Function to check shell and terminal tools
check_shell_tools() {
    echo ""
    echo "=== Shell & Terminal Tools ==="
    
    # Check zsh
    check_tool "zsh" "--version" "true"
    
    # Check bash
    check_tool "bash" "--version" "true"
    
    # Check tmux
    check_tool "tmux" "-V" "false"
    
    # Check oh-my-zsh
    if [[ -d "$HOME/.oh-my-zsh" ]]; then
        echo -e "${GREEN}✓${NC} oh-my-zsh: installed"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} oh-my-zsh: not installed"
    fi
    
    # Check powerlevel10k
    if [[ -d "$HOME/.oh-my-zsh/custom/themes/powerlevel10k" ]]; then
        echo -e "${GREEN}✓${NC} powerlevel10k: installed"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} powerlevel10k: not installed"
    fi
}

# Function to check linting tools
check_linting_tools() {
    echo ""
    echo "=== Linting Tools ==="
    
    # Shell linters
    check_tool "shellcheck" "--version" "true"
    check_tool "shfmt" "--version" "true"
    
    # YAML linters
    check_tool "yamllint" "--version" "true"
    
    # Dockerfile linters
    check_tool "hadolint" "--version" "true"
}

# Function to check network tools
check_network_tools() {
    echo ""
    echo "=== Network Tools ==="
    
    # Check curl
    check_tool "curl" "--version" "true"
    
    # Check wget
    check_tool "wget" "--version" "false"
    
    # Check nslookup/dig
    check_tool "nslookup" "-version" "false"
    check_tool "dig" "-v" "false"
    
    # netcat is optional and not checked by default
}

# Function to check editor tools
check_editor_tools() {
    echo ""
    echo "=== Editor Tools ==="
    
    # nano is optional and not checked by default
    
    # Check vim
    check_tool "vim" "--version" "false"
    
    # Check vi
    check_tool "vi" "--version" "false"
}

# Function to check Claude-specific tools
check_claude_tools() {
    echo ""
    echo "=== Claude-Specific Tools ==="
    
    # Check claude CLI
    if command -v claude >/dev/null 2>&1; then
        local claude_version=$(claude --version 2>&1 | head -n1 || echo "installed")
        echo -e "${GREEN}✓${NC} claude: $claude_version"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} claude: not found (may not be installed yet)"
    fi
    
    # Check Claude configuration directory
    if [[ -d "$HOME/.ai_agents_sandbox" ]]; then
        echo -e "${GREEN}✓${NC} Claude config directory: exists"
        ((TESTS_PASSED++))
        
        # Check for agents directory
        if [[ -d "$HOME/.ai_agents_sandbox/agents" ]]; then
            local agent_count=$(ls -1 "$HOME/.ai_agents_sandbox/agents"/*.md 2>/dev/null | wc -l)
            echo -e "${GREEN}✓${NC} Claude agents: $agent_count agent(s) found"
            ((TESTS_PASSED++))
        else
            echo -e "${YELLOW}⚠${NC} Claude agents directory: not found"
        fi
    else
        echo -e "${YELLOW}⚠${NC} Claude config directory: not found"
    fi
}

# Function to check system utilities
check_system_utilities() {
    echo ""
    echo "=== System Utilities ==="
    
    # Check essential commands
    local utils=(
        "ls"
        "cp"
        "mv"
        "rm"
        "mkdir"
        "chmod"
        "chown"
        "grep"
        "sed"
        "awk"
        "find"
        "which"
        "whoami"
        "id"
        "ps"
        "top"
        "df"
        "du"
        "tar"
        "gzip"
        "unzip"
    )
    
    local all_present=true
    for util in "${utils[@]}"; do
        if ! command -v "$util" >/dev/null 2>&1; then
            echo -e "${RED}✗${NC} $util: not found"
            ((TESTS_FAILED++))
            all_present=false
        fi
    done
    
    if $all_present; then
        echo -e "${GREEN}✓${NC} All essential system utilities are present"
        ((TESTS_PASSED++))
    fi
}

# Main test execution
main() {
    echo "========================================"
    echo "    Development Tools Tests"
    echo "========================================"
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    
    # Run tests
    check_python_tools
    check_nodejs_tools
    check_container_tools
    check_vcs_tools
    check_shell_tools
    check_linting_tools
    check_network_tools
    check_editor_tools
    check_claude_tools
    check_system_utilities
    
    # Summary
    echo ""
    echo "========================================"
    echo "Test Summary:"
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tool tests passed!${NC}"
        exit 0
    else
        echo -e "${YELLOW}Some required tools are missing.${NC}"
        exit 1
    fi
}

# Run tests
main "$@"