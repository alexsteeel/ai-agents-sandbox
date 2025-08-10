#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Setup script for Powerlevel10k configuration
# Copies p10k configuration from host to container

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to setup p10k configuration
setup_p10k_config() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local SOURCE_FILE="/host/.p10k.zsh"
    local TARGET_FILE="${HOME}/.p10k.zsh"
    
    echo "=== Powerlevel10k Configuration Setup ==="
    echo "User: ${USER}"
    echo "Home: ${HOME}"
    echo ""
    
    # Check if source file exists
    if [[ ! -f "${SOURCE_FILE}" ]]; then
        echo -e "${YELLOW}⚠${NC} Source file not found: ${SOURCE_FILE}"
        echo "  P10k configuration will not be copied."
        echo "  To enable p10k configuration, ensure .p10k.zsh exists in your home directory"
        return 1
    fi
    
    echo "Source file found: ${SOURCE_FILE}"
    
    # Copy the configuration file
    echo "Copying p10k configuration..."
    if cp -f "${SOURCE_FILE}" "${TARGET_FILE}"; then
        echo -e "${GREEN}✓${NC} Configuration copied to ${TARGET_FILE}"
    else
        echo -e "${RED}✗${NC} Failed to copy configuration"
        return 1
    fi
    
    # Set proper ownership
    echo "Setting ownership..."
    if chown "${USER}:${USER}" "${TARGET_FILE}"; then
        echo -e "${GREEN}✓${NC} Ownership set to ${USER}:${USER}"
    else
        echo -e "${RED}✗${NC} Failed to set ownership"
        return 1
    fi
    
    # Set readable permissions
    echo "Setting permissions..."
    if chmod 644 "${TARGET_FILE}"; then
        echo -e "${GREEN}✓${NC} Permissions set to 644"
    else
        echo -e "${RED}✗${NC} Failed to set permissions"
        return 1
    fi
    
    # Verify the file
    echo ""
    echo "Verification:"
    if [[ -f "${TARGET_FILE}" ]]; then
        local file_info=$(ls -la "${TARGET_FILE}")
        echo -e "${GREEN}✓${NC} File exists: ${file_info}"
        
        # Check if oh-my-zsh and powerlevel10k are installed
        if [[ -d "${HOME}/.oh-my-zsh" ]]; then
            echo -e "${GREEN}✓${NC} Oh My Zsh is installed"
            
            if [[ -d "${HOME}/.oh-my-zsh/custom/themes/powerlevel10k" ]]; then
                echo -e "${GREEN}✓${NC} Powerlevel10k theme is installed"
            else
                echo -e "${YELLOW}⚠${NC} Powerlevel10k theme not found"
                echo "  Install with: git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${HOME}/.oh-my-zsh/custom/themes/powerlevel10k"
            fi
        else
            echo -e "${YELLOW}⚠${NC} Oh My Zsh not found"
            echo "  P10k configuration requires Oh My Zsh with Powerlevel10k theme"
        fi
        
        return 0
    else
        echo -e "${RED}✗${NC} File verification failed"
        return 1
    fi
}

# Function to check zsh configuration
check_zsh_config() {
    local USER="${1:-claude}"
    local HOME="/home/${USER}"
    local ZSHRC="${HOME}/.zshrc"
    
    echo ""
    echo "=== Checking Zsh Configuration ==="
    
    if [[ ! -f "${ZSHRC}" ]]; then
        echo -e "${YELLOW}⚠${NC} .zshrc not found"
        return 1
    fi
    
    # Check if p10k is sourced in .zshrc
    if grep -q "source.*\.p10k\.zsh" "${ZSHRC}" || grep -q "\[.*-r.*\.p10k\.zsh.*\]" "${ZSHRC}"; then
        echo -e "${GREEN}✓${NC} P10k configuration is sourced in .zshrc"
    else
        echo -e "${YELLOW}⚠${NC} P10k configuration is not sourced in .zshrc"
        echo "  Add to .zshrc: [[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh"
    fi
    
    # Check if theme is set to powerlevel10k
    if grep -q "^ZSH_THEME.*powerlevel10k" "${ZSHRC}"; then
        echo -e "${GREEN}✓${NC} Powerlevel10k theme is configured"
    else
        echo -e "${YELLOW}⚠${NC} Powerlevel10k theme is not set"
        echo "  Set in .zshrc: ZSH_THEME=\"powerlevel10k/powerlevel10k\""
    fi
}

# Main execution
main() {
    local USER="${1:-claude}"
    
    echo "========================================"
    echo "    Powerlevel10k Setup"
    echo "========================================"
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    
    # Setup p10k configuration
    if setup_p10k_config "$USER"; then
        # Check zsh configuration
        check_zsh_config "$USER"
        
        echo ""
        echo -e "${GREEN}✓${NC} Powerlevel10k setup completed successfully"
        exit 0
    else
        echo ""
        echo -e "${YELLOW}⚠${NC} Powerlevel10k setup skipped (no configuration file)"
        # Don't fail if p10k config is not present - it's optional
        exit 0
    fi
}

# Run setup
main "$@"